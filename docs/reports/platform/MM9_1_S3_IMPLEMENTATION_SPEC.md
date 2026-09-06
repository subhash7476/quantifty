# MM9.1-S3 — Capital-Utilisation Gate: Implementation Specification

**Date:** 2026-06-26  
**Status:** Implementation-ready specification — authoritative for GLM  
**Head:** `23b15cc` (578 tests passing)  
**Slice:** MM9.1-S3 — first behavioural slice; activates the margin gate in the execution path  
**Source authority:**
- `docs/reports/MM9_IMPLEMENTATION_PLAN.md` §3 (locked decisions D1–D8, C1–C3)
- `docs/reports/MM9_IMPLEMENTATION_PLAN.md` §4 (slice sequencing — S3 body supersedes stale S2/S3 split)
- `docs/reports/MM9_0_MARGIN_ENFORCEMENT_ARCHITECTURE_REVIEW.md` §2 (enforcement-layer rationale)

> **GLM note:** The implementation plan's §4 slice-body text is partially stale. §9 (checklist) and `docs/CHANGELOG_PLATFORM.md` are authoritative for what was *actually delivered* in S1/S2. S2 shipped `_estimate_required_margin(quantity, price) → quantity * price`, **not** `_check_margin_budget`. S3 therefore implements both the gate method and the call-site wiring. This spec supersedes §4 MM9.1-S2 and §4 MM9.1-S3 in the implementation plan. §3 locked decisions are unchanged.

---

## 1. Gate Placement

### 1.1 Exact Insertion Point

The margin gate inserts in `core/execution/handler.py`, inside `process_signal`, **after** PHASE 2 (`RiskManager.evaluate`) and **before** PHASE 5 (`order_tracker.add_order`).

Current code (verify line numbers against HEAD before implementing):

```python
# PHASE 2: Pre-trade Risk Integration
risk_decision = self.risk_manager.evaluate(
    order,
    trades_today=self._trades_today,
    max_trades_per_day=self.config.max_trades_per_day
)
if not risk_decision.approved:
    self.metrics.rejected_trades += 1
    raise ExecutionRuleError(
        f"Pre-trade risk rejection: {risk_decision.reason}")

# PHASE 5: Order Lifecycle Registration        ← add_order is the next statement
self.order_tracker.add_order(order)
```

The gate occupies the **empty gap between PHASE 2 and PHASE 5**. GLM must insert between the `raise ExecutionRuleError(...)` statement and `self.order_tracker.add_order(order)`.

### 1.2 Why This Location Is Correct

**Order sizing is finalised:** `order.quantity` and `current_price` are both determined before order construction at PHASE 1. `_calculate_position_size` runs at the sizing block; the `NormalizedOrder` is built during PHASE 1. Both are available by the time the gate fires.

**Before broker interaction:** `broker.place_order(order)` is PHASE 7. The gate fires two phases earlier.

**Before `order_tracker.add_order` (C2):** This is the critical correction from the implementation plan §3.4. An order registered in the tracker but never sent to the broker becomes an orphaned order. On session recovery, `_replay_state()` loads all orders and adds them to `_seen_signals`. An orphaned order from a rejected margin gate call would pollute the recovered idempotency registry, permanently blocking the same signal from being reattempted on restart. S3 eliminates this risk by rejecting before registration.

**Preserves MM8 behaviour:** The MM8 error escalation paths (BrokerAuthError → kill switch; BrokerUnavailableError → threshold counter → kill switch) are in PHASE 7. The margin gate fires in the PHASE 2–5 gap. A margin-rejected signal never reaches PHASE 7, so MM8 escalation is unreachable on margin rejection — correct behaviour.

### 1.3 Gate Sequence After S3

```
[PHASE 0]   Authority enforcement + idempotency
[TLP]       Risk metadata validation (sl_dist, risk_r)
[0]         STOP file / kill switch file check
[1]         signals_received += 1
[2]         Kill switch state check → return None
[3]         Daily trade limit → kill switch + return None
[4]         Drawdown check → kill switch + return None
[4b]        Position stacking guard (non-EXIT) → return None
[5]         _check_risk_limits → ExecutionRuleError
[9C]        _check_greek_limits (dead code path at MM9.1-S3 time; became live at MM9.3-S1B)
[TLP]       Structural context capture
[PHASE 1]   Instrument resolution + NormalizedOrder construction
[PHASE 2]   RiskManager.evaluate → rejected_trades += 1 + ExecutionRuleError
[MM9.1]     _check_margin_budget (non-EXIT only) → rejected_trades += 1 + return None  ← NEW
[PHASE 5]   order_tracker.add_order(order)
[PHASE 7]   broker.place_order(order) + MM8 error handling
```

