# MM9.3 Implementation Specification
## Portfolio Greeks Gate + PortfolioView Runtime Integration

**Status:** PENDING IMPLEMENTATION  
**Preceded by:** MM9.2 (COMPLETE, 696 tests passing)  
**Followed by:** MM9.4 (SPAN Margin Calculator)  
**Date drafted:** 2026-06-27  
**Revised:** 2026-06-27 (S1 split into S1A/S1B; §2 expanded with IV/TTE rationale, dual-PortfolioView rationale, and telemetry backward-compat contract)

---

## 1. Objective

MM9.3 delivers two infrastructure completions and one defect closure:

- **S1A — Greek Gate Semantic Correction:** Convert `_check_greek_limits` from crash-escalation
  to D4 rejection semantics. Bool return, EXIT bypass, `process_signal` call-site wiring.
  The existing marginal-only delta check is retained but no longer raises.
- **S1B — Portfolio Greek Aggregation:** Replace the marginal-only check with full portfolio-level
  Greek aggregation. Adds `_price_cache` projection, `PortfolioGreeks.calculate_portfolio_greeks()`
  call, IV/TTE fallback strategy, and combined limit checks across delta, vega, and gamma.
- **S2 — PortfolioView Runtime Integration:** Wire `PortfolioView.snapshot()` into the
  `LoopDriver` telemetry tick so the Flask dashboard receives live MTM equity, unrealized PnL,
  gross exposure, and used margin — replacing the raw `position_tracker` call.
- **S3 — Drawdown Gate I.M.2 Full Fix (conditional):** Replace the per-symbol equity
  approximation in the drawdown gate with `PortfolioView.snapshot().mtm_equity`, fully resolving
  defect I.M.2 (portfolio-wide equity in the drawdown check). Conditional: proceeds only when S1A,
  S1B, and S2 are green.

S1A is a prerequisite for S1B. S1B and S2 may be developed in parallel once S1A is merged.

---

## 2. Architectural Rationale

### 2.1 Why the Greek gate must change

`_check_greek_limits` (handler.py:964–1005) has three structural defects:

| Defect | Current Behaviour | Required Behaviour |
|--------|------------------|-------------------|
| Outcome | `raise ExecutionRuleError` (crash-escalation) | `return False` + `rejected_trades += 1` (D4 gate pattern) |
| Scope | Marginal signal delta only | Portfolio total + marginal signal (S1B) |
| Instrument | `InstrumentParser.parse()` legacy path | Intentionally retained at [9C] — see §2.3 |

Platform Constitution §8 mandates "Portfolio Greeks aggregation." The current gate satisfies
neither the platform contract nor the gate semantics established by MM9.1 (the margin gate model).

### 2.2 Gate semantics invariant

The D4 gate pattern (established by MM9.1 `_check_margin_budget`):

```
rejection  = return None + rejected_trades += 1 + WARNING log
escalation = raise ExecutionRuleError (reserved for data/config violations)
kill-switch = reserved for daily drawdown and daily trade limit only
```

The Greek gate is a **rejection gate**, not an escalation. Using `ExecutionRuleError` is
architecturally incorrect: it propagates as a 500-class error rather than a silent trade skip.
S1A fixes this in isolation so the call-site wiring can be reviewed independently before S1B adds
the portfolio computation.

### 2.3 IV/TTE Fallback Strategy — Core Architectural Decision

This section is promoted from a supporting appendix because the fallback strategy is a deliberate
architectural choice, not an implementation detail.

**The problem:** `PortfolioGreeks.calculate_portfolio_greeks()` requires `volatilities` and
`time_to_expiry_map` for all held positions. The MM9 plan lists "IV source available per position"
as a dependency. This dependency is NOT satisfied: no per-position IV cache exists at runtime.

**The decision:** Proceed with empty dicts. `PortfolioGreeks` already applies internal defaults:

```python
vol = volatilities.get(symbol, 0.20)      # 20% if not supplied
tte = time_to_expiry_map.get(symbol, 0.0) # 0.0 if not supplied
```

**Why TTE=0.0 is safe:** `Black76Engine.calculate_greeks(T=0)` at black76_engine.py:32–39:

```python
if T <= 0:
    delta = 1.0 if (CE and F > K) else (-1.0 if (PE and K > F) else 0.0)
    return Greeks(delta, 0.0, 0.0, 0.0, 0.0)  # intrinsic only, no division
```

No divide-by-zero. No exception. The engine is explicitly defensive at T≤0.

**Conservative impact by Greek type:**

| Greek | TTE=0 result | Gate consequence |
|-------|------------|-----------------|
| Delta | Intrinsic (±1 ITM, 0 OTM) | Over-estimates ITM delta → tighter gate (safe-side) |
| Gamma | 0 | Under-estimates → gamma limit may not trigger |
| Vega | 0 | Under-estimates → vega limit may not trigger |

Delta checking — the primary value of this gate for an equity/futures book — is correct and
conservative under TTE=0 defaults. Vega and gamma limits are degraded but not eliminated for
the marginal signal (which carries real IV/TTE from `signal.metadata`).

**False-trigger risk for equity positions:** Equity positions return `vega=0` from
`GreeksCalculator` regardless of IV (no vol exposure for equities). IV=0.20 default does not
trigger false vega breaches on an equity book.

**Known limitation:** The vega and gamma gates for held option positions with TTE=0 defaults are
effectively inactive. This is intentional and documented. True per-position IV sourcing is deferred
to MM9.5 (options data integration), where a per-symbol IV cache will be populated from
`OptionsProvider` on each bar tick.

**Path to full IV sourcing (MM9.5):** When the IV cache is live, `_check_greek_limits` passes the
cache instead of `{}` to `calculate_portfolio_greeks`, and the vega/gamma limits become meaningful
for held option positions.

### 2.4 Two PortfolioView Instances — Intentional Design

