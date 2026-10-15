# Fresh Research Transfer Manifest

**Date:** 2026-10-01
**Source:** `F:\Nifty\data\`
**Target:** Clean research-only repository

---

## Transfer Summary

| Decision | Count | Size |
|----------|-------|------|
| YES (transfer) | 19,200+ | ~35.5 GB |
| NO (exclude) | ~7,900 | ~26.5 GB |
| REVIEW (human decision) | 5 | ~0.5 MB |

---

## Full Transfer Manifest

| PATH | CLASS | TRANSFER? | REASON | CANONICAL_SOURCE | DUPLICATE/RISK | SIZE |
|------|-------|-----------|---------|------------------|----------------|------|
| `market_data/nse/candles/1d/` | CANONICAL_SOURCE | YES | Core daily OHLCV data for NSE equities and indices. 2010→2026. | — | — | 4,574 MB |
| `market_data/nse/candles/1m/` | CANONICAL_SOURCE | YES | Core 1-minute OHLCV data for NSE equities and indices. 2012→2026. | — | — | 12,421 MB |
| `market_data/nse/candles/1m_vendor/` | CANONICAL_SOURCE | YES | Vendor 1m data (Upstox historical). Independent source. | — | — | 3,163 MB |
| `market_data/nse/candles/1d_snapshot_g1_r2/` | DUPLICATE/REDUNDANT | NO | Snapshot copies of 1d candles. Redundant with `1d/`. | `market_data/nse/candles/1d/` | Duplicate of canonical 1d data | 485 MB |
| `market_data/nse/candles/1d_snapshots/` | DUPLICATE/REDUNDANT | NO | Snapshot metadata. Redundant. | `market_data/nse/candles/1d/` | Duplicate metadata | 0.1 MB |
| `market_data/bhavcopy_raw/` | RAW_SOURCE | YES | Raw NSE bhavcopy files. Needed for validation and reconstruction. | — | — | 705 MB |
| `market_data/corporate_actions_raw/` | RAW_SOURCE | YES | Raw corporate actions data. Required for CA adjustment validation. | — | — | 11 MB |
| `market_data/universe_raw/` | RAW_SOURCE | YES | Raw universe membership files. Required for PIT universe reconstruction. | — | — | 0.3 MB |
| `market_data/bse/candles/1d/` | CANONICAL_SOURCE | YES | BSE daily candles. Independent source. | — | — | 6 MB |
| `market_data/bse/candles/1m/` | CANONICAL_SOURCE | YES | BSE 1-minute candles. Independent source. | — | — | 21 MB |
| `market_data/vendor/niftyindices/` | RAW_SOURCE | YES | Vendor index data from niftyindices.com. Needed for validation. | — | — | 0.1 MB |
| `instruments/nse_fo_instruments.duckdb` | REQUIRED_METADATA | YES | F&O instrument master. Required for symbol resolution and PIT linkage. | — | — | 411 MB |
| `cas/cas_category.duckdb` | REQUIRED_METADATA | YES | CAS category classification. Required for CAS-era filtering. | — | — | 0.8 MB |
| `span/*.parquet` | CANONICAL_SOURCE | YES | SPAN risk parameters (parquet). Needed for margin research. | — | — | 10,489 MB |
| `span/*.zip` | CANONICAL_SOURCE | YES | SPAN risk parameters (zip). Same data as parquet. | — | — | 2,796 MB |
| `span/staging/` | CACHE/TEMP | NO | SPAN staging area. Temporary processing artifacts. | `span/` | Redundant with canonical span data | 2,797 MB |
| `options/*.duckdb` | CANONICAL_SOURCE | YES | Options bhavcopy data. Needed for options research. | — | — | 234 MB |
| `options/wall_chain_snapshots/` | CANONICAL_SOURCE | YES | Option chain snapshots (Upstox V3). Needed for options structure research. | — | — | 945 MB |
| `reference/nse_index_pr/` | CANONICAL_SOURCE | YES | NSE index PR files. Needed for index research. | — | — | 55 MB |
| `reference/` (other) | CANONICAL_SOURCE | YES | Other reference data. | — | — | 24 MB |
| `trading/paper.duckdb` | OPERATIONAL_STATE | NO | Paper trading state. Not research data. | — | — | — |
| `trading/production.duckdb` | OPERATIONAL_STATE | NO | Production trading state. Not research data. | — | — | — |
| `trading/` (other) | OPERATIONAL_STATE | NO | Trading metadata. Not research data. | — | — | 0.1 MB |
| `ops/` (all) | OPERATIONAL_STATE | NO | Ops state files (PIDs, logs). Not research data. | — | — | 0.1 MB |
| `live_buffer/market_data.duckdb` | OPERATIONAL_STATE | NO | Live market data buffer. Not research data. | — | — | 192 MB |
| `paper/ts_daily_combo/` | OPERATIONAL_STATE | NO | Paper trading state. Not research data. | — | — | 2 MB |
| `_baselines/` (all) | BACKUP | NO | Baseline snapshots before data repairs. Backup artifacts. | — | — | 1,690 MB |
| `features/day_type/` | DERIVED_DATA | NO | DayType feature data. Derived from research, not canonical source. | — | — | 14 MB |
| `features/n200_regime/` | DERIVED_DATA | NO | N200 regime features. Derived from research. | — | — | 122 MB |
| `features/n200_regime/params/` | DERIVED_DATA | NO | N200 regime parameters. Derived from research. | — | — | 0.0 MB |
| `features/n200_regime/params_b/` | DERIVED_DATA | NO | N200 regime parameters (backup). Derived from research. | — | — | 0.0 MB |
| `a_index_intraday/` | RESEARCH_ARTIFACT | NO | A-index intraday research data. Research output. | — | — | 0.5 MB |
| `analog_path/` | RESEARCH_ARTIFACT | NO | Analog path research data. Research output. | — | — | 13 MB |
| `audit/` | RESEARCH_ARTIFACT | NO | Audit data. Research output. | — | — | 4 MB |
| `isd/` | RESEARCH_ARTIFACT | NO | ISD research data. Research output. | — | — | 5 MB |
| `jev_market_state/` | RESEARCH_ARTIFACT | NO | JEV market state research data. Research output. | — | — | 14 MB |
| `mrlc_test/` | RESEARCH_ARTIFACT | NO | MRLC test data. Research output. | — | — | 193 MB |
| `mto_probe/` | RESEARCH_ARTIFACT | NO | MTO probe data. Research output. | — | — | 149 MB |
| `nifty_shield/` | RESEARCH_ARTIFACT | NO | NiftyShield research data. Research output. | — | — | 9 MB |
| `nifty_shield/sessions/` | RESEARCH_ARTIFACT | NO | NiftyShield session data. Research output. | — | — | ~100 MB |
| `nifty_shield_preflight/` | RESEARCH_ARTIFACT | NO | NiftyShield preflight data. Research output. | — | — | 0.1 MB |
| `reliance_regime/` | RESEARCH_ARTIFACT | NO | Reliance regime research data. Research output. | — | — | 0.4 MB |
| `research/` | RESEARCH_ARTIFACT | NO | Research data (breakout_volume, m4a_compress, straddle_m10, vwap_extreme_reversion). Research output. | — | — | 397 MB |
| `se3/` | RESEARCH_ARTIFACT | NO | SE3 research data. Research output. | — | — | 8 MB |
| `signal_engine/` | RESEARCH_ARTIFACT | NO | Signal engine data (carry, ivol, lag, skew, trade_intelligence, trend, ts_basis, ts_basis_daily). Research output. | — | — | 2,992 MB |
| `psb1_synthetic/` | TEST_FIXTURE | NO | PSB1 synthetic test data. Test fixture. | — | — | 16 MB |
| `psb2_synthetic/` | TEST_FIXTURE | NO | PSB2 synthetic test data. Test fixture. | — | — | 26 MB |
| `scratch/` | CACHE/TEMP | NO | Scratch data. Temporary. | — | — | 3 MB |
| `scratch/options_seller_edge/` | CACHE/TEMP | NO | Options seller edge scratch data. Temporary. | — | — | 9 MB |
| `config/` | OPERATIONAL_STATE | NO | Configuration files. Not research data. | — | — | 0.1 MB |
| `data/*.json` (root) | OPERATIONAL_STATE | NO | Root-level JSON state files. Not research data. | — | — | 1.2 MB |

---

## REVIEW Items

| PATH | CLASS | REASON FOR REVIEW |
|------|-------|-------------------|
| `market_data/bhavcopy_raw/focal_*.404` | RAW_SOURCE | 1,697 zero-byte `.404` markers. These are download failure markers, not data. Recommend NO. |
| `market_data/bhavcopy_raw/udiff_*.404` | RAW_SOURCE | 275 zero-byte `.404` markers. Same as above. Recommend NO. |
| `market_data/bhavcopy_raw/legacy_*.csv` | RAW_SOURCE | 4,179 files, 135 MB. May contain legacy bhavcopy data. Needs human review. |
| `market_data/bhavcopy_raw/secfull_*.csv` | RAW_SOURCE | 2,463 files, 560 MB. May contain full bhavcopy data. Needs human review. |
| `market_data/bhavcopy_raw/foudiff_*.csv` | RAW_SOURCE | 281 files, 9 MB. May contain futures bhavcopy diff data. Needs human review. |

---

## Proposed Clean Directory Tree

```
research-data/
├── market_data/
│   ├── nse/
│   │   ├── candles/
│   │   │   ├── 1d/              # 4,147 files, 4.5 GB
│   │   │   └── 1m/              # 3,654 files, 12.4 GB
│   │   └── bhavcopy_raw/        # 8,895 files, 705 MB
│   ├── bse/
│   │   └── candles/
│   │       ├── 1d/              # 8 files, 6 MB
│   │       └── 1m/              # 27 files, 21 MB
│   ├── corporate_actions_raw/   # 2,965 files, 11 MB
│   ├── universe_raw/            # 3 files, 0.3 MB
│   └── vendor/
│       └── niftyindices/        # 8 files, 0.1 MB
├── instruments/
│   └── nse_fo_instruments.duckdb  # 411 MB
├── cas/
│   └── cas_category.duckdb       # 0.8 MB
├── span/
│   ├── *.parquet                # ~310 files, 10.5 GB
│   └── *.zip                    # ~320 files, 2.8 GB
├── options/
│   ├── *.duckdb                 # 9 files, 234 MB
│   └── wall_chain_snapshots/    # 19 files, 945 MB
└── reference/
    ├── nse_index_pr/            # 235 files, 55 MB
    └── ...                      # 204 files, 24 MB
```

**Total transfer size:** ~35.5 GB
**Total excluded size:** ~26.5 GB
**Duplicate/redundant size:** ~485 MB (1d snapshots) + ~2.8 GB (span staging) = ~3.3 GB
**Unresolved items:** 5 REVIEW items (bhavcopy_raw subdirectories)

---

## Notes

1. **No data was modified.** This manifest is for planning only.
2. **REVIEW items** require human decision before transfer.
3. **Duplicate detection** is based on directory naming and schema comparison.
4. **The target repository should NOT contain:** strategy outputs, signals, backtest results, experiment artifacts, research reports, models, trading state, live/paper state, caches, scratch data, synthetic test fixtures, obsolete/legacy copies, backups, or derived datasets where the canonical source already exists.
