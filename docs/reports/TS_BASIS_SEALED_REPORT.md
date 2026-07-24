# TS Basis — SEALED Read Report

**One-shot, script-generated** — `scripts/signal_engine/ts_basis/run_sealed.py`. Code commit `d177a04`.

**Run timestamp:** 2026-07-24T02:40:22.736702Z

**Protocol:** `TS_BASIS_SEALED_READ_PROTOCOL.md` (frozen, SHA `8bdec782...`).

**Pre-registration:** `TS_BASIS_PHASE0_PRE_REGISTRATION.md` (frozen, SHA `07265b50...`).

**Window:** SEALED 2023-01-01 -> 2026-07-20 (42 formations, 42 with IC).

**Sign:** +1 (long high z_ts, short low z_ts).


---
## 1. Rank-IC

| Metric | Value |
|---|---|
| Mean IC | +0.076687 |
| SD(IC) | 0.084419 |
| n | 42 |
| t-stat | 5.8872 |
| p (one) | 3.130120e-07 |
| AC1 | 0.1505 |
| Sign correct | PASS |
| IC gate (α=0.05) | **PASS** |

---
## 2. Net-of-Fee Spread

| Metric | Value |
|---|---|
| Gross ann | +24.27% |
| Net ann | +22.57% |
| Fee drag | 170 bp |
| Turnover | 1.485 |
| Return periods | 41 |
| Net > 0 | **PASS** |

### Fee Breakdown

| Component | Total (Rs) | Share |
|---|---:|--:|
| brokerage | 88,900 | 50.4% |
| stt | 49,839 | 28.3% |
| exchange_txn | 12,347 | 7.0% |
| sebi_fee | 619 | 0.4% |
| stamp_duty | 6,189 | 3.5% |
| gst | 18,336 | 10.4% |
| **Total** | **176,230** | 100.0% |

---
## 3. Power (context only)

Power at n*=42: **1.0000** (hurdle 0.80). SEALED is sign+spread confirmation.

---
## 4. SEALED Gate (per protocol §4)

| Condition | Result | Detail |
|---|---|---|
| IC sig (α=0.05, one-sided) | PASS | t=5.89, p=3.130120e-07 |
| Net > 0 | PASS | +22.57% |

**SEALED VERDICT: PASS** — TS Basis is a validated alpha across discovery (TRAIN) + two out-of-sample windows (HOLDOUT, SEALED). The research phase closes. Work moves to implementation.

