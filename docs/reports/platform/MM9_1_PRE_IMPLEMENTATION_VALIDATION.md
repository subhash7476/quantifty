# MM9.1 Pre-Implementation Validation Review

**Date:** 2026-06-16
**Reviewer role:** Platform Architect — evidence-only review
**Methodology:** Repository-first. Every claim cites a specific file and line.
**Scope:** Validate all MM9.0 assumptions against actual implementation before a single line of MM9.1 is written.

---

## Executive Summary

MM9.0 is partially correct. Three of its assumptions are **wrong or dangerously incomplete**:

1. `order.instrument.multiplier` is hardcoded to `1.0` for all option positions — making the exposure calculation wrong by a factor of `lot_size` for every F&O order. (`canonical_restore.py:68`)
2. `order_tracker.add_order()` fires **before** `broker.place_order()`. A margin rejection placed after `add_order()` orphans the order in the tracker. The gate position stated in MM9.0 is wrong.
3. `get_used_margin({signal.symbol: current_price})` with a single-symbol price dict is effectively a **per-symbol gate**, not a portfolio gate — other open symbols contribute zero to used margin, making the gate blind to portfolio-level margin requirements.

These are not edge cases. They are structural defects in the proposed contract. MM9.1 cannot be implemented from MM9.0 as written.

---

## A. Margin Inputs

### A.1 `margin_tracker.get_used_margin(...)`

**Source:** `core/execution/margin_tracker.py:37-39`

```python
def get_used_margin(self, current_prices: Dict[str, float]) -> float:
    return self.get_exposure(current_prices) * self.margin_rate
```

**Source:** `core/execution/margin_tracker.py:19-29`

```python
def get_exposure(self, current_prices, symbol=None):
    total_exposure = 0.0
    for sym in self.position_tracker._positions:
        price = current_prices.get(sym)
        if price:                                         # ← falsy check
            total_exposure += self._calculate_single_exposure(sym, price)
    return total_exposure

def _calculate_single_exposure(self, symbol, current_price):
    pos = self.position_tracker.get_position(symbol)
    return pos.quantity * current_price * pos.instrument.multiplier   # ← multiplier
```

**Confirmed:** Method exists. Signature takes `Dict[str, float]`. Returns float.

**Edge cases identified:**

- `if price:` is a **falsy check** — a position priced at exactly `0.0` is silently excluded from exposure. This is a pre-existing defect, not MM9.1's to fix, but it means the gate can under-count exposure if any price is zero.
- If `current_prices` is an empty dict or does not contain any open position's symbol, `get_exposure()` returns `0.0`. No error. Silent zero.
- `self.position_tracker._positions` is accessed directly (private attribute), bypassing the tracker's public API. Pre-existing coupling.

**Critical finding:** The method uses `pos.instrument.multiplier`. See A.3 for why this is catastrophically wrong for F&O.

---

### A.2 `margin_tracker.margin_rate`

**Source:** `core/execution/margin_tracker.py:11-17`

```python
class MarginTracker:
    def __init__(self, position_tracker, margin_rate: float = 0.2):
        self.margin_rate = margin_rate
```

**Confirmed:** Field exists. Type `float`. Default 0.2.

**Initialization path in `ExecutionHandler.__init__`:** `handler.py:163`

```python
self.margin_tracker = MarginTracker(self.position_tracker)
```

Called with no `margin_rate` argument — **always 0.2**. There is no config wiring between `ExecutionConfig` and `MarginTracker`. The rate is not tunable at runtime without constructing a custom `MarginTracker`.

**Implication for MM9.1:** `margin_tracker.margin_rate` is not operator-configurable via `ExecutionConfig`. The `max_capital_utilisation` field proposed in MM9.0 can be added to `ExecutionConfig`, but the flat rate itself cannot be tuned that way. This is an acceptable MM9.1 limitation.

---

### A.3 `order.instrument.multiplier` — CRITICAL DEFECT

**Source:** `core/instruments/instrument_base.py:13-17`

```python
@dataclass(frozen=True)
class Instrument:
    multiplier: float = 1.0
```

**Source:** `core/instruments/option.py:20-36`

```python
def __init__(self, ..., lot_size: int = 1, multiplier: float = 1.0, ...):
    object.__setattr__(self, 'multiplier', multiplier)   # independent of lot_size
    object.__setattr__(self, 'lot_size', lot_size)
```

**Source:** `core/execution/canonical_restore.py:61-69` — THE DECISIVE EVIDENCE

```python
return Option(
    symbol=symbol,
    underlying=underlying,
    expiry=expiry,
    strike=strike_price,
    option_type=option_type,
    lot_size=ci.lot_size,   # ← correctly sourced from CanonicalInstrument
    multiplier=1.0,          # ← HARDCODED TO 1.0 FOR ALL OPTIONS
)
```

`canonical_restore.py` is the G1 Wave 4B / Wave 3 canonicalization primitive. Every option position that has been through a live fill or a restored-ledger pass has its instrument replaced by this function. In every case, `multiplier=1.0` regardless of the actual lot size.

`MarginTracker._calculate_single_exposure` uses `pos.instrument.multiplier` — which is always `1.0` for options.

