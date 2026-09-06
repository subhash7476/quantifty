# MM9.3-S2 Implementation Specification
## PortfolioView Runtime Integration with Greek Exposure

**Status:** PENDING IMPLEMENTATION
**Preceded by:** MM9.3-S1B — Portfolio Greek Aggregation (COMPLETE, 693 tests passing)
**Followed by:** MM9.3-S3 — Drawdown Gate I.M.2 Full Fix
**Date drafted:** 2026-06-28

---

## 1. Objectives

S2 has a single architectural purpose: make the portfolio Greek state computed inside `_check_greek_limits` (S1B) **visible to runtime consumers** without duplicating the computation or creating a second source of truth.

Concretely, S2 delivers:

1. **`PortfolioSnapshot` gains Greek exposure** — the three checked Greeks (delta, gamma, vega)
   plus theta and rho are carried in an immutable `Greeks` field.
2. **`PortfolioView.snapshot()` computes Greeks** — by delegating to an optionally-injected
   `PortfolioGreeks` instance using the same IV/TTE fallback strategy as S1B (§2.3 of the
   parent MM9.3 spec: empty-dict defaults, 20% IV, 0.0 TTE).
3. **`LoopDriver` exposes the enriched snapshot** — `_build_positions()` is promoted from a raw
   position-tracker pass-through to a full `PortfolioSnapshot` projection: positions, cash,
   PnL, margin, exposure, and now Greeks — all in one telemetry cadence call.
4. **`fno_runner.py` wires the composition root** — constructs one `PortfolioView` bound to the
   handler's three trackers and its `portfolio_greeks` aggregator, then injects it into
   `LoopDriver`.

This slice introduces **no new risk logic**. The Greek values in the snapshot are observational:
they describe the portfolio's current exposure for dashboards and operators. The risk gate that
acts on those values is S1B and is already complete.

---

## 2. Architectural Rationale

### 2.1 Why Greeks belong in PortfolioSnapshot

`PortfolioSnapshot` is the canonical read-surface for portfolio state (ADR-001: Ledger Is Truth;
PORTFOLIO_STATE_DISCOVERY.md §5.2). Every existing field — positions, PnL, margin, equity — is a
projection of the ledger trackers. Portfolio Greeks are the same kind of projection: a derived
read-only view of held positions, prices, and instrument metadata. They belong here for the same
reason `used_margin` and `mtm_equity` already belong here.

### 2.2 Why PortfolioView owns the Greek computation

`PortfolioView` is already the aggregation surface for the three financial trackers. Adding an
optional fourth collaborator (`PortfolioGreeks`) follows the same injection pattern as
`MarginTracker` and `PnLTracker`. The alternative — computing Greeks in the LoopDriver's
`_build_positions()` directly — would couple the driver to `PortfolioGreeks` and bypass the
established view layer.

### 2.3 IV/TTE Fallback Strategy (unchanged from S1B)

`PortfolioView.snapshot()` passes empty dicts for `volatilities` and `time_to_expiry_map` to
`PortfolioGreeks.calculate_portfolio_greeks()`. The `PortfolioGreeks` class already applies
safe defaults internally:

```python
vol = volatilities.get(symbol, 0.20)       # 20% IV default
tte = time_to_expiry_map.get(symbol, 0.0)  # 0.0 TTE default
```

At TTE=0.0, `Black76Engine` returns intrinsic delta only (+-1 ITM, 0 OTM) with Gamma=Vega=0
(no divide-by-zero). This is conservative for the delta limit and known-degraded for vega/gamma,
exactly as documented in the parent spec §2.3. No change to this decision.

### 2.4 Single PortfolioGreeks Instance (Not Duplicated)

The handler already owns `self.portfolio_greeks: PortfolioGreeks` (handler.py:203). S2 does
**not** construct a second `PortfolioGreeks` instance. Instead, `fno_runner.py` passes the
handler's existing instance to the new `PortfolioView`:

```
ExecutionHandler.portfolio_greeks  ──► PortfolioView  ──► LoopDriver
```

Both `_check_greek_limits` (for gate admission) and `PortfolioView.snapshot()` (for telemetry)
read from the same `PortfolioGreeks` object. `PortfolioGreeks` is stateless — it delegates to
`position_tracker.get_all_positions()` on each call. Two callers reading the same stateless
aggregator does not create a second source of truth (ADR-001: the ledger is truth; this is
downstream of it).

### 2.5 One PortfolioView Instance in S2 (LoopDriver only)

The parent MM9.3 spec §2.4 described two `PortfolioView` instances (one in the handler for S3's
drawdown gate, one in the driver for telemetry). S2 creates **only the driver instance**. The
handler instance is S3 territory.

### 2.6 Telemetry Payload Backward Compatibility — Sentinel Key Design

The `publish_positions` channel is consumed by two live consumers that the spec cannot break:

1. **`flask_app/__init__.py:89`** — stores the blob as `self.latest_telemetry["positions"]`.
   Safe: stores any dict verbatim without iterating it.
