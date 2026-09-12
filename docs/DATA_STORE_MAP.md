# Data Store Map — Persistent Stores (repo-wide)

**Date:** 2026-09-12 · **§9 re-verified (P1):** 2026-09-12 · **Scope:** all persistent stores (`data/`, `historical/`, `cache/`, `backups/`, `models/`) — DuckDB + SQLite + raw archives + JSONL/session artifacts.
**Method:** filesystem enumeration + read-only schema sampling (`SHOW TABLES` / `DESCRIBE`, row counts). Counts are point-in-time; per-date partitions grow by ~1 file/session.
**Related (not duplicated here):** `docs/reports/ops_data/DATA_STORE_MAP.md` (historical market-state reconstruction detail), `docs/reports/ops_data/DATABASE_CENSUS_2026-09-03.md` (active-vs-redundant census, reclaimable size).

Conventions: **Engine** = DuckDB per-file / DuckDB single-file / SQLite / flat files. **Grain** = one row means what. Writer/reader columns are the owning pipeline, not an exhaustive grep.

## 0. Logical-store index

| # | Domain | Logical store (path) | Engine | Files | Role |
|---|---|---|---|---|---|
| 1 | Market · EOD equity | `data/market_data/equity_bhavcopy.duckdb` | DuckDB single | 1 | Canonical equity EOD panel + CA/universe tables |
| 2 | Market · EOD futures | `data/market_data/futures_bhavcopy.duckdb` | DuckDB single | 1 | FUTSTK/FUTIDX EOD + continuous series |
| 3 | Market · EOD options | `data/market_data/options_bhavcopy.duckdb` / `stock_options_bhavcopy.duckdb` | DuckDB single | 2 | Index / stock options EOD bhavcopy |
| 4 | Market · intraday | `data/market_data/nse/candles/1m/{YYYY-MM-DD}.duckdb` | DuckDB per-date | ~3,612 | Primary 1m candle store (`candles`) |
| 5 | Market · daily | `data/market_data/nse/candles/1d/{YYYY-MM-DD}.duckdb` | DuckDB per-date | ~4,135 | Per-date daily candles (`candles`) |
| 6 | Market · BSE | `data/market_data/bse/candles/{1m,1d}/{date}.duckdb` | DuckDB per-date | 23 | Sensex/BSE candles |
| 7 | Market · vendor 1m | `data/market_data/nse/candles/1m_vendor/{symbol}.duckdb` | DuckDB per-symbol | ~101 | Vendor 1m copy (G1 gate provenance, closed) |
| 8 | Market · raw archives | `data/market_data/bhavcopy_raw/` + `corporate_actions_raw/` + `universe_raw/` + `vendor/niftyindices/` | CSV/ZIP/`.404` | ~11.8k | Raw downloads + miss markers + vendor CSVs |
| 9 | Instruments | `data/instruments/nse_fo_instruments.duckdb` | DuckDB single | 1 | Canonical F&O instrument master |
| 10 | Signals · Carry | `data/signal_engine/carry/` (5 files) | DuckDB single | 5 | Production-ready Carry sleeve |
| 11 | Signals · TS Basis Daily | `data/signal_engine/ts_basis_daily/` (2 files) | DuckDB single | 2 | Research-only daily basis (active) |
| 12 | Signals · other sleeves | `trend/` `ts_basis/` `skew/` `ivol/` `lag/` `trade_intelligence/` | DuckDB single | 9 | Active continuous series + closed-sleeve remnants |
| 13 | Trading state | `data/trading/trading.db`, `data/nifty_shield/trading/trading.db`, `data/nifty_shield_preflight/trading/trading.db` | SQLite | 3 | Live/paper trade ledger (`trades`, `trade_context`) |
| 14 | App config/state | `data/config/config.db`, `data/config.duckdb`, `data/_schedule.duckdb`, `data/_eod_automation.sqlite` | SQLite/DuckDB | 4 | Users, watchlists, runner state, scheduler, EOD automation |
| 15 | Live session | `data/live_buffer/{candles_today,ticks_today}.duckdb` | DuckDB single | 2 | Today's WS buffer (rotates; currently large) |
| 16 | Options live | `data/options/chain_cache.duckdb`, `wall_scan_results.duckdb`, `wall_chain_snapshots/{date}.duckdb` | DuckDB | 9 | Chain cache, wall scans, daily snapshots |
| 17 | Paper sessions | `data/nifty_shield/` (`facts.duckdb`, `execution.db`, `sessions/{date}/`, `vix_history.duckdb`) | DuckDB/SQLite/JSON | ~200 | NiftyShield PAPER audit trail per session |
| 18 | Risk · SPAN | `data/span/` (`nse_fo_span_*.parquet/.zip`, `staging/`, logs) | Parquet/ZIP | ~836 | SPAN margin archives + staging |
| 19 | Reference | `data/reference/` (MCWB zips, NIFTY zips, instrument snapshot) | ZIP/CSV/DuckDB | ~131 | MCWB PIT weights, reference CSVs |
| 20 | Research artifacts | `data/features/`, `data/isd/`, `data/a_index_intraday/`, `data/mrlc_test/`, `data/analog_path/`, `data/reliance_regime/`, `data/se3/`, `data/mto_probe/`, `data/audit/` | DuckDB/CSV/Parquet/JSON | ~2.8k | Feature panels, ISD/PIT, experiments, MTO DATs |
| 21 | Closed-project fixtures | `data/psb1_synthetic/`, `data/psb2_synthetic/` | DuckDB | 14 | PSB-1/PSB-2 synthetic fixtures (CLOSED) |
| 22 | Safety copies | `data/_baselines/` (+ `1m_pre_fo_backfill/`), `backups/` | DuckDB | ~37 | Copy-first baselines + recovery backups |
| 23 | Legacy | `historical/index/` + `historical/index/1m/` | DuckDB per-date | ~1,251 | Superseded index history (last write Feb 2026) |
| 24 | Ephemeral | `cache/`, `data/tmp_duckdb/`, `data/scratch/`, `logs/` | ZIP/HTML/Parquet/log | ~45 | Download cache, scratch, logs |

