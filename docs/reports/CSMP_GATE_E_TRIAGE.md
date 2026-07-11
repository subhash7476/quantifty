# CSMP Gate (e) — 12-1 Momentum Transmission Triage

**Window:** dev window ONLY (2012-01 → 2022-12). Sealed held-out window (2023-01 → 2026-06) is untouched and is not read.
**Construct:** charter-locked classic 12-1, monthly rebalance, equal-weight, provisional top-quintile bucket. No tuning.
**Capital assumption:** Rs 1,00,00,000 (₹1 cr) — disclosed; ad-valorem costs are capital-independent, DP drag < 0.5 bp/mo at this scale.

## 1. Sealed-window fence

- `MAX(trade_date) <= 2022-12-31` asserted on every input query.
- Adjusted-view dev-window boundary: **MAX(trade_date) = 2022-12-30** (OK).
- Monthly full-session grid: 156 sessions, 2010-01-29 → 2022-12-30.
- Forward-return cutoff: the last dev-window session is **2022-12-30**; a formation's forward return needs the *next* session, so the last formation month with an in-dev forward return is **2022-11-30** (forward → 2022-12-30). The 2022-12-30 formation's forward return would read the sealed window (2023-01) and is excluded from the IC / portfolio series.

## 2. Formation & ranking

- **Score (12-1):** total adjusted return from `t−12m` to `t−1m` (skip most-recent month), entity-continuous across renames via `universe_eligibility`/`symbol_changes`.
- Members scored at each `t` are the point-in-time `universe_membership` members; names lacking a complete formation window (not priced at `t−12m` or `t−1m`) are excluded and counted.
- Forward return: adjusted return `t → t+1` (next grid session).
- Scored months (IC series): **131** (2012-01-31 → 2022-11-30).

- Total names excluded (incomplete formation window): **382** across 131 months.
- Incomplete-window exclusions by year: 2012:18, 2013:21, 2014:15, 2015:21, 2016:53, 2017:64, 2018:28, 2019:8, 2020:30, 2021:67, 2022:57.
- Forward returns computed for **25,797** member-months.

## 3. Cross-sectional rank IC (Spearman)

- Months: **131**
- Mean rank IC: **0.0458**  | SD: 0.2078  | naive t-stat: 2.52  | hit rate (>0): 57.25%
- Block-bootstrap 95% CI of mean IC (L=12, reps=20000, seed=20260711): **[0.0093, 0.0812]**

By formation year:

| Year | Months | Mean IC | Hit rate |
|------|-------:|--------:|---------:|
| 2012 | 12 | +0.1117 | 66.67% |
| 2013 | 12 | +0.0801 | 58.33% |
| 2014 | 12 | -0.0301 | 50.00% |
| 2015 | 12 | +0.0945 | 66.67% |
| 2016 | 12 | -0.0440 | 25.00% |
| 2017 | 12 | +0.0609 | 75.00% |
| 2018 | 12 | +0.0539 | 66.67% |
| 2019 | 12 | +0.1408 | 75.00% |
| 2020 | 12 | +0.0107 | 41.67% |
| 2021 | 12 | +0.0433 | 58.33% |
| 2022 | 11 | -0.0242 | 45.45% |

Monthly IC series (year, mean IC):

```
  2012: +0.1117
  2013: +0.0801
  2014: -0.0301
  2015: +0.0945
  2016: -0.0440
  2017: +0.0609
  2018: +0.0539
  2019: +0.1408
  2020: +0.0107
  2021: +0.0433
  2022: -0.0242
```

## 4. Bucket gross spreads (equal-weight, long top / short bottom)

- Top-minus-bottom **quintile** (40/40): mean gross spread **1.07%** per month, SD 6.33%, hit rate 60.31%.
- Top-minus-bottom **decile** (20/20): mean gross spread **1.22%** per month, SD 8.29%, hit rate 57.25%.

## 5. Net-of-fee portfolios (gate-(d) delivery fees on turnover)

- Capital: Rs 10,000,000. Equal-weight, monthly rebalance. Turnover = names entering/leaving the held bucket (bucket churn — for the top quintile, names rotating in/out of the top-40-by-momentum set; for the universe, membership churn). Equal-weight drift of continuing holdings is not re-traded, a disclosed simplification that slightly understates fees for both arms (conservative: the net drag is a few bp/mo either way).
- Fees: gate-(d) `delivery_equity_fees` on each buy/sell leg of rebalance turnover; first rebalance buys the whole book; terminal month marked, not liquidated (standard for a return series).

- **Top-quintile EW:** annualized net 15.53%, gross 16.26%, avg monthly two-way turnover 23.76%, avg fee drag 5.22 bp/mo, 131 periods
- **Equal-weight universe:** annualized net 9.16%, gross 9.25%, avg monthly two-way turnover 3.03%, avg fee drag 0.71 bp/mo, 131 periods
- **Net annualized top-minus-universe spread: 6.38%**

## 6. Reference arm (NIFTY200 Momentum 30 TRI)

- **Unobtainable** as a freely-downloadable historical TRI series. `https://archives.nseindia.com/content/indices/ind_nifty200momentum30list.csv` — HTTPError 404 — no historical TRI file published.
- This is a reference, not the gating baseline (per the prompt); the verdict below rests solely on the dev-window IC and net-spread stop rules.

## 7. Pre-committed stop rule (LOCKED before the run)

| Rule | Threshold | Observed | Result |
|------|-----------|----------|--------|
| (A) mean rank IC > 0.02 | 0.02 | 0.0458 | PASS |
| (A) bootstrap 95% CI excludes 0 (lower > 0) | 0 | [0.0093, 0.0812] | PASS |
| (B) net annualized top-minus-universe spread > 0 | 0 | 6.38% | PASS |

### VERDICT: **CONTINUE**

Both stop rules clear on the dev window: classic 12-1 momentum transmits into a statistically-positive, net-of-fee edge over the 2012-2022 point-in-time universe. CSMP may proceed to Phase-1 pre-registration; the sealed held-out window (2023-01 → 2026-06) remains untouched for the post-pre-registration test (D3).

---
*Report generated by `scripts/csmp/triage_momentum.py` against the gate-(a/b/c) store and gate-(d) fee model. Deterministic; re-running against an unchanged store reproduces this report byte-for-byte (fixed seed 20260711, 20000 bootstrap reps). Reference-arm probe cached at `data\market_data\ref_nifty200mom30tri.json`.*