2. **`flask_app/templates/dashboard.html:309`** — `updatePositions(data)` iterates
   `Object.entries(data)` and checks `if (position.quantity && Math.abs(position.quantity) > 0)`.
   A nested `{"positions": {...}, "cash_balance": ..., "portfolio_greeks": {...}}` structure would
   break this: the top-level keys would be `"positions"`, `"cash_balance"`, etc., and
   `position.quantity` would be `undefined` for every entry — the entire book would silently
   disappear from the dashboard.

**Design decision:** The positions channel payload **stays flat** (per-symbol `{symbol: {...}}`
map). Portfolio-level data (cash, PnL, Greeks) is embedded under a `_portfolio_summary` sentinel
key at the top level of the same dict. The `_` prefix signals "metadata, not a position entry."

The dashboard JS handles this safely: for the `_portfolio_summary` entry, `position.quantity` is
`undefined` (no such field), so `undefined && ...` evaluates to `false` — the entry is silently
skipped. The position table renders only real symbol entries. No template modification needed.

**Structural invariant preserved:** On both the enriched and raw paths, every non-sentinel key
in the payload is a symbol string, and its value is a dict with `quantity`, `avg_price`, `side`,
`pnl_pct` keys. The only new key is `_portfolio_summary` (enriched path only).

**Pre-S2 action required:** Run `grep -rn "_build_positions\|payload.keys" tests/runtime/`
before implementation begins. Any test asserting the exact key set must be updated to allow for
`_portfolio_summary`.

### 2.7 No New Telemetry Channel

Greeks are included in the `_portfolio_summary` sentinel entry of the existing `publish_positions`
payload. This avoids adding new methods to the `TelemetryTransport` protocol and the
`RuntimeTelemetryPublisher` bridge — both are unchanged. All existing subscribers iterate or
check specific keys and naturally skip `_portfolio_summary`; no subscriber is broken.

### 2.8 Thread Safety

The platform is single-threaded (ADR-003). `_drive_telemetry()` and `_check_greek_limits` both
execute on the same thread. `_price_cache` is read by the driver via the existing §10.7
private-attribute coupling (pre-approved in the parent MM9.3 spec). No locking is required.

### 2.9 Update Lifecycle

Greek exposure is computed on every `_drive_telemetry()` call, throttled to
`telemetry_interval_s` of deterministic clock time. Between cadences, the last-published value
stands — there is no push from the handler. This is the same pull-at-cadence model as all other
telemetry fields (health, positions, metrics). Consumers observing stale Greeks between cadences
is expected and acceptable for an observability-only field.

---

## 3. Repository Impact Review

### 3.1 Files Modified

| File | Change |
|------|--------|
| `core/execution/portfolio_view.py` | Add `portfolio_greeks: Greeks` to `PortfolioSnapshot`; accept `Optional[PortfolioGreeks]` in `PortfolioView.__init__`; compute Greeks in `snapshot()` |
| `core/runtime/driver.py` | Accept `Optional[PortfolioView]`; enrich `_build_positions()` with full snapshot payload including Greeks; extract `_build_positions_raw()` helper; startup WARNING when view is None |
| `scripts/fno_runner.py` | Construct `PortfolioView` from handler's trackers + `portfolio_greeks`; inject into `LoopDriver` |

### 3.2 Files NOT Modified

| File | Reason |
|------|--------|
| `core/execution/handler.py` | S1A + S1B complete; no changes in S2 |
| `core/risk/greeks/portfolio_greeks.py` | Complete; stateless; re-used via injection |
| `core/risk/greeks/greeks_model.py` | Complete; `Greeks` dataclass already has all five fields |
| `core/risk/greeks/greeks_calculator.py` | Complete; no change |
| `core/runtime/telemetry_publisher.py` | No new methods; existing `publish_positions` handles enriched payload |
| `core/messaging/telemetry.py` | No new methods; existing `publish_positions` handles enriched payload |
| `core/runtime/event_journal.py` | No new EventType for Greek snapshots (observational only; not audit-critical) |
| `core/runtime/metrics.py` | No new RuntimeMetric for Greek exposure (counters are for lifecycle/runtime events) |

### 3.3 New Files

None. All required classes exist. All required test files are new (§8).

### 3.4 Test Files

| File | Status | Purpose |
|------|--------|---------|
| `tests/execution/test_portfolio_view_greeks.py` | New | PortfolioSnapshot/PortfolioView Greek fields (8 tests) |
| `tests/runtime/test_driver_portfolio_view.py` | New | LoopDriver `_build_positions()` enrichment (8 tests) |
| `tests/integration/test_portfolio_view_driver.py` | New | End-to-end: handler fill → driver telemetry has Greek payload (1 test) |
| `tests/execution/test_portfolio_view.py` | Existing — must stay green | All 9 existing tests pass with `portfolio_greeks=None` default |

---

## 4. Dependency Validation

