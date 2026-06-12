# MM7J.0 — R1 Preconditions Verification (#6b.2 gate)

**Type:** Verification — empirically test the two R1 preconditions MM7I made conditional (P1 master coverage, P2 `instrument_token` path) and re-challenge the P3 unmapped policy, against the **live master snapshot on disk**, before any #6b.2 implementation. **No implementation. No adapter/mapping/reconciliation change. No code. No tests. No commits.**
**Date:** 2026-06-12
**Basis:** `MM7I_NAMESPACE_ROUTE_DECISION.md` (R1 frozen; §4.4 pre-checks; §7 R2-forcing evidence) · first-hand queries against `data/instruments/nse_fo_instruments.duckdb` (snapshot **2026-06-09**) · `core/brokers/mapping/upstox.py`, `core/brokers/upstox_adapter.py`, `scripts/fetch_instrument_master.py`, `tests/brokers/test_upstox_positions.py`.
**State:** 516 passing · 0 failing · Route FROZEN = R1 · #6b.2 NOT STARTED (unchanged by this slice).

> **Scope guard.** This slice writes only this report. It runs read-only queries against the master DB and reads source. It changes no production code, no test, no DB. It does not start #6b.2/#6b.3/4C.6–4C.8.

---

## 0. Headline

**R1 remains approved — but the verification reclassifies its two preconditions:**

- **P1 (coverage) splits into two paths with opposite verdicts.** Via **`instrument_token`** coverage is **deterministic 100%** and format-independent — the broker's `instrument_token` *is* the internal ledger key (proven below), so no string match and no `UpstoxMapping` lookup is even required. Via the **`trading_symbol` fallback** coverage is **unverifiable offline and likely 0%**: the master `tradingsymbol` is the **spaced** form `NIFTY 20350 CE 30 JUN 26`, and the compact form the MM7G/MM7I examples assumed (`NIFTY26JAN2623500CE`) **does not exist in the master** (0 rows).
- **P2 is therefore upgraded from "follow-up, noted" (MM7I §4.4 / MM7H §4) to a HARD prerequisite.** R1's soundness rests entirely on the `instrument_token` path; the `trading_symbol` fallback cannot be relied on without confirming a live-payload format match that is not observable from repo artifacts.

**Two of MM7I §7's R2-forcing conditions are now CLEARED by evidence** (the `trading_symbol → instrument_key` map is **1:1** — 0 collisions across 59,241 distinct resolvable symbols; the master-side projection is **complete** — 100% of NSE_FO derivatives carry a non-null, resolvable `tradingsymbol`). **One new hard gate is ADDED**: the live net-positions payload must actually carry `instrument_token`, and the adapter must preserve + key on it.

---

## 1. P1 — Master coverage

### 1.1 What was measured (master snapshot 2026-06-09, on disk)

Latest snapshot row counts (the population a live F&O run reconciles against):

| Segment | rows | | Derivative type | rows |
|---|---|---|---|---|
| NSE_FO | 41,227 | | PE | 27,939 |
| MCX_FO | 15,427 | | CE | 27,920 |
| NSE_EQ | 9,314 | | FUT | 795 |
| NSE_INDEX | 139 | | (NSE_FO FUT/CE/PE total) | **41,227** |

### 1.2 Master-side projection is complete and unique (the parts I *can* verify offline)

| Check | Result | Evidence |
|---|---|---|
| NSE_FO FUT/CE/PE rows with **non-null** `tradingsymbol` | **41,227 / 41,227 = 100.0000%** | direct query, latest snapshot |
| …with a **resolvable type** (`CE/PE/FUT` ∈ `_TYPE_TO_ASSET`) | **100%** — every derivative type resolves | `resolver.py:30-33`, `_build:216-217` |
| **1:1** `tradingsymbol → instrument_key` across **all** resolvable types | **0 collisions** / 59,241 distinct `tradingsymbol`s | aggregate `COUNT(DISTINCT instrument_key)>1` → empty |

This **clears MM7I §7 challenge #4** (non-1:1 map). The `UpstoxMapping` projection (`upstox.py:42-60`) populates `_ikey_by_tradingsymbol` for every NSE_FO derivative, with no last-write-wins ambiguity.

### 1.3 The decisive negative — `trading_symbol` format