**Magnitude of error:**

| Instrument | `lot_size` | `multiplier` (actual) | Exposure error factor |
|---|---|---|---|
| NIFTY option | 75 | 1.0 | 75× undercount |
| BANKNIFTY option | 30–35 | 1.0 | 30–35× undercount |
| NSE equity | N/A | 1.0 | Correct |

For a NIFTY option position:
- Correct margin: `50 lots × 75 × ₹100 × 0.2 = ₹75,000`
- MarginTracker margin: `50 lots × 1.0 × ₹100 × 0.2 = ₹1,000`
- The gate sees ₹1,000 consumed where ₹75,000 is actually required.

At `max_capital_utilisation = 0.80` and `cash_balance = ₹10,00,000`: the limit appears to be ₹8,00,000 of margin, but the effective limit is ₹8,00,000 ÷ 75 = ₹10,667 per NIFTY option position. The gate would approve hundreds of option positions before triggering.

The `CanonicalInstrument` computes this correctly:

**Source:** `core/instruments/canonical.py:85-88`

```python
@property
def multiplier(self) -> float:
    return float(self.lot_size)
```

And `NormalizedOrder` carries both instruments:

**Source:** `core/execution/order_models.py:39`

```python
canonical_instrument: Optional[CanonicalInstrument] = field(default=None)
```

**Conclusion:** `order.instrument.multiplier` is the wrong field. `order.canonical_instrument.multiplier` (where `canonical_instrument is not None`) is the correct source for F&O lot size. The MM9.0 specification must be corrected to use `canonical_instrument.multiplier` when available.

The same defect exists in `MarginTracker._calculate_single_exposure` for existing positions, but that is pre-existing and out of MM9.1 scope. MM9.1's incremental estimate must not inherit the same error.

---

### A.4 `metrics.cash_balance`

**Source:** `core/execution/handler.py:87-96`

```python
@dataclass
class ExecutionMetrics:
    cash_balance: float = 100000.0
```

**Source:** `core/execution/handler.py:180-183`

```python
self.metrics = ExecutionMetrics(
    max_equity=initial_capital,
    cash_balance=initial_capital
)
```

**Source:** `core/execution/handler.py:912-921` — update method that is never called

```python
def _update_equity_metrics(self, trade: TradeEvent):
    cost = trade.quantity * trade.price + trade.fees
    if trade.direction == "BUY":
        self.metrics.cash_balance -= cost
    else:
        self.metrics.cash_balance += (trade.quantity * trade.price - trade.fees)
```

**Confirmed:** `cash_balance` field exists. Type `float`. Initialized to `initial_capital`.

**Critical finding: `_update_equity_metrics` is never called.** It is defined but has zero call sites in `process_signal` or `_handle_broker_fill`. `cash_balance` never changes during a session.

**`fno_runner.py:171-177`** constructs the handler with no `initial_capital` argument:

```python
handler_kwargs = dict(
    db_manager=db_manager,
    clock=clock,
    broker=order_broker,
    config=ExecutionConfig(mode=execution_mode),
    load_db_state=True,
)
```

`initial_capital` defaults to `100000.0`. In a real F&O account, `cash_balance` may bear no relationship to the actual account balance.

**Recovery behavior:** `_replay_state()` does not update `cash_balance`. After recovery, `cash_balance` is always `initial_capital` (default ₹1,00,000), regardless of what happened in prior sessions.

**Implication:** `cash_balance` is a static constant, not an accounting measure. Using it as the denominator for utilization means MM9.1 is checking utilization against the hard-coded default, not actual capital. This is an inherent weakness but is acceptable for MM9.1 with documentation, because the error is conservative in most scenarios (actual capital > default → gate over-triggers, which is safe). The error is dangerous only if actual capital is significantly less than the hard-coded default — the drawdown gate is the complementary control for that scenario.

---

### A.5 `order.quantity`

**Source:** `core/execution/order_models.py:77`

```python
object.__setattr__(self, "quantity", int(quantity))
```

**Confirmed:** Field exists. Type `int` (cast in constructor). Available on the built order. No edge cases relevant to the margin gate.

---

## B. Utilization Denominator Review

### B.1 What state actually exists and is updated at runtime

| State | Source | Updated at runtime? | Survives recovery? |
|---|---|---|---|
| `metrics.cash_balance` | `ExecutionMetrics` | Never (`_update_equity_metrics` uncalled) | No (resets to `initial_capital`) |
| `pnl_tracker.get_realized_pnl()` | `PnLTracker._realized_pnl` | Yes — on fills via `_handle_broker_fill` | No — `_replay_state()` replays positions but never calls `pnl_tracker.update()` |
| `pnl_tracker.get_unrealized_pnl(prices)` | Computed from positions + prices | Computed on demand | Implicitly — position state survives replay |
| `metrics.max_equity` | `ExecutionMetrics` | Yes — `update_drawdown()` is called | No (resets to `initial_capital`) |
| `position_tracker._positions` | `PositionTracker` | Yes — on fills | Yes — rebuilt by `_replay_state()` |

### B.2 Recommendation

