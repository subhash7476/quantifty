# Data-Store Map — Historical Market-State Reconstruction

> Prepared for pattern / market-state similarity research. No strategy is designed here. All ranges are measured, not inferred.

**Generated:** 2026-09-01 from live datastore (`data/`). Commit-agnostic; re-run `inventory_scan*.py` to reproduce.

---

## Executive Summary

### A. What we definitely have
- **EOD equity panel:** 7.1 M rows (`data/market_data/equity_bhavcopy.duckdb:equity_bhavcopy` 2010-01-04→2026-09-01, 4 328 symbols) with OHLC + `prev_close`, `volume`, `turnover`, `deliv_qty`/`deliv_pct` (65 % coverage, start 2010), `adjustment_factors`/`equity_bhavcopy_adjusted`, `trading_calendar` (4 138 sessions), PIT `symbol_entity_intervals` / `symbol_isin`.
- **EOD index daily:** 4 127 per-date files `data/market_data/nse/candles/1d/{YYYY-MM-DD}.duckdb` (2010-01-04→2026-09-01). Each file `candles` (1–165 rows) with `open/high/low/close/volume/is_synthetic`. Early years sparse.
- **EOD derivatives (settlement):** `futures_bhavcopy` 1.49 M rows 2016-02-11→2026-09-01 (380 underlyings), `option_bhavcopy` 5.49 M rows 2016-02-11→2026-07-17, `stock_options_bhavcopy` 99.2 M rows 2016-02-11→2026-09-01 (366 underlyings).
- **Live 1m collector:** `data/live_buffer/candles_today.duckdb` (≈76 k rows today) + `ticks_today.duckdb` (≈42 k rows today) for Nifty/BankNifty/VIX.

### B. What we have historically
- **Daily close/breadth** 2010-present (Nifty only), 2016-present multi-index+futures/options.
- **1m bars** 2012-01-02→2026-09-01 (3 604 files) but **2 symbols only until 2024-10-17**; 195-231 symbols from 2024-10-17 onward. Vendor 1m 101 symbols 2015-02-02→2025-08-06 (separate family).
- **Futures/options EOD** 2016-present.
- **Universe/PIT** from 2012-01-31 (`universe_membership` 175 rebalances) and 2010 entity intervals.

### C. What exists only recently / live
- **Tick trades** (`ticks_today.duckdb`) only today (09:15–16:00), 3 indices only.
- **1m Nifty200 breadth** only from 2024-10-17 (earlier is Nifty/Bank only).
- **Live order-book / depth / MBO:** *none* historically or live (ticks store only `price/volume/bid/ask`).
- **Sector breadth, advanced breadth (A/D, NH/NL), FX/commodities/global indices:** none.

### D. Longest reliable historical period
**2016-02-11 → 2026-09-01** for a *daily* market state: Nifty family + ~3 k equities (daily OHLCV + delivery), index futures/options EOD. Earlier (2010–2016) is Nifty-only (or single-index) daily.

### E. Best intraday historical period
**2024-10-17 → 2026-09-01** (≈ 345 sessions) with 195–231 symbols 1m OHLCV; indices always 9:15–15:30 with `is_synthetic` flag post-CAS. Prior 2012–2024 is **intraday index-only** (Nifty/Bank, 2 symbols, 750 bars/day).

### F. Whether tick/microstructure history exists
**No historical tick.** Live tick exists only for today, 3 indices. No backfill, no depth, no order events. `ticks_today.duckdb` is purged daily.

### G. Major data limitations
- 1m vendor 101 symbols is a *different schema* (`vendor_1m.ts/open...` vs `candles`) and terminates 2025-08-06.
- 1m early sparsity (2 symbols) prevents breadth analogues before 2024-10-17.
- CAS synthetic bars 15:15–15:27 for F&O stocks + indices from 2026-08-03 (92-95 % of symbols, 1 auction bar at 15:28/29). Must filter `is_synthetic=FALSE`.
- Options `option_bhavcopy` lags to 2026-07-17 (45 d behind stock_options).
- Futures `stock_futures_continuous` only 2022-08-08→2025-07-17, not current.
- 2018 gap: 223 1m files vs 246–250 expected (holiday-aware) — certification shows 46 regular holes.

### H. Major survivorship / corporate-action concerns
- Survivorship **can be avoided** using `equity_bhavcopy` (contains every listed symbol per day) + `symbol_entity_intervals` (time-aware entity) + `universe_membership` PIT rebalances. But **current** `nifty200_current.csv` is snapshot only (200 rows); historical membership is in `universe_membership` (175 dates) and `pit_membership` (ISD, 900+ sessions). Not all research code uses PIT — many scripts read `nifty200_current.csv` (survivorship bias if time-travelled).
- CA: 11 965 events (BSE scrape), 1 207 `adjustment_factors`, with 16 `ca_evidence_exceptions` + 19 `ca_parse_rejects`. Adjusted view `equity_bhavcopy_adjusted` exists (7 132 767 rows) but not all factor edge cases dispositioned.

### I. Important uncertainty requiring verification
- 1m bars pre-2024 are *exchange-aggregated* or vendor-reconstructed? Cross-checked vs vendor in ISD certification (C5 alignment median ~0.03 bp, max 40 bp). Still UNKNOWN for 2012-2015 provenance.
- Vendor 1m `volume` for indices is synthetic (0 or fabricated) — never use for breadth.
- Tick `bid/ask` fields in `ticks` schema exist but are NULL for all observed today rows.

---

## 1. Complete Datastore Inventory

> Each entry: **path → format → universe → exchange → asset class → frequency → range → rows → columns → raw/derived → adjusted → partitioning → gaps → quality → infra use → prod/live/hist**