The master `tradingsymbol` is sourced verbatim from Upstox's instrument-master JSON (`fetch_instrument_master.py:140`, `item.get("tradingsymbol") or item.get("trading_symbol")`). Its observed form is **spaced**:

```
NIFTY 20350 CE 30 JUN 26       -> NSE_FO|79381
BANKNIFTY 43000 CE 30 JUN 26   -> NSE_FO|74892
```

The compact form assumed throughout MM7G/MM7H/MM7I (`NIFTY26JAN2623500CE`) returns **0 rows** as a `tradingsymbol`. So the `from_broker_position` `trading_symbol` fallback (`upstox.py:77-78`, `_ikey_by_tradingsymbol[trading_symbol]`) succeeds **only if** the live Upstox net-positions `trading_symbol` field is itself the spaced master form. **This cannot be confirmed from any repo artifact** — the only positions fixtures (`tests/brokers/test_upstox_positions.py:30-65`) use equity symbols `RELIANCE`/`TCS` and never a derivative, never `instrument_token`.

### 1.4 The path that *is* deterministic — `instrument_token`

Upstox order placement sends `"instrument_token": order.symbol` (`upstox_adapter.py:86`), and the fill is recorded to the ledger keyed on `fill.symbol` = that same order symbol (the driver instrument key, e.g. `NSE_FO|79381`). Net-positions returns the position under `instrument_token` = the same `instrument_key` (`NSE_FO|…`). Therefore:

> **The broker `instrument_token` equals the internal ledger key by construction.** A broker book keyed on `instrument_token` matches `reconcile()`'s internal keys **directly** — no `_ikey_by_tradingsymbol` lookup, no format dependency, no `UpstoxMapping` call. `from_broker_position` prefers exactly this key (`upstox.py:75`).

### 1.5 P1 verdict

| Key path | Coverage | Verifiable offline? | Failure mode |
|---|---|---|---|
| **`instrument_token`** | **100% deterministic** | Yes (key == ledger key, `upstox_adapter.py:86`) | none — exact-string identity |
| **`trading_symbol` fallback** | **0% (likely) — unverifiable** | No (live payload format not observable) | every position → `None` → (under fail-loud) `ORPHANED_BROKER_POSITION` → driver refuses to start on **every** run (`driver.py:483-493`) |

**Coverage is sound if and only if R1 uses the `instrument_token` path.** Relying on the `trading_symbol` fallback alone is the §7-challenge-#2 format-drift hazard, now concretely demonstrated (master is spaced; the compact assumption is absent).

---

## 2. P2 — Instrument-token path

### 2.1 Trace: net-positions payload → `get_positions()`

`UpstoxAdapter.get_positions()` (`upstox_adapter.py:126-152`):

```
GET /portfolio/net-positions
  → for pos_data in response['data']:
        symbol    = pos_data['trading_symbol']      # :132  (the dict KEY)
        qty       = float(pos_data['quantity'])     # :133
        avg_price = float(pos_data['average_price'])# :134
        positions[symbol] = Position(symbol=symbol, side=…, quantity=abs(qty), …)  # :143-149
```

| Question | Verdict | Evidence |
|---|---|---|
| Does `instrument_token` exist in the payload? | **Expected yes** (Upstox V2 net-positions returns `instrument_token` = the instrument_key; `from_broker_position` is built to prefer it, `upstox.py:75`) — **but NOT confirmed by any fixture**; `test_upstox_positions.py` omits it entirely. **Confirmation gap.** | `upstox.py:75`; `test_upstox_positions.py:30-65` |
| Is it discarded? | **Yes — unconditionally.** Only `trading_symbol`/`quantity`/`average_price` are read; any `instrument_token` in `pos_data` is dropped. | `upstox_adapter.py:131-134` |
| Smallest legal place to preserve it? | Inside the existing loop — capture `pos_data.get('instrument_token')` and **re-key the returned dict on it** (fallback to `trading_symbol` when absent). | `upstox_adapter.py:131-149` |

### 2.2 Smallest legal preservation — file:line

**Home: `core/brokers/upstox_adapter.py:131-149` (the broker layer).** This is legal: the broker layer may handle `instrument_token` (a plain payload string), and re-keying the dict imports no `CanonicalInstrument` (the only G1 ban on this file, `test_g1_closure_guard.py:312-330`). It trips **neither** G1 guard.

