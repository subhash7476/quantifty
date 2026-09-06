# Carry Sleeve — Net-of-Fee Long/Short Spread

**Script-generated** — `scripts/signal_engine/carry/run_net_spread.py`. Code commit `da3e3ba`.

**Generated:** 2026-07-23

**Protocol:** `CARRY_SEALED_READ_PROTOCOL.md` §1 — precondition gate for SEALED read.

**Sign:** positive (long high residual carry, short low). Frozen per `CARRY_V2_PRE_REGISTRATION.md` §1.

**Construction:** frozen per `CARRY_PHASE0_PRE_REGISTRATION.md` §3–§8 (annualized basis, dividend-adjusted, cross-sectionally demeaned, winsorized +/-3σ, z-scored, beta+sector neutralized, monthly, roll T-3).


---


## 1. Fee Model

| Component | Rate / Rule |
|---|---|
| Futures STT | Tiered (canonical `futures_fees.py`): 0.0100% ≤ 2023-03-31 · 0.0125% 2023-04-01 → 2024-09-30 · 0.0200% ≥ 2024-10-01, SELL side only. TRAIN/HOLDOUT both pre-2023-04 → effective 0.0100%. |
| Exchange transaction charge | 0.0021% pre-2024-10 / 0.0019% post-2024-10, both legs (NSE retail tier) |
| SEBI turnover fee | 0.0001% both legs (Rs 10/crore) |
| Stamp duty | 0.010% BUY side (pre-2020-07-01); 0.002% BUY side (post-2020-07-01) |
| GST / service tax | Era-accurate (18% post-2017-07-01; service tax rates pre-2017) on (brokerage + exchange_txn + sebi_fee) |
| Brokerage | Rs 20 flat per order (discount broker futures) |
| Slippage | 5 bp per side (modeling choice, fixed) |
| Gross exposure | Rs 1.0 Cr (fixed) |
| ADV cap | Position <= 10% of trailing 20-day ADV |
| No-trade band | 0.25σ of cross-sectional target weights |

## 2. Quintile (equal-weight) Portfolio


| Window | Net > 0? | Gross ann | Net ann | Fee drag | Slippage | Avg turnover | Formations |
|---|:--:|--:|--:|--:|--:|--:|--:|
| **TRAIN** | **PASS** | +14.37% | +12.84% | 153.5 bp | 7163 Rs/mo | 1.440 | 58 |
| **HOLDOUT** | **PASS** | +8.42% | +6.96% | 146.4 bp | 7319 Rs/mo | 1.484 | 24 |

### Fee Component Breakdown (TRAIN)

| Component | Total (Rs) | Share |
|---|---:|--:|
| brokerage | 119,240 | 49.5% |
| stt | 41,547 | 17.3% |
| exchange_txn | 17,450 | 7.2% |
| sebi_fee | 831 | 0.3% |
| stamp_duty | 38,079 | 15.8% |
| gst | 23,610 | 9.8% |
| **Total fees** | **240,757** | 100.0% |
| **Slippage** | **415,469** | — |

## 2. z-Weighted Portfolio


| Window | Net > 0? | Gross ann | Net ann | Fee drag | Slippage | Avg turnover | Formations |
|---|:--:|--:|--:|--:|--:|--:|--:|
| **TRAIN** | **PASS** | +26.53% | +24.80% | 173.2 bp | 7361 Rs/mo | 1.480 | 58 |
| **HOLDOUT** | **PASS** | +14.67% | +13.07% | 160.2 bp | 7657 Rs/mo | 1.556 | 24 |

---

## 3. Gate — Net-of-Fee Precondition

Both windows must show NET > 0 (annualized) on the quintile portfolio.

| Window | Gross ann | Net ann | Net > 0? |
|---|--:|--:|:--:|
| TRAIN | +14.37% | +12.84% | PASS |
| HOLDOUT | +8.42% | +6.96% | PASS |

**GATE VERDICT: PASS** — Net spread > 0 on both TRAIN and HOLDOUT.

Precondition met. SEALED read (2023-01-01 → 2026-07-20) may proceed under `CARRY_SEALED_READ_PROTOCOL.md`.

