# MM7K.0 — Broker Contract Hardening: Characterization Report

**Branch:** `main` | **Commit:** `2fd4892` | **Suite:** 522 passing | **Date:** 2026-06-15

**Preceded by:** MM7J.3 — token-primary reconciliation wiring + UNRECONCILABLE_UNMAPPED_POSITION  
**Next slice:** MM7K.1 — Broker Failure Contract: Distinguish Error from Empty

---

## Context

MM7J is complete. `instrument_token` is now the authoritative reconciliation identity. `trading_symbol` is retired as a reconciliation key. Live payload evidence is captured. Token-primary reconciliation is active.

The next priority is broker contract hardening before any `ExecutionMode.LIVE` work proceeds. This report characterizes every broker failure path as it exists today, defines desired semantics, and identifies the single highest-leverage next engineering slice.

---

## Deliverable 1 — Broker Failure Map

### 1.1 Execution Operations

#### `GET /v2/portfolio/short-term-positions` → `get_positions()`

**File:** `core/brokers/upstox_adapter.py:127–154`

| Failure Condition | Code Path | Returned | Caller Sees |
|-------------------|-----------|----------|-------------|
| HTTP 401/403 | `_make_request` raises `RuntimeError` at `:63` → caught by `except Exception` at `:153` | `{}` | Empty dict |
| HTTP 429 | `_make_request` retries 3× then returns `None` → guard at `:133` fails → `except Exception` | `{}` | Empty dict |
| HTTP 5xx | `raise_for_status()` → `RequestException` → retry 3× → raises → caught | `{}` | Empty dict |
| Timeout (10s) | `RequestException` → retry 3× → raises → caught | `{}` | Empty dict |
| Malformed JSON | implicit exception → caught | `{}` | Empty dict |
| `KeyError` on missing field | caught by broad except | `{}` | Empty dict |
| True flat account | loop doesn't iterate | `{}` | Empty dict |

**Critical:** Every failure mode and "account is flat" both return `{}`. They are indistinguishable.

---

#### `GET /v2/order/details` → `get_order_status()`

**File:** `core/brokers/upstox_adapter.py:108–125`

| Failure Condition | Code Path | Returned | Caller Sees |
|-------------------|-----------|----------|-------------|
| HTTP 401 | `RuntimeError` from `_make_request` → caught at `:124` | `OrderStatus.SUBMITTED` | False pending |
| HTTP 429/5xx/timeout | `Exception` → caught at `:124` | `OrderStatus.SUBMITTED` | False pending |
| Missing `data.status` field | `KeyError` → caught at `:124` | `OrderStatus.SUBMITTED` | False pending |
| Unknown status string | `.get()` returns default | `OrderStatus.SUBMITTED` | Ambiguous |
| True pending order | Maps `"open"` | `OrderStatus.OPEN` | Correct |

**Critical:** `SUBMITTED` is both the truth and the lie. The caller cannot distinguish.

---

#### `POST /v2/order/place` → `place_order()`

**File:** `core/brokers/upstox_adapter.py:80–106`

| Failure Condition | Code Path | Returned |
|-------------------|-----------|----------|
| HTTP 401 | `RuntimeError` raised at `:63` → caught at `:104` → re-raised | Exception propagates |
| HTTP 429 (all retries exhausted) | `_make_request` returns `None` → guard fails → `KeyError` → caught → re-raised | Exception propagates |
| HTTP 5xx (all retries exhausted) | Exception chain → caught → re-raised | Exception propagates |
| Malformed response | `KeyError` on `response['data']['order_id']` → caught → re-raised | Exception propagates |

`place_order` is the one operation that propagates failures. It does not swallow. The handler catches it at `handler.py:664`.

---

#### `DELETE /v2/order/cancel` → `cancel_order()`

**File:** `core/brokers/upstox_adapter.py:156–161`

| Failure Condition | Returned |
|-------------------|----------|
| Any exception (401/429/5xx/timeout) | `False` |
| 404 (order not found) | `False` |
| True cancellation failure (broker rejected) | `False` |

`False` means "I tried and failed" or "API is down" or "order doesn't exist". All identical to caller.

---

### 1.2 Market Data Operations

#### `GET /v2/market-quote/quotes` → `fetch_ltp()` / `fetch_ltp_batch()`