No repository-native cash measure updates during runtime. The only available denominator is `metrics.cash_balance` = static `initial_capital`.

MTM equity (`cash_balance + unrealized_pnl`) would be more accurate but since `cash_balance` never updates and `pnl_tracker.get_realized_pnl()` does not survive recovery, MTM equity is also not reliable.

**Decision for MM9.1:** Use `metrics.cash_balance` as denominator, with the explicit acknowledgment that it equals the hard-coded `initial_capital` for the entire session. This is conservative (does not become more permissive as capital erodes) but not accurate.

**Risk:** In a drawdown scenario, actual capital shrinks but the denominator does not reflect this. The gate is too permissive for eroded-capital scenarios. The drawdown gate is the intended partial control. They remain independent gates.

**Future fix (MM9.2 or standalone):** `fno_runner.build_runner()` should accept and forward `initial_capital`. `_handle_broker_fill` should call `_update_equity_metrics()`. Neither is MM9.1 scope.

---

## C. Gate Placement Validation — CRITICAL CORRECTION REQUIRED

MM9.0 stated: gate lives between `RiskManager.evaluate(order)` and `broker.place_order(order)`.

The actual `process_signal` execution sequence is:

**Source:** `core/execution/handler.py:648-663`

```python
# Line 648 — PHASE 2: Pre-trade Risk Integration
risk_decision = self.risk_manager.evaluate(
    order, trades_today=self._trades_today, max_trades_per_day=...
)
if not risk_decision.approved:
    self.metrics.rejected_trades += 1           # ← incremented here
    raise ExecutionRuleError(...)

# Line 659 — PHASE 5: Order Lifecycle Registration
self.order_tracker.add_order(order)             # ← ORDER REGISTERED IN TRACKER HERE

# Line 663 — PHASE 7: Broker Execution
broker_id = self.broker.place_order(order)
```

There is an intermediate step — **`order_tracker.add_order(order)` fires between `risk_manager.evaluate()` and `broker.place_order()`**.

**Consequence of placing the margin gate after `add_order()`:**

If `_check_margin_budget()` rejects and `return None` is executed after `order_tracker.add_order()`, the order exists in `self.order_tracker._orders` but has no corresponding broker submission and no fill. This is an orphaned order in the tracker — it will be replayed on the next session as a pending order with no matching fill, corrupting recovered ledger state.

**Correct placement:** Between `risk_manager.evaluate()` (approved) and `order_tracker.add_order()`.

**Corrected gate sequence (for implementation):**

```
risk_manager.evaluate(order)        → approve
↓
_check_margin_budget(order, price)  → approve    ← NEW — must be here
↓
order_tracker.add_order(order)      → register
↓
broker.place_order(order)           → submit
```

This correction also aligns the margin gate with the existing `rejected_trades` pattern: the `risk_manager` rejection at line 654 explicitly increments `rejected_trades` BEFORE adding to the tracker. The margin gate must do the same: increment, log, then return None, before `add_order()`.

---

## D. EXIT Path Validation

**Source:** `core/execution/handler.py:615-623`

```python
if signal.signal_type == SignalType.EXIT:
    if current_position.side == PositionSide.FLAT:
        return None          # ← Already handled: FLAT position, no exit needed

    side = OrderSide.SELL if current_position.side == PositionSide.LONG else OrderSide.BUY
    quantity = current_position.quantity  # ← ALWAYS full position
```

**Finding: only full-position exits exist.** There is no partial exit path in `process_signal`. `quantity` is always `current_position.quantity`. Partial exit is not an edge case to handle.

**Finding: no reverse-and-exit.** An EXIT signal only closes the existing position. A flip requires a separate signal. The position stacking guard (line 537) only applies to non-EXIT signals, and after an EXIT fill, the position becomes FLAT, allowing a new entry on the next signal.

**Finding: no synthetic exits, no grouped exits in process_signal.** `process_group_signal` exists (line 730) but has separate handling that does not call `process_signal`.

**Finding: EXIT bypass is not just safe — it is required for correctness.**

An EXIT BUY (covering a short) would compute `incremental_est = quantity × multiplier × current_price × margin_rate` as a positive addition to used margin. But the true effect is to CLOSE a short position, reducing margin. Applying the margin gate to an EXIT would incorrectly reject position-closing trades. The bypass is architecturally mandatory.

**Gate bypass mechanism:** The bypass must happen at the call site in `process_signal`, not inside `_check_margin_budget`. This follows the pattern of the existing stacking guard (`handler.py:537`): `if signal.signal_type != SignalType.EXIT:`. The method receives an `order`, which has no `signal_type` field; the signal is in scope at the call site.

---

## E. Margin Rejection Semantics

### E.1 Existing return patterns in `process_signal`

| Gate | Rejection mechanism | `rejected_trades`? |
|---|---|---|
| STOP file / kill switch file | `activate_kill_switch()` then `return None` | No |
| Kill switch state | `return None` | No |
| Daily trade limit | `activate_kill_switch()` then `return None` | No |
| Drawdown | `activate_kill_switch()` then `return None` | No |
| Position stacking guard | `return None` | No |
| `_check_risk_limits` | `raise ExecutionRuleError` (via `enforce_risk_clearance`) | No |
| `RiskManager.evaluate` rejection | `self.metrics.rejected_trades += 1` then `raise ExecutionRuleError` | **Yes** |
| Invalid risk types | `return None` | No |
| EXIT on FLAT position | `return None` | No |

