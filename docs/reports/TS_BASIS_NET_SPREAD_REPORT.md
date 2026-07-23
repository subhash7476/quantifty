# TS Basis — Net-of-Fee Long/Short Spread

**Script-generated** — `scripts/signal_engine/ts_basis/run_net_spread.py`. Code commit `22bb3dd`.

**Generated:** 2026-07-23

**Protocol:** `TS_BASIS_PHASE0_PRE_REGISTRATION.md` §5.

**Sign:** positive (long high z_ts, short low z_ts).

**Construction:** z_ts = (basis_now - trailing_mean) / trailing_std, lookback=504d, min_obs=12, winsorize +/-3σ, equal-weight Q5/Q1, ADV-capped 10%, 0.25σ band.


---
## 1. Rank-IC

| Window | n | Mean IC | SD(IC) |
|---|--:|--:|--:|
| TRAIN | 47 | +0.0704 | 0.0980 |
| HOLDOUT | 24 | +0.0429 | 0.1010 |

---
## 2. Net-of-Fee Spread

| Window | Net > 0? | Gross ann | Net ann | Fee drag | Slippage | Avg turnover | Formations |
|---|:--:|--:|--:|--:|--:|--:|--:|
| **TRAIN** | **PASS** | +20.05% | +18.38% | 168 bp | 7603 Rs/mo | 1.532 | 47 |
| **HOLDOUT** | **PASS** | +16.26% | +14.80% | 146 bp | 7191 Rs/mo | 1.457 | 24 |

---
## 3. Fee Breakdown (TRAIN)

| Component | Total (Rs) | Share |
|---|---:|--:|
| brokerage | 93,140 | 47.5% |
| stt | 35,734 | 18.2% |
| exchange_txn | 15,008 | 7.7% |
| sebi_fee | 715 | 0.4% |
| stamp_duty | 32,048 | 16.4% |
| gst | 19,347 | 9.9% |
| **Total fees** | **195,992** | 100.0% |

---
## 4. Gate

| Window | Gross ann | Net ann | Net > 0? |
|---|--:|--:|:--:|
| TRAIN | +20.05% | +18.38% | PASS |
| HOLDOUT | +16.26% | +14.80% | PASS |

**GATE VERDICT: PASS** — Net > 0 on both TRAIN and HOLDOUT. Proceed to SEALED.

