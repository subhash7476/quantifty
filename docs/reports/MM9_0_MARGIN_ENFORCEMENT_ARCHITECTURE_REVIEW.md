# MM9.0 — Margin Enforcement Architecture Review

**Date:** 2026-06-16
**Status:** Architecture review — no implementation. Decisions locked here govern MM9.1–MM9.4.
**Depends on:** `docs/reports/MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` (MM9 audit)

---

## 0. Purpose

The MM9 audit established that `MarginTracker` exists but is never consulted in the execution decision path — making margin enforcement structurally absent despite Constitution Principle 4 requiring it. This document resolves four open architectural questions before any implementation begins:

1. What exactly constitutes "margin validation" under Principle 4?
2. Which enforcement layer should be the first gate — exposure, used-margin, capital-utilization, or buying-power?
3. Where does the gate live — `ExecutionHandler`, `RiskManager`, or a separate service?
4. How does the gate interact with recovery, reconciliation, drawdown controls, portfolio Greeks, and future SPAN?

Each question is answered with a binding decision and rationale. The milestone ladder follows.

---

## 1. What Constitutes "Margin Validation" Under Principle 4?

Constitution Principle 4 states: "Required before order submission: Position size, Risk amount, Stop definition, **Margin validation**, Risk clearance."

Constitution §8 states: "The platform must support: **Margin-aware execution**."

### 1.1 What the Constitution does not define

The Constitution names the obligation but not the implementation. "Margin validation" has at least four plausible meanings:

| Interpretation | Meaning | NSE term |
|---|---|---|
| A | Verify gross notional stays below a leverage cap | Exposure limit |
| B | Verify estimated margin in use stays below a capital fraction | Capital utilisation |
| C | Verify the account has enough free cash to fund the new position | Buying power |
| D | Compute and verify SPAN initial + exposure margin for the full portfolio | SPAN margin |

### 1.2 The minimum constitutional obligation

The Constitution's obligation is that **no trade may be submitted without margin having been checked**. The check must be:

- **Pre-trade** — runs before `broker.place_order`, not after
- **Gating** — must be able to reject the order, not just log
- **Deterministic** — same state + same prices → same decision (ADR-003)
- **Auditable** — every rejection must be explainable (Constitution §7)

Interpretations A and B satisfy the minimum obligation. Interpretations C and D are the correct long-term target but require capabilities that do not yet exist (per-order incremental margin, SPAN parameter sets).

### 1.3 Binding definition

> **"Margin validation" under Constitution Principle 4 means: before submitting an order to the broker, verify that the estimated total margin consumed by all open positions plus the proposed new position does not exceed a configured fraction of available capital. The estimate may be approximate; it must be gating.**

This definition:
- Is satisfiable by the existing `MarginTracker` infrastructure (no new tracking needed)
- Is transitional: "estimate" acknowledges the flat-rate limitation without encoding it as permanent
- Is gating: "does not exceed" means reject, not warn
- Is pre-trade: "before submitting" is the correct moment

An approximation that gates is constitutionally superior to an accurate calculation that never gates.

---

## 2. Which Enforcement Layer?

### 2.1 Exposure-based (`gross_exposure / capital <= max_leverage`)

`MarginTracker.get_exposure(prices)` computes `qty × price × multiplier` across all open positions. A leverage cap would be `gross_exposure <= capital × max_leverage_ratio`.

**Problem for option selling:** gross notional for a sold call is the full strike notional, but the actual margin is far smaller (bounded by the option premium + SPAN scan range). An exposure-based gate would massively over-estimate margin for short options and reject valid trades.

**Problem for incrementalism:** gross exposure does not map to a margin budget. If capital is ₹10L and the cap is 5× leverage, the platform could hold ₹50L notional with ₹2,00,000 of actual NSE margin. The exposure cap would fire long before the real margin constraint.

**Verdict: not the first layer.** Exposure is a useful secondary risk metric (MM9.3 — Portfolio Exposure Controls), not the primary margin gate.

