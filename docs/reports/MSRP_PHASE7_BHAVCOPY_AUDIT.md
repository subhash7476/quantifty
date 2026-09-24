# MSRP Phase 7 — Bhavcopy Ingestion Audit

*Generated: 2026-09-13T22:32:21.698056*

## Ingestion Summary

- Date range: 2026-09-10 to 2026-09-13
- Data coverage: 2016-02-11 to 2026-09-11
- Rows in database: 5,556,591
- Rows inserted this run: 0
- Dates skipped (already present): 2
- Dates with 404 (holiday/unavailable): 0
- Non-NIFTY rows purged (NIFTYNXT50): 0

Total rows ingested: 5,556,591
Date range: 2016-02-11 to 2026-09-11
Distinct trade dates: 2612
Distinct expiry dates: 465

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
2026-09-15         23         59815      349906             0
2026-09-22         18          2690       64961             0
2026-10-06          8            83        3395             0
2026-10-13          3            15         462             0
2026-11-23         13           185       16322             0

## ATM-Adjacent Strike Quality (±200 from Nifty close)

### Thursday regime
- Trade dates: 2440
- Days with ATM contracts > 0: 2437/2440 (99.9%)
- Avg ATM open interest: 366,556
- Stale-open candidates (open==prev_settle same contract, ctr<10): 455

### Tuesday regime
- Trade dates: 172
- Days with ATM contracts > 0: 172/172 (100.0%)
- Avg ATM open interest: 906,600
- Stale-open candidates (open==prev_settle same contract, ctr<10): 11

### Overall Verdict: PASS
Reason: ATM strikes have 99.9% of days with contracts>0 and average OI of 394,576 (>1000).
