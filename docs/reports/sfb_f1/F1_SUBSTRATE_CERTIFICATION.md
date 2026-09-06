# F1 Substrate Certification Report
*Generated: 2026-07-19T10:25:41.022093*

## Data Overview
- Date range: 2022-08-08 to 2025-07-17
- Raw rows: 159,001
- Distinct FUTSTK underlyings: 271
- Distinct FUTIDX underlyings: 5
- Ingestion sources: 2

## F-A: Roll-seam continuity
- **Prediction: 0 roll splices exceed tolerance (adj_return ~= economic_return).**
- **Violations: 0**
- n_splices: 0

## F-B: Contract-grain integrity
- **Prediction: 0 duplicate (underlying, expiry, trade_date) rows; roll_flag dates strictly increasing.**
- **Violations: 0**
- n_raw_rows: 0
- n_continuous_rows: 0

## F-C: No-lookahead roll
- **Prediction: every computed roll date matches the independently recomputed date (0 lookahead violations).**
- **Violations: 0**
- n_rolls: 0

## F-D: PIT universe correctness
- **Prediction: 0 intervals violate liquidity floor, 0 members active before/after data coverage, 0 causality violations.**
- **Violations: 0**
- n_intervals: 0

## F-E: Fee-era boundaries
- **Prediction: 0 rate mismatches at any pinned boundary (14 source-verified tests).**
- **Violations: 0**
- n_tests: 14

## Coverage Assessment (degeneracy floor)
- Session density: 0.242 (260/1074) FAIL (need >=0.30)
- TRAIN (<=2018): 0 rows FAIL (need >50K)
- HOLDOUT (2019-2022): 602 rows FAIL (need >2.5K)
- SEALED (>2022): 158,399 rows
- Calendar span: 1074 days PASS
- Underlyings with series > 5 rows: 0
- Roll splices tested: 0
- Roll events verified: 0
- Universe intervals: 0
- **INCOMPLETE — insufficient TRAIN/HOLDOUT coverage or density.**

## Summary
**Total violations: 0**
**INCOMPLETE — insufficient TRAIN/HOLDOUT coverage.** Substrate NOT certified. Acquire TRAIN/HOLDOUT data and re-run.

## Configuration
- Roll trigger: volume-crossover (calendar fallback expiry-1)
- Liquidity floor: median daily contracts >= 100 over trailing 63 sessions
- Roll splice tolerance: 0.001
- Format boundary: legacy <= 2024-07-05, UDiFF >= 2024-06-01
- STT schedule: pre-2024-10-01 = 0.0125%, post = 0.02% (forward-adjustment convention)
