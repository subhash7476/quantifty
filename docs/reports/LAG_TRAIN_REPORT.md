# LAG Sleeve — TRAIN Report

**Script-generated** — `scripts/signal_engine/lag/run_train.py`. Code commit `7ec088d`.

**Frozen protocol:** `LAG_PHASE0_PRE_REGISTRATION.md` §9 gate 2 (declaration SHA `0092919c…`).

**Windows:** TRAIN 2017-02-28 → 2020-12-31. HOLDOUT (2021-01 → 2022-12) and SEALED (2023-01 → 2026-07) untouched.

## Substrate

| Quantity | Value |
|---|---|
| Formations (total in TRAIN window) | 47 |
| Formations with >= 5 scored names | 47 |
| Mean names per formation | 149 |
| Neutralized signals in TRAIN | 17,635 |

## Rank-IC Results

| Metric | Value |
|---|---|
| Mean IC | -0.030730 |
| SD(IC) | 0.147550 |
| t-stat (simple) | -1.4278 |
| p-value (one-sided) | 9.199532e-01 |
| AC1 | -0.0842 |
| NW t (\|AC1\| <= 0.1) | below trigger, not computed |
| First-half mean IC | -0.032613 |
| Second-half mean IC | -0.028926 |
| Sign matches prediction (positive) | **FAIL** |
| Structural bet (IC >= 0.04) | below bet — India delay not enlarged vs US |

## IC SD Band Check

| Check | Band | Realized | Result |
|---|---|---|:--:|
| IC SD | [0.10, 0.18] | 0.1476 | PASS |

## Quintile Spread (Net of Fees)

| Metric | Value |
|---|---|
| Gross annualized return (L-S) | 0.0092 (0.92%) |
| Net annualized return (L-S) | 0.0031 (0.31%) |
| Q1-Q5 gross spread (last formation) | 0.014876 |
| Fee+slippage drag (annualized) | 60.9 bp |
| Avg turnover per rebalance | 0.7401 |

## Neutralization & Trend-Subsumption

| Check | Value | Result |
|---|---|:--:|
| Raw IC (pre-neutralization) | -0.042451 | — |
| Neutralized IC / raw IC (same sign, >= 0.60) | 0.72, same_sign=True | PASS |
| IC after residualizing on Trend z_trend_neut | -0.017788 | — |
| Not subsumed by Trend (>= 60% of raw, same sign) | ratio=0.58 | **FAIL** — momentum-in-disguise risk |
| (joined 7,016 name-formation pairs with Trend) | | |

## Power Projection (n* = 42, sealed window)

| Method | Power |
|---|---|
| Noncentral-t (simple SD) | 0.0015 |
| Noncentral-t (half-IC) | 0.0105 |
| Hurdle | 0.80 |

## Prediction Outcomes (pre-reg section 11)

| # | Prediction | Result | Detail |
|---|---|---|---|
| 1 | LAG rank-IC positive-signed + significant | **FAIL** | mean_ic=-0.0307 (expected > 0). simple t: -1.4278. Structural bet IC >= 0.04: NO |
| 2 | Diffusion mechanism (cross-autocorr exists) | unconfirmed | a positive significant LAG-IC is itself the demonstration that laggards catch up to leaders; no separate stat computed |
| 3 | Not subsumed by Trend (resid IC >= 60% raw) | **FAIL** | resid_ic=-0.0178, raw_ic=-0.0307, ratio=0.58 |
| 4 | Net quintile spread > 0 | PASS | net spread=0.31% annualized |
| 5 | IC SD in [0.10, 0.18] | PASS | SD=0.1476 |

## IC Series (all formations)

| Formation date | IC | Raw IC | Names |
|---|---|---|---:|
| 2017-02-28 | -0.011835 | 0.033013 | 155 |
| 2017-03-31 | -0.055684 | -0.125641 | 160 |
| 2017-04-28 | 0.028026 | -0.092937 | 158 |
| 2017-05-31 | -0.059739 | -0.182915 | 60 |
| 2017-06-30 | -0.038561 | 0.041982 | 155 |
| 2017-07-31 | -0.074701 | 0.051752 | 160 |
| 2017-08-31 | -0.026262 | -0.099307 | 156 |
| 2017-09-29 | 0.118754 | 0.011360 | 160 |
| 2017-10-31 | 0.015827 | 0.041709 | 161 |
| 2017-11-30 | 0.043505 | 0.018859 | 163 |
| 2017-12-29 | 0.059258 | 0.025928 | 162 |
| 2018-01-31 | 0.013908 | -0.110157 | 163 |
| 2018-02-28 | -0.241746 | -0.248002 | 70 |
| 2018-03-28 | -0.119510 | -0.168503 | 159 |
| 2018-04-30 | -0.116572 | -0.052532 | 174 |
| 2018-05-31 | -0.185468 | -0.352004 | 191 |
| 2018-06-29 | 0.149208 | 0.203995 | 196 |
| 2018-07-31 | -0.003393 | -0.216570 | 200 |
| 2018-08-31 | -0.135576 | -0.249029 | 202 |
| 2018-09-28 | 0.173983 | 0.228563 | 202 |
| 2018-10-31 | -0.212036 | -0.149800 | 89 |
| 2018-11-30 | 0.135972 | 0.411069 | 196 |
| 2018-12-31 | -0.207466 | -0.238001 | 193 |
| 2019-01-31 | -0.069979 | -0.006550 | 194 |
| 2019-02-28 | 0.127218 | 0.357622 | 193 |
| 2019-03-29 | -0.127409 | -0.221408 | 193 |
| 2019-04-30 | -0.119400 | 0.118028 | 189 |
| 2019-05-31 | -0.248718 | -0.261830 | 189 |
| 2019-06-28 | -0.093065 | -0.228014 | 186 |
| 2019-07-31 | -0.153245 | -0.250327 | 84 |
| 2019-08-30 | -0.118096 | -0.146620 | 153 |
| 2019-09-30 | 0.039092 | 0.063690 | 153 |
| 2019-10-31 | 0.091129 | 0.087907 | 137 |
| 2019-11-29 | -0.144529 | -0.171733 | 137 |
| 2019-12-31 | -0.334558 | -0.244603 | 135 |
| 2020-01-31 | -0.260826 | -0.370540 | 132 |
| 2020-02-28 | 0.027122 | 0.039692 | 132 |
| 2020-03-31 | 0.108592 | 0.128407 | 116 |
| 2020-04-30 | 0.045255 | -0.218795 | 126 |
| 2020-05-29 | 0.263539 | 0.270947 | 125 |
| 2020-06-30 | -0.126120 | -0.153253 | 120 |
| 2020-07-31 | 0.328091 | 0.207613 | 112 |
| 2020-08-31 | -0.296389 | -0.391683 | 118 |
| 2020-09-30 | 0.130856 | 0.206117 | 63 |
| 2020-10-30 | 0.084628 | 0.285620 | 114 |
| 2020-11-27 | 0.150010 | 0.103745 | 113 |
| 2020-12-31 | 0.002578 | 0.017950 | 117 |

## §9 Gate 2 — FAIL

Dispositive prediction(s) 1 (positive-signed significant IC) failed. TRAIN authorization NOT satisfied.

**Prediction 1 failure is dispositive:** sign or magnitude failure. LAG is not a viable sleeve.

Per §9: no successor auto-authorized; HOLDOUT and SEALED stay untouched.