**File:** `core/brokers/upstox_market_data.py:32–124`

| Operation | Failure → Returns |
|-----------|-------------------|
| `fetch_ltp` — no token | `None` |
| `fetch_ltp` — HTTP ≠ 200 | `None` |
| `fetch_ltp` — instrument not in response | `None` |
| `fetch_ltp` — any exception | `None` |
| `fetch_ltp_batch` — any failure | `{}` (entire batch lost) |

Partial batch failures are silently absorbed: if 3 of 5 instruments fail to parse, the dict contains only the 2 that succeeded. No indication which instruments failed.

---

#### `GET /v2/option/chain` → `fetch_option_chain()`

**File:** `core/data/options_provider.py:175–223`

| Failure Condition | Behavior |
|-------------------|----------|
| API returns HTTP ≠ 200 | Fallback to DuckDB cache |
| `requests.RequestException` | Fallback to DuckDB cache |
| Cache populated (any age) | Returns cached rows — **no staleness flag** |
| Cache miss | Returns `[]` |

The `OptionChainRow` dataclass does not carry `data_source` or `snapshot_timestamp`. The UI receives stale data with no marking.

---

#### Historical Candles — `fetch_intraday_candles_v3()` / `fetch_historical_candles_v3()`

**File:** `core/api/upstox_client.py:48–182`

These are the only operations that propagate failures correctly. HTTP errors raise `ValueError` or `Exception` with the HTTP status in the message. Callers must handle explicitly.

Exception: `fetch_ohlc()` at `:44` returns an error dict `{"status": "error"}` instead of raising — a type inconsistency with the V3 methods.

---

#### WebSocket — `wss://api.upstox.com/v3/feed/market-data-feed`

**File:** `core/database/ingestors/websocket_ingestor.py:150–188`

| Event | Behavior |
|-------|----------|
| Authorization 401 | Caught, logged, retry with backoff |
| Connection refused | Caught at `:182`, retry with backoff |
| Frame parse error | Caught at `:182`, reconnect |
| Prolonged outage | **Infinite reconnect loop** (60s ceiling, no max count) |
| Messages during reconnect | **Lost permanently** (no offline buffer) |

Backoff starts at 1.0s, doubles each attempt, caps at 60s. No maximum retry count. No circuit-breaker.

---

## Deliverable 2 — Failure Semantics Report

### 2.1 Positions

| Scenario | Current Behavior | Recommended Behavior |
|----------|-----------------|----------------------|
| Timeout / network error | Returns `{}` → treated as flat | Raise `BrokerUnavailableError` — reconciliation halts, does NOT proceed |
| HTTP 401 token expired | Returns `{}` → treated as flat | Raise `BrokerAuthError` — trigger operator alert, halt |
| HTTP 429 rate limited | Returns `{}` after 3 retries | Raise `BrokerRateLimitError` — backoff and retry with caller awareness |
| HTTP 5xx broker outage | Returns `{}` → treated as flat | Raise `BrokerUnavailableError` — do not reconcile against phantom state |
| Malformed payload | Returns `{}` → treated as flat | Raise `BrokerContractError(field, value)` — log exact field that failed |
| True flat account | Returns `{}` — correct | Returns `{}` with explicit `source=LIVE_CONFIRMED` tag |

**Key principle:** An empty broker book and a failed API call must never look the same. The reconciliation engine must be able to ask "did you get a real answer?" before deciding whether to proceed.

---

### 2.2 Order Status

| Scenario | Current Behavior | Recommended Behavior |
|----------|-----------------|----------------------|
| API error of any kind | Returns `OrderStatus.SUBMITTED` | Raise `BrokerUnavailableError` — caller retries with exponential backoff |
| HTTP 401 | Returns `OrderStatus.SUBMITTED` | Raise `BrokerAuthError` — do not cache stale status |
| Unknown status string | Returns `OrderStatus.SUBMITTED` | Raise `BrokerContractError("unknown_status", value)` |
| True SUBMITTED | Returns `OrderStatus.SUBMITTED` | Returns `OrderStatus.SUBMITTED` with `confirmed=True` |

**Key principle:** The order tracker must know whether SUBMITTED is confirmed or assumed. These are not the same thing.

