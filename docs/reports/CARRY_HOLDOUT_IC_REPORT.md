# Carry v2 — HOLDOUT Rank-IC Report

**Script-generated** — `scripts/signal_engine/carry/run_holdout.py`. Code commit `42d17fc`.

**Generated:** 2026-07-25

**Pre-registration:** `CARRY_V2_PRE_REGISTRATION.md` (frozen, SHA `74c7311cd84d48db8552f8bacd880b5e43d2264ae3b671aa12e7b3013fe4b1ec`).

**Window:** HOLDOUT 2021-01-31 -> 2022-12-31 (23 formations with IC).

**Sign:** +1 (long high residual carry, short low).

**Evidence floor:** Bonferroni α = 0.025 (m = 2: v1 falsified, v2 re-registered). One-sided test in the pre-committed direction.


---
## 1. Rank-IC (Spearman)

| Metric | Value |
|---|---|
| Mean IC | +0.054426 |
| SD(IC) | 0.078960 |
| n | 23 |
| t-stat | 3.3057 |
| p-value (one-sided) | 1.609096e-03 |
| AC1 | -0.0960 |
| Sign matches declaration (+1) | PASS |
| Significant at α=0.025 | **PASS** |

---
## 2. Comparison with pre-registered predictions

- **Pre-registered IC band (v2 §5, prediction 3):** +0.03 to +0.045

- **Realized IC:** +0.0544 — outside the band on the upside


---
## 3. Gate

| Condition | Result |
|---|---|
| Positive-sign IC at Bonferroni α=0.025 | PASS |
| Net spread > 0 (CARRY_NET_SPREAD_REPORT.md) | PASS (+6.96%) |

**HOLDOUT IC GATE: PASS** — Carry v2 clears the pre-registered rank-IC condition. Combined with net > 0, both §4.1 acceptance criteria are met. The SEALED read (+20.52%) was substantively justified.