**Rejected alternative:** adding an `instrument_key`-named field to `Position` (`core/execution/position_models.py`) — **illegal**: `test_instrument_key_absent_from_execution` (`test_g1_closure_guard.py:333-340`) greps every `core/execution/*.py` for the literal string `instrument_key` and asserts none. A field carrying the token under a non-`instrument_key` name would skirt the literal grep but is semantically the same leak; keep token handling in `core/brokers/`.

**Consequence for R1's shape:** if `get_positions()` keys the book on `instrument_token`, the broker book arrives **already in namespace #1**. R1's "remap" then collapses to "use the key as-is," and `UpstoxMapping` is needed only for the residual `trading_symbol`-only fallback rows. This is *smaller* than MM7I's framing (which routed the whole book through `UpstoxMapping`).

### 2.3 P2 verdict

`instrument_token` is the load-bearing key for R1 and is **discarded today** (`:131-134`). Preserving it is a **2–4 line broker-layer change** at `upstox_adapter.py:131-149`, legal under both G1 guards. **P2 is upgraded from optional follow-up to a HARD R1 prerequisite** — with one open confirmation (§2.1: prove the live payload actually carries `instrument_token`).

---

## 3. P3 — Unmapped-policy validation (challenge)

**MM7I §4.3 recommended:** unmapped (`from_broker_position → None`) → keep `trading_symbol` key → surfaces as `ORPHANED_BROKER_POSITION` (fail-loud, refuse startup).

**Challenge — is fail-loud still correct if coverage < 100%?** The answer is conditional on *which path produced the miss*, and the §1 split makes this sharp:

- **On the `instrument_token` path, coverage is 100%, so "unmapped" is near-impossible for a position the platform itself opened** (it sent that `instrument_token`). A genuinely unidentifiable live position is then a *real* anomaly — **fail-loud is correct**: refusing to start beats trading blind against a book you can't reconcile (ADR-001 spirit; `driver.py:483-493`).
- **On the `trading_symbol` fallback with a format mismatch (§1.3), "unmapped" is 100% — and fail-loud is CATASTROPHIC**: it converts a *formatting* defect into a total, every-run startup refusal that *looks* like a fleet of orphaned positions. Here fail-loud is actively misleading — the operator chases phantom orphans instead of a symbol-format bug.

**Conclusion:** fail-loud is correct **only when layered on the deterministic `instrument_token` path**. It is unsafe as the *primary* defense against `trading_symbol` misses.

### Alternatives considered

| Option | Behavior on unmapped | Verdict |
|---|---|---|
| **A. Fail-loud as `ORPHANED_BROKER_POSITION`** (MM7I §4.3) | refuse startup, but mislabels cause | OK **only** atop the `instrument_token` path; misleading if a fallback-format miss |
| **B. Fail-open / skip unmapped** | drop the position silently | **Rejected** — re-creates the exact silent-orphan hazard #6b exists to close |
| **C. Distinct alert class `UNRECONCILABLE_UNMAPPED_POSITION`** | refuse startup, but names "could not identify" vs "genuinely orphaned" | **Recommended** — same fail-loud safety, correct diagnostics, distinguishes a coverage/format bug from a real orphan |
| **D. Degrade-to-warn at PAPER only** | warn, not refuse, when mode = PAPER | Acceptable as a secondary (PAPER has no real book), but irrelevant to the LIVE rung R1 targets |

**Recommendation for #6b.2:** `instrument_token`-primary key + fail-loud, but emit option **C**'s distinct `UNRECONCILABLE_UNMAPPED_POSITION` (not a plain `ORPHANED_BROKER_POSITION`) so a coverage/format regression is diagnosable rather than disguised as a swarm of orphans.

---

## 4. Does R1 remain approved?

**Yes — approved, with a sharpened precondition set.** Net effect of this verification on MM7I:

| MM7I item | Before (MM7I) | After (this slice) |
|---|---|---|
| §7 #4 non-1:1 map | open risk | **CLEARED** — 0 collisions / 59,241 symbols |
| master-side projection completeness | assumed | **CONFIRMED** — 100% non-null, resolvable |
| §4.4 #2 `instrument_token` preservation | "follow-up, noted, not done" | **HARD prerequisite** — R1's only deterministic key |
| §7 #2 `trading_symbol` format drift | flagged hypothetically | **demonstrated** — master is spaced; compact form absent (0 rows) |
| §4.3 unmapped policy | fail-loud → `ORPHANED` | fail-loud **only atop `instrument_token`**; prefer distinct `UNRECONCILABLE_UNMAPPED` alert |