MM9.3 creates two `PortfolioView` instances that wrap the same three trackers:

| Instance | Attribute | Owner | Purpose | Triggered by |
|----------|-----------|-------|---------|-------------|
| `self._handler_portfolio_view` | `ExecutionHandler` | Handler | Runtime risk decision (drawdown gate) | Per signal in `process_signal` |
| `self._portfolio_view` | `LoopDriver` | Driver | Telemetry projection (Flask dashboard) | Per telemetry cadence in `_drive_telemetry` |

Both wrap `position_tracker`, `pnl_tracker`, and `margin_tracker` from the same
`ExecutionHandler`. `PortfolioView.snapshot()` is a pure read — it does not modify any tracker
state. Two instances sharing the same trackers introduce no shared mutable state and do not violate
ADR-001 (Ledger Is Truth): both read from the ledger, neither writes to it.

**Why not one shared instance?**

- The handler's instance must be available synchronously at signal-processing time, before any
  LoopDriver involvement.
- The driver's instance is triggered asynchronously during the telemetry cadence, which may lag
  signal processing.
- Constructing the instance only in the driver and injecting it back into the handler would require
  the handler to depend on the driver, violating ADR-006 (LoopDriver is sole runtime orchestrator).

The cost is two heap objects holding the same three tracker references. This is negligible.

### 2.5 Telemetry Payload Backward Compatibility

S2 enriches the `_build_positions()` payload with new keys (`mtm_equity`, `realized_pnl`,
`unrealized_pnl`, `gross_exposure`, `used_margin`). Existing consumers are unaffected:

- Python dict consumers accessing named keys (`payload['positions']`, `payload['cash_balance']`)
  are unaffected by the addition of new keys — unknown keys are silently ignored.
- The SSE publisher serialises the payload to JSON; additional keys are serialised, not dropped.
- Flask blueprint template bindings on existing keys continue to work without modification.

**One exception:** Any test that asserts the exact key-set of the payload using
`assert payload.keys() == {...}` will need updating to use subset or `assertIn` checks. Before S2
proceeds, search `tests/runtime/` for exact key-set assertions on the positions payload and update
them.

### 2.6 Why PortfolioView belongs in LoopDriver

`PortfolioView` is a read-only projection (ADR-001: Ledger Is Truth). It does not modify
`position_tracker`, `pnl_tracker`, or `margin_tracker`. Injecting it into the LoopDriver provides
the telemetry layer with a structured snapshot without coupling the driver to internal tracker
state directly. ADR-006 (LoopDriver is sole runtime orchestrator) is satisfied: data flows
read-only from execution → driver → telemetry bus.

### 2.7 Gate ordering (post-MM9.3)

```
[PHASE 0]  Authority enforcement + idempotency
[TLP]      Risk metadata validation (sl_dist, risk_r)
[0]        STOP file / kill switch file check
[1]        signals_received += 1
[2]        Kill switch state check → return None
[3]        Daily trade limit → kill switch + return None
[4]        Drawdown check → kill switch + return None  ← S3 upgrades equity here
[4b]       Position stacking guard (non-EXIT) → return None
[5]        _check_risk_limits → ExecutionRuleError
[9C]       _check_greek_limits → return None  (S1A fixes semantics; S1B adds aggregation)
[TLP]      Structural context capture
[PHASE 1]  Instrument resolution + NormalizedOrder construction
[PHASE 2]  RiskManager.evaluate → rejected_trades += 1 + ExecutionRuleError
[PRICEABLE] _check_book_priceable() — EXIT bypasses (MM9.2-S3)
[MARGIN]   _check_margin_budget() — EXIT bypasses (MM9.1)
[PHASE 5]  order_tracker.add_order(order)
[PHASE 7]  broker.place_order(order)
```

The Greek gate remains at [9C] — before instrument resolution. Rationale: the gate is a
lightweight early-exit screen; `InstrumentParser.parse()` is acceptable at [9C] since only
asset-class dispatch is needed, not broker-resolution (PHASE 1). EXIT signals bypass the gate via
an early return inside `_check_greek_limits`.

---

## 3. Repository Impact Review

### 3.1 Files modified

| File | Slice | Change |
|------|-------|--------|
| `core/execution/handler.py` | S1A, S1B, S3 | S1A: semantics fix + call-site; S1B: portfolio aggregation body; S3: `_handler_portfolio_view` + drawdown gate |
| `core/runtime/driver.py` | S2 | `__init__` accepts `Optional[PortfolioView]`; `_build_positions()` uses snapshot |
| `scripts/fno_runner.py` | S2 | Constructs and injects `PortfolioView` into `LoopDriver` |

### 3.2 Files NOT modified

| File | Reason |
|------|--------|
| `core/execution/portfolio_view.py` | Complete and tested; no change needed |
| `core/risk/greeks/portfolio_greeks.py` | Complete and tested; no change needed |
| `core/risk/greeks/greeks_calculator.py` | Complete and tested; no change needed |
| `core/risk/greeks/black76_engine.py` | Complete; T=0 path already safe (line 32–39) |
| `core/execution/config.py` | Greek limit fields already defined |

### 3.3 New files

None. All required classes exist.

### 3.4 Test files

| File | Slice | Change |
|------|-------|--------|
| `tests/execution/test_greek_limits.py` | S1A, S1B | New — 6 S1A tests + 7 S1B tests = 13 total |
| `tests/execution/test_handler.py` | S1A | Confirm no `ExecutionRuleError` from greek gate |
| `tests/runtime/test_driver_portfolio_view.py` | S2 | New — 7 PortfolioView telemetry tests |
| `tests/execution/test_drawdown_gate.py` | S3 | Confirm `mtm_equity` used in gate |

---

## 4. Dependency Validation

All MM9.3 dependencies are confirmed landed:

| Dependency | Status | Evidence |
|------------|--------|---------|
| MM9.1 `_check_margin_budget` (D4 pattern) | COMPLETE | handler.py margin gate, returns None |
| MM9.2 `_price_cache: Dict[str, PriceSnapshot]` | COMPLETE | handler.py, MM9.2-S3 |
| MM9.2 `_update_equity_metrics` + accurate `cash_balance` | COMPLETE | MM9.2-S4 |
| `PortfolioGreeks.calculate_portfolio_greeks()` | COMPLETE | portfolio_greeks.py, dict-key bug fixed Phase 0 |
| `self.portfolio_greeks` in handler | COMPLETE | handler.py:203 |
| `PortfolioView.snapshot()` | COMPLETE | portfolio_view.py, Phase 1 |
| `GreeksCalculator.calculate()` for Equity/Future/Option | COMPLETE | greeks_calculator.py, 4C.6 |
| `Black76Engine` T=0 safety | CONFIRMED | black76_engine.py:32–39 — intrinsic, no divide-by-zero |
| `ExecutionConfig.max_portfolio_delta/vega/gamma_exposure` | COMPLETE | config.py |

**Unresolved dependency (documented, resolved via fallback — see §2.3):**  
MM9 plan lists "IV source available per position" as a dependency for S1B. Resolved by passing
empty dicts to `calculate_portfolio_greeks()`, which applies 20% IV / 0.0 TTE defaults internally.
True per-position IV sourcing deferred to MM9.5 (options data integration). Delta limit enforcement
is sound. Vega/gamma limits for held option positions are degraded until MM9.5.

---

## 5. Implementation Slices

### Slice S1A: Greek Gate Semantic Correction

**File:** `core/execution/handler.py`  
**Dependency:** None (first slice)  
**Scope:** Fix semantics only. After S1A, `_check_greek_limits` still performs only a marginal
delta check — but it no longer raises, it returns bool, and the call site is wired correctly.
The marginal-only scope is a documented interim state; S1B replaces the check body entirely.

#### S1A.1 — Signature change

Current: `_check_greek_limits(self, signal, current_price) -> None`  
Target:  `_check_greek_limits(self, signal: SignalEvent, current_price: float) -> bool`

Returns `True` = signal allowed, `False` = rejected (caller returns None from `process_signal`).

#### S1A.2 — EXIT bypass

First statement in the method body:

```python
if signal.signal_type == SignalType.EXIT:
    return True  # reducing risk is always allowed
```

Rationale: EXIT signals reduce portfolio exposure. Greek limits must never block position closure.

#### S1A.3 — Convert raise to rejection

Replace the existing `raise ExecutionRuleError(...)` with D4 pattern:

```python
if abs(new_greeks.delta) > self.config.max_portfolio_delta:
    self.metrics.rejected_trades += 1
    logger.warning("[%s] Greek delta breach (marginal): %.1f vs limit %.1f",
                   self.runner_id, new_greeks.delta, self.config.max_portfolio_delta)
    return False
return True
```

The remainder of the existing method body (the `InstrumentParser.parse()` call, quantity
calculation, and `GreeksCalculator.calculate()` call for the marginal delta) is kept intact.
S1B will replace this body in full.

#### S1A.4 — Call site change in `process_signal`

At handler.py:613 (current: `self._check_greek_limits(signal, current_price)` with no return
value captured):

```python
if not self._check_greek_limits(signal, current_price):
    return None
```

The call site is NOT inside an `if signal.signal_type != SignalType.EXIT:` guard — the EXIT
bypass is handled inside `_check_greek_limits` itself (S1A.2), consistent with how
`_check_risk_limits` is structured.

---

### Slice S1B: Portfolio Greek Aggregation

**File:** `core/execution/handler.py`  
**Dependency:** S1A complete and merged.  
**Scope:** Replace the marginal-only body of `_check_greek_limits` (left by S1A) with full
portfolio-level Greek aggregation. The signature, EXIT bypass, and call site established in S1A
are unchanged.

#### S1B.1 — Current portfolio Greeks computation

```python
market_prices = {sym: snap.price for sym, snap in self._price_cache.items()}
current_pf_greeks = self.portfolio_greeks.calculate_portfolio_greeks(
    market_prices=market_prices,
    volatilities={},           # empty dict → PortfolioGreeks uses 0.20 default per position
    time_to_expiry_map={},     # empty dict → PortfolioGreeks uses 0.0 default per position
    risk_free_rate=0.05
)
```

**Empty book case:** If `position_tracker.get_all_positions()` is empty, `current_pf_greeks` is
all-zero Greeks. Only the marginal signal is checked. Correct.

**Empty `_price_cache` case:** Safe at startup — positions can only exist after bars have been
received and processed, which populates `_price_cache` first.

#### S1B.2 — Marginal signal Greeks computation

```python
meta = signal.metadata or {}

# TODO(MM10): Migrate from InstrumentParser to canonical InstrumentResolver if PHASE 1
# gate ordering changes. InstrumentParser.parse() is intentionally retained here because
# this gate runs at [9C], before PHASE 1 instrument resolution. Asset-class dispatch only
# is needed (Equity / Future / Option); broker-resolution is not. Changing this before
# PHASE 1 ordering changes would create a race with the canonical resolution path.
instrument = InstrumentParser.parse(signal.symbol)

qty = self._calculate_position_size(signal, current_price)
if signal.signal_type == SignalType.SELL:
    qty = -qty

from core.risk.greeks.greeks_calculator import GreeksCalculator
marginal_greeks = GreeksCalculator.calculate(
    instrument=instrument,
    quantity=qty,
    underlying_price=meta.get('underlying_price', current_price),
    volatility=meta.get('iv', 0.20),
    time_to_expiry=meta.get('tte', 0.0)
)
```

The TODO comment is intentional — it prevents well-meaning future refactoring from migrating
`InstrumentParser.parse()` to the canonical resolver before the gate ordering supports it.
Remove the TODO only when PHASE 1 is moved above [9C] (expected MM10 or later).

