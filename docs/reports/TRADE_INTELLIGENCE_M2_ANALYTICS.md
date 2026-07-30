# Trade Intelligence — M2 Analytics

**Script-generated.** Code commit `dcfad45`.

**Generated:** 2026-07-30

**Data:** 10,180 total trades, 9,924 closed.

---
## 1. TRAIN vs HOLDOUT Summary

| Metric | TRAIN | HOLDOUT | Delta |
|---|---|--:|--:|--:|
| Trades | 6,980 | 2,944 | -4,036 |
| Mean Return (%) | +0.31 | +0.25 | -0.06 |
| Median Return (%) | +0.26 | +0.27 | +0.01 |
| Win Rate (%) | +55.46 | +55.26 | -0.19 |
| TP Rate (%) | +44.89 | +44.70 | -0.18 |
| SL Rate (%) | +26.23 | +26.66 | +0.43 |
| Avg Days Held | 2 | 2 | -0 |
| Std Return (%) | +4.08 | +2.90 | -1.18 |

---
## 2. Exit Reason Analysis

| Exit Reason | TRAIN n | TRAIN Win | TRAIN Mean | HOLDOUT n | HOLDOUT Win | HOLDOUT Mean |
|---|---|--:|--:|--:|--:|--:|
| EXIT_SIGNAL | 3,847 | 19.2% | -1.723% | 1,628 | 19.1% | -1.507% |
| EXIT_TP | 3,133 | 100.0% | +2.805% | 1,316 | 100.0% | +2.416% |

---
## 3. P&L Distribution

**TRAIN** — p1=-10.21% p5=-4.53% p25=-1.09% p50=+0.26% p75=+1.66% p95=+5.19% p99=+11.22% mean=+0.31% std=+4.08%
**HOLDOUT** — p1=-7.83% p5=-4.10% p25=-1.12% p50=+0.27% p75=+1.59% p95=+4.60% p99=+8.21% mean=+0.25% std=+2.90%

---
## 4. Monthly Win Rate

