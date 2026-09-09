# TS Basis Daily — Exit Optimization Research

**Script-generated.** Code commit `456f19b`.

**Generated:** 2026-07-28

**Portfolio:** top-5 by z_ts, equal-weight, ADV-capped 10%, 0.25σ band, 5bp slip.


---
## 1. Baseline

| Window | Formations | Ann Gross | Ann Net | Sharpe | Max DD | Avg TO |
|---|---|--:|--:|--:|--:|--:|
| TRAIN-baseline | 1174 | +139.56% | +95.66% | 2.39 | -23.3% | 1.249 |
| HOLDOUT-baseline | 495 | +117.38% | +79.38% | 2.91 | -19.2% | 1.255 |

---
## 2. Exit Rule Experiments (TRAIN)

*Sorted by net return improvement vs baseline.*

| Rule | Ann Net | vs Baseline | Sharpe | Max DD | Avg TO | Exits |
|---|---|--:|--:|--:|--:|--:|
| TP@0.5% | +100.85% | +5.19pp | 2.48 | -23.2% | 1.088 | 4,699 |
| TP@1.0% | +99.64% | +3.98pp | 2.46 | -23.2% | 1.125 | 3,700 |
| TP@1.5% | +98.80% | +3.15pp | 2.44 | -23.2% | 1.151 | 2,858 |
| TP@1%+MaxHold=5d | +98.60% | +2.94pp | 2.44 | -23.2% | 1.157 | 5,140 |
| TP@2%+MaxHold=3d | +98.58% | +2.93pp | 2.44 | -23.2% | 1.157 | 6,102 |
| TP@2.0% | +97.98% | +2.33pp | 2.43 | -23.2% | 1.176 | 2,220 |
| TP@2%+MaxHold=5d | +97.71% | +2.06pp | 2.42 | -23.2% | 1.184 | 4,389 |
| MaxHold=3d | +96.79% | +1.13pp | 2.41 | -23.3% | 1.213 | 4,926 |
| SL@1.0% | +96.07% | +0.41pp | 2.40 | -23.2% | 1.236 | 3,724 |
| SL@1.5% | +95.65% | -0.00pp | 2.39 | -23.2% | 1.249 | 2,931 |
| SL@2.0% | +95.56% | -0.10pp | 2.39 | -23.2% | 1.252 | 2,361 |
| SL@2.5% | +95.38% | -0.28pp | 2.39 | -23.3% | 1.258 | 1,910 |
| MaxHold=10d | +95.15% | -0.50pp | 2.38 | -23.3% | 1.265 | 524 |
| MaxHold=7d | +94.51% | -1.15pp | 2.37 | -23.3% | 1.285 | 1,148 |
| MaxHold=5d | +94.43% | -1.23pp | 2.37 | -23.3% | 1.288 | 2,078 |

---
## 3. HOLDOUT Validation

| Rule | Ann Net | vs Baseline | Sharpe | Max DD | Avg TO | Exits |
|---|---|--:|--:|--:|--:|--:|
| TP@0.5%-HOLDOUT | +83.66% | +4.28pp | 3.02 | -18.9% | 1.101 | 2,002 |
| TP@1.0%-HOLDOUT | +82.65% | +3.26pp | 2.99 | -19.0% | 1.137 | 1,560 |
| TP@1.5%-HOLDOUT | +81.73% | +2.34pp | 2.97 | -19.0% | 1.169 | 1,205 |

---
## 4. Verdict

**PROMOTE:** Best HOLDOUT exit rule improves net return by +4.28pp.

---

**Generated:** 2026-07-28 | **Commit:** `456f19b`