#### S1B.3 — Combined limit check

```python
combined_delta = current_pf_greeks.delta + marginal_greeks.delta
combined_vega  = current_pf_greeks.vega  + marginal_greeks.vega
combined_gamma = current_pf_greeks.gamma + marginal_greeks.gamma

breaches = []
if abs(combined_delta) > self.config.max_portfolio_delta:
    breaches.append(f"delta {combined_delta:.1f} vs limit {self.config.max_portfolio_delta}")
if abs(combined_vega) > self.config.max_portfolio_vega:
    breaches.append(f"vega {combined_vega:.1f} vs limit {self.config.max_portfolio_vega}")
if abs(combined_gamma) > self.config.max_gamma_exposure:
    breaches.append(f"gamma {combined_gamma:.1f} vs limit {self.config.max_gamma_exposure}")

if breaches:
    self.metrics.rejected_trades += 1
    logger.warning("[%s] Greek limits breached: %s", self.runner_id, "; ".join(breaches))
    return False

return True
```

---

### Slice S2: PortfolioView Runtime Integration

**Files:** `core/runtime/driver.py`, `scripts/fno_runner.py`  
**Dependency:** S1A complete (S1B may be in parallel).

#### S2.1 — LoopDriver constructor

Add `Optional[PortfolioView]` parameter:

```python
from typing import Optional
from core.execution.portfolio_view import PortfolioView

class LoopDriver:
    def __init__(self, ..., portfolio_view: Optional[PortfolioView] = None):
        ...
        self._portfolio_view = portfolio_view
```

Optional parameter ensures backward compatibility: existing test instantiations of `LoopDriver`
that omit `portfolio_view` continue to work with degraded telemetry (§2.5).

#### S2.2 — `_build_positions()` enriched path

```python
def _build_positions(self) -> dict:
    if self._portfolio_view is not None:
        prices = {sym: snap.price for sym, snap in self._execution._price_cache.items()}
        cash = self._execution.metrics.cash_balance
        snapshot = self._portfolio_view.snapshot(prices, cash)
        positions_payload = {}
        for sym, pos in snapshot.positions.items():
            current_price = prices.get(sym, pos.average_price)
            pnl_pct = (
                (current_price - pos.average_price) / pos.average_price * 100
                if pos.average_price != 0 else 0.0
            )
            positions_payload[sym] = {
                'quantity': pos.quantity,
                'average_price': pos.average_price,
                'current_price': current_price,
                'pnl_pct': pnl_pct,
            }
        return {
            'positions': positions_payload,
            'cash_balance': snapshot.cash_balance,
            'realized_pnl': snapshot.realized_pnl,
            'unrealized_pnl': snapshot.unrealized_pnl,
            'mtm_equity': snapshot.mtm_equity,
            'gross_exposure': snapshot.gross_exposure,
            'used_margin': snapshot.used_margin,
        }
    # Degraded fallback: pre-S2 behaviour
    positions = self._execution.position_tracker.get_all_positions()
    return {
        'positions': {
            sym: {'quantity': pos.quantity, 'average_price': pos.average_price}
            for sym, pos in positions.items()
        }
    }
```

The coupling to `self._execution._price_cache` is a pre-existing §10.7 private-attribute
coupling, already accepted in DRIVER_SPEC §10.7 for infra-to-infra links.

This also resolves the DRIVER_SPEC §10.4 `pnl_pct: 0.0` placeholder: `pnl_pct` is now computed
per position from `(current_price - average_price) / average_price * 100`.

#### S2.3 — Startup warning when PortfolioView not injected

In `LoopDriver.__init__`, after assigning `self._portfolio_view`:

```python
if self._portfolio_view is None:
    logger.warning("[%s] PortfolioView not injected — telemetry will use degraded position payload",
                   self.runner_id)
```

Prevents silent degraded telemetry going unnoticed (see F5 in §7).

#### S2.4 — fno_runner.py composition root

After constructing `execution_handler` and before constructing `driver`:

```python
from core.execution.portfolio_view import PortfolioView

portfolio_view = PortfolioView(
    position_tracker=execution_handler.position_tracker,
    pnl_tracker=execution_handler.pnl_tracker,
    margin_tracker=execution_handler.margin_tracker,
)
driver = LoopDriver(..., portfolio_view=portfolio_view)
```

This is the first of the two `PortfolioView` instances described in §2.4. The handler's instance
(`_handler_portfolio_view`) is added in S3.

#### S2.5 — Watchdog heartbeat equity (deferred)

DRIVER_SPEC §9.4 heartbeat uses `equity = execution.metrics.cash_balance` (known simplification).
S2 does NOT change the watchdog heartbeat path. After MM9.2-S4, `cash_balance` correctly tracks
realized PnL. The `mtm_equity` fix for the watchdog heartbeat is deferred to keep S2 scope
bounded. Document DRIVER_SPEC §9.4 as "partially resolved": the telemetry stream now carries
`mtm_equity`; the watchdog heartbeat equity fix remains outstanding.

---

### Slice S3: Drawdown Gate I.M.2 Full Fix (Conditional)

**Precondition:** S1A, S1B, and S2 complete, test suite green (≥ 696 + all new tests).

**File:** `core/execution/handler.py`

#### S3.1 — `PortfolioView` on the handler

In `ExecutionHandler.__init__`, after constructing the three trackers:

```python
from core.execution.portfolio_view import PortfolioView

self._handler_portfolio_view = PortfolioView(
    self.position_tracker,
    self.pnl_tracker,
    self.margin_tracker,
)
```

This is the second `PortfolioView` instance (see §2.4 for the intentional-design rationale).
Both this instance and the driver's instance are read-only projections of the same three trackers.
ADR-001 (Ledger Is Truth) is not violated: both read; neither writes.

#### S3.2 — Drawdown gate update in `process_signal`

Locate the drawdown equity calculation (~line 590):

