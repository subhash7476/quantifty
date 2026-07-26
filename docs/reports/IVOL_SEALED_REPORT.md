# IVOL Sleeve — SEALED Read Report

**One-shot, script-generated** — `scripts/signal_engine/ivol/run_sealed.py`. Code commit `fc92693`.

**Run timestamp:** 2026-07-26T05:18:49.230924Z

**Protocol:** `IVOL_SEALED_READ_PROTOCOL.md` §1–§5 (frozen, SHA-256 `d54e955b9134c3287715ba255d58db1fb94c06c3e3fb0447b2f706ac8d627201`).

**Pre-registration:** `IVOL_PHASE0_PRE_REGISTRATION.md` (frozen, SHA-256 `82ed96f9c493852c81c7452f54dee20cd452d7656ebb243cfe5fb406cd1c3f4d`).

**Construction:** `IVOL_PHASE0_PRE_REGISTRATION.md` §3–§4 (frozen).

**Window:** SEALED 2023-01-01 → 2026-07-20 (42 formations, 42 with IC).

**Sign:** −1 (long low idiosyncratic vol, short high).


---

## 1. Rank-IC (Negative-Sign, One-Sided)

| Metric | Value |
|---|---|
| Mean IC | +0.018212 |
| SD(IC) | 0.137654 |
| n (formations) | 42 |
| t-stat (simple) | 0.8574 |
| p-value (one-sided, negative direction) | 8.018961e-01 |
| AC1 | 0.0799 |
| NW t | below trigger (\|AC1\| <= 0.1), not computed |
| Sign matches declaration (−1) | **FAIL** |
| Significant at alpha=0.05 | **FAIL** |

---

## 2. Net-of-Fee Long/Short Spread

| Metric | Value |
|---|---|
| Gross annualized | -13.18% |
| Net annualized | -13.78% |
| Fee drag | 60.1 bp |
| Slippage (5 bp/side) | 139,127 Rs |
| Avg turnover | 0.654 |
| Return periods | 41 |
| Net > 0 | **FAIL** |

### Fee Component Breakdown

| Component | Total (Rs) | Share |
|---|---:|--:|
| brokerage | 59,840 | 58.1% |
| stt | 22,431 | 21.8% |
| exchange_txn | 5,843 | 5.7% |
| sebi_fee | 278 | 0.3% |
| stamp_duty | 2,783 | 2.7% |
| gst | 11,873 | 11.5% |
| **Total fees** | **103,048** | 100.0% |
| **Slippage** | **139,127** | — |

---

## 3. Power (Context Only — Not a Gate)

Power at n*=42: **0.2114** (hurdle 0.80). SEALED is a sign+spread confirmation, not a standalone power clearance.


---

## 4. SEALED Gate (per §5)

| Condition | Result | Detail |
|---|---|---|
| Negative-sign IC significant (one-sided, alpha=0.05) | **FAIL** | t=0.8574, p=8.018961e-01 |
| Net long/short spread > 0 | **FAIL** | -13.78% annualized |

**SEALED VERDICT: FAIL** — the effect did not survive the true holdout.

IVOL is dead; the sealed window is spent. An honest terminal result, reported as-is.