**Finding:** `rejected_trades` is only explicitly incremented in one place — the `RiskManager.evaluate` rejection path at line 654. All `return None` paths leave `rejected_trades` unchanged.

**Finding:** `raise ExecutionRuleError` is used for invariant violations. `return None` is used for expected runtime conditions. The behavior difference is significant: `ExecutionRuleError` propagates to any outer exception handler; `return None` is silent.

**Correct mechanism for margin rejection:** `return None`. Margin budget exceeded is an expected runtime condition (portfolio is at capacity). It is not a constitutional violation. It must not raise. It must not kill the session.

**Explicit metric action required:** `self.metrics.rejected_trades += 1` before `return None`. This is NOT automatic. Without it, the Flask dashboard and telemetry will not count margin-rejected signals.

**Logging:** `self.logger.warning(...)` before returning. No journal event. No alerter call. The existing pattern for a single soft rejection is WARNING-level logger only.

---

## F. Recovery / Reconciliation Coupling

### F.1 Position state after replay

**Source:** `core/execution/handler.py:239-241`

```python
fills = self.fill_repo.get_all()
for fill in fills:
    self.order_tracker.process_fill(fill, persist=False)
    self.position_tracker.update_from_fill(fill, persist=False)
```

**Confirmed:** `_replay_state()` correctly rebuilds `position_tracker._positions` from all historical fills. `MarginTracker` holds a reference to `position_tracker` and reads `_positions` on demand. After replay, `get_used_margin(prices)` will count all recovered open positions — subject to the multiplier defect (A.3) and the price-dict scope issue (I.C.3).

### F.2 PnLTracker not restored

`_replay_state()` calls `position_tracker.update_from_fill(fill, persist=False)` but never calls `pnl_tracker.update(fill, realized_pnl)`. The `PnLTracker._realized_pnl` dict is empty after recovery. This is a pre-existing gap. It does not affect the margin gate.

### F.3 cash_balance not restored

`metrics.cash_balance` always resets to `initial_capital` after construction. There is no recovery of cash state. The margin gate denominator is therefore always `initial_capital`, regardless of what prior sessions produced.

### F.4 Reconciliation gate

If reconciliation fails, `abort_startup()` is called and the driver enters STOPPED. `process_signal` is never called. The margin gate cannot fire on an unreconciled ledger. MM9.0's assumption ("gate preconditions guaranteed by startup gate sequence") is confirmed correct.

---

## G. Metrics Impact

### G.1 `signals_received`

**Source:** `core/execution/handler.py:510-511`

```python
self.metrics.signals_received += 1
```

This fires at step 1, before all gates. Margin rejection at the corrected placement (after `risk_manager.evaluate`, before `order_tracker.add_order`) occurs AFTER `signals_received` is already incremented. Correct: the signal was received and processed, even if rejected.

### G.2 `rejected_trades`

NOT incremented automatically by `return None`. Must be explicit. If MM9.1 uses `return None` without explicitly incrementing `rejected_trades`, the metric will be silently wrong.

### G.3 `trades_executed`

Never incremented in `process_signal`. Pre-existing gap. Not a MM9.1 concern.

### G.4 `_persist_metrics()`

Not called on soft `return None` paths. Only called in `activate_kill_switch()`. Margin rejections that increment `rejected_trades` in memory will not be visible to the Flask dashboard until the next persist call. This is a pre-existing observability gap; MM9.1 leaves it as-is.

---

## H. Logging and Journaling

### H.1 Repository precedent

| Event | Logger | Journal | Alerter |
|---|---|---|---|
| Kill switch activated | `WARNING` | Yes (via `_emit`) | `CRITICAL` |
| BrokerAuthError | `ERROR` (via `_journal.record`) | Yes (`BROKER_ERROR`) | None |
| BrokerUnavailableError | Warning (via journal) | Yes (`BROKER_ERROR`) | None |
| RiskManager rejection | Exception propagated | None | None |
| Position stacking guard | None | None | None |
| FLAT exit guard | None | None | None |

### H.2 Decision for MM9.1

Margin rejection is a routine pre-trade condition. It should:
- Log at `WARNING` via `self.logger.warning(...)` — auditable, visible in logs
- Not emit a journal event — journal is for system/lifecycle events
- Not call alerter — alerter is for critical system events (kill switch, broker auth failure)
- Not create a new `EventType` — no new event types required

Log must include: `symbol`, `signal_id`, `utilisation`, `limit`, `used_current`, `incremental`, `cash_balance`. This is sufficient for audit trail without introducing a new event type.

---

## I. Hidden Risks — Classified

### CRITICAL

**I.C.1 — `multiplier=1.0` hardcoded in `canonical_restore.py:68` for all options**