---

### 2.3 Order Placement

Current behavior is already closest to correct — 401 propagates. The gaps:

| Gap | Current | Recommended |
|-----|---------|-------------|
| 401 on `place_order` | Exception propagates, no kill switch activated | Activate kill switch; halt all pending signal processing |
| 429 exhausted | Returns `None` → `KeyError` → exception | Raise `BrokerRateLimitError` with retry-after hint |

---

### 2.4 Order Cancellation

| Scenario | Current Behavior | Recommended Behavior |
|----------|-----------------|----------------------|
| API unavailable | Returns `False` | Raise `BrokerUnavailableError` — caller must assume cancel did NOT happen |
| 404 (order not found) | Returns `False` | Return `True` (idempotent — order is gone, cancel goal achieved) |
| True rejection | Returns `False` | Return `False` with `reason` enum |

---

### 2.5 Option Chain

| Scenario | Current Behavior | Recommended Behavior |
|----------|-----------------|----------------------|
| API fails, cache hit | Returns stale data, no marking | Return data with `data_source=CACHE`, `cache_age_seconds=N` |
| API fails, cache miss | Returns `[]` | Raise `DataUnavailableError` — do not silently return empty |
| Cache age > threshold | No check | Refuse to serve; raise `StaleDataError` |

---

### 2.6 LTP / Market Quotes

| Scenario | Current Behavior | Recommended Behavior |
|----------|-----------------|----------------------|
| API unavailable | Returns `None` | Distinguish `None` (not found) from `BrokerUnavailableError` |
| Batch partial failure | Returns partial dict, no indication | Return `BatchLTPResult(data={...}, failures=[...])` |

---

### 2.7 WebSocket

| Scenario | Current Behavior | Recommended Behavior |
|----------|-----------------|----------------------|
| Prolonged outage | Infinite retry | Max retry count; raise `WebSocketDeadError` after cap |
| Messages lost during reconnect | Lost silently | Emit `TickGapEvent` or trigger REST fallback poll |
| Authorization 401 | Retries forever | Raise `BrokerAuthError` after N auth failures — circuit-break |

---

## Deliverable 3 — OAuth Lifecycle Report

### 3.1 Token Storage

```
File:    config/credentials.json
Fields:  access_token (JWT), token_saved_at (Unix timestamp float), last_refresh_date (date string)
Format:  Plain JSON, disk-persisted
Loaded:  At startup via CredentialManager._load() — no exception on missing file
```

### 3.2 Expiry Detection

**`credentials.py:58–65`**

```python
@property
def is_token_expired(self) -> bool:
    saved_at = self.get("token_saved_at")
    if not saved_at:
        return self.has_upstox_token   # no timestamp → treat as expired
    elapsed_hours = (time.time() - saved_at) / 3600
    return elapsed_hours >= 22         # 22h threshold (Upstox token is 24h)
```

This is a read-only property. It detects expiry but takes no action.

### 3.3 Refresh Path — Does Not Exist

There is no automatic token refresh anywhere in the codebase. The OAuth flow is entirely manual:

```
Operator clicks "Login with Upstox"
    → Flask redirects to api.upstox.com/v2/login/authorization/dialog
    → User authenticates in browser
    → Browser redirected to /ops/callback/upstox?code=ABC
    → Flask POSTs code to api.upstox.com/v2/login/authorization/token
    → Response JSON saved to config/credentials.json
    → token_saved_at = time.time()
```

There is no `refresh_token` grant, no background refresh thread, no scheduled re-auth.

### 3.4 OAuth Lifecycle Diagram