### 2.2 Used-margin-based (`used_margin + incremental <= capital`)

`MarginTracker.get_used_margin(prices)` returns `gross_exposure × 0.2`. Adding an incremental term for the new order gives a pre-trade check: `current_used + new_used <= capital`.

**Form is correct; calculation is wrong.** The flat 20% rate is arbitrary and not derived from NSE margin norms. For index option selling, NSE initial margin is typically 8–15% of notional (SPAN-computed), not 20%. The gate would over-reject and would produce different thresholds for different instruments without any principled basis.

**However:** this is the transition form. If the flat rate is replaced by SPAN, the gate's outer logic is unchanged. The rate is the variable; the gate structure is permanent.

### 2.3 Capital-utilization-based (`(used_margin + incremental) / cash_balance <= max_utilisation`)

This is a ratio formulation of 2.2. Instead of an absolute capital cap, it uses a fraction (e.g., 0.8 = 80%). Benefits over 2.2:

- Survives capital changes (`cash_balance` drifts as PnL realizes; a ratio gate self-adjusts)
- Operator-tunable without knowing the absolute capital figure in code
- Creates an explicit headroom buffer: `(1 - max_utilisation)` of capital is always reserved for adverse moves, margin calls, and new opportunities
- Separates the question "how much capital are we using?" from "how much is allowed?" — making both tunable independently

**This is the recommended first enforcement layer.**

### 2.4 Buying-power-based (`free_capital >= incremental_margin`)

`free_capital = cash_balance - used_margin`. A new order is rejected if its incremental margin exceeds free capital.

This is the **correct financial framing** — it matches how brokers think about margin. NSE's real-time risk management (RMS) works exactly this way: it checks if the account's available margin (capital − used margin) covers the new position's SPAN margin before allowing the order.

**Problem:** "incremental margin" requires knowing the SPAN margin of the specific contract — strike, expiry, underlying volatility, scan range. None of that infrastructure exists yet. A flat-rate approximation would work in form but would be wrong for option selling (where SPAN may produce an incremental margin very different from `qty × multiplier × price × 0.2`).

**Verdict: the correct long-term target for MM9.4 (SPAN integration), not the first gate.**

### 2.5 Decision

| Milestone | Layer | Calculation | Status |
|---|---|---|---|
| MM9.1 | Capital-utilization | `(used_margin + incremental_est) / cash_balance <= max_util` | First gate |
| MM9.2 | Capital-utilization + exposure ceiling | Add absolute notional cap per underlying | Secondary gate |
| MM9.4 | Buying-power | `free_capital >= SPAN_incremental_margin(order)` | SPAN target |

The capital-utilization layer is adopted for MM9.1. `max_capital_utilisation` is a new `ExecutionConfig` field with a conservative default (0.80 = 80%).

The incremental margin estimate for MM9.1 is:

```
incremental_est = order.quantity × order.instrument.multiplier × current_price × margin_tracker.margin_rate
```

This is wrong for option selling (over-estimates) and a defensible starting point for futures (reasonable first-order estimate). It is honest about its approximation because it reuses the existing `margin_tracker.margin_rate` rather than encoding a new magic constant.

---

## 3. Where Does the Gate Live?

### 3.1 Current `process_signal` gate sequence

`handler.py:439–724` establishes the following sequence:

```
1.  Authority enforcement             (handler, ~line 447)
2.  Idempotency check                 (handler, ~line 459)
3.  STOP file / kill switch file      (handler, ~line 506)
4.  signals_received++                (handler, ~line 511)
5.  Kill switch state check           (handler, ~line 514)
6.  Daily trade limit                 (handler, ~line 518)
7.  Drawdown kill switch              (handler, ~line 526)
8.  Position stacking guard           (handler, ~line 537)
9.  _check_risk_limits(signal, price) (handler, private method, ~line 542)
10. _check_greek_limits(signal, price)(handler, private method, ~line 547)
11. TLP context capture               (handler, ~line 549)
12. Instrument resolution + order build (handler, ~lines 570–635)
13. RiskManager.evaluate(order)       (injected)
14. broker.place_order(order)         (injected)
```

