# Carry Sleeve — TRAIN Report

**Script-generated** — `scripts/signal_engine/carry/run_train.py`. Code commit `18641ba`.

**Frozen protocol:** `CARRY_PHASE0_PRE_REGISTRATION.md` §9 gate 2.

**Windows:** TRAIN 2016-03-31 → 2020-12-31. HOLDOUT and SEALED untouched.

## Substrate

| Quantity | Value |
|---|---|
| Formations (total in TRAIN window) | 58 |
| Formations with >= 5 scored names | 58 |
| Mean names per formation | 164 |
| Neutralized signals in TRAIN | 22,140 |

## Rank-IC Results

| Metric | Value |
|---|---|
| Mean IC | 0.040911 |
| SD(IC) | 0.082004 |
| t-stat (simple) | 3.7994 |
| p-value (one-sided) | 1.773398e-04 |
| AC1 | 0.1060 |
| t-stat (NW SE, lag=4) | 3.5932 |
| First-half mean IC | 0.026824 |
| Second-half mean IC | 0.054997 |
| Sign matches prediction (negative) | **FAIL** |

## IC SD Band Check

| Check | Band | Realized | Result |
|---|---|---|:--:|
| IC SD | [0.10, 0.18] | 0.0820 | **FAIL** (C2 wide-SD failure pattern) |

## Quintile Spread (Net of Fees)

| Metric | Value |
|---|---|
| Gross annualized return (L−S) | -0.1366 (-13.66%) |
| Net annualized return (L−S) | -0.1463 (-14.63%) |
| Net spread vs baseline | -0.1550 (-15.50%) |
| Q1−Q5 gross spread (last formation) | -0.028768 |
| Fee+slippage drag (annualized) | 96.8 bp |
| Avg turnover per rebalance | 1.1913 |

## Power Projection (n* = 42, sealed window)

| Method | Power |
|---|---|
| Noncentral-t (simple SD) | 0.9375 |
| Noncentral-t (half-IC) | 0.4781 |
| Noncentral-t (NW SD) | 0.9134 |
| Hurdle | 0.80 |
| CLEARS HURDLE | |

## Prediction Outcomes

| # | Prediction | Result | Detail |
|---|---|---|
| 1 | Residual-carry rank-IC negative-signed | **FAIL** | mean_ic=+0.0409 (expected < 0). AC1-corrected t: 3.5932 |
| 2 | IC survives neutralization | PASS | raw IC=+0.0396, neut IC=+0.0409, same_sign=True, mag_ratio=1.03 |
| 3 | Net quintile spread > 0 | **FAIL** | net spread=-14.63% annualized |
| 4 | IC SD in [0.10, 0.18] | **NOTE** | SD=0.0820 — below band (stable, not a stop condition). Pre-reg only flags SD > 0.18 as failure |

## IC Series (all formations)

| Formation date | IC | Raw IC | Names |
|---|---|---|---:|
| 2016-03-31 | 0.085140 | 0.067386 | 169 |
| 2016-04-29 | 0.226791 | 0.184006 | 168 |
| 2016-05-31 | 0.083624 | 0.106432 | 162 |
| 2016-06-30 | 0.095123 | 0.084200 | 168 |
| 2016-07-29 | -0.096388 | -0.171212 | 170 |
| 2016-08-31 | -0.058220 | -0.108961 | 81 |
| 2016-09-30 | -0.052827 | 0.026599 | 170 |
| 2016-10-28 | -0.064197 | -0.163280 | 171 |
| 2016-11-30 | -0.092223 | 0.053976 | 70 |
| 2016-12-30 | 0.088198 | 0.019622 | 173 |
| 2017-01-31 | 0.027794 | 0.021441 | 166 |
| 2017-02-28 | 0.058304 | 0.055077 | 174 |
| 2017-03-31 | -0.062183 | 0.057491 | 173 |
| 2017-04-28 | 0.014515 | -0.094543 | 184 |
| 2017-05-31 | 0.154350 | 0.224458 | 97 |
| 2017-06-30 | 0.064832 | 0.008505 | 201 |
| 2017-07-31 | 0.028135 | -0.079774 | 208 |
| 2017-08-31 | -0.043575 | -0.020548 | 197 |
| 2017-09-29 | 0.171692 | 0.197158 | 210 |
| 2017-10-31 | -0.010765 | -0.017210 | 203 |
| 2017-11-30 | -0.028365 | 0.056956 | 208 |
| 2017-12-29 | -0.099304 | -0.184597 | 209 |
| 2018-01-31 | 0.061717 | -0.075711 | 207 |
| 2018-02-28 | -0.062098 | -0.007993 | 109 |
| 2018-03-28 | 0.009061 | -0.090869 | 206 |
| 2018-04-30 | 0.070773 | -0.048614 | 206 |
| 2018-05-31 | 0.007352 | -0.032034 | 206 |
| 2018-06-29 | 0.124190 | 0.106180 | 205 |
| 2018-07-31 | 0.076458 | 0.091127 | 203 |
| 2018-08-31 | -0.032680 | -0.162987 | 206 |
| 2018-09-28 | 0.126378 | 0.199094 | 204 |
| 2018-10-31 | 0.240708 | 0.109139 | 100 |
| 2018-11-30 | 0.002385 | 0.058940 | 199 |
| 2018-12-31 | 0.082976 | -0.010236 | 198 |
| 2019-01-31 | -0.053774 | -0.077576 | 198 |
| 2019-02-28 | 0.034305 | 0.064789 | 195 |
| 2019-03-29 | -0.003581 | -0.009196 | 194 |
| 2019-04-30 | 0.136506 | 0.073033 | 193 |
| 2019-05-31 | 0.076527 | 0.034815 | 194 |
| 2019-06-28 | 0.091233 | 0.134684 | 159 |
| 2019-07-31 | -0.039911 | -0.130132 | 103 |
| 2019-08-30 | 0.128517 | 0.111852 | 159 |
| 2019-09-30 | 0.100220 | 0.008489 | 148 |
| 2019-10-31 | 0.045127 | 0.002003 | 147 |
| 2019-11-29 | 0.095120 | 0.045709 | 147 |
| 2019-12-31 | 0.058834 | 0.127838 | 144 |
| 2020-01-31 | -0.099004 | 0.177305 | 140 |
| 2020-02-28 | 0.006332 | 0.084387 | 139 |
| 2020-03-31 | 0.075458 | 0.192374 | 133 |
| 2020-04-30 | 0.041628 | 0.166317 | 141 |
| 2020-05-29 | 0.154346 | 0.261880 | 139 |
| 2020-06-30 | -0.062578 | -0.058185 | 136 |
| 2020-07-31 | 0.003399 | -0.168291 | 130 |
| 2020-08-31 | 0.041871 | 0.167343 | 130 |
| 2020-09-30 | 0.015870 | -0.048521 | 80 |
| 2020-10-30 | 0.020498 | 0.139295 | 128 |
| 2020-11-27 | 0.148073 | 0.326243 | 129 |
| 2020-12-31 | 0.160134 | 0.213036 | 133 |

## §9 Gate 2 — FAIL

Predictions [1, 3] failed. TRAIN authorization NOT satisfied. Per §9: sleeve stops here. Sealed window preserved.


**Prediction 1 failure is dispositive** (§11): sign or magnitude failure. Carry is not a viable sleeve. The engine proceeds with Trend as anchor.


**Prediction 3 failure is dispositive** (§11): net spread < 0. Carry cannot clear fees.