| # | Dataset / Table | Path / Table | Format | Universe | Exchange | Asset | Freq | Earliest | Latest | Rows | Columns | Raw/Derived | Adjusted | Part. | Known gaps | Quality notes | Used by infra | Live/Hist |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|1|Equity EOD|`data/market_data/equity_bhavcopy.duckdb:equity_bhavcopy`|DuckDB|4 328 NSE symbols (varies/yr)|NSE|Equity|Daily|2010-01-04|2026-09-01|7 135 363|trade_date PK, symbol, series, open/high/low/close, prev_close, volume, turnover, deliv_qty, deliv_pct|Raw (NSE bhavcopy)|**No** (raw); adjusted sibling exists|Single DB, trade_date PK|None systematic; deliv null pre-2010?  4281 `.404` markers|652K deliv null early; volume 0 for illiquid|PSB, CSMP, Carry|Hist|
|2|Adjusted equity|`:equity_bhavcopy_adjusted` (VIEW over factors)|DuckDB view|same|NSE|Equity|Daily|2010-01-04|2026-09-01|7 132 767|same + cumulative factor applied|Derived|YES (split/bonus)|same|same|Residue 78 large genuine, 4 splice fab (PSB cert)|Research|Hist|
|3|Index 1d candles| `data/market_data/nse/candles/1d/{YYYY-MM-DD}.duckdb:candles` |per-date DuckDB|1–165 indices (see §6)|NSE|Index|Daily|2010-01-04|2026-09-01|4 127 files, ~1–165 rows/file|symbol, timeframe=1d, timestamp 00:00, open/high/low/close, volume, is_synthetic|Raw|No|One file/day|2010-01-04 only Nifty 50; 2016-02-11 →58 indices; 2023-01-02 →3 indices (N/BN/VIX)| `is_synthetic` always FALSE historically; early years sparse|DRA, DayType|Hist|
|4|Equity/Fut/Opt 1m (current store)|`data/market_data/nse/candles/1m/{YYYY-MM-DD}.duckdb:candles`|per-date DuckDB|2 syms pre-2024-10-17, 195–231 post|NSE|Equity+Index|1m|2012-01-02|2026-09-01|3 604 files, 749–76 125 rows/file|symbol, instrument_key, timeframe 1m, timestamp 09:15-15:30, OHLC, volume, is_synthetic|Internally aggregated (from Upstox WS `live_buffer` + `fetch_upstox_historical` / `fetch_intermarket_data`)|No|One file/day|2012-2024: only Nifty/Bank (2); 2018: 223 files (23 missing vs calendar); 2026-08-01 missing|CAS synthetics from 2026-08-03 (see §9); schema added `instrument_key` column in 2026|LoopDriver Live, ISD, A-Index|Hist+Live|
|5|Vendor 1m (alt)|`data/market_data/nse/candles/1m_vendor/{symbol}.duckdb:vendor_1m`|per-symbol DuckDB|101 Nifty200 names (abb→zyduslife)|NSE|Equity|1m|2015-02-02|2025-08-06|~920 k rows/symbol|ts, open/high/low/close, volume|Vendor (true 1m)|Unknown|One file/symbol|No file for many Nifty200; ends 2025-08-06|C5 alignment median 0.03% vs official; max 40 bp|ISD certification|Hist|
|6|Futures EOD|`data/market_data/futures_bhavcopy.duckdb:futures_bhavcopy`|DuckDB|380 underlyings (189→263/yr)|NSE FO|Futures|Daily|2016-02-11|2026-09-01|1 490 813|underlying, expiry_dt, trade_date, open/high/low/close/settle, contracts, val_in_lakh, open_int, chg_in_oi|Raw|No|Single DB|None|Settle vs close both present|Carry/TS, SFB|Hist|
|7|Index options EOD|`data/market_data/options_bhavcopy.duckdb:option_bhavcopy`|DuckDB|1 symbol (Nifty only?) + strikes|NSE FO|Index Option|Daily|2016-02-11|2026-07-17|5 490 319|symbol, expiry_dt, strike, option_type (CE/PE), open/high/low/close/settle, contracts, val, open_int, chg_in_oi|Raw|No|Single DB|2026-07-18→09-01 missing (45 d lag)|Symbol null? single underlying|Options analytics|Hist|
|8|Stock options EOD|`data/market_data/stock_options_bhavcopy.duckdb:stock_options_bhavcopy`|DuckDB|366 underlyings|NSE FO|Stock Option|Daily|2016-02-11|2026-09-01|99 267 586|underlying, expiry/strike/type, OHLC/settle, contracts, open_int, chg_in_oi|Raw|No|Single DB|None|~6–9 M/yr|Skew sleeve|Hist|
|9|Instrument master|`data/instruments/nse_fo_instruments.duckdb:instruments`|DuckDB|F&O master (all strikes/expiries)|NSE FO|Fut/Opt master|Snapshot|snapshot_date 2026-06-09→2031-06-24|1099302|instrument_key, tradingsymbol, name, expiry, strike, instrument_type, lot_size, exchange, isin, tick_size, snapshot_date|Raw (Upstox/NSE)|—|Single DB|Snapshot only, not historical|Used for option selection (strike/expiry)|Live|
|10|Config/fo_stocks|`data/config/config.db:fo_stocks` (SQLite)|SQLite|203 (3 indices +200 equities, snapshot `parked`)|NSE|Equity+Index|Static|2026-08-11 (parked)|203|trading_symbol PK, instrument_key, name, lot_size, is_active|Curated|—|Single table|Snapshot; not PIT|Parked equities note: WS cap 42|Live universe|Live|
|11|Live buffer candles|`data/live_buffer/candles_today.duckdb:candles`|DuckDB|3 indices (Nifty/Bank/VIX) today only|NSE|Index|1m|today 09:15→16:00|today|76 218 rows today|same as 1m|Derived (WS aggregation)|No|Single file, purged daily|Only today; volatile|Ingestor → provider|Live|
|12|Live buffer ticks|`data/live_buffer/ticks_today.duckdb:ticks`|DuckDB|3 indices today|NSE|Index|Tick|today 12:01→16:00|today|42 720|symbol, timestamp, price, volume, bid, ask|Raw WS|—|Single file|Only today|bid/ask NULL|Live|Live|
|13|Bhavcopy raw| `data/market_data/bhavcopy_raw/{secfull,focal}_*.csv/.404` |CSV+.404 marker|All listed|NSE|Equity|Daily raw|2010→2026|2076 CSV, 4281 `.404`|CSV cols (symbol, series, OHLC etc.)|Raw archive|No|One file/day|404 markers = missing (some are holidays)|Not used directly (ingested)|Archive|
|14|Corporate actions raw|`data/market_data/corporate_actions_raw/CF-CA-*.csv` + `bse_ca_*.json`|CSV+JSON|All BSE scrip codes|BSE|CA|Event|2010→2026|~3 000 files|symbol, ex_date, purpose, ratio_or_fv, raw_json|Raw|—|One file per scrip/chunk|19 parse rejects|PSB CA pipeline|Hist|
|15|CAS categories|`data/cas/cas_category.duckdb:cas_category`|DuckDB|366 symbols|NSE|Equity|Static|effective_from/to|366|symbol, effective_from/to|Derived (NSE circular)|—|CAT1/2 per 2026-08-03|Introduced 2026-08-27|Reference for CAS flag|Hist|
|16|ISD PIT universe|`data/isd/pit_universe.duckdb:pit_membership`|DuckDB|173 900 rows|NSE|Equity|Daily PIT|2023-01-02|2026-08-24|173 900|session_date, symbol, isin, entity, intraday_present, fno_member|Derived|—|Single DB|Sessions 903|Gate certified|Hist|
|17|Signal-engine facts| `data/signal_engine/*/facts.duckdb` etc.|DuckDB|Backtest universes|—|—|Daily/formation|2016→2026|see §10|formation-based signals|Derived|—|Per-sleeve DB|N/A|Carry/TS/Skew|Hist|
|18|Day-type features| `data/features/day_type/*.csv` + `.duckdb:day_type_facts`|CSV+DB|Nifty 50 only|NSE|Index|Daily + intraday checkpoints|2012→2026|3 402 intraday rows (13pm etc.)|53 features (A–G) + regime|Derived|—|CSV per checkpoint|844 day_type_facts|Used for regime|Hist|
|19|A-Index intraday| `data/a_index_intraday/paper_trades.duckdb` + JSONs|DB+JSON|3 indices (cost meas.)|NSE|Index|1m+cost|2023-01-02→2026-08-24 (certified)|trial 2 files|entry bp, slippage, basis etc.|Derived|—|Per-session|Only certified slice|Research only|Live/Paper|
|20|Universe raw snapshot| `data/market_data/universe_raw/nifty200_current.csv` |CSV|200 snapshot|NSE|Equity|Static|snapshot 2026|200|Company, Industry, Symbol, ISIN|Raw|—|—|Snapshot only|Survivorship risk|Reference|Live|
|21|Market cap / MCWB| `data/reference/mcwb_*.zip` / NIFTY CSV|ZIP CSV|Broad|NSE|Equity|Monthly|2016→2026|—|market cap, weights|Raw NSE|—|ZIP per month|Gaps as per manifest|Not fully automated|Hist|

