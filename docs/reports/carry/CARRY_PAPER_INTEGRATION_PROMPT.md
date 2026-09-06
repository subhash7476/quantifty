# Carry Sleeve — PAPER Mode Integration Prompt (for DeepSeek)

**Created:** 2026-07-23
**Parent docs:** `CARRY_IMPLEMENTATION_BRIDGE.md` §4.1 (rebalance execution path), §5.3 (parity-gate
bug history — read this before touching anything here), §6 (go-live gate, step 4 = PAPER).
**Role split (standing):** DeepSeek implements from this written prompt. Claude wrote the prompt
and reviews the delivered work; Claude does not implement this deliverable.
**Scope:** wire the already-built, already-parity-verified Carry construction into a running
PAPER-mode `LoopDriver`. No new signal/construction logic — §5's parity gate already proved
`compute_target_book` reproduces research exactly. This prompt is pure integration.

---

## 0. Read this before writing any code

§5.3 of the bridge doc records three real bugs found in this exact codebase during the parity
work: a gate verdict that ignored its own tolerance check, a construction fix applied to a
throwaway script copy instead of the real production module, and a NULL-leak in a SQL join. All
three were caught only by independently re-running the code, not by trusting a report. Apply the
same discipline here: state a falsifiable prediction before each deliverable, then report the
actual result next to it, and do not mark anything PASS on your own say-so — Claude re-runs
everything before accepting it.

**Verified facts about the current code (2026-07-23, re-check before relying on line numbers):**
- `build_runner()` in `scripts/fno_runner.py:105` has no hook parameter. `ExecutionHandler` is
  constructed at `fno_runner.py:243`, `LoopDriver` at `fno_runner.py:265`, with no
  `rebalance_hook` passed.
- `LoopDriver.__init__` already accepts `rebalance_hook` (`core/runtime/driver.py:159`) and
  invokes it once per tick after clock advance (`driver.py:670-671`). This seam is real and
  already tested; you are feeding it, not building it.
- `CarryRebalancerHook` (`core/execution/portfolio/carry_rebalancer.py`) bypasses
  `process_signal` entirely — it writes `FillEvent`s straight to
  `position_tracker.update_from_fill()`. This is deliberate (§4.1: book-level batch, not
  per-symbol streaming) and must not change.
- Because of that bypass, `ExecutionHandler.metrics.cash_balance` and the handler's own
  drawdown/equity tracking (`handler.py:279`, `_check_margin_budget` at `handler.py:1130-1166`)
  **never see Carry fills**. Any PAPER monitoring must read `position_tracker` /
  `PnLTracker` directly — the handler's built-in telemetry will show a flat, wrong picture.
- `MarginTracker.margin_rate` defaults to `0.2` (`core/execution/margin_tracker.py:11`);
  `ExecutionConfig.max_capital_utilisation` defaults to `0.80` (`handler.py:110`). These are
  pre-existing platform defaults — do not change them.
- ADV wiring in `CarryRebalancerHook` is already fixed (`_load_adva` is an instance method
  reading `self._bhavcopy_db`), but `bhavcopy_db_path` still silently defaults to `None` with no
  warning. Step 1 below fixes the silence, not the default.

---

## 1. ADV-wiring log warning

**File:** `core/execution/portfolio/carry_rebalancer.py`, `CarryRebalancerHook.__init__`.

When `bhavcopy_db_path` is `None`, log a `logging.WARNING` (not print) stating ADV capping is
disabled for this instance. Two lines. Do not change the default itself — a caller may
legitimately want ADV capping off; the fix is making that choice loud, not removing the choice.

---

## 2. `rebalance_hook_factory` parameter on `build_runner()`

**File:** `scripts/fno_runner.py`.

Add a parameter:
```python
rebalance_hook_factory: Optional[Callable[[ExecutionHandler], Any]] = None,
```
After `execution = ExecutionHandler(**handler_kwargs)` (currently line 243), call the factory
with the constructed handler if provided, and pass the result as `rebalance_hook=` into the
`LoopDriver(...)` call (currently line 265). This is the only change to `build_runner()` — do not
restructure anything else in it. The factory pattern exists because `CarryRebalancerHook` needs
the handler at construction time, but the handler is built inside `build_runner()` after all its
other parameters are already collected; this is the standard fix for that ordering problem, not a
new idea to second-guess.

---

## 3. Gross-exposure policy injection (replaces the flat `gross_exposure` constant)

**File:** `core/execution/portfolio/carry_rebalancer.py`.

This is the substantive design change in this prompt. Do not skip the reasoning below —
implementing it as a flat constant again defeats the point.

