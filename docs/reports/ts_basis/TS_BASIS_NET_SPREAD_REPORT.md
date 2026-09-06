# TS Basis — Net-of-Fee Long/Short Spread

**Script-generated** — `scripts/signal_engine/ts_basis/run_net_spread.py`. Code commit `b9524cf`.

**Generated:** 2026-07-25

**Protocol:** `TS_BASIS_PHASE0_PRE_REGISTRATION.md` §5.

**Sign:** positive (long high z_ts, short low z_ts).

**Construction:** z_ts = (basis_now - trailing_mean) / trailing_std, lookback=504d, min_obs=12, winsorize +/-3σ, equal-weight Q5/Q1, ADV-capped 10%, 0.25σ band.


---
## 1. Rank-IC

| Window | n | Mean IC | SD(IC) |
|---|--:|--:|--:|
| TRAIN | 47 | +0.0593 | 0.1041 |
| HOLDOUT | 24 | +0.0412 | 0.1031 |

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

**NET-SPREAD GATE: PASS** — Net > 0 on both TRAIN and HOLDOUT.


> **⚠️ RETROACTIVE NOTE (2026-07-25):** This net-spread gate (net > 0) was satisfied, but the HOLDOUT IC gate was NOT — when computed with the pre-registered Spearman estimator, HOLDOUT IC fails at α=0.025 (p=0.0313). Per `TS_BASIS_PHASE0_PRE_REGISTRATION.md` §6, the signal is NOT falsified (net > 0, sign correct) but the HOLDOUT is INCONCLUSIVE. The SEALED read was opened on a confirmation gate that did not hold. See `TS_BASIS_SEALED_REPORT.md` for the de-authorization marker and `TS_BASIS_HOLDOUT_REPORT.md` for the recomputed IC.

