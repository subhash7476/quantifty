# TS Basis Daily — Live ATM Anchor + Tradeability Screen (design)

**Date:** 2026-07-30
**Goal:** Select each option on **live** market data instead of stale end-of-day
(EOD) bhavcopy. Two changes: (1) strike the ATM on a live underlying forward, and
(2) screen the chosen strike for real tradeability — live bid/ask spread, open
interest, and volume — dropping-to-flag any name whose best strike is untradeable.
The signal construct is unchanged; this is purely how a signal maps to a contract.

## Problem

`core/analytics/options_selection.py` selects entirely from EOD bhavcopy:
- **ATM anchor** = near-month futures **EOD close** (`futures_bhavcopy`,
  `MAX(trade_date)`) — days old on weekends/holidays/ingest lag; if spot moved, the
  "ATM" strike is no longer ATM.
- **Liquidity** = EOD `open_int > 100` only — a strike liquid yesterday can be dead
  today, and **spread is never checked at all**. Since the strategy was validated on
  the linear **futures** basis, the option spread is a pure, unmodeled cost; a wide
  spread can consume the entire directional edge.

The Upstox API is currently used only for *display* (2s LTP poll on the panel), never
for selection. This spec routes selection through live data with a clean EOD fallback.

## Scope (operator-approved)

| Decision | Choice |
|---|---|
| Live vs EOD | **Augment + fallback** — live selection when market open & token valid; automatic EOD fallback otherwise. One code path. |
| Live checks | **ATM anchor + bid/ask spread + live OI + live volume.** No greeks/IV (a different question — position sizing and options-vehicle risk, not strike choice). |
| Re-anchor cadence | **Once per load / formation change.** A deliberate snapshot at book-resolve time; not re-centred every 2s. Reload re-anchors. |
| Fail behavior | **Flag visible, do not drop.** A name with no tradeable strike stays in the output marked `no_tradeable_strike` with the reason. |
| Surface | Shared module -> CLI report and Flask panel both benefit (no drift). |

Out of scope: greeks/IV, intraday re-anchoring, order placement, any change to the
signal construct. The strategy remains validated on the futures basis, not options —
that standing caveat is unchanged and the surfaces keep stating it.

## Proposed thresholds (operator-confirmed defaults)

| Parameter | Constant | Default | Role |
|---|---|---|---|
| Max spread | `MAX_SPREAD_PCT` | 0.05 (5% of mid) | Primary tradeability gate |
| Candidate band | `STRIKE_BAND` | ±3 listed strikes | How far the snap may wander from ATM |
| Min live OI | `MIN_OI` (reused) | 100 | Resting liquidity |
| Min live volume | `MIN_VOLUME` | 1 lot traded today | Actually printing today |

All four are module constants, tunable in one place.

## Selection flow (per name, once per load)

```
1. Expiry          nearest monthly >= min_dte  (EOD list — expiries don't change intraday)
2. Live forward    live near-month FUTURE LTP
                     -> fallback: EOD future close
                     -> fallback: synthetic PCP forward
3. Candidate band  listed strikes within STRIKE_BAND of the forward, for the name's
                   opt_type (LONG->CE, SHORT->PE)
4. One batched live quote call for ALL candidates across ALL names (~<=70 keys):
                   best_bid, best_ask, oi, volume, feed_ts
5. Screen each candidate (live):
     spread = (ask - bid)/mid <= MAX_SPREAD_PCT
     oi     >= MIN_OI
     volume >= MIN_VOLUME
6. Choose the passing candidate NEAREST the forward (ATM intent);
   tie-break on tightest spread.
7. None pass -> keep the row, flag screen="no_tradeable_strike" + reason string.
```

### Live forward — how
- Reuse `UpstoxMarketData.fetch_ltp_batch` for the future LTP (no new endpoint).
- Resolve each name's near-month future key from `nse_fo_instruments.duckdb` (latest
  snapshot) via the **same EQ `tradingsymbol` -> `name` mapping the module already
  uses for options**: `instrument_type='FUT' AND name=? AND expiry=? AND
  instrument_key LIKE 'NSE_FO%'`. (Verified: EQ `WIPRO` -> name `WIPRO LTD` -> FUT
  `NSE_FO|61322` exp `2026-07-28`; option `name` is also `WIPRO LTD`, one mapping
  serves both. Monthly future and option share the expiry.)
- One batched LTP call for all ~10 futures.

### Screen quotes — how
- Candidate option instrument keys are resolved from the instrument master the same
  way the final contract key is resolved today (name + opt_type + strike + expiry).
- **Extend the adapter** to expose top-of-book: `best_bid = depth.buy[0].price`,
  `best_ask = depth.sell[0].price`, alongside the `oi`/`volume` it already returns.
- **Build-time check (not an assumption):** confirm the `depth` object is present in
  the live `market-quote/quotes` payload before relying on it. The 2026-07-28 panel
  work already calls this endpoint, so this is verifiable against a real response;
  if `depth` is absent, the spread gate degrades to OI+volume only and the spec is
  revised — do not silently treat a missing spread as a pass.

### Fallback semantics (no silently-swallowed failure)
`fetch_ltp_batch` / the batch quote already return `{}` on any failure (missing
token, non-200, network error) and never raise. Two fallback cases:
- **No live forward** for a name -> use its EOD future close (or synthetic PCP);
  `anchor_source` records which.
