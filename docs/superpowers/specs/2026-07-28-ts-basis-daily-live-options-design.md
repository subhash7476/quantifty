# TS Basis Daily — Live Options Panel (design)

**Date:** 2026-07-28
**Goal:** Show the TS Basis Daily 10-name book as tradeable option contracts on
`/ts-basis-daily/`, with prices refreshing continuously while the tab is visible.

## Decisions (operator-approved)

| Question | Decision |
|---|---|
| Delivery mechanism | Fast polling, ~2s, one batched upstream call per poll |
| Fields per row | Live LTP + day change % |
| Polling when tab hidden | Paused (resume on visibility) |
| Strike / expiry | ATM with liquidity snap; nearest monthly ≥7 DTE (reuses existing rules) |

Rejected: SSE push (adds a background thread and new plumbing for no visible gain
at 2s), and a true WebSocket tick feed (no source in repo — the ingestor is a stale
`.pyc`; protobuf/WS ingest is a disproportionate build for this panel).

## Architecture

Layer flow follows the repo convention (DuckDB → core → Flask UI).

### 1. `core/analytics/options_selection.py` (new)

One function, `select_book_options(book, as_of)`, returning per name:
`ticker, direction, opt_type, expiry, strike, lot_size, instrument_key,
settle_ref, oi, forward`.

It owns the rules that today live only inside `scripts/ts_basis_daily_options.py`:
- **Expiry:** nearest monthly ≥ `min_dte` days out (default 7).
- **Strike:** nearest listed strike to the expiry forward (near-month future close),
  then a **liquidity snap** — if that strike's OI < `MIN_OI` (100), move to the
  nearest strike that carries real OI.
- **Instrument key:** resolved from `nse_fo_instruments.duckdb` at the latest
  snapshot, via the EQ `tradingsymbol` → `name` mapping (option rows are keyed by
  full company name, e.g. `WIPRO` → `WIPRO 175 CE 25 AUG 26` / `NSE_FO|153458`).

`scripts/ts_basis_daily_options.py` is refactored to import this. Reason: the CLI
and the page must not drift into two different definitions of "the trade".

### 2. `core/brokers/upstox_market_data.py` (extend)

Add `fetch_quotes_batch(keys) -> {key: {ltp, prev_close, net_change, change_pct,
volume, oi, feed_ts}}`. Existing `fetch_ltp`/`fetch_ltp_batch` are left untouched.

**Prev close must be derived as `last_price - net_change`.** It is NOT `ohlc.close`
— verified against the live payload: `ohlc.close` tracks the current session and
equalled `last_price` (8.06/8.06), so using it yields a permanent 0.00% change.

### 3. `flask_app/blueprints/ts_basis_daily.py` (extend)

Two endpoints, deliberately split so the expensive resolution does not re-run every
2 seconds:

- `GET /api/options` — DuckDB only, no network. Resolves the current formation's
  book into contracts. Called once on load and on formation change.
- `GET /api/options/live` — one batched Upstox call for all 10 keys. Polled ~2s.
  Returns quotes plus a market-state verdict.

  **The client does not supply instrument keys.** The server resolves the book once
  per formation date, caches that mapping in module state, and the live endpoint
  quotes only from that cache (re-resolving if the formation changed). This keeps
  the outbound call driven by the strategy's own book rather than by request input,
  and keeps the 2s path free of DuckDB work.

### 4. `flask_app/templates/ts_basis_daily/index.html` (extend)

An options table beneath the existing signals: ticker · dir · contract · strike ·
LTP · change % · lot · premium/lot. Green/red flash on tick. Status pill.

**Dual-date header (required).** The panel always shows both dates side by side:

> **Book: 27 Jul close** · **Prices: live, 28 Jul 13:24**

The name list is computed from the previous session's close; the prices are from the
current session. That is inherent to a daily strategy — today's list cannot exist
until today's close. Showing one date invites the reader to assume the names were
picked from today's data. Both dates are always rendered, never collapsed to one.

JS polls `/api/options/live` every 2s via `setInterval`, guarded by
`document.visibilityState` — poll pauses on `visibilitychange` to hidden and
resumes (with an immediate fetch) on return.

## Market-state rule (the subtle part)

The pill is **LIVE / CLOSED / STALE**, and it is decided by the **feed timestamp**,
never by whether the price moved.

Empirically, a real live feed returned an unchanged LTP and unchanged volume across
6 seconds while its `timestamp` advanced (12:50:13 → 12:50:20 IST). A thinly-traded
strike not printing for a few seconds is normal. Inferring staleness from an
unchanged price would mislabel a healthy feed as stale.

- **LIVE** — newest `feed_ts` is within ~60s of now.
- **CLOSED** — feed_ts older than that during non-market hours.
- **STALE** — request failed, token missing/expired, or feed_ts unexpectedly old.
  Last good prices are retained and visibly marked; errors are never rendered as
  live prices.

## Error handling

Per repo convention, no speculative retry/fallback layers. Specifically:
- Upstox non-200 or network error → endpoint returns the error reason; UI keeps last
  good values and flips to STALE with that reason shown.
- Missing/expired token → STALE with an explicit "re-authenticate" message, not an
  empty table.
- A contract that resolves to no instrument key → row renders with "—" rather than
  being dropped, so a silently missing name is visible.

## Testing

- Unit: strike selection (exact-hit, liquidity snap, penny-strike), expiry choice at
  the ≥7 DTE boundary, and `prev_close = last_price - net_change` (the `ohlc.close`
  trap, asserted explicitly).
- Integration: `/api/options` against the real facts + instrument DBs; `/api/options/live`
  with a stubbed quote payload; market-state verdict from synthetic feed timestamps
  (fresh → LIVE, old → CLOSED/STALE, unchanged-price-but-fresh-ts → LIVE).
- Manual: page open during market hours; confirm ticking, confirm polling stops when
  the tab is hidden.

## Out of scope

Order placement, greeks/IV, bid-ask depth, historical tick storage, and any change to
the signal construct itself. The panel is a live view of an existing book.

## Standing caveat (carried into the UI)

The strategy was validated on the linear long/short **futures** basis, not on options.
An ATM option is ~0.5 delta and adds theta and spread the backtest never modeled. The
page states this inline so a live-looking table is not mistaken for a validated
options strategy.
