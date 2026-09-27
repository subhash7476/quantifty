# W2 — NiftyShield Afternoon Variance and Trend Term (generated)

Pre-analysis note: `NIFTY_SHIELD_AFTERNOON_VARIANCE_PREREG_2026-09-27.md`. Script: `scripts/research/nifty_shield_diag/afternoon_variance.py`.

- Sessions used: 899 (860 pre-CAS, 39 post-CAS), 2023-01-02 → 2026-09-25
- Dropped: {'no index bars': 22, 'special session': 5}
- Moving-block bootstrap over sessions: block 20, 10,000 reps, seed 20260927; 95% percentile intervals; every statistic is a ratio of sums

## pre-CAS

| statistic | estimate [95% CI] | reference |
|---|--:|--:|
| **H**: hold-window share of close-to-close variance (5-min) | 0.181 [0.151, 0.223] | bracket assumes 0.40 |
| H at 1-min (robustness) | 0.184 [0.157, 0.222] | 0.40 |
| hold share of 09:15→window-end variance (5-min) | 0.301 [0.275, 0.328] | uniform 0.40 |
| overnight share of close-to-close variance | 0.444 [0.327, 0.577] | bracket assumes 0 |
| **VR**: (S_end/S_13)² ÷ Σ D² (5-min) | 1.046 [0.917, 1.204] | 1 = no autocorrelation |
| VR at 1-min (robustness) | 1.028 [0.890, 1.196] | 1 |
| mean trend term T, bp² per session (5-min) | +54.53 [-102.59, +233.59] | 0 |

f = √(H/0.40) = **0.673** (bracket σ ÷ what the window actually carries, if f < 1 the bracket is too wide).

## post-CAS

| statistic | estimate [95% CI] | reference |
|---|--:|--:|
| **H**: hold-window share of close-to-close variance (5-min) | 0.167 [0.158, 0.303] | bracket assumes 0.40 |
| H at 1-min (robustness) | 0.167 [0.167, 0.359] | 0.40 |
| hold share of 09:15→window-end variance (5-min) | 0.313 [0.272, 0.322] | uniform 0.38 |
| overnight share of close-to-close variance | 0.430 [0.384, 0.641] | bracket assumes 0 |
| **VR**: (S_end/S_13)² ÷ Σ D² (5-min) | 0.864 [0.740, 1.334] | 1 = no autocorrelation |
| VR at 1-min (robustness) | 0.863 [0.624, 1.302] | 1 |
| mean trend term T, bp² per session (5-min) | -71.06 [-101.18, +156.39] | 0 |

f = √(H/0.40) = **0.645** (bracket σ ÷ what the window actually carries, if f < 1 the bracket is too wide).

## VR by 13:00 DayType label (pre-CAS)

| label | 2024+ (out of sample): n, VR [95% CI] | 2023 (in-sample model): n, VR |
|---|--:|--:|
| BullTrend | 213, 0.964 [0.736, 1.202] | 77, 0.927 |
| BearTrend | 168, 0.842 [0.619, 1.085] | 55, 0.918 |
| Choppy | 235, 1.242 [0.952, 1.561] | 92, 1.623 |

Sessions with no 13pm fact: 20 (excluded from this table only).

## Pinned conclusions (pre-analysis note §5, pre-CAS)

- **Q1:** √t bracket misstates the hold move by factor f = 0.673. A corrected-σ bracket is a v2 candidate for the promotion pipeline; E008 is unchanged.
- **Q2 (pooled):** No detectable afternoon autocorrelation (VR CI contains 1).
- **Q2 (by label):** No detectable path difference by label; the gate's value, if any, must come from elsewhere.

Post-CAS is descriptive only (few sessions). Nothing here changes an E008 rule.