---

## 2. Capital Calculation

### 2.1 Denominator

The gate uses **`self.metrics.cash_balance`** as the capital denominator.

At construction, `self.metrics = ExecutionMetrics(max_equity=initial_capital, cash_balance=initial_capital)`. Because `_update_equity_metrics` is never called from the fill path (pre-existing gap I.H.1, resolved in MM9.2-S4), `cash_balance` is permanently equal to the initial capital value passed at construction.

This is a documented, accepted limitation for MM9.1. The denominator is effectively the initial capital — stable, predictable, and consistent with the static analysis the gate performs. The plan's D2 specifies `cash_balance` deliberately. Do **not** introduce a separate `self._initial_capital` instance variable; that creates a second source of truth and diverges from the planned MM9.2-S4 fix path.

### 2.2 Numerator

The numerator is `used_current + incremental_est`, where:

**`used_current`** — existing portfolio margin:
```python
used_current = self.margin_tracker.get_used_margin({order.symbol: current_price})
```
This computes `get_exposure({order.symbol: current_price}) * margin_rate`. `get_exposure` iterates all tracked positions but only prices the symbol matching `order.symbol`; all other open symbols contribute zero exposure. This is the C3 single-symbol limitation — documented, accepted, and logged. Do not fix in S3.

**`incremental_est`** — new order's margin contribution:
```python
effective_multiplier = (
    order.canonical_instrument.multiplier
    if order.canonical_instrument is not None
    else order.instrument.multiplier
)
incremental_est = (
    self._estimate_required_margin(order.quantity * effective_multiplier, current_price)
    * self.margin_tracker.margin_rate
)
```

This applies the C1 correction (§3.6 of the plan): for F&O instruments, `canonical_instrument.multiplier` equals `lot_size` (e.g. 65 for NIFTY, 30 for BANKNIFTY). Without the multiplier, the gate underestimates option/futures margin by a factor of `lot_size`. For equity, `canonical_instrument` is `None` and `instrument.multiplier` defaults to `1.0`.

### 2.3 Utilisation Formula

```
utilisation = (used_current + incremental_est) / self.metrics.cash_balance
```

The gate approves when `utilisation <= self.config.max_capital_utilisation`. Equal to the limit is **approved** (boundary included per D-boundary).

### 2.4 Why `cash_balance`, Not Current Equity or Realized PnL

- **`cash_balance` (= initial capital):** Stable denominator. Correctly tightens effective headroom as positions accumulate.
- **Current equity:** Not available — `_update_equity_metrics` is unwired; position tracker values are not marked-to-market.
- **Realized PnL:** Not appropriate — a session profit should not relax the margin limit. The limit governs capital deployment, not profitability.
- **Available cash:** Conceptually correct for a buying-power model (MM9.4), but requires SPAN incremental margin, which does not exist yet.

---

## 3. Margin Estimate

### 3.1 S2 Helper — Role in S3

`_estimate_required_margin(quantity, price) → quantity * price` is the **notional primitive**. It is consumed inside `_check_margin_budget` with the C1 multiplier applied to `quantity` and the `margin_rate` factor applied to the result:

```python
self._estimate_required_margin(order.quantity * effective_multiplier, current_price)
* self.margin_tracker.margin_rate
```

This is mathematically identical to `order.quantity * effective_multiplier * current_price * margin_rate`. The S2 helper provides the notional computation; the gate method wraps it with the economic context (rate, multiplier). When SPAN replaces the helper in MM9.4, only `_estimate_required_margin` changes — it returns actual SPAN margin directly, and the `* margin_rate` factor is dropped from `_check_margin_budget`. The call site in `process_signal` is unchanged.

### 3.2 Helper Must Not Be Modified in S3

`_estimate_required_margin` ships exactly as implemented in S2. Its replacement boundary is clearly marked: "Future MM9.x: replace with broker/SPAN margin engine." Any change to the helper belongs in MM9.4, not S3.

### 3.3 Known Defects in the Existing Portfolio Estimate

`MarginTracker._calculate_single_exposure` uses `pos.instrument.multiplier`, which is `1.0` for all option positions restored via the canonical restore path (`canonical_restore.py` hardcodes `multiplier=1.0`). This means `used_current` systematically underestimates the option portfolio's margin by a factor of `lot_size`. This is a pre-existing defect documented in the implementation plan §2.2 and §8.3 (I.C.1 partial). It is **not fixed in S3** — the full fix is MM9.2-S2. The C1 correction in S3 applies only to the **new order's** incremental estimate, not to `used_current`.