## 1. Market data (canonical)

| Store | Tables / grain | Key columns | Rows / range | Writer → Reader |
|---|---|---|---|---|
| `equity_bhavcopy.duckdb` | `equity_bhavcopy` (symbol-day), `equity_bhavcopy_adjusted` VIEW, `corporate_actions` (11,965), `adjustment_factors` (1,194), `trading_calendar` (4,146), `symbol_entity_intervals`, `symbol_isin`, `instrument_master`, `universe_*` | trade_date, symbol, series, OHLC, prev_close, volume, turnover, deliv_qty, deliv_pct | 7,158,443 rows; 2010-01-04 → 2026-09-11 | `scripts/csmp/ingest_*` + `scripts/ingest_equity_bhavcopy.py` → PSB/CSMP/Carry, backtests |
| `futures_bhavcopy.duckdb` | `futures_bhavcopy` (1.496M), `stock_futures_continuous` (49,711), `fo_eligible_intervals` (9,092), `ingest_meta` | underlying, expiry_dt, trade_date, OHLC, settle, contracts, open_int, chg_in_oi | 2016-02-11 → present | `scripts/sfb/ingest_futures_bhavcopy_v2.py` → Carry/TS-Basis |
| `options_bhavcopy.duckdb` | `option_bhavcopy` (5.49M, index) | symbol, expiry_dt, strike, option_type, OHLC, settle, contracts, open_int | 2016-02-11 → 2026-07-17 (lags stock opts) | SFB options ingest → options analytics |
| `stock_options_bhavcopy.duckdb` | `stock_options_bhavcopy` (99.5M) | underlying, expiry_dt, strike, option_type, OHLC, settle, contracts, open_int | 2016-02-11 → present | `scripts/sfb/ingest_stock_options_bhavcopy.py` → Skew sleeve |
| `1m/{date}.duckdb` | `candles`: (symbol, timeframe, timestamp) | symbol, instrument_key, timeframe=1m, timestamp (bar open, IST-naive), OHLC, volume, is_synthetic | 2012-01-02 → present (3,612 files); **2 symbols 2012-01-02 → 2022-12-30; 190 → 198 symbols (188 → 196 `NSE_EQ`) from 2023-01-02**; filter `is_synthetic=FALSE` post-CAS 2026-08-03 | Upstox WS ingestor + historical backfill → LoopDriver, ISD, A-Index |
| `1d/{date}.duckdb` | `candles`: (symbol, timeframe, timestamp) | symbol, timeframe=1d, timestamp 00:00, OHLC, volume, is_synthetic | 2010-01-04 → present (1–165 rows/file) | `scripts/ingest_index_history.py` → DayType, DRA |
| `bse/candles/{1m,1d}/` | `candles` | same as NSE | 2026-08-24 → present (15 × 1m, 8 × 1d) | BSE ingest → options_wall D2 |
| `1m_vendor/{symbol}.duckdb` | `vendor_1m`: per-symbol 1m | ts, OHLC, volume (different schema) | 101 syms, 2015-02-02 → 2025-08-06; `vendor_flat.duckdb` roll-up | Vendor copy for G1-B1 gate (closed) — provenance only |
| `bhavcopy_raw/` etc. | raw CSV + `.404` miss markers + `corporate_actions_raw/` + `vendor/niftyindices/*.csv` | exchange-native columns | 2010 → present; 4,292 `.404`, 3,170 `.zip` | download scripts → ingest scripts (never read directly by research) |

