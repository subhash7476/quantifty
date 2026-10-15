# Fresh Research Data Inventory — FINAL

**Date:** 2026-10-01
**Status:** READY_FOR_TRANSFER
**Scope:** Final inventory of `F:\Nifty\data\` for clean research repository

---

## Final Summary

| Category | Files | Size | Decision |
|----------|-------|------|----------|
| CANONICAL_SOURCE | 7,804 | 17.1 GB | TRANSFER |
| REQUIRED_METADATA | 2 | 412 MB | TRANSFER |
| RAW_SOURCE | 2,976 | 12 MB | TRANSFER |
| DEFERRED | 7,709 | 18.1 GB | DEFER |
| EXCLUDED | 15,206 | 26.6 GB | EXCLUDE |
| **Total** | **34,144** | **62.0 GB** | — |

---

## Transferable Data (TRANSFER)

### Canonical NSE Market Data

| Path | Files | Size | Date Range | Description |
|------|-------|------|------------|-------------|
| `market_data/nse/candles/1d/` | 4,147 | 4,573.8 MB | 2010-01-04 → 2026-09-30 | Daily OHLCV candles (adjusted) |
| `market_data/nse/candles/1m/` | 3,654 | 12,421.3 MB | 2012-01-02 → 2026-09-30 | 1-minute OHLCV candles (adjusted) |

### Required Raw NSE Source Data

| Path | Files | Size | Date Range | Description |
|------|-------|------|------------|-------------|
| `market_data/bhavcopy_raw/udiff_20240703.zip` | 1 | 164.1 KB | — | Incremental bhavcopy update |
| `market_data/bhavcopy_raw/udiff_20260901.zip` | 1 | 204.8 KB | — | Incremental bhavcopy update |
| `market_data/corporate_actions_raw/` | 2,965 | 11.1 MB | — | Raw corporate actions |
| `market_data/universe_raw/` | 3 | 0.3 MB | — | Raw universe membership |
| `market_data/vendor/niftyindices/` | 8 | 0.1 MB | — | Vendor index data |

### Required Metadata

| Path | Files | Size | Description |
|------|-------|------|-------------|
| `instruments/nse_fo_instruments.duckdb` | 1 | 410.8 MB | F&O instrument master (2.3M rows) |
| `cas/cas_category.duckdb` | 1 | 0.8 MB | CAS category classification (366 rows) |

### Options Data

| Path | Files | Size | Date Range | Description |
|------|-------|------|------------|-------------|
| `options/*.duckdb` | 9 | 234.2 MB | 2016-02-11 → 2026-07-20 | Options bhavcopy |

### Reference Data

| Path | Files | Size | Description |
|------|-------|------|-------------|
| `reference/mcwb_*.zip` | 198 | 1.2 MB | MCWB index membership/weight data |
| `reference/mcwb_manifest.json` | 1 | 0.1 MB | MCWB manifest |
| `reference/nifty50_constituents_current.csv` | 1 | 0.0 MB | Current Nifty 50 constituents |
| `reference/nifty50_pit_*.json` | 2 | 0.2 MB | Nifty 50 PIT membership and weights |
| `reference/nse_index_pr/` | 235 | 54.7 MB | NSE index PR files (official constituent lists) |
| `reference/BNF_2012-2023.csv.zip` | 1 | 12.2 MB | Bank Nifty historical data |
| `reference/NIFTY_2012-2023.csv.zip` | 1 | 10.8 MB | Nifty historical data |

**Transfer total:** 11,229 files, 17.32 GB

---

## Deferred Data (DEFER)

| Path | Files | Size | Reason |
|------|-------|------|-------|
| `market_data/nse/candles/1m_vendor/` | 102 | 3,163 MB | Historically research-consumed; cannot be fresh surface |
| `span/*.parquet` | ~310 | 10,489 MB | Economic/margin infrastructure; not needed for first-stage discovery |
| `span/*.zip` | ~320 | 2,796 MB | Same deferral as parquet |
| `market_data/bse/candles/` | 35 | 27 MB | Low-priority; not required for first clean laboratory |
| `options/wall_chain_snapshots/` | 19 | 945 MB | Low-priority; not required for first clean laboratory |
| `market_data/bhavcopy_raw/legacy_*.csv` | 4,179 | 134.8 MB | Unresolved raw CSV; preserve for forensic review |
| `market_data/bhavcopy_raw/secfull_*.csv` | 2,463 | 560.3 MB | Unresolved raw CSV; preserve for forensic review |
| `market_data/bhavcopy_raw/foudiff_*.csv` | 281 | 9.1 MB | Unresolved raw CSV; preserve for forensic review |

**Deferred total:** 7,709 files, 18.1 GB

---

## Excluded Data (EXCLUDE)

| Path | Files | Size | Reason |
|------|-------|------|-------|
| `market_data/nse/candles/1d_snapshot_g1_r2/` | 242 | 485 MB | Duplicate of canonical 1d |
| `market_data/nse/candles/1d_snapshots/` | 1 | 0.1 MB | Duplicate metadata |
| `span/staging/` | 320 | 2,797 MB | Temporary processing artifacts |
| `market_data/bhavcopy_raw/focal_*.404` | 1,697 | 0.0 MB | Zero-byte download-failure markers |
| `market_data/bhavcopy_raw/udiff_*.404` | 275 | 0.4 MB | Zero-byte download-failure markers |
| `trading/` | 4 | 0.1 MB | Operational state |
| `ops/` | 6 | 0.1 MB | Operational state |
| `live_buffer/` | 3 | 192 MB | Operational state |
| `paper/` | 3 | 2 MB | Operational state |
| `_baselines/` | 17 | 1,690 MB | Backup artifacts |
| `features/` | 28 | 136 MB | Derived research data |
| `isd/` | 11 | 5 MB | Old research-derived PIT panel |
| `a_index_intraday/` | 5 | 0.5 MB | Research output |
| `analog_path/` | 31 | 13 MB | Research output |
| `audit/` | 3 | 4 MB | Research output |
| `jev_market_state/` | 18 | 14 MB | Research output |
| `mrlc_test/` | 19 | 193 MB | Research output |
| `mto_probe/` | 2,728 | 149 MB | Research output |
| `nifty_shield/` | 8 | 9 MB | Research output |
| `nifty_shield/sessions/` | ~200 | ~100 MB | Research output |
| `nifty_shield_preflight/` | 4 | 0.1 MB | Research output |
| `reliance_regime/` | 5 | 0.4 MB | Research output |
| `research/` | 60 | 397 MB | Research output |
| `se3/` | 1 | 8 MB | Research output |
| `signal_engine/` | 14 | 2,992 MB | Research output |
| `psb1_synthetic/` | 3 | 16 MB | Test fixture |
| `psb2_synthetic/` | 11 | 26 MB | Test fixture |
| `scratch/` | 1 | 3 MB | Scratch data |
| `config/` | 2 | 0.1 MB | Configuration |

**Excluded total:** 15,206 files, 26.6 GB

---

## Data Quality Metadata (for transfer)

### Corporate Action Adjustment Status
- `market_data/nse/candles/1d/` — **ADJUSTED** (back-adjusted to current basis)
- `market_data/nse/candles/1m/` — **ADJUSTED** (back-adjusted to current basis)
- `market_data/bhavcopy_raw/` — **AS-TRADED** (not adjusted)
- `market_data/corporate_actions_raw/` — Raw CA data for adjustment calculations

### PIT/Entity Linkage
- `instruments/nse_fo_instruments.duckdb` — Contains instrument master with ISIN linkage
- `market_data/universe_raw/` — Contains universe membership data
- `reference/nifty50_pit_*.json` — Nifty 50 PIT membership and weights
- `reference/nse_index_pr/` — Official NSE constituent lists

### Timestamp/Session Semantics
- `market_data/nse/candles/1d/` — Daily timestamps (date only)
- `market_data/nse/candles/1m/` — 1-minute timestamps (intraday)
- `options/*.duckdb` — Daily timestamps

### Known Missingness
- `market_data/bhavcopy_raw/` — Contains `.404` markers for failed downloads (excluded)
- `market_data/nse/candles/1d/` — 16 sessions absent (Saturday specials, Diwali Muhurat)
- `market_data/nse/candles/1m/` — Some F&O names absent on certain sessions

### Coverage Dates
- `market_data/nse/candles/1d/` — 2010-01-04 → 2026-09-30
- `market_data/nse/candles/1m/` — 2012-01-02 → 2026-09-30
- `market_data/bhavcopy_raw/` — 2010-01-01 → 2026-09-30
- `options/` — 2016-02-11 → 2026-07-20

---

## Key Database Schemas (transferable)

### instruments/nse_fo_instruments.duckdb
- **Table:** `instruments` — 2,328,917 rows, 11 columns
- **Date range:** 2026-06-08 to 2026-10-01

### cas/cas_category.duckdb
- **Table:** `cas_category` — 366 rows, 3 columns

### market_data/nse/candles/1d/2026-09-30.duckdb
- **Table:** `candles` — 146 rows, 9 columns

### market_data/nse/candles/1m/2026-09-30.duckdb
- **Table:** `candles` — 86,625 rows, 10 columns

---

## Explicit Statements

- **No files were copied.**
- **No files were modified.**
- **No files were deleted.**
- **Old research history was not used** to make classification decisions.
- **This is a planning inventory only.** No action has been taken.
- **No Git repository has been initialized.**
- **No new folders have been created.**
- **No research has been performed.**