---

## 4. Behaviour on Utilisation Exceeded

### 4.1 Gate Outcome

Per locked decision D4: **rejection, not kill switch**. Margin budget exhaustion on one signal is a per-bar condition. The next bar may bring a different signal, or an open position may close, restoring headroom. Tripping the kill switch would permanently halt the session for a recoverable condition.

| Property | Drawdown Gate | Margin Gate |
|---|---|---|
| Trigger | Equity loss > threshold | Margin utilisation > limit |
| Consequence | Kill switch (session ends) | Order rejected (session continues) |
| Reversible? | No — requires restart | Yes — next bar may clear |
| Cascade? | Kills all subsequent signals | Only this signal |

### 4.2 Logging

Log at WARNING level on every rejection. The warning must include:
- `symbol` — which instrument was being considered
- `signal_id` — for correlation with the audit trail
- `utilisation` — the computed ratio (as percentage, two decimal places)
- `limit` — the configured `max_capital_utilisation` (as percentage, two decimal places)
- The C3 disclosure string verbatim: `[C3: single-symbol gate only — other open positions not priced]`

Required format:
```python
self.logger.warning(
    "MARGIN_BUDGET_REJECTED symbol=%s signal_id=%s utilisation=%.2f%% "
    "limit=%.2f%% [C3: single-symbol gate only — other open positions not priced]",
    order.symbol, signal_id,
    utilisation * 100,
    self.config.max_capital_utilisation * 100,
)
```

The C3 disclosure is mandatory — it is the only runtime indication that the gate is not a portfolio-level control.

### 4.3 Metrics

Increment `self.metrics.rejected_trades` by exactly 1 on rejection. This is the same counter incremented on `RiskManager.evaluate` rejection. The distinction between margin rejection and risk rejection is captured in the log message, not in separate counters. Do not add a new counter in S3.

`signals_received` is already incremented unconditionally at gate [1] and is not touched here.

### 4.4 Return Value

`return None` — consistent with every other per-signal rejection gate in `process_signal` (kill switch, drawdown, stacking guard). This ensures margin-rejected signals are invisible to `EXECUTION_CALLS` (MM8 §7.5 behavioural contract: a non-`None` return means broker execution was attempted).

### 4.5 Event Journal — No Entry for Margin Rejection

**Do not add a new `EventType.MARGIN_GATE_REJECTED` and do not write a journal entry on margin rejection.**

The `RuntimeEventJournal` is for durable operational incidents (broker failures, kill switch activations, startup gate events). A margin rejection is a routine per-bar execution decision — noisy, expected, and recoverable. Journaling every rejection would flood the JSONL with non-incident entries, conflating them with the auditable incident record. The WARNING log provides sufficient observability. Adding a new EventType is scope creep — no consumer reads it yet.

### 4.6 Interaction with MM8

MM8 paths (BrokerAuthError escalation, BrokerUnavailableError threshold counter) live in PHASE 7. A margin-rejected signal never reaches PHASE 7, so `_consecutive_broker_errors` and `activate_kill_switch` are never reached from a margin rejection. The two systems are orthogonal.

### 4.7 Interaction with RiskManager

`RiskManager.evaluate()` fires before the margin gate and may reject independently. If `RiskManager` rejects, the margin gate never runs. If `RiskManager` approves, the margin gate runs next. The two gates are independent — no shared state. Both increment `rejected_trades` on their respective rejections — correct, as the counter tracks total rejected signals regardless of rejection reason.

`RiskManager` must remain stateless per locked decision D5. The margin gate is **not** added to `RiskManager`. It belongs to `ExecutionHandler` as a portfolio-level control.

---

## 5. Edge Cases

### 5.1 Zero Capital (`cash_balance <= 0`)

Return `(True, 0.0)` immediately. No exception. No rejection. If `cash_balance` is zero or negative (degenerate construction), the gate cannot compute a meaningful utilisation ratio. Blocking all trading would be worse than allowing it. This guard is the **first check** in `_check_margin_budget`, before any division.

### 5.2 Zero Margin Estimate (`quantity == 0` or `price == 0`)

`_estimate_required_margin(0, price) == 0` and `_estimate_required_margin(qty, 0) == 0`. `incremental_est == 0`. `utilisation = used_current / cash_balance`. If `used_current == 0` as well, `utilisation = 0.0` — passes. No special handling needed.

