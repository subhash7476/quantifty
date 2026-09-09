# NiftyShield - Regime Horizon Diagnostic

Read-only. Run before the Q1(b) redesign to decide whether moving the entry to the open is worth doing at all.

**Question.** The structure choice is directional: BullTrend buys a bull put spread, BearTrend a bear call spread. For that to pay, the predicted regime must separate the *direction of the move the position actually holds*. The live audit found 0 of 6 directional calls hit over the 13:00-15:15 window. Six observations settle nothing. This tests the same question over every session the prediction artifact covers.

**Method.** `daytype_predictions.csv` (10220 rows, 3406 sessions) joined to Nifty 1m candles. The return runs from the checkpoint FORWARD to the session close - never from the open, because anything before the checkpoint has already happened and cannot be predicted. Grouped by *predicted* label. Separation is the mean difference between the BullTrend and BearTrend groups with a 4,000-sample bootstrap 95% CI. A CI excluding zero means the call carries direction; one spanning zero means it does not.

**Out-of-sample split.** `train_daytype_classifier.py` trains on 2023-24 and validates on 2025. Sessions up to 2022-12-31 predate the training window and are the honest read; the full-sample rows are shown alongside and should be read as partly in-sample.

## Out-of-sample (through 2022-12-31)

| checkpoint | predicted | n | mean checkpoint->close % | median % | share closing up | mean abs move (pts) |
|---|---|---:|---:|---:|---:|---:|
| 10am | BullTrend | 819 | +0.082 | +0.099 | 57% | 44 |
| 10am | Choppy | 1175 | -0.178 | -0.207 | 39% | 66 |
| 10am | BearTrend | 692 | +0.093 | +0.046 | 55% | 42 |
| 11am | BullTrend | 883 | +0.059 | +0.077 | 56% | 46 |
| 11am | Choppy | 791 | -0.220 | -0.216 | 38% | 64 |
| 11am | BearTrend | 1011 | +0.058 | +0.033 | 53% | 39 |
| 13pm | BullTrend | 805 | +0.095 | +0.107 | 62% | 38 |
| 13pm | Choppy | 1078 | +0.021 | +0.031 | 54% | 31 |
| 13pm | BearTrend | 801 | -0.160 | -0.124 | 40% | 49 |

**Separation (BullTrend minus BearTrend, checkpoint->close %):**

| checkpoint | mean difference | 95% CI | n Bull | n Bear | carries direction? |
|---|---:|---|---:|---:|---|
| 10am | -0.0105 pp | [-0.0730, +0.0505] | 819 | 692 | no - CI spans zero |
| 11am | +0.0010 pp | [-0.0537, +0.0575] | 883 | 1011 | no - CI spans zero |
| 13pm | +0.2546 pp | [+0.1967, +0.3123] | 805 | 801 | **YES** |

## Full sample

| checkpoint | predicted | n | mean checkpoint->close % | median % | share closing up | mean abs move (pts) |
|---|---|---:|---:|---:|---:|---:|
| 10am | BullTrend | 1034 | +0.094 | +0.108 | 58% | 52 |
| 10am | Choppy | 1425 | -0.177 | -0.212 | 38% | 76 |
| 10am | BearTrend | 947 | +0.091 | +0.047 | 55% | 46 |
| 11am | BullTrend | 1126 | +0.066 | +0.081 | 57% | 51 |
| 11am | Choppy | 1019 | -0.195 | -0.202 | 38% | 72 |
| 11am | BearTrend | 1260 | +0.054 | +0.033 | 53% | 42 |
| 13pm | BullTrend | 1052 | +0.078 | +0.084 | 60% | 41 |
| 13pm | Choppy | 1357 | +0.022 | +0.026 | 53% | 34 |
| 13pm | BearTrend | 993 | -0.136 | -0.111 | 41% | 52 |

**Separation (BullTrend minus BearTrend, checkpoint->close %):**

| checkpoint | mean difference | 95% CI | n Bull | n Bear | carries direction? |
|---|---:|---|---:|---:|---|
| 10am | +0.0035 pp | [-0.0454, +0.0530] | 1034 | 947 | no - CI spans zero |
| 11am | +0.0113 pp | [-0.0352, +0.0564] | 1126 | 1260 | no - CI spans zero |
| 13pm | +0.2142 pp | [+0.1673, +0.2611] | 1052 | 993 | **YES** |
