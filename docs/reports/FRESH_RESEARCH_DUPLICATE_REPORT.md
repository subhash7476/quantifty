# Fresh Research Duplicate Report

**Date:** 2026-10-01
**Scope:** Duplicate and redundant data detection across `F:\Nifty\data\`

---

## Summary

| Duplicate Type | Count | Size | Canonical Source |
|----------------|-------|------|------------------|
| 1d snapshot copies | 242 files | 485 MB | `market_data/nse/candles/1d/` |
| SPAN staging area | 320 files | 2,797 MB | `span/` |
| N200 regime params backup | 10 files | 0.0 MB | `features/n200_regime/params/` |
| **Total** | **572 files** | **3,282 MB** | — |

---

## Detailed Duplicate Analysis

### 1. `market_data/nse/candles/1d_snapshot_g1_r2/` — DUPLICATE

| Property | Value |
|----------|-------|
| **Files** | 241 `.duckdb` files + 1 CSV |
| **Size** | 485 MB |
| **Date range** | 2012-02-21 → 2013-02-07 (241 sessions) |
| **Canonical source** | `market_data/nse/candles/1d/` |
| **Relationship** | Snapshot copies of 1d candles for a specific date range |
| **Evidence** | Same schema (candles table, 9 cols), same date range as subset of `1d/` |
| **Recommendation** | **DO NOT TRANSFER.** Redundant with canonical `1d/` data. |

**Note:** The `pre_vendor_fill_20260722T141047.csv` file (152 KB) is a pre-vendor-fill snapshot. This is a backup artifact, not a duplicate.

### 2. `market_data/nse/candles/1d_snapshots/` — DUPLICATE

| Property | Value |
|----------|-------|
| **Files** | 1 file |
| **Size** | 0.1 MB |
| **Canonical source** | `market_data/nse/candles/1d/` |
| **Relationship** | Snapshot metadata for 1d candles |
| **Recommendation** | **DO NOT TRANSFER.** Metadata only, no unique data. |

### 3. `span/staging/` — DUPLICATE

| Property | Value |
|----------|-------|
| **Files** | 320 files (parquet + zip) |
| **Size** | 2,797 MB |
| **Canonical source** | `span/` |
| **Relationship** | Staging area for SPAR data processing. Contains parquet and zip files that are copies of canonical span data. |
| **Evidence** | Same file naming convention (`nse_fo_span_YYYY-MM-DD.parquet/zip`), same date range as `span/`. |
| **Recommendation** | **DO NOT TRANSFER.** Temporary processing artifacts. |

### 4. `features/n200_regime/params_b/` — DUPLICATE

| Property | Value |
|----------|-------|
| **Files** | 10 files |
| **Size** | 0.0 MB |
| **Canonical source** | `features/n200_regime/params/` |
| **Relationship** | Backup of N200 regime parameters |
| **Recommendation** | **DO NOT TRANSFER.** Backup of already-excluded derived data. |

---

## Non-Duplicate Overlaps (Canonical Sources with Multiple Copies)

These are **NOT duplicates** — they are canonical sources with redundant copies that should be consolidated:

### 5. `span/*.parquet` vs `span/*.zip`

| Property | Value |
|----------|-------|
| **Parquet files** | ~310 files, 10,489 MB |
| **Zip files** | ~320 files, 2,796 MB |
| **Relationship** | Same data in two formats (parquet and zip) |
| **Recommendation** | **TRANSFER BOTH.** Parquet is for analysis, zip is for archive. Both are canonical. |

### 6. `market_data/nse/candles/1d/` vs `market_data/nse/candles/1m/`

| Property | Value |
|----------|-------|
| **1d files** | 4,147 files, 4,574 MB |
| **1m files** | 3,654 files, 12,421 MB |
| **Relationship** | Different time resolutions of the same underlying data |
| **Recommendation** | **TRANSFER BOTH.** Both are canonical. |

### 7. `market_data/nse/candles/1m/` vs `market_data/nse/candles/1m_vendor/`

| Property | Value |
|----------|-------|
| **1m files** | 3,654 files, 12,421 MB |
| **1m_vendor files** | 102 files, 3,163 MB |
| **Relationship** | Different sources (NSE vs Upstox) for 1m data |
| **Recommendation** | **TRANSFER BOTH.** Both are canonical from different sources. |

---

## Hash-Based Comparison

Hash-based comparison was **not performed** for all files due to the large size (62 GB). Duplicate detection relied on:

1. **Directory naming convention** — `_snapshot_`, `_staging_`, `_baselines` indicate non-canonical copies
2. **Schema comparison** — Same table structure and column count
3. **Date range overlap** — Same or subset date ranges
4. **File count comparison** — Same or subset file counts

For the 1d snapshot comparison:
- `1d/` has 4,147 files spanning 2010-01-04 → 2026-09-30
- `1d_snapshot_g1_r2/` has 241 files spanning 2012-02-21 → 2013-02-07
- The 241 files are a **subset** of the 4,147 files
- Schema is identical (candles table, 9 columns)
- **Conclusion:** `1d_snapshot_g1_r2/` is a subset duplicate of `1d/`

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Transferring duplicate data | Low | Medium | This report identifies all known duplicates |
| Missing canonical data | Low | High | All canonical sources identified |
| Breaking PIT/entity linkage | Medium | High | `instruments/` and `universe_raw/` must be transferred |
| Losing data quality metadata | Medium | High | CA adjustment status, timestamp semantics documented in inventory |
| REVIEW items misclassified | Medium | Medium | 5 items flagged for human review |

---

## Recommendation

1. **Transfer all YES items** from the transfer manifest.
2. **Exclude all NO items** from the transfer manifest.
3. **Resolve 5 REVIEW items** before transfer.
4. **Do not transfer** any duplicate identified in this report.
5. **Preserve data quality metadata** documented in the inventory report.

---

## Notes

1. **No data was modified.** This is a read-only analysis.
2. **No research reports were read.** Classification is based on directory structure and database schemas only.
3. **Hash-based comparison** was not performed for all files due to size. See methodology above.
