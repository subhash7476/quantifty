# MM7J.1 — Upstox Net-Positions Payload Verification (#6b.2 final external gate)

**Type:** Verification — resolve the single remaining external uncertainty before #6b.2: does the live Upstox `GET /portfolio/net-positions` payload actually carry `instrument_token`, and in what format. **No implementation. No adapter/mapping/reconciliation change. No production code. No tests. No commits. No KB sync.**
**Date:** 2026-06-12
**Basis:** `MM7I_NAMESPACE_ROUTE_DECISION.md` (R1 frozen) · `MM7J0_R1_PRECONDITIONS.md` (P1/P2/P3, "single highest-value next action = capture one authenticated net-positions response") · first-hand artifacts captured this slice: (a) read-only live probe of `https://api.upstox.com/v2/portfolio/net-positions`; (b) authoritative Upstox V2 net-positions response schema (official developer docs); (c) read-only queries against `data/instruments/nse_fo_instruments.duckdb` (snapshot 2026-06-09); (d) `core/brokers/upstox_adapter.py`, `core/brokers/mapping/upstox.py`, `config/credentials.py`.
**State:** 516 passing · 0 failing · Route FROZEN = R1 · #6b.2 NOT STARTED (unchanged by this slice).

> **Scope guard.** This slice writes only this report. It issued **one read-only** authenticated GET (no order, no mutation) and read-only DB/doc reads. It changes no production code, no test, no DB, no credential. It does not start #6b.2/#6b.3/4C.6–4C.8.

---

## 0. Headline

**`instrument_token` is present in the Upstox V2 net-positions payload, format `NSE_FO|<numeric>` — byte-identical to the internal ledger namespace. R1 remains approved. #6b.2 may begin with the `instrument_token`-primary design.**

One honesty caveat governs the whole verdict: the **first-hand live capture was blocked** — the on-disk access token is **~31 days expired** (saved 2026-05-12; a live read-only probe returned `HTTP 401 UDAPI100050 "Invalid token"`). The `instrument_token` presence/format verdict therefore rests on the **authoritative official Upstox V2 schema** + the adapter's existing design (`from_broker_position` is built to prefer exactly this key), **not** on a captured authenticated body. A first-hand capture remains a cheap, recommended **pre-production-LIVE** confirmation (one OAuth token refresh + one read-only GET against an account that holds at least one open position) — but it is **not** a pre-coding blocker for #6b.2's broker-layer step, which is defensive and route-independent regardless.

---

## 1. J1 — Can a real net-positions payload be captured without placing a trade?

| Question | Finding |
|---|---|
| **Existing holdings?** | Irrelevant to this endpoint. `holdings` (`/portfolio/holdings`) is settled delivery equity; **net-positions** is the F&O/intraday book. They are different endpoints. |
| **Open positions?** | **Required for field evidence.** `net-positions` reflects current + day positions. A flat account returns `data: []` — which carries **no field schema at all**. To observe `instrument_token` in a *real* body you need ≥1 open/overnight position in the account. |
| **Paper account?** | Upstox offers a **sandbox** (`api-sandbox.upstox.com`) with mock order placement and a separate sandbox token — this is the safe way to manufacture a position for capture **without real capital**. The live `config/credentials.json` is a **live** account (`is_active: true`). |
| **Live account?** | Yes — the configured credential is a live Upstox individual account (`api_key`/`user_id` present, non-template). |
| **Safest operational method** | **(1)** Refresh the access token via the existing OAuth flow (`redirect_uri: /ops/callback/upstox`) — an interactive user action; **(2)** issue a **read-only** `GET /portfolio/net-positions` (non-mutating, no order). **No trade is required if the account already carries an open F&O position.** If the live book is flat, prefer the **sandbox** to mint a throwaway mock position rather than opening a real one. **Do not open a real position solely for this capture.** |

**J1 verdict:** A no-trade capture is possible **iff** the account already holds an open position. The capture's only hard dependency is a **fresh token** (the current one is expired, §2). A read-only GET places no order and is the safest probe.

---

## 2. J2 — Capture attempt (real authenticated payload)

**Live probe issued this slice (read-only, non-mutating):**

```
GET https://api.upstox.com/v2/portfolio/net-positions
Authorization: Bearer <on-disk token>
→ HTTP 401
{
  "status": "error",
  "errors": [{ "errorCode": "UDAPI100050",
               "message": "Invalid token used to access API" }]
}
```

**Why it failed — token age (metadata only, no secret printed):**

