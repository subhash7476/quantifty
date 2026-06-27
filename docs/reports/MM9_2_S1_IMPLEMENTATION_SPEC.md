# MM9.2-S1 — Multi-Symbol Margin Accounting (C3 Removal)
## Implementation Specification

**Date:** 2026-06-27
**Status:** Architecture-only — do NOT implement code until this document is accepted.
**Prerequisite:** MM9.1 complete (HEAD cfbe62a, 600 tests passing).

---

## 0. Scope Resolution — What "C3 Removal" Actually Requires

The MM9 plan describes MM9.2-S1 as "per-symbol price cache" in three lines. This specification rejects that framing as insufficient.

C3 is defined as:

> `get_used_margin({signal.symbol: current_price})` with a single-symbol price dict — all other open symbols contribute zero exposure. In a 5-symbol portfolio each at 40% utilisation, the gate approves a new order while actual portfolio utilisation is 240%.

Removing C3 requires the gate to observe **correct** portfolio margin across all open symbols. Passing a full price cache to `get_used_margin()` is necessary but not sufficient, because `MarginTracker._calculate_single_exposure` uses `pos.instrument.multiplier`, which `canonical_restore.py:68` hardcodes to `1.0` for every restored option position. Passing correct prices into an incorrect multiplier produces a gate that prices all option legs at `qty × 1.0 × price × rate` instead of `qty × lot_size × price × rate` — undercounting NIFTY by 75× and BANKNIFTY by 30–35×.