### 3.2 Why not `RiskManager`

`RiskManager.evaluate(order)` is currently **stateless** — it evaluates a single `NormalizedOrder` against configured limits (max quantity, symbol allow/deny, kill switch, daily limit) without any portfolio state. Its inputs are: `order`, `trades_today`, `max_trades_per_day`.

To perform a margin check, `RiskManager` would need:
- `MarginTracker` reference (position-derived state)
- `ExecutionMetrics.cash_balance` (session state)
- Current prices for all open positions (runtime state)

That would make `RiskManager` stateful and tightly coupled to the tracker chain. It would destroy the clean "pure order evaluation" contract that makes it independently testable and replaceable. The `RiskManager` is for **order-level** controls; margin is a **portfolio-level** control.

**Verdict: `RiskManager` must not own the margin gate.**

### 3.3 Why not a separate `MarginService`

A standalone `MarginService(margin_tracker, metrics)` injected into `ExecutionHandler` would be clean in isolation. However:

- It creates a new abstraction for a single gate that calls two existing objects
- The handler already owns all the inputs (tracker chain + metrics)
- ADR-001 places portfolio-state ownership in the execution layer; a `MarginService` is a second owner of derived portfolio state
- It introduces a DI surface that SPAN would render obsolete (SPAN will be a `MarginCalculator` that replaces `MarginTracker`, not a service wrapping it)

**Verdict: a separate `MarginService` is premature abstraction.** The right seam for SPAN is a `MarginCalculator` interface replacing `MarginTracker` itself, not a service wrapping either.

### 3.4 Decision: the gate lives in `ExecutionHandler`

The margin gate is a private method `_check_margin_budget(order: NormalizedOrder, current_price: float) -> bool` on `ExecutionHandler`, called at step **13.5** — after `RiskManager.evaluate(order)` passes and before `broker.place_order(order)`.

Position in the gate sequence after step 12 is deliberate:

- **We need the built order's `instrument.multiplier`** for the incremental margin estimate. `instrument.multiplier` is the lot size, which is canonical-resolution-dependent. It is not available from the signal alone until the order is built (step 12).
- **Quantity is finalized** at step 12 (`_calculate_position_size` result flows into `NormalizedOrder`). The incremental margin estimate requires the exact quantity.
- **All prior gates are cheaper**: kill switch, daily limit, drawdown, and symbol checks are O(1). Letting them reject first avoids the (slightly more expensive) tracker reads in the margin check.

The gate outcome is **rejection** (return None from `process_signal`) — not a kill switch trip. Exceeding the margin budget on one order is a per-order condition; it may clear on the next bar (prices fall, or a position closes, freeing budget). It must not permanently halt the session.

### 3.5 Handler-level inputs available at step 13.5

| Input | Source | Available? |
|---|---|---|
| `order.quantity` | `NormalizedOrder` (step 12) | Yes |
| `order.instrument.multiplier` | `NormalizedOrder.instrument` (canonical lot) | Yes |
| `current_price` | `process_signal` argument | Yes |
| `margin_tracker.get_used_margin(prices)` | `self.margin_tracker` (DI at construction) | Yes (single-price dict approximation) |
| `margin_tracker.margin_rate` | `self.margin_tracker.margin_rate` | Yes |
| `metrics.cash_balance` | `self.metrics.cash_balance` | Yes |
| `config.max_capital_utilisation` | new `ExecutionConfig` field | Needs adding |