### 5.3 Floating Point Precision

The comparison `utilisation <= self.config.max_capital_utilisation` uses Python's native float comparison. At exactly equal values (e.g. both `0.8000000000000000`), this evaluates to `True` (approved). No epsilon tolerance is required; this is not a numerical computation requiring guard against rounding error.

### 5.4 EXIT Signals (D8)

EXIT signals bypass the gate unconditionally. An EXIT BUY (covering a short) computes a positive incremental margin estimate, but the economic effect is to *close* a short position, reducing required margin. Gating an EXIT blocks position-closing trades — the opposite of safety.

The bypass is enforced at the **call site** in `process_signal`, not inside `_check_margin_budget`, because `NormalizedOrder` has no `signal_type` field. `signal` is in scope at the call site. The guard is:

```python
if signal.signal_type != SignalType.EXIT:
    approved, utilisation = self._check_margin_budget(order, current_price)
    if not approved:
        ...
        return None
```

`order_tracker.add_order(order)` runs unconditionally after this block (for both EXIT and approved non-EXIT).

### 5.5 Repeated Rejected Signals

Each signal has a unique `signal_id`. After rejection, the signal has been added to `_seen_signals` (idempotency lock fires before the gate). The same signal cannot be re-submitted. A new signal for the same instrument on the next bar has a different `signal_id` and is evaluated independently. No special handling needed.

### 5.6 Paper Broker

The gate runs identically in PAPER mode. `PaperBroker.place_order()` generates a synthetic fill; the margin gate fires before it. The paper rung is the full execution path with simulated fills — the same capital model applies.

### 5.7 Live Broker

The gate runs identically in LIVE mode. No broker API call is made during the gate check. All inputs are local in-process state: `order.quantity`, `current_price`, `position_tracker._positions`, `metrics.cash_balance`.

### 5.8 Restored State (Recovery)

`_replay_state()` runs at construction (before `process_signal` is ever called) and rebuilds `PositionTracker` from all historical fills. By the time the gate runs on the first live signal, `PositionTracker._positions` reflects all recovered positions. `MarginTracker.get_used_margin()` reads from `PositionTracker` at call time, so the gate correctly accounts for all open positions including those restored from persistence.

### 5.9 Replay / Backtest

The gate applies in backtest mode — consistent with the platform invariant that every trade must be validated. Backtesting disables idempotency (`execution._is_signal_already_executed = lambda sid: False`) but does not disable the margin gate.

### 5.10 Multi-Symbol Portfolio (C3 — documented, not fixed)

In a portfolio with open positions in five symbols (e.g. NIFTY, BANKNIFTY, RELIANCE, INFY, TCS) and a new signal for SBIN:

`get_used_margin({order.symbol: current_price})` iterates all six symbols but only has a price for SBIN. The five existing symbols contribute zero to `used_current`. The gate sees `incremental_est / cash_balance` rather than `(existing_portfolio_margin + incremental_est) / cash_balance`.

If each of the five open positions carries 30% of capital in margin, the actual portfolio margin is ~150% — but the gate approves the sixth signal at ~25% apparent utilisation.

This is C3, documented and accepted for MM9.1. The C3 disclosure is mandatory in the WARNING log. The fix is MM9.2-S1 (per-symbol price cache). Until then, `max_capital_utilisation = 0.80` provides **no portfolio-level protection** for multi-symbol deployments.

---

## 6. Architectural Risks

### 6.1 Orphaned Order on Rejection (Critical — C2, Eliminated by This Spec)

A rejection after `order_tracker.add_order()` creates an orphaned order that corrupts session recovery. S3's placement strictly before `add_order` eliminates this risk. GLM must verify the insertion is before `self.order_tracker.add_order(order)` — no code between the margin gate rejection block and `add_order` must be skipped.

**Mitigation:** Test I6 (`test_rejected_signal_order_not_in_tracker`) is the acceptance gate for this risk.

### 6.2 Static `cash_balance` Denominator (I.H.1 — Accepted)

`metrics.cash_balance` does not update during a session. In a losing session, the denominator does not shrink — the gate is too permissive. This is I.H.1, resolved in MM9.2-S4. No action in S3.

### 6.3 MarginTracker Option Multiplier Defect (I.C.1 Partial — Accepted)

`used_current` from `MarginTracker.get_used_margin()` underestimates option portfolio margin by `lot_size` (pre-existing defect in the restore path). The C1 correction applies only to the new order's incremental estimate. The gate is too permissive for portfolios with existing option positions. Resolved in MM9.2-S2. No action in S3.

