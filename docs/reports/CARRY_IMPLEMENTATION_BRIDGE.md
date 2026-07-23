# Carry → Implementation Bridge (Design)

**Status:** DRAFT design. **Research is CLOSED** — Carry is a validated alpha across TRAIN /
HOLDOUT / SEALED (`CARRY_SEALED_REPORT.md`), construction frozen and hash-locked
(`CARRY_V2_PRE_REGISTRATION.md`, SHA `74c7311c…`). This document maps the validated signal onto
the production architecture and defines the go-live gate. **It authorizes implementation design
only — not live capital.** No research is reopened here; the signal, sign, construction, and fee
model are settled and immutable.

---

## 0. What is settled vs. what this covers

**Settled (frozen):** the signal (residual cross-sectional carry, **+sign**), the construction
(top-minus-bottom quintile, equal-weight, beta + sector neutralized, ADV-capped at 10% of
20-day ADV, monthly on the roll, 0.25σ no-trade band), the era-accurate futures fee model, and
the validation.

**This document:** how that signal becomes a **deterministic, auditable production strategy**
under the platform's architecture, and the sequenced gate that stands between a validated
backtest and real capital. The load-bearing risk is **not** the signal — it is whether the
*production code path* faithfully reproduces the *research harness* that validated it (§5).

---

## 1. Architectural placement — the four principles

Carry must obey the platform constitution (`CLAUDE.md`): strategies stay dumb, analytics
produce facts, execution owns reality, the runner is neutral, everything is auditable.

| Concern | Layer | Why |
|---|---|---|
| Residual-carry z, neutralized z, **quintile membership**, eligibility | **Analytics (facts)** | Cross-sectional ranking is a pre-computed fact, not runtime logic — "Analytics Produce Facts, runtime read-only." |
| On formation date: emit long/short/exit **intents** per name | **Strategy (dumb)** | Reads facts, emits `SignalEvent` only — no sizing, no margin, no broker. |
| Equal-weight construction, ADV caps, no-trade band, sizing, risk limits, orders | **Execution (owns reality)** | Sizing/risk/broker live exclusively in `core/execution/`; `NseMarginEngine` is the sole sizing authority. **No neutralization here** — it is already in the `z_carry_neut` fact (§2). |
| Drive formation dates + fills, identically in backtest and live | **Runner (neutral)** | `LoopDriver` treats live and backtest data identically — the basis of the §5 parity guarantee. |

The key placement decision: **the quintile ranking is analytics, not strategy.** The strategy
does not rank — it reads which quintile each name is in and emits accordingly. **Neutralization
is also analytics** — the per-name cross-sectional beta+sector OLS is computed once, in the fact
layer, producing `z_carry_neut`. Execution does **weighting, caps, and sizing only, and never
re-neutralizes.** This keeps the strategy dumb and reproduces the validated construction exactly.

---

## 2. Analytics layer — Carry as a fact table

An offline, scheduled batch job computes per `(date, symbol)`: `resid_carry_z`,
`carry_z_neutralized`, `quintile`, `eligible` (F&O-listed, ADV floor, DTE). Written to DuckDB;
runtime is read-only.

**Critical: promote the *frozen research code*, do not reimplement it.** The validated signal
came from `scripts/signal_engine/carry/`. The analytics job must run **that same construction
code**, wrapped as a scheduled producer — a reimplementation is a new, unvalidated construction
and silently breaks the edge. Same code → same facts → same edge.

---

## 3. Strategy layer — the dumb emitter

`core/strategies/carry_strategy.py` (the strategy layer is greenfield today — this is its first
inhabitant):

- On each **monthly formation date**, read the carry fact table and emit:
  `SignalEvent(symbol, direction=LONG)` for top-quintile names, `direction=SHORT` for
  bottom-quintile, and exit events for names leaving the book.
- Between formation dates: emit nothing; positions are held.
- **No sizing, no neutralization, no margin, no broker contact.** The strategy communicates
  *intent and rank only*.