Every option position that has been through the live fill path (`_handle_broker_fill` → G1 Wave 4B → `replace_instrument`) has `instrument.multiplier = 1.0`. `canonical_restore._resolve_option` explicitly passes `multiplier=1.0` regardless of `ci.lot_size`.

`MarginTracker._calculate_single_exposure` uses `pos.instrument.multiplier`. Therefore `get_used_margin()` computes option margin using lot_size=1 instead of the actual lot_size (e.g., 75 for NIFTY). The gate is wrong by a factor of `lot_size` for ALL F&O positions.

This pre-existing defect in `MarginTracker` cannot be silently inherited by MM9.1. The incremental estimate MUST use `order.canonical_instrument.multiplier` (which correctly derives from `lot_size` via the `CanonicalInstrument.multiplier` property at `canonical.py:85-88`).

Note: `get_used_margin()` for existing positions still uses the wrong multiplier. This means the gate correctly measures the cost of the NEW position but underestimates the existing portfolio's margin. This is directionally safe (conservative on what's new) but not accurate on the portfolio total. Full fix requires correcting `MarginTracker._calculate_single_exposure` — that is MM9.2 scope.

**I.C.2 — `order_tracker.add_order()` fires before `broker.place_order()`, between which MM9.0 placed the gate**

Detailed in section C. A margin rejection after `add_order()` orphans the order in the tracker. This corrupts the replayed ledger on next session start. **The gate must be placed before `add_order()`**, not between `add_order()` and `broker.place_order()`.

**I.C.3 — Multi-symbol portfolio margin blindness**

`get_used_margin({signal.symbol: current_price})` iterates `position_tracker._positions` but only prices the positions whose symbol appears in the price dict. With a single-symbol dict, all other open positions contribute zero exposure.

In a multi-symbol portfolio where each symbol has a position:
- 5 symbols open, each consuming 30% of capital in margin
- New signal for symbol F
- `get_used_margin({F: price})` = 0 (no existing F position)
- `incremental_est` = 30% of capital
- Gate sees: `(0 + 30%) / 100% = 30%` — APPROVED
- Actual portfolio margin: 5 × 30% + 30% = 180% — ACCOUNT WIPE

MM9.0 acknowledged this as a "known limitation" acceptable for MM9.1. However, the severity is account-wiping for any deployment that trades more than one symbol simultaneously. This is not a medium risk — it is CRITICAL for multi-symbol F&O operations.

**Requirement:** MM9.1 must explicitly document in code (log on every gate check) that the utilization figure is per-symbol only. The `max_capital_utilisation` default of 0.80 provides NO protection in multi-symbol scenarios. The correct fix (a running price cache per symbol, updated each bar) is MM9.2.

---

### HIGH

**I.H.1 — `cash_balance` is permanently static**

`_update_equity_metrics()` (`handler.py:912-921`) is never called. `cash_balance` is always `initial_capital`. In a losing session, actual capital may be meaningfully lower than `initial_capital`, but the gate's denominator does not reflect this. Acceptable for MM9.1 with documentation.

**I.H.2 — `fno_runner` does not pass `initial_capital` to `ExecutionHandler`**

`fno_runner.py:171-177` constructs `ExecutionHandler` without `initial_capital`. Default is ₹1,00,000. A real F&O account typically has far more capital. This makes `max_capital_utilisation` effectively meaningless without operator configuration. MM9.1 must document: **operators must set `initial_capital` to their actual account capital.** A future slice of `fno_runner` should expose `initial_capital` as a parameter.

**I.H.3 — `if price:` falsy check silently excludes zero-priced positions**

`margin_tracker.py:27`: `if price:` — if any position's price is exactly 0.0, it is excluded from exposure. Could occur for expired options or corrupted market data. Silent exclusion means margin appears lower than it is. Should be `if price is not None:`. Pre-existing `MarginTracker` defect, not MM9.1's to fix.

---

### MEDIUM

**I.M.1 — `rejected_trades` not auto-incremented by `return None`**

Margin gate must explicitly increment `self.metrics.rejected_trades`. Failure to do so will result in the metric being incorrect and the Flask dashboard underreporting rejections. This is a required implementation detail, not automatic.

**I.M.2 — Drawdown check only accounts for current symbol**

**Source:** `core/execution/handler.py:527-528`

```python
total_equity = self.metrics.cash_balance + \
    (self.position_tracker.net_quantity(signal.symbol) * current_price)
```

Same single-symbol limitation as the margin gate. The drawdown check is not a compensating control for the multi-symbol margin blindness — it has the same blindness. Two gates with the same flaw do not cover each other.

**I.M.3 — `_check_risk_limits` called twice for non-mock broker without sl_dist**

`handler.py:479-482` and `handler.py:542-544`. `_check_risk_limits` is called inside the sl_dist/risk_r missing branch for non-mock broker AND again at the regular gate. Pre-existing handler bug. Not MM9.1's concern.

**I.M.4 — PaperBroker fill path does not update `cash_balance`**

`_handle_broker_fill` updates `position_tracker` and `pnl_tracker` but never `metrics.cash_balance`. Consistent with the static cash_balance finding. Paper simulations also use static capital as denominator.

---

### LOW