```python
# Current (signal-symbol approximation — I.M.2 defect):
current_equity = self.metrics.cash_balance + net_qty * current_price
```

Replace with:

```python
# Full portfolio MTM equity (I.M.2 fix):
_prices = {sym: snap.price for sym, snap in self._price_cache.items()}
current_equity = self._handler_portfolio_view.snapshot(
    _prices, self.metrics.cash_balance
).mtm_equity
```

`mtm_equity = cash_balance + unrealized_pnl` where `unrealized_pnl` sums ALL held positions.
This fully resolves I.M.2.

**Edge case — empty `_price_cache`:** Safe: positions can only exist after bars are received.
At startup with no positions, `unrealized_pnl = 0` and `mtm_equity = cash_balance`. Drawdown
gate behaviour is unchanged from the empty-book baseline.

---

## 6. Behavioral Contracts

### 6.1 `_check_greek_limits` post-S1A (interim state)

| Pre-condition | Action | Outcome |
|--------------|--------|---------|
| `signal.signal_type == EXIT` | Early return | `True` — gate passes |
| `abs(marginal_delta) ≤ max_portfolio_delta` | Return | `True` — gate passes |
| `abs(marginal_delta) > max_portfolio_delta` | `rejected_trades += 1`, WARNING | `False` → `process_signal` returns `None` |
| Any input | No exception raised | Guaranteed — `ExecutionRuleError` removed |

**Invariant post-S1A:** The gate NEVER raises. It checks only marginal delta (known interim
limitation). This state is transitional; S1B replaces the check body.

### 6.2 `_check_greek_limits` post-S1B (target state)

| Pre-condition | Action | Outcome |
|--------------|--------|---------|
| `signal.signal_type == EXIT` | Early return | `True` — gate passes |
| Combined Greeks within all limits | Compute and return | `True` — gate passes |
| `abs(combined_delta) > max_portfolio_delta` | `rejected_trades += 1`, WARNING | `False` → `process_signal` returns `None` |
| `abs(combined_vega) > max_portfolio_vega` | `rejected_trades += 1`, WARNING | `False` → `process_signal` returns `None` |
| `abs(combined_gamma) > max_gamma_exposure` | `rejected_trades += 1`, WARNING | `False` → `process_signal` returns `None` |
| Multiple limits breached simultaneously | Single rejection, all breach detail in one WARNING | `False` |
| Empty position book | `current_pf_greeks` = zero; only marginal checked | `True` if marginal within limits |
| `_price_cache` empty | `market_prices = {}`; PortfolioGreeks uses 0 prices | Safe (no positions at startup) |
| `signal.metadata` absent | `iv=0.20`, `tte=0.0`, `underlying_price=current_price` applied | Correct |

**Invariant post-S1B:** The gate NEVER raises. Portfolio Greeks plus marginal Greeks are checked
against all three limits. IV/TTE defaults apply per §2.3.

### 6.3 `PortfolioView.snapshot()` in driver (post-S2)

| Pre-condition | Telemetry payload | Notes |
|--------------|-------------------|-------|
| `portfolio_view` injected | Rich: `mtm_equity`, `unrealized_pnl`, `gross_exposure`, `used_margin`, real `pnl_pct` | Production path |
| `portfolio_view` not injected (None) | Degraded: raw positions dict only | Backward compat; tests; WARNING logged |
| No open positions | All PnL fields = 0.0; `mtm_equity = cash_balance` | Correct |
| Price missing for a position | `PortfolioView.snapshot()` uses 0.0 for missing price | Degrade gracefully |

**Backward compatibility (§2.5):** Adding `mtm_equity`, `realized_pnl`, `unrealized_pnl`,
`gross_exposure`, `used_margin` to the payload is safe for all existing consumers. Before S2
is merged, search `tests/runtime/` for exact key-set assertions and convert to subset checks.

### 6.4 Drawdown gate (post-S3)

| Pre-condition | `current_equity` value | I.M.2 status |
|--------------|----------------------|--------------|
| Single-symbol book | `cash + unrealized(symbol)` | Equivalent to pre-S3 |
| Multi-symbol book | `cash + Σ unrealized(all positions)` | RESOLVED |
| Empty book | `cash_balance` (no unrealized) | Correct |

---

## 7. Failure Modes and Mitigations

| # | Failure | Severity | Mitigation |
|---|---------|----------|-----------|
| F1 | `InstrumentParser.parse()` returns unknown type → `GreeksCalculator` returns zero Greeks | Medium | Zero marginal Greeks → gate does not reject. Over-permissive, not dangerous. TODO comment (S1B.2) flags future migration path. |
| F2 | `_price_cache` contains stale prices (no bar received for a symbol recently) | Low | PortfolioGreeks uses last-seen price. Staleness bounded by bar cadence (1 min). |
| F3 | `position_tracker.get_all_positions()` raises inside `PortfolioGreeks` | High | Exception propagates to `process_signal`. Gate defect, not system defect; investigate. |
| F4 | `PortfolioView.snapshot()` called with empty `_price_cache` at startup | Low | No open positions at startup → PnL = 0. Safe. |
| F5 | `PortfolioView` not injected into driver (omitted in fno_runner) | Medium | Startup WARNING log (S2.3) makes this visible. Degraded telemetry, not a crash. |
| F6 | `position.average_price == 0` → `pnl_pct` divide-by-zero | Low | Guard in S2.2: `if pos.average_price != 0 else 0.0`. |
| F7 | Multiple Greek breaches log only one WARNING | Low | All breaches included in a single message — acceptable. |
| F8 | `_handler_portfolio_view` (S3) and driver's `portfolio_view` share trackers | None | Both are read-only projections — no state conflict. See §2.4 for rationale. |
| F9 | IV=0.20 default causes false vega trigger on equity book | None | Equity positions return `vega=0` from `GreeksCalculator`. Default IV activates only for option positions. |
| F10 | TTE=0.0 default makes vega/gamma limits inactive for held option positions | High | Documented known limitation (§2.3). Delta is sound. Full fix is MM9.5 prerequisite. |
| F11 | Exact key-set assertion in existing tests breaks on S2 payload enrichment | Low | Pre-S2 audit of `tests/runtime/` required (§2.5). Convert exact-set assertions to subset checks. |

