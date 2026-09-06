# MM9 — Margin Enforcement Implementation Plan

**Date:** 2026-06-26
**Status:** Authoritative implementation guide — supersedes MM9.0 and MM9.1 pre-implementation documents for planning purposes.
**Source documents:**
- `docs/reports/MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` — evidence audit
- `docs/reports/MM9_0_MARGIN_ENFORCEMENT_ARCHITECTURE_REVIEW.md` — architecture decisions
- `docs/reports/MM9_1_PRE_IMPLEMENTATION_VALIDATION.md` — validation corrections

This document is the primary reference for all MM9 implementation slices. Implementors must read it before touching any file. The source documents remain authoritative for their evidence; this document is authoritative for decisions and implementation order.

---

## 1. Executive Summary

### Purpose

MM9 introduces a pre-trade margin gate that enforces Constitution Principle 4: "no trade without margin validation." The platform currently has a margin calculator (`MarginTracker`) that is instantiated in `ExecutionHandler` but never consulted in the execution decision path. Every signal that passes `RiskManager.evaluate` proceeds unconditionally to broker submission regardless of portfolio margin utilisation. MM9 closes this gap.

### Constitutional Basis

**Constitution Principle 4** — "Required before order submission: Position size, Risk amount, Stop definition, **Margin validation**, Risk clearance."

**Constitution §8** — "The platform must support: **Margin-aware execution**."

These requirements are unmet in the current codebase. Constitution Principle 4 is violated by every live order submitted.

### Scope

MM9 is a four-milestone ladder:

| Milestone | Scope | Status |
|---|---|---|
| **MM9.1** | Basic capital-utilisation gate in `process_signal` | **In scope — implement now** |
| MM9.2 | Multi-symbol price cache (S1), MarginTracker multiplier fix (S2), price freshness gate (S3) | **S1/S2/S3 COMPLETE (2026-06-27)**; S4 (`_update_equity_metrics`) pending. Original "per-underlying notional cap" (old S3) deferred — see §4 |
| MM9.3 | Portfolio Greeks wiring, `PortfolioView` runtime integration, drawdown gate I.M.2 fix | S1A/S1B/S2/S3 COMPLETE |
| MM9.4 | SPAN engine, `MarginCalculator` protocol, buying-power model | S1/S2/S3/S4 COMPLETE |

### Out of Scope for MM9 Overall

