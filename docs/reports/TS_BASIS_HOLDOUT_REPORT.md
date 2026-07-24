# TS Basis — HOLDOUT Read Report

**Script-generated** — `scripts/signal_engine/ts_basis/run_holdout.py`. Code commit `5c1f5d2`.

**Generated:** 2026-07-24

**Pre-registration:** `TS_BASIS_PHASE0_PRE_REGISTRATION.md` (frozen, SHA-256 `07265b507179667588d06cb35c1e98c72bd065a3bbf95cf9a6c7d8b996a1ad84`).

**Window:** HOLDOUT 2021-01-01 -> 2022-12-31 (24 formations with IC, 23 return periods).

**Sign:** +1 (long high z_ts, short low z_ts).

**Evidence floor:** Bonferroni α = 0.025 (m ≥ 2: cross-sectional carry + TS Basis sign discovery on TRAIN). One-sided test in the pre-committed direction.


---
## 1. Rank-IC

| Metric | Value |
|---|---|
| Mean IC | +0.042875 |
| SD(IC) | 0.101036 |
| n (formations) | 24 |
| t-stat | 2.0789 |
| p-value (one-sided) | 2.448306e-02 |
| AC1 | -0.0780 |
| Sign matches declaration (+1) | PASS |
| Significant at α=0.025 | **PASS** |

---
## 2. Net-of-Fee Spread

| Metric | Value |
|---|---|
| Gross annualized | +16.26% |
| Net annualized | +14.80% |
| Fee drag | 146 bp |
| Avg turnover | 1.457 |
| Return periods | 23 |
| Net > 0 | **PASS** |

---
## 3. Fee Component Breakdown

| Component | Total (Rs) | Share |
|---|---:|--:|
| brokerage | 41,780 | 52.9% |
| stt | 17,258 | 21.9% |
| exchange_txn | 7,249 | 9.2% |
| sebi_fee | 345 | 0.4% |
| stamp_duty | 3,452 | 4.4% |
| gst | 8,887 | 11.3% |
| **Total fees** | **78,971** | 100.0% |

---
## 4. HOLDOUT Gate (per pre-reg §6)

| Condition | Result | Detail |
|---|---|---|
| Positive-sign IC significant (α=0.025, one-sided) | PASS | IC=+0.0429, t=2.08, p=2.448306e-02 |
| Net long/short spread > 0 | PASS | +14.80% annualized |

**HOLDOUT VERDICT: PASS** — TS Basis clears both pre-registered acceptance criteria on the only clean out-of-sample window. The signal survives multiplicity-adjusted significance (m≥2, α=0.025) and produces a positive net spread under futures fees.

Proceed to SEALED read (2023-01-01 -> 2026-07-20) under `TS_BASIS_SEALED_READ_PROTOCOL.md`. The SEALED protocol must be frozen before the read.