```
T=0h   Operator launches platform
         └─ CredentialManager._load() reads credentials.json
         └─ access_token loaded into memory cache

T=0–22h  Normal operation
         └─ All API calls use Bearer {access_token}
         └─ is_token_expired = False

T=22h   is_token_expired becomes True
         └─ CredentialManager.is_token_expired → True
         └─ Platform has NO automatic response to this flag
         └─ Nothing happens unless explicitly checked by driver startup gate

T=22–24h  DANGER ZONE
         └─ Token is flagged expired but may still work (Upstox 24h window)
         └─ Any check of is_token_expired returns True
         └─ Upstox API still accepts the token

T≈24h   Upstox invalidates token
         └─ Next API call receives HTTP 401

         What happens per component:
         ┌─ upstox_adapter._make_request ──────── raises RuntimeError("token expired")
         │   ├─ get_positions() ────────────────── caught → returns {}  ← SILENT
         │   ├─ get_order_status() ──────────────── caught → returns SUBMITTED  ← SILENT
         │   └─ place_order() ──────────────────── raises → handler catches → logs  ← VISIBLE
         │
         ├─ upstox_market_data.fetch_ltp() ────── HTTP != 200 → returns None  ← SILENT
         │
         ├─ options_provider._fetch_from_upstox() HTTP != 200 → ([], None) → stale cache  ← SILENT
         │
         └─ websocket_ingestor._get_authorized_url()
              HTTP error → caught → retry loop  ← LOOPS FOREVER
```

### 3.5 Visibility of 401 Failures by Component

| Component | 401 Response | Visible to Operator? |
|-----------|-------------|----------------------|
| `place_order` | Exception propagates to handler log | YES — error log |
| `get_positions` | Swallowed → `{}` | NO — looks like flat account |
| `get_order_status` | Swallowed → `SUBMITTED` | NO — looks like real status |
| `cancel_order` | Swallowed → `False` | NO — looks like cancel failure |
| `fetch_ltp` | Swallowed → `None` | NO — looks like missing price |
| `fetch_option_chain` | Stale cache returned | NO — looks like fresh data |
| WebSocket authorize | Retry loop | DELAYED — log after retry failure |

### 3.6 Operational Consequence

If the token expires at 14:00 during a live session:

- Trading loop continues running with no clear signal of degradation
- Reconciliation at next gate call receives `{}` → detects QUANTITY_MISMATCH → may abort
- Order status polling returns `SUBMITTED` for all orders regardless of broker state
- Option chain shows stale Greeks indefinitely
- WebSocket enters infinite retry loop
- Operator receives no single root-cause alert — failures are scattered across multiple log lines

Manual re-auth (browser OAuth flow) is the only recovery. There is no in-process mechanism.

---

## Deliverable 4 — LIVE Readiness Gap Report

### CRITICAL

**C1 — Broker API failure is indistinguishable from flat account**

`upstox_adapter.py:153` returns `{}` for both "no positions" and "API is down". Reconciliation engine treats both as a flat account. A 401 at 14:00 will cause reconciliation to generate QUANTITY_MISMATCH alerts and refuse to allow the trading loop to continue. Actual broker positions are unaffected — the platform loses visibility with no clear error signal.

**C2 — Token expiry has no automated recovery**

A 24-hour session crosses the token expiry boundary without exception. When the token expires, most failures are silent (§3.5). The operator sees degraded behaviour across multiple subsystems with no single root-cause alert. Manual browser OAuth re-auth is the only recovery path. This is not compatible with an unattended LIVE deployment.

**C3 — Order status returns `SUBMITTED` on any API error**

During a token expiry window, every call to `get_order_status()` returns `SUBMITTED`. The order tracker has no way to detect this. If an order was actually FILLED while the API was unreachable, the position tracker will not update, PnL will be wrong, and the position stacking guard will fail to block a duplicate entry.

**C4 — Option chain staleness is not surfaced**

The UI can display hours-old Greeks without any indicator. For a delta-adjustment trigger that fires at GEX or IV thresholds, stale data produces false triggers or missed triggers. There is no threshold after which the platform refuses to act on cached options data.

---

### HIGH

**H1 — WebSocket reconnect loop is unbounded**

If Upstox WebSocket is unreachable, the ingestor retries forever at 60-second intervals. The trading loop receives no ticks. There is no circuit-breaker, no tick-gap event, and no automatic switch to REST polling fallback. Duration of data blindness is unlimited.

**H2 — LTP batch failure loses the entire batch silently**

`fetch_ltp_batch()` returns `{}` on any error. A transient 429 causes an entire cycle of pricing to use stale values. There is no partial-success path.

**H3 — 401 on `place_order` does not activate kill switch**

Token expiry during order placement propagates as an exception to `handler.py:664`, which logs the error but does not activate the kill switch or halt signal processing. Subsequent signals also fail, also log, and also do not halt. The platform appears to be running while no orders are being placed.