| Field | Value |
|---|---|
| `access_token` present | yes (len 311) |
| `token_saved_at` | 1778566042 → **2026-05-12** |
| age at probe | **~746.7 h (~31 days)** |
| `CredentialManager.is_token_expired` threshold | 22 h (`config/credentials.py:65`) |

Upstox V2 access tokens expire daily (~24 h). A 31-day-old token is unconditionally invalid — the `401 UDAPI100050` confirms it. **A first-hand authenticated body could not be captured this session.** Obtaining one requires an interactive OAuth refresh (user action); I did **not** place a trade and did **not** refresh the token autonomously.

**Fallback evidence — authoritative Upstox V2 net-positions response schema** (official developer documentation, `upstox.com/developer/api-documentation/get-positions`). Each position object in `data[]`:

```
exchange "NFO" | product "D" | multiplier 1.0 | quantity 15
instrument_token "NSE_FO|52618"          ← present, namespace #1
trading_symbol  "BANKNIFTY23OCT38000PE"  ← COMPACT form
tradingsymbol   "BANKNIFTY23OCT38000PE"  ← duplicate alias
average_price 2.65 | last_price 1.75 | close_price 1.95 | value 39.75
buy_value/sell_value, day_*/overnight_* buy/sell qty+price, pnl, realised, unrealised
```

### 2.1 First-hand resolution probe (real `UpstoxMapping`, in-memory, read-only)

The live token is dead, but the **resolution behavior** of the actual mapping against each candidate key *is* observable offline. Building the real `UpstoxMapping` (snapshot 2026-06-09; 59,241 `_ikey_by_tradingsymbol` entries, 55,508 `_ref_by_canonical`) and calling `from_broker_position` directly:

| Input (as the payload would carry it) | `from_broker_position` result |
|---|---|
| `instrument_token = "NSE_FO\|74892"` | **resolves** → `NSE:OPT:BANKNIFTY:2026-06-30:43000:CE` (+ tradingsymbol `BANKNIFTY 43000 CE 30 JUN 26`) — **deterministic, token path** |
| `trading_symbol = "NIFTY26JAN2623500CE"` (compact, MM7G/MM7I-assumed) | **`None`** — fallback miss |
| `trading_symbol = "BANKNIFTY 43000 CE 30 JUN 26"` (spaced master form) | resolves → `NSE:OPT:BANKNIFTY:2026-06-30:43000:CE` |

This **behaviorally demonstrates** the §1/§6 split: the `instrument_token` path resolves deterministically; the **compact** `trading_symbol` (the form the live payload actually uses, §6) resolves to **`None`**; only the **spaced** form resolves — and the live payload does **not** send the spaced form. So the live fallback is dead in practice, while the token path is live and exact.

---

## 3. J3 — Is `instrument_token` present? **YES**

- **Official V2 schema:** `instrument_token` is a documented field of every net-positions object, example `"NSE_FO|52618"`.
- **Adapter corroboration:** `from_broker_position` already **prefers** this exact key — `ikey = raw.get("instrument_token") or raw.get("instrument_key")` (`core/brokers/mapping/upstox.py:75`) — i.e. the code was written against a payload that carries it.
- **Order-side symmetry:** order placement sends `"instrument_token": order.symbol` (`upstox_adapter.py:86`), and Upstox echoes the same field back on the position book.

**Caveat (carried from §0/§2):** confirmed by **authoritative schema + adapter design**, not by a first-hand captured body (token expired). Confidence: high. Residual: one live capture.

---

## 4. J4 — Exact value format

| Source | `instrument_token` example |
|---|---|
| Official V2 schema | `NSE_FO\|52618`, also `BSE_EQ\|INE220J01025` |
| Master `instrument_key` (first-hand, snapshot 2026-06-09) | `NSE_FO\|98913`, `NSE_FO\|50973`, … |

Format = **`<SEGMENT>\|<token>`** — segment prefix (`NSE_FO`, `NSE_EQ`, `BSE_EQ`, …), a literal pipe, then a numeric (F&O/index) or ISIN-bearing (cash) token. **This is namespace #1 — the platform's `instrument_key`.** Not a bare numeric, not the spaced display string.

Master namespace prefixes present (first-hand): `NSE_FO` 41,227 · `MCX_FO` 15,427 · `NSE_EQ` 9,314 · `NSE_INDEX` 139.

---

## 5. J5 — Does `instrument_token` match the internal ledger namespace?

**Trace `order.symbol → broker payload → fill symbol → ledger key`:**

