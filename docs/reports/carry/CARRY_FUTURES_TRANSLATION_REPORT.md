# Carry — Futures Translation (TRAIN + HOLDOUT)

**Script-generated** — `scripts/signal_engine/carry/futures_translation.py`, commit `5ac8160`, run 2026-09-24. Descriptive measurement of the FROZEN book; no parameter, signal or window changed. Price reads fenced at 2022-12-31; max futures date read: **2022-12-30**.

Portfolio logic imported from `run_net_spread.py` (targets, ADV cap, 0.25σ band, fee model). Futures return = frozen spot `fwd_ret_1m` × same-contract basis-ratio chain on the T-3-roll near-month contract (futures close). Roll cost = both legs of every T-3 roll at the fee model + 5 bp/side slippage — a cost the frozen net spread does not charge.

## 0. Reproduction of the frozen spot numbers

| Book | Δ gross vs frozen | Δ net vs frozen |
|---|--:|--:|
| TRAIN_quintile | +0.0000 bp | +0.0000 bp |
| TRAIN_zweighted | +0.0000 bp | +0.0000 bp |
| HOLDOUT_quintile | +0.0000 bp | +0.0000 bp |
| HOLDOUT_zweighted | +0.0000 bp | +0.0000 bp |

## 1a. Annualised spread — quintile

| Window | Gross spot (t) | Gross futures (t) | Gross fut (settle) | Net spot (frozen) | Net futures | t net fut | % months net fut > 0 |
|---|--:|--:|--:|--:|--:|--:|--:|
| TRAIN | +14.37% (+3.88) | -3.09% (-0.83) | -3.13% | +12.84% | **-6.16%** | -1.77 | 42% |
| HOLDOUT | +8.42% (+1.41) | -4.82% (-0.79) | -4.77% | +6.96% | **-7.80%** | -1.34 | 30% |

Mean monthly Q5−Q1 decomposition (bp/month): futures = spot + convergence; convergence = ordinary-dividend component + residual basis/roll component.

| Window | Spot | Convergence (t) | of which dividend | of which residual basis + roll | Futures | Rebalance cost | Roll cost | Net futures |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| TRAIN | +115.0 | -138.8 (-16.66) | -2.2 | -136.6 | -23.8 | -11.4 | -15.3 | -50.5 |
| HOLDOUT | +70.3 | -108.8 (-10.58) | -7.8 | -101.0 | -38.5 | -11.4 | -15.0 | -64.8 |

| Window | Long spot | Long futures | Short spot | Short futures | Held raw ann. basis, long / short | Turnover | Coverage (missing fut / held) | Jump-flagged periods |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| TRAIN | +138.0 | +78.3 | +23.0 | +102.1 | +7.35% / -8.83% | 1.440 | 1 / 3746 | 1 |
| HOLDOUT | +159.3 | +108.2 | +89.0 | +146.6 | +6.92% / -5.41% | 1.484 | 0 / 1588 | 0 |

## 1b. Annualised spread — zweighted

| Window | Gross spot (t) | Gross futures (t) | Gross fut (settle) | Net spot (frozen) | Net futures | t net fut | % months net fut > 0 |
|---|--:|--:|--:|--:|--:|--:|--:|
| TRAIN | +26.53% (+5.16) | -2.74% (-0.56) | -2.81% | +24.80% | **-5.86%** | -1.32 | 44% |
| HOLDOUT | +14.67% (+2.30) | -5.27% (-0.82) | -5.23% | +13.07% | **-8.28%** | -1.35 | 39% |

Mean monthly Q5−Q1 decomposition (bp/month): futures = spot + convergence; convergence = ordinary-dividend component + residual basis/roll component.

| Window | Spot | Convergence (t) | of which dividend | of which residual basis + roll | Futures | Rebalance cost | Roll cost | Net futures |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| TRAIN | +202.2 | -221.8 (-14.31) | -4.3 | -217.5 | -19.6 | -11.7 | -15.3 | -46.7 |
| HOLDOUT | +117.6 | -159.7 (-10.25) | -15.1 | -144.6 | -42.1 | -11.8 | -14.9 | -68.9 |

| Window | Long spot | Long futures | Short spot | Short futures | Held raw ann. basis, long / short | Turnover | Coverage (missing fut / held) | Jump-flagged periods |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| TRAIN | +152.8 | +91.9 | -49.4 | +111.5 | +7.35% / -8.83% | 1.480 | 1 / 3746 | 1 |
| HOLDOUT | +166.2 | +114.5 | +48.6 | +156.6 | +6.92% / -5.41% | 1.556 | 0 / 1588 | 0 |

## 2. Rank IC of frozen `z_carry_neut` (all eligible names, per formation)

| Window | vs spot return | vs futures return | vs convergence alone | n |
|---|--:|--:|--:|--:|
| TRAIN | +0.0421 (t +3.96) | -0.0106 (t -1.02) | -0.5575 (t -43.04) | 58 |
| HOLDOUT | +0.0419 (t +2.32) | -0.0070 (t -0.40) | -0.5829 (t -30.19) | 23 |