| Dependency | Status | Evidence |
|------------|--------|---------|
| S1A — `_check_greek_limits` bool semantics | COMPLETE | handler.py:967–1041; test_greek_limits.py |
| S1B — Portfolio Greek aggregation in `_check_greek_limits` | COMPLETE | handler.py:967–1041; test_greek_limits.py |
| `PortfolioGreeks.calculate_portfolio_greeks()` | COMPLETE | portfolio_greeks.py |
| `self.portfolio_greeks: PortfolioGreeks` on handler | COMPLETE | handler.py:203 |
| `Greeks` dataclass (frozen, `__add__`) | COMPLETE | greeks_model.py |
| `PortfolioView.snapshot()` existing contract | COMPLETE | portfolio_view.py; test_portfolio_view.py (9 tests) |
| `self._price_cache: Dict[str, PriceSnapshot]` on handler | COMPLETE | handler.py; MM9.2-S3 |
| `self.metrics.cash_balance` on handler | COMPLETE | handler.py; MM9.2-S4 |
| `LoopDriver._drive_telemetry()` / `_build_positions()` pattern | COMPLETE | driver.py:694–772 |
| `RuntimeTelemetryPublisher.publish_positions()` | COMPLETE | telemetry_publisher.py:107–119 |
| `Black76Engine` T=0 safety | CONFIRMED | black76_engine.py:32–39 — intrinsic delta, no divide-by-zero |

---

## 5. Implementation Plan

### 5.1 `core/execution/portfolio_view.py`

#### Change 1 — Import `Greeks` and `PortfolioGreeks`

```python
from typing import Dict, Optional
from core.risk.greeks.greeks_model import Greeks
from core.risk.greeks.portfolio_greeks import PortfolioGreeks
```

