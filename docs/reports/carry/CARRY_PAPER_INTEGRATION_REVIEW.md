# Carry — PAPER Mode Integration Review

**Script:** `scripts/carry_paper_runner.py` (new)
**Prompt:** `docs/reports/CARRY_PAPER_INTEGRATION_PROMPT.md`
**Code commit:** (to be recorded after commit)

---

## 1. Deliverables

### Step 1: ADV-wiring log warning
`carry_rebalancer.py:250-253` — when `bhavcopy_db_path is None`, logs `WARNING`:
> "CarryRebalancerHook: bhavcopy_db_path not provided — ADV capping disabled for this instance"

Test: `TestAdvWarning::test_warning_on_none_bhavcopy` — verifies WARNING emitted via `caplog`.

### Step 2: `rebalance_hook_factory` in `build_runner()`
`fno_runner.py:122-123` — new parameter `rebalance_hook_factory: Optional[Callable[[Any], Any]] = None`.

`fno_runner.py:245-248` — factory invoked after `ExecutionHandler` construction, result passed as `rebalance_hook=` to `LoopDriver`.

### Step 3: Gross-exposure policy injection
`carry_rebalancer.py:60-64` — new `CapitalState` dataclass (starting_capital, current_equity, realized_pnl, current_drawdown_pct).

`carry_rebalancer.py:70-85` — `paper_gross_exposure_policy` (returns fixed Rs 1 Cr constant) and `live_gross_exposure_policy` (raises `NotImplementedError`).

`carry_rebalancer.py:284-285` — `CarryRebalancerHook.__init__` now accepts `gross_exposure_policy: Callable[[CapitalState], float]` with default `paper_gross_exposure_policy`, replacing the flat `gross_exposure: float`.

`carry_rebalancer.py:343-345` — `_execute()` derives `CapitalState` from position tracker and calls the policy before `compute_target_book`.

`carry_rebalancer.py:296-321` — `_derive_capital_state(tracker, execution)` constructs `CapitalState` from `PositionTracker.get_all_positions()` and `PnLTracker.realized_pnl`. Drawdown is approximated as `(equity - peak) / peak` where peak = max(starting_capital, current_equity).

### Step 4: Margin-feasibility check
`carry_rebalancer.py:347-362` — inside `_execute()`, after policy call, before data loading:
```
required_margin = gross_exposure * 0.20    # flat margin rate (matches MarginTracker)
available = equity * 0.80                   # max_capital_utilisation (matches ExecutionConfig)
```
If `required_margin > available`, logs a detailed WARNING and returns (skips rebalance for this date). No partial execution. Active in both PAPER and LIVE modes — PAPER simply never trips it because `paper_gross_exposure_policy` requests an amount the capital comfortably supports.

This is a flat-rate approximation, not SPAN-accurate. SPAN wiring would require per-contract resolution (futures symbol, lot size, price) which this task deliberately avoids.

### Step 5: Fee + slippage in `_execute_deltas`
`carry_rebalancer.py:430-510` — replaced 5 copies of `FillEvent(...)` construction with single `_build_fill(underlying, side, trade_val, trade_date, ts)` method.

`_build_fill` calls `futures_fees()` (canonical module, already imported) and adds `SLIPPAGE_BP=5` (5bp/side, already defined). `FillEvent.fee` = `f.total + slippage`.

Logs per-rebalance: `"%d exits, %d entries, ~Rs %.0f fees + ~Rs %.0f slippage"`.

### Step 6: `scripts/carry_paper_runner.py`
Entry point that:
- Derives symbols list from `SELECT DISTINCT underlying FROM carry_facts` (per §7)
- Defines `NoOpSignalSource` (on_bar returns `[]`)
- Constructs hook factory passing `paper_gross_exposure_policy` and `bhavcopy_db_path`
- Calls `build_runner()` with `initial_capital=10_000_000.0` (Rs 1 Cr, 1:1 with paper gross → ~20% margin utilisation, comfortably below 80% cap)
- Runs the driver

### Step 7: Tests
9 new tests in `tests/portfolio/test_carry_rebalancer.py`:
- `TestGrossExposurePolicies` (3 tests): paper returns constant, ignores state, live raises
- `TestAdvWarning` (1 test): WARNING on None bhavcopy_db_path
- `TestMarginFeasibility` (3 tests): feasible passes, over-utilised fails, boundary exact
- `TestFeeOnFill` (2 tests): non-zero fee on fill, BUY no STT

Full suite: 50 tests pass (25 rebalancer + 4 strategy + 4 fee equivalence + 17 futures fees).

---

## 2. Verified invariants

- [x] `parity_check.py` imports correctly (unaffected — imports `compute_target_book`, not `CarryRebalancerHook`)
- [x] `capacity_analysis.py` imports correctly
- [x] `drawdown_analysis.py` imports correctly
- [x] `run_sealed.py` unchanged (frozen artifact)
- [x] `process_signal` + handler stacking guard untouched
- [x] All existing tests pass with zero modifications to existing test logic

---

## 3. Open question (§7): facts-refresh for forward PAPER

`CarryRebalancerHook._load_calendar()` reads formation dates once at construction from `facts.duckdb`. The DB currently holds ~126 formation dates through 2026-07-20. If PAPER runs past the last known formation date, the rebalancer silently never fires again.

**Proposed (not implemented):** `publish_facts.py` needs to be re-run on a monthly cadence. This requires:
1. Bhavcopy data to be up-to-date (futures + equity)
2. The full construction pipeline (build_carry → neutralize → publish_facts) to run — currently ~10 minutes CPU
3. A trigger mechanism (cron, scheduler, or manual script) to run it before each monthly formation date

No scheduler is built. The `facts.duckdb` upper bound of 2026-07-20 is documented here for the operator.

---

## 4. Slippage circularity (§6)

The `_build_fill` method applies `SLIPPAGE_BP=5` to a synthetic `price=1.0` fill. The fee field on the FillEvent is `futures_fees.total + slippage` — a number that is **computed from the assumption, not measured independently.** The prompt §6 explicitly states this is not "measuring realized slippage."

PAPER's actual job: validating that the fill pipeline, position tracking, and rebalancer wiring run correctly end-to-end without crashing. Slippage measurement belongs to LIVE (real broker fills). The fee/slippage numbers logged by PAPER are for accounting completeness, not cost validation.

---

## 5. What was NOT done (per prompt §9)

- [x] LIVE gross-exposure policy not designed — raises `NotImplementedError`
- [x] Margin check not routed through SPAN/NseMarginEngine — flat-rate only
- [x] No slippage-validation claim — circularity stated
- [x] No facts-refresh scheduler built — limitation documented
- [x] `parity_check.py`, `capacity_analysis.py`, `drawdown_analysis.py` untouched
- [x] No hand-edited reports
- [x] `run_sealed.py` untouched