*Exact counts measured 2026-09-01; vendor `/tmp` counts vary.*

---

## 2. Historical Coverage Matrix

> Legend: **●** substantial; **◐** partial/2-sym only; **○** sparse/1; **—** absent. Row labels give exact start date and underlying file count.

| Dataset / Feature | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (→09-01) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **NIFTY 1d OHLC (index)** | ●252 | ●247 | ●251 | ●250 | ●244 | ●240 | ●247 | ●248 | ●246 | ●245 | ●252 | ●248 | ●248 | ●246 | ●249 | ●249 | ●165 |
| **BANKNIFTY 1d** | ○1 | ○1 | ○1 | ○1 | ○1 | ●49* | ●247 | ●248 | ●246 | ●245 | ●252 | ●248 | ●248 | ●246 | ●249 | ●249 | ●165 |
| **India VIX 1d** | — | — | — | — | — | ◐49* | ●247 | ●248 | ●246 | ●245 | ●252 | ●248 | ●248 | ●246 | ●249 | ●249 | ●165 |
| *`1d` distinct rows/file: 2010=1 (Nifty only), 2015=49 nascent index set, 2016=58, 2023=3 (curated N/BN/VIX)* |
| **NIFTY 1m OHLC** | — | — | ◐250 | ◐249 | ◐243 | ◐247 | ◐246 | ◐247 | ◐223 | ◐244 | ◐251 | ◐247 | ◐247 | ◐246 | ●249† | ●249† | ●166† |
| **†2024-10-17→: 195–231 syms; prior = 2 syms (Nifty/Bank), 750 rows/file** |
| **Equity daily OHLC (panel)** | ●347k | ●363k | ●379k | ●352k | ●365k | ●406k | ●432k | ●462k | ●448k | ●460k | ●443k | ●452k | ●474k | ●496k | ●541k | ●586k | ●432k |
| **Equity deliv %** | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | *6570k of 7135k have deliv; null early illiquid* |
| **Futures EOD (380 us)** | — | — | — | — | — | — | ●120k | ●157k | ●157k | ●127k | ●106k | ●124k | ●150k | ●140k | ●139k | ●161k | ●104k |
| **Index options EOD** | — | — | — | — | — | — | ●456k | ●527k | ●566k | ●770k | ●731k | ●510k | ●562k | ●339k | ●394k | ●394k | ●238k |
| **Stock options EOD (366 us)** | — | — | — | — | — | — | ●6.5M | ●8.7M | ●9.0M | ●9.1M | ●8.5M | ●8.2M | ●8.1M | ●7.6M | ●8.1M | ●7.4M | ●5.8M |
| **Vendor 1m (101 eq)** | — | — | — | — | — | ●84k | ●91k | ●92k | ●91k | ●90k | ●93k | ●92k | ●92k | ●91k | ●92k | ●56k† | — |
| **Tick (N/BN/VIX)** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | ●today only |
| **ADX/market cap MCWB** | — | — | — | — | — | — | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |

**Common historical intersections (exact):**
- **Tier A longest daily:** `2010-01-04 → 2026-09-01` (Nifty 50 daily). **2016-02-11 → 2026-07-17** for *multi-asset daily* (futures + both option sets overlap). 2026-07-18→09-01 loses index options.
- **Tier B intraday index-only:** `2012-01-02 → 2026-09-01` with 750-bar days (Nifty/Bank 2-sym). 2018 gap (223 vs ~245).
- **Tier B2 full breadth intraday:** `2024-10-17 → 2026-08-31` (≈ 195–231 syms, 71–74 k rows/day). Prior 2012–2024 breadth intraday is *vendor only* (101 syms, 2015-02-02→2025-08-06).
- **Tier C options-aware intraday:** No strike-level intraday historically; only EOD options since 2016.
- **Tier D microstructure:** No history; `ticks_today` only.

---

## 3. OHLC / Volume / OI Detail

### Price (all EOD unless noted)
| Family | Open | High | Low | Close | Adjusted? | Settlement | Source file |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
|Equity daily (`equity_bhavcopy`) | Y | Y | Y | Y | N (raw); `equity_bhavcopy_adjusted` Y via factors | `prev_close` present, not settle | `equity_bhavcopy.duckdb` |
|Index 1d (`1d/candles`) | Y | Y | Y | Y | N | — | `nse/candles/1d/*.duckdb` |
|Equity 1m (`1m/candles`) | Y | Y | Y | Y | N | — | `nse/candles/1m/*.duckdb` |
|Vendor 1m | Y | Y | Y | Y | UNKNOWN (vendor) | — | `1m_vendor/*.duckdb:vendor_1m` |
|Futures daily | Y | Y | Y | Y | N | Y (`settle`) | `futures_bhavcopy.duckdb` |
|Index options daily | Y | Y | Y | Y | N | Y | `options_bhavcopy` |
|Stock options daily | Y | Y | Y | Y | N | Y | `stock_options_bhavcopy` |

### Activity
| Family | Volume (shares) | Turnover (INR) | #Trades | Notes |
|---|:---:|:---:|:---:|---|
|Equity daily | Y (`volume`) | Y (`turnover`) | — | `deliv_qty` + `deliv_pct` 2010-present (65 % fill) |
|Index 1d | Y (N/BN positive; VIX/EOD indices 0 pre-2016, then volume 137M→296M) | — | — | VIX volume is NSE disseminated, sparse early |
|1m (current) | Y (zero for synthetic 15:15-15:27 post-CAS) | — | — | Index volume block G always 0 (index has no volume) |
|Vendor 1m | Y | — | — | Index volumes synthetic |
|Futures | Y (`contracts` + `val_in_lakh`) | Y | — |  |
|Options | Y (`contracts`, `val_in_lakh`) | Y | — |  |

### Derivatives
| Family | OI | chg_in_oi | basis | strike-level vol/OI | IV | bid/ask |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
|Futures daily | Y (`open_int`) | Y (`chg_in_oi` alias `chg_in_oi`) | Compute as `fclose − spot_close` (requires join to equity/index close) | — | — | — |
|Futures continuous (`stock_futures_continuous`) | Y (rolled) | — | implied via `adj_close`/`roll_ratio` | — | — | — |
|Options daily (index/stock) | Y | Y | — | **Y**: rows at `(expiry,strike,type)` incl. volume+OI | **N** (must compute) | **N** |
|1m vendor/1m current | **N** | **N** | **N** | **N** | **N** | **N** (ticks have null bid/ask) |

Do not assume IV/bid/ask exist historically — Upstox chain snapshots are *live only* (`core/data/options_provider.py`).

---

## 4. Intraday Data

| Timeframe | Historical range | Instruments | OHLC | Vol | OI | Bar origin | Reconstructable? | “Today” vs “Historically” |
|---|---|---|---|---|---|---|---|---|
| **1m (primary)** | **2012-01-02 → 2026-09-01** (3 604 files) | 2012-2024-10-16: Nifty/Bank only (2); 2024-10-17→: 195–231 Nifty200 + Nifty/Bank/VIX (73–76 k rows/d) | Y | Y (0 for synthetic) | N | Internally aggregated (WS `LiveBufferWriter` → `Max`/`Min` etc.; not exchange native 1m) | Y for covered symbols; vendor alignment median 0.03% | Today in `live_buffer/candles_today.duckdb`; history in `1m/*.duckdb` |
| **1m (vendor)** | **2015-02-02 → 2025-08-06** (101 per-symbol files, ~920 k rows/sym) | 101 equities (abb … zyduslife); *not* indices | Y | Y | N | Vendor (unknown agg) | Y (different schema) | History only (file per symbol) |
| **5m/15m/30m/1h** | **None stored historically** | — | — | — | — | Resampled on the fly via `core/analytics/resampler.py` (no overnight bars) | Resamplable from 1m where 1m exists | “Today” resamplable; historically only where 1m existed |
| **1d (resampled intraday)** | 2010-01-04→ (via EOD) | see §2 | — | — | — | EOD bhavcopy + index daily | Y | — |

**Exchange vs internal:** 1m bars are *not* NSE-native 1m dissemination; they are `DBTickAggregator` → `LiveBufferWriter` aggregation (tick→bar). CAS flag `is_synthetic` marks halt/auction carry-forward (15:15–15:27, 13 copies + 1 auction bar). Vendor 1m bar provenance undocumented.

**Reconstruction consistency:** Full period reconstructable only for the two indices; Nifty200 breadth reconstructable only 2024-10-17→. Resampling to 5/15/30m is deterministic via `resampler.py` where 1m exists.

---

## 5. Tick and Market-Microstructure Data

| Field | Live today? | Historical? | Coverage | Source | Notes |
|---|---|:---:|---|---|---|
| **Trades (price, qty, timestamp)** | Y | N | 2026-09-01 only, 09:15–16:00 | `live_buffer/ticks_today.duckdb:ticks` (3 indices) | 42 720 ticks today |
| **tick timestamp** | Y | N | same | same | `TIMESTAMP` precision seconds (IST) |
| **trade price / volume** | Y | N | same | same | schema `price DOUBLE, volume BIGINT` |
| **bid / ask / bid size / ask size** | Schema exists, values **NULL** today | — | — | `ticks.bid/ask` | Not populated |
| **Order-book depth / MBP / MBO** | N | N | — | — | Not collected |
| **Order events / cancellations / aggressor** | N | N | — | — | — |
| **Sequence numbers** | N | N | — | — | — |