**Decision D-S1-1:** The multiplier fix and zero-price falsy guard (plan's MM9.2-S2) are sequenced as a mandatory immediately-following slice. MM9.2-S1 establishes the price cache and wires it in. MM9.2-S2 immediately repairs the multiplier so the full portfolio exposure is computed correctly. Either alone is insufficient. The implementor MUST treat MM9.2-S1 and MM9.2-S2 as a tightly coupled deployment pair. An intermediate state where MM9.2-S1 has merged but MM9.2-S2 has not is hazardous.

---

## 1. Current Implementation Review

### 1.1 Where Used Margin Is Computed

**`MarginTracker.get_used_margin(current_prices: Dict[str, float]) → float`**
File: `core/execution/margin_tracker.py:37–39`

```python
def get_used_margin(self, current_prices: Dict[str, float]) -> float:
    return self.get_exposure(current_prices) * self.margin_rate
```

Delegates to `get_exposure()` (lines 19–28):

```python
def get_exposure(self, current_prices: Dict[str, float], symbol: Optional[str] = None) -> float:
    if symbol:
        return self._calculate_single_exposure(symbol, current_prices.get(symbol))
    total_exposure = 0.0
    for sym in self.position_tracker._positions:
        price = current_prices.get(sym)
        if price:
            total_exposure += self._calculate_single_exposure(sym, price)
    return total_exposure
```

`get_exposure()` iterates all positions in `position_tracker._positions` and calls `current_prices.get(sym)` for each. Any symbol absent from `current_prices` returns `None`; the `if price:` guard skips it. The result: only symbols present in the caller-supplied dict contribute to exposure.

**`MarginTracker._calculate_single_exposure(symbol, current_price) → float`**
File: `core/execution/margin_tracker.py:31–35`

```python
def _calculate_single_exposure(self, symbol: str, current_price: Optional[float]) -> float:
    if current_price is None:
        return 0.0
    pos = self.position_tracker.get_position(symbol)
    return pos.quantity * current_price * pos.instrument.multiplier
```

Uses `pos.instrument.multiplier`. For positions restored via G1 Wave 4B/3 (live restart), `canonical_restore.py:68` sets `multiplier=1.0` for all option positions. Option exposure is therefore underestimated by a factor of `lot_size` (75× for NIFTY, 30–35× for BANKNIFTY). This is the MM9.2-S2 defect, exposed only once a full price cache is passed.

### 1.2 Where Incremental Margin Is Computed

**`ExecutionHandler._check_margin_budget(order, current_price) → tuple[bool, float]`**
File: `core/execution/handler.py:930–949`

```python
def _check_margin_budget(self, order: NormalizedOrder, current_price: float) -> tuple[bool, float]:
    if self.metrics.cash_balance <= 0:
        return True, 0.0
    effective_multiplier = (
        order.canonical_instrument.multiplier
        if order.canonical_instrument is not None
        else order.instrument.multiplier
    )
    used_current = self.margin_tracker.get_used_margin({order.symbol: current_price})   # ← C3
    incremental_est = (
        self._estimate_required_margin(order.quantity * effective_multiplier, current_price)
        * self.margin_tracker.margin_rate
    )
    utilisation = (used_current + incremental_est) / self.metrics.cash_balance
    return utilisation <= self.config.max_capital_utilisation, utilisation
```

The problem is the argument `{order.symbol: current_price}` — a single-entry dict. `MarginTracker.get_exposure()` iterates all positions but only finds a price for the one symbol in this dict. All other held symbols contribute 0.0 to `used_current`.

### 1.3 Where Utilisation Is Computed

Utilisation is computed inline in `_check_margin_budget`:

```python
utilisation = (used_current + incremental_est) / self.metrics.cash_balance
```

`cash_balance` is the denominator. It is set to `initial_capital` at construction and **never updated during a session** (pre-existing defect I.H.1, addressed by MM9.2-S4; out of MM9.2-S1 scope).

### 1.4 Precisely Why the Gate Is Single-Symbol Aware

`_check_margin_budget` receives only `current_price: float` for the signal's symbol. No mechanism exists in the current handler to recall last-seen prices for any other symbol. The gate constructs the price dict `{order.symbol: current_price}` from whatever scalar it was passed. Other symbols in `position_tracker._positions` are priced at zero — not because they are flat, but because no price was ever recorded for them.

This is a **caller-side data starvation problem**, not a MarginTracker design problem. MarginTracker already iterates all positions correctly — it simply has no prices to use for them.

### 1.5 Call Site for the Gate

File: `core/execution/handler.py:662–676`

```python
if signal.signal_type != SignalType.EXIT:
    approved, utilisation = self._check_margin_budget(order, current_price)
    if not approved:
        self.metrics.rejected_trades += 1
        self.logger.warning(
            "MARGIN_BUDGET_REJECTED symbol=%s signal_id=%s utilisation=%.2f%% "
            "limit=%.2f%% [C3: single-symbol gate only — other open positions not priced]",
            ...
        )
        return None
```

EXIT signals bypass unconditionally. The C3 disclosure in the log format must be removed after MM9.2-S1.

---

## 2. Design Alternatives

### Architecture A — Handler-Owned Price Cache (Stateless MarginTracker)

Maintain `_latest_prices: Dict[str, float]` as an instance attribute on `ExecutionHandler`. Update it at the start of `process_signal` with `_latest_prices[signal.symbol] = current_price`. Pass `self._latest_prices` to `get_used_margin()`. MarginTracker remains a stateless computation object — its signature does not change.

| Dimension | Assessment |
|---|---|
| Complexity | Minimal: one dict attr, one assignment, one arg change |
| Determinism | Fully deterministic — prices reflect exact `bar.close` values from LoopDriver |
| Correctness | Prices are live-bar marks; stale for non-signaling symbols (documented in §8 R3) |
| Performance | O(N) over open positions — identical asymptotic to current |
| Maintainability | Dict on handler is consistent with `metrics.cash_balance` and `position_tracker` already owned there |
| Recovery | Cache is empty after restart; warms as bars arrive (§5) |
| SPAN seam | `MarginCalculator.get_used_margin(prices: Dict[str, float])` in MM9.4 is stateless — handler feeds prices, calculator consumes them. Cache stays in handler. No protocol change needed when SPAN replaces MarginTracker. |

**Verdict: Recommended.**

### Architecture B — Running Margin Aggregate

Maintain a scalar `_used_margin_running: float` in `ExecutionHandler`. Increment on fill entry, decrement on fill exit.

| Dimension | Assessment |
|---|---|
| Complexity | Moderate: fill-time accounting in `_handle_broker_fill` |
| Determinism | Breaks under price drift: a short entered at 22,500 marked at 23,000 has more margin requirement; running total does not update until the next fill |
| Correctness | Tracks entry-margin, not current-margin — fundamentally wrong |
| Recovery | Must rebuild from all historical fills on restart — same work as calling `get_used_margin(prices)` but more complex and error-prone |
| ADR-001 | Creates a second source of margin truth alongside PositionTracker — violation |
| SPAN seam | Breaks entirely: SPAN computes scenario-based margin, not a scalar that increments on fill |

**Verdict: Rejected.** No compensating benefit; introduces drift, ADR-001 violation, and breaks SPAN.

### Architecture C — MarginTracker-Owned Price Cache

Add `self._last_prices: Dict[str, float]` to `MarginTracker` with a `record_price(symbol, price)` mutator. Handler calls `self.margin_tracker.record_price(...)` at signal intake.

| Dimension | Assessment |
|---|---|
| Complexity | Same data footprint as A; adds a mutator and internal cache to MarginTracker |
| Determinism | Same as A |
| Correctness | Same as A |
| SPAN seam | The `MarginCalculator` protocol in MM9.4 is intentionally stateless (`get_used_margin(prices: Dict[str, float]) → float`). If MarginTracker owns the cache, the protocol inherits a stateful `record_price()` mutator — which the SPAN calculator does not need and should not have. The handler-owned cache keeps the SPAN boundary clean |

**Verdict: Rejected.** Correct in the short term but pollutes the MM9.4 SPAN seam. Architecture A is strictly simpler with no downside.

### Tiebreaker

The SPAN seam (MM9.4-S1) settles the Architecture A vs C question. The handler feeds prices to any `MarginCalculator`; the calculator never owns a cache. Architecture A is the correct long-term boundary.

---

## 3. Data Requirements

### 3.1 Required Data Items

| Data Item | Purpose | Canonical Source |
|---|---|---|
| `signal.symbol` | Key into price cache and position lookup | `process_signal(signal, current_price)` parameter |
| `current_price` | Latest close for the signal's symbol | `bar.close` forwarded by LoopDriver |
| `self._latest_prices: Dict[str, float]` | Running cache of most recent price for each symbol seen | `ExecutionHandler._latest_prices` (new) |
| `position_tracker._positions` | All open positions (symbols, quantities, instruments) | `PositionTracker._positions` |
| `pos.instrument.multiplier` | Contract multiplier for exposure (defective for options — MM9.2-S2) | `Position.instrument.multiplier` |
| `order.canonical_instrument.multiplier` | Correct lot-size for F&O incremental estimate | `NormalizedOrder.canonical_instrument.multiplier` |
| `margin_tracker.margin_rate` | Flat margin rate applied to gross exposure | `MarginTracker.margin_rate` (default 0.20) |
| `metrics.cash_balance` | Gate denominator | `ExecutionMetrics.cash_balance` (defect I.H.1 fixed in MM9.2-S4) |
| `config.max_capital_utilisation` | Utilisation limit | `ExecutionConfig.max_capital_utilisation` (default 0.80) |

### 3.2 What Is NOT Required

- **Entry price (`pos.avg_price`)** — margin is computed from current mark-to-market, not cost basis. Avg price is for PnL computation, not margin.
- **Order fill price** — incremental estimate uses `current_price` (bar.close), consistent with MM9.1-S2.
- **Volume, OI, or analytics data** — margin approximation is flat-rate × exposure.
- **Broker margin API response** — approximated as margin_rate × notional.

### 3.3 Price Cache Update Scope

The cache updates **per signal**, not per bar. The LoopDriver calls `process_signal(signal, bar.close)` only when a strategy emits a signal for a symbol. A symbol that has not signaled recently will have a stale price in the cache.

An alternative is a `update_market_price(symbol, price)` hook on the handler called by the LoopDriver every bar. This would provide bar-fresh prices for all symbols. However:

- It requires a LoopDriver change (the driver currently knows nothing about handler's price cache, and §5.4 of the Driver Specification states the seam holds no handler handle).
- In practice, the universe is small (2–5 underlyings) and bars arrive within the same tick, so intra-tick staleness is bounded by universe size, not wall clock time.

**Decision D-S1-2:** Signal-only cache update for MM9.2-S1. Staleness is documented as a named residual limitation (§8 R3). A per-bar update hook is noted as a future improvement but is NOT part of this slice.

---

## 4. Algorithm

All pseudocode below is specification-level. The exact Python expression for each step must respect the surrounding contracts described in §6.

### 4.1 Cache Update

```
PROCEDURE update_price_cache(symbol: str, current_price: float):
    self._latest_prices[symbol] = current_price
```

Called at the **start** of `process_signal`, before any gate or order construction, so the most recent price for the signal's symbol is always in the cache by the time the margin gate runs.

### 4.2 used_margin(prices) — existing in MarginTracker, called with full cache

```
PROCEDURE used_margin(prices: Dict[str, float]) -> float:
    total = 0.0
    FOR sym IN position_tracker._positions:
        price = prices.get(sym)
        IF price IS NOT None AND price > 0:    # (after MM9.2-S2: 'price is not None' only)
            pos = position_tracker.get_position(sym)
            multiplier = pos.instrument.multiplier   # (after MM9.2-S2: use lot_size lookup)
            total += pos.quantity * price * multiplier
    RETURN total * margin_rate
```

Note: The `if price:` guard in the current implementation silently drops zero-priced legs. After MM9.2-S2 this becomes `if price is not None:`. This matters for options quoted near zero.

### 4.3 incremental_margin(order, current_price) — in _check_margin_budget

```
PROCEDURE incremental_margin(order, current_price: float) -> float:
    IF order.canonical_instrument IS NOT None:
        effective_multiplier = order.canonical_instrument.multiplier   # lot_size (correct)
    ELSE:
        effective_multiplier = order.instrument.multiplier             # 1.0 for equity (correct)
    notional = order.quantity * effective_multiplier * current_price
    RETURN notional * margin_tracker.margin_rate
```

No change from MM9.1. The incremental formula was corrected in MM9.1-S2.

### 4.4 total_required_margin(order, current_price, full_price_cache) — gate perspective

```
PROCEDURE total_required_margin(order, current_price: float, full_price_cache: Dict) -> float:
    used = margin_tracker.get_used_margin(full_price_cache)   # ← MM9.2-S1 change
    incremental = incremental_margin(order, current_price)
    RETURN used + incremental
```

`full_price_cache` = `self._latest_prices` (already updated with the current signal's price at signal intake).

### 4.5 utilisation(order, current_price, full_price_cache) — gate formula

```
PROCEDURE utilisation(order, current_price: float, full_price_cache: Dict) -> float:
    IF metrics.cash_balance <= 0:
        RETURN 0.0                  # degenerate guard; do not block
    total_req = total_required_margin(order, current_price, full_price_cache)
    RETURN total_req / metrics.cash_balance

PROCEDURE check_margin_budget(order, current_price: float) -> (bool, float):
    u = utilisation(order, current_price, self._latest_prices)
    RETURN (u <= config.max_capital_utilisation, u)
```

### 4.6 Boundary Conditions

| Scenario | Behaviour |
|---|---|
| **No positions (empty portfolio)** | `position_tracker._positions` is empty. `used_margin()` = 0.0. `utilisation` = `incremental_only / cash_balance`. Gate approves if below limit. |
| **Multiple instruments, all priced in cache** | `used_margin` sums all. `total_required_margin` = portfolio margin + new order margin. Correct. |
| **Multiple instruments, some not in cache** | Symbols absent from `_latest_prices` are skipped in `get_exposure`. Partial portfolio pricing — residual form of C3 during cold start. Documented in §8 R2. |
| **Long positions only** | `pos.quantity > 0`, `pos.side == LONG`. Exposure = `qty × price × multiplier`. Margin = `exposure × rate`. Correct. |
| **Short positions only** | `pos.quantity > 0`, `pos.side == SHORT`. `_calculate_single_exposure` uses `pos.quantity` (absolute). Short positions consume margin identically. Correct. |
| **Mixed long + short (different symbols)** | Summed independently. No netting across symbols. Conservative. |
| **EXIT signal** | Bypass unconditionally — EXIT does not enter `_check_margin_budget`. Cache is still updated at signal intake so the price remains warm for subsequent entry signals. |
| **Partial exit** | Not implemented in the platform. If introduced, `position_tracker.update_from_fill` would reduce `pos.quantity`; `used_margin` would automatically reflect the reduced exposure on the next call. No change to the gate formula needed. |
| **Reversal (flip)** | A flip goes through EXIT (bypasses gate) + new entry (goes through gate against the now-reduced/zero position). Correct. |
| **Zero quantity in positions dict** | `pos.quantity == 0.0` means FLAT. PositionTracker stores FLAT positions when explicitly set (e.g., forced flatten). Zero quantity contributes zero exposure. Safe. |
| **Missing price for held symbol** | `prices.get(sym)` returns `None`. Symbol skipped. Conservative error (understates `used_margin`, never overstates). Documented as named residual. |
| **Degenerate denominator (`cash_balance <= 0`)** | Guard returns `(True, 0.0)`. No ZeroDivisionError. Matches MM9.1 behaviour. |
| **Incremental price == 0.0** | `incremental_margin` = 0.0. Gate computes `used / cash_balance`. No division-by-zero risk (denominator is `cash_balance`, not price). |

### 4.7 Non-Double-Counting Dependency

The formula `used_margin(all positions) + incremental(new order)` is non-double-counting only because the position-stacking guard (handler.py:539–541) prevents the signal's symbol from already being open for non-EXIT signals. If the stacking guard were ever relaxed (e.g., position pyramiding), the gate would double-count the new order's symbol: once from `used_margin` (the existing position) and once from `incremental_margin` (the additional order).

**Mitigation:** A comment in `_check_margin_budget` must note this dependency on the stacking guard.

---

## 5. Recovery Behaviour

### 5.1 Position State After Restart

`ExecutionHandler._replay_state()` (handler.py:228–274) rebuilds `PositionTracker` from all fills in persistence before `process_signal` is ever called. After replay, `position_tracker._positions` accurately reflects all open positions.

This means the **quantity** side of `used_margin` is recovery-safe: positions are correct. The **price** side is not: `_latest_prices` is in-memory and starts empty on every restart.

### 5.2 The Cold-Start Gap

At startup, `_latest_prices = {}`. On the first signal for symbol A, the cache gets `{A: price_A}`. `get_used_margin({"A": price_A})` is called. Open positions in symbols B, C, D are correctly tracked by PositionTracker but have no price in the cache — they contribute 0.0 to `used_margin`. The gate transiently re-exhibits the C3 undercount until all held symbols have received at least one live bar and signaled.

### 5.3 Should the Cache Be Seeded From the Ledger?

No. The canonical source for current prices is live market data (`bar.close` forwarded by LoopDriver). The ledger records fill prices (entry prices) and realized PnL, not current marks. Seeding `_latest_prices["B"] = pos.avg_price` would make the gate compute margin using the **entry price** from days or weeks ago — which may be materially different from the current market price. This would produce false accuracy while using stale data.

**Decision D-S1-3:** Do not seed `_latest_prices` from the ledger at startup.

### 5.4 Warmup Duration

For a 3-symbol universe (NIFTY, BANKNIFTY, FINNIFTY), all three are typically priced within the first tick cycle (bars arrive in symbol order per the driver config). By the time the strategy can generate a signal after warmup, the cache is warm. For held positions whose symbol is no longer in the active universe, the price will never arrive. The gate silently skips these. This is the correct conservative behaviour.

**Decision D-S1-4:** The cold-start gap is accepted as a bounded known limitation (at most one tick cycle per restart). Log a WARNING at startup noting `_latest_prices` is empty and will warm on first bars.

### 5.5 Should the Cache Be Persisted?

No. Restoring `_latest_prices["NIFTY"] = 22300.0` from yesterday's last bar would price today's position at yesterday's close until the first live bar arrives. The cold-start gap (at most one tick cycle) is safer than stale-data injection.

---

## 6. Interaction With Existing MM9 Code

### 6.1 ExecutionHandler (`core/execution/handler.py`)

**Changes required (4 surgical edits):**

**Edit 1 — `__init__`**: After `self.metrics = ExecutionMetrics(...)` initialization, add:
```python
self._latest_prices: Dict[str, float] = {}
```

**Edit 2 — `process_signal`**: At the very start of the try block (before any gate, order construction, or signal routing), add:
```python
self._latest_prices[signal.symbol] = current_price
```

**Edit 3 — `_check_margin_budget`**: Change the argument to `get_used_margin` from the single-entry dict to the full cache:
```python
# Before (MM9.1):
used_current = self.margin_tracker.get_used_margin({order.symbol: current_price})
# After (MM9.2-S1):
used_current = self.margin_tracker.get_used_margin(self._latest_prices)
```

**Edit 4 — WARNING log format** in `process_signal` (line ~671): Remove the C3 disclosure phrase from the rejection log, as C3 is resolved:
```python
# Before:
# "MARGIN_BUDGET_REJECTED ... [C3: single-symbol gate only — other open positions not priced]"
# After:
"MARGIN_BUDGET_REJECTED symbol=%s signal_id=%s utilisation=%.2f%% limit=%.2f%%"
```

**Unchanged in this slice:**
- The gate formula itself (`_check_margin_budget`): structurally identical.
- `_estimate_required_margin`: unchanged helper.
- Incremental computation: multiplier sourcing already correct from MM9.1.
- All other gates: kill switch, drawdown, stacking guard, risk manager, Greek limits.
- `_replay_state`: unchanged — PositionTracker recovery is correct.
- `_handle_broker_fill`: unchanged (cash_balance update is MM9.2-S4).
- `get_stats()`: the `margin_tracker.get_used_margin(current_prices)` call at line ~982 already receives a multi-symbol dict in the telemetry context. No change needed.

### 6.2 MarginTracker (`core/execution/margin_tracker.py`)

**No changes in MM9.2-S1.** The multiplier defect and `if price:` falsy guard are deferred to MM9.2-S2. The `get_used_margin()` interface signature remains `(current_prices: Dict[str, float]) → float` — exactly what Architecture A passes. No protocol change needed.

**Changes deferred to MM9.2-S2** (must follow S1 immediately):
- `_calculate_single_exposure`: replace `pos.instrument.multiplier` with lot_size lookup.
- `if price:` guard: replace with `if price is not None:`.

### 6.3 PositionTracker (`core/execution/position_tracker.py`)

**Unchanged.** `update_from_fill` correctly maintains `_positions` through entry, reduction, flip, and close. `get_all_positions()` provides the full ledger. No changes to how positions are stored or recovered.

### 6.4 ExecutionMetrics (`core/execution/handler.py` dataclass)

**Unchanged in this slice.** `cash_balance` static denominator is pre-existing defect I.H.1, addressed by MM9.2-S4. Adding `_latest_prices` to `ExecutionMetrics` would be wrong — it is execution-operational state, not an observability metric.

### 6.5 `build_runner` / `fno_runner.py`

**Unchanged.** `build_runner` already propagates `initial_capital` (MM9.1-S4). No new parameters for MM9.2-S1.

### 6.6 LoopDriver (`core/runtime/driver.py`)

**Unchanged.** The driver calls `process_signal(signal, bar.close)`. The handler extracts and records `current_price` internally. The driver does not interact with the handler's price cache. No new hook.

### 6.7 Modules Unchanged

`RiskManager`, `PnLTracker`, `ReconciliationEngine`, `OrderTracker`, `GroupTracker`, `GroupPnLTracker`, `PortfolioView`, all brokers, all instruments, all signal sources — unchanged.

---

## 7. Runtime Complexity

### 7.1 Current (MM9.1)

| Operation | Complexity | Notes |
|---|---|---|
| `get_used_margin({symbol: price})` | O(N) positions | Iterates N positions but prices only 1 |
| `incremental_margin()` | O(1) | Scalar arithmetic |
| Total gate per call | O(N) | N-1 positions return 0.0 — wasted work |
| Price dict construction | O(1) | Single-entry literal |

### 7.2 Proposed (MM9.2-S1)

| Operation | Complexity | Notes |
|---|---|---|
| `_latest_prices[symbol] = price` | O(1) amortised | Dict insertion |
| `get_used_margin(self._latest_prices)` | O(N) positions | Same iteration; now finds prices for all warmed symbols |
| `incremental_margin()` | O(1) | Unchanged |
| Total gate per call | O(N) | Same asymptotic; N-1 additional float multiplications |
| Price dict lookup | O(1) per symbol | Hash table |

The additional work relative to MM9.1 is N-1 floating-point multiplications that were previously skipped (because prices were missing). For a 20-symbol universe this is 19 multiplications per gate call — nanosecond-scale. Negligible.

### 7.3 Memory

`_latest_prices: Dict[str, float]`: one entry per distinct symbol ever seen. For a 5-symbol universe: ~200 bytes. Negligible.

---

## 8. Risks

### R1 — Stale Price for Non-Signaling Held Symbols

**Description:** The cache updates only when a signal arrives for a symbol. If FINNIFTY has not signaled for 30 minutes but holds an open short, its price in `_latest_prices` is 30 minutes old.

**Severity:** Low in practice. In normal operation, a strategy generating entries on FINNIFTY also processes every FINNIFTY bar and can signal on each. If a strategy holds FINNIFTY but never signals on it, the position was opened externally — an unusual operating mode.

**Error direction:** Random (price may be higher or lower). In a rising market for a short, cached price underestimates margin — conservative. In a falling market, it overestimates — safe for the gate.

**Future resolution (not MM9.2-S1):** Introduce `update_market_price(symbol, price)` on `ExecutionHandler` called by the driver every bar. Requires a minor LoopDriver change; out of scope for this slice.

### R2 — Cold-Start Undercount (Transient C3 Reinstatement)

**Description:** At session restart, `_latest_prices = {}`. PositionTracker has recovered all held positions. Until the first bar arrives for each symbol, the gate prices only the signaling symbol.

**Severity:** Bounded to the first tick cycle (time to receive one bar per symbol). For 1-minute bars and a 3-symbol universe, this is under 3 minutes.

**Mitigation:** Log a WARNING at startup that `_latest_prices` is cold. Accept the gap; the alternative (seeding from `avg_price`) uses stale entry prices.

### R3 — Double-Count Dependency on Stacking Guard

**Description:** `used_margin(all positions) + incremental(new order)` is non-double-counting only because the position-stacking guard (handler.py:539–541) prevents the signal's symbol from already being open for non-EXIT signals. If pyramiding is ever introduced, the gate double-counts: once from `used_margin` (existing position) and once from `incremental_margin` (additional order).

**Mitigation:** Add a comment in `_check_margin_budget` noting this dependency. When pyramiding is implemented, the gate must be redesigned to compute `used_margin_excluding(symbol) + full_incremental(symbol, existing+new_qty)`.

### R4 — Incorrect Multiplier for Option Positions (Pre-MM9.2-S2) — HIGH

**Description:** Even with a full price cache, `_calculate_single_exposure` uses `pos.instrument.multiplier = 1.0` for restored option positions. A NIFTY short (1 lot = 75 shares) is computed as `1 × 23000 × 1.0 = Rs 23,000` instead of `1 × 23000 × 75 = Rs 17,25,000`. The gate drastically underestimates existing option margin.

**Severity:** HIGH. MM9.2-S1 alone does not produce correct multi-symbol margin.

**Mitigation:** MM9.2-S2 must merge immediately after MM9.2-S1. The two slices must be treated as a deployment pair. An intermediate state with S1 merged and S2 not merged is hazardous in production.

### R5 — Zero-Price Falsy Guard Silently Drops Legs

**Description:** `if price:` evaluates `0.0` as falsy. An option position at or near zero (deep OTM approaching expiry) is silently excluded.

**Severity:** Low in normal operation; meaningful at expiry.

**Mitigation:** Fixed by MM9.2-S2: `if price is not None:`.

### R6 — Performance Regression for Large Universes

**Description:** `get_used_margin` now performs N float multiplications instead of 1 for N open positions.

**Severity:** Negligible. Even at 1000 signals/second, 20 multiplications adds ~20 microseconds of CPU time per second.

### R7 — Future SPAN Engine Price Feed

**Description:** The SPAN engine (MM9.4) will receive prices from a tick feed, not `bar.close`. If `_latest_prices` is passed to `MarginCalculator.get_used_margin()`, the caller controls which prices SPAN sees.

**Resolution built-in:** Architecture A keeps the handler in control of which prices are passed to any calculator. The SPAN designer may update `_latest_prices` with tick-level prices before calling `get_used_margin`. This is by design.

---

## 9. Repository Impact

### 9.1 Files Changed by MM9.2-S1

| File | Change |
|---|---|
| `core/execution/handler.py` | `_latest_prices` attr in `__init__`; cache update in `process_signal`; arg change in `_check_margin_budget`; remove C3 warning phrase from rejection log |

### 9.2 Files Changed by MM9.2-S2 (Must Follow Immediately)

| File | Change |
|---|---|
| `core/execution/margin_tracker.py` | `_calculate_single_exposure`: lot_size fix; `if price:` → `if price is not None:` |

### 9.3 New Tests

| File | Contents |
|---|---|
| `tests/execution/test_mm9_2_s1_price_cache.py` | Full test suite specified in §10 |

### 9.4 Existing Tests Affected

**MM9.2-S1 alone:** No existing test should fail. The gate is more restrictive (more margin counted) but only if held positions exist. Tests that mock `position_tracker` with no held positions see no change. Review `tests/execution/test_mm9_1_margin_gate.py` for any test with held positions that sets `cash_balance` tightly — those expectations may need updating to the now-correct (higher) margin values.

**MM9.2-S2:** Tests asserting specific `get_used_margin()` values for option positions will observe a ~lot_size× increase. These tests must be identified and updated before MM9.2-S2 implementation. The prior values were wrong; updated values are correct.

### 9.5 Documentation Updates (KB Sync)

| Document | Update |
|---|---|
| `docs/reports/MM9_IMPLEMENTATION_PLAN.md` | Tick MM9.2-S1 and MM9.2-S2 when both slices complete |
| `docs/PROJECT_STATE.md` | After MM9.2-S2: update margin gate description from "single-symbol gate" to "portfolio-aware (flat-rate; multiplier approximate for live option positions until canonical_restore.py is fixed)" |
| `docs/DRIVER_SPECIFICATION.md` | §8.5: remove C3 limitation note after MM9.2-S2 complete |

---

## 10. Slice Plan

MM9.2-S1 and MM9.2-S2 are a tightly coupled deployment pair. Do not deploy S1 without immediately following with S2.

---

### Slice MM9.2-S1 — Handler-Owned Price Cache

**Objective:** Resolve C3 (portfolio blindness) by maintaining a running price cache in `ExecutionHandler` and passing it to `get_used_margin()`.

**Files touched:** `core/execution/handler.py`

**Exact changes:**

1. `__init__` (after `self.metrics = ExecutionMetrics(...)`):
   ```python
   self._latest_prices: Dict[str, float] = {}
   ```

2. `process_signal` (start of try block, before all gates):
   ```python
   self._latest_prices[signal.symbol] = current_price
   ```

3. `_check_margin_budget` (line ~943):
   ```python
   # Remove: used_current = self.margin_tracker.get_used_margin({order.symbol: current_price})
   # Add:
   used_current = self.margin_tracker.get_used_margin(self._latest_prices)
   ```

4. WARNING log format: Remove `[C3: single-symbol gate only — other open positions not priced]` from the rejection log string.

**Acceptance criteria:**

- `self._latest_prices` is a `Dict[str, float]` on `ExecutionHandler`, initialized `{}`.
- On `process_signal(signal_A, price_A)`, `self._latest_prices["A"] == price_A`.
- On subsequent `process_signal(signal_B, price_B)`, `self._latest_prices == {"A": price_A, "B": price_B}`.
- `_check_margin_budget` receives a dict with all symbols seen so far.
- A held position for symbol A with a cached price contributes non-zero to `used_margin` when a signal for symbol B triggers the gate.
- All 600 existing tests pass unchanged.
- C3 warning phrase absent from rejection log.

**Regression risk:** Very low. The only observable change from an existing-test perspective: gate may reject signals that MM9.1 would approve (more margin counted). Tests with no held positions see no change.

---

### Slice MM9.2-S2 — MarginTracker Multiplier and Falsy Guard Fix

**Objective:** Repair `MarginTracker._calculate_single_exposure` to use lot_size for F&O positions, and fix the `if price:` falsy guard. Without this slice, MM9.2-S1 prices all symbols but computes option margin at 1/lot_size of the correct value.

**Files touched:** `core/execution/margin_tracker.py`

**Exact changes:**

1. `_calculate_single_exposure`: Replace `pos.instrument.multiplier` with a lot_size-aware lookup. The exact attribute path must be confirmed by reading `canonical_restore.py` and the `Instrument` class hierarchy before implementing. Pseudocode:
   ```python
   # Before:
   return pos.quantity * current_price * pos.instrument.multiplier
   # After (implementor must confirm attribute path):
   lot_size = getattr(pos.instrument, 'lot_size', None) or pos.instrument.multiplier
   return pos.quantity * current_price * lot_size
   ```

2. `get_exposure`: Replace `if price:` with `if price is not None:`.

**Acceptance criteria:**

- NIFTY option position qty=1, price=23000 → exposure = `1 × 23000 × 75 = Rs 17,25,000`.
- BANKNIFTY option position computes exposure with the correct lot_size.
- Equity position still computes `qty × price × 1.0`.
- Zero-priced position (`price=0.0`) is included in the sum.
- All MM9.2-S1 tests pass.
- All MM9.1 tests pass (option-position margin assertions updated to correct values).

**Regression risk:** Medium. Changes numeric output of `get_used_margin()` for option portfolios by ~lot_size. Tests asserting specific margin values for option positions must be updated — expected behaviour, not a regression.

---

### Slice MM9.2-S1-T — Tests

**File:** `tests/execution/test_mm9_2_s1_price_cache.py` (new file)

**Priority 1 — Required before merge of MM9.2-S1:**

| Test ID | What it verifies |
|---|---|
| `test_price_cache_initializes_empty` | `handler._latest_prices == {}` after construction |
| `test_price_cache_updated_on_signal` | After `process_signal(signalA, 100.0)`, `handler._latest_prices["A"] == 100.0` |
| `test_price_cache_accumulates_across_signals` | Signal for A then B → both keys present |
| `test_price_cache_overwritten_on_repeat_signal` | Second signal for A at different price overwrites first |
| `test_margin_gate_uses_full_cache` | Hold position in A, new signal for B; `get_used_margin` called with dict containing both A and B |
| `test_held_symbol_contributes_to_used_margin` | Concrete: held 1 lot A (cached at 100), new order in B; `used_current > 0` (not 0.0 as in MM9.1) |
| `test_exit_still_bypasses_gate` | EXIT signal: cache updated, gate not called |
| `test_cache_warm_cold_start` | Fresh handler; first signal; no error; cache contains exactly one entry |
| `test_no_c3_warning_in_log_format` | Rejection log does NOT contain "single-symbol gate only" |

**Priority 2 — Cold-start and recovery:**

| Test ID | What it verifies |
|---|---|
| `test_cold_start_held_symbol_not_in_cache` | Held symbol with no signal yet: absent from `_latest_prices`; gate runs without error; symbol contributes 0 to `used_margin` |
| `test_recovery_positions_priced_after_first_bar` | After `_replay_state` (held position), first signal for that symbol warms cache; subsequent signal for different symbol sees held position priced |
| `test_utilisation_with_two_held_positions_and_new_signal` | Three-symbol scenario: two positions priced (cached), new order in third symbol; `total_required_margin` includes all three |

**Documented limitation test:**

| Test ID | What it verifies |
|---|---|
| `test_stale_price_in_cache_for_non_signaling_symbol` | Symbol B priced at 100.0 from prior signal; no further B signals; `_latest_prices["B"] == 100.0`. Docstring states: "Accepted limitation — cache is signal-driven, not bar-driven. See MM9.2-S1 §8 R1." |

---

## 11. Definition of Done (MM9.2-S1 + MM9.2-S2 Pair)

```
[ ] MM9.2-S1: _latest_prices: Dict[str, float] = {} added to ExecutionHandler.__init__
[ ] MM9.2-S1: self._latest_prices[signal.symbol] = current_price at start of process_signal
[ ] MM9.2-S1: _check_margin_budget passes self._latest_prices to get_used_margin
[ ] MM9.2-S1: C3 warning phrase removed from rejection log format
[ ] MM9.2-S1-T: test suite written — all Priority 1 and Priority 2 tests passing
[ ] MM9.2-S1-T: stale-price limitation test present with docstring
[ ] MM9.2-S1: stacking-guard dependency comment added in _check_margin_budget
[ ] MM9.2-S2: lot_size attribute path confirmed via canonical_restore.py + Instrument class read
[ ] MM9.2-S2: _calculate_single_exposure uses lot_size (not multiplier)
[ ] MM9.2-S2: if price is not None: guard in get_exposure
[ ] MM9.2-S2: NIFTY option margin verified = qty × price × 75 (not × 1)
[ ] All 600+ existing tests passing
[ ] docs/reports/MM9_IMPLEMENTATION_PLAN.md: MM9.2-S1 and MM9.2-S2 ticked
```

---

## 12. Architectural Issues Beyond C3 (Out of MM9.2-S1 Scope)

Documented here for completeness; must NOT be implemented in this slice.

**I.H.1 — Static `cash_balance` denominator:** `metrics.cash_balance` never updates during a session. In a losing session, the gate denominator is too optimistic. Resolved by MM9.2-S4.

**I.M.2 — Single-symbol unrealized equity:** `_update_equity_metrics` and `_persist_metrics` include only the signal's symbol in the unrealized P&L computation. Full multi-symbol equity computation follows the same pattern as the price cache but applies to equity reporting, not margin. Partially resolved by MM9.2-S4.

**I.L.1 — `process_group_signal` not covered:** The group signal path bypasses all gates including the margin gate. Pre-existing gap; orthogonal to MM9.2.

**I.L.2 — PnLTracker recovery:** Realized PnL is not persisted; `get_realized_pnl()` returns 0.0 after every restart. Orthogonal to margin.