The existing ADR-002 forbidden-import guard (`test_portfolio_view.py` test #8) checks against
`strategies`, `backtest`, `runner`, `ftmo`, `models`, `scanners`, `research`, `analytics`.
`risk` is NOT in that set. The import is permitted.

#### Change 2 — `PortfolioSnapshot` gains `portfolio_greeks`

```python
@dataclass(frozen=True)
class PortfolioSnapshot:
    positions: Dict[str, Position]
    cash_balance: float
    realized_pnl: float
    unrealized_pnl: float
    mtm_equity: float
    gross_exposure: float
    used_margin: float
    portfolio_greeks: Greeks       # new field — zero-Greeks when no PortfolioGreeks injected
```

**Field ordering:** appended last to minimise disruption. All existing callers of
`PortfolioSnapshot(...)` use keyword arguments — confirmed by `grep -n "PortfolioSnapshot("`.

**No default on the dataclass field.** `PortfolioView.snapshot()` always supplies a value:
either the computed result or `Greeks(0.0, 0.0, 0.0, 0.0, 0.0)` when `PortfolioGreeks` is not
injected. The sentinel lives in `PortfolioView`, not in the DTO.

#### Change 3 — `PortfolioView.__init__` accepts optional `PortfolioGreeks`

```python
def __init__(
    self,
    position_tracker: PositionTracker,
    pnl_tracker: PnLTracker,
    margin_tracker: MarginTracker,
    portfolio_greeks: Optional[PortfolioGreeks] = None,
):
    self.position_tracker = position_tracker
    self.pnl_tracker = pnl_tracker
    self.margin_tracker = margin_tracker
    self._portfolio_greeks = portfolio_greeks
```

All existing three-argument constructions `PortfolioView(pt, pnl, margin)` continue to work
without modification. `portfolio_greeks` defaults to `None`.

#### Change 4 — `PortfolioView.snapshot()` computes Greeks

```python
def snapshot(self, current_prices: Dict[str, float], cash_balance: float) -> PortfolioSnapshot:
    realized_pnl = self.pnl_tracker.get_realized_pnl()
    unrealized_pnl = self.pnl_tracker.get_unrealized_pnl(current_prices)

    if self._portfolio_greeks is not None:
        greeks = self._portfolio_greeks.calculate_portfolio_greeks(
            market_prices=current_prices,
            volatilities={},
            time_to_expiry_map={},
            risk_free_rate=0.05,
        )
    else:
        greeks = Greeks(0.0, 0.0, 0.0, 0.0, 0.0)

    return PortfolioSnapshot(
        positions=self.position_tracker.get_all_positions(),
        cash_balance=cash_balance,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        mtm_equity=cash_balance + unrealized_pnl,
        gross_exposure=self.margin_tracker.get_exposure(current_prices),
        used_margin=self.margin_tracker.get_used_margin(current_prices),
        portfolio_greeks=greeks,
    )
```

The signature is **unchanged** — `(current_prices, cash_balance)` only. IV/TTE inputs are
always empty-dict (per §2.3 fallback strategy). The public interface is not widened.

**Failure isolation:** If `calculate_portfolio_greeks()` raises, the exception propagates to
the caller. `PortfolioView.snapshot()` is not a gate; a failure here is a bug, not a silently
swallowed edge case. The driver's `_build_positions()` wraps the entire telemetry build in a
best-effort try/except (§5.2 Change 4).

---

### 5.2 `core/runtime/driver.py`

#### Change 1 — Import `PortfolioView`

```python
from core.execution.portfolio_view import PortfolioView
```

Add to the existing imports block.

#### Change 2 — `__init__` accepts `Optional[PortfolioView]`

Add `portfolio_view: Optional[PortfolioView] = None` as the last parameter:

```python
def __init__(self, config: DriverConfig,
             ...,          # all existing params unchanged
             master_readiness: Optional[Callable[[], ReadinessVerdict]] = None,
             portfolio_view: Optional[PortfolioView] = None):   # new, last
    ...
    self._portfolio_view = portfolio_view
```

All existing `LoopDriver(...)` instantiations omit `portfolio_view` and receive `None`.
The driver degrades to the pre-S2 raw-tracker fallback (§5.2 Change 4).

#### Change 3 — Startup WARNING when `portfolio_view` is None

Immediately after assigning `self._portfolio_view` in `__init__`:

```python
if self._portfolio_view is None:
    self._logger.warning(
        "PortfolioView not injected — telemetry will use degraded position payload "
        "(no Greek exposure, no MTM equity, no PnL breakdown)"
    )
```

This makes silent telemetry degradation visible in the log without affecting any runtime behavior.

#### Change 4 — `_build_positions()` enriched path

Replace the current `_build_positions()` body with the enriched path, extracting the existing
body into a private helper:

```python
def _build_positions(self) -> Dict[str, Any]:
    if self._portfolio_view is not None and self._execution is not None:
        prices = {sym: snap.price
                  for sym, snap in self._execution._price_cache.items()}
        cash = self._execution.metrics.cash_balance
        try:
            snapshot = self._portfolio_view.snapshot(prices, cash)
        except Exception as exc:
            self._logger.error(
                "_build_positions: PortfolioView.snapshot() failed: %s; "
                "falling back to raw positions", exc)
            return self._build_positions_raw()

        payload: Dict[str, Any] = {}
        for sym, pos in snapshot.positions.items():
            current_price = prices.get(sym, 0.0)
            avg = pos.avg_price
            pnl_pct = (
                (current_price - avg) / avg * 100.0
                if avg != 0.0 else 0.0
            )
            payload[sym] = {
                "quantity": pos.quantity,
                "avg_price": avg,
                "side": pos.side.value,
                "current_price": current_price,
                "pnl_pct": round(pnl_pct, 4),
            }

        g = snapshot.portfolio_greeks
        payload["_portfolio_summary"] = {
            "cash_balance": snapshot.cash_balance,
            "realized_pnl": snapshot.realized_pnl,
            "unrealized_pnl": snapshot.unrealized_pnl,
            "mtm_equity": snapshot.mtm_equity,
            "gross_exposure": snapshot.gross_exposure,
            "used_margin": snapshot.used_margin,
            "portfolio_greeks": {
                "delta": round(g.delta, 4),
                "gamma": round(g.gamma, 4),
                "vega": round(g.vega, 4),
                "theta": round(g.theta, 4),
                "rho": round(g.rho, 4),
            },
        }
        return payload

    return self._build_positions_raw()


def _build_positions_raw(self) -> Dict[str, Any]:
    """Pre-S2 fallback: raw position-tracker pass-through, no financial projection."""
    if self._execution is None:
        return {}
    return {
        symbol: {
            "quantity": pos.quantity,
            "avg_price": pos.avg_price,
            "side": pos.side.value,
            "pnl_pct": 0.0,
        }
        for symbol, pos in self._execution.position_tracker.get_all_positions().items()
    }
```

**`_build_positions_raw()` is the exact pre-S2 body of `_build_positions()`** — same flat
structure, same keys, same `pnl_pct: 0.0` placeholder. No `_portfolio_summary` key. No new
behavior on the fallback path.

**Coupling note:** `self._execution._price_cache` is the same §10.7 infra-to-infra coupling
already accepted in the parent MM9.3 spec §S2.2 and in MM9.2-S3-S2. No new coupling.

**`pnl_pct` placeholder resolved:** The enriched path computes real per-position `pnl_pct`
from `(current_price - avg_price) / avg_price * 100`. This resolves the driver.py:769 known
gap for the production path.

**Sentinel key safety (backward compat):** The `_portfolio_summary` key is never a valid NSE
symbol — all real NSE symbols begin with `NSE_EQ|`, `NSE_INDEX|`, etc. The dashboard JS at
`flask_app/templates/dashboard.html:309` iterates `Object.entries(data)` and checks
`if (position.quantity && Math.abs(position.quantity) > 0)`. For `_portfolio_summary`, the
value dict has no `quantity` field — `position.quantity` is `undefined` (falsy) — so the entry
is silently skipped. The position table renders only real symbol entries. **No template change
needed.**

---

### 5.3 `scripts/fno_runner.py`

After the `ExecutionHandler` is constructed and before `LoopDriver` is constructed, add:

```python
from core.execution.portfolio_view import PortfolioView

portfolio_view = PortfolioView(
    position_tracker=execution_handler.position_tracker,
    pnl_tracker=execution_handler.pnl_tracker,
    margin_tracker=execution_handler.margin_tracker,
    portfolio_greeks=execution_handler.portfolio_greeks,   # existing instance, not new
)

driver = LoopDriver(
    ...,
    portfolio_view=portfolio_view,
)
```

`execution_handler.portfolio_greeks` is the existing `PortfolioGreeks` instance from
handler.py:203 — not a new instance (§2.4). `PortfolioView` holds only references; it is
lightweight and stateless.

---

## 6. Behavioral Contracts

### 6.1 `PortfolioView.snapshot()` post-S2

| Precondition | `portfolio_greeks` in result | Notes |
|---|---|---|
| `portfolio_greeks=None` (not injected) | `Greeks(0, 0, 0, 0, 0)` | Backward-compat default |
| Injected, empty book | `Greeks(0, 0, 0, 0, 0)` | No positions → zero aggregation |
| Injected, equity positions | `delta ≈ Σ quantities`, vega=0, gamma=0 | Per `GreeksCalculator` equity dispatch |
| Injected, option positions | Delta=intrinsic(TTE=0), vega=0, gamma=0 | Known limitation; full fix is MM9.5 |
| `current_prices` missing a held symbol | Price=0 for that position → Greeks=0 for it | `PortfolioGreeks` ignores zero-price positions |
| Same inputs, called twice | Returns equal `PortfolioSnapshot` | Determinism preserved |
| Any call | Does not mutate any tracker | Read-only invariant preserved |

### 6.2 `LoopDriver._build_positions()` post-S2

| Precondition | Payload | Notes |
|---|---|---|
| `portfolio_view` injected, execution present | Flat per-symbol map + `_portfolio_summary` sentinel key | Production path; per-symbol `pnl_pct` is real |
| `portfolio_view` is None | Raw: flat symbol dict only, `pnl_pct=0.0` placeholder, no `_portfolio_summary` | Pre-S2 degraded path; WARNING logged at startup |
| `execution` is None | `{}` (empty) | No-handler path (replay/inert/test) |
| `PortfolioView.snapshot()` raises | Log error, fall back to raw | Best-effort; telemetry never breaks the loop |

### 6.3 Enriched Payload Structure

```json
{
  "NSE_EQ|INE001A01036": {
    "quantity": 100,
    "avg_price": 2500.0,
    "side": "LONG",
    "current_price": 2560.0,
    "pnl_pct": 2.4
  },
  "_portfolio_summary": {
    "cash_balance": 95000.0,
    "realized_pnl": 3200.0,
    "unrealized_pnl": 6000.0,
    "mtm_equity": 101000.0,
    "gross_exposure": 256000.0,
    "used_margin": 51200.0,
    "portfolio_greeks": {
      "delta": 100.0,
      "gamma": 0.0,
      "vega": 0.0,
      "theta": 0.0,
      "rho": 0.0
    }
  }
}
```

All float values rounded to 4 decimal places in the payload. Per-symbol entries and
`_portfolio_summary` are the only top-level keys. The dashboard JS checks `position.quantity`
before rendering — the `_portfolio_summary` entry has no `quantity` field and is skipped.

### 6.4 Raw Payload Structure (degraded path — unchanged from pre-S2)

```json
{
  "NSE_EQ|INE001A01036": {
    "quantity": 100,
    "avg_price": 2500.0,
    "side": "LONG",
    "pnl_pct": 0.0
  }
}
```

No `_portfolio_summary` key. All consumers that were working pre-S2 continue to work unchanged.

---

## 7. Failure Modes and Mitigations

| # | Failure | Severity | Mitigation |
|---|---------|----------|-----------|
| F1 | `PortfolioView.snapshot()` raises inside `_build_positions()` | Medium | Log error; fall back to `_build_positions_raw()` — telemetry degrades, loop continues |
| F2 | `portfolio_view` not injected in `fno_runner.py` | Medium | Startup WARNING log (§5.2 Change 3) makes this visible at launch |
| F3 | `_price_cache` is cold at startup (no bars yet received) | Low | No positions at startup → `PortfolioGreeks` returns `Greeks(0,0,0,0,0)`. Correct. |
| F4 | Stale prices in `_price_cache` (symbol not recently seen) | Low | Last-seen price used. Staleness bounded by bar cadence (1 min). |
| F5 | `calculate_portfolio_greeks()` raises on a tracker fault | High | Propagates to `_build_positions()`, which catches and falls back. Not silently swallowed. |
| F6 | `pos.avg_price == 0` in pnl_pct calculation | Low | Guard: `if avg != 0.0 else 0.0` (§5.2 Change 4) |
| F7 | Exact key-set assertion in existing `tests/runtime/` breaks | Medium | Pre-S2 audit is mandatory (§2.6 / §8.3). Must be done before any code is written. |
| F8 | `PortfolioSnapshot` positional constructor call breaks on new field | Low | Confirm all callers use keyword args: `grep -n "PortfolioSnapshot("` — expected zero positional callers |
| F9 | `_portfolio_summary` sentinel key surprises consumers that do exact key-set assertions | Low | Pre-S2 audit (§8.3) converts exact key-set checks to superset checks. The dashboard JS (`updatePositions`) skips `_portfolio_summary` because `position.quantity` is `undefined` for that entry — verified in spec review. |
| F10 | ADR-002 violation from `portfolio_view.py` importing `core.risk.*` | Low | The forbidden-import guard does NOT list `risk`. Verify guard set before merge. |

---

## 8. Testing Strategy

### 8.1 TDD Order

Write all tests first. Every test must be RED before any production code is written.

#### Block A — `PortfolioSnapshot` and `PortfolioView` Greek fields

**File:** `tests/execution/test_portfolio_view_greeks.py` (8 tests)

```
A1. test_portfolio_snapshot_has_portfolio_greeks_field
    Assert PortfolioSnapshot has attribute "portfolio_greeks"
    and it is an instance of Greeks.

A2. test_portfolio_view_without_pg_returns_zero_greeks
    Construct PortfolioView(pt, pnl, margin) — no portfolio_greeks.
    snap = view.snapshot({}, 100000.0)
    Assert snap.portfolio_greeks == Greeks(0.0, 0.0, 0.0, 0.0, 0.0)

A3. test_portfolio_view_with_pg_returns_computed_greeks
    Construct mock PortfolioGreeks returning Greeks(50.0, 1.0, 2.0, 0.0, 0.0).
    PortfolioView(pt, pnl, margin, portfolio_greeks=mock_pg)
    snap = view.snapshot({"SYM": 100.0}, 50000.0)
    Assert snap.portfolio_greeks.delta == 50.0

A4. test_portfolio_view_pg_called_with_price_cache
    Spy on pg.calculate_portfolio_greeks; assert called with
    market_prices matching the prices dict passed to snapshot().

A5. test_portfolio_view_pg_called_with_empty_vol_and_tte
    Assert volatilities={} and time_to_expiry_map={} in the call
    (IV/TTE fallback strategy invariant — must never pass real values).

A6. test_portfolio_view_zero_greeks_on_empty_book_with_pg_injected
    Inject real PortfolioGreeks(pt) with empty position_tracker.
    snap.portfolio_greeks == Greeks(0.0, 0.0, 0.0, 0.0, 0.0)

A7. test_portfolio_view_snapshot_deterministic_with_greeks
    Two calls with same inputs produce equal PortfolioSnapshot (including Greeks field).

A8. test_portfolio_view_does_not_mutate_trackers_with_pg
    Open one position. Snapshot with portfolio_greeks injected.
    Assert position_tracker.get_all_positions() unchanged after call.
```

#### Block B — `LoopDriver._build_positions()` enrichment

**File:** `tests/runtime/test_driver_portfolio_view.py` (8 tests)

```
B1. test_driver_accepts_optional_portfolio_view
    LoopDriver(config=...) with no portfolio_view kwarg — no exception.

B2. test_driver_startup_warning_when_no_portfolio_view
    Construct LoopDriver without portfolio_view.
    Assert WARNING logged containing "PortfolioView not injected".

B3. test_build_positions_raw_when_no_view
    driver._portfolio_view = None, driver._execution has positions.
    payload = driver._build_positions()
    Assert payload[some_symbol]["quantity"] is accessible (flat shape).
    Assert "_portfolio_summary" NOT in payload.

B4. test_build_positions_returns_empty_when_no_execution
    driver._portfolio_view = None, driver._execution = None.
    Assert driver._build_positions() == {}

B5. test_build_positions_enriched_payload_has_portfolio_summary
    Inject mock PortfolioView returning a known PortfolioSnapshot.
    payload = driver._build_positions()
    Assert "_portfolio_summary" in payload.
    Assert all of: "cash_balance", "realized_pnl", "unrealized_pnl",
    "mtm_equity", "gross_exposure", "used_margin", "portfolio_greeks"
    in payload["_portfolio_summary"].

B6. test_build_positions_portfolio_greeks_structure
    payload["_portfolio_summary"]["portfolio_greeks"] is a dict with
    keys exactly: {"delta", "gamma", "vega", "theta", "rho"} — all float.

B7. test_build_positions_pnl_pct_computed_not_placeholder
    Inject PortfolioView snapshot with one position (sym), avg=100.0,
    _price_cache = {sym: PriceSnapshot(110.0, ...)}.
    payload[sym]["pnl_pct"] == 10.0 (not 0.0).
    (Symbol is a direct top-level key — not nested under "positions".)

B8. test_build_positions_snapshot_exception_falls_back_to_raw
    Inject PortfolioView whose snapshot() raises RuntimeError.
    driver._build_positions() returns flat raw format without re-raising.
    Assert "_portfolio_summary" NOT in payload (raw fallback has no summary).
    Assert error was logged.
```

#### Block C — Integration

**File:** `tests/integration/test_portfolio_view_driver.py` (1 test)

```
C1. test_driver_publishes_greek_exposure_on_telemetry_cadence
    - Construct real ExecutionHandler (PaperBroker, tmp_path)
    - Submit one BUY signal → fill → position in book
    - Construct PortfolioView with handler.portfolio_greeks
    - Construct LoopDriver with portfolio_view and a spy transport
    - Advance one bar through _tick(); call _drive_telemetry()
    - Assert spy transport received publish_positions payload
      containing "_portfolio_summary" key
    - Assert payload["_portfolio_summary"]["portfolio_greeks"]["delta"] > 0
```

### 8.2 Existing Tests — Must Remain Green Without Modification

**`tests/execution/test_portfolio_view.py`** (9 tests):

All 9 tests call `PortfolioView(pt, pnl, margin)` without `portfolio_greeks`. After S2, these
still default to `portfolio_greeks=None`. The `snapshot()` call supplies `Greeks(0,0,0,0,0)` for
the new field; all existing field assertions hold. The frozen-dataclass test implicitly also
freezes `portfolio_greeks`. No modifications needed.

**`tests/risk/test_portfolio_greeks.py`** and **`tests/execution/test_greek_limits.py`**:
Unchanged — these test the aggregator and gate respectively, neither of which changes in S2.

### 8.3 Pre-S2 Mandatory Audit

Before writing any production code, run:

```bash
grep -rn "_build_positions\|positions_payload\|payload\.keys\|\"pnl_pct\"" tests/runtime/
```

For each match:
- If it asserts the flat-format structure (symbol as top-level key): verify it tests the
  raw/degraded path (no `portfolio_view` injected). Update to assert the raw path explicitly.
- If it asserts `payload["pnl_pct"] == 0.0`: the enriched path now returns a real value.
  Either test the raw path (where `0.0` is still correct) or update to test the enriched path.
- Convert any `payload.keys() == {...}` to `set(payload.keys()) >= {...}` (superset check).

---

## 9. Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `PortfolioSnapshot` is a frozen dataclass with a `portfolio_greeks: Greeks` field |
| AC2 | `PortfolioView(pt, pnl, margin)` (no `portfolio_greeks`) returns `Greeks(0,0,0,0,0)` in snapshot — all 9 existing tests pass without modification |
| AC3 | `PortfolioView(pt, pnl, margin, portfolio_greeks=pg)` calls `pg.calculate_portfolio_greeks(market_prices=prices, volatilities={}, time_to_expiry_map={}, risk_free_rate=0.05)` |
| AC4 | `LoopDriver` constructor accepts `portfolio_view=None` (default); logs WARNING at STARTUP when None |
| AC5 | `_build_positions()` with `portfolio_view` injected returns a dict with `"_portfolio_summary"` key containing `"portfolio_greeks"` with all five Greek keys as floats; per-symbol entries remain flat top-level keys |
| AC6 | `_build_positions()` with `portfolio_view=None` returns the pre-S2 flat format (no `"_portfolio_summary"` key); all consumers that worked pre-S2 continue to work unchanged |
| AC7 | `_build_positions()` with `portfolio_view` raising falls back to raw format; does not propagate; error is logged |
| AC8 | `fno_runner.py` constructs `PortfolioView` with `portfolio_greeks=execution_handler.portfolio_greeks` and passes it to `LoopDriver` |
| AC9 | All 693 existing tests pass (no regression) |
| AC10 | All 17 new tests (8 Block A + 8 Block B + 1 Block C) are green |
| AC11 | `PortfolioView.snapshot()` signature is unchanged — `(current_prices, cash_balance)` only |

---

## 10. Definition of Done

- [ ] `PortfolioSnapshot.portfolio_greeks: Greeks` field added (last field, no default on dataclass)
- [ ] `PortfolioView.__init__` accepts `Optional[PortfolioGreeks] = None`; stored as `self._portfolio_greeks`
- [ ] `PortfolioView.snapshot()` computes Greeks via `_portfolio_greeks` or returns `Greeks(0,0,0,0,0)` when None
- [ ] `LoopDriver.__init__` accepts `Optional[PortfolioView] = None`; stored as `self._portfolio_view`
- [ ] Startup WARNING logged when `portfolio_view` is None
- [ ] `_build_positions()` enriched path implemented: flat per-symbol entries (with real `pnl_pct`) + `"_portfolio_summary"` sentinel key containing financial fields + `"portfolio_greeks"` dict
- [ ] `_build_positions_raw()` private helper extracted (pre-S2 flat body, unchanged behavior)
- [ ] `fno_runner.py` composition root constructs and injects `PortfolioView` with handler's existing `portfolio_greeks` instance
- [ ] Pre-S2 `tests/runtime/` audit completed; key-set/structure assertions updated
- [ ] `tests/execution/test_portfolio_view_greeks.py` — 8 tests green
- [ ] `tests/runtime/test_driver_portfolio_view.py` — 8 tests green
- [ ] `tests/integration/test_portfolio_view_driver.py` — 1 test green
- [ ] All 693 prior tests still passing
- [ ] `docs/reports/MM9_3_IMPLEMENTATION_SPEC.md` §3.2 note updated: `portfolio_view.py` changed from "no change needed" to "S2: adds `portfolio_greeks` field to PortfolioSnapshot + PortfolioGreeks injection"

---

## 11. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|-----------|
| R1 | Payload structure change (nested `"positions"` key) breaks existing runtime tests | High | Low | Pre-S2 audit is mandatory (§8.3). Catch before any code is written. |
| R2 | `fno_runner.py` omits `portfolio_greeks` from `PortfolioView` constructor | Low | Medium | Startup WARNING log (§5.2 Change 3) makes it visible. AC8 is an acceptance criterion. |
| R3 | ADR-002 violation — `portfolio_view.py` imports `core.risk.*` | Low | Medium | Forbidden-import guard does NOT list `risk` as forbidden. Verify guard set before merge. |
| R4 | TTE=0.0 defaults make Greek snapshot misleading for options books | None (documented) | Low | Documented known limitation (§2.3). Delta is sound. Full fix is MM9.5. |
| R5 | `PortfolioSnapshot` field addition breaks positional constructor call | Low | Low | Confirm `grep -n "PortfolioSnapshot("` — expected zero positional callers. |
| R6 | `PortfolioGreeks.calculate_portfolio_greeks()` is slow at telemetry cadence for large books | Low | Low | Called at cadence only, not per-signal. Cadence is `telemetry_interval_s`. No performance concern at current scale. |

---

## 12. Explicit Non-Goals

The following are explicitly out of scope for S2 and must not be included:

- **New risk limits** — S1B already enforces limits; S2 is observability only
- **Per-position Greek breakdown** — the payload carries only portfolio-level Greeks
- **IV/TTE per-position sourcing** — deferred to MM9.5 (options data integration)
- **New `publish_greeks()` transport method** — Greeks are in the existing `publish_positions` payload
- **`_persist_metrics()` extension** — Flask reads from ZMQ telemetry; the handler metrics JSON does not need Greek fields in S2
- **Drawdown gate fix (I.M.2)** — that is S3, not S2
- **Handler `_handler_portfolio_view`** — that is S3, not S2
- **Additional Greeks (Charm, Vanna, etc.)** — not in `Greeks` dataclass; out of scope
- **UI / Flask template changes** — no template modifications
- **Watchdog heartbeat equity fix** — deferred (DRIVER_SPEC §9.4 known gap)
- **MM10 work** — `InstrumentParser.parse()` at [9C] is not touched here
- **Any architectural drift from ADR-001 / ADR-003 / ADR-006**

---

## Appendix A: `PortfolioSnapshot` Field Reference (Post-S2)

```python
@dataclass(frozen=True)
class PortfolioSnapshot:
    positions: Dict[str, Position]   # read from position_tracker
    cash_balance: float              # passed in by caller
    realized_pnl: float              # pnl_tracker.get_realized_pnl()
    unrealized_pnl: float            # pnl_tracker.get_unrealized_pnl(prices)
    mtm_equity: float                # cash_balance + unrealized_pnl
    gross_exposure: float            # margin_tracker.get_exposure(prices)
    used_margin: float               # margin_tracker.get_used_margin(prices)
    portfolio_greeks: Greeks         # portfolio_greeks.calculate_portfolio_greeks() or zero
```

## Appendix B: `PortfolioView.__init__` Signature (Post-S2)

```python
def __init__(
    self,
    position_tracker: PositionTracker,
    pnl_tracker: PnLTracker,
    margin_tracker: MarginTracker,
    portfolio_greeks: Optional[PortfolioGreeks] = None,
) -> None:
```

## Appendix C: Slice Dependencies

```
MM9.3-S1A (COMPLETE) ──► MM9.3-S1B (COMPLETE) ──► MM9.3-S2 (THIS SLICE)
                                                           │
                                                           ▼
                                                    MM9.3-S3 (Drawdown Gate Fix)
```

S3 cannot start until S2 is green — S3 adds `PortfolioView` to the handler constructor, and
the S2 interface (`portfolio_greeks` parameter) must be stable before S3 extends it.

## Appendix D: Gate Ordering (Post-S2, Unchanged)

S2 adds no new gate. The `process_signal` gate ordering is unchanged from S1B:

```
[PHASE 0]   Authority + idempotency
[TLP]       Risk metadata validation
[0]         STOP file / kill switch file check
[1]         signals_received += 1
[2]         Kill switch state check
[3]         Daily trade limit → kill switch
[4]         Drawdown check → kill switch          (S3 upgrades equity here)
[4b]        Position stacking guard
[5]         _check_risk_limits → ExecutionRuleError
[9C]        _check_greek_limits → return None     (S1B portfolio aggregation; unchanged)
[TLP]       Structural context capture
[PHASE 1]   Instrument resolution + order build
[PHASE 2]   RiskManager.evaluate
[PRICEABLE] _check_book_priceable()
[MARGIN]    _check_margin_budget()
[PHASE 5]   order_tracker.add_order
[PHASE 7]   broker.place_order
```
