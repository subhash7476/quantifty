# Carry Sleeve — SEALED Read Report

**One-shot, script-generated** — `scripts/signal_engine/carry/run_sealed.py`. Code commit `0ea419e`.

**Run timestamp:** 2026-07-23T08:17:58.636363Z

**Protocol:** `CARRY_SEALED_READ_PROTOCOL.md` §1–§5 (frozen, SHA-256 `459411ab20374f07dbe531519724574f9625e784d947511885fbb7d92b7874ba`).

**Pre-registration:** `CARRY_V2_PRE_REGISTRATION.md` (frozen, SHA-256 `74c7311cd84d48db8552f8bacd880b5e43d2264ae3b671aa12e7b3013fe4b1ec`).

**Construction:** `CARRY_PHASE0_PRE_REGISTRATION.md` §3–§8 (frozen).

**Window:** SEALED 2023-01-01 → 2026-07-20 (42 formations, 42 with IC).

**Sign:** +1 (long high residual carry, short low).


---

## 1. Rank-IC (Positive-Sign, One-Sided)

| Metric | Value |
|---|---|
| Mean IC | +0.061043 |
| SD(IC) | 0.088053 |
| n (formations) | 42 |
| t-stat (simple) | 4.4928 |
| p-value (one-sided) | 2.817441e-05 |
| AC1 | 0.1346 |
| NW t (|AC1| > 0.1, lag=4) | 4.1021 |
| Sign matches declaration (+1) | PASS |
| Significant at alpha=0.05 | **PASS** |

---

## 2. Net-of-Fee Long/Short Spread

| Metric | Value |
|---|---|
| Gross annualized | +22.23% |
| Net annualized | +20.52% |
| Fee drag | 170.6 bp |
| Slippage (5 bp/side) | 305,601 Rs |
| Avg turnover | 1.466 |
| Return periods | 41 |
| Net > 0 | **PASS** |

### Fee Component Breakdown

| Component | Total (Rs) | Share |
|---|---:|--:|
| brokerage | 100,920 | 53.0% |
| stt | 49,330 | 25.9% |
| exchange_txn | 12,835 | 6.7% |
| sebi_fee | 611 | 0.3% |
| stamp_duty | 6,112 | 3.2% |
| gst | 20,586 | 10.8% |
| **Total fees** | **190,394** | 100.0% |
| **Slippage** | **305,601** | — |

---

## 3. Power (Context Only — Not a Gate)

Power at n*=42: **0.9972** (hurdle 0.80). SEALED is a sign+spread confirmation, not a standalone power clearance.


---

## 4. SEALED Gate (per §5)

| Condition | Result | Detail |
|---|---|---|
| Positive-sign IC significant (one-sided, alpha=0.05) | PASS | t=4.4928, p=2.817441e-05 |
| Net long/short spread > 0 | PASS | +20.52% annualized |

**SEALED VERDICT: PASS** — Carry is a validated alpha across discovery (TRAIN) + two out-of-sample windows (HOLDOUT, SEALED).

The research phase closes. Work moves to implementation design (sizing via `NseMarginEngine`, execution, risk limits). **No further sleeve hunting.**

