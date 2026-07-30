# TS Basis Daily — Live ATM Anchor (design)

**Date:** 2026-07-30
**Goal:** Strike the ATM option on a **live** underlying forward instead of a stale
end-of-day (EOD) near-month futures close, so the selected strike is centred on the
current market rather than the last bhavcopy. Everything else about selection is
unchanged.

## Problem

`core/analytics/options_selection.py` picks the ATM strike as the listed strike
nearest to `forward`, where `forward` is the **near-month futures EOD close**
(`futures_bhavcopy`, `MAX(trade_date)`). That close can be days old (weekend /
holiday / ingest lag). If spot has moved since, the chosen strike is no longer ATM —
the selection is anchored to stale data. This is the defect that motivated the
change; it was confirmed to be by-design in the 2026-07-28 live-options panel work,
which reserved the Upstox API for *display* only, never for selection.

## Scope (operator-approved)

| Decision | Choice |
|---|---|
| Live vs EOD | **Augment + fallback** — live forward when market open & token valid; automatic EOD fallback otherwise. One code path. |
| Which live checks | **Live ATM anchor only.** Liquidity snap stays on EOD open interest; premium reference stays EOD. No bid/ask, no live OI, no live volume screen. |
| Re-anchor cadence | **Once per load / formation change.** The strike is a deliberate snapshot taken when the book is resolved; it does **not** re-centre every 2s. A page reload takes a fresh live anchor. |
| Surface | Shared module → both the CLI report and the Flask panel benefit (no drift). |

Out of scope: live OI/volume/spread screening, intraday re-anchoring, order
placement, greeks, any change to the signal construct. The strategy remains validated
on the futures basis, not options — that standing caveat is unchanged.

## Forward resolution (the only behavioural change)

`forward` is resolved per name with a three-step fallback:

```
1. live near-month FUTURE LTP   (Upstox market-quote, once at resolve time)
2. EOD future close             (futures_bhavcopy — today's behaviour)
3. synthetic PCP forward         (existing select_option fallback, when no future row)
```

Each returned contract row gains **`anchor_source`** in `{"live", "eod_future",
"synthetic"}` so both surfaces can show whether the ATM was struck live or stale.

### How the live future LTP is fetched
- Reuse `UpstoxMarketData.fetch_ltp_batch` — **no new endpoint, no depth parsing.**
- Resolve each name's near-month future instrument key from
  `nse_fo_instruments.duckdb` at the latest snapshot, via the **same EQ
  `tradingsymbol` -> `name` mapping the module already uses for options**, then:
  `instrument_type='FUT' AND name=? AND expiry=? AND instrument_key LIKE 'NSE_FO%'`.
  (Verified: EQ `WIPRO` -> name `WIPRO LTD`; the FUT row for that name+expiry is
  `NSE_FO|61322`. Option `name` is also `WIPRO LTD`, so one mapping serves both.)
- The future expiry equals the option expiry for monthly contracts (both settle the
  last Tuesday, e.g. `28 JUL 26`), so the anchor future is the same expiry already
  chosen for the option.
- One **batched** LTP call for all ~10 futures per resolve.

### Fallback semantics (no silently-swallowed failure)
`fetch_ltp_batch` already returns `{}` on any failure (missing token, non-200,
network error) and omits keys with no price — it never raises. So the fallback is a
plain dictionary miss: a name absent from the live batch (token down, market closed,
key unresolved) falls through to its EOD close, and `anchor_source` records which
path was taken. No new `try/except` is introduced in the selection module.

## Interface

`select_book_options(book, min_dte=DEFAULT_MIN_DTE, today=None, market_data=None)`:

- `market_data` is an object exposing `fetch_ltp_batch(keys) -> {key: ltp}`.
  - **Default (`None`) -> construct `UpstoxMarketData()` and attempt live** (augment).
  - Tests inject a stub (deterministic prices) or a sentinel that forces EOD
    (`market_data=_EOD_ONLY`) — no network in tests.
