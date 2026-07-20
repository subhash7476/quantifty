# MSRP Phase 7 — Bhavcopy Ingestion Audit

*Generated: 2026-07-20T23:05:30.769962*

## Ingestion Summary

- Date range: 2016-02-11 to 2026-07-19
- Data coverage: 2016-02-11 to 2026-07-17
- Rows in database: 5,490,319
- Rows inserted this run: 1,325,359
- Dates skipped (already present): 1956
- Dates with 404 (holiday/unavailable): 150
- Non-NIFTY rows purged (NIFTYNXT50): 0

Total rows ingested: 5,490,319
Date range: 2016-02-11 to 2026-07-17
Distinct trade dates: 2572
Distinct expiry dates: 457

## Per-Expiry Weekly Liquidity
Expiries with <= 30 DTE from their earliest observation (the weekly/fortnightly set). ZeroVolDays = distinct trade_dates where summed daily contracts = 0.
Expiry           Days       Avg Ctr      Avg OI   ZeroVolDays
------------------------------------------------------------
2016-02-25         11         28836      595209             0
2019-02-14          4         15638       86882             0
2019-02-21          9         10774       63256             0
2019-03-07         18          4710       36919             2
2023-06-28          1        746803      915656             0
2024-04-10         21         93802      270399             0
2025-09-16         21        139216      541484             0
2026-07-21         22         47334      268499             0
2026-08-04         17           213        9542             0
2026-08-11          8            35        1589             0
2026-08-18          3            10         411             0
2031-06-24         13             0           0            13

## ATM-Adjacent Strike Quality (±200 from Nifty close)

### Thursday regime
- Trade dates: 739
- Days with ATM contracts > 0: 738/739 (99.9%)
- Avg ATM open interest: 829,077
- Stale-open candidates (open==prev_settle same contract, ctr<10): 89

### Tuesday regime
- Trade dates: 122
- Days with ATM contracts > 0: 122/122 (100.0%)
- Avg ATM open interest: 821,786
- Stale-open candidates (open==prev_settle same contract, ctr<10): 9

### Overall Verdict: PASS
Reason: ATM strikes have 99.9% of days with contracts>0 and average OI of 828,032 (>1000).
