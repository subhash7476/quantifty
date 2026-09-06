# NiftyShield DayType Parity Report

**Generated:** script (`scripts/daytype/parity_check_13pm.py`)

- Model: `logistic_13pm_prod` (checkpoint `13pm`)
- `feature_names`: 38 features
- Orphan features absent from `feature_names`: yes
- `block_a_excluded`: True
- `train_thru`: 2023
- Train/Val/Hold accuracy: [('Train', 2907, 0.6615), ('Val', 246, 0.7073), ('Hold', 248, 0.7056)]

## 1. Engine-to-CSV feature parity (13pm)

- Sessions sampled across 2024-2025: **30** (>= 20 required)
- Sessions with full match (all features within 1e-6): **30**
- Sessions skipped (no session data): 0

**VERDICT: PASS** — every feature in `feature_names` matched within 1e-6 on every sampled session.

### Sampled sessions

| date | status | n_features | max_diff | n_mismatch |
|---|---|---|---|---|
| 2024-01-01 | ok | 38 | 8.109832250191573e-17 | 0 |
| 2024-01-24 | ok | 38 | 7.105427357601002e-15 | 0 |
| 2024-02-19 | ok | 38 | 9.8879238130678e-17 | 0 |
| 2024-03-14 | ok | 38 | 1.1102230246251565e-16 | 0 |
| 2024-04-10 | ok | 38 | 9.974659986866641e-17 | 0 |
| 2024-05-08 | ok | 38 | 9.020562075079397e-17 | 0 |
| 2024-06-03 | ok | 38 | 1.1102230246251565e-16 | 0 |
| 2024-06-27 | ok | 38 | 9.280770596475918e-17 | 0 |
| 2024-07-23 | ok | 38 | 1.1102230246251565e-16 | 0 |
| 2024-08-16 | ok | 38 | 9.627715291671279e-17 | 0 |
| 2024-09-10 | ok | 38 | 7.105427357601002e-15 | 0 |
| 2024-10-04 | ok | 38 | 8.586881206085195e-17 | 0 |
| 2024-10-29 | ok | 38 | 7.105427357601002e-15 | 0 |
| 2024-11-26 | ok | 38 | 9.367506770274758e-17 | 0 |
| 2024-12-19 | ok | 38 | 1.1102230246251565e-16 | 0 |
| 2025-01-14 | ok | 38 | 9.367506770274758e-17 | 0 |
| 2025-02-05 | ok | 38 | 9.64939933512099e-17 | 0 |
| 2025-03-03 | ok | 38 | 9.280770596475918e-17 | 0 |
| 2025-03-27 | ok | 38 | 1.1102230246251565e-16 | 0 |
| 2025-04-25 | ok | 38 | 1.1102230246251565e-16 | 0 |
| 2025-05-21 | ok | 38 | 1.1102230246251565e-16 | 0 |
| 2025-06-13 | ok | 38 | 9.80118763926896e-17 | 0 |
| 2025-07-08 | ok | 38 | 4.440892098500626e-16 | 0 |
| 2025-07-31 | ok | 38 | 9.71445146547012e-17 | 0 |
| 2025-08-26 | ok | 38 | 3.552713678800501e-15 | 0 |
| 2025-09-19 | ok | 38 | 1.1102230246251565e-16 | 0 |
| 2025-10-15 | ok | 38 | 9.454242944073599e-17 | 0 |
| 2025-11-12 | ok | 38 | 8.500145032286355e-17 | 0 |
| 2025-12-05 | ok | 38 | 9.324138683375338e-17 | 0 |
| 2025-12-31 | ok | 38 | 3.552713678800501e-15 | 0 |

### Worst per-feature absolute difference (across samples)

