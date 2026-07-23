# Carry — Weekly vs Monthly Net Spread

**Script-generated** — `scripts/signal_engine/carry/weekly_vs_monthly.py`. Code commit `e0618ed`.

**Generated:** 2026-07-23

**Data:** 207 weekly formations with z_carry_neut (TRAIN 2016-03-31 → 2020-12-31).

**Construction:** Q5 LONG, Q1 SHORT, equal-weight, ADV-capped (10%), 0.25σ no-trade band, futures fees (canonical tiered STT) + 5bp/side slippage.


---

## 1. Results


| Cadence | Formations | Periods | Gross ann | Net ann | Fee drag | Avg turnover |
|---|--:|--:|--:|--:|--:|--:|
| **Weekly** | 207 | 206 | +6.3% | +0.2% | 615 bp | 1.582 |
| **Monthly** | 58 | 57 | +14.4% | +12.8% | 153 bp | 1.440 |

---

## 2. Fee Breakdown


| Cadence | Total Fees (Rs) | Total Slippage (Rs) | Fee/period (Rs) |
|---|--:|--:|--:|
| Weekly | 736,363 | 1,634,853 | 3,557 |
| Monthly | 240,757 | 415,469 | 4,151 |

---

## 3. Head-to-Head


| Metric | Weekly | Monthly | Delta |
|---|--:|--:|--:|
| Net ann | +0.2% | +12.8% | -1265 bp |
| Gross ann | +6.3% | +14.4% | -803 bp |
| Turnover | 1.582 | 1.440 | 1.1x |
| Total fees | Rs 736,363 | Rs 240,757 | 3.1x |

---

## 4. Verdict


**Monthly BEATS weekly** by 1265bp net. The 3.1x higher fee drag (615bp vs 153bp) consumes the fresher signal's gross edge (-803bp).

Monthly rebalancing remains the correct cadence.