**Why:** the same construction code (`compute_target_book`, `_execute`, the margin-feasibility
check in §4 below) must run unchanged in PAPER and in a future LIVE — that is what "Runner is
Neutral" and the parity gate's deterministic-reproducibility guarantee require. What legitimately
differs between PAPER and LIVE is *how much gross exposure to target this rebalance*: PAPER can
run at full research gross from day one (there is no real capital to conserve — the point is
testing signal and mechanics). LIVE needs capital-aware sizing (starting capital, running PnL,
drawdown state) that does not exist yet and must not be invented as a side effect of this task.

**Change `CarryRebalancerHook.__init__`** to accept a policy callable instead of a flat float:
```python
gross_exposure_policy: Callable[[CapitalState], float]
```
replacing the current `gross_exposure: float` parameter. Define a minimal `CapitalState` — at
minimum `starting_capital`, `current_equity`, `realized_pnl`, `current_drawdown_pct` — sourced
from `position_tracker` / `PnLTracker` (not `ExecutionHandler.metrics`, per §0). Call the policy
inside `_execute()` at the top of each rebalance, before `compute_target_book`.

**Ship two policies:**
- `paper_gross_exposure_policy(state) -> float`: returns a fixed constant (see §5 for the
  number), ignoring `state` entirely. This is intentional, not a stub to fill in later.
- `live_gross_exposure_policy(state) -> float`: **do not design this.** Raise
  `NotImplementedError("LIVE gross-exposure policy is a separate, reviewed decision — see bridge
  §8 no-re-optimization guardrail")`, or equivalent. The bridge doc's guardrail is explicit that
  the frozen construction is the product and must not be re-optimized for live; a PnL-reactive
  sizing rule is new behavior never present in TRAIN/HOLDOUT/parity, and designing it is its own
  pre-registered decision, not something to fall out of this integration task.

---

## 4. Margin-feasibility check (always on, both modes — no PAPER bypass)

**File:** `core/execution/portfolio/carry_rebalancer.py`, inside `_execute()`, after the policy
call and before (or as part of) calling `compute_target_book`.

Compute directly, do **not** route through the polymorphic `MarginCalculator` protocol
(`get_incremental_margin` requires per-symbol quantity/price/lot_size, which the rebalancer does
not have — it works purely in rupee capital per underlying; forcing polymorphism here means
building futures-contract resolution that is out of scope for this task):

```
required_margin = projected_gross_exposure * MarginTracker.margin_rate   # 0.2 default
available = execution.position_tracker's capital state * max_capital_utilisation  # 0.80 default
if required_margin > available:
    log a clear rejection (which formation date, requested gross, required margin, available) and
    skip the rebalance for this date — do not partially execute.
```

State explicitly in your report that this is a flat-rate approximation, not SPAN-accurate, and
that it must be revisited if a SPAN snapshot is ever wired into this path (that would require the
contract-level resolution this task deliberately avoids).

This check is **not** disabled for PAPER. It stays on in both modes. PAPER simply never trips it,
because `paper_gross_exposure_policy` requests an amount `initial_capital` (§5) comfortably
supports — that is the correct way to make "capital should not reject trades in PAPER" true,
not a mode-specific carve-out on the check itself.

---

## 5. `scripts/carry_paper_runner.py` — the entry point

New file. Wires everything together:

```python
def _rebalance_hook_factory(execution_handler):
    return CarryRebalancerHook(
        facts_db_path="data/signal_engine/carry/facts.duckdb",
        execution_handler=execution_handler,
        gross_exposure_policy=paper_gross_exposure_policy,
        bhavcopy_db_path="data/market_data/futures_bhavcopy.duckdb",
    )
```

- **PAPER gross-exposure constant: Rs 1 Cr** (`10_000_000.0`), matching the fixed
  `GROSS_EXPOSURE` used throughout `run_net_spread.py` / `parity_check.py` /
  `capacity_analysis.py` — PAPER should test the exact book size that was validated, not an
  arbitrary one.
- **`initial_capital`: Rs 1 Cr** (`10_000_000.0`), matching gross exposure 1:1. At the flat 20%
  margin rate this gives ~20% utilisation against the 80% cap — comfortable headroom, never binds,
  without being an inflated placeholder number that misrepresents real capital. Do not set this
  to an arbitrarily large number (e.g. Rs 100 Cr) to "guarantee" the check never rejects — that
  defeats the check's purpose of being a real, meaningful constraint even in PAPER.
- **Signal source:** a trivial `NoOpSignalSource` (`on_bar()` returns `[]`) — the rebalance hook
  drives everything; no per-symbol signal path is used.
- **Symbols list:** OPEN QUESTION, do not decide unilaterally — see §7.