| feature | max abs diff |
|---|---|
| partial_twap_dist_std | 7.11e-15 |
| bn_nf_range_ratio | 4.44e-16 |
| open_30m_range_ratio_partial | 1.11e-16 |
| partial_clv | 1.11e-16 |
| range_pct_before_11am_partial | 1.11e-16 |
| partial_log_vol_expansion | 1.11e-16 |
| partial_pct_above_twap | 1.11e-16 |
| partial_dominant_direction_strength | 1.11e-16 |
| partial_close_dist_twap | 9.97e-17 |
| open_15m_ret | 9.89e-17 |
| partial_range_pct | 9.89e-17 |
| open_30m_ret | 9.87e-17 |
| open_30m_range | 9.80e-17 |
| partial_return | 9.71e-17 |
| open_5m_ret | 9.65e-17 |
| bn_nf_open_30m_spread | 9.63e-17 |
| bn_nf_open_5m_spread | 9.54e-17 |
| open_30m_twap_dist | 9.50e-17 |
| bn_nf_partial_return_spread | 9.37e-17 |
| partial_atr_5m | 9.22e-17 |
| partial_realized_vol | 8.98e-17 |
| partial_linreg_r2 | 8.33e-17 |
| partial_ll_count_15m | 8.33e-17 |
| partial_trend_score | 8.33e-17 |
| partial_twap_lean | 8.33e-17 |
| partial_hh_count_15m | 5.55e-17 |
| partial_center_of_mass | 5.55e-17 |
| partial_avg_adverse_excursion | 5.55e-17 |
| partial_hh_minus_ll | 5.55e-17 |
| bn_nf_correlation_5m | 5.55e-17 |
| partial_linreg_slope | 6.78e-21 |
| open_30m_high_break_min | 0.00e+00 |
| open_30m_low_break_min | 0.00e+00 |
| partial_twap_cross_count | 0.00e+00 |
| partial_longest_above_twap | 0.00e+00 |
| partial_longest_below_twap | 0.00e+00 |
| partial_flip_count_15m | 0.00e+00 |
| bn_leads_nifty | 0.00e+00 |

## 2. Deployed 2025 holdout accuracy (engine, harness-style)

The engine is run over every 2025 session exactly as the sealed harness runs it: full session bars fed, the locked/last acted-on regime scored against the 2025 `cluster_id` labels.

- Sessions scored: **248**
- Overall accuracy: **69.8%** (173/248)

| class | n | accuracy |
|---|---|---|
| Choppy | 117 | 57.3% |
| BullTrend | 78 | 85.9% |
| BearTrend | 53 | 73.6% |

### Per-session detail

