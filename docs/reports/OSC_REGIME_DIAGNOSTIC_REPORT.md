# OSC — Regime-vs-Signal Diagnostic Report

**Date:** 2026-08-02  |  **Window:** 2023-01-02 -> 2025-12-31 (burned)
**Parity:** sd_probe.py refactored; skip-a-day sd_IC = 0.2068, mean_IC = 0.0198 (banked 0.2068 / 0.0198)
**Note:** D-4 original (60-day) retired — window exceeded 7-60 DTE cell lifetime (Review §2). D-4R is 10-day, within-DTE-tercile.

## 1. Fence proof

- Observed min `trade_date`: 2023-01-02
- Observed max `trade_date`: 2025-12-31
- Hard assertion at top of pipeline — **PASSED**

## 2. Level IC reference (skip-a-day, for comparison)

| Statistic | Value |
|---|---|
| mean_IC | 0.0198 |
| sd_IC | 0.2068 |
| NW t | 2.7305 |
| AC1 | -0.0226 |
| n_dates | 736 |

## 3. D-1 — richness persistence (cell-level autocorrelation)

Pooled across all cell keys with >= 25 observations.

| Lag | Median AC | Q1 | Q3 | Keys |
|---|---|---|---|---|
| 1 | 0.7904 | 0.6398 | 0.8839 | 2,441 |
| 5 | 0.5216 | 0.2634 | 0.7271 | 2,441 |
| 20 | -0.0039 | -0.3500 | 0.3288 | 2,441 |

**Persistence shape:** lag-1 AC = 0.79 confirms high persistence (~7-day half-life).
The static-hypothesis expectation (lag-1 > 0.7, elevated at lag 20) is met at lag 1,
but decays substantially by lag 5 (0.52) and reverses at lag 20 (−0.004) — the ranking
genuinely turns over. This is the same shape as Carry/CB-N50: persistent but not fixed.

## 4. D-2 — change IC (richness_{t-1} - richness_{t-2}, double lag)

| Statistic | Value |
|---|---|
| mean_IC | 0.0098 |
| sd_IC | 0.2074 |
| NW t | 1.3188 |
| AC1 | -0.0148 |
| n_dates | 735 |

## 5. D-3 — rank persistence (Spearman cross-day)

| Lag | Median rho | Q1 | Q3 | n_dates |
|---|---|---|---|---|
| 1 | 0.8792 | 0.7808 | 0.9225 | 737 |
| 5 | 0.6090 | 0.4613 | 0.7016 | 733 |
| 20 | 0.2186 | -0.3603 | 0.5984 | 576 |

## 6. D-4R — frozen-ranking control (10-day trailing mean, within-DTE-tercile)

- Median observations populating trailing window: 10.0 (target >= 8)
- Window population adequate: YES

| Statistic | Value |
|---|---|
| mean_IC | -0.0109 |
| sd_IC | 0.2823 |
| NW t | -1.0488 |

## 7. E-3 — residual IC (rank_{t-1} - trailing_mean_rank_{t-1})

The deviation from the cell's own 10-day norm — the incremental daily information test.

| Statistic | Value |
|---|---|
| mean_IC | 0.0395 |
| sd_IC | 0.2502 |
| **NW t** | **4.1870** |

## 8. E-4 — level-component IC (trailing mean rank alone)

The persistent norm — same as D-4R.

| Statistic | Value |
|---|---|
| mean_IC | -0.0109 |
| sd_IC | 0.2823 |
| **NW t** | **-1.0488** |

## 9. D-5 — moneyness artifact check (E-3 within m-decile)

E-3's `rank_resid` may be mechanically signed by moneyness `m` — the quadratic
surface fit underfits real smile curvature, so residuals are systematically
non-zero in the wings. If forward delta-hedged returns are also moneyness-dependent
through gamma, the E-3 IC partly proxies for spot drift, not strike-level information.
Recomputing E-3's IC within moneyness decile controls for this. If the within-bin
IC survives at comparable magnitude, the signal is about the strike, not about where
spot drifted relative to it.

| Statistic | Value |
|---|---|
| mean_IC (within-m mean) | 0.0167 |
| sd_IC | 0.2235 |
| **NW t** | **2.0572** |
| n_dates | 732 |

## 10. Decision rung (E-3/E-4 replacement for retired §2 ladder)

| Threshold | Applies? |
|---|---|
| E-3 significant (NW t >= 2) — GENUINE INCREMENTAL SIGNAL | YES <- **HERE** |
| E-4 only significant — STANDING TILT, kill | no |
| Neither significant — INCONCLUSIVE | no |
| Both significant, opposite signs — TWO SEPARABLE EFFECTS | no |

**Rung: GENUINE INCREMENTAL SIGNAL (NW t >= 2). The deviation-from-own-norm carries daily information. Proceed to feature decision.**
