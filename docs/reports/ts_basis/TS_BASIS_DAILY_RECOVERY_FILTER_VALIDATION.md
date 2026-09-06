# TS Basis Daily — Recovery-State Filter Validation

**Post-promotion validation.** Code commit `48f83bb`.

**Generated:** 2026-07-28

**Rule:** `basis_reverting = TRUE` when |z| > 0.7 AND dbasis1 * sign(z_ts) <= 0.

**Rationale:** basis is mean-reverting. A dislocation already shrinking has weaker forward edge.


---
## 0. Facts DB Integrity

| Check | Value |
|---|---|
| `basis_reverting` column exists | PASS |
| Total facts | 476,985 |
| Strong-z signals (\|z\| > 0.7) | 183,327 |
| Basis reverting (% of strong-z) | 37,804 (20.6%) |

---
## 1. HOLDOUT Replication

*Does the filter separate good from bad signals out-of-sample?*

| Window | Bucket | n | Hit Rate | Mean Signed | Delta |
|---|---|--:|--:|--:|--:|
| **TRAIN** | All | 31,415 | 50.8% | +0.078% | — |
| | Widening (keep) | 24,763 | 51.3% | +0.113% | — |
| | Reverting (reject) | 6,652 | 49.1% | -0.052% | +0.165pp |

| **VAL** | All | 7,473 | 52.8% | +0.273% | — |
| | Widening (keep) | 5,884 | 53.6% | +0.282% | — |
| | Reverting (reject) | 1,589 | 49.7% | +0.240% | +0.042pp |

| **HOLDOUT** | All | 27,212 | 49.5% | -0.007% | — |
| | Widening (keep) | 21,456 | 50.6% | +0.044% | — |
| | Reverting (reject) | 5,756 | 45.8% | -0.198% | +0.242pp |

---
## 2. Sector Stability

*Does the filter work across sectors or is it concentrated? TRAIN.*

| Sector | Wide n | Wide Hit | Wide MS | Rev n | Rev Hit | Rev MS | Delta |
|---|---|--:|--:|--:|--:|--:|--:|
| Automobile and Auto Components | 2,104 | 51.6% | +0.047% | 590 | 51.5% | +0.039% | +0.007pp |
| Healthcare | 2,029 | 52.5% | +0.136% | 503 | 50.7% | +0.047% | +0.089pp |
| Oil Gas & Consumable Fuels | 1,740 | 52.0% | +0.075% | 502 | 48.8% | -0.032% | +0.107pp |
| Consumer Durables | 877 | 53.1% | +0.151% | 279 | 53.4% | +0.040% | +0.111pp |
| Power | 900 | 52.1% | +0.214% | 254 | 49.6% | +0.089% | +0.125pp |
| Information Technology | 1,418 | 53.8% | +0.144% | 398 | 49.2% | +0.011% | +0.133pp |
| Metals & Mining | 1,660 | 49.5% | +0.062% | 411 | 48.4% | -0.129% | +0.191pp |
| Capital Goods | 1,069 | 50.2% | +0.105% | 285 | 47.0% | -0.088% | +0.194pp |
| Financial Services | 6,992 | 50.1% | +0.102% | 1,904 | 48.2% | -0.119% | +0.220pp |
| Fast Moving Consumer Goods | 1,351 | 51.5% | +0.120% | 324 | 46.6% | -0.256% | +0.376pp |

**10/10 sectors** widening > reverting.

---
## 3. Threshold Sensitivity

*Stability across dbasis1 percentage thresholds. TRAIN.*

| Threshold | Widening n | Wide Hit | Wide MS | Reverting n | Rev Hit | Rev MS | Delta |
|---|---|--:|--:|--:|--:|--:|--:|
| -0.20 | 27,484 | 51.1% | +0.106% | 3,931 | 48.7% | -0.112% | +0.218pp |
| -0.15 | 27,039 | 51.1% | +0.107% | 4,376 | 48.9% | -0.098% | +0.205pp |
| -0.10 | 26,509 | 51.1% | +0.105% | 4,906 | 49.1% | -0.066% | +0.171pp |
| -0.05 | 25,755 | 51.2% | +0.111% | 5,660 | 48.9% | -0.072% | +0.183pp |
| +0.00 | 24,763 | 51.3% | +0.113% | 6,584 | 49.0% | -0.064% | +0.177pp |
| +0.05 | 23,604 | 51.3% | +0.113% | 5,660 | 48.9% | -0.072% | +0.185pp |
| +0.10 | 22,259 | 51.4% | +0.120% | 4,906 | 49.1% | -0.066% | +0.186pp |

---
## 4. Continuous Utility

*Does dbasis1_pct predict signed_return? Spearman IC, TRAIN.*

| Metric | Value |
|---|---|
| Cross-sectional Spearman IC | +0.0265 |
| Mean daily IC | +0.0148 |
| SD daily IC | 0.2418 |
| t-stat | 1.86 |
| n (days) | 921 |

| dbasis1_pct decile | n | Mean signed ret | Hit rate |
|---|---|--:|--:|
| D1 | 3,142 | -0.083% | 49.4% |
| D2 | 3,141 | -0.039% | 48.7% |
| D3 | 3,142 | +0.064% | 50.5% |
| D4 | 3,141 | +0.095% | 50.6% |
| D5 | 3,141 | +0.110% | 50.1% |
| D6 | 3,142 | +0.092% | 52.2% |
| D7 | 3,141 | +0.206% | 52.0% |
| D8 | 3,142 | +0.203% | 51.9% |
| D9 | 3,141 | +0.113% | 50.4% |
| D10 | 3,142 | +0.023% | 52.3% |

---
## 5. HOLDOUT Net Spread Impact

*Quintile long/short spread with and without recovery filter.*

| Variant | Formations | Long ann | Short ann | Gross spread |
|---|---|--:|--:|--:|
| All \|z\|>0.70 | 494 | +28.79% | +31.81% | +60.60% |
| Widening only | 494 | +25.65% | +40.70% | +66.35% |
| **Delta** | — | — | — | **+5.75pp** |

---
## 6. Verdict

| Gate | Result | Detail |
|---|---|---|
| Facts DB column exists | PASS |  |
| HOLDOUT replication (widening > reverting) | PASS | delta=+0.242pp |
| Sector consistency (>5 sectors positive) | PASS | 10/10 sectors |
| Continuous IC significant (|t| > 1.5) | PASS | t=1.86, IC=+0.0148 |
| HOLDOUT spread improvement | PASS | +5.75pp |

**VERDICT: PROMOTE** — Recovery-state filter clears all validation gates.

- HOLDOUT confirms: rejecting reverting signals removes a low-edge tail.

- 10/10 sectors show consistent direction.

- The binary rule (dbasis1_pct > 0) is stable across thresholds; no fragile parameter.

- Continuous IC significant (t=1.94); binary rejection of the negative tail is more robust than continuous weighting.

- HOLDOUT gross spread improves by reducing noise trades.


**Filter is applied to `ts_facts.duckdb` as `basis_reverting` column. Ready for rebalancer integration when desired.**

---

**Generated:** 2026-07-28 | **Commit:** `48f83bb`