## 2. Instruments

| Store | Tables / grain | Key columns | Rows | Writer → Reader |
|---|---|---|---|---|
| `data/instruments/nse_fo_instruments.duckdb` | `instruments`: one row per (instrument_key, snapshot_date) | instrument_key, tradingsymbol, name, expiry, strike, instrument_type, lot_size, exchange, isin, tick_size, snapshot_date | 1.47M | instrument-master ingest → option selection (`core/analytics/options_selection.py`), `/ts-basis-daily/` panel |

## 3. Signal engine (`data/signal_engine/`)

| Store | Tables / grain | Rows | Status / notes |
|---|---|---|---|
| `carry/signals.duckdb` | `signals` (formation×underlying, 23,629), `formations` (127) | z_carry, z_carry_neut, beta, fwd_ret_1m | Production-validated (TRAIN→HOLDOUT→SEALED PASS) |
| `carry/facts.duckdb` | `carry_facts` (22,125): formation×underlying | quintile, eligible, raw_z, basis_reverting | Published facts for runner |
| `carry/production.duckdb` | `run_metadata` (4), `rebalance_summary` (1,158), `rebalance_positions` (328), `equity_curve` | fees/slippage legs, turnover | `scripts/carry_paper_replay.py` → `scripts/carry_production_report.py` (A5-gated) |
| `carry/{weekly_signals,nifty50}.duckdb` | weekly / index series | — | Carry variants |
| `ts_basis_daily/ts_signals.duckdb` | `signals` (485,315) | raw_ann_basis, raw_z, z_ts | RESEARCH-ONLY (operator decision 2026-08-01); sealed window preserved, `run_sealed.py` refuses |
| `ts_basis_daily/ts_facts.duckdb` | `carry_facts` (480,923) | quintile, eligible, raw_z | Live store rebuilt 2026-09-11 (post-CAS spot = continuous-session close) |
| `trend/continuous.duckdb` | continuous futures | large (~383 MB) | Active working series |
| `trend/signals.duckdb`, `ts_basis/ts_*`, `skew/signals.duckdb`, `ivol/signals.duckdb`, `lag/signals.duckdb` | sleeve signals | small | Closed-sleeve remnants (Skew/LAG TRAIN FAIL, IVOL SEALED FAIL) — archival |
| `trade_intelligence/trade_intelligence.duckdb` | trade intelligence | ~1.8 GB | MRLC work |

## 4. Trading + app state (SQLite / scheduler)

| Store | Tables | Grain / notes |
|---|---|---|
| `data/trading/trading.db` (+ `nifty_shield/trading/trading.db`, `nifty_shield_preflight/trading/trading.db`) | `trades` (trade_id, signal_id, strategy_id, symbol, timestamp, side, quantity, pnl, fees, status), `trade_context` (model/universe/regime/dispersion/vol/breadth/SL) | Live/paper ledger; same schema in all three files |
| `data/config/config.db` | `users`, `roles`, `user_watchlist`, `instrument_meta`, `runner_state`, `fo_stocks`, `download_jobs`, `websocket_status` | Flask app state; `fo_stocks` = 203-symbol live snapshot (not PIT) |
| `data/config.duckdb` / `data/_schedule.duckdb` | `scheduled_jobs` (id, pipeline_id, schedule, params, enabled, last/next_run) | Scheduler store (currently 0 rows in sampled copy) |
| `data/_eod_automation.sqlite` | EOD chain state | Orchestrator bookkeeping |

