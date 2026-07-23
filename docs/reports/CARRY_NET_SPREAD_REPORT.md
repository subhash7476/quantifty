# Carry Sleeve — Net-of-Fee Long/Short Spread

**Script-generated** — `scripts/signal_engine/carry/run_net_spread.py`. Code commit `0ea419e`.

**Generated:** 2026-07-23

**Protocol:** `CARRY_SEALED_READ_PROTOCOL.md` §1 — precondition gate for SEALED read.

**Sign:** positive (long high residual carry, short low). Frozen per `CARRY_V2_PRE_REGISTRATION.md` §1.

**Construction:** frozen per `CARRY_PHASE0_PRE_REGISTRATION.md` §3–§8 (annualized basis, dividend-adjusted, cross-sectionally demeaned, winsorized +/-3σ, z-scored, beta+sector neutralized, monthly, roll T-3).


---


## 1. Fee Model

| Component | Rate / Rule |
|---|---|
| Futures STT | 0.0100% SELL side only (pre-2023-04, both TRAIN and HOLDOUT) |
| Exchange transaction charge | 0.0021% both legs (NSE retail tier) |
| SEBI turnover fee | 0.0001% both legs (Rs 10/crore) |
| Stamp duty | 0.010% BUY side (pre-2020-07); 0.002% BUY side (post-2020-07-01) |
| GST | 18% on (brokerage + exchange_txn + sebi_fee) |
| Brokerage | Rs 20 flat per order (discount broker futures) |
| Slippage | 5 bp per side (modeling choice, fixed) |
| Gross exposure | Rs 1.0 Cr (fixed) |
| ADV cap | Position <= 10% of trailing 20-day ADV |
| No-trade band | 0.25σ of cross-sectional target weights |

## 2. Quintile (equal-weight) Portfolio


| Window | Net > 0? | Gross ann | Net ann | Fee drag | Slippage | Avg turnover | Formations |
|---|:--:|--:|--:|--:|--:|--:|--:|
| **TRAIN** | **PASS** | +14.58% | +13.04% | 153.9 bp | 7158 Rs/mo | 1.439 | 58 |
| **HOLDOUT** | **PASS** | +8.42% | +6.96% | 146.4 bp | 7319 Rs/mo | 1.484 | 24 |

### Fee Component Breakdown (TRAIN)

| Component | Total (Rs) | Share |
|---|---:|--:|
| brokerage | 119,180 | 49.3% |
| stt | 41,514 | 17.2% |
| exchange_txn | 17,436 | 7.2% |
| sebi_fee | 830 | 0.3% |
| stamp_duty | 38,046 | 15.7% |
| gst | 24,740 | 10.2% |
| **Total fees** | **241,747** | 100.0% |
| **Slippage** | **415,140** | — |

## 2. z-Weighted Portfolio


| Window | Net > 0? | Gross ann | Net ann | Fee drag | Slippage | Avg turnover | Formations |
|---|:--:|--:|--:|--:|--:|--:|--:|
| **TRAIN** | **PASS** | +26.46% | +24.73% | 173.5 bp | 7358 Rs/mo | 1.479 | 58 |
| **HOLDOUT** | **PASS** | +14.67% | +13.07% | 160.2 bp | 7657 Rs/mo | 1.556 | 24 |

---

## 3. Gate — Net-of-Fee Precondition

Both windows must show NET > 0 (annualized) on the quintile portfolio.

| Window | Gross ann | Net ann | Net > 0? |
|---|--:|--:|:--:|
| TRAIN | +14.58% | +13.04% | PASS |
| HOLDOUT | +8.42% | +6.96% | PASS |

**GATE VERDICT: PASS** — Net spread > 0 on both TRAIN and HOLDOUT.

Precondition met. SEALED read (2023-01-01 → 2026-07-20) may proceed under `CARRY_SEALED_READ_PROTOCOL.md`.