### 6.4 `effective_multiplier` for Equity

For equity signals, `order.canonical_instrument` is `None`. The fallback `order.instrument.multiplier` is `1.0`. For equity: `incremental_est = _estimate_required_margin(quantity * 1.0, price) * margin_rate = quantity * price * margin_rate`. Correct.

### 6.5 Future SPAN Engine Interaction

In MM9.4: `_estimate_required_margin` returns SPAN initial margin directly. `_check_margin_budget` drops the `* margin_rate` factor. `get_used_margin()` is replaced by the SPAN calculator's portfolio scan. The call site in `process_signal` is unchanged. The S3 implementation must not expose `margin_rate` multiplication in the `_check_margin_budget` signature or to the call site — it is an internal detail that SPAN removes.

### 6.6 Regressions in MM8 Tests (Medium — Assessed Low Risk)

After wiring the gate, any test that calls `process_signal` with a large `quantity × price` relative to the default `initial_capital=100_000` may be margin-rejected. The default `margin_rate=0.20` and `max_capital_utilisation=0.80` allow up to `100_000 × 0.80 / 0.20 = 400_000` in notional. With `default_quantity=100` and `price=100`: notional = 10,000 — well under 400,000. Existing tests should pass. **Run the full suite immediately after S3 and investigate any failures.**

---

## 7. TDD Plan

All tests append to the existing `tests/execution/test_mm9_1_margin_gate.py`. The 4 S1 tests already in this file must remain passing and must not be modified.

### 7.1 Construction Helper

The S3 tests need `initial_capital` and `max_capital_utilisation` control. Either extract the helper from `test_mm9_1_margin_estimator.py` or define a new one in `test_mm9_1_margin_gate.py`:

```python
def _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0, max_utilisation=0.80):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    clock = ReplayClock(FIXED_DT)
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=PaperBroker(clock),
        config=ExecutionConfig(max_capital_utilisation=max_utilisation),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
    )
```

### 7.2 Signal Factory

```python
def _make_signal(symbol="NSE_EQ|INE001A01036", sig_type=SignalType.BUY, suffix="S3"):
    return SignalEvent(
        strategy_id="test_margin",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=sig_type,
        confidence=0.9,
        metadata={"signal_id": f"SIG-MM9-{suffix}"},
    )
```

### 7.3 Priority 1 — Gate Method Unit Tests (`_check_margin_budget`)

| ID | Test name | What it verifies |
|---|---|---|
| U1 | `test_check_margin_budget_returns_tuple` | Method exists on `ExecutionHandler`; returns `tuple[bool, float]` |
| U2 | `test_check_margin_budget_approves_below_limit` | utilisation 0.4 < limit 0.8 → `(True, ~0.4)` |
| U3 | `test_check_margin_budget_rejects_above_limit` | utilisation 0.9 > limit 0.8 → `(False, ~0.9)` |
| U4 | `test_check_margin_budget_boundary_equal_approved` | utilisation == limit exactly → `(True, utilisation)` |
| U5 | `test_check_margin_budget_zero_cash_balance_returns_true` | `cash_balance=0` → `(True, 0.0)`, no `ZeroDivisionError` |
| U6 | `test_canonical_multiplier_applied_f_and_o` | `canonical_instrument.multiplier=75`; incremental uses 75×, not 1× |
| U7 | `test_equity_fallback_multiplier_is_1_0` | `canonical_instrument=None`; incremental uses `instrument.multiplier == 1.0` |

For U6 and U7: construct a `NormalizedOrder` directly to control `canonical_instrument`. Do not rely on `process_signal` for these unit tests.

For U2/U3/U4: set `initial_capital` and `quantity × price` to produce known utilisation ratios. Example for U3 (over-limit): `initial_capital=100`, `quantity=100`, `price=10.0`, `margin_rate=0.20` → `incremental_est = 100 * 1.0 * 10.0 * 0.20 = 200`; `utilisation = 200/100 = 2.0 > 0.8`.

### 7.4 Priority 1 — Call Site Integration Tests

