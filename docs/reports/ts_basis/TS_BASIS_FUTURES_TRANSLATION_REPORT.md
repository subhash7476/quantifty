# TS Basis — Futures Translation (TRAIN + HOLDOUT)

**Script-generated** — `scripts/signal_engine/ts_basis/futures_translation.py`, commit `a2bed7c`, run 2026-09-24. Frozen construction, frozen portfolio logic; price reads fenced at 2022-12-31; max futures date read **2022-12-30**. Kill rule (pre-written): futures IC ≤ 0 OR gross futures spread ≤ 0 → closed as a futures strategy.

## 0. Reproduction of the frozen spot snapshot (`TS_BASIS_NET_SPREAD_SNAPSHOT.json`, Spearman)

| Window | Δ gross spot | Δ net spot | IC here vs frozen |
|---|--:|--:|--:|
| TRAIN | +0.00 bp | +0.00 bp | +0.0593 vs +0.0593 |
| HOLDOUT | +0.00 bp | +0.00 bp | +0.0428 vs +0.0412 |

## 1. Annualised Q5−Q1 (equal-weight quintile, frozen book)

| Window | Gross spot (t) | Spot incl. dividends | Gross futures (t) | Gross fut (settle) | Net spot (frozen) | Net futures (t) | Months gross fut > 0 |
|---|--:|--:|--:|--:|--:|--:|--:|
| TRAIN | +20.05% (+3.51) | +19.91% | **+3.78%** (+0.80) | +3.77% | +18.38% | **+0.48%** (+0.19) | 54% |
| HOLDOUT | +16.26% (+2.29) | +15.20% | **+3.07%** (+0.50) | +3.10% | +14.80% | **+0.03%** (+0.07) | 52% |

## 2. Monthly decomposition (bp/month)

| Window | Spot | Convergence (t) | of which dividends | of which basis + roll | Futures | Rebalance cost | Roll cost | Net futures |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| TRAIN | +158.0 | -122.6 (-16.22) | -1.0 | -121.6 | +35.3 | -11.9 | -15.1 | +8.4 |
| HOLDOUT | +129.8 | -101.0 (-9.63) | -7.7 | -93.3 | +28.8 | -10.6 | -14.3 | +3.9 |

| Window | Long spot | Long fut | Long div | Short spot | Short fut | Short div | Turnover | Missing fut / held | Jump-flagged |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| TRAIN | +133.3 | +72.4 | +0.0 | -24.7 | +37.1 | +1.0 | 1.532 | 0 / 2746 | 0 |
| HOLDOUT | +198.4 | +148.0 | +0.0 | +68.6 | +119.2 | +7.7 | 1.457 | 0 / 1266 | 0 |

## 3. Rank IC of frozen z_ts (all scored names, per formation)

| Window | vs spot | vs futures | vs convergence | vs spot + dividends | vs spot skipping day 1 (diagnostic) |
|---|--:|--:|--:|--:|--:|
| TRAIN | +0.0593 (t +3.91) | +0.0101 (t +0.64) | -0.5393 (t -33.06) | +0.0590 (t +3.88) | +0.0410 (t +2.84) |
| HOLDOUT | +0.0428 (t +1.95) | -0.0058 (t -0.26) | -0.5736 (t -25.20) | +0.0397 (t +1.82) | +0.0273 (t +1.24) |

## 4. Kill rule

| Window | Futures IC | Gross futures | Kill fires? |
|---|--:|--:|:--:|
| TRAIN | +0.0101 | +3.78% | no |
| HOLDOUT | -0.0058 | +3.07% | **YES** |

Survivorship: 18 liquid (formation, name) cells in 2016-03 → 2022 have no forward return and are excluded by the frozen builder's `fwd_ret_1m IS NOT NULL` membership filter.