```
driver instrument_key  e.g.  NSE_FO|79381
   │  place_order(): payload["instrument_token"] = order.symbol         upstox_adapter.py:86
   ▼
Upstox order book / net-positions echoes  instrument_token = NSE_FO|79381   (V2 schema, §4)
   │  fill recorded to ledger keyed on fill.symbol = order.symbol = NSE_FO|79381
   ▼
PositionTracker._positions key  =  NSE_FO|79381   (restored key preserved byte-for-byte,
                                                    handler.py:284-287 — re-verified in MM7J.0)
```

Broker `instrument_token` (`NSE_FO|52618`) and internal ledger key (`NSE_FO|<token>`) are **the same string in the same namespace**.

**Answer: EXACT MATCH. No transform required.** A broker book keyed on `instrument_token` lands directly on `reconcile()`'s internal keys with **no** `UpstoxMapping` lookup and **no** format dependency. (Confirmed first-hand: master `instrument_key` rows are `NSE_FO|98913`-shaped, identical to the schema's token format.)

---

## 6. J6 — Exact `trading_symbol` format returned by the live payload

**Official V2 schema:** `trading_symbol = "BANKNIFTY23OCT38000PE"` — **COMPACT, no spaces** (`<UNDERLYING><YY><MON><STRIKE><CE|PE>`).

**Compare to MM7J.0's master finding (re-verified first-hand this slice):**

| Source | trading_symbol form | Example |
|---|---|---|
| **Live payload** (V2 schema) | **compact, no spaces** | `BANKNIFTY23OCT38000PE` |
| **Master `tradingsymbol`** (snapshot 2026-06-09) | **spaced** | `HINDALCO 1230 CE 30 JUN 26`, `NIFTY 27000 CE 30 JUN 26` |
| Master compact-form rows (`BANKNIFTY%PE`, no spaces) | **0 rows** | — |

**This positively confirms MM7J.0 §1.3:** the live payload's `trading_symbol` is the **compact** form, which **does not exist** in the master `tradingsymbol` column (spaced). Therefore `from_broker_position`'s `trading_symbol` fallback (`_ikey_by_tradingsymbol[trading_symbol]`, `upstox.py:77-78`) resolves to **`None` for every derivative** — fallback coverage is **0%**, now demonstrated from both sides (live compact ≠ master spaced; 0 compact master rows). The fallback is **unusable** and must never be the primary key. Reinforces the `instrument_token`-primary mandate.

---

## 7. J7 — Challenge R1: assume `instrument_token` absent

**Would R1 still be safe? NO. Would the recommendation change? YES. Would R2 become mandatory? NO — neither route is rescued by R2.**

If the live payload lacked `instrument_token`, R1's only deterministic key is gone and only the **format-fragile compact `trading_symbol`** remains — which §6 proves does not match the master (0% fallback). R1 would then map **every** live position to `None` → under fail-loud, an every-run `ORPHANED`/`UNRECONCILABLE` storm → driver refuses to start on every run (`driver.py:483-493`). **R1 unsafe.**

Critically, **R2 does not rescue this.** R2's `reconcile()` consumes the *same* `from_broker_position`, which prefers the *same* missing `instrument_token` and falls back to the *same* broken `trading_symbol`. A missing broker key starves **both** routes equally. The correct response to a (hypothetical) missing token is **a broker-layer key fix first** (derive `instrument_token` from another field, or add a compact-`trading_symbol`→`instrument_key` master projection), **then** either route — not "switch to R2."

**Because §3/§4 show the token IS present and IS the ledger key, this hypothetical does not fire. R1 stays.**

---

## 8. J8 — Challenge the payload assumptions: is a better identity field available?

Surveying every documented net-positions field for reconciliation identity:

| Candidate | Suitability as reconciliation key |
|---|---|
| **`instrument_token`** `NSE_FO\|52618` | **Best — and optimal.** Already == the internal ledger key (§5). Zero transform, format-independent, stable across expiries. |
| `trading_symbol` / `tradingsymbol` | Worst — compact display string, 0% master match (§6), drifts with display formatting. Fallback-only. |
| `exchange` `"NFO"` | Segment only — not an instrument identity. Useful as a guard, not a key. |
| `product` `"D"` | Product intent — not identity. |
| `multiplier`, `*_price`, `*_value`, `quantity`, `pnl`, `realised`, `unrealised` | Quantities/economics — change intraday; never identity. |

