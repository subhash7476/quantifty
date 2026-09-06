# IVOL Sleeve — TRAIN Report

**Script-generated** — `scripts/signal_engine/ivol/run_train.py`. Code commit `4ef7123`.

**Frozen protocol:** `IVOL_PHASE0_PRE_REGISTRATION.md` §9 gate 2 (declaration SHA `d7ebcbcc…`).

**Windows:** TRAIN 2017-02-28 → 2020-12-31. HOLDOUT (2021-01 → 2022-12) and SEALED (2023-01 → 2026-07) untouched.

**Sign:** NEGATIVE (high idiosyncratic vol → low forward return). Book longs low-z_ivol (low vol), shorts high-z_ivol (high vol).

## Substrate

| Quantity | Value |
|---|---|
| Formations (total in TRAIN window) | 47 |
| Formations with >= 5 scored names | 47 |
| Mean names per formation | 167 |
| Neutralized signals in TRAIN | 20,162 |

## Rank-IC Results

| Metric | Value |
|---|---|
| Mean IC | -0.054596 |
| SD(IC) | 0.164894 |
| t-stat (simple) | -2.2699 |
| p-value (one-sided, negative direction) | 1.397304e-02 |
| AC1 | 0.0521 |
| NW t (\|AC1\| <= 0.1) | below trigger, not computed |
| First-half mean IC | -0.062077 |
| Second-half mean IC | -0.047426 |
| Sign matches prediction (negative) | PASS |
| Structural bet (\|IC\| >= 0.05) | **CLEARS** |

## IC SD Band Check

| Check | Band | Realized | Result |
|---|---|---|:--:|
| IC SD | [0.10, 0.18] | 0.1649 | PASS |

## Quintile Spread (Net of Fees — long low-vol / short high-vol)

| Metric | Value |
|---|---|
| Gross annualized return (L-S) | 0.0656 (6.56%) |
| Net annualized return (L-S) | 0.0596 (5.96%) |
| Q1-Q5 gross spread (last formation) | -0.025047 |
| Fee+slippage drag (annualized) | 60.4 bp |
| Avg turnover per rebalance | 0.6883 |

## Neutralization & Carry-Subsumption

| Check | Value | Result |
|---|---|:--:|
| Raw IC (pre-neutralization) | -0.075200 | — |
| Neutralized IC / raw IC (same sign, >= 0.60) | 0.73, same_sign=True | PASS |
| IC after residualizing on Carry z_carry_neut | -0.046855 | — |
| Not subsumed by Carry (>= 60% of raw, same sign) | ratio=0.86 | PASS |
| (joined 7,755 name-formation pairs with Carry) | | |

## Power Projection (n* = 42, sealed window)

| Method | Power |
|---|---|
| Noncentral-t (simple SD) | 0.6791 |
| Noncentral-t (half-IC) | 0.2777 |
| Hurdle | 0.80 |

## Prediction Outcomes (pre-reg section 11)

| # | Prediction | Result | Detail |
|---|---|---|---|
| 1 | IVOL rank-IC negative-signed + significant | PASS | mean_ic=-0.0546 (expected < 0). simple t: -2.2699 (threshold < -1.96). Structural bet \|IC\| >= 0.05: YES |
| 2 | Not subsumed by Carry (resid IC >= 60% raw) | PASS | resid_ic=-0.0469, raw_ic=-0.0546, ratio=0.86 |
| 3 | Net quintile spread > 0 (long low-vol) | PASS | net spread=5.96% annualized |
| 4 | IC SD in [0.10, 0.18] | PASS | SD=0.1649 |

## IC Series (all formations)

| Formation date | IC | Raw IC | Names |
|---|---|---|---:|
| 2017-02-28 | 0.027853 | -0.038958 | 173 |
| 2017-03-31 | 0.189790 | 0.084809 | 170 |
| 2017-04-28 | -0.114539 | -0.289855 | 170 |
| 2017-05-31 | 0.033763 | 0.073668 | 87 |
| 2017-06-30 | 0.176277 | 0.155096 | 181 |
| 2017-07-31 | -0.163553 | -0.118820 | 199 |
| 2017-08-31 | -0.286773 | -0.271394 | 192 |
| 2017-09-29 | 0.125058 | 0.209481 | 209 |
| 2017-10-31 | 0.028529 | 0.007986 | 201 |
| 2017-11-30 | 0.106772 | 0.030164 | 207 |
| 2017-12-29 | -0.177017 | -0.281476 | 209 |
| 2018-01-31 | -0.126426 | -0.139797 | 208 |
| 2018-02-28 | -0.307423 | -0.341508 | 109 |
| 2018-03-28 | -0.042707 | -0.120920 | 205 |
| 2018-04-30 | -0.194676 | -0.269147 | 206 |
| 2018-05-31 | -0.326881 | -0.395315 | 205 |
| 2018-06-29 | 0.060796 | -0.048043 | 205 |
| 2018-07-31 | -0.074131 | -0.045319 | 203 |
| 2018-08-31 | -0.341222 | -0.435651 | 206 |
| 2018-09-28 | 0.273638 | 0.360580 | 206 |
| 2018-10-31 | -0.109559 | -0.176544 | 100 |
| 2018-11-30 | 0.054567 | 0.220843 | 200 |
| 2018-12-31 | -0.239918 | -0.342628 | 197 |
| 2019-01-31 | -0.084034 | -0.037088 | 198 |
| 2019-02-28 | 0.076315 | 0.289493 | 197 |
| 2019-03-29 | -0.211498 | -0.447550 | 197 |
| 2019-04-30 | -0.234134 | -0.108030 | 193 |
| 2019-05-31 | -0.354405 | -0.306046 | 193 |
| 2019-06-28 | -0.157578 | -0.340727 | 190 |
| 2019-07-31 | -0.151265 | -0.353873 | 103 |
| 2019-08-30 | 0.022504 | -0.167393 | 159 |
| 2019-09-30 | 0.061945 | 0.130764 | 159 |
| 2019-10-31 | 0.006230 | 0.311635 | 148 |
| 2019-11-29 | -0.077722 | -0.106414 | 149 |
| 2019-12-31 | -0.168494 | -0.152592 | 147 |
| 2020-01-31 | -0.281719 | -0.461531 | 143 |
| 2020-02-28 | -0.102523 | -0.416556 | 143 |
| 2020-03-31 | 0.153548 | 0.143127 | 130 |
| 2020-04-30 | 0.063068 | -0.148195 | 139 |
| 2020-05-29 | 0.086580 | 0.376266 | 138 |
| 2020-06-30 | 0.083455 | 0.004933 | 136 |
| 2020-07-31 | 0.228356 | 0.422076 | 131 |
| 2020-08-31 | -0.110502 | -0.369571 | 133 |
| 2020-09-30 | -0.174566 | -0.152462 | 80 |
| 2020-10-30 | 0.213783 | 0.452689 | 128 |
| 2020-11-27 | -0.093709 | 0.059347 | 127 |
| 2020-12-31 | 0.068144 | 0.016032 | 132 |

## §9 Gate 2 — PASS

Dispositive predictions 1 (negative-signed significant IC) and 3 (net spread > 0) both hold. TRAIN authorization satisfied. 