**Start date:** Live ticks exist only from the *current session*; no archive. Historical tick is **absent** for all prior dates. Upstox WS tick collector (`scripts/market_ingestor.py`) writes via `LiveBufferWriter` queue; no backfill.

---

## 6. Market-Wide Data

| Series | Universe | Freq | Historical coverage | Source | Notes |
|---|---|---|---|---|---|
| **Nifty 50** | — | 1d+1m+ticks | 1d 2010→, 1m 2012→ (index-only early), tick today | `1d/1m/live_buffer` | Reference |
| **Nifty Next 50 / 100 / 500 etc.** | index family | 1d | 2016-02-11→: 58 →81 distinct per file | `1d/candles` | Not in 1m |
| **Nifty Bank** | — | 1d+1m | 1d from 2015 (49 rows) →247/yr; 1m 2012→ (2nd index) | same | 1m 2nd symbol |
| **India VIX** | — | 1d+1m | 1d 2015→; 1m from 2023-01-02 (3-sym file) | same | 1m late addition |
| **Sector indices** | — | 1d | In `1d` files (Nifty IT, etc.) from 2016→ | `1d` | No 1m |
| **Individual equities (≈4k names)** | 1 520 (2010) →2 954 (2026) | daily | 2010→ daily EOD; intraday breadth only 2024-10-17→ (195) or vendor 101 (2015→) | `equity_bhavcopy` / `1m` | Survivorship via bhavcopy |
| **Breadth (A/D, NH/NL, total vol)** | — | — | **None stored** (derivably count `equity_bhavcopy` per `trade_date`) | — | Compute at query time |
| **Volatility indices (ex VIX)** | — | — | — | — | Not stored |
| **Futures** | 380 underlyings | daily EOD | 2016-02-11→ | `futures_bhavcopy` | Spot-fut basis computeable |
| **Options (index+stock)** | 1 + 366 underlyings × strikes | daily EOD | 2016→ | `option_bhavcopy` | No intraday OI/IV |
| **FX / Commodities / Bonds / Global** | — | — | — | — | **None** (MCX packet in `fetch_intermarket_data.py` unused; no data) |

Live breadth via `market_ingestor` only for the 3 indices; no cross-market feed.

---

## 7. Universe / Survivorship Information

**Current snapshot only:** `data/market_data/universe_raw/nifty200_current.csv` (200 rows, Symbol/ISIN) is a date-less snapshot — **do not use for historical allocation** (survivorship bias).

**Point-in-time (corrected) sources:**
- `equity_bhavcopy.duckdb:trading_calendar` 2010-01-04→2026-09-01 (4 138 sessions) — authoritative session list, `n_symbols`.
- `instrument_master` 2 384 listings, `symbol_changes` 1 057 renames, `symbol_isin` 3 639 mappings.
- **Time-aware entity:** `symbol_entity_intervals` 4 133 rows (`symbol→entity` vaild_from/to, e.g., `HINDPETRO|2010-01-04→9999-12-31`). Prevents recycled tickers from conflating entities.
- **MCWB PIT:** `data/reference/mcwb_*.zip` (monthly, 2016→) + `universe_membership` 35 000 rows (rebalance_date, symbol, rank, turnover_median) 2012-01-31→2026-07-09 (175 dates) — **true PIT Nifty200 proxy**. Also `isd/pit_universe.duckdb:pit_membership` 173 900 rows 2023-01-02→2026-08-24 with `fno_member`, `intraday_present`.
- `universe_intervals` 590 entity intervals + `universe_eligibility` per symbol.

**Delisted/renamed/merged:** Covered via `symbol_entity_intervals` + `corporate_actions` (splits/bonus/dividends) + `symbol_changes`. Delisted stocks *remain* in `equity_bhavcopy` up to their last `trade_date` (no deletion); missing thereafter is natural attrition. No explicit `delisted` flag — infer via last occurrence vs calendar.

**Can we snapshot without bias? YES, WITH CAVEATS** if you use `trading_calendar` + `universe_membership`/`pit_membership` + `symbol_entity_intervals`. **NO** if you filter by `nifty200_current.csv` or static `fo_stocks`.

Missing: IPO dates not tabled (infer from first `equity_bhavcopy` appearance + `instrument_master.listing_date`); suspensions not tabled (404 markers + gaps).

---

## 8. Corporate-Action and Adjustment Infrastructure

| Artifact | Location | Rows | Coverage | Fields | Usage guidance |
|---|---|---|---|---|---|
|Raw purpose| `equity_bhavcopy.duckdb:corporate_actions`|11 965|2010→2026|spliced from BSE JSONs: symbol, ex_date, action_type (SPLIT/BONUS/DIVIDEND), ratio_or_fv, purpose_raw, scripcode, raw_json|PIT source; not adjusted|
|Adjusted prices|`:equity_bhavcopy_adjusted`|7 132 767|2010→|same cols, OHLC adjusted by cumulative factor|Use for **returns / momentum** research|
|Factors|`:adjustment_factors`|1 207|2010-01-04→2026-07-10|symbol, ex_date PK, factor, action_type, source|Cumulative; applied causally|
|Exceptions & rejects|`:ca_evidence_exceptions` (16), `:ca_parse_rejects` (19), `:ca_scope_exclusions` (13)|—|—|legs, stored_factor, deviation etc.|Manual review; 4 splice fabs dispositioned|
|ISIN linkage|`symbol_isin` 3 639|—|—|symbol, isin, n_days|For mapping after ISIN re-use|
|Expiry & continuous futures|`futures_bhavcopy` + `:stock_futures_continuous` 49 711 (2022-08-08→2025-07-17, `roll_flag`, `roll_ratio`)|—|2016→ (continuous 2022→)|Underlying, expiry_dt, adj_open…roll_ratio|Use `stock_futures_continuous` for **futures momentum** (not EOD raw); gap 2016-2022 has no continuous|
|Symbol maps|`instrument_master` 2 384 + `symbol_changes` 1 057|—|—|old→new, effective_dt|For long backtests|
|Vendor splits|`verified_splits_2010_2026.csv`|—|2010→|—|Reference|