**Contract check (first implementation task):** the existing `core/runtime/` signal-source
contract and `docs/DRIVER_SPECIFICATION.md` are likely shaped for **per-symbol streaming**
signals. Carry is a **cross-sectional, monthly, portfolio-formation** event. Confirm the
`SignalEvent`/SignalSource contract can carry a formation-date batch of intents; if it is
strictly per-bar/per-symbol, design a formation-date batch signal *before* writing the strategy.
This impedance mismatch is the first thing to resolve, not discover.

---

## 4. Execution layer — faithful reproduction of the validated book

`core/execution/`:

- **Portfolio constructor** turns per-name intents into the *validated* book **directly from the
  pre-neutralized `z_carry_neut` fact**: quintile assignment, equal-weight within legs, ADV cap
  (κ = 10% of 20-day ADV), 0.25σ no-trade band. **It does NOT re-neutralize** — the frozen
  research harness does per-name cross-sectional OLS once and builds straight from `z_carry_neut`
  with no book-level re-neutralization. Adding one is a new, unvalidated construction that
  breaks parity (§5) and the no-re-optimization guardrail (§8). Gross/leverage is a parity-neutral
  scaling set by the risk layer. The constructor must reproduce the research book **exactly**.
- **Sizing:** `NseMarginEngine` (`core/risk/nse_margin_engine.py`) is the **sole sizing
  authority** in paper and live alike — margin-aware, deterministic. The broker RMS is
  order-acceptance only, never consulted for sizing (ADR-011/012/013).
- **Risk:** position-stacking guard (block new entry while a position is open on the same
  symbol), gross/net exposure limits, per-name caps.
- **Broker:** `PaperBroker` first, then Upstox LIVE — same execution code, broker swapped.
- **Position tracker must update on fills** (`FillEvent → position_tracker.update_from_fill()`).
  This is a documented pitfall: without it, equity = cash only, drawdown is wrong, and TP/SL/
  time stops never fire.

### 4.1 Rebalance execution path (resolved) — book-level batch, not per-symbol streaming

A monthly portfolio rebalance is **inherently atomic and book-level**: the 0.25σ no-trade band
is a *scale* of existing positions (not exit-reentry), the margin budget is *shared across all
names*, and gross/neutrality normalization is a *whole-book* constraint. The per-symbol
`process_signal` path (one symbol at a time) plus its stacking guard (`handler.py:634`) is the
**wrong contract** for this.

**Decision: Carry rebalances through a formation-date, book-level batch operation in the
execution layer, invoked by the runner on formation dates — NOT through `process_signal`.** The
per-symbol handler and its stacking guard are **left untouched** (they still serve per-name
streaming strategies; Carry simply does not route through them).

Why not the alternatives:
- **Per-symbol streaming (constructor → `process_signal`)** requires *bypassing* the stacking
  guard **and** redesigning the margin-budget gate (`handler.py:1140`) — more handler surgery,
  it weakens the guard for the strategies that legitimately need it, and it still cannot
  naturally allocate a *shared* margin budget one symbol at a time. "Faithful to the per-bar
  contract" is a false virtue: the per-bar contract is the wrong shape for a monthly book.
- **Full exit-then-reentry** ignores the 0.25σ band and churns the whole book monthly →
  turnover roughly doubles vs. the research (1.44/yr) → net spread drops → **fails the parity
  gate (§5)**. Disqualified on parity alone.

**This is the MOST parity-faithful option, not a departure.** The research harness (`run_sealed.py`)
*is* a book-level monthly diff with a no-trade band; the batch path mirrors that computation, so
it is the likeliest to reproduce the research net spread. And it does **not** violate "Runner is
Neutral" — neutrality means live == backtest, which the batch path preserves by running
identical code in both modes. What is given up is only "reuse `process_signal` / zero handler
diffs," a lesser convention, in exchange for the correct home for a portfolio rebalance under
"Execution Owns Reality."

The batch operation (all in `core/execution/`, deterministic): read target book from the Carry
facts → read current holdings → per name compute target − held, suppress if `|Δ| < 0.25σ`
(no-trade band) → size the surviving deltas to the **shared** margin budget via `NseMarginEngine`
→ emit delta orders (scale / open / close) → `position_tracker` updates on fills. The **strategy
stays dumb** (emits target intents from facts); **execution owns the rebalance.**

---

