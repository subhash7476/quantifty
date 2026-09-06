# MM7J.2 — Instrument-Token Preservation (Route R1, broker-layer step)

**Type:** Implementation — preserve `instrument_token` through `UpstoxAdapter.get_positions()` so downstream reconciliation can key on it. Smallest viable change; broker layer only.
**Date:** 2026-06-12
**Basis:** `MM7I_NAMESPACE_ROUTE_DECISION.md` (R1 frozen) · `MM7J0_R1_PRECONDITIONS.md` (P2 = HARD prerequisite) · `MM7J1_UPSTOX_PAYLOAD_VERIFICATION.md` (payload carries `instrument_token = NSE_FO|<token>`, byte-identical to the ledger key).
**State:** before — 516 passing · 0 failing. after — **520 passing · 0 failing** (4 new). Route FROZEN = R1.

> **Scope guard.** This slice touches only the broker layer + its tests. It changes no `ExecutionHandler`, runtime loop, `SignalSource`, instrument master, `PortfolioView`, order-execution path, `reconciliation.py`, the shape adapter, or `BrokerMapping` wiring. No composition-root change, no re-key, no commit.

---

## 1. Findings — was `instrument_token` preserved, renamed, or dropped?

**DROPPED.** `UpstoxAdapter.get_positions()` (`upstox_adapter.py:126-152`) read only `trading_symbol`, `quantity`, `average_price` from each net-positions line and built a plain execution `Position` keyed on `trading_symbol`. Any `instrument_token` in the payload was discarded unconditionally (`:131-134`).

**Normalization path traced:**
```
GET /portfolio/net-positions
  → response['data'][i]  (carries instrument_token = NSE_FO|<token>, MM7J.1)
  → symbol = pos_data['trading_symbol']         # dict KEY
  → Position(symbol=…, side, quantity=abs, avg_price, last_updated)   ← token dropped here
  → positions[symbol] = Position(...)           # Dict[str, Position]
  → (downstream) to_reconcile_positions(...)    # {symbol: KEY, quantity, side}
```
The dict key flows verbatim into reconcile's `symbol`. `Position` (`core/execution/position_models.py`) is intentionally broker-identity-free; the G1 guard (`tests/g1/test_g1_closure_guard.py:333-340`) forbids the literal `instrument_key` anywhere in `core/execution/`. So the token could not simply be added to the execution model.

## 2. Design — smallest G1-clean change

A **broker-layer DTO** `BrokerPosition(Position)` in `core/brokers/broker_position.py`:
- **IS-A `Position`** (frozen subclass) → drop-in for `BrokerAdapter.get_positions() -> Dict[str, Position]` (`base.py:27`) and for the reconcile shape adapter (`to_reconcile_positions` reads `.side`/`.quantity` — unchanged). `isinstance(bp, Position)` is `True`, so every existing consumer and assertion holds.
- **Adds `instrument_token: Optional[str]`** (default `None`), set via `object.__setattr__` to respect the frozen base.
- **Lives in `core/brokers/`** — where broker identity is legal; the `instrument_token` literal never enters `core/execution/`, so the G1 grep stays empty.

`get_positions()` now constructs `BrokerPosition(..., instrument_token=pos_data.get('instrument_token'))` and **keeps keying on `trading_symbol`** (no re-key this slice — re-keying is the later #6b.3 composition-root wiring). When the field is absent (today's equity payload), it defaults to `None` — the legacy path is byte-for-byte unchanged.

**Why not re-key on `instrument_token` here?** That changes the dict key (observable behavior) and is the wiring slice's job. MM7J.2 only has to make the token *available on the position*; the future shape/root step reads `pos.instrument_token`.

## 3. File list

| File | Change | Lines |
|---|---|---|
| `core/brokers/broker_position.py` | **NEW** — `BrokerPosition(Position)` DTO carrying `instrument_token` | +45 |
| `core/brokers/upstox_adapter.py` | import `BrokerPosition`; build it in `get_positions()` preserving `instrument_token` | +3 / −1 net |
| `tests/brokers/test_upstox_positions.py` | +4 characterization tests | +94 |

No other file modified. (`docs/PROJECT_STATE.md` / `docs/CHANGELOG_PLATFORM.md` carried pre-existing edits from before this slice.)

## 4. Diff summary

- **`broker_position.py` (new):** frozen `@dataclass` subclass of `Position`, custom `__init__` delegating to `super().__init__(...)` then `object.__setattr__(self, "instrument_token", …)`.
- **`upstox_adapter.py`:** `from core.brokers.broker_position import BrokerPosition`; `positions[symbol] = Position(...)` → `positions[symbol] = BrokerPosition(..., instrument_token=pos_data.get('instrument_token'))`. Key, side/qty/avg logic, return type, and error paths untouched.

## 5. Test evidence

4 new characterization tests in `tests/brokers/test_upstox_positions.py`:
- `test_get_positions_preserves_instrument_token` — derivative line with `instrument_token=NSE_FO|79381` → `pos.instrument_token == "NSE_FO|79381"`, dict still keyed on the (compact) `trading_symbol`.
- `test_get_positions_with_token_leaves_existing_fields_unchanged` — `isinstance Position`; `symbol/side/quantity/avg_price` correct (incl. short→abs).
- `test_get_positions_token_absent_is_none_no_behavior_change` — equity line w/o token → valid `Position`, `instrument_token is None`, legacy behavior identical.
- `test_get_positions_with_token_still_shapes_for_reconcile` — token-bearing position passes through `to_reconcile_positions` to the exact `{symbol, quantity, side}` shape.

```
tests/brokers/test_upstox_positions.py  ... 8 passed   (4 pre-existing + 4 new)
G1 guards + to_reconcile + broker_positions_adapter + reconciliation_broker
  + reconcile_symbol_namespace ............. 47 passed
full suite ............................... 520 passed, 0 failed
```

Red-before-green confirmed: the two token-asserting tests failed with `AttributeError: 'Position' object has no attribute 'instrument_token'` prior to the implementation.

## 6. Success criteria — met

- A broker position from `UpstoxAdapter` now **contains `instrument_token = NSE_FO|<token>`** (rides on `BrokerPosition`). ✅
- **All existing tests pass** — 520/520, including the G1 guards (the `instrument_key` literal remains absent from `core/execution/`) and every reconcile/shape net. ✅
- **No runtime behavior change** — same dict key, same return contract, same fields; the token is additive and defaults to `None` on the legacy path. ✅

**Next slice (#6b.3):** wire the composition root (`scripts/fno_runner.py`, LIVE rung) to re-key the broker book on `instrument_token` via the shape adapter, with the distinct `UNRECONCILABLE_UNMAPPED` alert (MM7J.0 §4). Obtain the first-hand authenticated capture (MM7J.1 §D) before enabling the LIVE reconcile rung.
