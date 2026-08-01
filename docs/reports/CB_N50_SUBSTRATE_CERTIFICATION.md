# CB-N50 Substrate Certification — Phase 1
Generated: 2026-08-01

**Overall: PASS**

## G1 — Universe
**PASS: True**
NIFTY-200 top-50 approximation => PIT Nifty 50 membership. Source: universe_membership table, top 50 by rank per rebalance date. This is NOT a verified Nifty 50 index membership list — exact verification requires cross-referencing NSE published index changes and is deferred to the actual TRAIN build step.

- **n_dates_checked**: 20
- **n_dates_ok**: 19
- **n_dates_missing**: 1
- **total_constituent_dates_checked**: 1000
- **total_constituent_dates_present**: 999
- **coverage_rate**: 99.9
- **coverage_threshold**: 95%
- **n_rebalance_dates**: 175
- **rebalance_date_range**: 2012-01-31 -> 2026-07-09

### Sample checks (20 dates)
- 2016-06-02: OK (50/50 present)
- 2016-06-10: OK (50/50 present)
- 2016-06-30: OK (50/50 present)
- 2016-07-13: MISSING (49/50 present)
  Missing: SKSMICRO
- 2017-06-12: OK (50/50 present)
- 2017-07-20: OK (50/50 present)
- 2017-09-12: OK (50/50 present)
- 2017-11-06: OK (50/50 present)
- 2018-04-24: OK (50/50 present)
- 2019-08-16: OK (50/50 present)

## G2 — Data Coverage
**PASS: True**
NIFTY-200 top-50 constituent equity bhavcopy availability, 2016-01-01 → 2026-07-31.

- **total_constituent_dates**: 131050
- **total_misses**: 57
- **miss_rate**: 0.043
- **threshold**: 1%
- **dates_checked**: 2621
- **dates_below_30**: 0

#### Top missing symbols
- SKSMICRO: 19 dates
- HDFC: 12 dates
- ZOMATO: 12 dates
- MINDTREE: 5 dates
- TATAMOTORS: 5 dates
- JETAIRWAYS: 4 dates

## G3 — Futures
**PASS: True**
Nifty futures data availability + roll date identification

- **futures_date_range**: 2016-02-11 to 2026-07-31
- **n_trade_dates**: 2582
- **n_total_rows**: 7746
- **n_expiries**: 131
- **n_gaps_gt_5d**: 0
- **roll_dates_total**: 130

## G4 — Execution Price
**PASS: True**
Nifty futures near-month open auction prices

- **total_contract_dates**: 2582
- **open_valid**: 2582
- **open_zero**: 0
- **open_valid_rate**: 100.0
- **threshold**: 90%

## G5 — Roll Rule
**PASS: True**
Roll rule (2 days before expiry) is mechanically applicable

- **total_trade_dates**: 2582
- **total_roll_dates**: 355