| ID | Test name | What it verifies |
|---|---|---|
| I1 | `test_process_signal_rejected_when_over_limit` | Over-limit signal → `process_signal` returns `None`; `rejected_trades += 1` |
| I2 | `test_process_signal_approved_when_under_limit` | Under-limit signal → `process_signal` returns non-`None`; signal reaches broker |
| I3 | `test_exit_signal_bypasses_margin_gate` | EXIT against open LONG → executes; `_check_margin_budget` not called |
| I4 | `test_rejected_trades_increments_exactly_once_on_rejection` | Counter changes by exactly 1; approval leaves it unchanged |
| I5 | `test_approved_signal_order_not_orphaned` | Approval → `order_tracker` contains the order's `correlation_id` |
| I6 | `test_rejected_signal_order_not_in_tracker` | Rejection → `order_tracker` has no record for the rejected order |
| I7 | `test_warning_logged_on_rejection` | Rejected signal → `caplog` contains `"MARGIN_BUDGET_REJECTED"` and `"C3:"` |
| I8 | `test_warning_not_logged_on_approval` | Approved signal → no `"MARGIN_BUDGET_REJECTED"` in logs |

For I3: process a BUY signal first (open the LONG), then process an EXIT signal with over-limit `initial_capital` — EXIT must execute. Spy on `_check_margin_budget` using `monkeypatch` or `unittest.mock.patch.object` to confirm it was not called.

### 7.5 Priority 2 — Regression Tests

| ID | Test name | What it verifies |
|---|---|---|
| R1 | `test_kill_switch_still_gates_before_margin` | Kill switch active → `return None` before margin gate (kill switch is gate [2]) |
| R2 | `test_risk_manager_rejection_fires_before_margin_gate` | RiskManager rejects → `ExecutionRuleError` raised before margin gate runs |
| R3 | `test_paper_broker_fill_path_unaffected_by_approved_margin` | Approved signal → PaperBroker generates fill → position tracked normally |
| R4 | `test_recovery_positions_contribute_to_margin` | Manually inject position into `PositionTracker`; next signal sees recovered margin in gate |

For R4: build handler; call `position_tracker.update_from_fill(fill)` to inject a position; then process a new signal and verify `used_current > 0` in the gate. Do not mock `get_used_margin` — test the integration end-to-end.

### 7.6 Known-Limitation Documentation Test

| ID | Test name | What it verifies |
|---|---|---|
| L1 | `test_multi_symbol_blindness_documented` | Three open positions at 30% each; new signal for fourth symbol; gate approves (C3: sees ~9%, not ~99%). WARNING log must contain `"C3:"`. |

This test must include a docstring explaining the MM9.1 scope boundary and referencing MM9.2-S1 as the fix. This test is a specification test, not a correctness test — the C3 limitation is the expected, documented behaviour.

### 7.7 Existing Tests Must Not Be Modified

The 4 S1 tests in `test_mm9_1_margin_gate.py` and the 5 S2 tests in `test_mm9_1_margin_estimator.py` must remain green and unchanged.

---

## 8. Documentation

The following documents must be updated in a follow-on KB sync commit after S3 is merged. GLM implements S3 code only; the KB sync is a separate commit.

| Document | Required update |
|---|---|
| `docs/PROJECT_STATE.md` | In the MM9 "In Progress" entry: change "Margin Check status remains MISSING" to "PARTIAL (MM9.1-S3 complete: single-symbol, flat-rate gate wired)". Mark MM9.1-S3 as complete. |
| `docs/CHANGELOG_PLATFORM.md` | Add entry: `## 2026-06-26 — MM9.1-S3 — Capital-utilisation gate wired into process_signal (578→N passing)` with a short factual description matching the milestone format. |
| `docs/reports/MM9_IMPLEMENTATION_PLAN.md` | Tick `[x] MM9.1-S3` in §9. Add note to §4 MM9.1-S2 body: "Spec stale — S2 delivered `_estimate_required_margin`; `_check_margin_budget` implemented in S3. See `MM9_1_S3_IMPLEMENTATION_SPEC.md`." |
| `docs/DRIVER_SPECIFICATION.md` | Add subsection under the Execution section documenting the margin gate: placement (PHASE 2→PHASE 5 gap), formula, config field, EXIT bypass, C3 limitation, and the WARNING log format. |

---

## 9. Implementation Slices and Diff Plan

S3 is implemented in a **single commit**. The diff touches exactly **two locations** in `core/execution/handler.py` and appends to one test file.

### 9.1 Slice A — `_check_margin_budget` Private Method

Add immediately after `_estimate_required_margin` in `core/execution/handler.py` (currently ending at approximately line 913). The method is private, not called from outside `ExecutionHandler`.