---

## 6. Fee + slippage accounting in `_execute_deltas` — logged, not "validated"

**File:** `core/execution/portfolio/carry_rebalancer.py`, `_execute_deltas`.

Currently hardcodes `fee=0.0`. Change to compute real futures fees via `futures_fees()` (already
imported as `_calc_fees`, currently unused) and apply `SLIPPAGE_BP = 5` (already defined, unused)
as an additional deduction on the `FillEvent.fee` field. Log total fees and slippage per
rebalance.

**Do not describe this as "measuring realized slippage against the 5bp assumption."** It cannot
do that: the fill is synthetic (`price=1.0`, `PaperBroker` fills at zero slippage by design), so
applying 5bp to it and logging "5bp" is circular — the logged number *is* the assumption, not an
independent measurement of it. The bridge doc's §6.4 goal of validating realized slippage belongs
to LIVE (real broker fills), not PAPER. Scope this step honestly: it makes fee/slippage costs
visible in the fill record for accounting completeness, and PAPER's actual job is validating that
the fill pipeline, position tracking, and rebalancer wiring run correctly end-to-end without
crashing — nothing about cost realism.

---

## 7. Open question — do not answer unilaterally, flag it in your report

**How does `facts.duckdb` get fresh formation dates as PAPER runs forward in real time?**
`CarryRebalancerHook._load_calendar()` reads `SELECT DISTINCT formation_date FROM carry_facts`
once at construction and only fires on dates already in that set. `publish_facts.py` is a
batch/backfill script run on demand against historical bhavcopy — nothing in this codebase
currently refreshes `carry_facts` on a schedule. If PAPER is meant to run forward past whatever
date `publish_facts.py` was last run for, the rebalancer will simply never fire again once it
passes the last known formation date, silently. **Do not build a scheduler or cron job to solve
this** — that is real new infrastructure and out of scope here. Instead: state this limitation
explicitly in your delivery report, and propose (without implementing) what re-running
`publish_facts.py` on a monthly cadence would require. This also answers the symbols-list
question in §5 — until this is resolved, treat the PAPER run as bounded to the formation dates
already present in `facts.duckdb` today, and pull the symbols list as
`SELECT DISTINCT underlying FROM carry_facts` rather than inventing a separate universe source.

---

## 8. Tests

Extend `tests/portfolio/test_carry_rebalancer.py`:
- Policy injection: `paper_gross_exposure_policy` returns the fixed constant regardless of
  `CapitalState` contents; `live_gross_exposure_policy` raises `NotImplementedError`.
- Margin-feasibility check: a proposed book requiring more than `max_capital_utilisation *
  available_capital` is rejected and logged, not partially executed; a feasible book proceeds
  unchanged from current behavior.
- ADV-wiring warning: constructing `CarryRebalancerHook` with `bhavcopy_db_path=None` emits a
  `WARNING` log record (use `caplog` or equivalent).
- Fee/slippage: `_execute_deltas` produces non-zero `fee` on a `FillEvent` when a delta is
  executed, and the value matches `futures_fees()` + slippage for that trade's size and date.

Run the full existing suite (`tests/portfolio/`, `tests/strategies/test_carry_strategy.py`,
`tests/signal_engine/`, `tests/sfb/test_futures_fees.py` — 41 tests as of this prompt) and confirm
nothing regresses.

---

## 9. DO NOT

- Design the LIVE gross-exposure policy's actual sizing rule (§3).
- Route the margin-feasibility check through `NseMarginEngine`/SPAN or any per-contract
  resolution (§4) — flat-rate only, this phase.
- Claim slippage is "validated" or "measured" from this work (§6) — it is logged, and the
  circularity must be stated in your report, not glossed over.
- Build a facts-refresh scheduler (§7) — flag it, do not solve it.
- Touch `parity_check.py`, `capacity_analysis.py`, or `drawdown_analysis.py` — all three already
  passed independent verification and import `compute_target_book` from the real module; changing
  the module's signature (the `gross_exposure_policy` change in §3) means updating their call
  sites to pass a trivial policy too, but do not change their own simulation logic.
- Hand-edit any script-generated report.

---

## 10. Review checkpoint (Claude)

Independently re-run: the full test suite, `parity_check.py` (must still reproduce +0.0bp both
windows after the `compute_target_book` signature change), `capacity_analysis.py`, and
`drawdown_analysis.py` (all three call sites need updating for the policy-injection signature
change — verify they still reproduce their existing reported numbers with a trivial constant
policy substituted for the old flat `gross_exposure` argument). Findings go to
`docs/reports/CARRY_PAPER_INTEGRATION_REVIEW.md`.
