# MM9.2-S4 — `_update_equity_metrics` Wiring — Implementation Specification

**Slice**: MM9.2-S4  
**Status**: Pending implementation  
**Prerequisite**: MM9.2-S1, S2, S3 COMPLETE  
**Defects resolved**: I.H.1 (static `cash_balance`), I.M.2 partial  
**Test baseline**: 668 passing  
**Commit message**: `MM9.2-S4 — wire _update_equity_metrics to fill path; cash_balance tracks realized PnL`

---

## 1. Repository Impact Review

### 1.1 Files Modified

| File | Change |
|------|--------|
| `core/execution/handler.py` | Add `self._update_equity_metrics(trade)` inside `_handle_broker_fill`'s `if order_state:` block, after `TradeEvent` construction |
| `tests/` (potentially) | Any test that sends simulated fills and then asserts `cash_balance == initial_capital` will break and must be updated |

### 1.2 Files Unchanged

`ExecutionConfig`, `ExecutionMetrics`, the `_update_equity_metrics` method body, the drawdown gate formula at `process_signal:590`, `MarginTracker`, all event types, all other handler logic.

### 1.3 Test Churn Forecast

S4 turns dead code live. Every fill processed in every mode (live, paper, backtest) now moves `cash_balance`. Unlike MM9.2-S3-S3 where `float('inf')` guaranteed zero behavior change, S4 is always-on.

Two existing assertions were found that check `cash_balance`:

- `tests/scripts/test_fno_runner_composition.py:81` — `assert d._execution.metrics.cash_balance == 500_000.0`
- `tests/scripts/test_fno_runner_composition.py:87` — `assert d._execution.metrics.cash_balance == 100_000.0`

Both fire at construction time before any fills are processed. These remain correct after S4 — `_update_equity_metrics` is never called until a fill arrives, so the construction-time invariant holds.

Pre-implementation action: run `grep -rn "cash_balance" tests/ --include="*.py"` to enumerate all remaining assertions touching `cash_balance`. Any that assert `== initial_capital` after fills have been issued must be updated.

### 1.4 Call Graph (Post-S4)

```
_handle_broker_fill(fill)
  ├─ order_tracker.get_order(order_id)              [existing]
  ├─ order_tracker.process_fill(fill)               [existing]
  ├─ position_tracker.update_from_fill(fill)        [existing — sets post-fill net_qty]
  ├─ [G1 Wave 4B canonicalization]                  [existing]
  ├─ pnl_tracker.update(fill, realized_pnl)         [existing]
  ├─ group_tracker.update_from_order_status(...)    [existing]
  ├─ group_pnl_tracker.update(fill, realized_pnl)  [existing]
  └─ if order_state:
       trade = TradeEvent(...)                       [existing]
       self._update_equity_metrics(trade)           [← S4 ADDS THIS]
       [MAE/MFE computation]                        [existing]
       trading_writer.save_trade / update_exit      [existing]
```

---

## 2. Behavioural Contract

### 2.1 Pre-condition

`_update_equity_metrics(trade)` is called after `position_tracker.update_from_fill(fill)`. This ensures `position_tracker.net_quantity(trade.symbol)` reflects the post-fill state when `_update_equity_metrics` reads it for the `total_equity` computation.

### 2.2 Cash Balance Update — BUY Fill

Given a BUY fill for `qty` units at `price` with `fees`:

```
metrics.cash_balance -= (qty * price + fees)
```

`cash_balance` decreases by gross purchase cost plus fees.

### 2.3 Cash Balance Update — SELL Fill

Given a SELL fill for `qty` units at `price` with `fees`:

```
metrics.cash_balance += (qty * price - fees)
```

`cash_balance` increases by net sale proceeds after fees.

### 2.4 Direction String Contract

`trade.direction` is a plain `str` (type annotation at `core/events.py:91`), populated from `fill.side` which is also `str` (annotation at `core/execution/order_lifecycle.py:31`, coerced via `str(side)` at line 70). The comparison `if trade.direction == "BUY"` in `_update_equity_metrics` is a string-to-string equality check. No enum wrapping occurs. This was verified against the `FillEvent` and `TradeEvent` definitions before this spec was written.

### 2.5 Drawdown Update on Fill

After adjusting `cash_balance`, `_update_equity_metrics` computes:

```
total_equity = metrics.cash_balance + position_tracker.net_quantity(trade.symbol) * trade.price
```

This value is passed to `metrics.update_drawdown(total_equity)`, advancing the drawdown high-water mark if `total_equity` exceeds the prior maximum.