## 5. Live + options runtime

| Store | Tables / grain | Notes |
|---|---|---|
| `data/live_buffer/candles_today.duckdb` | `candles` (86,322 rows sampled): today's 1m bars | WS-aggregated; source of truth intraday → rolled to `1m/{date}` EOD |
| `data/live_buffer/ticks_today.duckdb` | `ticks`: today's raw ticks | Purge-daily buffer; flagged oversized (~9.5 GB in census — verify rotation) |
| `data/options/chain_cache.duckdb` | `option_chain_snapshot` (360 rows): (snapshot, underlying, expiry, strike, type) | Upstox V3 chain cache (5-sec snapshots) |
| `data/options/wall_scan_results.duckdb` | `scan_results` (71,625), `session_regime` (9,845), `oi_baseline` (7,977), `trades` (32) | Options-wall scanner output |
| `data/options/wall_chain_snapshots/{date}.duckdb` | per-date chain snapshots (6 files) | Wall scanner inputs |

## 6. Paper sessions + risk

| Store | Contents | Notes |
|---|---|---|
| `data/nifty_shield/facts.duckdb` | `day_type_facts` (14 rows): session×checkpoint regime facts | PAPER regime facts |
| `data/nifty_shield/execution.db` + `sessions/{date}/` | `bars.duckdb` + `facts.duckdb` + `facts_bars/{date}.duckdb` + `audit.json`, `marks.jsonl`, `signals.jsonl`, `telemetry.json`, `metrics.json` | Per-session PAPER audit trail (≈18 sessions 2026-08-13 → 2026-09-11) |
| `data/nifty_shield/vix_history.duckdb` | VIX history | Regime input |
| `data/cas/cas_category.duckdb` | `cas_category` (366 rows): symbol × [effective_from, effective_to] | CAS PIT Category I/II (assert non-empty before marking) |
| `data/span/` | `nse_fo_span_*.parquet/.zip` + `staging/nsccl_*.zip(.404)` + backfill logs | SPAN margin archives; staging `.404` = genuine missing days |

## 7. Reference + research artifacts

| Store | Contents |
|---|---|
| `data/reference/` | MCWB monthly zips + `BNF_2012-2023.csv.zip` / `NIFTY_2012-2023.csv.zip` + old instrument-master snapshot |
| `data/features/day_type/` | `day_type_facts.duckdb` + 53-feature CSVs (`nifty_day_features_YYYY.csv`, `intraday_features_{10am,11am,13pm}.csv`) + cluster artifacts |
| `data/features/n200_regime/` | `panel.duckdb` / `regime_panel{,_b}.duckdb` + `params{,_b}/fold_*.json` |
| `data/isd/pit_universe.duckdb` | `pit_membership` (173,900): session×symbol PIT (intraday_present, fno_member) + `baseline/2023-11-12.duckdb` |
| `data/a_index_intraday/` | `paper_trades.duckdb` + cost/certification JSONs |
| `data/mrlc_test/` | `candles/daily_ext/archive_candles.duckdb` + `paper/paper.duckdb` + trade CSVs |
| `data/se3/spread_collection.duckdb` | `spread_observations` (530): spread snapshots |
| `data/mto_probe/MTO_*.DAT` | 2,728 raw MTO delivery files |
| `data/analog_path/*.parquet`, `data/reliance_regime/`, `data/scratch/options_seller_edge/stock_straddles.parquet`, `data/audit/C2_*.csv` | Experiment outputs (parquet/CSV/JSON) |

## 8. Closed / safety / legacy / ephemeral

| Store | Disposition |
|---|---|
| `data/psb1_synthetic/` (3), `data/psb2_synthetic/` (11) | Closed batteries — fixtures only |
| `data/market_data/equity_bhavcopy_{mto_backfill,premto,devtruncated}.duckdb` | PSB build intermediates (closed) — archive candidates |
| `data/market_data/nse/candles/1d_snapshot_g1_r2/` (241) | G1-R2 copy-first baseline (closed, 0 code refs) |
| `data/_baselines/` + `1m_pre_fo_backfill/` (29) + `backups/` | Copy-first safety snapshots — keep per retention, never overwrite |
| `historical/index/` + `historical/index/1m/` (~1,251) | Legacy, superseded by `data/market_data/nse/candles` — re-point 6 refs, then archive |
| `cache/` (SPAN zips, NSE HTML/cookies), `data/tmp_duckdb/`, `logs/` | Ephemeral — safe to prune |
| `models/daytype/` (lgbm/logistic × checkpoints) | Model binaries + scalers + metadata |
| `tests/**/fixtures/*.duckdb` | Test fixtures — not production data |