**Formula:** Adjusted `close_adj = close_raw * Π(factor where ex_date > trade_date)`. Factors for splits/bonus only (divs are `DIVIDEND` but not in `adjustment_factors` — dividends are **not price-adjusted**; use total-return logic elsewhere).

**Which version for which research:**
- **Price-based patterns (intraday, regime, realized vol):** Use **raw** `1m` or `equity_bhavcopy` where horizon < split gap; else use adjusted.
- **Cross-sectional momentum / long-short panels:** Must use **adjusted** (`equity_bhavcopy_adjusted` or `carry/nifty50`).
- **Derivatives backtesting:** No dividend adjustment needed; expiry handling via `stock_futures_continuous`.

Inspect implementation in `scripts/csmp/ingest_corporate_actions.py` and PSB substrate cert.

---

## 9. Timestamp and Session Information

| Aspect | Detail |
|---|---|
| **Timezone** | `Asia/Kolkata` (IST, UTC+5:30), no DST. `core/market/session_schedule.py: CAS_EFFECTIVE 2026-08-03`. |
| **Session times (current CAS regime)** | Cash CAT1 (F&O stocks): 09:15–15:15 continuous + 15:15–15:27 halt/auction + 15:28/29 auction bar; Cash CAT2: 09:15–15:30 continuous; Auction: 15:30–15:35; Derivatives: to 15:40. Pre-CAS 1900-01-01→2026-08-02 was 09:15–15:30 uniform. Schedule is date-keyed, segment-named (`cash_cat1`, `cash_cat2`, `cash_auction`, `derivatives`). |
| **Timestamp precision / semantics** | 1m bars: `timestamp` = **bar open** (e.g. `09:15:00`), 1-sec ticks: `timestamp` = event time. 1d bars: `00:00:00`. `timestamp` naive (no tz) but IST semantics; Upstox WS delivers `+00:00` then converted `replace(tzinfo=None)` in loaders. |
| **Holidays / calendar** | `trading_calendar` is oracle (4 138 sessions, 2010-2026). Missing `1m`/`1d` files on holidays are correct absences; `.404` markers in `bhavcopy_raw`. |
| **Missing bars** | CAS: 13 synthetic `O=H=L=C, volume=0` 15:15–15:27 for 92-95 % symbols; flagged `is_synthetic=TRUE` — **must filter**. Vendor 1m missing 2025-08-07→ present. ISD certification C1: 35 missing 1m files (12 special + 46 regular holes 2018-05, 2023-02). |
| **Monotonic / duplicate** | 1m files enforce `PRIMARY KEY (symbol,timeframe,timestamp)`; certification C3: no dups/OI violations; 45 sessions with schema validity issues (pre-2014). |

---

## 10. Derived Features Already Available

> All derived features are **causal** (trailing only) where implemented correctly; verify per artifact.

| Feature | Formula / Source | Input | Timeframe | Hist availability | Causal? |
|---|---|---|---|---|---|
| **Day-type 53 features** | `core/analytics/day_features.py`: Gap (gap_pct…prev_day_vol), Opening (open_5/15/30m_ret…), Trend (CLV, linreg_r²/slope, HH/LL counts), Vol (realized_vol, ATR_5m), Microstructure (VWAP/TWAP, center-of-mass, twap_cross_count), Rotation (flip_count, dominant_dir), Volume (zeroed for index) | Nifty 1m (`nse/candles/1m`) | Daily per session, plus checkpoints 10am/11am/13pm | `nifty_day_features_2012…2026.csv` (one per year) + master; `intraday_features_{10am,11am,13pm}.csv` (3 402 rows: 2012→) | **YES** (rolling 20-d percentiles, intraday windows end at checkpoint) |
| **Day-type regime labels** | KMeans on PCA of 53-d; `cluster_centroids.csv`, `cluster_labels.csv` | Day features | Daily | 844 `day_type_facts.duckdb:day_type_facts` (session_date, checkpoint, regime, confidence, vix_close) 2023-01-02→ | TRAINED on 2012-2023 (leak if reused); **not PIT** unless retrained per window |
| **Signal-engine signals** | `data/signal_engine/carry` 22 k facts + weekly 106 k signals; `trend` 18 k; `ts_basis` 67 k facts → 67 k signals; `ts_basis_daily` 482 k facts; `skew` 7 k; `ivol` 20 k | Equity adjusted + futures | Formation dates | 2012-2026 (per sleeve) | PIT (formation-based), but formation universe is snapshot-biased if not using `pit_universe` |
| **Carry continuous / nifty50** | `carry/nifty50.duckdb` (4 127 daily) + `production.duckdb` (1 158 rebalance summaries) | adjusted equity + vol | Daily | 2010→ | Y |
| **Trend continuous** | `trend/continuous.duckdb:trend_continuous` 484 260 rows | futures `stock_futures_continuous` | Daily | 2022-08-08→2025-07-17 (limited) | Y (but limited window) |
| **Options analytics** | `core/analytics/options_analytics.py`: PCR, GEX, OI buildup, Max Pain, IV smile | Live `options_provider` chain snapshot | 5-sec snapshots | **None historically stored** | N/A (live) |
| **Realized vol / Resampler** | `realized_vol.py` (annualized 1m log-ret, intra-session only), `resampler.py` (1m→5/15/30m/1h, per-session) | 1m Nifty | On demand | Resamplable where 1m exists | Y (intra-session, no overnight) |
| **Is synthetic flag** | `is_synthetic` in 1m/1d | — | 1m | 2026-08-03→ | Y (era-aware) |
| **CAS category** | `cas/cas_category.duckdb` | — | static | 366 symbols | — |
| **Cost substrates** | `a_index_intraday/cost_substrate_measurements.json` + `paper_trades.duckdb` (ISD phase) | 1m vendor/native | Measured 2023-01-02→2026-08-24 | Certified (G1 contiguity) | Y |

