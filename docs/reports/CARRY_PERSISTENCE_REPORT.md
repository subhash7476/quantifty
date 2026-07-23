# Carry — Quintile Persistence: Hold vs Rotate

**Script-generated** — `scripts/signal_engine/carry/persistence.py`. Code commit `9da14c2`.

**Generated:** 2026-07-23

**Data:** 211 weekly formations with z_carry_neut (TRAIN window only — neutralize incomplete for HOLDOUT).


---

## 1. Quintile Persistence (% of Q5/Q1 names still in same quintile next week)

If high → monthly hold justified (same names, save fees). If low → weekly rotation justified (names churn, need to re-rank).


| Horizon | Long Persist | Short Persist | N pairs |
|---|--:|--:|--:|
| 1w | 35% | 43% | 210 |
| 2w | 28% | 36% | 209 |
| 3w | 26% | 32% | 208 |
| 4w | 29% | 31% | 207 |

---

## 2. Month-End Survival

Of names in Q5/Q1 at week 0, what fraction remain Q5/Q1 at week 4 (roughly one month later)?


- **Long persistence at month-end:** 29% (median 27%, range 0–100%)

- **Short persistence at month-end:** 31% (median 30%, range 0–83%)


---

## 3. Interpretation


- **Week-to-week persistence:** 35% (long) / 43% (short) of names stay in their quintile from one week to the next.

- **Month-end persistence:** 29% of original Q5 names are still Q5 after 4 weeks.


**Recommendation: ROTATE weekly.** Quintile membership churns rapidly — fewer than half of Q5/Q1 names stay there week to week. Weekly rebalancing captures fresher signals and avoids holding names that have rotated out. The higher fee drag must be weighed against the fresher book.