## 9. Research Data Readiness: Price × Time × Cross-Market × Sentiment

> Verified 2026-09-12 by read-only sampling. "TRAIN/HOLDOUT-suitable" means usable for in-sample/out-of-sample research splits — not a gate verdict (RFA + pre-registration still required).

### The two 2012–2024 intraday symbols (verified)

`data/market_data/nse/candles/1m/2012-01-02.duckdb` → 749 rows, **2 symbols**: `NSE_INDEX|Nifty 50`, `NSE_INDEX|Nifty Bank`. Same pair on `2020-01-02` (750 rows, 375 bars/symbol, 09:16→15:30). Breadth starts **2023-01-02** (190 symbols: 188 `NSE_EQ` + 2 index), growing to 198 by 2025 — **not 2024-10-17**, and never 231. Verified by per-file `count(distinct symbol)` across 2022-12 → 2023-09 (the step is 2 → 190 at 2023-01-02) and by first-file-of-year scan (every first file 2012–2022 holds 2 symbols). Corroborated by `data/isd/pit_universe.duckdb:pit_membership` (898 sessions, 2023-01-02 → 2026-08-24). Any **2012 → 2022-12-30** intraday construct is therefore an **index-pair construct on Nifty 50 vs Nifty Bank** — no equity breadth, and no VIX at any date in that span (1m VIX begins 2024-11-29; see Sentiment).

### Price

| Field | Detail |
|---|---|
| Exact stores | `data/market_data/equity_bhavcopy.duckdb` (`equity_bhavcopy` 7.16M + `equity_bhavcopy_adjusted` VIEW + `adjustment_factors`/`corporate_actions`), `futures_bhavcopy.duckdb` (`futures_bhavcopy` 1.496M + `stock_futures_continuous` 49,711), `options_bhavcopy.duckdb` (`option_bhavcopy` 5.49M), `stock_options_bhavcopy.duckdb` (99.5M), `nse/candles/1m/{date}.duckdb`, `nse/candles/1d/{date}.duckdb`, `1m_vendor/{symbol}.duckdb` (provenance only), `live_buffer/{candles,ticks}_today.duckdb` (today only) |
| Instruments | Equities `NSE_EQ|<ISIN>` (~1,500 in 2010 → ~2,950 in 2026); indices `NSE_INDEX|Nifty 50`, `NSE_INDEX|Nifty Bank`, `NSE_INDEX|India VIX`; futures 380 underlyings (`NIFTY`/`BANKNIFTY` FUTIDX + FUTSTK); options `NIFTY` index + 366 stock underlyings × strikes |
| Coverage / frequency | Equity EOD daily 2010-01-04→; futures/options EOD 2016-02-11→ (index options stall 2026-07-17); 1m 2012-01-02→ (2-symbol index pair until 2022-12-30; ~190→198 symbols from 2023-01-02); ticks today-only |
| Timestamp semantics | 1m `timestamp` = bar open, IST-naive (verified 2020-01-02: 09:16→15:30, 375 bars/symbol; pre-CAS session 09:15–15:30). 1d `timestamp` = 00:00 naive. Ticks = event time. Post-CAS (≥2026-08-03) F&O names carry `is_synthetic=TRUE` 15:15–15:27 + one auction print |
| PIT availability | YES with discipline: `trading_calendar` session oracle + `symbol_entity_intervals` (recycled tickers) + `symbol_isin` + cumulative `adjustment_factors` applied causally (ex_date-gated); `pit_membership` 2023-01-02→; `fo_eligible_intervals` for futures. Continuous futures only 2022-08-08→2025-07-17 — no rolled series before 2022 |
| Missingness | 2018: 223 × 1m files vs ~246 expected; 35 missing 1m files vs calendar overall; index-options 45-day lag; `deliv_*` null on ~8% early rows; CAS synthetics must be filtered (`WHERE is_synthetic=FALSE`, NSE_EQ only — indices have volume 0 on every bar) |
| TRAIN/HOLDOUT | EOD equity panel (adjusted + PIT universe): **suitable**. Index-pair 1m (2 syms, 2012→): **suitable for index-level constructs only**. Breadth 1m (**2023-01-02→**, ~900 sessions): a split is **arithmetically possible** (ISD ran a 474-session TRAIN on it), but the window is **budget-constrained, not data-constrained** — see `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` §4; still ~1 macro regime. Options EOD: **suitable daily** (no intraday OI/IV history) |
| Leakage risks | Snapshot universes (`nifty200_current.csv`, `fo_stocks`) time-travel; dividends NOT price-adjusted (TR confusion); vendor-1m schema differs (`vendor_1m.ts` vs `candles`) and ends 2025-08-06 — never stitch silently; recycled tickers (DTIL) and ISIN re-issue (PHILIPCARB/PCBL) without interval linkage fabricate >20% returns |

