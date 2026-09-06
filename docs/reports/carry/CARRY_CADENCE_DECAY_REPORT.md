# Carry — Cadence Decay / Intra-Month Persistence

**Script-generated** — `scripts/signal_engine/carry/cadence_decay.py`. Code commit `9da14c2`.

**Generated:** 2026-07-23

**Question:** does the carry edge accumulate linearly over the month, or is most earned in week 1-2? Should positions be held to month-end or exited early?


---

## 1. Horizon Quintile Spread (Q5−Q1, equal-weight, bp)


| Horizon | TRAIN Spread (bp) | TRAIN IC | HOLDOUT Spread (bp) | HOLDOUT IC |
|---|--:|--:|--:|--:|
| 1w (5d) | +85 | +0.0581 | +44 | +0.0532 |
| 2w (10d) | +95 | +0.0589 | +41 | +0.0532 |
| 3w (15d) | +96 | +0.0565 | +38 | +0.0462 |
| 1m (21d) | +123 | +0.0562 | +88 | +0.0519 |

---

## 2. Spread Accumulation (% of month-end spread earned by each horizon)


| Horizon | TRAIN % of 1m | HOLDOUT % of 1m |
|---|--:|--:|
| 1w | 69% | 50% |
| 2w | 77% | 46% |
| 3w | 78% | 43% |
| 1m | 100% | 100% |

---

## 3. Quintile Persistence (% of Q5/Q1 names still in calendar at horizon)

Tracks what fraction of the original quintile names are still alive in the price series at each horizon (not re-ranked — just survival). High persistence = same names drive edge throughout month. Low persistence = names churn, edge may depend on rebalancing.


| Horizon | TRAIN Long Persist | TRAIN Short Persist | HOLDOUT Long Persist | HOLDOUT Short Persist |
|---|--:|--:|--:|--:|
| 1w | 100% | 100% | 100% | 100% |
| 2w | 100% | 100% | 100% | 100% |
| 3w | 100% | 100% | 100% | 100% |
| 1m | 100% | 100% | 100% | 100% |

---

## 4. IC Decay Profile


| Horizon | TRAIN IC | TRAIN t | HOLDOUT IC | HOLDOUT t |
|---|--:|--:|--:|--:|
| 1w | +0.0581 | +3.84 | +0.0532 | +2.73 |
| 2w | +0.0589 | +4.57 | +0.0532 | +3.33 |
| 3w | +0.0565 | +4.29 | +0.0462 | +3.06 |
| 1m | +0.0562 | +4.66 | +0.0519 | +3.48 |

---

## 5. Interpretation


- **TRAIN:** week 1 captures **69%** of the full-month spread (+85bp of +123bp).

- **HOLDOUT:** week 1 captures **50%** of the full-month spread (+44bp of +88bp).


**Finding: mixed evidence.** TRAIN and HOLDOUT show different accumulation profiles. Further analysis with statistical thresholds is needed before changing the rebalance cadence.