**I.L.1 — `process_group_signal` bypasses all gates**

`process_group_signal` (line 730) creates and submits orders without any kill switch, drawdown, stacking guard, or margin checks. The margin gate specified for MM9.1 will NOT apply to grouped orders. Pre-existing gap.

**I.L.2 — `PnLTracker` not restored during `_replay_state()`**

Realized PnL history is lost on restart. `pnl_tracker.get_realized_pnl()` returns 0 post-recovery. Does not affect the margin gate but means PnL-based capital measures are not available.

**I.L.3 — `Option.lot_size` correctly set in `canonical_restore.py` but ignored by `MarginTracker`**

`canonical_restore.py:67`: `lot_size=ci.lot_size` is correctly set on the `Option` object. The data is present. `MarginTracker` reads `multiplier` (always 1.0), not `lot_size`. A targeted fix to `_calculate_single_exposure` to prefer `getattr(pos.instrument, 'lot_size', 1)` over `pos.instrument.multiplier` would fix existing position exposure — MM9.2 scope.

---

## J. Deliverables

### J.1 Assumption Validation

| MM9.0 Assumption | Status | Finding |
|---|---|---|
| `margin_tracker.get_used_margin(prices)` exists and is callable | CONFIRMED | Correct signature; callable |
| `margin_tracker.margin_rate` exists and is readable | CONFIRMED | float, always 0.2, not config-wired |
| `metrics.cash_balance` tracks current capital | **WRONG** | Never updated; always equals `initial_capital` |
| `order.instrument.multiplier` gives lot size for F&O | **WRONG** | Hardcoded 1.0 for options via `canonical_restore.py:68` |
| `order.quantity` is finalized after order creation | CONFIRMED | int, correct |
| Gate placement: after `risk_manager.evaluate`, before `broker.place_order` | **INCOMPLETE** | `order_tracker.add_order()` is between those two; gate must precede it |
| EXIT bypass is safe | CONFIRMED + STRENGTHENED | Required, not optional; EXIT BUY for short would add phantom margin |
| `return None` is the correct rejection mechanism | CONFIRMED | Consistent with stacking guard, kill switch paths |
| Recovery automatically feeds margin gate inputs | **PARTIALLY** | Positions rebuilt correctly; multiplier still wrong for options; cash not restored |
| Drawdown and margin are independent gates | CONFIRMED | Different triggers, different consequences |

---

### J.2 Hidden Couplings

1. **`MarginTracker._calculate_single_exposure` ↔ `Option.multiplier=1.0`**: The tracker reads a field that is always hardcoded wrong for options. Any usage of `get_used_margin()` for F&O is quietly returning 1/lot_size of the true exposure.

2. **`metrics.cash_balance` ↔ `initial_capital` parameter**: `cash_balance` is a proxy for `initial_capital`, not for actual capital. Any denominator logic is actually a function of construction-time parameter, not runtime state.

3. **Gate position ↔ `order_tracker.add_order()`**: The handler adds the order to the tracker BEFORE broker submission. A post-`add_order()` rejection corrupts the tracker state. This coupling is not documented in the handler and would be an easy implementation error.

4. **Price dict scope ↔ `position_tracker._positions`**: `get_exposure()` iterates ALL positions but prices only those in the dict. Single-symbol price dict = single-symbol gate, regardless of portfolio breadth.

5. **`rejected_trades` ↔ `raise ExecutionRuleError` (not `return None`)**: Only the `ExecutionRuleError` path increments `rejected_trades`. All `return None` paths leave it unchanged. Metric accuracy requires explicit increment.

---

### J.3 Runtime Flow Analysis — Corrected

```
process_signal(signal, current_price):
  │
  ├── [PHASE 0] Authority enforcement (re-entry guard)
  ├── [PHASE 0] Idempotency enforcement + registry lock
  ├── [TLP]    Risk metadata validation (sl_dist, risk_r)
  │    └── For non-mock broker, missing metadata: _check_risk_limits called HERE (pre-existing bug)
  ├── [0]  STOP file / kill switch file check
  ├── [1]  signals_received += 1   ← ALREADY FIRED before margin gate
  ├── [2]  Kill switch state check → return None
  ├── [3]  Daily trade limit → activate_kill_switch + return None
  ├── [4]  Drawdown check (single-symbol equity) → activate_kill_switch + return None
  ├── [4b] Position stacking guard (non-EXIT only) → return None
  ├── [5]  _check_risk_limits → enforce_risk_clearance (raises if false)
  ├── [9C] _check_greek_limits (single-order, not portfolio, no live caller)
  ├── [TLP] Capture structural context
  ├── [PHASE 1] Instrument resolution → canonical_instrument (CanonicalInstrument or None)
  ├── [PHASE 1] Quantity and side determination
  ├── [PHASE 1] NormalizedOrder construction
  │             order.instrument.multiplier = 1.0 for options (canonical_restore.py:68)
  │             order.canonical_instrument.multiplier = lot_size (canonical.py:87)
  │
  ├── [PHASE 2] risk_manager.evaluate(order) → rejected_trades += 1 + raise ExecutionRuleError
  │
  ├── [NEW MM9.1] ← GATE MUST BE PLACED HERE (BEFORE add_order)
  │    if signal.signal_type != SignalType.EXIT:
  │        _check_margin_budget(order, current_price)
  │            → rejected_trades += 1 + logger.warning + return None
  │
  ├── [PHASE 5] order_tracker.add_order(order)  ← ORDER ENTERS TRACKER
  │
  ├── [PHASE 7] broker.place_order(order)
  │    ├── PaperBroker: _handle_broker_fill inline → return order
  │    ├── BrokerAuthError → activate_kill_switch + return None
  │    ├── BrokerUnavailableError → threshold check → return None
  │    └── Success → return order
  └── Returns order or None
```