- **No live quotes at all** (token down / market closed) -> **screen is *skipped*,
  not failed**: fall back to today's EOD OI snap, mark `screen="skipped"`. Names are
  **never** dropped/flagged for lack of a feed — only for a live wide/illiquid
  verdict. No new `try/except` in the selection module; fallback is a dict miss.

## Interface

`select_book_options(book, min_dte=DEFAULT_MIN_DTE, today=None, market_data=None)`:

- `market_data` exposes `fetch_ltp_batch(keys)` and the depth-extended batch quote.
  - **Default (`None`) -> construct `UpstoxMarketData()` and attempt live** (augment).
  - Tests inject a stub (deterministic quotes) or a sentinel forcing EOD
    (`market_data=_EOD_ONLY`) — no network in tests.
- New module-private helpers:
  - `_resolve_live_forwards(inst_con, book, expiries, market_data) -> {ticker: ltp}`
  - `_screen_candidates(inst_con, name, opt_type, expiry, forward, strikes, quotes)
    -> chosen_row | flagged_row` — applies the band + three gates + nearest-to-forward
    pick.
- `select_option(...)` stays the seam for the EOD path; the live path adds the screen
  around the same strike list.

Each returned contract row gains:
`anchor_source` in {live, eod_future, synthetic},
`screen` in {pass, snapped, no_tradeable_strike, skipped},
plus `spread_pct`, `live_oi`, `live_volume`, `best_bid`, `best_ask`, `screen_reason`.

### CLI (`scripts/ts_basis_daily_options.py`)
- Same call; gains `Src` (anchor) and `Screen` columns + a footer legend. Off-hours /
  no token prints today's EOD selection with `screen="skipped"`.

### Flask panel (`flask_app/blueprints/ts_basis_daily.py`)
- `_resolve_contracts()` resolves live at cache-fill (once per formation/load). The 2s
  `/api/options/live` path is untouched.
- `/api/options` exposes the new fields; a `no_tradeable_strike` row renders greyed
  with its reason, and the dual-date header gains an anchor/screen freshness marker.

## Files touched

| File | Change |
|---|---|
| `core/analytics/options_selection.py` | `market_data` param, `_resolve_live_forwards`, `_screen_candidates`, thresholds, new row fields, three-step forward fallback. |
| `core/brokers/upstox_market_data.py` | Extend batch quote to return `best_bid`/`best_ask` from `depth`; build-time `depth`-present check. |
| `scripts/ts_basis_daily_options.py` | Print anchor + screen columns; footer legend. |
| `flask_app/blueprints/ts_basis_daily.py` | Live resolution through `_resolve_contracts`; expose new fields in `/api/options`. |
| `flask_app/templates/ts_basis_daily/index.html` | Anchor/screen freshness marker; grey out flagged rows. |
| `tests/analytics/test_options_selection.py` (new/extend) | See Testing. |

## Testing

- **Forward fallback (mocked market_data, no network):** live LTP -> `anchor_source
  == "live"` and ATM strike centres on it (differs from EOD anchor when the live value
  crosses a strike); empty live batch -> `eod_future`, output identical to today; no
  future row -> `synthetic`.
- **Screen gates (stub quotes):**
  - all candidates tight -> pick nearest forward, `screen == "pass"`.
  - nearest-to-forward strike has a wide spread but a neighbour in-band is tight ->
    `screen == "snapped"`, chosen strike is the tight neighbour.
  - every candidate wide/illiquid -> `screen == "no_tradeable_strike"`, row retained
    with a reason string; strike may be null.
  - spread exactly at `MAX_SPREAD_PCT` -> boundary is a pass (assert the `<=`).
  - OI below / volume below thresholds -> excluded even if spread is tight.
- **Skip vs fail:** no live quotes (token down) -> `screen == "skipped"`, EOD OI snap
  used, **no name dropped/flagged** for the missing feed.
- **Depth parse:** adapter maps `depth.buy[0].price`/`depth.sell[0].price` to
  `best_bid`/`best_ask`; a payload missing `depth` yields null bid/ask (and the
  screen degrades, per the build-time check) rather than a crash.
- **Integration:** `/api/options` with a stubbed `market_data` returns the new fields
  and a stable strike across two calls in one formation (once-per-load cache holds).
- **Regression:** `market_data=_EOD_ONLY` -> `select_book_options` output equals the
  current EOD selection byte-for-byte (guards the fallback against drift).

## Risks

- **Thin future off-hours:** its LTP may be a stale last-trade; off-hours it ≈ prev
  close ≈ the EOD value anyway, and `anchor_source` reports "live" honestly. Fine.
- **Early-session volume gate:** `MIN_VOLUME=1 lot` may exclude names at the open
  before they print. Tunable in one place; can be made advisory if too aggressive.
- **Screen churn is bounded:** the screen runs once per load (not per 2s tick), so a
  name's tradeability verdict is a snapshot. A reload re-screens.
- **Cache staleness within a session:** once-per-load means neither anchor nor screen
  re-centres if spot drifts intraday — the explicit operator decision (avoids strike
  churn). Reload re-resolves.