- SPAN parameter sourcing from NSE or Upstox margin API
- Buying-power calculation (requires SPAN incremental margin per contract)
- Inter-contract spread credits
- Per-order margin reservation accounting ledger
- `process_group_signal` gate coverage (separate path, separate milestone)
- Partial position exits (not implemented in the platform)
- PnLTracker recovery (pre-existing gap, orthogonal to margin)
- DuckDB `orders`/`positions` DDL prune (Planned #2)

### Current Repository Readiness for MM9.1

All architectural prerequisites are satisfied:
- `MarginTracker` exists with correct interface
- `ExecutionConfig` dataclass is the established config extension point
- `process_signal` gate sequence is established and understood
- `NormalizedOrder.canonical_instrument` carries the correct lot-size via `CanonicalInstrument.multiplier`
- 569 tests exist as a regression baseline

Three CRITICAL corrections to the MM9.0 design are required before implementation begins. These are recorded in §3 and incorporated into every slice specification.

---

## 2. Repository Baseline

### Existing Margin Infrastructure

`core/execution/margin_tracker.py` provides:
- `get_exposure(current_prices: Dict[str, float]) → float` — gross notional across all open positions
- `get_used_margin(current_prices) → float` — `get_exposure(...) × margin_rate` (default 0.20)

`MarginTracker` is injected into `ExecutionHandler` at `handler.py:163` and exposed in `PortfolioView.snapshot()` (`portfolio_view.py:57–65`). It is never called in the execution decision path.

`PortfolioView` is implemented, tested, and wired into the LoopDriver telemetry pipeline (MM9.3-S2).

Known pre-existing defects in `MarginTracker` (documented; not MM9.1's to fix):
- `_calculate_single_exposure` uses `pos.instrument.multiplier`, which is hardcoded to `1.0` for all options by `canonical_restore.py:68` — underestimates option exposure by factor of `lot_size`
- `if price:` falsy check silently excludes zero-priced positions

### Current Execution Flow (pre-MM9)

`handler.py:440–724` gate sequence:

```
[PHASE 0]  Authority enforcement + idempotency
[TLP]      Risk metadata validation (sl_dist, risk_r)
[0]        STOP file / kill switch file check
[1]        signals_received += 1
[2]        Kill switch state check → return None
[3]        Daily trade limit → kill switch + return None
[4]        Drawdown check → kill switch + return None
[4b]       Position stacking guard (non-EXIT) → return None
[5]        _check_risk_limits → ExecutionRuleError
[9C]       _check_greek_limits (no live caller; dead code path)
[TLP]      Structural context capture
[PHASE 1]  Instrument resolution + NormalizedOrder construction
[PHASE 2]  RiskManager.evaluate → rejected_trades += 1 + ExecutionRuleError
[PHASE 5]  order_tracker.add_order(order)                 ← TRACKER REGISTERS ORDER
[PHASE 7]  broker.place_order(order)
```

The margin gate inserts between PHASE 2 and PHASE 5. This is the only valid placement (see §3.4 — correction C2).

### Completed Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| `CanonicalInstrument.multiplier` = `float(lot_size)` | COMPLETE | `canonical.py:85–88` |
| `NormalizedOrder.canonical_instrument: Optional[CanonicalInstrument]` | COMPLETE | `order_models.py:39` |
| `ExecutionMetrics.rejected_trades` counter | COMPLETE | `handler.py:91` |
| `MarginTracker` DI into `ExecutionHandler` | COMPLETE | `handler.py:163` |
| `ExecutionConfig` as extension point | COMPLETE | `handler.py:68–84` |
| 569-test regression baseline | COMPLETE | confirmed passing |
| Master-readiness gate + canonicalization at startup | COMPLETE | `master_readiness.py`, `LoopDriver._run_startup_gate` |
| Recovery (`_replay_state`) rebuilds `PositionTracker` | COMPLETE | `handler.py:239–241` |

### Validated Assumptions

From MM9.1 pre-implementation validation — what was confirmed correct:

| Assumption | Validated? |
|---|---|
| `margin_tracker.get_used_margin(prices)` callable | Yes |
| `margin_tracker.margin_rate` readable (float, 0.20) | Yes |
| `order.quantity` is finalized after order creation (int) | Yes |
| EXIT bypass is required, not optional | Yes — EXIT BUY for short adds phantom margin |
| `return None` is the correct rejection mechanism | Yes — consistent with stacking guard pattern |
| Recovery feeds `PositionTracker`; margin gate sees recovered positions | Yes |
| Drawdown and margin are independent gates | Yes |
| Reconciliation failure prevents `process_signal` from reaching the gate | Yes |

---

## 3. Final Architecture Decisions

### 3.1 What "Margin Validation" Means Under Principle 4

**Binding definition (D1):** Margin validation = a gating pre-trade check that estimated total margin consumed by all open positions plus the proposed new position does not exceed a configured fraction of available capital. The estimate may be approximate; it must be gating.

An approximation that gates is constitutionally superior to an accurate calculation that never gates.

### 3.2 Why Capital-Utilisation Is the First Enforcement Layer

Four enforcement layers were evaluated: exposure-based, used-margin-based, capital-utilisation-based, and buying-power-based.

**Capital-utilisation is adopted (D2):** `(used_margin + incremental_est) / cash_balance ≤ max_capital_utilisation`

Rationale:
- Exposure-based (layer A): over-rejects short options (gross notional >> actual margin)
- Used-margin absolute cap (layer B): not self-adjusting as capital drifts; arbitrary threshold
- **Capital-utilisation (layer C): ratio self-adjusts; creates explicit headroom buffer; operator-tunable; separates "how much are we using" from "how much is allowed"**
- Buying-power (layer D): correct long-term target but requires SPAN incremental margin — infrastructure does not exist yet

### 3.3 Why the Gate Lives in ExecutionHandler (Not RiskManager or MarginService)

**RiskManager stays stateless (D5):** `RiskManager.evaluate(order)` evaluates a single order against configured limits (quantity, symbol, kill switch, daily limit). To perform a margin check it would need `MarginTracker`, `cash_balance`, and live prices — making it stateful and destroying its independently-testable contract. RiskManager is for order-level controls; margin is a portfolio-level control. Its signature must never grow a `margin_tracker` or `cash_balance` parameter.

**No separate MarginService for MM9.1–MM9.3 (D6):** A `MarginService` wrapper creates a new abstraction for a single gate that calls two existing objects, introduces a DI surface that SPAN would render obsolete, and creates a second owner of derived portfolio state contrary to ADR-001. The correct SPAN seam is a `MarginCalculator` protocol replacing `MarginTracker` itself (introduced in MM9.4).

**Gate location: `ExecutionHandler._check_margin_budget(order, current_price) → bool` (D3), called between PHASE 2 (`RiskManager.evaluate`) and PHASE 5 (`order_tracker.add_order`).**

### 3.4 Gate Placement: The Critical Correction (C2)

MM9.0 specified gate placement as "between `RiskManager.evaluate` and `broker.place_order`." This was wrong.

`order_tracker.add_order(order)` fires at `handler.py:659` — between `risk_manager.evaluate()` (line 648) and `broker.place_order()` (line 663). A rejection after `add_order()` creates an orphaned order in the tracker: registered, never filled, replayed on next session as a pending order with no matching fill — corrupting recovered ledger state.

**Correct placement:** AFTER `risk_manager.evaluate(order)` is approved, BEFORE `order_tracker.add_order(order)`.

```
risk_manager.evaluate(order)        → approve
↓
_check_margin_budget(order, price)  → approve    ← MM9.1 gate
↓
order_tracker.add_order(order)      → register
↓
broker.place_order(order)           → submit
```

### 3.5 Why MarginTracker Remains the Concrete Implementation (Through MM9.3)

`MarginTracker` is DI-injected at handler construction and provides the correct interface. For MM9.1–MM9.3, no second implementation exists, so introducing a `MarginCalculator` protocol violates YAGNI. The gate always delegates to `self.margin_tracker` — it never embeds the flat rate inline (D7). When SPAN provides a second implementation, the protocol is introduced in MM9.4 and `ExecutionHandler.__init__` type annotation changes from `MarginTracker` to `MarginCalculator`. The gate method itself does not change.

### 3.6 The Multiplier Defect and the Correct Source (C1)

`canonical_restore.py:68` hardcodes `multiplier=1.0` for every option position restored via G1 Wave 4B/3. `MarginTracker._calculate_single_exposure` uses `pos.instrument.multiplier`, making option exposure wrong by a factor of `lot_size` (75× for NIFTY, 30–35× for BANKNIFTY).

`NormalizedOrder.canonical_instrument.multiplier` is correct — `CanonicalInstrument.multiplier` at `canonical.py:85–88` returns `float(self.lot_size)`.

**MM9.1 incremental estimate must use `order.canonical_instrument.multiplier` when `canonical_instrument is not None`, falling back to `order.instrument.multiplier` for equity.** Using `order.instrument.multiplier` for F&O makes the gate wrong by a factor of lot_size — not an acceptable approximation.

Note: `get_used_margin()` for existing open positions still uses the wrong multiplier (pre-existing `MarginTracker` defect). MM9.1 correctly estimates the new position's cost but underestimates the existing portfolio's margin consumption. Full fix is MM9.2-S2.

### 3.7 Gate Outcome: Rejection, Not Kill Switch

**Gate outcome = rejection (D4):** `return None` from `process_signal` with `self.metrics.rejected_trades += 1`. Exceeding the margin budget on one order is a per-order condition that may clear on the next bar. It must not permanently halt the session. Drawdown controls (which do trip the kill switch) remain entirely separate.

| Property | Drawdown Gate | Margin Gate |
|---|---|---|
| Trigger | Equity loss > threshold | Margin utilisation > limit |
| Consequence | Kill switch (session ends) | Order rejected (session continues) |
| Reversible? | No — requires restart | Yes — next bar may clear |
| Cascade? | Kills all subsequent signals | Only this signal |

### 3.8 EXIT Signal Bypass

**EXIT signals bypass the margin gate unconditionally (D8).** An EXIT BUY (covering a short) computes a positive incremental margin estimate, but the true effect is to close a short, reducing margin. Gating an EXIT would incorrectly block position-closing trades — the opposite of safety.

The bypass is enforced at the call site in `process_signal` (`if signal.signal_type != SignalType.EXIT:`), not inside `_check_margin_budget`. The order object has no `signal_type` field; the signal is in scope at the call site.

### 3.9 Multi-Symbol Scope Limitation (C3)

`get_used_margin({signal.symbol: current_price})` with a single-symbol price dict iterates all positions but prices only the one matching symbol. All other open symbols contribute zero exposure. In a multi-symbol portfolio this is not a portfolio gate — it is a per-symbol gate. In the worst case (five symbols each at 40% utilisation, new signal for a sixth symbol), the gate sees 40% utilisation and approves while actual portfolio utilisation is 240%.

**MM9.1 must carry an explicit operator warning** in code (log message), documentation, and tests: the gate is per-symbol only, not a portfolio gate. `max_capital_utilisation = 0.80` provides no portfolio-level protection for multi-symbol deployments. The correct fix (running per-symbol price cache updated each bar) is MM9.2-S1.

### 3.10 Gate Interactions with Recovery, Reconciliation, Drawdown, Greeks, and SPAN

**Recovery:** `_replay_state()` rebuilds `PositionTracker` from all historical fills before `process_signal` is ever called. The margin gate correctly sees all recovered positions. No structural interaction required.

**Reconciliation:** A reconciliation failure triggers `abort_startup()` before RUNNING state. `process_signal` never reaches the margin gate on an unreconciled ledger.

**Drawdown:** Drawdown check runs at gate step [4], margin check runs at step [PHASE 2+]. They are independent. Drawdown fires first; if the session is already killed, the margin gate never runs.

**Portfolio Greeks:** `_check_greek_limits` (step [9C]) has no live caller. When eventually wired, it is a parallel independent gate. Greeks run before the order is built; margin runs after. Both reject independently.

**Future SPAN Engine:** The gate always delegates to `self.margin_tracker`. Transition: MM9.4 replaces `MarginTracker` with `SpanMarginCalculator` implementing a `MarginCalculator` protocol with the same interface. The gate method is unchanged. The gate's post-order-build position gives it access to `order.canonical_instrument` — SPAN-ready by construction.

---

## 4. Implementation Roadmap

### MM9.1-S1 — ExecutionConfig Field

**Objective:** Add `max_capital_utilisation` to `ExecutionConfig`. This is the only config change for MM9.1.

**Files touched:** `core/execution/handler.py`

**Repository impact:** Adds one field to `ExecutionConfig` dataclass (`handler.py:68–84`). All existing instantiation sites that omit the argument receive the default (0.80). No behaviour change.

**Acceptance criteria:**
- `ExecutionConfig()` default is `max_capital_utilisation = 0.80`
- `ExecutionConfig(max_capital_utilisation=0.5)` produces `config.max_capital_utilisation = 0.5`
- Inline comment notes it applies only to the single-symbol incremental estimate (MM9.1 limitation)

**Definition of Done:** Field visible in `ExecutionConfig`. All existing tests pass unchanged.

**Estimated complexity:** Trivial (one line in the dataclass).

**Suggested implementor:** Claude

**Dependencies:** None

**Suggested commit message:**
```
MM9.1-S1 — ExecutionConfig.max_capital_utilisation field (default 0.80)
```

---

### MM9.1-S2 — `_check_margin_budget` Private Method

**Objective:** Implement the margin gate as a private method on `ExecutionHandler`. Returns `True` (approve) or `False` (reject). Does not increment metrics or log — the call site owns those concerns.

**Files touched:** `core/execution/handler.py`

**Gate formula (incorporating C1, C2, C3 corrections):**

```python
def _check_margin_budget(self, order: NormalizedOrder, current_price: float) -> tuple[bool, float]:
    if self.metrics.cash_balance <= 0:
        return True, 0.0  # degenerate denominator — do not block

    prices = {order.symbol: current_price}
    used_current = self.margin_tracker.get_used_margin(prices)

    # C1: use canonical_instrument.multiplier (lot-correct for F&O); fallback for equity
    effective_multiplier = (
        order.canonical_instrument.multiplier
        if order.canonical_instrument is not None
        else order.instrument.multiplier
    )
    incremental_est = (
        order.quantity * effective_multiplier * current_price * self.margin_tracker.margin_rate
    )
    utilisation = (used_current + incremental_est) / self.metrics.cash_balance
    return utilisation <= self.config.max_capital_utilisation, utilisation
```

Returning `(bool, float)` makes utilisation available to the call site for logging without recomputing.

**Repository impact:** Adds one private method. No change to public API of `ExecutionHandler`, `MarginTracker`, `RiskManager`, or `ExecutionConfig`.

**Acceptance criteria:**
- Returns `(True, utilisation)` when utilisation ≤ limit
- Returns `(True, 0.0)` when `cash_balance <= 0` (degenerate guard)
- Returns `(False, utilisation)` when utilisation exceeds limit
- Uses `canonical_instrument.multiplier` when `canonical_instrument is not None`
- Falls back to `order.instrument.multiplier` when `canonical_instrument is None`
- Does not call `rejected_trades += 1` (caller's responsibility)
- Does not log (caller's responsibility)

**Definition of Done:** Method present on `ExecutionHandler`. Unit tests in MM9.1-S4 pass against it.

**Estimated complexity:** Low (15–20 lines).

**Suggested implementor:** Claude

**Dependencies:** MM9.1-S1

**Suggested commit message:**
```
MM9.1-S2 — _check_margin_budget: capital-utilisation gate with canonical multiplier (C1 fix)
```

---

### MM9.1-S3 — Call Site in `process_signal`

**Objective:** Wire `_check_margin_budget` into `process_signal` at the correct placement (C2: after `risk_manager.evaluate`, before `order_tracker.add_order`).

**Files touched:** `core/execution/handler.py`

**Exact placement:** Between line 656 (end of risk rejection branch) and line 659 (`self.order_tracker.add_order(order)`).

**Call site contract:**

```python
# C2: gate before order_tracker.add_order — rejection here does not orphan order in tracker
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

self.order_tracker.add_order(order)
```

**Repository impact:** Approximately 10 lines added to `process_signal`. No structural change to the gate sequence. All existing gates remain independent and unmodified.

**Acceptance criteria:**
- EXIT signals are not passed to `_check_margin_budget`
- A rejected signal returns `None` without calling `order_tracker.add_order`
- A rejected signal increments `self.metrics.rejected_trades` by exactly 1
- A rejected signal logs at WARNING level including symbol, signal_id, utilisation, limit
- Warning log includes "single-symbol gate only" (C3 disclosure)
- An approved signal reaches `order_tracker.add_order` and then `broker.place_order`
- `rejected_trades` does not change on EXIT signals or approvals

**Definition of Done:** Call site present; confirmed by MM9.1-S4 integration tests.

**Estimated complexity:** Low (10 lines).

**Suggested implementor:** Claude

**Dependencies:** MM9.1-S1, MM9.1-S2

**Suggested commit message:**
```
MM9.1-S3 — wire _check_margin_budget into process_signal (C2: before add_order)
```

---

### MM9.1-S4 — Test Suite

**Objective:** Provide a complete characterization and regression test suite for MM9.1.

**Files touched:** `tests/execution/test_mm9_1_margin_gate.py` (new file)

**Priority 1 — Must pass before merge:**

| Test | What it verifies |
|---|---|
| `test_rejection_no_tracker_entry` | Signal at utilisation ≥ limit → `return None`, `rejected_trades += 1`, order NOT in tracker |
| `test_approval_order_registered` | Signal at utilisation < limit → `NormalizedOrder` returned, order in tracker, `rejected_trades` unchanged |
| `test_exit_bypass` | EXIT signal against LONG position → `_check_margin_budget` not called, order proceeds |
| `test_rejected_trades_explicit_increment` | Counter changes by exactly 1 on rejection; unchanged on approval or EXIT |
| `test_canonical_instrument_multiplier_f_and_o` | `canonical_instrument.lot_size=75` → `effective_multiplier=75.0`; incremental uses 75 not 1.0 |
| `test_equity_fallback_multiplier` | `canonical_instrument=None` → `effective_multiplier=1.0`; correct for equity |
| `test_tracker_integrity_after_rejection` | After rejection, `order_tracker.get_order(correlation_id)` raises or returns None |
| `test_degenerate_denominator_guard` | `cash_balance=0` → gate returns True; no ZeroDivisionError |
| `test_boundary_equal_utilisation_approved` | `utilisation == max_capital_utilisation` → approved (≤ not <) |

**Priority 2 — Regression:**

| Test | What it verifies |
|---|---|
| `test_kill_switch_gates_independent` | Existing kill switch, drawdown, stacking guard paths unchanged |
| `test_risk_manager_rejection_independent` | RiskManager rejection fires before margin gate; ordering preserved |
| `test_paper_broker_fill_path` | Margin-approved signal with PaperBroker reaches fill callback correctly |
| `test_recovery_feeds_position_tracker` | Replay fills → `get_used_margin` reflects recovered positions; gate fires correctly |

**Known-limitation test (must exist; behavior confirmed, not fixed):**

| Test | What it verifies |
|---|---|
| `test_multi_symbol_blindness_documented` | Three symbols each at 40% actual margin; new signal for fourth → gate sees 40%, approves. Confirms WARNING log contains "single-symbol gate only" |

**Repository impact:** New test file. All 569 existing tests must remain passing.

**Definition of Done:** All Priority 1 and Priority 2 tests pass. Known-limitation test exists with docstring explaining MM9.1 scope boundary.

**Estimated complexity:** Medium (15–20 test cases).

**Suggested implementor:** Claude

**Dependencies:** MM9.1-S1, MM9.1-S2, MM9.1-S3

**Suggested commit message:**
```
MM9.1-S4 — margin gate tests: rejection, approval, EXIT bypass, multiplier, multi-symbol doc
```

---

### MM9.1-S5 — `fno_runner.py` initial_capital Propagation

**Objective:** Address I.H.2 (HIGH risk): `fno_runner.py` does not pass `initial_capital` to `ExecutionHandler`. The gate runs against the ₹1,00,000 default regardless of actual account capital, making `max_capital_utilisation` effectively meaningless without operator intervention.

**Files touched:** `scripts/fno_runner.py`

**Scope:** Add `--initial-capital` CLI argument (or config key) that flows from `build_runner()` → `ExecutionHandler(initial_capital=...)` → `ExecutionMetrics.cash_balance`. No change to gate logic.

**Repository impact:** `fno_runner.py` gains one CLI argument. Default remains `100000.0` for backwards compatibility.

**Acceptance criteria:**
- `python scripts/fno_runner.py --initial-capital 500000` sets `handler.metrics.cash_balance = 500000.0`
- No `--initial-capital` argument → `cash_balance = 100000.0` (unchanged default)
- Usage string documents the parameter

**Definition of Done:** Parameter accepted and propagated. Documented in `docs/DRIVER_SPECIFICATION.md`.

**Estimated complexity:** Low (plumbing only).

**Suggested implementor:** Claude

**Dependencies:** MM9.1-S3 (gate must exist before this is meaningful)

**Suggested commit message:**
```
MM9.1-S5 — fno_runner: --initial-capital wired to ExecutionHandler; gate denominator configurable
```

---

### MM9.2-S1 — Per-Symbol Price Cache

**STATUS: COMPLETE (2026-06-27).** Delivered alongside S2 as a deployment pair. The cache was subsequently refactored to `Dict[str, PriceSnapshot]` in MM9.2-S3-S1 (see `MM9_2_S3_IMPLEMENTATION_SPEC_V2.md`); the `_latest_prices: Dict[str, float]` described below was the S1-as-built shape, now superseded.

**Objective:** Maintain `self._latest_prices: Dict[str, float]` in `ExecutionHandler`, updated on every signal with the current bar's price. Pass this full cache to `get_used_margin()`. Resolves C3 (multi-symbol portfolio blindness).

**Files touched:** `core/execution/handler.py`

**Change:** `self._latest_prices = {}` in `__init__`; `self._latest_prices[signal.symbol] = current_price` at start of `process_signal`; gate call changes from `{order.symbol: current_price}` to `self._latest_prices`.

**Dependencies:** MM9.1 complete

**Suggested commit message:**
```
MM9.2-S1 — per-symbol price cache; margin gate sees full portfolio exposure
```

---

### MM9.2-S2 — MarginTracker Multiplier Fix

**STATUS: COMPLETE (2026-06-27).** Delivered as the second half of the S1+S2 deployment pair.

**Objective:** Fix the pre-existing defect in `MarginTracker._calculate_single_exposure`: replace `pos.instrument.multiplier` with `getattr(pos.instrument, 'lot_size', None) or pos.instrument.multiplier`. Also fix `if price:` to `if price is not None:`.

**Files touched:** `core/execution/margin_tracker.py`

**Repository impact:** `get_used_margin()` output changes for any portfolio containing option positions. Tests asserting specific values against option positions must be updated.

**Dependencies:** MM9.2-S1

**Suggested commit message:**
```
MM9.2-S2 — MarginTracker: lot_size for options; zero-price falsy guard fix
```

---

### MM9.2-S3 — Per-Underlying Notional Cap

**Objective:** Add `max_single_underlying_exposure: float` to `ExecutionConfig` and enforce it in `_check_margin_budget` as a secondary check.

**Files touched:** `core/execution/handler.py`

**Dependencies:** MM9.2-S1, MM9.2-S2

**Suggested commit message:**
```
MM9.2-S3 — per-underlying notional cap as secondary gate in _check_margin_budget
```

---

### MM9.2-S4 — `_update_equity_metrics` Wiring

**Objective:** Call `_update_equity_metrics` from `_handle_broker_fill` so `metrics.cash_balance` updates as fills occur. Resolves I.H.1 (static cash_balance). Also partially fixes the drawdown gate's single-symbol equity calculation (I.M.2).

**Files touched:** `core/execution/handler.py`

**Dependencies:** MM9.2-S1

**Suggested commit message:**
```
MM9.2-S4 — wire _update_equity_metrics to fill path; cash_balance tracks realized PnL
```

---

### MM9.3-S1 — PortfolioGreeks Aggregation

**Objective:** Implement portfolio-level Greek aggregation in `_check_greek_limits` by summing `GreeksCalculator.calculate()` across all open positions. Currently unreachable.

**Files touched:** `core/execution/handler.py`, `core/risk/greeks/`

**Dependencies:** MM9.2 complete; IV source available per position — resolved via TTE=0.0/IV=0.20 defaults; true per-position IV deferred to MM9.5.

**Split:** S1A (semantic correction — COMPLETE 2026-06-28) + S1B (portfolio aggregation). S1A converted `_check_greek_limits` from `raise ExecutionRuleError` to a bool-returning D4 rejection gate (EXIT bypass, `GREEK_DELTA_BREACH` WARNING, call-site wired). Body remains marginal-only until S1B.

---

### MM9.3-S2 — PortfolioView Runtime Integration

**Objective:** Wire `PortfolioView.snapshot()` into the `LoopDriver` telemetry tick so the Flask dashboard receives live margin and exposure data.

**Files touched:** `core/runtime/driver.py`, telemetry surface

**Dependencies:** MM9.3-S1

---

### MM9.4-S1 — MarginCalculator Protocol

**Objective:** Define `core/risk/margin_calculator.py` with a `MarginCalculator` protocol. Update `ExecutionHandler.__init__` type annotation. Gate method unchanged.

**Interface:**
```python
class MarginCalculator(Protocol):
    margin_rate: float
    def get_used_margin(self, current_prices: Dict[str, float]) -> float: ...
    def get_exposure(self, current_prices: Dict[str, float]) -> float: ...
```

**Files touched:** `core/risk/margin_calculator.py` (new), `core/execution/handler.py` (type annotation only)

**Dependencies:** MM9.3 complete

---

### MM9.4-S2 — SPAN Parameter Sourcing

**Objective:** Source SPAN parameter files (NSE publishes daily) or integrate Upstox margin API. Design the data model for scenario-based margin.

**Files touched:** New `core/risk/span/` module, `scripts/fetch_span_params.py`

**Dependencies:** MM9.4-S1

---

### MM9.4-S3 — SpanMarginCalculator Implementation

**Objective:** Implement `SpanMarginCalculator` satisfying `MarginCalculator` protocol. Computes initial margin (worst-case scenario), exposure margin, and incremental margin for a proposed order using `CanonicalInstrument` and `GreeksCalculator`.

**Files touched:** `core/risk/span/span_calculator.py`

**Dependencies:** MM9.4-S1, MM9.4-S2

---

### MM9.4-S4 — Gate Formula Update to Buying-Power Model

**Objective:** Replace capital-utilisation formula with: `free_capital = cash_balance - span_used_margin; reject if free_capital < span_incremental(order)`. Gate method `_check_margin_budget` changes internally; call site unchanged.

**Files touched:** `core/execution/handler.py`

**Dependencies:** MM9.4-S1, MM9.4-S2, MM9.4-S3

---

## 5. Slice Dependency Graph

```
MM9.1-S1 (ExecutionConfig field)
    └── MM9.1-S2 (_check_margin_budget method)
            └── MM9.1-S3 (call site in process_signal)
                    ├── MM9.1-S4 (test suite)
                    └── MM9.1-S5 (fno_runner initial_capital)
                            └── MM9.2-S1 (per-symbol price cache)
                                    ├── MM9.2-S2 (MarginTracker multiplier fix)
                                    ├── MM9.2-S4 (_update_equity_metrics wiring)
                                    └── MM9.2-S3 (per-underlying notional cap)
                                            └── MM9.3-S1 (PortfolioGreeks aggregation)
                                                    └── MM9.3-S2 (PortfolioView runtime)
                                                            └── MM9.4-S1 (MarginCalculator protocol)
                                                                    └── MM9.4-S2 (SPAN sourcing)
                                                                            └── MM9.4-S3 (SpanMarginCalculator)
                                                                                    └── MM9.4-S4 (buying-power gate)
```

MM9.1-S1 through MM9.1-S5 are the active implementation scope. MM9.2–MM9.4 are deferred.

---

## 6. Testing Strategy

### MM9.1-S1

| Category | Requirement |
|---|---|
| Unit | Default field value is 0.80; custom value propagates |
| Regression | All existing `ExecutionConfig` instantiation sites pass unchanged |

### MM9.1-S2

| Category | Requirement |
|---|---|
| Unit | F&O path: lot_size=75 → incremental = `qty × 75 × price × rate` |
| Unit | Equity path (no canonical_instrument): incremental = `qty × 1.0 × price × rate` |
| Unit | Degenerate guard: `cash_balance=0` → `(True, 0.0)`, no exception |
| Unit | Boundary: utilisation == limit → `(True, utilisation)` (equal is approved) |
| Unit | Boundary: utilisation > limit by epsilon → `(False, utilisation)` |
| Regression risk | None — new private method, no existing callers |

### MM9.1-S3

| Category | Requirement |
|---|---|
| Integration | Rejected signal: `return None`, `rejected_trades += 1`, order not in tracker |
| Integration | Approved signal: order in tracker, broker called |
| Integration | EXIT signal: `_check_margin_budget` not called |
| Integration | `rejected_trades` unchanged on EXIT and approval |
| Regression | All 569 existing tests pass |
| Acceptance | Confirmed by full test suite run |

### MM9.1-S4

See test table in §4. Additional:

| Category | Requirement |
|---|---|
| Characterization | Multi-symbol blindness: behavior confirmed and documented; WARNING log includes "single-symbol gate only" |
| Repository audit | `order_tracker` has no orphaned orders after any rejection scenario |

### MM9.1-S5

| Category | Requirement |
|---|---|
| Integration | `--initial-capital 500000` → `handler.metrics.cash_balance = 500000.0` |
| Regression | Default behavior (no flag) → `cash_balance = 100000.0` |

### MM9.2 (price cache, multiplier fix, notional cap)

| Category | Requirement |
|---|---|
| Unit (S1) | Bar for symbol A updates `_latest_prices["A"]`; bar for B updates `_latest_prices["B"]` |
| Unit (S2) | NIFTY option, lot_size=75: exposure = `qty × 75 × price` |
| Integration (S2) | Three open option positions correctly contribute to total used_margin |
| Regression (S2) | Equity positions still compute correctly (fallback to multiplier=1.0) |
| Acceptance (S3) | Signal where single-underlying notional exceeds cap → rejected |

---

## 7. Documentation Requirements

### After MM9.1-S3 merges

| Document | Required update |
|---|---|
| `docs/PROJECT_STATE.md` | Move "Margin Check" from MISSING to PARTIAL (MM9.1: single-symbol, flat-rate gate). Note MM9.2–MM9.4 as backlog. Keep SPAN blocked note. |
| `docs/CHANGELOG_PLATFORM.md` | Add entry: "MM9.1 COMPLETE — capital-utilisation margin gate wired into process_signal; corrections C1/C2/C3 applied." |
| `docs/DRIVER_SPECIFICATION.md` | Add §"Margin Gate" — placement (between PHASE 2 and PHASE 5), formula, config field, EXIT bypass, known limitations. |
| `docs/reports/MM9_IMPLEMENTATION_PLAN.md` | Tick MM9.1-S1 through MM9.1-S4 in §9. |

### After MM9.1-S5 merges

| Document | Required update |
|---|---|
| `docs/DRIVER_SPECIFICATION.md` | Add `--initial-capital` parameter to CLI reference. |
| `docs/PROJECT_STATE.md` | Note operators must set `initial_capital` to actual account capital. |
| `docs/reports/MM9_IMPLEMENTATION_PLAN.md` | Tick MM9.1-S5 in §9. |

### After MM9.2 complete

| Document | Required update |
|---|---|
| `docs/PROJECT_STATE.md` | Move margin gate from PARTIAL to "portfolio-aware (flat-rate)". |
| `docs/CHANGELOG_PLATFORM.md` | MM9.2 entry with MarginTracker multiplier fix noted. |
| `docs/SESSION_BOOTSTRAP.md` | Update "Current Gaps §8" — flat-rate portfolio margin now enforces; remaining gap is SPAN. |

### After MM9.4 complete

| Document | Required update |
|---|---|
| `docs/PLATFORM_CONSTITUTION.md` | §8 Option Selling Requirements: mark "Margin-aware execution" as satisfied. |
| `docs/ARCHITECTURE_DECISIONS.md` | Add ADR for `MarginCalculator` protocol introduction. |
| `docs/PROJECT_STATE.md` | Close "Live derivatives trading blocked on SPAN margin engine (Planned #5)." |
| `docs/SESSION_BOOTSTRAP.md` | Remove SPAN from "Current Gaps §8". |
| `docs/CHANGELOG_PLATFORM.md` | MM9.4 entry. |

### SESSION_BOOTSTRAP.md timing

Do not update `SESSION_BOOTSTRAP.md` until MM9.2 is complete. MM9.1's single-symbol limitation means the existing gap entry remains accurate. Update only when the multi-symbol limitation is resolved.

---

## 8. Known Limitations

### MM9.1 Limitations (Accepted, Documented)

1. **Single-symbol gate (C3):** `get_used_margin()` is called with `{signal.symbol: current_price}`. All other open symbols contribute zero exposure. The gate provides no portfolio-level protection in multi-symbol deployments. Logged on every rejection. Resolved by MM9.2-S1.

2. **Static denominator (I.H.1):** `metrics.cash_balance` never updates during a session (`_update_equity_metrics` is never called). The gate's denominator is permanently `initial_capital`. In a losing session the effective limit is too permissive. Resolved by MM9.2-S4.

3. **Flat rate over-estimates option margin, existing positions wrong (I.C.1 partial):** The incremental estimate uses the correct `canonical_instrument.multiplier` for new orders (C1 fix). But `get_used_margin()` for existing option positions still uses `MarginTracker._calculate_single_exposure` with `multiplier=1.0` — underestimating by factor of `lot_size`. New position is measured correctly; portfolio total is not. Resolved by MM9.2-S2.

4. **`fno_runner` default capital (I.H.2):** Without MM9.1-S5, `initial_capital` defaults to ₹1,00,000. Operators must set this to actual account capital; otherwise `max_capital_utilisation=0.80` maps to an ₹80,000 margin budget. Resolved by MM9.1-S5.

5. **`process_group_signal` not covered (I.L.1):** Group-based order path bypasses all gates including the margin gate. Pre-existing gap; not introduced by MM9.1.

6. **`if price:` falsy check in MarginTracker (I.H.3):** Zero-priced positions silently excluded from exposure. Pre-existing defect; resolved by MM9.2-S2.

### MM9.2 Planned Work

- Per-symbol price cache (C3 resolution)
- `MarginTracker` multiplier fix (I.C.1 full resolution)
- `_update_equity_metrics` wiring (I.H.1 resolution)
- `initial_capital` propagation in `fno_runner` (if not done in MM9.1-S5)
- Per-underlying notional cap as secondary gate

### MM9.3 Status

- **S1A — Greek Gate Semantic Correction — COMPLETE (2026-06-28).** `_check_greek_limits` converted from `raise ExecutionRuleError` to bool-returning D4 rejection gate.
- **S1B — Portfolio Greek Aggregation — COMPLETE (2026-06-28).** Portfolio-level delta+vega+gamma aggregation via `PortfolioGreeks.calculate_portfolio_greeks()`.
- **S2 — PortfolioView Runtime Integration — COMPLETE (2026-06-28).** `PortfolioView` wired into `LoopDriver._build_positions()`; enriched telemetry payload with portfolio Greeks, MTM equity, PnL breakdown, and real per-symbol `pnl_pct`; degraded raw fallback when `PortfolioView` absent.
- **S3 — Drawdown Gate I.M.2 Full Fix — COMPLETE (2026-06-28).** Replaced single-symbol drawdown equity with `PortfolioView.mtm_equity` via handler-local `_handler_portfolio_view`. EXIT bypass preserved. 719 passing.

### MM9.4 SPAN Work

- `MarginCalculator` protocol introduction
- SPAN parameter file sourcing (NSE daily files or Upstox margin API)
- `SpanMarginCalculator` — scenario-based initial margin + exposure margin
- Gate formula change from capital-utilisation to buying-power
- Constitution §8 "Margin-aware execution" fully satisfied only after MM9.4

### Intentionally Deferred (Beyond MM9)

- Inter-contract spread credits
- Per-order margin reservation ledger
- Assignment margin modeling
- `process_group_signal` gate coverage
- PnLTracker recovery gap (I.L.2)

---

## 9. Completion Checklist

```
MM9.1 — Basic Capital-Utilisation Gate
[x] MM9.1-S1 — ExecutionConfig.max_capital_utilisation field added  (COMPLETE 2026-06-26)
[x] MM9.1-S2 — _estimate_required_margin deterministic estimation helper  (COMPLETE 2026-06-26)
[x] MM9.1-S3 — _check_margin_budget gate + call site in process_signal + full test suite (578→598)  (COMPLETE 2026-06-26; plan's S4 "test suite" delivered bundled with S3)
[x] MM9.1-S4 — fno_runner.build_runner initial_capital propagation (598→600)  (COMPLETE 2026-06-26; plan's S5 renumbered S4; closes I.H.2 at API boundary)
[x] MM9.1     — PROJECT_STATE.md updated  (COMPLETE 2026-06-26)
[x] MM9.1     — CHANGELOG_PLATFORM.md entry added  (COMPLETE 2026-06-26)
[x] MM9.1     — DRIVER_SPECIFICATION.md §8.5 "Margin Gate" added  (COMPLETE 2026-06-26)

MM9.2 — Portfolio-Accurate Capital Controls
[x] MM9.2-S1 — Per-symbol price cache in ExecutionHandler  (COMPLETE 2026-06-27)
[x] MM9.2-S2 — MarginTracker multiplier fix (lot_size, zero-price guard)  (COMPLETE 2026-06-27)
[ ] MM9.2-S3 — Per-underlying notional cap gate
[x] MM9.2-S4 — _update_equity_metrics wired to fill path  (COMPLETE 2026-06-27)
[ ] MM9.2     — Documentation updated
[ ] MM9.2     — SESSION_BOOTSTRAP.md §"Current Gaps §8" updated

MM9.3 — Portfolio Exposure Controls
[x] MM9.3-S1A — Greek gate semantic correction (COMPLETE 2026-06-28)
[x] MM9.3-S1B — Portfolio Greek aggregation (COMPLETE 2026-06-28)
[x] MM9.3-S2 — PortfolioView runtime integration
[x] MM9.3-S3 — Drawdown gate I.M.2 full fix
[x] MM9.3     — Documentation updated

MM9.4 — SPAN Integration
[x] MM9.4-S1 — MarginCalculator protocol
[x] MM9.4-S2 — SPAN parameter sourcing
[x] MM9.4-S3 — SpanMarginCalculator implementation
[x] MM9.4-S4 — Buying-power gate formula
[x] MM9.4     — PLATFORM_CONSTITUTION.md §8 marked satisfied
[x] MM9.4     — ARCHITECTURE_DECISIONS.md ADR added
[x] MM9.4     — SESSION_BOOTSTRAP.md SPAN gap closed
[x] MM9.4     — PROJECT_STATE.md Planned #5 closed
```

---

## 10. Project State Update Recommendations

### PLATFORM_CONSTITUTION.md

No changes required now. After MM9.4: update §8 "Option Selling Requirements" to mark "Margin-aware execution" as satisfied with a reference to the SPAN milestone completion date.

### ARCHITECTURE_DECISIONS.md

No new ADRs required for MM9.1–MM9.3. The gate is in `ExecutionHandler` (consistent with ADR-006), is deterministic (ADR-003), and delegates to `MarginTracker` (ADR-001). These ADRs are not violated.

One new ADR is required in MM9.4: introduction of the `MarginCalculator` protocol (first protocol in `core/risk/`). It should record why the protocol was deferred until MM9.4 (YAGNI — only one implementation existed), and why `RiskManager` is not the owner (order-level vs portfolio-level control separation).

### PROJECT_STATE.md

After MM9.1-S3: change "Margin Check — MISSING" to "Margin Check — PARTIAL (MM9.1: single-symbol, flat-rate gate)." Add MM9.2–MM9.4 to deferred backlog. Retain "Live derivatives trading blocked on SPAN margin engine (Planned #5)" — MM9.1 does not satisfy the SPAN requirement.

### SESSION_BOOTSTRAP.md

After MM9.2 (not MM9.1): update "Current Gaps §8" from "MarginTracker flat 20% rate, not SPAN — insufficient for real option-selling margin" to "Margin gate: portfolio-aware flat-rate gate enforcing; remaining gap is SPAN (MM9.4)."

### CHANGELOG_PLATFORM.md

One entry per commit. Do not batch. Follow the existing format: date, milestone tag, one-line summary. The C1/C2/C3 corrections are implementation details; note them in the MM9.1-S2 and MM9.1-S3 entries.