---

## 8. Testing Strategy

### 8.1 TDD Order (Red-Green-Refactor)

Write tests first. Production code follows. Each test must be red before implementation begins.

**S1A test order (6 tests — semantic correction):**
1. `test_greek_gate_never_raises_on_delta_breach`
2. `test_greek_gate_returns_bool`
3. `test_greek_gate_bypasses_exit_signal`
4. `test_process_signal_returns_none_when_greek_gate_rejects`
5. `test_greek_gate_increments_rejected_trades`
6. `test_greek_gate_logs_warning_on_breach`

**S1B test order (7 tests — portfolio aggregation):**
1. `test_greek_gate_returns_true_on_empty_book`
2. `test_greek_gate_returns_false_on_portfolio_delta_breach`
3. `test_greek_gate_returns_false_on_vega_breach`
4. `test_greek_gate_returns_false_on_gamma_breach`
5. `test_greek_gate_uses_price_cache_for_market_prices`
6. `test_greek_gate_uses_signal_metadata_iv_for_marginal`
7. `test_greek_gate_defaults_iv_when_metadata_absent`

**S2 test order (7 tests):**
1. `test_driver_accepts_optional_portfolio_view`
2. `test_build_positions_rich_payload_when_view_injected`
3. `test_build_positions_degraded_when_no_view`
4. `test_mtm_equity_in_telemetry_payload`
5. `test_realized_pnl_in_telemetry_payload`
6. `test_gross_exposure_in_telemetry_payload`
7. `test_used_margin_in_telemetry_payload`

**S3 test order (2 tests):**
1. `test_drawdown_gate_uses_mtm_equity_multi_symbol`
2. `test_drawdown_gate_fires_on_portfolio_loss_not_single_symbol`

### 8.2 Characterization tests

Write these against the UNCHANGED codebase before implementing S1A. They lock current broken
behaviour as a baseline.

```
test_current_greek_gate_raises_executionruleerror_on_delta_breach   [DELETE AFTER S1A]
test_current_greek_gate_checks_only_marginal_not_portfolio           [DELETE AFTER S1B]
```

Note: the first characterization test is deleted after S1A (semantics fixed). The second is
deleted after S1B (portfolio scope fixed). The second test is intentionally left alive through
the S1A→S1B interval: it documents a known interim limitation.

### 8.3 Unit tests — new files

**`tests/execution/test_greek_limits.py`** (13 tests — 6 S1A + 7 S1B)

S1A tests mock only `_check_greek_limits` inputs (signal, current_price) and assert on
return type, raised exceptions (must be none), rejected_trades counter, and log output.

S1B tests additionally mock `self.portfolio_greeks.calculate_portfolio_greeks` and
`self._price_cache`. Use `ExecutionConfig` with tight limits (e.g. `max_portfolio_delta=10.0`)
to trigger breaches without realistic position sizes.

**`tests/runtime/test_driver_portfolio_view.py`** (7 tests, S2)

Construct `LoopDriver` with and without a mock `PortfolioView`. Assert on the dict returned by
`_build_positions()` directly. No real telemetry bus required.

Pre-S2 audit: run `grep -r "payload.keys()" tests/runtime/` and convert exact key-set
assertions to subset checks before S2 proceeds.

### 8.4 Integration tests

```
tests/execution/test_handler_integration.py::test_process_signal_greek_gate_rejects_large_position
  - Create handler, set max_portfolio_delta=10.0
  - Submit BUY signal for 100 shares of equity
  - Assert process_signal returns None
  - Assert rejected_trades == 1

tests/execution/test_handler_integration.py::test_process_signal_greek_gate_passes_exit
  - Build book with delta near limit
  - Submit EXIT signal for the same symbol
  - Assert process_signal does not return None at the greek gate step

tests/integration/test_portfolio_view_driver.py::test_driver_telemetry_has_portfolio_snapshot
  - Construct handler + PortfolioView + LoopDriver
  - Process one FillEvent
  - Call _build_positions() directly
  - Assert mtm_equity == cash_balance + unrealized
```

### 8.5 Regression guard

`tests/execution/test_fno_runner_composition.py:81,87` (cash_balance == initial_capital at
construction) remain valid — no fills at construction time.

After S3, add:

```
test_drawdown_gate_im2_multi_position_full_equity
  - Open positions on SYMBOL_A and SYMBOL_B
  - Inject prices showing combined unrealized loss exceeding drawdown threshold
  - Submit a new signal for SYMBOL_B
  - Assert drawdown gate fires using portfolio-wide equity, not SYMBOL_B alone
```

---

## 9. Acceptance Criteria

### S1A — Greek Gate Semantic Correction

- [ ] `_check_greek_limits` return type is `bool` — never raises, never returns `None`
- [ ] EXIT signal: always returns `True`, remaining body is not executed
- [ ] Delta breach (marginal): returns `False`, `rejected_trades += 1`, WARNING log
- [ ] Call site: `if not self._check_greek_limits(signal, current_price): return None`
- [ ] `ExecutionRuleError` not raised in `_check_greek_limits` (grep-verified)
- [ ] All 6 S1A tests green; suite ≥ 696 passing
- [ ] Characterization test 1 deleted

### S1B — Portfolio Greek Aggregation