- Live-forward resolution is a new module-private helper
  `_resolve_live_forwards(inst_con, book, expiries, market_data) -> {ticker: ltp}`,
  called once before the per-name loop. It does the FUT-key lookup + one batch call.
- `select_option(...)` is unchanged — it already takes `forward` as a parameter, so
  the live value flows in through the existing seam. The EOD-close lookup in
  `select_book_options` stays as the step-2 fallback.

### CLI (`scripts/ts_basis_daily_options.py`)
- No signature change to the call; it already calls `select_book_options(book,
  min_dte=…)`. During market hours with a valid token it now prints live-anchored
  strikes; after hours / no token it prints exactly today's EOD output.
- Add an `anchor_source` column (or a per-row note) to the printed table and to the
  footer legend, so the operator sees whether `Fwd` was live or EOD.

### Flask panel (`flask_app/blueprints/ts_basis_daily.py`)
- `_resolve_contracts()` already caches contracts per formation. It now resolves with
  the live anchor **at cache-fill time** — i.e. once per formation/load, matching the
  once-per-load decision. The 2s `/api/options/live` path is untouched (still just
  quotes the cached keys).
- `/api/options` response gains `anchor_source` per contract and an overall
  `anchor_asof` note; the template's existing dual-date header gains a small marker
  (e.g. "ATM: live 30 Jul 13:24" vs "ATM: EOD 29 Jul") so a stale anchor is visible.
- **Cache note:** because the anchor is captured at cache fill, the panel keeps the
  same strike for the life of the cached formation — consistent with once-per-load.
  A formation change (next session's book) or process restart re-resolves live.

## Files touched

| File | Change |
|---|---|
| `core/analytics/options_selection.py` | Add `market_data` param, `_resolve_live_forwards`, three-step forward fallback, `anchor_source` field. |
| `scripts/ts_basis_daily_options.py` | Print `anchor_source`; update footer legend. |
| `flask_app/blueprints/ts_basis_daily.py` | Pass live resolution through `_resolve_contracts`; expose `anchor_source` in `/api/options`. |
| `flask_app/templates/ts_basis_daily/index.html` | Show anchor freshness marker. |
| `tests/analytics/test_options_selection.py` (new/extend) | See Testing. |

`core/brokers/upstox_market_data.py` is **unchanged** — `fetch_ltp_batch` already
provides exactly what is needed.

## Testing

- **Unit — forward fallback (mocked market_data, no network):**
  - live LTP present -> `forward == live LTP`, `anchor_source == "live"`, and the ATM
    strike is the one nearest that live value (assert it differs from the EOD-anchored
    strike when the live value crosses a strike boundary).
  - live batch returns `{}` (token down) -> `forward == EOD future close`,
    `anchor_source == "eod_future"` — output identical to pre-change behaviour.
  - no future row at all -> `anchor_source == "synthetic"` via the existing PCP path.
- **Unit — key resolution:** the FUT instrument key is resolved by (name, expiry) and
  handed to `fetch_ltp_batch`; a name whose FUT key is unresolved is simply absent
  from the live map and falls back (asserted).
- **Unit — snap unchanged:** the `MIN_OI` liquidity snap still operates on EOD OI and
  is unaffected by the anchor source (exact-hit and snapped cases both retained).
- **Integration:** `/api/options` with a stubbed `market_data` returns
  `anchor_source` per contract and a stable strike across two calls in the same
  formation (once-per-load cache holds).
- **Regression:** with `market_data=_EOD_ONLY`, `select_book_options` output equals
  the current EOD selection byte-for-byte (guards the fallback path against drift).

## Risks

- **Live future thinly traded:** its LTP can itself be a stale last-trade off-hours.
  Mitigated by fallback labelling — off-hours the LTP ≈ prev close ≈ the EOD value we
  would have used anyway, and `anchor_source` still reports "live" honestly (it *was*
  the live quote). Acceptable; documented.
- **Cache staleness within a session:** once-per-load means a strike chosen at 09:20
  is not re-centred if spot drifts 3% by 14:00. This is the explicit operator
  decision (avoids strike churn); a reload re-anchors.