## 5. The PARITY GATE — the single most important implementation risk

**Status: PASSED, 2026-07-23** (`docs/reports/CARRY_PARITY_REPORT.md`,
`scripts/signal_engine/carry/parity_check.py`, code commit `da3e3ba`). TRAIN and HOLDOUT both
reproduce the research net spread at **+0.0 bp delta**, independently re-verified against
`core/execution/portfolio/carry_rebalancer.py` — the actual production module, not a
parity-script copy of it. See §5.3 for how three real bugs were found and fixed to get there;
read it before trusting any future green run of this gate at face value.

**The validated numbers came from the standalone research harness (`run_sealed.py`), not from
the production `LoopDriver` + strategy + `NseMarginEngine` + `PaperBroker` path.** These are
different code. Before anything else:

> Run the **production path** through `LoopDriver` in **backtest mode** over TRAIN + HOLDOUT +
> SEALED, and confirm it **reproduces the research harness's net quintile spread** within a
> tight, pre-stated tolerance (same sign, magnitude within a few percent per window).

If the production path does not reproduce the research edge, the implementation is **unfaithful
and the edge is not real in production** — no amount of downstream work fixes that. This is a
**hard gate**: pass it before capacity, drawdown, or paper trading. It is also the direct
expression of "Runner is Neutral / deterministic reproducibility" — same code, backtest and
live, byte-identical logic.

### 5.1 Canonical fee model (resolved) — one implementation, era-accurate tiered STT

Three fee conventions existed in the pipeline: `run_sealed.py`'s inline **tiered** STT
(0.0100 → 0.0125 → 0.0200, which produced the validated SEALED +20.52%), `run_net_spread.py`'s
flat **0.0100%** (TRAIN/HOLDOUT), and `futures_fees.py`'s **0.0125% pre-2024-10**. These are not
three legitimate choices — the **tiered schedule is canonical**: it is what `CARRY_PHASE0_PRE_REGISTRATION.md`
§8 pre-registered and what produced every validated number.

Key fact: the flat 0.0100% and the tiered model are **identical over TRAIN/HOLDOUT**
(both windows precede the 2023-04 STT change, where the tiered rate *is* 0.0100%), so the
+13%/+7% nets already sit on the canonical model. The only real divergence is
`futures_fees.py`, which is simply **wrong** — it omits the pre-2023-04 0.0100% tier and
overcharges that era (and the Jan–Mar 2023 slice inside SEALED).

**Resolution (single source of truth):**
1. **Correct `core/execution/futures/futures_fees.py`** to the full three-tier schedule
   (0.0100% ≤ 2023-03-31 · 0.0125% 2023-04-01 → 2024-09-30 · 0.0200% ≥ 2024-10-01, sell-side).
   This becomes the one fee model for research **and** production. Retire the inline model in the
   **live, re-runnable** research script (`run_net_spread.py` → calls the module). **Do NOT
   refactor `run_sealed.py`** — see the note below.
2. **Preserve SEALED by proven equivalence, NOT by re-read.** Unit-test the corrected
   `futures_fees.py` against `run_sealed.py`'s inline tiered model on shared inputs → the test
   must show **identity** (byte-identical per-contract fees), not a documented divergence. If
   identical, the SEALED +20.52% transfers **by construction** — the one-shot SEALED window is
   **not** re-read (SEALED protocol §2 holds).

   **`run_sealed.py` stays frozen and inline — it is not refactored.** It is a spent one-shot
   artifact that will never execute again; its remaining value is *provenance* (byte-for-byte the
   code that produced +20.52%). Its inline model is therefore the **permanent regression anchor**
   the equivalence test pins the canonical module against — refactoring it to call the module
   makes that test circular and destroys the anchor. Any re-run guard belongs **outside** the
   file (an invocation-layer / CI check refusing to regenerate `CARRY_SEALED_SNAPSHOT.json` if it
   exists), never as an edit to the frozen artifact.
3. **Re-derive TRAIN/HOLDOUT** on the corrected module (free, no sealed data) → must reproduce
   +13%/+7% (STT is identical in that era).
