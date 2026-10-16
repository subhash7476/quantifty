# Fresh Research Data Inventory

**Date:** 2026-10-01
**Scope:** Complete inventory of `F:\Nifty\data\` tree
**Purpose:** Identify canonical data vs research artifacts for a clean research-only repository

---

## Summary

| Category | Size | Files |
|----------|------|-------|
| CANONICAL_SOURCE | ~35.5 GB | ~19,000 |
| REQUIRED_METADATA | ~412 MB | 2 |
| RAW_SOURCE | ~716 MB | ~8,900 |
| DERIVED_DATA | ~136 MB | 28 |
| RESEARCH_ARTIFACT | ~1.2 GB | ~3,100 |
| OPERATIONAL_STATE | ~193 MB | 16 |
| CACHE/TEMP | ~2.8 GB | 322 |
| BACKUP | ~1.7 GB | 17 |
| TEST_FIXTURE | ~42 MB | 14 |
| DUPLICATE/REDUNDANT | ~485 MB | 242 |
| UNKNOWN | ~0.5 MB | 10 |

**Total:** ~62.0 GB across 27,144 files

---

## Directory-by-Directory Classification

### market_data/ — CANONICAL_SOURCE + RAW_SOURCE

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `nse/candles/1d/` | CANONICAL_SOURCE | 4,574 MB | 4,147 | Daily OHLCV candles, 2010-01-04 → 2026-09-30. Per-date DuckDB files. |
| `nse/candles/1m/` | CANONICAL_SOURCE | 12,421 MB | 3,654 | 1-minute OHLCV candles, 2012-01-02 → 2026-09-30. Per-date DuckDB files. |
| `nse/candles/1m_vendor/` | CANONICAL_SOURCE | 3,163 MB | 102 | Vendor 1m data (Upstox historical). |
| `nse/candles/1d_snapshot_g1_r2/` | DUPLICATE/REDUNDANT | 485 MB | 241 | Snapshot copies of 1d candles. Redundant with `1d/`. |
| `nse/candles/1d_snapshots/` | DUPLICATE/REDUNDANT | 0.1 MB | 1 | Snapshot metadata. |
| `bhavcopy_raw/` | RAW_SOURCE | 705 MB | 8,895 | Raw NSE bhavcopy files (equity, futures, options). Includes `.404` markers. |
| `corporate_actions_raw/` | RAW_SOURCE | 11 MB | 2,965 | Raw corporate actions data. |
| `universe_raw/` | RAW_SOURCE | 0.3 MB | 3 | Raw universe membership files. |
| `bse/candles/1d/` | CANONICAL_SOURCE | 6 MB | 8 | BSE daily candles. |
| `bse/candles/1m/` | CANONICAL_SOURCE | 21 MB | 27 | BSE 1-minute candles. |
| `vendor/niftyindices/` | RAW_SOURCE | 0.1 MB | 8 | Vendor index data (niftyindices.com). |

### instruments/ — REQUIRED_METADATA

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `nse_fo_instruments.duckdb` | REQUIRED_METADATA | 411 MB | 1 | F&O instrument master. 2,328,917 rows, 11 cols. |

### cas/ — REQUIRED_METADATA

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `cas_category.duckdb` | REQUIRED_METADATA | 0.8 MB | 1 | CAS category classification. 366 rows, 3 cols. |

### span/ — CANONICAL_SOURCE

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `span/*.parquet` | CANONICAL_SOURCE | ~10,489 MB | ~310 | SPAN risk parameter files (parquet format). |
| `span/*.zip` | CANONICAL_SOURCE | ~2,796 MB | ~320 | SPAN risk parameter files (zip format). |
| `span/staging/` | CACHE/TEMP | 2,797 MB | 320 | SPAR staging area (parquet + zip). |

### options/ — CANONICAL_SOURCE

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `options/*.duckdb` | CANONICAL_SOURCE | 234 MB | 9 | Options bhavcopy data. |
| `options/wall_chain_snapshots/` | CANONICAL_SOURCE | 945 MB | 19 | Option chain snapshots (Upstox V3). |

### reference/ — CANONICAL_SOURCE

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `reference/nse_index_pr/` | CANONICAL_SOURCE | 55 MB | 235 | NSE index PR files. |
| `reference/` (other) | CANONICAL_SOURCE | 24 MB | 204 | Other reference data. |

### trading/ — OPERATIONAL_STATE

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `trading/paper.duckdb` | OPERATIONAL_STATE | — | — | Paper trading state. |
| `trading/production.duckdb` | OPERATIONAL_STATE | — | — | Production trading state. |
| `trading/` (other) | OPERATIONAL_STATE | 0.1 MB | 4 | Trading metadata. |

### ops/ — OPERATIONAL_STATE

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `ops/` (all) | OPERATIONAL_STATE | 0.1 MB | 6 | Ops state files (PIDs, logs, JSON state). |

### live_buffer/ — OPERATIONAL_STATE

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `live_buffer/market_data.duckdb` | OPERATIONAL_STATE | 192 MB | 3 | Live market data buffer. |

### paper/ — OPERATIONAL_STATE

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `paper/ts_daily_combo/` | OPERATIONAL_STATE | 2 MB | 3 | Paper trading state for TS Basis Daily combo. |

### _baselines/ — BACKUP

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `_baselines/` (all) | BACKUP | 1,690 MB | 17 | Baseline snapshots before data repairs. |

### features/ — DERIVED_DATA

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `features/day_type/` | DERIVED_DATA | 14 MB | 25 | DayType feature data. |
| `features/n200_regime/` | DERIVED_DATA | 122 MB | 3 | N200 regime features. |
| `features/n200_regime/params/` | DERIVED_DATA | 0.0 MB | 10 | N200 regime parameters. |
| `features/n200_regime/params_b/` | DERIVED_DATA | 0.0 MB | 10 | N200 regime parameters (backup). |

### Research Artifact Directories — RESEARCH_ARTIFACT

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `a_index_intraday/` | RESEARCH_ARTIFACT | 0.5 MB | 5 | A-index intraday research data. |
| `analog_path/` | RESEARCH_ARTIFACT | 13 MB | 31 | Analog path research data. |
| `audit/` | RESEARCH_ARTIFACT | 4 MB | 3 | Audit data. |
| `isd/` | RESEARCH_ARTIFACT | 5 MB | 11 | ISD research data. |
| `jev_market_state/` | RESEARCH_ARTIFACT | 14 MB | 18 | JEV market state research data. |
| `mrlc_test/` | RESEARCH_ARTIFACT | 193 MB | 19 | MRLC test data. |
| `mto_probe/` | RESEARCH_ARTIFACT | 149 MB | 2,728 | MTO probe data. |
| `nifty_shield/` | RESEARCH_ARTIFACT | 9 MB | 8 | NiftyShield research data. |
| `nifty_shield/sessions/` | RESEARCH_ARTIFACT | ~100 MB | ~200 | NiftyShield session data. |
| `nifty_shield_preflight/` | RESEARCH_ARTIFACT | 0.1 MB | 4 | NiftyShield preflight data. |
| `reliance_regime/` | RESEARCH_ARTIFACT | 0.4 MB | 5 | Reliance regime research data. |
| `research/` | RESEARCH_ARTIFACT | 397 MB | 60 | Research data (breakout_volume, m4a_compress, straddle_m10, vwap_extreme_reversion). |
| `se3/` | RESEARCH_ARTIFACT | 8 MB | 1 | SE3 research data. |
| `signal_engine/` | RESEARCH_ARTIFACT | 2,992 MB | 14 | Signal engine data (carry, ivol, lag, skew, trade_intelligence, trend, ts_basis, ts_basis_daily). |

### Test Fixtures — TEST_FIXTURE

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `psb1_synthetic/` | TEST_FIXTURE | 16 MB | 3 | PSB1 synthetic test data. |
| `psb2_synthetic/` | TEST_FIXTURE | 26 MB | 11 | PSB2 synthetic test data. |

### Scratch — CACHE/TEMP

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `scratch/` | CACHE/TEMP | 3 MB | 1 | Scratch data. |
| `scratch/options_seller_edge/` | CACHE/TEMP | 9 MB | 1 | Options seller edge scratch data. |

### Config — OPERATIONAL_STATE

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `config/` | OPERATIONAL_STATE | 0.1 MB | 2 | Configuration files. |

### Root Data Files — OPERATIONAL_STATE

| Path | Type | Size | Files | Description |
|------|------|------|-------|-------------|
| `data/*.json` | OPERATIONAL_STATE | 1.2 MB | 10 | Root-level JSON state files. |

---

## Key Database Schemas

### instruments/nse_fo_instruments.duckdb
- **Table:** `instruments` — 2,328,917 rows, 11 columns
- **Date range:** 2026-06-08 to 2026-10-01
- **Type:** REQUIRED_METADATA

### cas/cas_category.duckdb
- **Table:** `cas_category` — 366 rows, 3 columns
- **Type:** REQUIRED_METADATA

### options/wall_chain_snapshots/2026-09-30.duckdb
- **Table:** `option_chain_snapshot` — 1,969,340 rows, 27 columns
- **Table:** `option_chain_snapshot_far` — 136,080 rows, 27 columns
- **Date range:** 2026-09-30 09:15 to 15:40
- **Type:** CANONICAL_SOURCE

### market_data/nse/candles/1d/2026-09-30.duckdb
- **Table:** `candles` — 146 rows, 9 columns
- **Type:** CANONICAL_SOURCE

### market_data/nse/candles/1m/2026-09-30.duckdb
- **Table:** `candles` — 86,625 rows, 10 columns
- **Type:** CANONICAL_SOURCE

---

## Data Quality Metadata

### Corporate Action Adjustment Status
- `market_data/nse/candles/1d/` — **ADJUSTED** (back-adjusted to current basis)
- `market_data/nse/candles/1m/` — **ADJUSTED** (back-adjusted to current basis)
- `market_data/bhavcopy_raw/` — **AS-TRADED** (not adjusted)
- `market_data/corporate_actions_raw/` — Raw CA data for adjustment calculations

### PIT/Entity Linkage
- `instruments/nse_fo_instruments.duckdb` — Contains instrument master with ISIN linkage
- `market_data/universe_raw/` — Contains universe membership data

### Timestamp/Session Semantics
- `market_data/nse/candles/1d/` — Daily timestamps (date only)
- `market_data/nse/candles/1m/` — 1-minute timestamps (intraday)
- `options/wall_chain_snapshots/` — Microsecond timestamps (intraday)

### Known Missingness
- `market_data/bhavcopy_raw/` — Contains `.404` markers for failed downloads
- `market_data/nse/candles/1d/` — 16 sessions absent (Saturday specials, Diwali Muhurat)
- `market_data/nse/candles/1m/` — Some F&O names absent on certain sessions

### Coverage Dates
- `market_data/nse/candles/1d/` — 2010-01-04 → 2026-09-30
- `market_data/nse/candles/1m/` — 2012-01-02 → 2026-09-30
- `market_data/bhavcopy_raw/` — 2010-01-01 → 2026-09-30
- `span/` — 2025-06-19 → 2026-09-30
- `options/` — 2016-02-11 → 2026-07-20

---

## Notes

1. **No data was modified.** This is a read-only inventory.
2. **No research reports were read.** Classification is based on directory structure and database schemas only.
3. **Duplicate detection** is based on directory naming and schema comparison. Hash-based comparison was not performed for all files due to size.
4. **REVIEW items** are flagged where classification is uncertain.
