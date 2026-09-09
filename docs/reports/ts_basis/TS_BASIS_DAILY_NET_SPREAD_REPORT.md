# TS Basis Daily — Net-of-Fee Long/Short Spread

**Script-generated** — `scripts/signal_engine/ts_basis_daily/run_net_spread.py`. Code commit `3f3603d`.

**Generated:** 2026-07-27

**Sign:** positive (long high z_ts, short low z_ts).

**Cadence:** daily (252 formations/year).

**Construction:** z_ts = (basis_now - trailing_mean) / trailing_std, lookback=504d, min_obs=12, winsorize +/-3σ, equal-weight Q5/Q1, ADV-capped 10%, 0.25σ band.


---
## 1. Rank-IC

| Window | n | Mean IC | SD(IC) |
|---|--:|--:|--:|
| TRAIN | 1173 | +0.0486 | 0.1397 |
| HOLDOUT | 495 | +0.0471 | 0.1018 |

---
## 2. Net-of-Fee Spread

| Window | Net > 0? | Gross ann | Net ann | Fee drag | Slippage | Avg turnover | Periods |
|---|:--:|--:|--:|--:|--:|--:|--:|
| **TRAIN** | **PASS** | +98.09% | +60.23% | 3786 bp | 5752 Rs/d | 1.150 | 1173 |
| **HOLDOUT** | **PASS** | +72.86% | +41.44% | 3142 bp | 5280 Rs/d | 1.056 | 495 |

---
## 3. Fee Breakdown (TRAIN)

| Component | Total (Rs) | Share |
|---|---:|--:|
| brokerage | 1,286,280 | 40.9% |
| stt | 674,677 | 21.4% |
| exchange_txn | 283,364 | 9.0% |
| sebi_fee | 13,494 | 0.4% |
| stamp_duty | 616,634 | 19.6% |
| gst | 273,483 | 8.7% |
| **Total fees** | **3,147,932** | 100.0% |

---
## 4. Gate

| Window | Gross ann | Net ann | Net > 0? |
|---|--:|--:|:--:|
| TRAIN | +98.09% | +60.23% | PASS |
| HOLDOUT | +72.86% | +41.44% | PASS |

**NET-SPREAD GATE: PASS** — Net > 0 on both TRAIN and HOLDOUT.