Single-price approximation note: `get_used_margin` takes a `Dict[str, float]` of prices. At gate time, only `current_price` (for the current signal's symbol) is available from the bar. For existing open positions, prices are stale (from prior bars). A practical approximation: pass `{signal.symbol: current_price}` — positions in the current symbol get live prices; other open positions contribute 0 to exposure until their bar is processed. This is a known under-estimate for multi-symbol portfolios. It is acceptable for MM9.1 because:

1. The flat 20% rate already over-estimates option margin (compensating)
2. `max_capital_utilisation` default (0.80) provides headroom
3. Full multi-price exposure requires a price cache (MM9.2 or MM9.3 scope)

---

## 4. Gate Interactions

### 4.1 Recovery

`ExecutionHandler._replay_state()` (`handler.py:226–272`) replays orders and fills from SQLite into `OrderTracker` and `PositionTracker`. This runs at handler construction (`load_db_state=True`), before `LoopDriver` reaches RUNNING state.

By the time `process_signal` is first called, the position tracker already reflects the full recovered position set. `margin_tracker.get_used_margin(prices)` will correctly account for all recovered positions in its exposure calculation.

**No gate interaction required.** Recovery feeds the margin gate's inputs automatically. The gate cannot fire during recovery because `process_signal` is not called during recovery.

### 4.2 Reconciliation

Reconciliation (`_reconcile_ledger`) runs in `_run_startup_gate` — after recovery, before RUNNING. A reconciliation mismatch (`RECONCILIATION_FAIL`) triggers `abort_startup()` → STOPPED. The margin gate never runs if reconciliation fails.

A passed reconciliation confirms that the internal position ledger agrees with the broker's book. This means the margin gate operates on a **broker-verified** position set — the strongest possible precondition for a margin check.

**No structural interaction required.** The gate's preconditions are guaranteed by the startup gate sequence. One consequence: the margin gate inherits the startup gate's integrity guarantee. If the startup gate is bypassed (e.g., paper/replay with `broker_positions=None`), the margin gate is still correct — it measures the internal ledger, which is truth (ADR-001) regardless of broker agreement.

### 4.3 Drawdown Controls

The drawdown check (step 7) trips `activate_kill_switch()` — a one-way, session-ending action. The margin gate (step 13.5) returns `None` — a per-order rejection.

**The two controls must remain structurally separate:**

| Property | Drawdown | Margin |
|---|---|---|
| Trigger | Equity loss > threshold | Margin budget exceeded |
| Consequence | Kill switch (session ends) | Order rejected (session continues) |
| Reversible? | No (requires restart) | Yes (next bar may clear) |
| Cascade? | Kills all subsequent signals | Affects only this signal |
| Constitution basis | Principle 4 (risk clearance) | Principle 4 (margin validation) |

A margin breach is not a drawdown event. Treating it as one would permanently halt the session when a valid market opportunity arrived while the portfolio was at 80% utilisation — which is operationally wrong.

The ordering in `process_signal` is also correct: drawdown check runs **before** the margin check (step 7 vs step 13.5). If the session is already in drawdown, there is no point building the order and computing margin.

### 4.4 Portfolio Greeks

`_check_greek_limits` (step 10) is a pre-order check currently calling a single-order greek estimate (not a portfolio-level calculation, and with no live caller). When eventually wired for portfolio-level Greek limits, it will be another rejection gate.

**Structural relationship: margin and Greek checks are independent parallel gates.**

Neither calls the other. Both return rejection decisions. Ordering matters only for performance: cheaper checks should run first. The recommended ordering:

```
Step  8: Position stacking guard    (O(1) dict lookup)
Step  9: _check_risk_limits         (O(1) qty check)
Step 10: _check_greek_limits        (O(n_positions) — deferred until wired)
Step 11: TLP capture + order build  (resolver cache hit; fast)
Step 12: RiskManager.evaluate       (O(1) stateless)
Step 13: _check_margin_budget       (O(n_positions) tracker read)
Step 14: broker.place_order         (network call)
```

Margin check (step 13) after Greek check (step 10) is intentional: Greeks require IV/TTE metadata that may be absent; the margin check uses only position quantity and price, which are always available. Putting Greeks first lets them reject cheaply before the order is built; the margin check runs on the fully-built order.

### 4.5 SPAN Integration / Replacement

The MM9.1 margin gate calls `margin_tracker.get_used_margin(prices)` and reads `margin_tracker.margin_rate`. The SPAN integration goal is to replace the flat-rate calculation with a scenario-based one without changing the gate's location or contract.

**Required design constraint for MM9.1:** the gate must never embed the flat rate inline. It must always delegate to `self.margin_tracker`. This is already the correct pattern — `MarginTracker` is DI-injected at handler construction.

The SPAN transition path:

```
MM9.1:  _check_margin_budget uses MarginTracker (flat rate, 20%)
                   ↓
MM9.4:  MarginTracker replaced by SpanMarginCalculator
        implementing the same interface:
          get_used_margin(prices) → float
          get_exposure(prices)    → float
        The gate in _check_margin_budget is unchanged.
```

The transition requires:
1. A `MarginCalculator` protocol (`core/risk/margin_calculator.py`) that `MarginTracker` and `SpanMarginCalculator` both satisfy — **MM9.4 concern**
2. `ExecutionHandler.__init__` type annotation changes from `MarginTracker` to `MarginCalculator` — **MM9.4 concern**
3. The gate method itself does not change — **by design**

For MM9.1, `MarginTracker` continues as the concrete implementation. No protocol is introduced yet (YAGNI — only one implementation exists).

One additional SPAN dependency not resolved by the gate's location: the SPAN incremental margin for a new option order requires option-specific data (strike, expiry, underlying IV, scan range). This data is available from `CanonicalInstrument` (strike, expiry, underlying) and `GreeksCalculator` (IV from `black76_engine.py`). The gate's post-order-build position (step 13.5) means `order.instrument` is available as the canonical `Option` object. **The gate position chosen here is SPAN-ready by construction.**

---

## 5. Milestone Ladder

Based on the design decisions above:

### MM9.1 — Basic Margin Gate (smallest coherent increment)

**What:** `_check_margin_budget(order, current_price) -> bool` in `ExecutionHandler.process_signal`, at step 13.5.

**Gate formula:**
```
incremental_est = order.quantity × order.instrument.multiplier × current_price × margin_tracker.margin_rate
used_after      = margin_tracker.get_used_margin({signal.symbol: current_price}) + incremental_est
utilisation     = used_after / metrics.cash_balance
reject if       utilisation > config.max_capital_utilisation
```

**New config field:** `ExecutionConfig.max_capital_utilisation: float = 0.80`

**Outcome on rejection:** return `None` from `process_signal` (order rejected; session continues; `rejected_trades++`). No kill switch.

**Preconditions:**
- `ExecutionConfig` extended with `max_capital_utilisation`
- `_check_margin_budget` is a private method; no change to `RiskManager`, `MarginTracker`, or `PortfolioView`
- Tests: rejection fires correctly; approval passes through; EXIT signals bypass the gate (closing a position never fails margin); mock broker paths preserved

**Known limitations:**
- Flat rate (20%) over-estimates option margin — gate may reject valid option-selling entries
- Single-price approximation under-estimates multi-symbol portfolio exposure
- Both limitations are documented, not silent (log the gate decision)
- `max_capital_utilisation=0.80` default is deliberately conservative to compensate

### MM9.2 — Capital Utilization Controls

**What:** multi-price portfolio exposure tracking + per-underlying notional caps.

**Requires:** a price cache keyed by symbol, fed by the `LoopDriver` tick (every bar updates prices for that symbol; the handler holds the latest price per symbol). `MarginTracker.get_exposure()` is then called with the cached prices rather than the single-signal price.

**New controls:**
- `max_gross_exposure: float` — absolute notional cap across all positions
- `max_single_underlying_exposure: float` — per-underlying notional cap (prevents concentration)

**Gate:** runs at the same step 13.5, in the same `_check_margin_budget` method, with extended checks.

### MM9.3 — Portfolio Exposure Controls

**What:** wire `_check_greek_limits` for portfolio-level Greeks (not single-order). Wire `PortfolioView` into the runtime for a unified exposure view.

**Requires:** PortfolioGreeks aggregation over all open positions (calling `GreeksCalculator.calculate` per position and summing). This requires IV/TTE per position — either from signal metadata or a live IV surface.

### MM9.4 — SPAN Integration

**What:** replace `MarginTracker` flat rate with a SPAN-based `MarginCalculator`.

**Requires:**
- SPAN parameter files (NSE publishes SPAN files daily) or Upstox margin API
- `SpanMarginCalculator` implementing the `MarginCalculator` protocol
- Per-order incremental margin lookup (contract-specific)
- Gate formula changes to: `free_capital = cash_balance - span_used_margin; reject if free_capital < span_incremental(order)`

**SPAN dependencies from existing platform:**
- `CanonicalInstrument` (strike, expiry, underlying, lot_size) — exists
- `PositionTracker` (open positions) — exists
- `PnLTracker` (realized PnL → cash adjustment) — exists
- Greeks infrastructure (`black76_engine.py`) — exists
- SPAN parameter files — **not yet sourced**
- `MarginCalculator` protocol — introduced in this milestone

---

## 6. Design Decisions (Locked)

| # | Decision |
|---|---|
| D1 | "Margin validation" = a gating pre-trade check that estimated total margin (open + new) does not exceed a configured capital fraction. Approximate calculation is acceptable; no gate is not. |
| D2 | First enforcement layer = **capital-utilization-based**: `(used_margin + incremental_est) / cash_balance ≤ max_capital_utilisation`. |
| D3 | Gate location = `ExecutionHandler.process_signal`, step 13.5 (after `RiskManager.evaluate`, before `broker.place_order`), as private method `_check_margin_budget`. |
| D4 | Gate outcome = **rejection** (return `None`; `rejected_trades++`). Never a kill switch. Drawdown controls remain separate. |
| D5 | `RiskManager` stays stateless (per-order controls only). It must not own portfolio-level margin state. |
| D6 | No separate `MarginService` for MM9.1–MM9.3. The `MarginCalculator` protocol is introduced only in MM9.4 when SPAN provides a second implementation. |
| D7 | Gate always delegates to `self.margin_tracker` — never embeds the flat rate inline. This preserves SPAN replaceability. |
| D8 | EXIT signals bypass the margin gate. Closing a position reduces margin; it cannot fail a margin check. |
| D9 | The gate's position (post-order-build) gives it access to `order.instrument.multiplier` (canonical lot) and `order.quantity` — required for a correct incremental estimate. |
| D10 | Multi-symbol price state (for accurate portfolio exposure) is a MM9.2 concern. MM9.1 uses single-signal price + zero for other positions (honest under-estimate; documented). |
| D11 | Constitution Principle 4 is satisfied by MM9.1 even with flat-rate approximation, because the gate exists and is gating. The accuracy improves progressively (MM9.2 → MM9.4). |

---

## 7. Architectural Constraints Reaffirmed

All ADRs from the MM9 audit apply without modification. The additional constraints surfaced by this review:

**New constraint (from D3):** `_check_margin_budget` must be positioned **after** order creation (step 12) to access `order.instrument.multiplier`. Any future refactor that moves order creation later in the sequence must also move the margin gate correspondingly. The gate is logically coupled to the order's instrument identity.

**New constraint (from D8):** EXIT signals must bypass the margin gate unconditionally. An exit reduces margin; gating it would block position closure, which is the opposite of safety. This must be enforced with an explicit `if signal.signal_type == SignalType.EXIT: return True` guard at the top of `_check_margin_budget`.

**New constraint (from D5):** `RiskManager.evaluate(order, ...)` signature must not grow a `margin_tracker` or `cash_balance` parameter. If `RiskManager` ever needs margin context, that is an architectural change requiring a new ADR, not a parameter addition.