| Year-Month | TRAIN n | TRAIN Win | HOLDOUT n | HOLDOUT Win |
|---|---|--:|--:|--:|
| 2016-04 | 10 | 60.0% | 0 | 0.0% |
| 2016-05 | 130 | 60.8% | 0 | 0.0% |
| 2016-06 | 110 | 59.1% | 0 | 0.0% |
| 2016-07 | 112 | 50.9% | 0 | 0.0% |
| 2016-08 | 125 | 61.6% | 0 | 0.0% |
| 2016-09 | 116 | 53.4% | 0 | 0.0% |
| 2016-10 | 115 | 46.1% | 0 | 0.0% |
| 2016-11 | 122 | 54.9% | 0 | 0.0% |
| 2016-12 | 127 | 47.2% | 0 | 0.0% |
| 2017-01 | 128 | 53.1% | 0 | 0.0% |
| 2017-02 | 112 | 60.7% | 0 | 0.0% |
| 2017-03 | 135 | 60.0% | 0 | 0.0% |
| 2017-04 | 107 | 54.2% | 0 | 0.0% |
| 2017-05 | 139 | 56.1% | 0 | 0.0% |
| 2017-06 | 119 | 52.1% | 0 | 0.0% |
| 2017-07 | 118 | 61.0% | 0 | 0.0% |
| 2017-08 | 96 | 49.0% | 0 | 0.0% |
| 2017-09 | 120 | 57.5% | 0 | 0.0% |
| 2017-10 | 126 | 57.9% | 0 | 0.0% |
| 2017-11 | 148 | 54.1% | 0 | 0.0% |
| 2017-12 | 133 | 54.1% | 0 | 0.0% |
| 2018-01 | 152 | 56.6% | 0 | 0.0% |
| 2018-02 | 117 | 53.0% | 0 | 0.0% |
| 2018-03 | 125 | 56.0% | 0 | 0.0% |
| 2018-04 | 152 | 52.6% | 0 | 0.0% |
| 2018-05 | 130 | 52.3% | 0 | 0.0% |
| 2018-06 | 144 | 57.6% | 0 | 0.0% |
| 2018-07 | 133 | 48.9% | 0 | 0.0% |
| 2018-08 | 103 | 63.1% | 0 | 0.0% |
| 2018-09 | 114 | 52.6% | 0 | 0.0% |
| 2018-10 | 144 | 51.4% | 0 | 0.0% |
| 2018-11 | 121 | 55.4% | 0 | 0.0% |
| 2018-12 | 132 | 59.8% | 0 | 0.0% |
| 2019-01 | 142 | 62.0% | 0 | 0.0% |
| 2019-02 | 133 | 51.1% | 0 | 0.0% |
| 2019-03 | 125 | 59.2% | 0 | 0.0% |
| 2019-04 | 114 | 50.9% | 0 | 0.0% |
| 2019-05 | 135 | 54.8% | 0 | 0.0% |
| 2019-06 | 142 | 47.9% | 0 | 0.0% |
| 2019-07 | 138 | 55.1% | 0 | 0.0% |
| 2019-08 | 119 | 52.1% | 0 | 0.0% |
| 2019-09 | 119 | 57.1% | 0 | 0.0% |
| 2019-10 | 106 | 64.2% | 0 | 0.0% |
| 2019-11 | 122 | 58.2% | 0 | 0.0% |
| 2019-12 | 109 | 58.7% | 0 | 0.0% |
| 2020-01 | 132 | 54.5% | 0 | 0.0% |
| 2020-02 | 113 | 55.8% | 0 | 0.0% |
| 2020-03 | 159 | 55.3% | 0 | 0.0% |
| 2020-04 | 123 | 62.6% | 0 | 0.0% |
| 2020-05 | 117 | 53.0% | 0 | 0.0% |
| 2020-06 | 127 | 48.8% | 0 | 0.0% |
| 2020-07 | 113 | 48.7% | 0 | 0.0% |
| 2020-08 | 96 | 56.2% | 0 | 0.0% |
| 2020-09 | 124 | 60.5% | 0 | 0.0% |
| 2020-10 | 120 | 58.3% | 0 | 0.0% |
| 2020-11 | 120 | 58.3% | 0 | 0.0% |
| 2020-12 | 117 | 60.7% | 0 | 0.0% |
| 2021-01 | 0 | 0.0% | 10 | 70.0% |
| 2021-02 | 0 | 0.0% | 120 | 60.0% |
| 2021-03 | 0 | 0.0% | 115 | 56.5% |
| 2021-04 | 0 | 0.0% | 119 | 55.5% |
| 2021-05 | 0 | 0.0% | 130 | 50.8% |
| 2021-06 | 0 | 0.0% | 103 | 47.6% |
| 2021-07 | 0 | 0.0% | 104 | 57.7% |
| 2021-08 | 0 | 0.0% | 114 | 49.1% |
| 2021-09 | 0 | 0.0% | 131 | 54.2% |
| 2021-10 | 0 | 0.0% | 127 | 64.6% |
| 2021-11 | 0 | 0.0% | 125 | 56.0% |
| 2021-12 | 0 | 0.0% | 150 | 59.3% |
| 2022-01 | 0 | 0.0% | 137 | 58.4% |
| 2022-02 | 0 | 0.0% | 134 | 55.2% |
| 2022-03 | 0 | 0.0% | 127 | 56.7% |
| 2022-04 | 0 | 0.0% | 134 | 54.5% |
| 2022-05 | 0 | 0.0% | 142 | 47.9% |
| 2022-06 | 0 | 0.0% | 141 | 57.4% |
| 2022-07 | 0 | 0.0% | 147 | 51.0% |
| 2022-08 | 0 | 0.0% | 121 | 52.1% |
| 2022-09 | 0 | 0.0% | 125 | 55.2% |
| 2022-10 | 0 | 0.0% | 128 | 54.7% |
| 2022-11 | 0 | 0.0% | 134 | 58.2% |
| 2022-12 | 0 | 0.0% | 126 | 56.3% |

---
## 5. Sector × Quintile Expectancy

*Mean return (%), min 30 trades per cell.*

