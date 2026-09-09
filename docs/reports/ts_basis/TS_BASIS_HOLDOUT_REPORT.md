# TS Basis — HOLDOUT Read Report

**Script-generated** — `scripts/signal_engine/ts_basis/run_holdout.py`. Code commit `42d17fc`.

**Generated:** 2026-07-25

**Pre-registration:** `TS_BASIS_PHASE0_PRE_REGISTRATION.md` (frozen, SHA-256 `07265b507179667588d06cb35c1e98c72bd065a3bbf95cf9a6c7d8b996a1ad84`).

**Window:** HOLDOUT 2021-01-01 -> 2022-12-31 (24 formations with IC, 23 return periods).

**Sign:** +1 (long high z_ts, short low z_ts).

**Evidence floor:** Bonferroni α = 0.025 (m ≥ 2: cross-sectional carry + TS Basis sign discovery on TRAIN). One-sided test in the pre-committed direction.


---
## 1. Rank-IC

| Metric | Value |
|---|---|
| Mean IC | +0.041182 |
| SD(IC) | 0.103086 |
| n (formations) | 24 |
| t-stat | 1.9571 |
| p-value (one-sided) | 3.128925e-02 |
| AC1 | -0.1205 |
| Sign matches declaration (+1) | PASS |
| Significant at α=0.025 | **FAIL** |

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
| Positive-sign IC significant (α=0.025, one-sided) | **FAIL** | IC=+0.0412, t=1.96, p=3.128925e-02 |
| Net long/short spread > 0 | PASS | +14.80% annualized |

**HOLDOUT VERDICT: INCONCLUSIVE** — TS Basis does NOT clear the pre-registered significance threshold (IC +{mean_ic:+.4f}, p=0.0313 > α=0.025), but net spread IS positive (+14.8%). Per §6, falsification requires the CONJUNCTION of insignificance AND net ≤ 0 — neither being negative-signed, this clause is not met. The HOLDOUT is inconclusive: it neither confirms nor falsifies. The SEALED window (2023-2026) was opened on this gate and its read was therefore NOT authorized by the protocol. The SEALED result (+22.6%, p=3.1e-07) is a genuine out-of-sample test of a pre-specified hypothesis (construction SHA-locked before the read), but reached through a gate that did not hold — a selection concern, not a signal-quality concern.