4. **Parity tolerance (§5) must NOT absorb any fee discrepancy.** The fee code is *shared and
   identical*, not reconciled by tolerance. Tolerance is reserved for genuine execution-path
   differences (float ordering, fill timing). Using it to mask a fee-model gap would pollute the
   gate that exists to catch real divergence.

### 5.2 The parity gate and the SEALED one-shot rule

The parity gate must **not** become a backdoor re-run of the SEALED window — the same discipline
that governed the fee decision (§5.1) governs here.

- **Establish parity on TRAIN + HOLDOUT**, where re-running the production path is unrestricted
  and free. That is where divergences are found and fixed.
- **SEALED parity is guaranteed *by construction*.** If the production path reproduces research
  on TRAIN + HOLDOUT (identical construction, rebalance logic, and — per §5.1 — an identical fee
  module), then it necessarily reproduces the recorded SEALED series. No fresh SEALED read is
  required to know this.
- **If a production run over SEALED is performed at all**, it is a **verification against the
  frozen `CARRY_SEALED_SNAPSHOT.json`** (an already-recorded result), makes **no new inferential
  use** of the window, and changes no construction/fee/sign. It is therefore not a "read" in the
  sense of the one-shot rule (SEALED protocol §2) — but it must be logged and framed explicitly
  as such, never as a new evaluation.

**Isolate construction from margin-sizing in the harness.** The research book used a fixed gross
(≈ ₹50 lakh/leg); production sizes via `NseMarginEngine`. Pin the *parity* harness to the
research-identical gross + injected 5 bp/side slippage, so any residual gap is **pure
construction divergence**, not a margin-model difference. Real margin sizing is validated later
in **PAPER** (§6.4), not conflated into the parity gate.

**De-risk the biggest new surface first.** Before building the daily-bar provider + full
LoopDriver replay (the largest net-new plumbing), run a cheap, deterministic **rebalancer-only
construction-parity sub-check**: feed the rebalancer the research facts and confirm it produces
the research book's target weights and deltas. If construction parity fails there, it is fixed
before any provider work.

### 5.3 How the gate actually closed — three bugs, and the pattern behind them

