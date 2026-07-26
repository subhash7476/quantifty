# IVOL Sleeve — HOLDOUT Report

**Script-generated** — `scripts/signal_engine/ivol/run_holdout.py`. Code commit `15ed26c`.

**Frozen protocol:** `IVOL_PHASE0_PRE_REGISTRATION.md` §9 gate 3 (declaration SHA `d7ebcbcc…`).

**Windows:** HOLDOUT 2021-01-31 → 2022-12-31. SEALED (2023-01 → 2026-07) still untouched.

**No parameter touched between TRAIN and HOLDOUT** — the frozen `build_ivol.py` signal is evaluated unchanged on the HOLDOUT window.

## Self-check (TRAIN re-derived, must match frozen TRAIN report)

| Quantity | Re-derived | Frozen ref | Match |
|---|---|---|:--:|
| TRAIN mean IC | -0.054596 | -0.054596 | PASS |
| TRAIN net spread | 0.0596 | 0.0596 | PASS |

## HOLDOUT Results

| Metric | TRAIN | HOLDOUT |
|---|---|---|
| Formations | 47 | 23 |
| Mean names/formation | 167 | 170 |
| Mean IC | -0.054596 | -0.029470 |
| SD(IC) | 0.164894 | 0.106069 |
| t-stat (simple) | -2.2699 | -1.3325 |
| p-value (neg-direction) | — | 9.817478e-02 |
| AC1 | 0.0521 | -0.0936 |
| Gross annualized (L-S) | 6.56% | 2.72% |
| Net annualized (L-S) | 5.96% | 2.16% |
| Avg turnover | 0.6883 | 0.6500 |

## Gate-3 Persistence Check

| Check | TRAIN | HOLDOUT | Result |
|---|---|---|:--:|
| Sign persists (negative) | -0.0546 | -0.0295 | PASS |
| Net spread persists (> 0) | 5.96% | 2.16% | PASS |

**Note on significance:** gate 3 tests *persistence* of sign and net spread, not re-significance (the HOLDOUT window is short — 23 formations). Significance is reported above for transparency: HOLDOUT t = -1.3325, p = 9.8175e-02.

## HOLDOUT IC Series

| Formation date | IC | Names |
|---|---|---:|
| 2021-02-26 | -0.105490 | — |
| 2021-03-31 | -0.163882 | — |
| 2021-04-30 | 0.082527 | — |
| 2021-05-31 | 0.026275 | — |
| 2021-06-30 | -0.000053 | — |
| 2021-07-30 | -0.236633 | — |
| 2021-08-31 | 0.067075 | — |
| 2021-09-30 | 0.168753 | — |
| 2021-10-29 | -0.082508 | — |
| 2021-11-30 | 0.066393 | — |
| 2021-12-31 | -0.001249 | — |
| 2022-01-31 | -0.170711 | — |
| 2022-02-28 | 0.065864 | — |
| 2022-03-31 | -0.057020 | — |
| 2022-04-29 | -0.185511 | — |
| 2022-05-31 | -0.182483 | — |
| 2022-06-30 | 0.075004 | — |
| 2022-07-29 | 0.044589 | — |
| 2022-08-30 | -0.037326 | — |
| 2022-09-30 | 0.036844 | — |
| 2022-10-31 | -0.063156 | — |
| 2022-11-30 | 0.024197 | — |
| 2022-12-30 | -0.049306 | — |

## §9 Gate 3 — PASS

The negative sign and positive net spread both persist from TRAIN to HOLDOUT. No parameter was touched. HOLDOUT authorization satisfied.

**Next:** §9 gate 4 (composite power check with Carry) and gate 5 (the one-shot SEALED read, 2023-01 → present). The SEALED window is the final, unrepeatable resource — opened only after the composite check is cleared.