- [ ] Empty book: gate passes (combined Greeks = marginal only)
- [ ] Delta breach on combined portfolio + marginal: `rejected_trades += 1`, WARNING, return `False`
- [ ] Vega breach: `rejected_trades += 1`, WARNING, return `False`
- [ ] Gamma breach: `rejected_trades += 1`, WARNING, return `False`
- [ ] Multiple breaches: single rejection, all details in one log entry
- [ ] `_price_cache` projected to `market_prices` dict and passed to `portfolio_greeks`
- [ ] Signal metadata `iv` / `tte` used for marginal Greeks; defaults applied when absent
- [ ] TODO comment present on `InstrumentParser.parse()` line per S1B.2
- [ ] All 7 S1B tests green; suite ≥ 696 passing
- [ ] Characterization test 2 deleted

### S2 — PortfolioView Runtime Integration

- [ ] `LoopDriver.__init__` accepts `Optional[PortfolioView] = None`
- [ ] Startup WARNING logged when `portfolio_view` is None
- [ ] `_build_positions()` returns enriched payload (`mtm_equity`, `realized_pnl`,
  `unrealized_pnl`, `gross_exposure`, `used_margin`, real `pnl_pct`) when view is not None
- [ ] `_build_positions()` falls back to degraded dict when view is None
- [ ] `fno_runner.py` constructs `PortfolioView` from handler trackers and injects
- [ ] Pre-S2 audit of `tests/runtime/` for exact key-set assertions completed; conversions done
- [ ] All 7 S2 tests green; suite ≥ 696 passing
- [ ] DRIVER_SPEC §10.4 `pnl_pct` placeholder status updated

### S3 — Drawdown Gate I.M.2 Full Fix (conditional)

- [ ] S1A, S1B, S2 complete and green first
- [ ] `ExecutionHandler.__init__` constructs `self._handler_portfolio_view`
- [ ] Drawdown gate uses `_handler_portfolio_view.snapshot(...).mtm_equity`
- [ ] I.M.2 regression test passes
- [ ] All 2 S3 tests green; suite ≥ 696 passing

---

## 10. Documentation Updates Required

### 10.1 `docs/DRIVER_SPECIFICATION.md`

- **§8 Greek gate:** Update from "no live caller; dead code path" to "functional portfolio-level
  Greek aggregation gate at [9C]; IV/TTE defaults documented; vega/gamma limits degraded until
  MM9.5."
- **§9.4 Heartbeat equity:** Update "known simplification" note — telemetry stream now carries
  `mtm_equity` (S2); watchdog heartbeat equity fix remains outstanding (deferred).
- **§10.4 `publish_positions`:** Remove `pnl_pct: 0.0` placeholder note; document real MTM
  values now published via `PortfolioSnapshot`.
- **§10.7 Private-attribute coupling:** Add `_price_cache` (accessed in `_build_positions()` via
  `self._execution._price_cache`) to the accepted coupling table.

### 10.2 `docs/PROJECT_STATE.md`

- Move MM9.3 from "Remaining" to "COMPLETE" under MM9 In Progress.
- Update test count post-MM9.3.
- Add I.M.2 to resolved defects (post-S3).
- Note IV fallback strategy and MM9.5 as the path to full Greek coverage.

### 10.3 `docs/reports/MM9_IMPLEMENTATION_PLAN.md`

- Mark `[ ] MM9.3-S1`, `[ ] MM9.3-S2`, `[ ] MM9.3 Documentation updated` as complete.
- Add note: "MM9.3-S1 split into S1A (semantic correction) and S1B (portfolio aggregation)."
- Add note under §4 MM9.3 dependencies: "IV source available per position — resolved via
  TTE=0.0/IV=0.20 defaults; true per-position IV deferred to MM9.5."

### 10.4 `docs/CHANGELOG.md`

- Add MM9.3 entry: Greek gate semantic correction (S1A), portfolio Greek aggregation (S1B),
  PortfolioView runtime integration (S2), I.M.2 full fix (S3 if complete).

### 10.5 `docs/ARCHITECTURE_DECISIONS.md`

- No new ADRs required for MM9.3.
- Add design note on intentional dual `PortfolioView` instances (§2.4) under the "Execution
  Owns Reality" principle — both instances are read-only projections; the separation enforces
  the handler ↔ driver layering constraint.
- Add design note on IV fallback strategy (§2.3) under the "Analytics Produce Facts" principle —
  IV is an analytics concern; execution uses defaults until MM9.5 wires the options provider.

---

## 11. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|-----------|
| R1 | `InstrumentParser.parse()` wrong asset class post-G1 for a symbol format | Medium | Gate underestimates Greeks silently | TODO comment in S1B.2 flags migration path; add assertion test |
| R2 | Position symbol ≠ price cache key → market_prices miss for that position | Low | Zero price → Black76 delta=0 (underestimate) | Document symbol key convention; add test |
| R3 | `_handler_portfolio_view` (S3) and driver's `portfolio_view` share trackers | None | No conflict — both read-only; see §2.4 | ADR-001 compliant; add inline comment in S3.1 |
| R4 | fno_runner omits PortfolioView injection | Medium | Degraded telemetry silently | Startup WARNING log (S2.3) catches this |
| R5 | TTE=0.0 default makes vega/gamma limits ineffective for option books | High | Limits not enforced | Documented §2.3; MM9.5 prerequisite flag |
| R6 | `_calculate_position_size()` called at [9C] and again in PHASE 1 (duplicate computation) | Low | Performance — negligible for intraday | Acceptable; sizing is deterministic and fast |
| R7 | `max_portfolio_delta=1000.0` default too generous to catch real breaches | Low | Over-permissive gate | Leave defaults as-is; require explicit tightening in config |
| R8 | Exact key-set assertion in existing tests breaks on S2 payload enrichment | Low | S2 tests fail unexpectedly | Pre-S2 audit required (§2.5, §8.3) |
| R9 | S1B merged before S1A complete — TODO comment references non-existent interim state | Low | Confusion during code review | Enforce merge order: S1A must precede S1B |

---

## 12. Completion Checklist

