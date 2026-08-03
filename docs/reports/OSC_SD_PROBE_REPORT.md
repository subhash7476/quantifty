# OSC — Option Surface Cross-Section: SD/Breadth Probe Report

**Date:** 2026-08-02  |  **Window:** 2023-01-02 -> 2025-12-31 (burned)
**n_dates (same-day):** 737  |  **Unread window:** 2016-02-11 -> 2022-12-31 (1,701 formations, preserved)

## 1. Fence proof

- Observed min `trade_date`: 2023-01-02
- Observed max `trade_date`: 2025-12-31
- Hard assertion at top of pipeline: `assert obs_min >= FENCE_START and obs_max <= FENCE_END` — **PASSED**

## 2. Attrition

| Stage | Cells |
|---|---|
| Rows loaded | 1,127,502 |
| Traded (contracts>0, OI>0) | 621,635 |
| Merged with forward (inner join) | 598,791 |
| Settle >= 0.5 | 589,963 |
| 7 <= DTE <= 60 | 397,829 |
| |m| <= 0.15 | 388,038 |
| OTM only | 237,430 |
| IV inversion converged | 237,430 (0 discarded) |
| Paired t->t+1 | 208,245 |
| Expiry-dates dropped (no forward) | 1794 |
| Surface-fit dates dropped (<30 cells) | 0 |

## 3. Cells per day (after all filters, paired)

- Median paired cells/day: 283
- 10th percentile: 213
- 90th percentile: 353

| Year | Median cells | P10 | P90 |
|---|---|---|---|
| 2023 | 243 | 195 | 300 |
| 2024 | 294 | 232 | 354 |
| 2025 | 311 | 251 | 367 |

## 4. IC comparison — same-day vs skip-a-day vs backward vs trailing-IV

| Series | n_dates | mean_IC | sd_IC | AC1 | NW t | NW SE |
|---|---|---|---|---|---|---|
| Same-day | 737 | -0.0615 | 0.2032 | -0.0138 | -8.4895 | 0.0072 |
| Skip-a-day (C-1) **LADDER INPUT** | 736 | 0.0198 | 0.2068 | -0.0226 | 2.7305 | 0.0073 |
| Backward (C-1b) | 736 | 0.0185 | 0.2067 | -0.0210 | 2.5694 | 0.0072 |
| Trail-IV (C-2) | 735 | 0.0192 | 0.1976 | 0.0064 | 2.6964 | 0.0071 |

### C-1 interpretation (skip-a-day vs same-day)

- same-day |mean_IC| = 0.0615
- skip-a-day |mean_IC| = 0.0198
- Fall: 67.7%
- Reading: **Same-day IC was predominantly bounce (68% fall). Same-day number is void.**

The skip-a-day `sd_IC` — not the same-day — is the ladder input (prompt §7).

## 5. Effective breadth (bucket space on moneyness decile x DTE tercile, rolling 60-day)

| Statistic | Value |
|---|---|
| Median N_eff | 1.9 |
| Median PC1 variance share | 61.05% |
| Median raw cell count | 286 |
| Median populated buckets | 10

### C-5 — N_eff vs sd_IC consistency

sd_IC = 0.2068 implies roughly 26 effective independent
cross-sectional observations. N_eff = 1.9 measures return co-movement in bucket
space. Both are internally consistent: Spearman rank correlation is invariant to
a common additive shift in returns (the PC1 vol-level factor at 61% barely
perturbs ranks), so the rank-statistic sampling error is much smaller than the
return co-movement would suggest. They measure different things.

**Economic consequence (Grinold-Kahn):** N_eff ~ 2 implies effective breadth
BR ~ 2 x 252 ~ 504 independent bets/year, not ~raw-cells x 252. An L/S book
built on these rankings is close to a two-position book wearing a multi-position
costume. This does not block the RFA (demonstrability only), but it directly
attacks the economic case — the gap between statistical significance and
tradeable diversification must be closed at design time.

## 6. Feasibility read-out

**Ladder input (skip-a-day sd_IC) = 0.2068**

| sd_IC threshold | Verdict |
|---|---|
| <= 0.2207 | Green — feasible even at pessimistic delta=0.015. Proceed to design. <- **HERE** |
| <= 0.2943 | Amber — feasible only if delta>=0.020 can be independently defended. |
| <= 0.4267 | Red-amber — feasible only at delta>=0.029 (CB-N50 stock HOLDOUT IC). Likely not defensible for option cells. |

**Rung: Green — feasible even at pessimistic delta=0.015. Proceed to design.**

## 7. Predictions (original pre-registered, keyed on same-day IC)

| # | Prediction | Result | Held? |
|---|---|---|---|
| P1 | Median surviving cells >= 150 | 283 | **HELD** |
| P2 | PC1 >= 50% | 61.05% | **HELD** |
| P3 | N_eff << raw cells; median N_eff < 25 | 1.9 | **HELD** |
| P4 | mean_IC negative (same-day) | -0.0615 | **HELD** |
| P5a | sd_IC <= 0.2943 (Green or Amber) | 0.2068 | **HELD** |
| P5b | sd_IC >= 0.15 | 0.2068 | **HELD** |
| P6 | IV discard < 5% | 0.00% | **HELD** |

## 8. Carry-forward note

The delta half of the RFA input is **not an output of this probe.** Section 6's ladder is
keyed to assumed delta values, and the prompt (S7-S8) forbids inheriting `mean_IC`
as the delta anchor. A Green/Amber rung supplies the SD half; the delta anchor must be
established at design time from an external source (Goyal & Saretto 2009;
Bakshi & Kapadia 2003).

The 2016-02-11 -> 2022-12-31 window (1,701 formations) was not read by this probe.