```python
def _check_margin_budget(self, order: NormalizedOrder, current_price: float) -> tuple[bool, float]:
    # MM9.1: capital-utilisation gate — (approved, utilisation).
    # C2: must be called before order_tracker.add_order to avoid orphaned orders on recovery.
    # C3: single-symbol price dict — other open symbols contribute 0 to used_current.
    if self.metrics.cash_balance <= 0:
        return True, 0.0

    # C1: canonical_instrument.multiplier is lot_size for F&O (e.g. 65 for NIFTY).
    effective_multiplier = (
        order.canonical_instrument.multiplier
        if order.canonical_instrument is not None
        else order.instrument.multiplier
    )
    used_current = self.margin_tracker.get_used_margin({order.symbol: current_price})
    incremental_est = (
        self._estimate_required_margin(order.quantity * effective_multiplier, current_price)
        * self.margin_tracker.margin_rate
    )
    utilisation = (used_current + incremental_est) / self.metrics.cash_balance
    return utilisation <= self.config.max_capital_utilisation, utilisation
```

### 9.2 Slice B — Call Site in `process_signal`

Insert between the PHASE 2 risk rejection block and the PHASE 5 `order_tracker.add_order` statement. The `signal_id` variable and `signal` object are both in scope at this point.

```python
# MM9.1-S3: capital-utilisation gate
# D8: EXIT signals bypass — closing a position reduces margin; gating an EXIT is unsafe.
if signal.signal_type != SignalType.EXIT:
    approved, utilisation = self._check_margin_budget(order, current_price)
    if not approved:
        self.metrics.rejected_trades += 1
        self.logger.warning(
            "MARGIN_BUDGET_REJECTED symbol=%s signal_id=%s utilisation=%.2f%% "
            "limit=%.2f%% [C3: single-symbol gate only — other open positions not priced]",
            order.symbol, signal_id,
            utilisation * 100,
            self.config.max_capital_utilisation * 100,
        )
        return None

# PHASE 5: Order Lifecycle Registration
self.order_tracker.add_order(order)
```

### 9.3 No Other File Changes

- `core/execution/risk_manager.py` — no change (D5: RiskManager stays stateless)
- `core/execution/margin_tracker.py` — no change (defects deferred to MM9.2-S2)
- `core/runtime/event_journal.py` — no change (no new EventType)
- `scripts/fno_runner.py` — no change (`initial_capital` propagation is MM9.1-S5)
- No new modules or files

---

## 10. Behavioural Contract

After S3, `process_signal` satisfies the following invariants on every call:

**B1 — No orphaned orders on margin rejection.**  
A signal rejected by `_check_margin_budget` is not registered in `order_tracker`. `order_tracker` has no record for the rejected order's `correlation_id`.

**B2 — EXIT signals are not margin-gated.**  
`signal.signal_type == SignalType.EXIT` reaches `order_tracker.add_order` without a `_check_margin_budget` call.

**B3 — `rejected_trades` is monotonically non-decreasing.**  
On margin rejection: `rejected_trades[after] == rejected_trades[before] + 1`. On any other path: `rejected_trades[after] == rejected_trades[before]`.

**B4 — Return value semantics.**  
A margin-rejected signal returns `None`. An approved signal returns a `NormalizedOrder` on successful broker placement, or `None` on broker error (as per MM8 contracts). The margin gate never produces a `NormalizedOrder` on rejection — it can only produce `None`.

**B5 — C3 disclosure on every rejection.**  
Every `MARGIN_BUDGET_REJECTED` log line contains `[C3: single-symbol gate only — other open positions not priced]`.

**B6 — Gate does not alter idempotency state.**  
The signal ID is added to `_seen_signals` before the gate fires (standard idempotency lock at the top of `process_signal`). A margin-rejected signal is permanently blocked from reprocessing in the same session — correct.

---

## 11. Runtime Semantics

### 11.1 First Signal in Session (No Open Positions)

`position_tracker._positions` is empty. `used_current = 0.0`. `utilisation = incremental_est / cash_balance`. For a single equity signal with `quantity=100`, `price=₹100`, `margin_rate=0.20`, `cash_balance=₹100,000`: `utilisation = 100 * 1.0 * 100 * 0.20 / 100,000 = 0.02 = 2%`. Well under the 80% limit. Gate passes.

### 11.2 After a Fill

When a paper fill processes via `_handle_broker_fill`, `position_tracker` updates. On the next signal, `margin_tracker.get_used_margin({symbol: price})` sees the open position. If it is the same symbol as the new signal, the existing position's margin contributes to `used_current`. If a different symbol, it contributes zero (C3).

### 11.3 After Session Recovery