**H4 — `cancel_order` returns `False` for transient API errors**

If the broker is temporarily unavailable when a cancel is requested, the cancel does not execute but the platform does not retry. The order remains open on the broker. If the platform has already updated internal state to reflect the cancellation, the ledger and broker are now diverged.

---

### MEDIUM

**M1 — Partial LTP batch failure is invisible**

When 3 of 5 instruments fail to fetch, the returned dict has 2 entries. The caller cannot identify which instruments failed. Options pricing silently uses stale values for the missing instruments.

**M2 — `fetch_ohlc` (V2) returns an error dict instead of raising**

`upstox_client.py:44` returns `{"status": "error", "message": ...}`. All other historical candle methods raise. This is a type inconsistency that callers using both V2 and V3 must handle as two different error contracts.

**M3 — `_make_request` rate limiter is static**

Fixed 0.11s sleep between requests (≈9 req/s). No dynamic adjustment based on `Retry-After` header inspection. Bursts can still trigger 429s under a sliding window rate limiter.

**M4 — No startup gate for token expiry**

`driver.py` checks reconciliation alerts at startup but does NOT check `is_token_expired` before entering the RUNNING state. A platform started with an already-expired token proceeds to RUNNING and silently fails on every broker call.

---

### LOW

**L1 — `fetch_ohlc` has no explicit timeout**

No `timeout=` parameter. On a hung connection, this can block indefinitely.

**L2 — WebSocket subscription does not validate acknowledgement**

After sending the subscribe JSON, the ingestor immediately begins reading messages. If the broker rejects the subscription silently, ticks for those instruments are never received. No ACK/NACK check exists.

---

## Deliverable 5 — Recommended Next Slice

### MM7K.1 — Broker Failure Contract: Distinguish Error from Empty

**Scope:** `core/brokers/upstox_adapter.py` only. No other files touched.

**What changes:**

1. Define three narrow exception types local to the adapter module:
   - `BrokerAuthError(Exception)` — token expired/invalid (HTTP 401/403)
   - `BrokerUnavailableError(Exception)` — timeout, 5xx, connection error, rate limit exhausted
   - `BrokerContractError(Exception)` — missing field, malformed response, schema drift

2. In `get_positions()`: raise the appropriate typed exception instead of `except Exception: return {}`. Return `{}` **only** when the API returns HTTP 200 and `data` is genuinely empty.

3. In `get_order_status()`: raise the appropriate typed exception instead of returning `SUBMITTED`. Return `SUBMITTED` only when the API explicitly confirms it.

4. In `cancel_order()`: raise on auth/availability errors; return `False` only for genuine business rejections (order already filled, not cancellable).

**Selection criteria:**

- **Highest risk reduction** — eliminates C1 (phantom flat account) and C3 (false SUBMITTED) with a single file change
- **Smallest scope** — one file, three new exception classes, three method bodies changed
- **Strongest impact on LIVE readiness** — C1 and C3 are the two failure modes that would produce incorrect broker-side outcomes under real money
- **No cascading risk** — does not touch reconciliation, handler, OAuth, or any other component; callers receive typed exceptions they can handle at their own pace

**What this does NOT solve** (explicitly deferred):

- Token auto-refresh (separate OAuth slice)
- WebSocket circuit-breaker (separate ingestor slice)
- Options staleness marking (separate options-provider slice)
- Startup gate for token expiry (separate driver slice)

**Success criterion:** After MM7K.1, calling `get_positions()` when the broker is unavailable raises `BrokerUnavailableError`. Calling it with an expired token raises `BrokerAuthError`. Calling it when the account is genuinely flat returns `{}`. These three outcomes are distinguishable. The reconciliation engine can halt safely on error instead of acting on phantom state.

---

*No code was modified in this slice. All findings are derived from reading:*  
*`core/brokers/upstox_adapter.py`, `core/brokers/upstox_market_data.py`, `core/api/upstox_client.py`,*  
*`core/data/options_provider.py`, `core/auth/credentials.py`, `core/execution/reconciliation.py`,*  
*`core/execution/handler.py`, `core/database/ingestors/websocket_ingestor.py`,*  
*`core/runtime/driver.py`, `flask_app/blueprints/ops/routes.py`*
