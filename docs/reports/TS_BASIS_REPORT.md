# Time-Series Basis — Strategy Report

**Script-generated** — `scripts/signal_engine/carry/ts_basis_reversal.py`. Code commit `8f4673b`.

**Generated:** 2026-07-23

**Data:** 17,496 z-scores across 113 formations.

**Signal:** z_ts = (basis_now - trailing_mean) / trailing_std, lookback=504d, min_obs=12.

**Direction:** highest z_ts (unusually wide basis) → LONG, lowest z_ts (unusually narrow basis) → SHORT. The basis persists — unusually wide predicts continued outperformance.


---
## 1. Rank-IC

| Window | n | Mean IC | SD(IC) | t |
|---|--:|--:|--:|--:|
| TRAIN | 47 | +0.0894 | 0.1053 | +5.82 |
| HOLDOUT | 24 | +0.0412 | 0.1046 | +1.93 |

---
## 2. Net-of-Fee Spread

| Window | Net > 0? | Gross ann | Net ann | Fee drag | Avg turnover | Formations |
|---|:--:|--:|--:|--:|--:|--:|
| **TRAIN** | **PASS** | +19.72% | +18.05% | 167 bp | 1.533 | 47 |
| **HOLDOUT** | **PASS** | +16.26% | +14.80% | 146 bp | 1.457 | 24 |

---
## 3. Comparison with Cross-Sectional Carry

| Metric | TS Basis Reversal | XS Carry (monthly) | Delta |
|---|--:|--:|--:|
| TRAIN net | +18.1% | +12.8% | +521 bp |
| HOLDOUT net | +14.8% | +7.0% | +784 bp |

---
## 4. Verdict

**VIABLE** — positive net spread on both TRAIN (+18.1%) and HOLDOUT (+14.8%). The time-series basis signal substantially outperforms cross-sectional carry (TRAIN +521bp, HOLDOUT +784bp).


The signal measures 'how wide is this name's basis relative to its own history' rather than 'how wide relative to other names today.' Construction is simpler — no dividend adjustment, cross-sectional demeaning, or beta/sector neutralization required. The time-series and cross-sectional dimensions are moderately correlated (both read from the same underlying basis data) but capture different edges — combining them could produce a stronger composite.

