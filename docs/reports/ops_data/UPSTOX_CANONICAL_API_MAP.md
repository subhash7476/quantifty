# Upstox Canonical API Map (Nifty Project)

**Status:** SOURCE OF TRUTH for broker integration reviews.
**Purpose:** Stop endpoint discovery by trial-and-error. No identity or endpoint decision is frozen from documentation alone — only from live-confirmed evidence.
**Last updated:** 2026-06-12 (live OAuth refresh + first-hand endpoint probe this session).

---

## 1. Current Account / Session Status

| Fact | Value |
|---|---|
| Live OAuth | works |
| Token | fresh, `LIVE-CANDIDATE` (refreshed 2026-06-12, ~24h validity) |
| Account | LIVE |
| Balance | zero |
| Holdings | zero |
| Positions | zero |
| Consequence | **all position endpoints currently return `data: []`** |
| `instrument_token` schema evidence | **NOT captured** (no non-empty payload exists) |

---

## 2. Critical Finding — the adapter called a dead endpoint  ✅ RESOLVED (6B.ENDPOINT, 2026-06-12)

**Resolution:** `upstox_adapter.py:129` corrected `net-positions → short-term-positions`; full suite 520/520 passing. The finding below is retained as the historical record.

The adapter (`core/brokers/upstox_adapter.py:129`) **previously** called:

```
GET /v2/portfolio/net-positions
```

**Live result against a VALID fresh token:**

```
HTTP 400
{ "status":"error","errors":[{ "errorCode":"UDAPI100012",
                               "message":"Invalid Endpoint" }] }
```

The path does not exist. Any logic relying on it operates on a dead path.

Because `UpstoxAdapter.get_positions()` wraps the call in a bare `except: return {}` (`upstox_adapter.py:153`), **live broker positions have been silently empty regardless of actual holdings/positions** — the 400 was swallowed on every call.

**Do not assume MM7J.1 endpoint conclusions are frozen.** MM7J.1's live probe hit `401` on an expired token and never reached the endpoint, so the dead path was never discovered; its `net-positions` schema verdict rests on documentation for a path the live API rejects.

---

## 3. Canonical Portfolio Endpoints

| Purpose | Endpoint | Confirmation status (this session) |
|---|---|---|
| **Positions** (short-term / trading) | `GET /v2/portfolio/short-term-positions` | **LIVE-CONFIRMED** — `200 SUCCESS`, `data: []` (account flat) |
| **Holdings** (demat) | `GET /v2/portfolio/long-term-holdings` | **LIVE-CONFIRMED** — `200 SUCCESS`, `data: []` |
| **MTF positions** | `GET /v3/portfolio/mtf-positions` | DOCUMENTED — not yet probed this session |
| Portfolio streaming | WebSocket — Portfolio Stream Feed (order/position/holding updates) | DOCUMENTED — potential LIVE execution/reconciliation validation later |

**Primary investigation target:** `/v2/portfolio/short-term-positions` (the documented "Get Positions" endpoint, live-confirmed).

**Dead paths observed this session (do not use):**

| Tried | Result |
|---|---|
| `/v2/portfolio/net-positions` | `400 UDAPI100012 Invalid Endpoint` |
| `/v2/portfolio/positions` | `400 UDAPI100012 Invalid Endpoint` |
| `/v3/portfolio/short-term-positions` | `404 UDAPI100060` |
| `/v2/order/positions` | `400 UDAPI100012 Invalid Endpoint` |

Sources: Upstox "Get Positions" documentation · Upstox Swagger/OpenAPI · first-hand live probe (2026-06-12).

---

## 4. Identity Investigation Rules

Until a **non-empty** position payload exists, all of the following are **UNVERIFIED**:

- `instrument_token` existence in the live payload
- `instrument_token` namespace shape
- `instrument_token` == platform ledger key

Documentation may suggest these fields exist. **We do not freeze identity architecture from documentation alone.** Empty arrays carry no schema and prove nothing about field shape.

---

## 5. Gate State

| Item | State |
|---|---|
| MM7J.2 | COMPLETE |
| #6b.3 | **HELD** |

**Reason held:** `instrument_token` is preserved through the adapter, but has **not** been observed in a live non-empty position payload.

---

## 6. Required Before #6b.3 Design May Begin

One authenticated payload from:

```
GET /v2/portfolio/short-term-positions
```

containing **at least one actual position**, captured as evidence:

- raw redacted JSON
- `instrument_token`
- `trading_symbol`
- `exchange`
- `product`
- `quantity`
- `average_price`

Then compare: **`instrument_token` vs platform ledger key.**

Only after this evidence exists may #6b.3 design begin.

> **Capture feasibility note (2026-06-12):** the live account has **zero balance / zero positions**, so a live non-empty payload cannot be produced from it without funding+trading. Realistic routes to the required evidence: (a) an actual open position appears in the account, or (b) mint a throwaway position in the Upstox **sandbox** (`api-sandbox.upstox.com`) and confirm the sandbox payload carries `instrument_token` in the same namespace shape.

---

## 7. Do Not

- Do not use `/portfolio/net-positions`.
- Do not infer schema from empty arrays.
- Do not freeze identity decisions from documentation alone.
- Do not implement token-primary reconciliation until a live payload exists.

---

## 8. Priority Order

1. ✅ **Broker endpoint correctness — DONE (6B.ENDPOINT, 2026-06-12)** — corrected `net-positions` → `short-term-positions` (`upstox_adapter.py:129`); 520/520 passing.
2. **Payload shape verification** — capture a non-empty `short-term-positions` body (blocked on a real/sandbox position).
3. **Identity verification** — `instrument_token` presence, namespace, == ledger key.
4. **#6b.3 design review** — the 7 questions, answered from observed payload.
5. **#6b.3 implementation** — token-primary reconciliation.

---

*Companion to `MM7J1_UPSTOX_PAYLOAD_VERIFICATION.md` (now partially superseded on the endpoint point) and the MM7H/MM7I/MM7J broker-integration series. Filed under the G1 / MM7 review-first, characterize-then-verify-before-change discipline.*
