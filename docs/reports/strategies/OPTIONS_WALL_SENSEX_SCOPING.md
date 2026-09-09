# Options Wall — Adding Sensex (BSE) — Scoping

**Date:** 2026-09-03
**Question:** Beyond Nifty and BankNifty, what is required to add **Sensex** to the Options Wall?
**Method:** Static trace of the options-wall stack (provider → poller → engine → analytics → UI) and the instrument/candle substrate. No code changed.

## Status — 2026-09-03

- **D1 (BSE in instrument master): DONE + verified.** `BSE_FO`/`BSE_INDEX` added to `ACCEPTED_SEGMENTS`; master re-fetched (61,692 rows). `BSE_INDEX|SENSEX` resolves, live option chain returns 260 rows @ spot 76,615, weekly expiry Thursday.
- **Code wiring 1–6: DONE + verified.** Sensex is a tab; `trades_view('SENSEX')` and the structural build both work (regime "Positive GEX (Stable)", pin 75,200). Farm screen correctly returns 0 signals because RV is `None`.
- **D2 (Sensex 1m candles for realized vol): DONE.** Backfilled 8 sessions (2026-08-24 → 09-02, 3,000 1m bars) via `fetch_intermarket_data.py --instrument "BSE_INDEX|SENSEX" --include-1m`; `session_realized_vol_pct('BSE_INDEX|SENSEX')` returns **7.37%**. The farm screen is unblocked. Implementation note below.
- Requires a **Flask + poller restart** to load (both `UNDERLYINGS` dicts and the template changed).