The first "GATE D PASS" was not real. It was caught only by re-running the gate script fresh
instead of trusting its printed report — the same lesson this track has re-learned every round
(see `CLAUDE.md`'s "recurring lesson" note under the Carry section). Recording the sequence here
because the failure mode is the load-bearing part, not the individual bugs:

1. **`parity_check.py`'s own verdict logic ignored the parity check it displayed.** `all_pass`
   was wired only to `production net > 0`; the `within_tol` delta check was computed and printed
   in the table but never fed into the gate. The script could print a `**FAIL**` row and
   `GATE D VERDICT: PASS` on the same page. Separately, the report artifact at the time also
   contained a hand-written `PASS*` verdict and footnote blaming "the signals DB was partially
   overwritten" — text the script does not generate. Re-running research fresh against the
   already-current `signals.duckdb` reproduced the same delta, refuting that explanation. Fixed
   by wiring `gate_pass = net_pass and parity_pass` into the exit code and printed verdict.
2. **Quintile membership was computed on two different populations.** Research
   (`run_net_spread.py`) ranks by `z_carry_neut` *after* filtering to ADV-eligible names.
   Production pre-assigned a fixed quintile label ranked over *all* liquid names (ADV
   availability ignored), then merely dropped ADV-ineligible names from that fixed label with no
   re-rank or backfill. Whenever ADV data wasn't available for every liquid name on a formation
   date, the two paths picked different names. Fixed by rewriting `compute_target_book` in
   `core/execution/portfolio/carry_rebalancer.py` to re-rank by `z_carry_neut` within the
   caller-supplied (pre-filtered) fact list — the caller is now responsible for ADV/eligibility
   filtering before calling it.
3. **NULL forward returns leaked into the production portfolio.** A `LEFT JOIN` pulled in facts
   with no `fwd_ret_1m`, diluting returns; research excludes them via `WHERE fwd_ret_1m IS NOT
   NULL`. Fixed by matching the filter.

The fix for bug 2 was first applied only inside `parity_check.py`'s own local copy of the
construction logic (`_compute_target_book_production`) — which made the gate pass while leaving
the real production module, `core/execution/portfolio/carry_rebalancer.py`, on the old buggy
logic. **A parity gate that verifies a duplicate of the production code proves nothing about the
production code.** This was caught and fixed: the local copy was deleted, and `parity_check.py`
now imports `compute_target_book` directly from `core.execution.portfolio.carry_rebalancer`, so
the gate can no longer drift from what will actually execute. Verified independently: 41 tests
pass, fresh re-run gives +0.0 bp on both windows against the real module.

**ADV-wiring gap: fixed, 2026-07-23.** `_load_adva` is now an instance method reading
`self._bhavcopy_db` instead of a static method that ignored the constructor argument and
hardcoded its own path — the argument now actually controls which DB gets read. Re-verified:
parity still holds at +0.0 bp both windows after the change, 41 tests pass. One smaller piece is
unchanged and not urgent: `bhavcopy_db_path` still defaults to `None`, and `_execute` still
silently skips ADV loading with no warning when it's unset. Add a log warning before wiring this
into a real driver so a missing path is loud, not silent — small, not blocking.

---

## 6. Go-live gate (sequenced — no step skipped before real capital)

1. **Parity gate (§5).** Production path reproduces the research net spread. *Hard gate.* **PASSED.**
2. **Capacity analysis.** Max AUM before the ADV caps bind and the edge compresses — set by the
   thin-name tail of the ~120-name book. Output: a capital ceiling. **DONE, 2026-07-23**
   (`docs/reports/CARRY_CAPACITY_REPORT.md`, `scripts/signal_engine/carry/capacity_analysis.py`,
   independently re-run and reproduced). **Finding: the ADV cap is not the binding constraint** —
   at Rs 100 Cr gross (the top of the tested range), only 2.9% of TRAIN names / 0.3% of HOLDOUT
   names are capped; the formula never actually bound within the tested range. The real
   constraint is expected to be execution impact/slippage on the thin-name tail (p5 ADV Rs 23.7 Cr
   TRAIN / Rs 32.9 Cr HOLDOUT), which this analysis does not measure — that's step 4 (PAPER).
   Caveat: cap incidence here is measured pre-renormalization, so it doesn't capture second-order
   cascading (redistributed capital pushing another name over its own cap); a small effect at
   these incidence rates, but the true ceiling is a little more conservative than the headline
   number, not less.
3. **Drawdown / regime profile.** Worst month, max DD, and how concentrated the SEALED **+20.5%**
   is — it is likely regime-flattered (carry-favorable 2023–26), so size on the conservative
   HOLDOUT-class net, not 20.5%. Optionally evaluate the **Trend −0.246 overlay** for
   drawdown reduction here (a risk study on TRAIN/HOLDOUT — consumes no sealed data).
   **DONE, 2026-07-23** (`docs/reports/CARRY_DRAWDOWN_REPORT.md`,
   `scripts/signal_engine/carry/drawdown_analysis.py`, reuses the fixed production simulation
   from `parity_check.py`; independently re-run and reproduced exactly). **Conservative numbers
   for sizing: net +6.96%/yr, worst month −4.59%, max DD −6.44%, Sharpe 0.86.** Drawdowns are
   mild in absolute terms, but HOLDOUT's risk stats rest on only 23 monthly observations and its
   returns are concentrated (top 3 months = 87% of total return, top 5 = 129%) — the same
   small-sample fragility this track has run into before (PSB-1/PSB-2/RFA), not a new problem,
   but a reason to size conservatively rather than read Sharpe 0.86 as a stable estimate. Trend
   overlay evaluation was scoped but not run — still open if drawdown reduction is wanted before
   PAPER.
4. **PAPER mode.** Run live-paper via `scripts/fno_runner.py` (PAPER) for a defined period;
   validate realized slippage against the 5 bp/side assumption (slippage dominated costs — it
   is the production lever) and confirm fills + position tracking behave.
5. **LIVE.** Only after 1–4, at small size, with **IC-decay monitoring** — a validated signal is
   not a permanent one; carry edges crowd out.

---

## 7. Audit & determinism (non-negotiable)

- **Audit-first:** every order traceable to the exact carry fact `(date, symbol, z, quintile)`
  that produced it.
- **Deterministic:** same inputs → byte-identical orders, in backtest and live. This is the
  guarantee the parity gate (§5) verifies and the reason no construction parameter may drift.

---

## 8. Guardrails (explicit non-goals)

- **No re-optimization of the construction for live.** It would break both the validated edge
  and the determinism guarantee. The frozen construction is the product.
- **No broker-RMS-driven sizing.** `NseMarginEngine` is the sole authority.
- **Size on the conservative net, not the regime-flattered SEALED +20.5%.**
- **No reopening research / adding sleeves to "improve" before this is live.** The job is now
  implementation and risk, not discovery.

---

## 9. Key files

| File | Purpose | Status |
|---|---|---|
| `scripts/signal_engine/carry/publish_facts.py` | Promote frozen construction → scheduled analytics fact table | Built |
| `core/strategies/carry_strategy.py` | Dumb formation-date `SignalEvent` emitter | Built |
| `core/execution/portfolio/carry_rebalancer.py` | Book-level `compute_target_book` + `compute_deltas` + `rebalance_book` + `CarryRebalancerHook` (the constructor named in §4 as `carry_constructor.py` was built here instead) | Built |
| `core/database/providers/daily_bhavcopy.py` | Daily-bar bhavcopy provider for REPLAY | Built |
| `scripts/signal_engine/carry/parity_check.py` | §5 production-vs-research parity harness — imports `compute_target_book` from the production module directly | Built, GATE D PASS |
| `tests/strategies/test_carry_strategy.py`, `tests/portfolio/test_carry_rebalancer.py` | Strategy + rebalancer unit tests (4 + 16) | Built, passing |
| `docs/reports/CARRY_PARITY_REPORT.md` | Script-generated parity result (the §5 gate) | Current: +0.0bp TRAIN/HOLDOUT |

---

## 10. Next step

**§6 steps 1–3 are all closed and independently verified.** Fact promotion, the dumb strategy,
the parity gate, the ADV-wiring fix, capacity analysis, and the drawdown/regime profile are all
built, tested, and re-run from scratch to confirm every reported number reproduces exactly. The
next work phase is **go-live gate step 4: PAPER mode** — run `scripts/fno_runner.py` in PAPER for
a defined period, validate realized slippage against the 5 bp/side assumption baked into every
report above (slippage is the dominant, least-tested cost — capacity analysis found the ADV cap
formula doesn't bind, which pushes the real capacity question onto slippage), and confirm fills
and position tracking behave. Size the PAPER run off the conservative numbers in §6 step 3
(+6.96%/yr, −6.44% max DD), not SEALED.

This is the first step that touches live infrastructure, so close these two before it, not
during: (1) the deferred ADV-wiring log-warning (§5.3 — silent default when `bhavcopy_db_path` is
unset on `CarryRebalancerHook`), and (2) no instantiation site for `CarryRebalancerHook` exists
anywhere in the repo yet — wiring it into `LoopDriver`'s `rebalance_hook` for a real PAPER run is
itself new integration work, not just a config flip, and should get the same "verify independent
of the report" treatment the last three deliverables got.

**PAPER integration prompt written and issued to DeepSeek, 2026-07-23:**
`docs/reports/CARRY_PAPER_INTEGRATION_PROMPT.md`. Covers the `build_runner()`
`rebalance_hook_factory` wiring, the ADV-warning fix, a gross-exposure **policy-injection** seam
(PAPER uses a trivial fixed-Rs-1-Cr policy; LIVE's policy is explicitly left unimplemented —
sizing off real PnL/drawdown is new behavior outside the frozen construction and is its own
future decision, not something to invent here), an always-on flat-rate margin-feasibility check
(not routed through SPAN — that needs contract-level resolution out of scope for this phase), and
an explicit correction that PAPER fee/slippage logging is bookkeeping, not the realized-slippage
validation §6.4 actually calls for (that needs real broker fills and belongs to LIVE). Also flags,
without solving, an open gap: nothing currently refreshes `facts.duckdb` with new formation dates
as time moves forward — `CarryRebalancerHook` will silently stop firing once it passes the last
formation date `publish_facts.py` was run against.