| Sector | Quintile | n | Mean Ret |
|---|---|--:|--:|
| Automobile and Auto Components | SHORT | 318 | +0.08% |
| Automobile and Auto Components | SHORT | 112 | +0.42% |
| Automobile and Auto Components | LONG | 442 | +0.31% |
| Capital Goods | SHORT | 136 | +0.20% |
| Capital Goods | SHORT | 68 | +0.42% |
| Capital Goods | LONG | 221 | +0.57% |
| Chemicals | SHORT | 122 | -0.20% |
| Chemicals | LONG | 123 | +0.43% |
| Construction | SHORT | 64 | +0.51% |
| Construction | SHORT | 30 | +0.40% |
| Construction | LONG | 84 | +0.18% |
| Construction Materials | SHORT | 93 | +0.16% |
| Construction Materials | LONG | 183 | +0.43% |
| Consumer Durables | SHORT | 119 | +0.85% |
| Consumer Durables | SHORT | 34 | +0.23% |
| Consumer Durables | LONG | 265 | +0.49% |
| Consumer Services | SHORT | 79 | +0.41% |
| Consumer Services | LONG | 120 | -0.14% |
| Fast Moving Consumer Goods | SHORT | 204 | +0.07% |
| Fast Moving Consumer Goods | SHORT | 62 | -0.47% |
| Fast Moving Consumer Goods | LONG | 318 | +0.18% |
| Financial Services | SHORT | 878 | +0.23% |
| Financial Services | SHORT | 452 | +0.35% |
| Financial Services | LONG | 1,264 | +0.24% |
| Healthcare | SHORT | 274 | +0.20% |
| Healthcare | SHORT | 156 | +0.51% |
| Healthcare | LONG | 462 | +0.26% |
| Information Technology | SHORT | 288 | +0.43% |
| Information Technology | SHORT | 70 | -0.07% |
| Information Technology | LONG | 323 | +0.34% |
| Media Entertainment & Publication | SHORT | 70 | +0.28% |
| Media Entertainment & Publication | LONG | 95 | +1.30% |
| Metals & Mining | SHORT | 209 | +0.68% |
| Metals & Mining | SHORT | 119 | -0.15% |
| Metals & Mining | LONG | 256 | +0.58% |
| Oil Gas & Consumable Fuels | SHORT | 288 | +0.40% |
| Oil Gas & Consumable Fuels | SHORT | 110 | +0.38% |
| Oil Gas & Consumable Fuels | LONG | 281 | +0.15% |
| Power | SHORT | 137 | +0.15% |
| Power | LONG | 149 | +0.34% |
| Realty | SHORT | 38 | +1.21% |
| Realty | LONG | 50 | -0.24% |
| Services | SHORT | 87 | -0.02% |
| Services | LONG | 129 | +0.90% |
| Telecommunication | SHORT | 105 | +0.60% |
| Telecommunication | LONG | 167 | -0.66% |
| Textiles | SHORT | 37 | +0.88% |
| Textiles | LONG | 60 | +0.36% |

---
## 6. Recovery Filter × Exit Reason

*Mean return by recovery state and exit type.*

| Reverting? | Exit | n | Win Rate | Mean Ret | Avg Days |
|---|---|--:|--:|--:|--:|
| No | EXIT_SIGNAL | 5,143 | 19.2% | -1.637% | 2.5 |
| No | EXIT_TP | 4,222 | 100.0% | +2.689% | 2.2 |
| Yes | EXIT_SIGNAL | 332 | 18.7% | -1.997% | 2.9 |
| Yes | EXIT_TP | 227 | 100.0% | +2.722% | 2.6 |

---
## 7. Holding Period Distribution by Exit Type

| Exit Reason | Avg Days | Med Days | p75 Days | Win Rate |
|---|---|--:|--:|--:|
| EXIT_TP | 2.3 | 1 | 3 | 100.0% |
| EXIT_SIGNAL | 2.5 | 1 | 3 | 19.2% |

---
## 8. Top Failure Clusters

*3-feature combinations with lowest mean return, min 100 trades.*

| Sector | Reverting | Exit | n | Mean Ret | Win Rate |
|---|---|--:|--:|--:|
| Financial Services | Yes | EXIT_SIGNAL | 82 | -2.450% | 25.6% |
| Telecommunication | No | EXIT_SIGNAL | 165 | -2.431% | 8.5% |
| Consumer Services | No | EXIT_SIGNAL | 110 | -2.314% | 21.8% |
| Metals & Mining | No | EXIT_SIGNAL | 272 | -2.148% | 18.4% |
| Media Entertainment & Publication | No | EXIT_SIGNAL | 83 | -1.934% | 18.1% |
| Textiles | No | EXIT_SIGNAL | 57 | -1.882% | 19.3% |
| Financial Services | No | EXIT_SIGNAL | 1,380 | -1.877% | 16.3% |
| Power | No | EXIT_SIGNAL | 147 | -1.767% | 18.4% |
| Chemicals | No | EXIT_SIGNAL | 135 | -1.759% | 18.5% |
| Services | No | EXIT_SIGNAL | 107 | -1.741% | 15.9% |
| Construction | No | EXIT_SIGNAL | 94 | -1.689% | 21.3% |
| Realty | No | EXIT_SIGNAL | 59 | -1.675% | 20.3% |
| Oil Gas & Consumable Fuels | No | EXIT_SIGNAL | 349 | -1.517% | 20.1% |
| Information Technology | No | EXIT_SIGNAL | 351 | -1.448% | 23.4% |
| Capital Goods | No | EXIT_SIGNAL | 210 | -1.436% | 15.2% |

---

**Generated:** 2026-07-30 | **Commit:** `dcfad45`

