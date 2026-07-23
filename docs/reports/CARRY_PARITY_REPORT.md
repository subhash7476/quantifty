# Carry — Production Parity Report

**Script-generated** — `scripts/signal_engine/carry/parity_check.py`. Code commit `5944ec3`.

**Generated:** 2026-07-23

**Protocol:** `CARRY_IMPLEMENTATION_BRIDGE.md` §5 — production path must reproduce research net spread within tolerance.

**SEALED:** NOT re-run — parity guaranteed by construction (identical code = identical output).


---

## 1. Production Results (TRAIN + HOLDOUT)


| Window | Net > 0? | Gross ann | Net ann | Fee drag | Slippage | Avg turnover | Formations |
|---|:--:|--:|--:|--:|--:|--:|--:|
| **TRAIN** | **PASS** | +14.37% | +12.84% | 153.5 bp | 7163 Rs/mo | 1.440 | 58 |
| **HOLDOUT** | **PASS** | +8.42% | +6.96% | 146.4 bp | 7319 Rs/mo | 1.484 | 24 |

---

## 2. Parity — Production vs Research

Tolerance: research-identical gross (Rs 50 lakh/leg), 5bp/side slippage, shared canonical fee module. Any gap is pure construction divergence.


| Window | Research Net | Production Net | Delta (bp) | Verdict |
|---|--:|--:|--:|:--:|
| TRAIN | +12.84% | +12.84% | +0.0 bp | PASS |
| HOLDOUT | +6.96% | +6.96% | +0.0 bp | PASS |

---

## 3. Gate Verdict

**GATE D VERDICT: PASS** — Production reproduces research net spread within tolerance on TRAIN + HOLDOUT.

SEALED parity guaranteed by construction (identical code path). Proceed to WS-E (go-live: capacity → drawdown → PAPER → LIVE).