`_replay_state()` calls `position_tracker.update_from_fill()` for every historical fill at startup. Open positions are tracked. On the first live signal, `used_current` correctly reflects all recovered open positions — identical to a non-recovered session with the same positions.

---

## 12. Acceptance Criteria

All of the following must be true before S3 is considered complete:

**AC1.** `_check_margin_budget(order, current_price)` method exists on `ExecutionHandler`, returns `tuple[bool, float]`.

**AC2.** `_check_margin_budget` returns `(True, 0.0)` when `self.metrics.cash_balance <= 0`. No `ZeroDivisionError`.

**AC3.** `_check_margin_budget` uses `canonical_instrument.multiplier` when `canonical_instrument is not None`, and `instrument.multiplier` as fallback.

**AC4.** A signal where `(used_current + incremental_est) / cash_balance > max_capital_utilisation` causes `process_signal` to return `None`.

**AC5.** After AC4: `rejected_trades` incremented by exactly 1; `order_tracker` has no record for the rejected order.

**AC6.** A signal where `(used_current + incremental_est) / cash_balance <= max_capital_utilisation` causes `process_signal` to reach `order_tracker.add_order` and returns non-`None`.

**AC7.** An EXIT signal against an open LONG position reaches `order_tracker.add_order` without `_check_margin_budget` being called.

**AC8.** On any rejection: WARNING log contains `"MARGIN_BUDGET_REJECTED"` and `"[C3: single-symbol gate only"`.

**AC9.** All 578 pre-existing tests pass unchanged.

**AC10.** All Priority 1 tests (U1–U7, I1–I8) pass.

**AC11.** Known-limitation test L1 exists, documents C3, and confirms gate approval despite multi-symbol portfolio saturation.

---

## 13. Implementation Risks

### 13.1 Insertion After `add_order` (Critical)

If `_check_margin_budget` is called after `order_tracker.add_order`, a rejected signal leaves an orphaned order that corrupts session recovery. GLM must verify the insertion strictly precedes `self.order_tracker.add_order(order)`.

**Detection:** Test I6 (`test_rejected_signal_order_not_in_tracker`) fails if this is wrong.

### 13.2 EXIT Bypass Omitted (High)

If the EXIT bypass is omitted or incorrectly conditioned, EXIT signals are margin-gated, blocking position-closing trades.

**Detection:** Test I3 (`test_exit_signal_bypasses_margin_gate`) fails if this is wrong.

### 13.3 MM8 Test Regressions (Low — Assessed)

With `default_quantity=100`, `price=100`, `initial_capital=100,000`, `margin_rate=0.20`: `utilisation = 0.02`. Well below `max_capital_utilisation=0.80`. Existing MM8 tests are not expected to fail. Run the full suite immediately after S3 to confirm.

### 13.4 `margin_rate` Accessibility

`self.margin_tracker.margin_rate` is a public instance variable set in `MarginTracker.__init__`. No access risk.

---

## 14. Readiness Verdict

**READY TO IMPLEMENT.**

All prerequisites are satisfied:

| Prerequisite | Status |
|---|---|
| `ExecutionConfig.max_capital_utilisation = 0.80` | COMPLETE — MM9.1-S1 |
| `_estimate_required_margin(quantity, price) → quantity * price` | COMPLETE — MM9.1-S2 |
| Gate placement verified against `handler.py` HEAD | CONFIRMED — between PHASE 2 and PHASE 5 |
| Exact insertion identified | CONFIRMED — after `raise ExecutionRuleError(risk rejection)`, before `order_tracker.add_order` |
| Formula specified (D2, C1, C3 applied) | COMPLETE — §2 above |
| Behaviour on rejection specified (D4, D8) | COMPLETE — §4 above |
| EXIT bypass at call site confirmed (D8) | CONFIRMED — `signal.signal_type != SignalType.EXIT` |
| No new EventType, no new instance variables | CONFIRMED |
| TDD plan (Priority 1, Priority 2, L1) | COMPLETE — §7 above |
| MM8 regression risk assessed | LOW — small quantities relative to default capital |
| Baseline test count | 578 tests passing at HEAD `23b15cc` |

S3 is two insertions into `core/execution/handler.py` plus additions to `tests/execution/test_mm9_1_margin_gate.py`. No other file is touched. All architectural decisions are locked in the implementation plan §3; no new decisions are required during implementation.

**Suggested commit message:**
```
MM9.1-S3 — capital-utilisation gate wired into process_signal (C1/C2/C3 applied)
```
