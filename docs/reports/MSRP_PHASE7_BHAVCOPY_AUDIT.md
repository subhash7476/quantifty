# MSRP Phase 7 -- Bhavcopy Ingestion Audit

*Generated: 2026-07-07T19:01:43.551671*

## Ingestion Summary

- Data coverage: 2023-01-02 to 2026-07-06
- Distinct trade dates: 862
- Rows in database: 1,351,214
- Legacy slice: 2023-01-02 to 2024-07-05
- UDiFF slice: 2024-07-08 to 2026-07-06

Total rows ingested: 1,351,214
Date range: 2023-01-02 to 2026-07-06
Distinct trade dates: 862
Distinct expiry dates: 214

## Per-Expiry Weekly Liquidity
Expiries with <= 30 DTE from their earliest observation.
Expiry           Days       Avg Ctr      Avg OI   ZeroVolDays
------------------------------------------------------------
2023-01-05          4        307538      715928             0
2023-01-12          9        262158      720490             0
2023-01-19         14        144635      428334             0
2023-01-25         18         67200      377320             0
2023-06-28          1        746803      915656             0
2024-04-10         21         93802      270399             0
2025-09-16         21        139216      541484             0
2026-07-14         18          2782       55920             0
2026-07-21         13           284        9688             0
2026-08-04          8            15         901             0
2031-06-24          4             0           0             4

## ATM-Adjacent Strike Quality (+/-200 from Nifty close)

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
