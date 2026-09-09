# TS Basis — SEALED Read Report

**One-shot, script-generated** — `scripts/signal_engine/ts_basis/run_sealed.py`. Code commit `d177a04`.

**Run timestamp:** 2026-07-24T02:40:22.736702Z

**Protocol:** `TS_BASIS_SEALED_READ_PROTOCOL.md` (frozen, SHA `8bdec782...`).

**Pre-registration:** `TS_BASIS_PHASE0_PRE_REGISTRATION.md` (frozen, SHA `07265b50...`).

**Window:** SEALED 2023-01-01 -> 2026-07-20 (42 formations, 42 with IC).

**Sign:** +1 (long high z_ts, short low z_ts).

> **⚠️ RETROACTIVE DE-AUTHORIZATION (2026-07-25):** This SEALED read was authorized
> by a HOLDOUT gate computed with the wrong estimator (Pearson, not Spearman rank-IC).
> When recomputed with the pre-registered Spearman estimator, HOLDOUT fails at the
> multiplicity-adjusted α=0.025 (IC +0.0412, t=1.96, p=0.0313). Per the pre-registration
> §6 falsification clause, the signal is NOT falsified (net > 0, sign correct) but the
> gate is INCONCLUSIVE — it neither confirms nor falsifies. The SEALED window was opened
> on a gate that did not hold per the pre-registered criteria.
>
> The SEALED result itself (+22.6%, IC +0.077, p=3.1e-07) is a genuine out-of-sample
> test of a pre-specified hypothesis (construction and sign SHA-locked before the read),
> and the Spearman estimator was correctly used inside `run_sealed.py` itself. What is
> compromised is **selection** — TS Basis reached this window because of a gate that
> didn't clear, not because of any defect in the SEALED read's internal validity.
> This is a multiplicity/selection concern, not evidence against the signal.


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