*No stored SMA/EMA/RSI/ATR series; compute on demand from 1m/1d where available.*

---

## 11. Live / Historical Availability Matrix

| Variable | Live today? | Historical? | Hist start | Freq | Quality |
|---|---|:---:|---|---|---|---|
|Nifty 50 OHLC (daily) | Y (EOD) | Y |2010-01-04|Daily|High (bhavcopy + 1d, bhavcopy close == 1d close)|
|Nifty 50 OHLC 1m | Y | Y |2012-01-02|1m|Medium (synthetic flag after CAS)|
|Nifty 50 volume (daily) | Y | Y |2010|Daily|Low early (1 row file)|
|Nifty Bank OHLC 1m | Y | Y |2012-01-02|1m|Medium|
|India VIX 1m | Y | Y (short) |2023-01-02|1m|Medium|
|Equity daily OHLC (4k names) | Y (EOD) | Y |2010-01-04|Daily|High|
|Equity 1m (Nifty200) | Y (intraday) | **Partial** |2024-10-17|1m|High (195-231 syms) — prior **No** (2 syms or vendor 101 2015→)|
|Equity turnover/deliv% | Y | Y |2010|Daily|Medium (deliv sparse)|
|Futures settle/OI (daily) | Y | Y |2016-02-11|Daily|High|
|Futures continuous (rolled) | N | **Partial** |2022-08-08→2025-07-17|Daily|Gap 2016-2022|
|Options EOD (OI/chg, vol) | Y | Y |2016-02-11|Daily|High (stock opts to 2026-09-01, index opts to 07-17)|
|Options IV / Greeks / bid-ask | Y (snapshot) | **N** |—|5-sec|Live only|
|Tick (price/vol, N/BN/VIX) | Y (42k ticks today) | **N** |—|Tick|Live only|
|Depth / MBO / order events | N | N |—|—|—|
|FX / Commod/ Bonds / Global | N | N |—|—|—|
|Universe PIT (175 dates) | Y | Y |2012-01-31|Rebalance|High|
|Corp actions / splits | Y | Y |2010|Event|Medium (16 exceptions)|
|Realized vol (computed) | Y | Y (where 1m) |2012 (index) / 2024 (breadth)|1m→daily|Y|
|Breadth A/D, NH/NL | Computable via bhavcopy | **Not stored** |2010|Daily|Derivable|

---

## 12. Historical Common Denominator — Tiers

### Tier A — longest history (daily)
**2010-01-04 → 2011‑ish: Nifty 50 daily only** (1 row/day, 1d + bhavcopy). **2016-02-11 → 2026-07-17: full daily multi-asset** (equities 1 500→2 900 names, 58→80+ indices, 380 futures, both option sets). *Use for EOD pattern / regime over 14 y.*

### Tier B — intraday breadth (current store)
**2024-10-17 → 2026-08-31** (≈ 345 valid sessions): 1d (3–165 indices) + 1m (195–231 eq+3 indices, 71–76 k rows/d) + futures/options EOD. *Use for intraday analogues with real cross-section.* Prior 2012-2024 is **index-only intraday** (Nifty/Bank, 750 bars/d) — breadth analogues impossible.

### Tier B‑vendor — vendor breadth intraday
**2015-02-02 → 2025-08-06**: vendor 1m 101 eq (per-symbol files, ~920 k rows/sym) + index 1m (2 syms) + daily panels. *Longer breadth intraday but only 101 names, different schema, no VIX/Bank early.*

### Tier C — richer market state (daily + options)
**2016-02-11 → 2026-07-17**: All of A + strike-level options EOD (99 M stock opts rows). Basis & skew computeable. Still no intraday OI/IV. Best for option-structure analogues at **daily** resolution.

### Tier D — microstructure
**Today only** (09:15–16:00, 3 indices, ticks+1m live_buffer). No historical microstructure. **NOT usable for pattern search.**

*Do not mix tiers without noting the universe shift (2 → 101 → 231).*

---

## 13. Data Quality Assessment

### Confirmed problems
- **CAS synthetic:** 92-95 % of 1m rows 15:15-15:27 from 2026-08-03 are `is_synthetic=TRUE, volume=0` + 1 auction bar (15:28/29 with entire auction vol). Unfiltered VWAP/vol/MAE toxic. *Verified 2026-08-03…24*.
- **1m breadth sparsity:** 2012-2024-10-16 only 2 symbols (749-750 rows/file vs 73k). Early breadth empty.
- **Vendor 1m gaps:** 48 sessions 2018-05-02…25 + 2023-02-01…03-01 missing (ISD C1). 2018 yearly files 223 vs 246 expected.
- **1m native C2:** 66 partial days (not 375 bars) 2012-2026 (histogram 374×17, 373×6…). 35 missing 1m files vs calendar (3598 vs 3624).
- **Index options lag:** 45 days stale (max 2026-07-17 vs stock opts 2026-09-01).
- **CA residue:** 78 large_genuine + 4 splices dispositioned, 16 evidence exceptions, 19 parse rejects.
- **Equity panel duplicates:** 2024-2026 yearly distinct 2 400→2 954 but file counts stable — list expansion via SME/microcap, not survivorship fix.
- **Live ticks bid/ask NULL:** schema exists, values absent.

### Possible / unverified
- **1m 2012-2015 bar construction** may blend exchange + vendor reconstruction; C5 alignment vendor vs official median 0.03 %, max 40 bp — unverified per-bar for early years.
- **Corporate dividend adjustment:** Not price-adjusted; TR not stored — unverified for TR-based patterns.
- **After-hours zero bars:** `live_buffer` keeps 16:00 cutoff; 15:40 derivatives tail not captured.
- **Vendor 1m volume for indices** possibly synthetic (0).

### Schema stability
- `candles` added `instrument_key` column mid-2026 (old files lack it). `is_synthetic` added 2026. Both are nullable with guards.

---

## 14. Existing Research / Backtest Infrastructure

