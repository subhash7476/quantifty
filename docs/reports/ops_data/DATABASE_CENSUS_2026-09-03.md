# DuckDB Store Census — Active vs Redundant

**Date:** 2026-09-03 · **Scope:** every `*.duckdb` under the repo root · **Method:** filesystem enumeration (count/size/mtime) cross-referenced against `*.py` code references in `scripts/ core/ flask_app/ strategies/ app_facade/`.

## 1. Headline

| Metric | Value |
|---|---|
| Total `.duckdb` files | **9,452** |
| Total on disk | **45.27 GB** |
| Distinct **logical** stores (partitions rolled up) | ~40 |
| Actively written / read by the platform | **~24 logical stores** |
| Redundant / archival / orphaned | **~16 logical stores, ≈ 9.2 GB reclaimable** |

Most of the 9,452 files are **per-date partitions** of a few logical stores (1m candles = 3,605 files, 1d candles = 4,128, legacy `historical/index` = 1,251, vendor/snapshot copies = 342). Counting *logical* stores is the meaningful number.

## 2. Active stores (keep)

| Store (path) | Files | Size | Last write | Role / writer |
|---|---|--:|---|---|
| `data/live_buffer/candles_today.duckdb` | 1 | 3.8 GB | 09-03 | Live 1m buffer (ingestor) — the source the 13:00 fact reads |
| `data/live_buffer/ticks_today.duckdb` | 1 | 9.5 GB | 09-03 | Live raw ticks (ingestor) — **see §4, bloated** |
| `data/market_data/nse/candles/1m/{date}` | 3,605 | 10.2 GB | 09-02 | Per-date 1m EOD candle store (primary) |
| `data/market_data/nse/candles/1d/{date}` | 4,128 | 4.5 GB | 09-02 | Per-date daily intermarket store |
| `data/market_data/bse/candles/{1m,1d}` | 16 | 12 MB | 09-03 | Sensex/BSE candles (options_wall D2) |
| `data/market_data/stock_options_bhavcopy.duckdb` | 1 | 6.1 GB | 09-03 | OPTSTK bhavcopy (98M rows) |
| `data/market_data/equity_bhavcopy.duckdb` | 1 | 693 MB | 09-03 | Equity bhavcopy (live) |
| `data/market_data/options_bhavcopy.duckdb` | 1 | 290 MB | 07-20 | Index options bhavcopy |
| `data/market_data/futures_bhavcopy.duckdb` | 1 | 121 MB | 09-03 | FUTSTK/FUTIDX bhavcopy |
| `data/instruments/nse_fo_instruments.duckdb` | 1 | 240 MB | 09-03 | Instrument master (canonical) |
| `data/features/day_type/day_type_facts.duckdb` | 1 | 2.3 MB | 08-31 | DayType 13:00 facts (the fix's output target) |
| `data/nifty_shield/facts.duckdb` + `sessions/{date}/` | ~30 | 45 MB | 09-03 | NiftyShield paper session artifacts (audit trail) |
| `data/options/wall_scan_results.duckdb` + chain cache | 2 | 118 MB | 09-03 | options_wall scan results / chain (3 code refs) |
| `data/signal_engine/carry/*` (production, weekly_signals, facts, signals, nifty50) | 5 | 34 MB | 09-03 | Carry sleeve — production-ready |
| `data/signal_engine/ts_basis_daily/{ts_signals,ts_facts}.duckdb` | 2 | 90 MB | 09-03 | TS Basis Daily (research-only, active) |
| `data/signal_engine/trend/continuous.duckdb` | 1 | 308 MB | 09-03 | Continuous futures series (6 code refs, freshly written) |
| `data/signal_engine/trade_intelligence/trade_intelligence.duckdb` | 1 | 293 MB | 09-03 | Trade-intelligence store (8 code refs, MRLC) |
| `data/mrlc_test/{daily_ext,archive_candles,candles}.duckdb` + `paper/paper.duckdb` | 4 | 208 MB | 08-31→09-03 | MRLC-testing branch working data (current work) |
| `data/cas/cas_category.duckdb` | 1 | 0.5 MB | 08-30 | CAS PIT category (Category I/II) |
| `data/a_index_intraday/*.duckdb` | 1 | 0.5 MB | 08-28 | A-INDEX-INTRADAY RFA candidate |
| `data/isd/*` | 2 | 4 MB | 08-26 | ISD straddle baseline |

## 3. Redundant / archival / orphaned (candidates to remove or archive)

| Store (path) | Files | Size | Why redundant |
|---|---|--:|---|
| `historical/index/` + `historical/index/1m/` | 1,251 | **4.23 GB** | Legacy index history, last written Feb 2026; superseded by `data/market_data/nse/candles`. Only 6 legacy code refs — none on the live path. |
| `data/market_data/nse/candles/1m_vendor/` | 101 | **3.16 GB** | Vendor 1m copy for the CARRY G1 Gate-B1 tick-verification; that gate is **closed** (max diff 0.0000). 2 code refs (the verification scripts). Provenance-only. |
| `data/market_data/equity_bhavcopy_mto_backfill.duckdb` | 1 | 641 MB | PSB substrate build intermediate (Jul 18). PSB CLOSED. |
| `data/market_data/equity_bhavcopy_premto.duckdb` | 1 | 620 MB | PSB substrate build intermediate (Jul 17). PSB CLOSED. |
| `data/market_data/nse/candles/1d_snapshot_g1_r2/` | 241 | 485 MB | One-time copy-first baseline from the G1-R2 re-ingest. **0 code refs.** G1 closed. |
| `data/market_data/equity_bhavcopy_devtruncated.duckdb` | 1 | 159 MB | Dev-truncated equity slice (Jul 12). PSB CLOSED. |
| `data/psb2_synthetic/` | 11 | 26 MB | Synthetic fixtures for PSB-2 (**CLOSED** 2026-07-17). |
| `reference/instrument_master/latest/*.duckdb` | 1 | 20 MB | Old instrument master (May 12); superseded by `data/instruments/`. |
| `data/psb1_synthetic/` | 3 | 16 MB | Synthetic fixtures for PSB-1 (**CLOSED** 2026-07-14). |
| `data/se3/spread_collection.duckdb` | 1 | 7.5 MB | Near-orphaned experiment (Aug 7, 1 code ref). |
| `.claude/worktrees/*/tests/**` fixtures | ~7 | ~11 MB | Duplicated test DBs inside 5 stale git worktrees (see §4). |
| `data/signal_engine/{skew,ivol,lag}/signals.duckdb` + `trend/signals.duckdb` | 4 | 11 MB | Dead-sleeve remnants — Skew/LAG TRAIN FAIL, IVOL SEALED FAIL (per CLAUDE.md). `trend/continuous.duckdb` is separate and active. |
| `data/_baselines/carry_signals_20260829_091650.duckdb` | 1 | 4.8 MB | Timestamped baseline snapshot of carry signals. |
| `backups/recover_2026-08-19_.../` | 1 | 1.5 MB | One-off recovery backup (Aug 19). |
| `data/market_data/nse_fo_instruments.duckdb` | 1 | **0 bytes** | Empty dead duplicate of `data/instruments/nse_fo_instruments.duckdb`. |
| `data/signal_engine/ts_basis/{ts_facts,ts_signals}.duckdb` | 2 | 14 MB | Monthly TS Basis (Aug); superseded by ts_basis_daily + de-authorized sealed read. Archival. |

**Reclaimable ≈ 9.2 GB** (dominated by `historical/index` 4.2 GB + `1m_vendor` 3.2 GB + the three `equity_bhavcopy_*` variants 1.4 GB).

## 4. Flagged — needs an operator decision (not auto-classified)

- **`data/live_buffer/ticks_today.duckdb` = 9.5 GB.** A per-session raw-tick buffer should reset daily; 9.5 GB implies it is **accumulating across sessions rather than rotating**. Biggest single file in the repo. Confirm the reset/rotation policy — this alone is ~21% of total footprint. (`candles_today.duckdb` at 3.8 GB likely the same pattern to a lesser degree.)
- **5 stale git worktrees** (`git worktree list`): `basis-momentum-decision-607d29`, `daily-signals-options-67f7ec`, `signal-failure-analysis-66468d`, `wonderful-perlman-ecb414`, `wonderful-shirley-a33c41`. Each carries its own test-fixture DBs and a full working copy. If the associated work is landed/abandoned, `git worktree remove` reclaims them.
- **`historical/index/`** retains 6 legacy code references. Confirm none is on a live ingest/backtest path before deleting (it appears fully superseded by the candles store, but the refs should be re-pointed or the scripts retired first).

## 5. Recommendation

1. **Safe to delete now (0 code refs / empty / closed-project):** `1d_snapshot_g1_r2` (485 MB), `data/market_data/nse_fo_instruments.duckdb` (empty), `psb1_synthetic` + `psb2_synthetic` (42 MB), `_baselines` + `backups` snapshots. ≈ **530 MB**, zero risk.
2. **Archive off-repo then delete (provenance, closed gates):** `1m_vendor` (3.2 GB), `equity_bhavcopy_{mto_backfill,premto,devtruncated}` (1.4 GB), `historical/index` (4.2 GB after re-pointing the 6 refs). ≈ **8.8 GB**.
3. **Investigate rotation:** `live_buffer/ticks_today.duckdb` (9.5 GB) — fix the reset policy rather than delete.
4. **Prune stale worktrees** once their branches are merged/abandoned.

_Counts and sizes are a point-in-time snapshot (2026-09-03 evening, post-session). Per-date partition counts drift by one file per trading day._