| date | true | pred | regime | conf | locked | ok |
|---|---|---|---|---|---|---|
| 2025-01-01 00:00:00 | 1 | 1 | BullTrend | 0.744 | False | YES |
| 2025-01-02 00:00:00 | 1 | 1 | BullTrend | 0.986 | False | YES |
| 2025-01-03 00:00:00 | 0 | 2 | BearTrend | 0.515 | False | no |
| 2025-01-06 00:00:00 | 2 | 2 | BearTrend | 0.892 | False | YES |
| 2025-01-07 00:00:00 | 0 | 1 | BullTrend | 0.730 | True | no |
| 2025-01-08 00:00:00 | 0 | 2 | BearTrend | 0.796 | False | no |
| 2025-01-09 00:00:00 | 0 | 2 | BearTrend | 0.669 | False | no |
| 2025-01-10 00:00:00 | 0 | 0 | Choppy | 0.474 | False | YES |
| 2025-01-13 00:00:00 | 2 | 1 | BullTrend | 0.720 | True | no |
| 2025-01-14 00:00:00 | 0 | 1 | BullTrend | 0.757 | True | no |
| 2025-01-15 00:00:00 | 0 | 0 | Choppy | 0.647 | False | YES |
| 2025-01-16 00:00:00 | 0 | 0 | Choppy | 0.525 | False | YES |
| 2025-01-17 00:00:00 | 0 | 1 | BullTrend | 0.508 | False | no |
| 2025-01-20 00:00:00 | 1 | 1 | BullTrend | 0.872 | False | YES |
| 2025-01-21 00:00:00 | 2 | 2 | BearTrend | 0.733 | True | YES |
| 2025-01-22 00:00:00 | 0 | 2 | BearTrend | 0.722 | False | no |
| 2025-01-23 00:00:00 | 0 | 1 | BullTrend | 0.823 | False | no |
| 2025-01-24 00:00:00 | 2 | 2 | BearTrend | 0.479 | False | YES |
| 2025-01-27 00:00:00 | 2 | 0 | Choppy | 0.517 | False | no |
| 2025-01-28 00:00:00 | 1 | 1 | BullTrend | 0.879 | False | YES |
| 2025-01-29 00:00:00 | 1 | 1 | BullTrend | 0.771 | False | YES |
| 2025-01-30 00:00:00 | 0 | 1 | BullTrend | 0.461 | False | no |
| 2025-01-31 00:00:00 | 1 | 1 | BullTrend | 0.734 | True | YES |
| 2025-02-01 00:00:00 | 0 | 2 | BearTrend | 0.826 | False | no |
| 2025-02-03 00:00:00 | 1 | 1 | BullTrend | 0.704 | True | YES |
| 2025-02-04 00:00:00 | 1 | 1 | BullTrend | 0.847 | False | YES |
| 2025-02-05 00:00:00 | 0 | 0 | Choppy | 0.770 | True | YES |
| 2025-02-06 00:00:00 | 2 | 2 | BearTrend | 0.801 | False | YES |
| 2025-02-07 00:00:00 | 0 | 0 | Choppy | 0.528 | False | YES |
| 2025-02-10 00:00:00 | 0 | 2 | BearTrend | 0.727 | False | no |
| 2025-02-11 00:00:00 | 2 | 2 | BearTrend | 0.926 | False | YES |
| 2025-02-12 00:00:00 | 1 | 1 | BullTrend | 0.709 | False | YES |
| 2025-02-13 00:00:00 | 0 | 1 | BullTrend | 0.712 | False | no |
| 2025-02-14 00:00:00 | 2 | 2 | BearTrend | 0.968 | False | YES |
| 2025-02-17 00:00:00 | 1 | 1 | BullTrend | 0.712 | True | YES |
| 2025-02-18 00:00:00 | 0 | 0 | Choppy | 0.709 | True | YES |
| 2025-02-19 00:00:00 | 0 | 0 | Choppy | 0.455 | False | YES |
| 2025-02-20 00:00:00 | 0 | 1 | BullTrend | 0.517 | False | no |
| 2025-02-21 00:00:00 | 0 | 0 | Choppy | 0.717 | True | YES |
| 2025-02-24 00:00:00 | 0 | 0 | Choppy | 0.582 | False | YES |
| 2025-02-25 00:00:00 | 0 | 1 | BullTrend | 0.745 | True | no |
| 2025-02-27 00:00:00 | 0 | 0 | Choppy | 0.509 | False | YES |
| 2025-02-28 00:00:00 | 2 | 2 | BearTrend | 0.972 | False | YES |
| 2025-03-03 00:00:00 | 0 | 0 | Choppy | 0.389 | False | YES |
| 2025-03-04 00:00:00 | 0 | 1 | BullTrend | 0.706 | True | no |
| 2025-03-05 00:00:00 | 1 | 1 | BullTrend | 0.744 | True | YES |
| 2025-03-06 00:00:00 | 1 | 1 | BullTrend | 0.753 | False | YES |
| 2025-03-07 00:00:00 | 0 | 0 | Choppy | 0.515 | False | YES |
| 2025-03-10 00:00:00 | 2 | 1 | BullTrend | 0.749 | True | no |
| 2025-03-11 00:00:00 | 1 | 1 | BullTrend | 0.823 | True | YES |
| 2025-03-12 00:00:00 | 0 | 0 | Choppy | 0.723 | True | YES |
| 2025-03-13 00:00:00 | 2 | 0 | Choppy | 0.561 | False | no |
| 2025-03-17 00:00:00 | 0 | 1 | BullTrend | 0.776 | True | no |
| 2025-03-18 00:00:00 | 1 | 1 | BullTrend | 0.823 | True | YES |
| 2025-03-19 00:00:00 | 1 | 1 | BullTrend | 0.761 | False | YES |
| 2025-03-20 00:00:00 | 1 | 1 | BullTrend | 0.863 | False | YES |
| 2025-03-21 00:00:00 | 1 | 1 | BullTrend | 0.969 | False | YES |
| 2025-03-24 00:00:00 | 1 | 1 | BullTrend | 0.705 | True | YES |
| 2025-03-25 00:00:00 | 2 | 2 | BearTrend | 0.514 | False | YES |
| 2025-03-26 00:00:00 | 2 | 0 | Choppy | 0.487 | False | no |
| 2025-03-27 00:00:00 | 1 | 1 | BullTrend | 0.866 | True | YES |
| 2025-03-28 00:00:00 | 0 | 0 | Choppy | 0.505 | False | YES |
| 2025-04-01 00:00:00 | 2 | 2 | BearTrend | 0.866 | False | YES |
| 2025-04-02 00:00:00 | 1 | 1 | BullTrend | 0.776 | True | YES |
| 2025-04-03 00:00:00 | 0 | 0 | Choppy | 0.604 | False | YES |
| 2025-04-04 00:00:00 | 2 | 2 | BearTrend | 0.685 | False | YES |
| 2025-04-07 00:00:00 | 1 | 1 | BullTrend | 0.810 | True | YES |
| 2025-04-08 00:00:00 | 1 | 1 | BullTrend | 0.928 | False | YES |
| 2025-04-09 00:00:00 | 0 | 0 | Choppy | 0.874 | False | YES |
| 2025-04-11 00:00:00 | 0 | 1 | BullTrend | 0.775 | False | no |
| 2025-04-15 00:00:00 | 0 | 1 | BullTrend | 0.541 | False | no |
| 2025-04-16 00:00:00 | 1 | 0 | Choppy | 0.491 | False | no |
| 2025-04-17 00:00:00 | 1 | 1 | BullTrend | 0.989 | False | YES |
| 2025-04-21 00:00:00 | 1 | 1 | BullTrend | 0.980 | False | YES |
| 2025-04-22 00:00:00 | 0 | 0 | Choppy | 0.650 | False | YES |
| 2025-04-23 00:00:00 | 1 | 0 | Choppy | 0.527 | False | no |
| 2025-04-24 00:00:00 | 0 | 0 | Choppy | 0.705 | True | YES |
| 2025-04-25 00:00:00 | 2 | 2 | BearTrend | 0.696 | False | YES |
| 2025-04-28 00:00:00 | 1 | 1 | BullTrend | 0.864 | True | YES |
| 2025-04-29 00:00:00 | 0 | 0 | Choppy | 0.589 | False | YES |
| 2025-04-30 00:00:00 | 0 | 0 | Choppy | 0.648 | False | YES |
| 2025-05-02 00:00:00 | 2 | 1 | BullTrend | 0.818 | True | no |
| 2025-05-05 00:00:00 | 0 | 1 | BullTrend | 0.810 | True | no |
| 2025-05-06 00:00:00 | 0 | 0 | Choppy | 0.705 | True | YES |
| 2025-05-07 00:00:00 | 0 | 0 | Choppy | 0.603 | False | YES |
| 2025-05-08 00:00:00 | 2 | 0 | Choppy | 0.713 | True | no |
| 2025-05-09 00:00:00 | 0 | 0 | Choppy | 0.634 | False | YES |
| 2025-05-12 00:00:00 | 1 | 1 | BullTrend | 0.937 | True | YES |
| 2025-05-13 00:00:00 | 2 | 2 | BearTrend | 0.746 | True | YES |
| 2025-05-14 00:00:00 | 0 | 1 | BullTrend | 0.734 | True | no |
| 2025-05-15 00:00:00 | 1 | 1 | BullTrend | 0.781 | True | YES |
| 2025-05-16 00:00:00 | 0 | 0 | Choppy | 0.714 | True | YES |
| 2025-05-19 00:00:00 | 0 | 0 | Choppy | 0.702 | True | YES |
| 2025-05-20 00:00:00 | 2 | 2 | BearTrend | 0.879 | False | YES |
| 2025-05-21 00:00:00 | 0 | 1 | BullTrend | 0.733 | True | no |
| 2025-05-22 00:00:00 | 0 | 2 | BearTrend | 0.572 | False | no |
| 2025-05-23 00:00:00 | 1 | 1 | BullTrend | 0.792 | True | YES |
| 2025-05-26 00:00:00 | 0 | 1 | BullTrend | 0.731 | True | no |
| 2025-05-27 00:00:00 | 0 | 2 | BearTrend | 0.708 | False | no |
| 2025-05-28 00:00:00 | 0 | 0 | Choppy | 0.635 | False | YES |
| 2025-05-29 00:00:00 | 0 | 2 | BearTrend | 0.570 | False | no |
| 2025-05-30 00:00:00 | 0 | 0 | Choppy | 0.613 | False | YES |
| 2025-06-02 00:00:00 | 1 | 1 | BullTrend | 0.761 | False | YES |
| 2025-06-03 00:00:00 | 2 | 2 | BearTrend | 0.866 | False | YES |
| 2025-06-04 00:00:00 | 1 | 1 | BullTrend | 0.607 | False | YES |
| 2025-06-05 00:00:00 | 0 | 1 | BullTrend | 0.688 | False | no |
| 2025-06-06 00:00:00 | 1 | 1 | BullTrend | 0.808 | True | YES |
| 2025-06-09 00:00:00 | 0 | 0 | Choppy | 0.777 | False | YES |
| 2025-06-10 00:00:00 | 0 | 0 | Choppy | 0.692 | False | YES |
| 2025-06-11 00:00:00 | 0 | 1 | BullTrend | 0.752 | True | no |
| 2025-06-12 00:00:00 | 2 | 2 | BearTrend | 0.698 | False | YES |
| 2025-06-13 00:00:00 | 1 | 1 | BullTrend | 0.820 | True | YES |
| 2025-06-16 00:00:00 | 1 | 1 | BullTrend | 0.884 | False | YES |
| 2025-06-17 00:00:00 | 0 | 0 | Choppy | 0.810 | True | YES |
| 2025-06-18 00:00:00 | 0 | 1 | BullTrend | 0.728 | True | no |
| 2025-06-19 00:00:00 | 0 | 1 | BullTrend | 0.821 | True | no |
| 2025-06-20 00:00:00 | 1 | 1 | BullTrend | 0.805 | True | YES |
| 2025-06-23 00:00:00 | 1 | 1 | BullTrend | 0.617 | False | YES |
| 2025-06-24 00:00:00 | 2 | 0 | Choppy | 0.410 | False | no |
| 2025-06-25 00:00:00 | 1 | 1 | BullTrend | 0.816 | True | YES |
| 2025-06-26 00:00:00 | 1 | 0 | Choppy | 0.503 | False | no |
| 2025-06-27 00:00:00 | 1 | 0 | Choppy | 0.770 | True | no |
| 2025-06-30 00:00:00 | 0 | 2 | BearTrend | 0.526 | False | no |
| 2025-07-01 00:00:00 | 0 | 1 | BullTrend | 0.742 | True | no |
| 2025-07-02 00:00:00 | 2 | 2 | BearTrend | 0.684 | False | YES |
| 2025-07-03 00:00:00 | 2 | 0 | Choppy | 0.660 | False | no |
| 2025-07-04 00:00:00 | 0 | 0 | Choppy | 0.535 | False | YES |
| 2025-07-07 00:00:00 | 0 | 0 | Choppy | 0.681 | False | YES |
| 2025-07-08 00:00:00 | 0 | 0 | Choppy | 0.622 | False | YES |
| 2025-07-09 00:00:00 | 0 | 1 | BullTrend | 0.631 | False | no |
| 2025-07-10 00:00:00 | 2 | 2 | BearTrend | 0.761 | True | YES |
| 2025-07-11 00:00:00 | 2 | 2 | BearTrend | 0.696 | False | YES |
| 2025-07-14 00:00:00 | 0 | 0 | Choppy | 0.553 | False | YES |
| 2025-07-15 00:00:00 | 1 | 1 | BullTrend | 0.672 | False | YES |
| 2025-07-16 00:00:00 | 0 | 0 | Choppy | 0.725 | True | YES |
| 2025-07-17 00:00:00 | 0 | 0 | Choppy | 0.625 | False | YES |
| 2025-07-18 00:00:00 | 2 | 2 | BearTrend | 0.870 | True | YES |
| 2025-07-21 00:00:00 | 1 | 1 | BullTrend | 0.526 | False | YES |
| 2025-07-22 00:00:00 | 0 | 0 | Choppy | 0.441 | False | YES |
| 2025-07-23 00:00:00 | 1 | 1 | BullTrend | 0.711 | False | YES |
| 2025-07-24 00:00:00 | 2 | 2 | BearTrend | 0.711 | True | YES |
| 2025-07-25 00:00:00 | 2 | 2 | BearTrend | 0.811 | True | YES |
| 2025-07-28 00:00:00 | 2 | 2 | BearTrend | 0.561 | False | YES |
| 2025-07-29 00:00:00 | 1 | 0 | Choppy | 0.463 | False | no |
| 2025-07-30 00:00:00 | 0 | 0 | Choppy | 0.629 | False | YES |
| 2025-07-31 00:00:00 | 1 | 1 | BullTrend | 0.974 | False | YES |
| 2025-08-01 00:00:00 | 2 | 2 | BearTrend | 0.621 | False | YES |
| 2025-08-04 00:00:00 | 1 | 1 | BullTrend | 0.787 | False | YES |
| 2025-08-05 00:00:00 | 0 | 0 | Choppy | 0.515 | False | YES |
| 2025-08-06 00:00:00 | 0 | 0 | Choppy | 0.507 | False | YES |
| 2025-08-07 00:00:00 | 1 | 2 | BearTrend | 0.828 | True | no |
| 2025-08-08 00:00:00 | 2 | 2 | BearTrend | 0.459 | False | YES |
| 2025-08-11 00:00:00 | 1 | 1 | BullTrend | 0.747 | True | YES |
| 2025-08-12 00:00:00 | 2 | 0 | Choppy | 0.591 | False | no |
| 2025-08-13 00:00:00 | 1 | 1 | BullTrend | 0.707 | True | YES |
| 2025-08-14 00:00:00 | 0 | 0 | Choppy | 0.740 | True | YES |
| 2025-08-18 00:00:00 | 0 | 1 | BullTrend | 0.733 | True | no |
| 2025-08-19 00:00:00 | 1 | 1 | BullTrend | 0.853 | False | YES |
| 2025-08-20 00:00:00 | 1 | 1 | BullTrend | 0.957 | False | YES |
| 2025-08-21 00:00:00 | 0 | 0 | Choppy | 0.564 | False | YES |
| 2025-08-22 00:00:00 | 2 | 2 | BearTrend | 0.617 | False | YES |
| 2025-08-25 00:00:00 | 1 | 1 | BullTrend | 0.786 | False | YES |
| 2025-08-26 00:00:00 | 0 | 0 | Choppy | 0.648 | False | YES |
| 2025-08-28 00:00:00 | 0 | 0 | Choppy | 0.691 | False | YES |
| 2025-08-29 00:00:00 | 0 | 0 | Choppy | 0.622 | False | YES |
| 2025-09-01 00:00:00 | 1 | 1 | BullTrend | 0.708 | True | YES |
| 2025-09-02 00:00:00 | 2 | 2 | BearTrend | 0.772 | True | YES |
| 2025-09-03 00:00:00 | 1 | 0 | Choppy | 0.533 | False | no |
| 2025-09-04 00:00:00 | 2 | 2 | BearTrend | 0.478 | False | YES |
| 2025-09-05 00:00:00 | 0 | 2 | BearTrend | 0.824 | False | no |
| 2025-09-08 00:00:00 | 0 | 1 | BullTrend | 0.557 | False | no |
| 2025-09-09 00:00:00 | 0 | 2 | BearTrend | 0.731 | True | no |
| 2025-09-10 00:00:00 | 0 | 0 | Choppy | 0.678 | False | YES |
| 2025-09-11 00:00:00 | 0 | 0 | Choppy | 0.552 | False | YES |
| 2025-09-12 00:00:00 | 1 | 1 | BullTrend | 0.671 | False | YES |
| 2025-09-15 00:00:00 | 0 | 0 | Choppy | 0.683 | False | YES |
| 2025-09-16 00:00:00 | 1 | 1 | BullTrend | 0.916 | False | YES |
| 2025-09-17 00:00:00 | 0 | 0 | Choppy | 0.590 | False | YES |
| 2025-09-18 00:00:00 | 0 | 0 | Choppy | 0.553 | False | YES |
| 2025-09-19 00:00:00 | 0 | 2 | BearTrend | 0.595 | False | no |
| 2025-09-22 00:00:00 | 2 | 0 | Choppy | 0.461 | False | no |
| 2025-09-23 00:00:00 | 0 | 2 | BearTrend | 0.853 | True | no |
| 2025-09-24 00:00:00 | 0 | 0 | Choppy | 0.502 | False | YES |
| 2025-09-25 00:00:00 | 2 | 2 | BearTrend | 0.558 | False | YES |
| 2025-09-26 00:00:00 | 2 | 0 | Choppy | 0.476 | False | no |
| 2025-09-29 00:00:00 | 0 | 2 | BearTrend | 0.612 | False | no |
| 2025-09-30 00:00:00 | 0 | 0 | Choppy | 0.527 | False | YES |
| 2025-10-01 00:00:00 | 1 | 1 | BullTrend | 0.769 | False | YES |
| 2025-10-03 00:00:00 | 1 | 0 | Choppy | 0.536 | False | no |
| 2025-10-06 00:00:00 | 1 | 1 | BullTrend | 0.945 | False | YES |
| 2025-10-07 00:00:00 | 0 | 1 | BullTrend | 0.465 | False | no |
| 2025-10-08 00:00:00 | 2 | 2 | BearTrend | 0.892 | True | YES |
| 2025-10-09 00:00:00 | 1 | 1 | BullTrend | 0.647 | False | YES |
| 2025-10-10 00:00:00 | 0 | 1 | BullTrend | 0.795 | False | no |
| 2025-10-13 00:00:00 | 0 | 0 | Choppy | 0.754 | False | YES |
| 2025-10-14 00:00:00 | 2 | 2 | BearTrend | 0.832 | True | YES |
| 2025-10-15 00:00:00 | 1 | 1 | BullTrend | 0.873 | True | YES |
| 2025-10-16 00:00:00 | 1 | 1 | BullTrend | 0.866 | False | YES |
| 2025-10-17 00:00:00 | 1 | 1 | BullTrend | 0.763 | False | YES |
| 2025-10-20 00:00:00 | 0 | 0 | Choppy | 0.624 | False | YES |
| 2025-10-23 00:00:00 | 2 | 1 | BullTrend | 0.936 | True | no |
| 2025-10-24 00:00:00 | 2 | 2 | BearTrend | 0.517 | False | YES |
| 2025-10-27 00:00:00 | 1 | 1 | BullTrend | 0.803 | True | YES |
| 2025-10-28 00:00:00 | 0 | 2 | BearTrend | 0.856 | True | no |
| 2025-10-29 00:00:00 | 1 | 1 | BullTrend | 0.843 | False | YES |
| 2025-10-30 00:00:00 | 2 | 2 | BearTrend | 0.511 | False | YES |
| 2025-10-31 00:00:00 | 2 | 2 | BearTrend | 0.496 | False | YES |
| 2025-11-03 00:00:00 | 0 | 1 | BullTrend | 0.839 | True | no |
| 2025-11-04 00:00:00 | 2 | 2 | BearTrend | 0.652 | False | YES |
| 2025-11-06 00:00:00 | 0 | 0 | Choppy | 0.467 | False | YES |
| 2025-11-07 00:00:00 | 1 | 1 | BullTrend | 0.889 | False | YES |
| 2025-11-10 00:00:00 | 0 | 0 | Choppy | 0.731 | True | YES |
| 2025-11-11 00:00:00 | 1 | 0 | Choppy | 0.491 | False | no |
| 2025-11-12 00:00:00 | 1 | 1 | BullTrend | 0.917 | False | YES |
| 2025-11-13 00:00:00 | 0 | 1 | BullTrend | 0.876 | False | no |
| 2025-11-14 00:00:00 | 0 | 0 | Choppy | 0.731 | False | YES |
| 2025-11-17 00:00:00 | 1 | 1 | BullTrend | 0.500 | False | YES |
| 2025-11-18 00:00:00 | 0 | 0 | Choppy | 0.484 | False | YES |
| 2025-11-19 00:00:00 | 1 | 1 | BullTrend | 0.913 | False | YES |
| 2025-11-20 00:00:00 | 1 | 0 | Choppy | 0.724 | True | no |
| 2025-11-21 00:00:00 | 0 | 1 | BullTrend | 0.483 | False | no |
| 2025-11-24 00:00:00 | 2 | 0 | Choppy | 0.703 | False | no |
| 2025-11-25 00:00:00 | 0 | 0 | Choppy | 0.613 | False | YES |
| 2025-11-26 00:00:00 | 1 | 1 | BullTrend | 0.803 | True | YES |
| 2025-11-27 00:00:00 | 0 | 0 | Choppy | 0.661 | False | YES |
| 2025-11-28 00:00:00 | 0 | 0 | Choppy | 0.709 | False | YES |
| 2025-12-01 00:00:00 | 2 | 2 | BearTrend | 0.714 | True | YES |
| 2025-12-02 00:00:00 | 0 | 2 | BearTrend | 0.648 | False | no |
| 2025-12-03 00:00:00 | 0 | 0 | Choppy | 0.536 | False | YES |
| 2025-12-04 00:00:00 | 0 | 0 | Choppy | 0.540 | False | YES |
| 2025-12-05 00:00:00 | 1 | 1 | BullTrend | 0.872 | False | YES |
| 2025-12-08 00:00:00 | 2 | 2 | BearTrend | 0.895 | True | YES |
| 2025-12-09 00:00:00 | 0 | 2 | BearTrend | 0.771 | True | no |
| 2025-12-10 00:00:00 | 2 | 2 | BearTrend | 0.714 | False | YES |
| 2025-12-11 00:00:00 | 1 | 1 | BullTrend | 0.853 | False | YES |
| 2025-12-12 00:00:00 | 1 | 0 | Choppy | 0.704 | True | no |
| 2025-12-15 00:00:00 | 1 | 1 | BullTrend | 0.775 | False | YES |
| 2025-12-16 00:00:00 | 0 | 2 | BearTrend | 0.723 | True | no |
| 2025-12-17 00:00:00 | 0 | 2 | BearTrend | 0.751 | False | no |
| 2025-12-18 00:00:00 | 0 | 1 | BullTrend | 0.710 | True | no |
| 2025-12-19 00:00:00 | 0 | 0 | Choppy | 0.575 | False | YES |
| 2025-12-22 00:00:00 | 1 | 1 | BullTrend | 0.555 | False | YES |
| 2025-12-23 00:00:00 | 0 | 0 | Choppy | 0.457 | False | YES |
| 2025-12-24 00:00:00 | 0 | 0 | Choppy | 0.680 | False | YES |
| 2025-12-26 00:00:00 | 2 | 2 | BearTrend | 0.785 | False | YES |
| 2025-12-29 00:00:00 | 2 | 2 | BearTrend | 0.826 | False | YES |
| 2025-12-30 00:00:00 | 0 | 0 | Choppy | 0.618 | False | YES |
| 2025-12-31 00:00:00 | 1 | 1 | BullTrend | 0.968 | False | YES |

## 3. Opportunistic 10am/11am parity (non-gating)

Task 2's EOD-loader fix unblocked the 10am/11am engines. The 13pm gate above is the acceptance criterion; 10am/11am are recorded here opportunistically and do **not** gate NiftyShield (it consumes the 13pm regime). Residual feature differences below reflect the engine and CSV builder defining `partial_vol_pct20` / `partial_range_pct20` differently (all-history percentile in `_inject_block_a` vs trailing-20-day `_rolling_pct_rank` in `build_intraday_features.py`).

| cp | date | n_feat | mismatched features |
|---|---|---|---|
| 10am | 2025-03-05 | 48 | partial_vol_pct20, partial_range_pct20 |
| 10am | 2025-06-13 | 48 | partial_vol_pct20, partial_range_pct20 |
| 10am | 2024-08-16 | 48 | partial_vol_pct20, partial_range_pct20 |
| 11am | 2025-03-05 | 48 | partial_vol_pct20, partial_range_pct20 |
| 11am | 2025-06-13 | 48 | partial_vol_pct20, partial_range_pct20 |
| 11am | 2024-08-16 | 48 | partial_vol_pct20, partial_range_pct20 |