| Component | Location | Purpose | PIT / Lookahead | Snapshot? | Efficiency |
|---|---|---|---|---|---|
| **LoopDriver** | `core/runtime/driver.py` (+ `config.py`, `event_journal.py`) | Single-threaded orchestrator; pulls bars from `MarketDataProvider`, advances `Clock` per bar | **Prevents look-ahead** (causal `Clock`, 90-day warmup, `is_synthetic` filter) | Replays at arbitrary intervals (backtest) or live (LoopDriver) | Deterministic |
| **MarketDataProvider / DuckDB reader** | `core/data/options_provider.py`, `core/msi/dra/duckdb_observation_reader.py` | Reads `1d`/`1m` per-date DuckDBs | **PIT**: `et` param, `as_of` date; reads committed files only | `read(date, symbols)` | DuckDB vectorized |
| **Bhavcopy loader** | `scripts/csmp/ingest_*.py`, `core/data/loader*` | Ingests NSE bhavcopy + vendor | Inserts with `ON CONFLICT DO UPDATE`; idempotent | `equity_bhavcopy.duckdb` | Bulk |
| **Feature store** | `core/analytics/day_features.py`, `realized_vol.py`, `resampler.py` | 53 day features, vol, resampling | Causal (trailing windows) | `day_type_facts.duckdb` (844 sessions) | CSV cache |
| **Signal engine** | `data/signal_engine/carry|trend|ts_basis*|skew|ivol` | Precomputed formation signals (carry 22k, etc.) | Formation dates (not strategy) | `facts.duckdb`, `signals.duckdb` | —
| **ISD certification** | `scripts/isd/run_certification.py`, `gate_contiguity.py` etc. | Vendor vs native cross-check | Gate suite C1-C6 | `ISD_PHASE1_SNAPSHOT.json` (903 sessions 2023-01-02→2026-08-24) | Verified |
| **Universe / CA** | `instrument_master`, `universe_membership`, `adjustment_factors` | PIT entity mapping | **YES** (`valid_from/to`) | Via intervals table | Indexed |
| **Live breadth via WS** | `scripts/market_ingestor.py` → `live_buffer` | WS → aggregated 1m | Not historical | `candles_today` | Bounded queue |

**Can we reconstruct snapshot at arbitrary timestamp?** **YES** for daily (query `equity_bhavcopy` where `trade_date <= ts` + `trading_calendar` + `adjustment_factors`). For intraday: `DuckDBObservationReader.read(ts, symbols)` joins `1m` file for `ts.date()` + `1d` fallbacks — fully PIT if `is_synthetic=FALSE`.

**Feature store:** No unified feature store; day-type CSVs + per-sleeve DuckDBs are the store.

---

## 15. Available vs Reconstructable

| Variable | Reconstructable at arbitrary historical `ts`? | Reason |
|---|:---|---|
| **Nifty 50 1d close/breadth** | **YES** | Raw `equity_bhavcopy` + `1d/candles` 2010→ |
| **Equity daily OHLC + volume/deliv** | **YES** (with deliv nulls early) | `equity_bhavcopy` 2010→, entity-corrected |
| **Adjusted close for splits/bonus** | **YES, WITH CAVEATS** | `equity_bhavcopy_adjusted` 2010→; 16 exceptions, dividends not adjusted |
| **Futures settle/OI daily** | **YES** | `futures_bhavcopy` 2016→ |
| **Options strike OI/vol daily** | **YES** | `stock_options_bhavcopy` / `option_bhavcopy` 2016→ |
| **Futures basis** | **YES** | spot (`equity_bhavcopy`/`1d`) + futures settle (same trade_date) |
| **Nifty 1m OHLC (index)** | **YES** 2012→ | `1m/candles` (post-CAS filter `is_synthetic`) |
| **Equity 1m OHLC breadth** | **YES** 2024-10-17→ (101 names 2015→ via vendor, different schema) | Current store 2→231; vendor only 101 |
| **Resampled 5/15/30m bars** | **YES, WITH CAVEATS** | Recomputed via `resampler.py` from 1m where 1m exists |
| **Tick trades (today)** | **NO** (historical) | `ticks_today` purged daily |
| **Order-book / depth** | **NO** | Never collected |
| **IV / Greeks / bid-ask intraday** | **NO** | Live chain snapshot only |
| **Realized vol (annualized)** | **YES where 1m exists** | Causal from 1m closes (intra-session) |
| **Day-type regime label** | **YES, WITH CAVEATS** | Causal 53-d features; label is trained-on-2012-2023 → lookahead if reused; retrain per window |
| **Breadth (A/D, NH/NL)** | **YES** (derivable) | Count `equity_bhavcopy` per `trade_date` where `close>open` etc. |
| **Sector indices 1m** | **NO** | 1d only (2016→), no intraday |
| **FX/Commod/Global** | **NO** | Not in store |
| **Total-return (div-adjusted)** | **UNKNOWN** | Dividend table exists but factor not applied — need verification |

---

## 16. Final Output — Relevance for Pattern Research

To construct a **daily market-state** (EOD) you have 2016-02-11→2026-07-17 *complete*: ~2 500 equities, 380 futures, 366+1 option underlyings, 80+ indices, delivery, splits-adjusted closes, PIT universe. That is the longest *comparable* panel.

To construct an **intraday market-state** (1m) you have *two non-comparable eras*: **index-only** 2012→2024-10-16 (Nifty/Bank, 750 bars/d) and **breadth** 2024-10-17→2026-08-31 (195–231 names, 71–76 k bars/d). Choose one tier; do not stitch without noting the universe break. The vendor 101-name 1m (2015→2025-08-06) is a third tier with different schema and terminal date.

Microstructure (ticks/depth) is **absent historically** — pattern work cannot use it.

---

### Paths to verify before designing

- Re-run `scripts/isd/run_certification.py` for post-2026-08-24 C1 gaps (ISD snapshot ends 2026-08-24).
- Decide dividend treatment (TR vs price) — `corporate_actions` dividends not in `adjustment_factors`.
- Pin `day_type` retraining window to avoid label leakage.
- Enforce `WHERE is_synthetic = FALSE` for all intraday research (CAS).
- For breadth backtests, use `universe_membership`/`pit_membership`, not `nifty200_current.csv`.