### D2 as implemented (differs from the original plan below)
`BSE_INDEX|SENSEX` maps to exchange **`bse`** (`get_exchange_from_key`), so the fetcher writes to `data/market_data/**bse**/candles/1m/{date}.duckdb` — not `nse/`. Rather than co-locate BSE data in the NSE dir, `realized_vol` was made exchange-aware (`_candles_1m_dir(symbol)` resolves the dir from the symbol's exchange; NSE behavior unchanged). `BSE_INDEX|SENSEX` was added to `ONE_MIN_INDICES` in `scripts/download_all_data.py` so the nightly pipeline keeps it current. **Still TODO for durability:** confirm the BSE holiday calendar in the nightly job, and today's session isn't backfilled by the historical endpoint (intraday-only) — RV uses the 5 most recent SENSEX-bearing files, so it stays valid, but a same-day top-up would keep it freshest.

## TL;DR

Sensex is a **BSE** index (`BSE_INDEX|SENSEX`); the entire wall was NSE-bound. The Upstox APIs it uses (option chain, quotes, instrument master, historical candles) are **exchange-generic** — no API blocker. D1 + the 6 wiring edits are done; the heaviest remaining item is ingesting Sensex 1-minute index candles, without which the premium-farm screen stays dark (realized vol is `None`), though the structural wall (GEX / pin / OI / max-pain) renders from the chain immediately.

## Data blockers (the real work)

### D1 — Instrument master excludes BSE
`scripts/fetch_instrument_master.py` downloads Upstox's **complete** master (`assets.upstox.com/.../complete.json.gz`, which includes BSE_FO + BSE_INDEX) but filters:
```
ACCEPTED_SEGMENTS = ("NSE_FO", "MCX_FO", "NSE_EQ", "NSE_INDEX")   # line 52
_DERIVATIVE_SEGMENTS = ("NSE_FO", "MCX_FO")                        # line 54 (contract-shape guard)
```
Confirmed: `data/instruments/nse_fo_instruments.duckdb` holds only NIFTY / BANKNIFTY / FINNIFTY / MIDCPNIFTY; exchanges present are `NSE_FO, MCX_FO, NSE_INDEX, NSE_EQ` — **no BSE**.
- **Fix:** add `"BSE_FO"`, `"BSE_INDEX"` to `ACCEPTED_SEGMENTS` (and `"BSE_FO"` to `_DERIVATIVE_SEGMENTS` so the CE/PE/FUT shape guard covers it), then re-run the fetch. Source data already contains it — no new feed.
- This is what makes `get_weekly_expiry()` resolve real Sensex expiries (it reads `WHERE name = 'SENSEX'` from this master; `core/data/options_provider.py:520-532`).
- Cosmetic: the file is named `nse_fo_instruments.duckdb` but would now hold BSE too. Rename optional, not blocking.

### D2 — No Sensex 1-minute candles for realized vol
`core/analytics/realized_vol.py` reads `data/market_data/nse/candles/1m/*.duckdb` filtered by `symbol`. There are **no `BSE_INDEX|SENSEX` candles** anywhere on disk (the `bse_*` files found are equity corporate-actions, not index candles).
- Consequence: `session_realized_vol_pct("BSE_INDEX|SENSEX")` → `None` → `_farm_screen` returns `[]` (`chain_scanner.py:100`), so **no farm signals and no paper trades** for Sensex until candles exist. GEX/pin/OI still compute (they don't need RV).
- **Fix:** ingest Sensex 1m index candles into the 1m store (Upstox historical/intraday candle API for `BSE_INDEX|SENSEX`; mirror `scripts/ingest_reference_1m.py` / `fetch_intermarket_data.py`). Like all index symbols it carries `volume=0` — same handling as NSE indices; never apply vol/VWAP filters.

### D2 — job spec (standalone task)
1. Add `BSE_INDEX|SENSEX` to the intraday 1m ingest so it writes into `data/market_data/nse/candles/1m/{date}.duckdb` under `symbol='BSE_INDEX|SENSEX', timeframe='1m'` (the exact table/columns `realized_vol._load_sessions` reads). The store name is `nse/…` but symbol-keyed, so a BSE symbol coexists fine.
2. **Only ≥5 recent sessions are needed** — `realized_vol` takes the 5 newest files. No deep history required for the farm screen; a same-day + trailing-4-session backfill suffices.
3. Wire it into the nightly EOD/refresh chain (wherever Nifty/BankNifty 1m is refreshed) so it stays current.
4. **BSE holiday calendar** — confirm the ingest's trading-day calendar covers BSE (mostly shared with NSE, occasional divergence).
5. Verify: `session_realized_vol_pct('BSE_INDEX|SENSEX')` returns a float; then the poller's next cycle emits a Sensex `premium_farm` row when GEX/pin/IV-RV gates hold.

Effort: the ingest + a trailing backfill is the bulk of the remaining work; no vendor purchase, Upstox historical candles cover BSE indices.

## Code wiring (small, mechanical)

| # | File | Change |
|---|------|--------|
| 1 | `core/options_wall/engine.py` (`UNDERLYINGS`, ~line 27) | add `"SENSEX": "BSE_INDEX|SENSEX"` |
| 2 | `core/options_wall/poller.py` (`UNDERLYINGS`, ~line 40) | add `"SENSEX": "BSE_INDEX|SENSEX"` (poller then accumulates a third chain per cycle) |
| 3 | `core/data/options_provider.py` `EXPIRY_MAP` (line 90) | add `"SENSEX": "BSE_INDEX|SENSEX"` |
| 4 | `core/data/options_provider.py` `EXPIRY_WEEKDAY` (line 96) | add `"BSE_INDEX|SENSEX": <weekday>` (fallback only — real expiry comes from the master) |
| 5 | `core/data/options_provider.py` `get_weekly_expiry` `index_map` (line 514) | add `"BSE_INDEX|SENSEX": "SENSEX"` |
| 6 | `flask_app/templates/options_wall/index.html` | add a `tab-SENSEX` button (line 38-39); add `'SENSEX'` to the `['NIFTY','BANKNIFTY']` list in `paintTabs` (line 258); replace the binary label at line 313 (`currentIndex === 'NIFTY' ? 'Nifty 50' : 'Bank Nifty'`) with a 3-way map |

The blueprint (`_sym` → `UNDERLYINGS.get`) and `/api/farm|regime|trades` need no change once `UNDERLYINGS` carries SENSEX.

## What already works (no change)

- **Option-chain fetch** — `OptionsProvider._fetch_from_upstox` passes `instrument_key` straight to `GET /v2/option/chain` (`options_provider.py:251`); `BSE_INDEX|SENSEX` is a valid key. Generic.
- **Quotes** — `UpstoxMarketData.fetch_quotes_batch` is keyed on instrument_key; exchange-agnostic.
- **Structural analytics** — `OptionsAnalytics` (GEX, pin, OI walls, max-pain) computes off the chain rows; no NSE assumption.
- **Iron-fly build / paper executor** — `build_iron_fly` snaps to the nearest listed strike and reads live per-leg quotes; Sensex's ~100-wide strikes and ~80k level adapt automatically. `wing_pct` is fractional. Lot size comes from the chain row.
- **Trades panel + live marks** (just built) — index-agnostic; works for SENSEX the moment `UNDERLYINGS` includes it.

## Nuances to check during implementation

- **Expiry day** — BSE Sensex weekly expiry has shifted with SEBI's calendar changes; the code is **master-driven** (fallback weekday only), so correct once D1 lands. Set the fallback to the current Sensex weekday but don't rely on it.
- **Market hours** — verify `core/database/utils/market_hours.MarketHours.is_derivatives_open()` isn't NSE-calendar-specific (BSE trades the same 09:15–15:30, but holiday lists can differ).
- **RV annualization** — assumes a 375-min session; BSE session length matches, so `annualized_rv_pct` is fine.
- **Poller load** — a third underlying adds one more chain fetch + quotes batch per 5s cycle; watch Upstox rate limits.

## Recommended order

1. **D1** (master segments + re-fetch) — unblocks expiry resolution and the option chain. ~30 min.
2. **Code wiring 1–6** — Sensex appears as a tab; **structural wall + trades render live** even before D2.
3. **D2** (Sensex 1m candle ingest + a nightly refresh) — turns on realized vol → premium-farm screen + paper trades for Sensex.

Effort: D1 + wiring is a half-day; D2 (candle ingest job + backfill) is the larger piece and is what gates the farm screen. No API purchase or new vendor needed.
