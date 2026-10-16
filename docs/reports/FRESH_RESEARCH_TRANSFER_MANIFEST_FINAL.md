# Fresh Research Transfer Manifest — FINAL

**Date:** 2026-10-01
**Status:** READY_FOR_TRANSFER
**Source:** `F:\Nifty\data\`
**Target:** Clean research-only repository (not yet created)

---

## Final Transfer Summary

| Decision | Files | Size |
|----------|-------|------|
| TRANSFER | 11,229 | 17.32 GB |
| DEFER | 7,709 | 18.1 GB |
| EXCLUDE | 15,206 | 26.6 GB |
| **Total** | **34,144** | **62.0 GB** |

---

## Final Transfer Manifest

| PATH | CLASS | DECISION | REASON | STATUS | SIZE |
|------|-------|----------|---------|--------|------|
| `market_data/nse/candles/1d/` | CANONICAL_SOURCE | TRANSFER | Core daily OHLCV data for NSE equities and indices. 2010→2026. Required for mechanism discovery. | READY | 4,573.8 MB |
| `market_data/nse/candles/1m/` | CANONICAL_SOURCE | TRANSFER | Core 1-minute OHLCV data for NSE equities and indices. 2012→2026. Required for mechanism discovery. | READY | 12,421.3 MB |
| `market_data/bhavcopy_raw/udiff_20240703.zip` | RAW_SOURCE | TRANSFER | Incremental bhavcopy update. Raw source data. | READY | 164.1 KB |
| `market_data/bhavcopy_raw/udiff_20260901.zip` | RAW_SOURCE | TRANSFER | Incremental bhavcopy update. Raw source data. | READY | 204.8 KB |
| `market_data/bhavcopy_raw/focal_*.404` | CACHE/TEMP | EXCLUDE | Zero-byte download-failure markers. Not market data. | EXCLUDED | 0.0 MB |
| `market_data/bhavcopy_raw/udiff_*.404` | CACHE/TEMP | EXCLUDE | Zero-byte download-failure markers. Not market data. | EXCLUDED | 0.4 MB |
| `market_data/bhavcopy_raw/legacy_*.csv` | RAW_SOURCE | DEFER | Unresolved raw CSV group. Preserve for possible later forensic review. | DEFERRED_RAW_SOURCE | 134.8 MB |
| `market_data/bhavcopy_raw/secfull_*.csv` | RAW_SOURCE | DEFER | Unresolved raw CSV group. Preserve for possible later forensic review. | DEFERRED_RAW_SOURCE | 560.3 MB |
| `market_data/bhavcopy_raw/foudiff_*.csv` | RAW_SOURCE | DEFER | Unresolved raw CSV group. Preserve for possible later forensic review. | DEFERRED_RAW_SOURCE | 9.1 MB |
| `market_data/corporate_actions_raw/` | RAW_SOURCE | TRANSFER | Raw corporate actions data. Required for CA adjustment validation. | READY | 11.1 MB |
| `market_data/universe_raw/` | RAW_SOURCE | TRANSFER | Raw universe membership files. Required for PIT universe reconstruction. | READY | 0.3 MB |
| `market_data/vendor/niftyindices/` | RAW_SOURCE | TRANSFER | Vendor index data from niftyindices.com. Needed for validation. | READY | 0.1 MB |
| `market_data/nse/candles/1m_vendor/` | CANONICAL_SOURCE | DEFER | Vendor bundle historically research-consumed. Cannot be treated as fresh research surface. | DEFERRED | 3,163 MB |
| `market_data/nse/candles/1d_snapshot_g1_r2/` | DUPLICATE/REDUNDANT | EXCLUDE | Snapshot copies of 1d candles. Redundant with `1d/`. | EXCLUDED | 485 MB |
| `market_data/nse/candles/1d_snapshots/` | DUPLICATE/REDUNDANT | EXCLUDE | Snapshot metadata. Redundant. | EXCLUDED | 0.1 MB |
| `market_data/bse/candles/` | CANONICAL_SOURCE | DEFER | Low-priority dataset. Not required for first clean research laboratory. | DEFERRED | 27 MB |
| `instruments/nse_fo_instruments.duckdb` | REQUIRED_METADATA | TRANSFER | F&O instrument master. Required for symbol resolution and PIT linkage. | READY | 410.8 MB |
| `cas/cas_category.duckdb` | REQUIRED_METADATA | TRANSFER | CAS category classification. Required for CAS-era filtering. | READY | 0.8 MB |
| `span/*.parquet` | CANONICAL_SOURCE | DEFER | SPAN risk parameters. Economic/margin infrastructure, not required for first-stage mechanism discovery. | DEFERRED | 10,489 MB |
| `span/*.zip` | CANONICAL_SOURCE | DEFER | SPAN risk parameters (zip format). Same deferral as parquet. | DEFERRED | 2,796 MB |
| `span/staging/` | CACHE/TEMP | EXCLUDE | SPAN staging area. Temporary processing artifacts. | EXCLUDED | 2,797 MB |
| `options/*.duckdb` | CANONICAL_SOURCE | TRANSFER | Options bhavcopy data. Needed for options research. | READY | 234.2 MB |
| `options/wall_chain_snapshots/` | CANONICAL_SOURCE | DEFER | Low-priority dataset. Not required for first clean research laboratory. | DEFERRED | 945 MB |
| `reference/mcwb_*.zip` | REQUIRED_METADATA | TRANSFER | MCWB index membership/weight data. Required for index research. | READY | 1.2 MB |
| `reference/mcwb_manifest.json` | REQUIRED_METADATA | TRANSFER | MCWB manifest. Required for index research. | READY | 0.1 MB |
| `reference/nifty50_constituents_current.csv` | REQUIRED_METADATA | TRANSFER | Current Nifty 50 constituents. Required for index research. | READY | 0.0 MB |
| `reference/nifty50_pit_*.json` | REQUIRED_METADATA | TRANSFER | Nifty 50 PIT membership and weights. Required for index research. | READY | 0.2 MB |
| `reference/nse_index_pr/` | REQUIRED_METADATA | TRANSFER | NSE index PR files (official constituent lists). Required for index research. | READY | 54.7 MB |
| `reference/BNF_2012-2023.csv.zip` | CANONICAL_SOURCE | TRANSFER | Bank Nifty historical data. Required for index research. | READY | 12.2 MB |
| `reference/NIFTY_2012-2023.csv.zip` | CANONICAL_SOURCE | TRANSFER | Nifty historical data. Required for index research. | READY | 10.8 MB |
| `trading/` | OPERATIONAL_STATE | EXCLUDE | Trading state. Not research data. | EXCLUDED | 0.1 MB |
| `ops/` | OPERATIONAL_STATE | EXCLUDE | Ops state files. Not research data. | EXCLUDED | 0.1 MB |
| `live_buffer/` | OPERATIONAL_STATE | EXCLUDE | Live market data buffer. Not research data. | EXCLUDED | 192 MB |
| `paper/` | OPERATIONAL_STATE | EXCLUDE | Paper trading state. Not research data. | EXCLUDED | 2 MB |
| `_baselines/` | BACKUP | EXCLUDE | Baseline snapshots. Backup artifacts. | EXCLUDED | 1,690 MB |
| `features/` | DERIVED_DATA | EXCLUDE | Derived research features. Not canonical source. | EXCLUDED | 136 MB |
| `isd/` | RESEARCH_ARTIFACT | EXCLUDE | Old research-derived PIT/feature panel. Not transferred per instruction. | EXCLUDED | 5 MB |
| `a_index_intraday/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 0.5 MB |
| `analog_path/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 13 MB |
| `audit/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 4 MB |
| `jev_market_state/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 14 MB |
| `mrlc_test/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 193 MB |
| `mto_probe/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 149 MB |
| `nifty_shield/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 9 MB |
| `nifty_shield/sessions/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | ~100 MB |
| `nifty_shield_preflight/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 0.1 MB |
| `reliance_regime/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 0.4 MB |
| `research/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 397 MB |
| `se3/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 8 MB |
| `signal_engine/` | RESEARCH_ARTIFACT | EXCLUDE | Research output. | EXCLUDED | 2,992 MB |
| `psb1_synthetic/` | TEST_FIXTURE | EXCLUDE | Synthetic test data. | EXCLUDED | 16 MB |
| `psb2_synthetic/` | TEST_FIXTURE | EXCLUDE | Synthetic test data. | EXCLUDED | 26 MB |
| `scratch/` | CACHE/TEMP | EXCLUDE | Scratch data. | EXCLUDED | 3 MB |
| `config/` | OPERATIONAL_STATE | EXCLUDE | Configuration files. | EXCLUDED | 0.1 MB |

---

## Proposed Final Transfer Tree

```
research-data/
├── market_data/
│   ├── nse/
│   │   ├── candles/
│   │   │   ├── 1d/              # 4,147 files, 4.5 GB — TRANSFER
│   │   │   └── 1m/              # 3,654 files, 12.4 GB — TRANSFER
│   │   └── bhavcopy_raw/
│   │       ├── udiff_20240703.zip  # 164 KB — TRANSFER
│   │       └── udiff_20260901.zip  # 205 KB — TRANSFER
│   ├── corporate_actions_raw/   # 2,965 files, 11.1 MB — TRANSFER
│   ├── universe_raw/            # 3 files, 0.3 MB — TRANSFER
│   └── vendor/
│       └── niftyindices/        # 8 files, 0.1 MB — TRANSFER
├── instruments/
│   └── nse_fo_instruments.duckdb  # 410.8 MB — TRANSFER
├── cas/
│   └── cas_category.duckdb       # 0.8 MB — TRANSFER
├── options/
│   └── *.duckdb                 # 9 files, 234.2 MB — TRANSFER
└── reference/
    ├── mcwb_*.zip               # 198 files, 1.2 MB — TRANSFER
    ├── mcwb_manifest.json       # 1 file, 0.1 MB — TRANSFER
    ├── nifty50_constituents_current.csv  # 1 file, 0.0 MB — TRANSFER
    ├── nifty50_pit_*.json       # 2 files, 0.2 MB — TRANSFER
    ├── nse_index_pr/            # 235 files, 54.7 MB — TRANSFER
    ├── BNF_2012-2023.csv.zip    # 1 file, 12.2 MB — TRANSFER
    └── NIFTY_2012-2023.csv.zip  # 1 file, 10.8 MB — TRANSFER
```

**Final transfer size:** 17.32 GB (11,229 files)
**Deferred size:** 18.1 GB (7,709 files)
**Excluded size:** 26.6 GB (15,206 files)

---

## Metadata Files to Eventually Create (NOT YET CREATED)

The following metadata/documentation files should be created in the new repository to describe objective data semantics. **These are listed for planning only and have NOT been created.**

| File | Purpose |
|------|---------|
| `README.md` | Repository overview and data semantics |
| `DATA_DICTIONARY.md` | Column definitions, data types, and semantics for each dataset |
| `COVERAGE.md` | Date ranges, symbol counts, and known gaps for each dataset |
| `CORPORATE_ACTIONS.md` | CA adjustment status and methodology |
| `TIMESTAMP_SEMANTICS.md` | Timestamp conventions (daily vs intraday, session boundaries) |
| `PIT_LINKAGE.md` | Point-in-time entity linkage and ISIN mapping documentation |
| `INSTRUMENT_MASTER.md` | Instrument master schema and usage |
| `CAS_CATEGORY.md` | CAS category classification and usage |
| `PROVENANCE.md` | Data source and ingestion methodology |
| `KNOWN_ISSUES.md` | Known data quality issues and missingness |

---

## HUMAN APPROVAL REQUIRED

| Item | Question | Context |
|------|----------|---------|
| `reference/nse_index_pr/` scope | Confirm that all 235 NSE index PR files are required for interpretation | These are official NSE publications listing index constituents. They are raw source data, not research-derived. |
| `reference/mcwb_*.zip` scope | Confirm that all 198 MCWB files are required for interpretation | These are monthly index membership/weight files. They are raw source data, not research-derived. |

---

## Explicit Statements

- **No files were copied.**
- **No files were modified.**
- **No files were deleted.**
- **Old research history was not used** to make classification decisions.
- **This is a planning manifest only.** No action has been taken.
- **No Git repository has been initialized.**
- **No new folders have been created.**
- **No research has been performed.**