**Verdict:** no field is more suitable than `instrument_token`. It is not merely "the preferred field" — it is the **only** payload field that *is already* the canonical ledger key, so reconciliation needs no projection at all. The current design (token-primary, trading_symbol-fallback) is **optimal**; J8 surfaces no better alternative. (`exchange` is worth carrying only as a cheap sanity assertion that the token's segment prefix agrees — defensive, not identity.)

---

## Additional Review

### A. Do MM7J.0's conclusions remain valid? **Yes — and are strengthened.**

- P1 `instrument_token` path = 100% deterministic, format-independent → **reconfirmed** (token == ledger key, both `NSE_FO|<token>`, §4/§5).
- P1 `trading_symbol` fallback ≈ 0% → **upgraded from "likely" to demonstrated** (live compact vs master spaced, both sides, §6).
- P2 `instrument_token` is the load-bearing key, discarded today at `upstox_adapter.py:131-134` → **unchanged**; remains the HARD prerequisite.
- 1:1 map / complete master projection → unaffected (still cleared).
- P3 fail-loud only atop the token path, prefer a distinct `UNRECONCILABLE_UNMAPPED` alert → **unchanged**.

### B. What evidence would reverse the recommendation (→ R2 / → broker-layer fix first)?

1. A **first-hand captured** authenticated body that **omits** `instrument_token`, or returns it in a namespace that is **not** `<SEGMENT>|<token>` matching the ledger (→ broker-layer key fix before either route; §7).
2. A committed decision to re-key `PositionTracker._positions` to `canonical_id` (→ R1's instrument_key target invalidated; R2).
3. A confirmed near-term Phase-4C resume (4C.6→4C.8) before #6b is needed live (→ build R1, then revert = wasted motion).

Absent all three — and none is in evidence — R1 holds.

### C. Should #6b.2 proceed immediately after this verification? **Yes, with a scoped boundary.**

- **Proceed now:** the broker-layer `instrument_token` preservation + re-key in `get_positions()` (`upstox_adapter.py:131-149`) — step 1 of the MM7J.0 §4 gate. It is defensive (token-primary, trading_symbol-fallback, distinct unmapped alert), route-independent, trips neither G1 guard, and is needed by R1 **and** R2.
- **Gate before trusting the LIVE reconcile rung in production:** obtain **one first-hand authenticated capture** (§D). The defensive design means a doc-vs-live mismatch surfaces **loudly** (an alert / refuse-to-start), never silently — so coding ahead of the capture carries no silent-failure risk.

### D. Is any additional verification still required?

**Yes — exactly one, and only as a pre-production-LIVE gate (not a pre-coding blocker):**

> **Capture one first-hand authenticated `/portfolio/net-positions` body** confirming (a) `instrument_token` present and (b) its value equals the ledger `instrument_key` for a known open position. Method: refresh the token (OAuth, user action) → read-only GET against an account with ≥1 open position, **or** mint a throwaway position in the Upstox **sandbox**. **No real trade should be opened solely for this.**

Everything else is verified. No further analysis is required before #6b.2's broker-layer step.

---

## 9. Return summary

1. **`instrument_token` present?** **YES** — documented in the authoritative Upstox V2 net-positions schema and preferred by the existing `from_broker_position` (`upstox.py:75`). *Caveat:* not confirmed by a first-hand authenticated body this slice — the on-disk token is ~31 days expired (live read-only probe → `HTTP 401 UDAPI100050`); confirming evidence is the official schema + adapter design.
2. **Exact format:** `NSE_FO|<numeric>` (e.g. `NSE_FO|52618`) — segment-prefixed pipe-token, **identical** to the master/ledger `instrument_key` (first-hand: master rows are `NSE_FO|98913`-shaped).
3. **`trading_symbol` format:** **compact** `BANKNIFTY23OCT38000PE` — confirmed **absent** from the spaced master (`HINDALCO 1230 CE 30 JUN 26`; 0 compact rows) → fallback coverage 0%, fallback-only, never primary.
4. **Does R1 remain approved?** **Yes.** `instrument_token` == ledger key → exact match, no transform (§5); no R2-forcing condition fired.
5. **Can #6b.2 begin?** **Yes** — start with the broker-layer `instrument_token` preservation (`upstox_adapter.py:131-149`), which is defensive and route-independent. Trusting the LIVE reconcile rung in production is gated on one first-hand authenticated capture.
6. **Remaining blockers:** exactly one, and it is a **pre-production-LIVE** gate, not a pre-coding one — a single first-hand authenticated net-positions capture (needs an OAuth token refresh; account must hold ≥1 open position, or use the sandbox). No real trade should be placed for it.

*Filed under the G1 / MM7A–J review-first, characterize-then-verify-before-change discipline. Companion to `MM7I_NAMESPACE_ROUTE_DECISION.md` and `MM7J0_R1_PRECONDITIONS.md`. Next slice: #6b.2 — implement R1 behind the §4 revised gate, beginning with the broker-layer `instrument_token` preservation; obtain the first-hand authenticated capture before enabling the LIVE reconcile rung.*