**Revised R1 gate for #6b.2 (must all hold before coding the wiring):**
1. **Confirm** the live net-positions payload carries `instrument_token` (§2.1 — the one unresolved fact; needs one real authenticated payload).
2. **Preserve + key on `instrument_token`** in `get_positions()` (`upstox_adapter.py:131-149`) — the broker-layer change, ahead of the composition-root wiring.
3. **Treat `trading_symbol` as fallback-only**, never the primary key.
4. **Emit a distinct unmapped alert class** (P3 option C) and keep fail-loud.

The G1 placement decision (MM7I §3/§4.2) is **unchanged and reinforced**: the `instrument_token` handling lives in `core/brokers/` (legal), never `core/execution/`.

---

## 5. Evidence that would force R2

R2 (full 4C.8 canonical↔canonical) becomes the correct call if any of:

1. **The live net-positions payload does NOT carry `instrument_token`.** Then R1's only deterministic key is gone and only the format-fragile `trading_symbol` remains — but note this *also* undercuts `from_broker_position` (which R2 consumes), so the true response is a **broker-layer key fix first**, then either route. Absent any reliable broker key, neither R1 nor R2 is safe; R2 is not a rescue from a missing `instrument_token`.
2. **A confirmed near-term Phase-4C resume** (4C.6→4C.8) before #6b is needed live — building-then-reverting R1 becomes wasted motion (MM7I §7).
3. **A decision to re-key `PositionTracker._positions` to `canonical_id`** — invalidates R1's "both sides → instrument_key" target (MM7I §7 #3; the ledger key is preserved today, `handler.py:284-287`).

**Conditions that would have forced R2 but are now CLEARED:** non-1:1 symbol map (§1.2) and incomplete master-side projection (§1.2). The remaining live risk is concentrated entirely in **fact #1** (does the payload carry `instrument_token`), which a single captured authenticated net-positions response resolves.

---

## 6. Stop condition / return summary

**Verification complete. Report written. No code, no test, no commit, no adapter/mapping/reconciliation change. 516 passing · 0 failing (unchanged).**

1. **Coverage verdict (P1):** via `instrument_token` — **100% deterministic, format-independent** (token == ledger key, `upstox_adapter.py:86`). Via `trading_symbol` fallback — **unverifiable offline, likely 0%**: master is spaced (`NIFTY 20350 CE 30 JUN 26`), the compact MM7G/MM7I form is absent (0 rows). Master-side projection is complete (100% non-null/resolvable) and **1:1** (0 collisions / 59,241 symbols).
2. **Instrument-token verdict (P2):** exists per the V2 schema and `from_broker_position`'s preferred path (`upstox.py:75`) but **unconfirmed by any fixture**; **discarded** at `upstox_adapter.py:131-134`; smallest legal preservation is a re-key on `instrument_token` inside `get_positions()` (`upstox_adapter.py:131-149`, broker layer — trips no G1 guard). **Upgraded to a HARD prerequisite.**
3. **R1 remains approved** — conditional on the four-item revised gate (§4): confirm payload `instrument_token`; preserve + key on it; `trading_symbol` fallback-only; distinct `UNRECONCILABLE_UNMAPPED` alert + fail-loud.
4. **Evidence that would force R2:** the live payload lacking `instrument_token` (§5 #1 — the one open fact), a near-term 4C resume (#2), or a ledger re-key to `canonical_id` (#3). The non-1:1 and projection-completeness R2-triggers are **cleared**.

**Single highest-value next action before #6b.2:** capture one authenticated `/portfolio/net-positions` response to confirm (a) `instrument_token` is present and (b) the `trading_symbol` format — this resolves the entire residual P1/P2 uncertainty.

*Filed under the G1 / MM7A–I review-first, characterize-then-verify-before-change discipline. Companion to `MM7I_NAMESPACE_ROUTE_DECISION.md` (§4.4 pre-checks, §7 R2-forcing evidence). Next slice: #6b.2 — implement R1 behind the §4 revised gate, beginning with the `instrument_token` broker-layer preservation + a captured-payload confirmation.*