Note: `total_equity` here reflects only the fill symbol's unrealized PnL, using the fill price. This is the existing `_update_equity_metrics` formula and is NOT changed by S4.

### 2.6 Partial Fix for I.M.2

The drawdown gate at `process_signal:590` computes:

```python
total_equity = self.metrics.cash_balance + \
    (self.position_tracker.net_quantity(signal.symbol) * current_price)
```

After S4, `metrics.cash_balance` carries realized PnL from all prior fills rather than being permanently anchored to `initial_capital`. The gate's equity estimate therefore improves for any session with fills. The single-symbol unrealized PnL component of the gate's formula is NOT changed by S4 — this remains I.M.2. Full resolution of I.M.2 (portfolio-wide unrealized PnL in the gate) is deferred to MM9.3.

### 2.7 Fills With No order_state (Boundary)

If `order_state` is None (orphan fill — arrived for an unknown order ID), the `if order_state:` block is skipped entirely. `_update_equity_metrics` is NOT called. `cash_balance` is not updated for orphan fills. This is the accepted boundary: orphan fills are reconciliation events and are not modeled in the runtime cash ledger.

### 2.8 Exception Safety

`_update_equity_metrics` executes inside the existing `try/except Exception` in `_handle_broker_fill` (lines 376–447). If it raises (e.g., an unexpected exception in `position_tracker.net_quantity`), the exception is caught by the existing handler and logged at ERROR level. `cash_balance` will be in an inconsistent state for that fill. No change to the error-handling policy is introduced by S4.

### 2.9 Idempotency Warning

`_update_equity_metrics` is NOT idempotent. Calling it twice for the same fill would doubly adjust `cash_balance`. S4 must add exactly one call site and must not be placed where it can be executed more than once per fill.

### 2.10 Double Drawdown Sampling

After S4, `metrics.update_drawdown` is called from two locations:

1. Inside `_update_equity_metrics` at fill time (fill price, fill symbol's post-fill net qty)
2. Inside the drawdown gate in `process_signal` at signal time (current price, signal symbol's current qty)

More frequent sampling increases accuracy of the HWM. The two samples use different price snapshots and are expected to differ — this is correct behavior, not a bug.

### 2.11 Session Causality (PAPER / DRY_RUN)

In PaperBroker mode, `_handle_broker_fill` is called synchronously from within `process_signal` (line 817). The causal order is:

1. Drawdown gate at line 590 evaluates using `cash_balance` through fill N-1
2. `broker.place_order()` invokes `_handle_broker_fill`, which calls `_update_equity_metrics` for fill N
3. `process_signal` returns

Signal N's drawdown gate never sees the effect of fill N on `cash_balance`. It evaluates risk before the fill, not after. This is correct causal behavior and requires no mitigation.

### 2.12 Fees Field Consistency

`trade.fees` is populated from `fill.fee` (handler.py line 419: `fees=fill.fee`). For the BUY path, `_update_equity_metrics` uses `cost = trade.quantity * trade.price + trade.fees`, crediting the fee to the cash outflow. For the SELL path, the formula is `trade.quantity * trade.price - trade.fees`, deducting fees from proceeds. Both match the real-world cash impact of each leg.

### 2.13 Short/SELL Cash Semantics

For short option positions (SELL to open), the SELL branch credits the full premium minus fees to `cash_balance`, as if receiving cash. Real margin mechanics are deferred to MM9.4 (SPAN margin). This is the accepted flat-rate approximation under the platform's D1 constitution and is not in S4 scope.

### 2.14 Scope Boundary

S4 does NOT:

- Change the body of `_update_equity_metrics`
- Change the drawdown gate's equity formula at `process_signal:590`
- Touch `MarginTracker` or its `get_used_margin` signature
- Add new `ExecutionConfig` fields
- Change event types or logging behavior

S4 is exactly: add `self._update_equity_metrics(trade)` at one insertion point.

---

## 3. Runtime Ordering

### 3.1 Insertion Point

Inside `_handle_broker_fill`, within the `if order_state:` block, after the `TradeEvent` is constructed and before the MAE/MFE computation and `trading_writer` calls.

### 3.2 Why After `position_tracker.update_from_fill`

`_update_equity_metrics` reads `self.position_tracker.net_quantity(trade.symbol)` to compute `total_equity`. Placement before `update_from_fill` would produce the pre-fill net qty, giving an incorrect `total_equity` for the drawdown HWM sample. Placement after (step 8 in the call graph, after step 3) is mandatory.

### 3.3 Why After `trade = TradeEvent`

`_update_equity_metrics` accepts a `TradeEvent`, not a `FillEvent`. The `TradeEvent` object is only constructed inside `if order_state:`. There is no alternative construction point, and changing the method signature to accept `FillEvent` is out of scope.

### 3.4 Why Before `trading_writer` Calls

`trading_writer` is the persistence step. `_update_equity_metrics` is a state-mutation step. Convention in this file is: mutate state, then persist. This ordering is consistent with the existing pattern (`position_tracker.update_from_fill` precedes `pnl_tracker.update`, which precedes `trading_writer`).

---

## 4. Architecture Rationale

### 4.1 Why the Call Was Missing

`_update_equity_metrics` was written but never wired — a classic dead-method defect. The method's signature, logic, and placement in the class are all correct. The sole missing piece is the call site.

### 4.2 Why Not Change `_update_equity_metrics` to Accept `FillEvent`

The method's `TradeEvent` signature makes it usable at any point where a trade record exists. Changing it to `FillEvent` would:

- Require rebuilding equivalent fields manually from `fill` attributes
- Diverge from the `if order_state:` block pattern used throughout `_handle_broker_fill`
- Reduce the method's ability to be called from other future contexts (e.g., trade replay)

The existing signature is left unchanged.

### 4.3 Why Not Fix the Drawdown Gate Formula in This Slice

The gate's formula uses only `signal.symbol`'s unrealized PnL. The full fix — iterating all held positions using `_price_cache` — belongs in MM9.3 where `PortfolioView.mtm_equity` is introduced and wired. Including it in S4 would:

1. Duplicate work planned for MM9.3-S2 (`PortfolioView` runtime integration)
2. Change the behavior of a kill-switch trigger, which is the highest-blast-radius edit in the execution engine
3. Violate the minimum-diff principle for a "wire one call" slice

### 4.4 Single Source of Truth for Cash

After S4, `metrics.cash_balance` becomes the authoritative realized-PnL-adjusted cash balance. All consumers (margin gate at line 1090, drawdown gate at line 590) automatically see accurate values without requiring changes to those call sites. State is maintained at the mutation point; callers are read-only.

---

## 5. Failure Matrix

| ID | Scenario | Expected Behaviour |
|----|----------|--------------------|
| F1 | BUY fill arrives, `order_state` present | `cash_balance -= qty * price + fees`; `update_drawdown` called with post-fill equity |
| F2 | SELL fill arrives, `order_state` present | `cash_balance += qty * price - fees`; `update_drawdown` called with post-fill equity |
| F3 | Fill arrives, `order_state` is None | `_update_equity_metrics` NOT called; `cash_balance` unchanged |
| F4 | `_update_equity_metrics` raises | Caught by existing `try/except`; ERROR logged; fill trackers already mutated; `cash_balance` in partial-update state; no exception propagation |
| F5 | Round-trip BUY then SELL, same symbol, same price, zero fees | `cash_balance` returns to `initial_capital` |
| F6 | Round-trip BUY then SELL with fees | `cash_balance < initial_capital` by sum of fees paid both legs |
| F7 | Multiple fills across different symbols | Each fill independently adjusts `cash_balance`; running total is cumulative realized PnL |
| F8 | BUY fill drives `cash_balance < 0` | `cash_balance` goes negative; margin gate (line 1090) short-circuits on `cash_balance <= 0` and blocks next signal with utilisation=0.0 |
| F9 | `_update_equity_metrics` called twice for same trade (implementation error) | `cash_balance` doubly adjusted — this must not happen; one insertion point only |
| F10 | PAPER mode: signal N's drawdown gate runs before fill N updates `cash_balance` | Gate reads `cash_balance` through fill N-1; fill N updates it in the synchronous `_handle_broker_fill` call; correct causal order |
| F11 | LIVE mode: fill arrives asynchronously from WebSocket | Platform single-threaded invariant means no race condition; `_update_equity_metrics` executes on the callback path |
| F12 | Session started with `initial_capital=500_000`, no fills issued | `cash_balance == 500_000` unchanged; construction-time assertions remain correct |
| F13 | Backtest with idempotency guard disabled | Each fill flows through `_handle_broker_fill`; `cash_balance` tracks cumulatively across all fills |
| F14 | `fee=0.0` (missing fee data) | BUY: `cash_balance -= qty * price`; SELL: `cash_balance += qty * price`; fee-free accounting is arithmetically correct |

---

## 6. TDD Plan

Tests must be written before S4-S1 is applied (characterization), and validated after (integration).

### Phase 1 — Characterization Tests for `_update_equity_metrics`

Call `_update_equity_metrics` directly (bypassing `_handle_broker_fill`) to confirm the dead method's behavior before it goes live.

| Test | Assertion |
|------|-----------|
| `test_characterize_buy_decreases_cash` | `cash_balance == initial_capital - (qty * price + fees)` |
| `test_characterize_sell_increases_cash` | `cash_balance == initial_capital + (qty * price - fees)` |
| `test_characterize_round_trip_zero_fees` | BUY then SELL at same price, zero fees → `cash_balance == initial_capital` |
| `test_characterize_round_trip_with_fees` | BUY then SELL → `cash_balance == initial_capital - total_fees` |
| `test_characterize_updates_drawdown_hwm` | SELL that takes equity above prior max → `metrics.max_equity` advances |
| `test_characterize_direction_string_branch` | `direction="BUY"` vs `direction="SELL"` → cash moves in correct direction |
| `test_characterize_sell_only_subtracts_fees_once` | SELL at 500, fees=20 → proceeds = `500*qty - 20`, not `500*qty + 20` |

### Phase 2 — Fill-Path Integration Tests

Send fills through `_handle_broker_fill` and assert `cash_balance` state.

| Test | Assertion |
|------|-----------|
| `test_fill_path_buy_updates_cash_balance` | BUY FillEvent with known order_state → `cash_balance` decreases |
| `test_fill_path_sell_updates_cash_balance` | SELL FillEvent with known order_state → `cash_balance` increases |
| `test_fill_path_no_order_state_cash_unchanged` | Unknown order_id → `cash_balance == initial_capital` |
| `test_fill_path_exception_in_equity_metrics_swallowed` | Mock `_update_equity_metrics` to raise → fill completes, no exception propagates |
| `test_fill_path_equity_metrics_called_exactly_once` | Single fill → `_update_equity_metrics` called exactly once (not zero, not twice) |

### Phase 3 — Margin Gate Integration Tests

| Test | Assertion |
|------|-----------|
| `test_margin_gate_denominator_reflects_prior_fill` | Large BUY fill reduces `cash_balance`; subsequent signal margin gate uses updated denominator |
| `test_margin_gate_unaffected_before_any_fills` | No fills → `cash_balance == initial_capital`; gate denominator unchanged |

### Phase 4 — Drawdown Gate Integration Tests

| Test | Assertion |
|------|-----------|
| `test_drawdown_gate_reflects_realized_loss_after_sell` | BUY at 100, SELL at 80 → `max_drawdown_pct > 0` after the SELL fill |
| `test_drawdown_sampled_at_fill_time_and_signal_time` | Verify `update_drawdown` called from both `_update_equity_metrics` and the gate in `process_signal` |

### Phase 5 — Regression Tests

| Test | Assertion |
|------|-----------|
| `test_no_regression_construction_cash_balance_no_fills` | `cash_balance == initial_capital` when no fills have occurred (guards `test_fno_runner_composition.py:81,87`) |
| Full 668-test suite | Zero regressions; all new tests pass |

---

## 7. Implementation Slices

### S4-S1 — Wire `_update_equity_metrics` Into `_handle_broker_fill`

**File**: `core/execution/handler.py`

**Location**: Inside `_handle_broker_fill`, within the `if order_state:` block, immediately after the `TradeEvent` (`trade`) is constructed, before the MAE/MFE block and `trading_writer` calls.

**Change**: Add exactly one line:

```python
self._update_equity_metrics(trade)
```

**Constraints**:
- Must be inside `if order_state:` — `trade` only exists in this block
- Must be after `position_tracker.update_from_fill(fill)` — net_qty must be post-fill
- Must be after `trade = TradeEvent(...)` — method requires a `TradeEvent`
- Must remain inside the existing `try/except Exception` — no exception-handling changes

No other code changes. No changes to `_update_equity_metrics`, the drawdown gate, the margin gate, or any other method.

---

## 8. Acceptance Criteria

1. After any BUY fill with a known order_id, `metrics.cash_balance` decreases by `qty * fill_price + fill_fee`.
2. After any SELL fill with a known order_id, `metrics.cash_balance` increases by `qty * fill_price - fill_fee`.
3. After a BUY+SELL round-trip at identical prices with zero fees, `metrics.cash_balance == initial_capital`.
4. A fill for an unknown order_id leaves `metrics.cash_balance` unchanged.
5. An exception inside `_update_equity_metrics` does not propagate out of `_handle_broker_fill`.
6. `metrics.max_drawdown_pct` advances at fill time when the fill represents a realized loss.
7. The margin gate denominator (`metrics.cash_balance`) reflects realized PnL from all prior fills when gating a new signal.
8. `metrics.cash_balance == initial_capital` when no fills have been processed (construction-time assertions remain valid).
9. `_update_equity_metrics` is called exactly once per fill — no double-accounting.
10. All 668 pre-existing tests pass; no regression is introduced.

---

## 9. Characterization Tests

Characterization tests document the existing behavior of `_update_equity_metrics` before S4 wires it. They must be written and passing on the pre-S4 codebase to prove the dead method is correct before it goes live.

```
test_characterize_update_equity_metrics_buy:
  Given:  handler initialized with initial_capital=100_000
  And:    a TradeEvent(direction="BUY", quantity=10, price=500.0, fees=20.0)
  When:   _update_equity_metrics(trade) called directly
  Then:   metrics.cash_balance == 100_000 - (10 * 500.0 + 20.0) == 94_980.0

test_characterize_update_equity_metrics_sell:
  Given:  handler initialized with initial_capital=100_000
  And:    a TradeEvent(direction="SELL", quantity=10, price=500.0, fees=20.0)
  When:   _update_equity_metrics(trade) called directly
  Then:   metrics.cash_balance == 100_000 + (10 * 500.0 - 20.0) == 104_980.0

test_characterize_update_equity_metrics_drawdown_hwm:
  Given:  handler with initial_capital=100_000, metrics.max_equity=100_000
  And:    position_tracker.net_quantity returns 10 for the trade symbol post-fill
  And:    a TradeEvent(direction="SELL", quantity=10, price=600.0, fees=0.0)
         [cash_balance becomes 106_000; total_equity = 106_000 + 10*600 = 112_000]
  When:   _update_equity_metrics(trade) called
  Then:   metrics.max_equity == 112_000

test_characterize_update_equity_metrics_buy_fees_in_cost:
  Given:  TradeEvent(direction="BUY", quantity=5, price=200.0, fees=50.0)
  When:   _update_equity_metrics(trade) called
  Then:   cash outflow == 5 * 200.0 + 50.0 == 1_050.0
         [fees are included in cost, not deducted — verify BUY branch uses `cost` var]
```

---

## 10. Integration Tests

```
test_integration_fill_path_updates_cash_balance:
  Given:  fully initialized ExecutionHandler with PaperBroker, initial_capital=100_000
  When:   a BUY signal is processed and a fill is produced
  Then:   metrics.cash_balance < 100_000 after the fill

test_integration_fill_path_margin_gate_uses_updated_cash:
  Given:  initial_capital=10_000, max_capital_utilisation=0.80
  And:    a BUY fill has consumed 8_000 of capital (cash_balance ≈ 2_000 post-fill)
  When:   a second BUY signal arrives with incremental_est > 1_600 (80% of remaining 2_000)
  Then:   margin gate rejects the signal using the updated 2_000 denominator (not 10_000)

test_integration_paper_mode_round_trip:
  Given:  handler in PAPER mode
  When:   BUY signal produces fill N → SELL EXIT signal produces fill M
  Then:   metrics.cash_balance == initial_capital - (fees_N + fees_M)
  And:    realized PnL reflected in cash balance matches pnl_tracker output

test_integration_no_fill_no_cash_change:
  Given:  handler constructed with initial_capital
  When:   no signals or fills processed
  Then:   metrics.cash_balance == initial_capital

test_integration_orphan_fill_cash_unchanged:
  Given:  a FillEvent with an order_id not in order_tracker
  When:   _handle_broker_fill(fill) called
  Then:   metrics.cash_balance == initial_capital (unchanged)
  And:    no exception propagates
```

---

## 11. Definition of Done

- [ ] Phase 1 (characterization) tests written and passing on pre-S4 codebase
- [ ] S4-S1 applied: `self._update_equity_metrics(trade)` inserted at the correct location in `_handle_broker_fill`
- [ ] Phase 2 (fill-path) tests written and passing
- [ ] Phase 3 (margin gate) tests written and passing
- [ ] Phase 4 (drawdown gate) tests written and passing
- [ ] Phase 5 (regression) passes — all 668 baseline tests green, zero regressions
- [ ] All Failure Matrix rows F1–F14 covered by at least one test
- [ ] `grep -rn "cash_balance" tests/` reviewed; any post-fill `== initial_capital` assertions identified and updated
- [ ] `docs/PROJECT_STATE.md` updated: MM9.2-S4 marked COMPLETE; test count updated
- [ ] `docs/CHANGELOG.md` updated with S4 entry
- [ ] `docs/reports/MM9_IMPLEMENTATION_PLAN.md` §9 checklist: `[x] MM9.2-S4` checked
- [ ] Git commit with message: `MM9.2-S4 — wire _update_equity_metrics to fill path; cash_balance tracks realized PnL`

---

## 12. Documentation Updates Required

| Document | Update |
|----------|--------|
| `docs/PROJECT_STATE.md` | Mark MM9.2-S4 COMPLETE; update "Remaining" list (remove S4); update passing test count |
| `docs/CHANGELOG.md` | Add entry: I.H.1 resolved — `metrics.cash_balance` now tracks realized PnL after each fill via `_update_equity_metrics` wired to `_handle_broker_fill` |
| `docs/reports/MM9_IMPLEMENTATION_PLAN.md` | Check `[x] MM9.2-S4` in §9; update §6 status table to COMPLETE |
| `docs/DRIVER_SPECIFICATION.md` | If §8.5 (Margin Gate) describes the capital denominator as `initial_capital`, update to note it is now dynamic (`cash_balance` reflecting realized PnL) |

---

## 13. Risk Assessment

| ID | Risk | Likelihood | Severity | Mitigation |
|----|------|-----------|---------|------------|
| R1 | Exception in `_update_equity_metrics` silently corrupts `cash_balance` — ERROR logged but fill proceeds with stale balance | Low | High | Phase 2 test covers this path (F4); existing try/except logs at ERROR; `cash_balance` drift detectable via telemetry |
| R2 | `_update_equity_metrics` double-called for a single fill if a second call site is added later | Low | Medium | Single insertion point now; characterization test `test_fill_path_equity_metrics_called_exactly_once` asserts call count == 1 |
| R3 | `cost` variable in `_update_equity_metrics` is used only by the BUY branch; SELL recomputes inline — the variable name is misleading but behavior is correct | None | High | Verified before spec was written: BUY uses `cost = qty * price + fees`; SELL uses `qty * price - fees` inline. No logic change needed; flag in code review |
| R4 | SELL-to-open cash credit for short options inflates `cash_balance` relative to real margin-locked capital | Low | Medium | Accepted under D1 flat-rate approximation; MM9.4 SPAN margin will correct this |
| R5 | Drawdown HWM advancing at fill time could make `max_drawdown_pct` larger than signal-time-only sampling | Near-zero | Medium | `update_drawdown` only advances HWM; kill-switch is evaluated only in `process_signal` (line 590); fill-time HWM advance cannot trigger the kill-switch |
| R6 | Existing `test_fno_runner_composition.py:81,87` break post-S4 | Low (they assert pre-fill state) | Low | Both assertions fire at construction time before any fills; they remain valid after S4 |
| R7 | Orphan fill leaves `cash_balance` stale for that fill | Accepted | Medium | Documented boundary (§2.7); orphan fills are reconciliation events; out of S4 scope |

---

## 14. Completion Checklist

- [ ] Read `handler.py:369–450` to confirm exact insertion point and surrounding context before touching the file
- [ ] Run `grep -rn "cash_balance" tests/ --include="*.py"` and enumerate all assertions before any code changes
- [ ] Write Phase 1 characterization tests; confirm they pass on pre-S4 codebase
- [ ] Apply S4-S1: add `self._update_equity_metrics(trade)` at the insertion point
- [ ] Write and pass Phase 2 fill-path integration tests
- [ ] Write and pass Phase 3 margin gate integration tests
- [ ] Write and pass Phase 4 drawdown gate integration tests
- [ ] Run full test suite; confirm ≥668 passing, zero regressions
- [ ] Review any `cash_balance` assertions broken by S4; update them
- [ ] Update `docs/PROJECT_STATE.md`
- [ ] Update `docs/CHANGELOG.md`
- [ ] Check `[x] MM9.2-S4` in `docs/reports/MM9_IMPLEMENTATION_PLAN.md` §9
- [ ] Commit with canonical message: `MM9.2-S4 — wire _update_equity_metrics to fill path; cash_balance tracks realized PnL`