---

### J.4 Metrics Impact Analysis

| Metric | At margin rejection | Notes |
|---|---|---|
| `signals_received` | Already incremented (step 1) | Correct — signal was received |
| `rejected_trades` | NOT auto-incremented | **Must be explicitly incremented before `return None`** |
| `trades_executed` | Not changed | Correct — trade was not executed |
| `max_equity` / `max_drawdown_pct` | Not changed | Correct — no equity event |
| `_trades_today` | Not changed | Correct — trade was not executed |

---

### J.5 Risk Classification Summary

| ID | Finding | Severity |
|---|---|---|
| I.C.1 | `multiplier=1.0` hardcoded for options in `canonical_restore.py:68` — gate wrong by factor of `lot_size` | CRITICAL |
| I.C.2 | Gate placement after `order_tracker.add_order()` orphans orders on rejection | CRITICAL |
| I.C.3 | Single-symbol price dict makes gate blind to multi-symbol portfolio margin | CRITICAL |
| I.H.1 | `cash_balance` never updated — denominator is permanently `initial_capital` | HIGH |
| I.H.2 | `fno_runner` does not pass `initial_capital` — gate runs against ₹1,00,000 default | HIGH |
| I.H.3 | `if price:` silently excludes zero-priced positions from exposure | HIGH |
| I.M.1 | `rejected_trades` not auto-incremented by `return None` | MEDIUM |
| I.M.2 | Drawdown check has same single-symbol blindness — no compensation | MEDIUM |
| I.M.3 | `_check_risk_limits` called twice in same signal flow | MEDIUM |
| I.M.4 | PaperBroker fills do not update `cash_balance` | MEDIUM |
| I.L.1 | `process_group_signal` bypasses all gates including margin | LOW |
| I.L.2 | `PnLTracker` not restored during `_replay_state()` | LOW |
| I.L.3 | `Option.lot_size` correctly set but ignored by `MarginTracker` | LOW (pre-existing) |

---

### J.6 Corrected MM9.1 Behavioral Contract

**Gate identity:** `_check_margin_budget(order: NormalizedOrder, current_price: float) -> bool`

**Call site:** In `process_signal`, AFTER `risk_manager.evaluate(order)` is approved, BEFORE `order_tracker.add_order(order)`. Called only when `signal.signal_type != SignalType.EXIT`.

**Formula:**

```
prices_for_check     = {order.symbol: current_price}
used_margin_current  = margin_tracker.get_used_margin(prices_for_check)
                       [Note: underestimates existing option positions due to I.C.1;
                        underestimates other-symbol positions due to I.C.3;
                        both are documented known limitations of MM9.1]

effective_multiplier = order.canonical_instrument.multiplier
                       if order.canonical_instrument is not None
                       else order.instrument.multiplier

incremental_est      = order.quantity × effective_multiplier × current_price
                       × margin_tracker.margin_rate

used_after           = used_margin_current + incremental_est
utilisation          = used_after / metrics.cash_balance
                       [cash_balance = static initial_capital — see B.2]

if metrics.cash_balance <= 0: return True   [degenerate denominator guard]
if utilisation > config.max_capital_utilisation: return False
return True
```

**Rejection path in `process_signal`:**

```
if signal.signal_type != SignalType.EXIT:
    if not self._check_margin_budget(order, current_price):
        self.metrics.rejected_trades += 1
        self.logger.warning(
            f"MARGIN_BUDGET_REJECTED symbol={order.symbol} "
            f"utilisation={utilisation:.2%} limit={config.max_capital_utilisation:.2%} "
            f"[single-symbol check only — other open positions not priced]"
        )
        return None
# [order_tracker.add_order(order) follows here]
```

**Config addition:**

```
@dataclass
class ExecutionConfig:
    ...existing fields...
    max_capital_utilisation: float = 0.80
```

**Documented limitations for MM9.1:**

1. `used_margin_current` only prices positions in `{signal.symbol: current_price}`. In a multi-symbol portfolio, other symbols contribute zero. This is a per-symbol gate, not a portfolio gate. Effective only for single-symbol deployments or as the first gate in a future multi-gate sequence.
2. `used_margin_current` for option positions uses `multiplier=1.0` from existing position instruments (pre-existing `MarginTracker` defect). Option exposure from existing positions is underestimated by a factor of `lot_size`.
3. `metrics.cash_balance` is static (`initial_capital`) and does not reflect realized PnL or capital erosion. Operators must set `initial_capital` to their actual account capital.
4. The gate does not apply to orders created via `process_group_signal`.