### Time (sessions, calendar, clocks)

| Field | Detail |
|---|---|
| Exact stores | `equity_bhavcopy.duckdb:trading_calendar` (4,146 sessions 2010→, as of 2026-09-11; grows ~1/session) + `core/market/session_schedule.py` (date-keyed, segment-named; `CAS_EFFECTIVE 2026-08-03`) + `bhavcopy_raw/*.404` miss markers + `core/market/nse_holidays.py` |
| Coverage / frequency | Session-level daily (calendar) + 1m bar grid (09:15–15:30 pre-CAS; CAT1 09:15–15:15 + halt/auction to 15:29 post-CAS; derivatives to 15:40) |
| Timestamp semantics | As Price; LoopDriver `Clock` advances per bar with 90-day warmup; 1d files carry 1–165 rows (early years Nifty-only). **⚠ DUAL GRID (V1, found 2026-09-12): index 1m runs `09:16 → 15:30` for 2012-01-02 → 2022-12-30 (plus 2023-01-31, the reference-CSV bundle's last date) and `09:15 → 15:29` from 2023-01-02 for every symbol. In 2022 files the Upstox-backfilled VIX sits on the modern grid while Nifty 50 / Nifty Bank sit on the old one, so a `timestamp` join offsets them by one minute. Whether the pre-2023 slice is end-labelled is UNRESOLVED — the daily-close test does not discriminate. P2 certification item: `VIX_1M_INGEST_VERIFICATION_2026-09-12.md` §4 V1** |
| PIT availability | Calendar is a PIT-safe oracle; schedule resolves era **by rule** (date), never by detecting `volume=0` on indices |
| Missingness | Holiday absences are correct (cross-check `.404` + calendar); 2026-08-01 1m file missing; pre-2014 files have schema-validity quirks (no `instrument_key`) |
| TRAIN/HOLDOUT | **Suitable** — calendar + schedule are lookahead-free by construction |
| Leakage risks | Counting T-3 roll triggers off **stored** dates misses the live edge while expiry is in the future (count past last stored date from `nse_holidays.py`); resampling across the CAS boundary without the synthetic filter smears auction prints into indicators |

### Cross-Market

| Field | Detail |
|---|---|
| Exact stores | NSE index family in `nse/candles/1d/{date}.duckdb` (149 symbols on the latest file 2026-09-11; **up to 200 observed in 2026**, max at 2026-03-02 — the per-file count is the writer's universe that day, not the store's breadth); `data/market_data/bse/candles/1m/` (15 files) + `1d/` (8 files); `futures_bhavcopy.duckdb` FUTIDX (`NIFTY`, `BANKNIFTY` verified); `data/reference/mcwb_*.zip` (monthly weights) |
| Instruments | `NSE_INDEX|Nifty Bank / Nifty IT / sector + thematic` (1d only, 2016→); `BSE_INDEX|SENSEX` (single symbol, 2026-08-24→ only); NIFTY/BANKNIFTY futures. **Nothing else: no FX, commodities, bonds, or global indices** (MCX packet in `fetch_intermarket_data.py` unused) |
| Coverage / frequency | Cross-index **daily** 2016-02-11→; cross-index **intraday** = Nifty-vs-Bank 1m 2012→ (2-sym era) + SENSEX 1m 2026-08-24→ (3 weeks) |
| Timestamp semantics | Same bar-open IST-naive grid; BSE files share the `candles` schema incl. `is_synthetic` |
| PIT availability | Spot/futures joins are PIT-safe on `trade_date`; MCWB weights are monthly-PIT; sector-index membership is **not** PIT-tabled |
| Missingness | No sector 1m at any date; SENSEX history absent before 2026-08-24; Bank 1d starts 2015 (1 row/file before), VIX 1d 2015→ |
| TRAIN/HOLDOUT | Cross-index **daily** (2016→): **suitable**. Intraday cross-market: **only the Nifty/Bank pair is suitable**; SENSEX: **unsuitable** (3 weeks, no split) |
| Leakage risks | Legacy index names (`S&P CNX Nifty` → `CNX Nifty` → `Nifty 50`) — match by containment, hard-fail unmapped, never fall through to `f"NSE_INDEX|{raw}"`; assuming sector membership is static injects survivorship bias |

### Sentiment (no dedicated store — proxies only)

| Field | Detail |
|---|---|
| Exact stores | `NSE_INDEX|India VIX` (1d 2015→; canonical **1m 2022-01-03 → 2026-09-11, 1,165 sessions / 435,244 rows** — Upstox backfill via `fetch_upstox_historical.py`, `is_synthetic=FALSE` (correct by rule: indices are not CAS Category I). *(Supersedes the 2026-09-12 P1 reading of 117 sessions from 2024-11-29, which was measured before this ingest landed.)* **88 defect sessions** (2022-03-24 → 2026-03-04, 83 of them in 2022) carry trailing bars to 15:31/15:32; a further 3 Muhurat evening sessions are caught by the same broad filter and are **not** defects — see `VIX_1M_INGEST_VERIFICATION_2026-09-12.md`; a separate **uncertified, gitignored vendor CSV** `data/market_data/INDIA VIX_minute.csv` holds 938,695 rows / **2,515 of 2,518 calendar sessions, 2015-01-09 → 2025-03-05** — 99.99% value-exact against canonical over the 8,249-bar overlap, same timestamp convention, includes Muhurat sessions, but carries 2,547 invalid-OHLC rows in 2018–2019 and has no stated provenance: **never stitch into the canonical store**; see `docs/reports/index_research/VIX_1M_VENDOR_CSV_ASSESSMENT_2026-09-12.md`; `data/nifty_shield/vix_history.duckdb:vix_history` 3,040 rows 2014-05-14→2026-09-07); PCR/GEX **live-only** (`data/options/chain_cache.duckdb:option_chain_snapshot` 360 rows + `wall_scan_results.duckdb:session_regime` 9,845 + `wall_chain_snapshots/` 6 days; computed by `core/analytics/options_analytics.py`); `data/features/day_type/day_type_facts.duckdb` (845 rows 2023-01-02→: regime, confidence, `vix_pctile`); positioning proxies: `equity_bhavcopy.deliv_qty/deliv_pct` (**92.1% fill — 7.92% of rows null**; first non-null 2010-01-04) + `data/mto_probe/MTO_*.DAT` (2,728 raw) + options EOD `open_int/chg_in_oi` |
| Instruments | India VIX; NIFTY PCR (live chain); Nifty 50 regime labels; delivery % per equity symbol; strike-level OI (EOD) |
| Coverage / frequency | VIX daily 2014/2015→; PCR/GEX 5-sec snapshots **today + 6 recent days only**; regime labels daily 2023→; delivery/OI daily 2010/2016→ |
| Timestamp semantics | VIX EOD close + `vix_at_checkpoint` (10am/11am/13pm) in day-type facts; chain snapshots carry `snapshot_timestamp`; OI rows keyed to `trade_date` (no intraday OI) |
| PIT availability | VIX close and delivery/OI: **PIT-safe**. Regime labels: **NOT PIT-safe on reuse** (KMeans trained 2012–2023 — retrain per window). Live PCR: PIT only at the snapshot instant, no history to train on |
| Missingness | No historical PCR/IV/Greeks/bid-ask intraday (ticks `bid/ask` exist in schema, values NULL); no fear-greed/news/flows store |
| TRAIN/HOLDOUT | VIX daily + delivery/OI EOD: **suitable**. PCR/GEX intraday: **unsuitable** (no history). Regime labels: **suitable only retrained per window** |
| Leakage risks | Reusing 2012–2023-trained regime labels as "facts" leaks the training window into every backtest; VIX/indices volume is dissemination noise (never VWAP/vol_z on `NSE_INDEX`); treating EOD OI change as an intraday timing signal overstates executability |

## 10. How to use this map

- **New research:** start from §1 canonical tables + `symbol_entity_intervals` + PIT membership (`universe_membership` / `pit_membership`); never filter history by `nifty200_current.csv` or `fo_stocks`.
- **Intraday:** read `1m/{date}.duckdb` with `WHERE is_synthetic = FALSE` (NSE_EQ only; indices carry volume 0 on every bar).
- **Live/paper:** `live_buffer` (today) → `1m/{date}` (history); trades land in `data/trading/trading.db` or `data/nifty_shield/trading/trading.db`.
- **Before deleting anything:** consult `DATABASE_CENSUS_2026-09-03.md` §3–§5 — only `1d_snapshot_g1_r2`, empty duplicates, and closed-project fixtures are zero-risk.

---

## 11. §9 verification log (P1, 2026-09-12)

Every §9 claim was re-checked at **meta level** (schema, counts, min/max dates, file
presence — no OHLC entered any feature, label or fitted parameter; boundary ratified by
operator decision PTMS-2026-09-12 §1). Corrections are in the diff above; this table
records what was checked, including the claims that held.

| Claim | Verified value | Verdict |
|---|---|---|
| equity rows / span | 7,158,443 · 2010-01-04 → 2026-09-11 | **OK** (was "7.16M → present"; pinned) |
| `corporate_actions` / `adjustment_factors` | 11,965 / 1,194 | **OK** |
| `trading_calendar` | 4,146 sessions | **corrected** (was 4,138 — moving count, now stamped) |
| `symbol_entity_intervals` / `symbol_isin` | 4,133 / 3,639 | **OK** (not previously stated) |
| futures rows / span | 1,495,989 · 2016-02-11 → 2026-09-11 | **OK** |
| `stock_futures_continuous` | 49,711 · 2022-08-08 → 2025-07-17 | **OK** |
| `fo_eligible_intervals` | 9,092 | **OK** |
| index options | 5,490,319 · 2016-02-11 → **2026-07-17** | **OK** (the stall is real) |
| stock options | 99,485,464 · 2016-02-11 → 2026-09-11 | **OK** |
| instrument master | 1,467,444 rows | **OK** |
| NSE 1m files | 3,612 · 2012-01-02 → 2026-09-11 | **OK** |
| NSE 1m symbol breadth | 2 syms → 2022-12-30; **190 at 2023-01-02** → 198 | **CORRECTED** (was 2024-10-17 / 195–231) |
| NSE 1d files | 4,135 · 2010-01-04 → 2026-09-11 | **OK** |
| NSE 1d index breadth | 149 on latest file; **200 max in 2026** | **CORRECTED** (per-file ≠ store breadth) |
| BSE 1m / 1d files | 15 / 8, from 2026-08-24 | **OK** |
| vendor 1m files | 101 | **OK** |
| missing 1m files vs calendar | **35** (calendar 3,646 sessions ≥ 2012-01-02) | **OK** |
| 1m files with **no** calendar session | **1 — `2026-03-03`** | **new** (set difference run in both directions; 3,646 − 35 + 1 = 3,612 reconciles exactly to the file count). Recorded as a fact, not repaired — calendar changes are the operator's pre-freeze item |
| 2018 1m file count | **223** (23 of the 35 misses fall in 2018) | **OK** |
| `deliv_pct` fill | 7.92% null → **92.1% fill**, first non-null 2010-01-04 | **CORRECTED** (§9 Price said "~8% early rows null" — right; §9 Sentiment said "65% fill" — wrong; the two contradicted each other) |
| India VIX 1m | **2022-01-03 → 2026-09-11, 1,165 sessions, 435,244 rows** | **CORRECTED TWICE** — the map said "1m 2023-01-02→"; the first P1 pass measured 117 sessions from 2024-11-29; an Upstox backfill landed between the two readings. A count is only true as of its timestamp |
| `pit_membership` | 173,900 rows · 898 sessions · 2023-01-02 → 2026-08-24 | **OK** |

**Method note.** Reader enumeration for this map must use component-wise search, not path
literals: `grep -rl "candles/1m"` finds 9 readers of the 1m store while the component-wise
pattern finds 63, missing `scripts/build_intraday_features.py` entirely because the path is
assembled from parts. See `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` §2.