### Pre-implementation
- [ ] Read `handler.py` `_check_greek_limits` body and call site (lines 964–1005, 613)
- [ ] Read `driver.py` `_build_positions()` current implementation (line 752)
- [ ] Read `portfolio_view.py` `PortfolioView.snapshot()` signature
- [ ] Read `portfolio_greeks.py` `calculate_portfolio_greeks()` default handling
- [ ] Confirm baseline test count ≥ 696
- [ ] Audit `tests/runtime/` for exact key-set assertions on positions payload (for S2 compat)

### S1A — Greek Gate Semantic Correction
- [ ] Characterization test 1 written (`raises_executionruleerror`) — red
- [ ] 6 S1A unit tests written — all red
- [ ] `_check_greek_limits` signature → `bool`
- [ ] EXIT bypass added
- [ ] `raise ExecutionRuleError(...)` replaced with `rejected_trades += 1` + WARNING + `return False`
- [ ] Call site in `process_signal` updated to `if not self._check_greek_limits(...): return None`
- [ ] All 6 S1A tests green
- [ ] Characterization test 1 deleted
- [ ] Suite ≥ 696 still passing
- [ ] `grep ExecutionRuleError core/execution/handler.py` shows no match inside `_check_greek_limits`

### S1B — Portfolio Greek Aggregation
- [ ] Characterization test 2 written (`checks_only_marginal`) — red
- [ ] 7 S1B unit tests written — all red
- [ ] S1B.1: `_price_cache` projection + `portfolio_greeks.calculate_portfolio_greeks()` call
- [ ] S1B.2: marginal greeks with TODO comment on `InstrumentParser.parse()`
- [ ] S1B.3: combined check for delta + vega + gamma
- [ ] All 7 S1B tests green
- [ ] Characterization test 2 deleted
- [ ] Suite ≥ 696 still passing

### S2 — PortfolioView Runtime Integration
- [ ] Pre-S2 exact key-set audit completed
- [ ] 7 S2 unit tests written — all red
- [ ] `LoopDriver.__init__` accepts `Optional[PortfolioView]`; startup WARNING added
- [ ] `_build_positions()` enriched/degraded paths implemented
- [ ] `fno_runner.py` constructs and injects `PortfolioView`
- [ ] All 7 S2 tests green
- [ ] Suite ≥ 696 still passing
- [ ] Telemetry payload contains `mtm_equity` in integration test

### S3 — Drawdown Gate I.M.2 Full Fix (conditional)
- [ ] S1A + S1B + S2 confirmed complete and green
- [ ] 2 S3 tests written — red
- [ ] `_handler_portfolio_view` added to `ExecutionHandler.__init__` with ADR-001 comment
- [ ] Drawdown gate uses `mtm_equity`
- [ ] All 2 S3 tests green
- [ ] I.M.2 regression test passes
- [ ] Suite ≥ 696 still passing

### Documentation
- [ ] DRIVER_SPEC §8, §9.4, §10.4, §10.7 updated
- [ ] PROJECT_STATE.md MM9.3 moved to COMPLETE
- [ ] MM9_IMPLEMENTATION_PLAN.md §4/§9 MM9.3 checked off; S1A/S1B split noted
- [ ] CHANGELOG.md MM9.3 entry added
- [ ] ARCHITECTURE_DECISIONS.md design notes added (dual PortfolioView + IV fallback)

### Definition of Done

MM9.3 is DONE when:
1. `_check_greek_limits` is functional: returns bool, never raises, uses portfolio total + marginal
2. TODO comment on `InstrumentParser.parse()` is present and readable
3. `PortfolioView.snapshot()` is live in `LoopDriver` with enriched telemetry payload
4. Drawdown gate uses portfolio-wide `mtm_equity` (I.M.2 closed)
5. Suite passes at ≥ 696 + all 20 new tests (6 S1A + 7 S1B + 7 S2)
6. S3 adds 2 more tests if proceeded
7. All documentation sections above are updated
8. `fno_runner.py` wires `PortfolioView` at the composition root
9. No `ExecutionRuleError` in `_check_greek_limits` (grep-verified)

---

## Appendix A: Black76 T=0 Safety Proof

The full IV/TTE fallback rationale is in §2.3. This appendix retains only the safety proof for
reference.

`Black76Engine.calculate_greeks(T=0)` at black76_engine.py:32–39:

```python
if T <= 0:
    delta = 1.0 if (CE and F > K) else (-1.0 if (PE and K > F) else 0.0)
    return Greeks(delta, 0.0, 0.0, 0.0, 0.0)  # intrinsic only, no division
```

No divide-by-zero. No exception. Gate consequence by Greek type:

| Greek | TTE=0 result | Gate consequence |
|-------|------------|-----------------|
| Delta | Intrinsic (±1 ITM, 0 OTM) | Over-estimates ITM delta → tighter gate (safe-side) |
| Gamma | 0 | Under-estimates → gamma limit may not trigger (documented risk) |
| Vega | 0 | Under-estimates → vega limit may not trigger (documented risk) |

---

## Appendix B: PortfolioSnapshot Field Reference

From `core/execution/portfolio_view.py`:

```python
@dataclass(frozen=True)
class PortfolioSnapshot:
    positions: Dict[str, Position]
    cash_balance: float        # ledger cash (realized PnL + initial capital)
    realized_pnl: float        # cumulative closed-position PnL
    unrealized_pnl: float      # sum of all open position MTM PnL
    mtm_equity: float          # cash_balance + unrealized_pnl (total net worth)
    gross_exposure: float      # sum of abs(position_value) across all positions
    used_margin: float         # sum of margin required for all open positions
```

`mtm_equity` is the canonical portfolio value for drawdown checking (S3) and future watchdog
heartbeat fix (deferred beyond MM9.3).

`unrealized_pnl` requires current prices to be accurate. When `_price_cache` lags between
bar arrivals, the unrealized value reflects the last-seen bar close. Consistent with how the
margin gate and drawdown gate use `current_price` today.