---

### J.7 Corrected MM9.1 Implementation Slices

**Slice 1 — `ExecutionConfig` field addition:**
Add `max_capital_utilisation: float = 0.80` to `ExecutionConfig` dataclass in `handler.py:68-83`. This is the only change to `ExecutionConfig`.

**Slice 2 — `_check_margin_budget` private method:**
New method on `ExecutionHandler`. Accepts `NormalizedOrder` and `float` (current price). Returns `bool`. Uses `canonical_instrument.multiplier` when available (F&O), falls back to `instrument.multiplier` (equity). Guards against `cash_balance <= 0`. Does NOT increment metrics or log — caller does. Returns `True` to approve, `False` to reject.

**Slice 3 — Call site in `process_signal`:**
Between the approved `risk_decision` branch (line ~656) and `order_tracker.add_order(order)` (line 659). Guard is `signal.signal_type != SignalType.EXIT`. On `False` return: increment `rejected_trades`, log warning at WARNING level, `return None`. Order does NOT enter the tracker.

**Slice 4 — PaperBroker path verification:**
`handler.py:668-693`: the PaperBroker special case is inside the `try` block that begins at broker execution, which is AFTER `order_tracker.add_order()`. The margin gate at the corrected placement (before `add_order()`) fires BEFORE the PaperBroker branch. The gate must be tested with PaperBroker in the injection chain to confirm it rejects without reaching `add_order()`.

---

### J.8 Updated Testing Strategy

**Priority 1 — Must pass before merge:**

- **Rejection path, no tracker entry:** Signal where `utilisation >= max_capital_utilisation` → returns `None`. `rejected_trades` incremented by 1. Order NOT in `order_tracker`. No kill switch. Session continues.
- **Approval path, order registered:** Signal where `utilisation < max_capital_utilisation` → returns `NormalizedOrder`. Order IS in `order_tracker`. `rejected_trades` unchanged.
- **EXIT bypass:** EXIT signal against existing LONG position → `_check_margin_budget` NOT called. Order proceeds. `rejected_trades` unchanged.
- **`rejected_trades` explicit increment:** Counter changes by exactly 1 on rejection. Does not change on approval or EXIT.
- **Canonical instrument multiplier (F&O):** `canonical_instrument.lot_size = 75` → `effective_multiplier = 75.0`. Incremental estimate uses 75, not 1.0.
- **No canonical instrument (equity):** `canonical_instrument = None` → `effective_multiplier = 1.0`. Correct for equities.
- **Tracker integrity:** After margin rejection, `order_tracker.get_order(order.correlation_id)` raises or returns None — order was never registered.

**Priority 2 — Regression (existing gate chain must not break):**

- All kill switch, drawdown, stacking guard, and `_check_risk_limits` tests continue to pass — gates remain independent.
- RiskManager rejection tests continue to pass — gate ordering unchanged (margin comes after risk_manager).
- PaperBroker fill path tests: a margin-approved signal with PaperBroker reaches the fill callback correctly.
- Recovery path: replay fills, then send a new signal. `get_used_margin` reflects recovered positions. Gate fires correctly.

**Known limitation test (must be documented, not fixed):**

- Multi-symbol blindness: three symbols open (A, B, C), each consuming 40% margin. New signal for D. Gate sees `used_current = 0` (D has no position), `incremental = 40%`. Utilisation = 40% < 80% → APPROVED despite 160% actual portfolio utilisation. Test must confirm this behavior and its log output. It is the documented MM9.1 limitation.

---

### J.9 Final Readiness Verdict

**MM9.1 as specified in MM9.0 is NOT implementation-ready.**

Three CRITICAL corrections are required:

**Correction C1 — Gate placement:**
Gate must be placed BEFORE `order_tracker.add_order()`, not just "before `broker.place_order()`". The existing code has `add_order()` between risk evaluation and broker submission (`handler.py:659`). A rejection after `add_order()` orphans the order in the tracker and corrupts recovery.

**Correction C2 — Multiplier source:**
Gate must use `order.canonical_instrument.multiplier` (when `canonical_instrument is not None`) for the incremental estimate. `order.instrument.multiplier` is hardcoded to `1.0` for all options by `canonical_restore.py:68`. Using it makes the F&O gate wrong by a factor of `lot_size`.

**Correction C3 — Multi-symbol scope documentation:**
MM9.1 must carry an explicit operator warning in code, documentation, and tests: the gate is a per-symbol gate, not a portfolio gate. The multi-symbol exposure underestimation means `max_capital_utilisation=0.80` provides no portfolio-level protection when trading multiple symbols simultaneously. This must be visible in every margin-check log entry.

With C1, C2, and C3 incorporated, MM9.1 can proceed. The remaining findings (static `cash_balance`, pre-existing `MarginTracker` multiplier defect for existing positions, `_update_equity_metrics` uncalled, `fno_runner` missing `initial_capital` propagation) are acceptable known limitations for MM9.1 and are backlog items for MM9.2.

**Ready to implement:** Yes, after incorporating C1, C2, and C3.
