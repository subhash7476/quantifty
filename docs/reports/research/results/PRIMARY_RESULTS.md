# VWAP-XREV-1 — primary results (auto-generated from results/*.csv)


## TRAIN — primary cells (gross bp, reversion direction)

| side | H | n_events | n_names | n_sessions | session_mean_bp | nw_t | p_one_nw | p_holm_all10 | ci_lo | ci_hi | mean_bp_event | median_bp_event | frac_pos | mde_bp_80 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| up_disp_short | 5 | 1827 | 140 | 265 | 1.006 | 0.773 | 0.220 | 1.000 | -1.508 | 3.601 | -0.364 | 1.299 | 0.514 | 3.543 |
| up_disp_short | 10 | 1827 | 140 | 265 | 0.428 | 0.224 | 0.412 | 1.000 | -3.242 | 4.326 | -3.307 | 1.029 | 0.508 | 4.839 |
| up_disp_short | 15 | 1827 | 140 | 265 | -0.750 | -0.343 | 0.634 | 1.000 | -4.950 | 3.539 | -4.846 | 0.485 | 0.502 | 5.434 |
| up_disp_short | 30 | 1826 | 140 | 265 | -1.282 | -0.399 | 0.655 | 1.000 | -7.515 | 5.014 | -6.984 | 1.485 | 0.505 | 7.367 |
| up_disp_short | 60 | 1826 | 140 | 265 | -2.171 | -0.571 | 0.716 | 1.000 | -9.623 | 5.111 | -8.143 | 0.000 | 0.498 | 9.240 |
| down_disp_long | 5 | 1841 | 140 | 242 | 4.151 | 2.199 | 0.014 | 0.086 | 0.337 | 7.818 | 1.283 | 2.964 | 0.532 | 4.773 |
| down_disp_long | 10 | 1841 | 140 | 242 | 7.521 | 3.400 | 0.000 | 0.003 | 3.157 | 11.918 | -0.944 | 3.593 | 0.531 | 6.007 |
| down_disp_long | 15 | 1841 | 140 | 242 | 8.258 | 2.936 | 0.002 | 0.013 | 2.858 | 13.903 | -1.771 | 3.683 | 0.525 | 7.473 |
| down_disp_long | 30 | 1841 | 140 | 242 | 12.542 | 3.660 | 0.000 | 0.001 | 6.093 | 19.543 | -1.746 | 5.438 | 0.532 | 9.531 |
| down_disp_long | 60 | 1841 | 140 | 242 | 19.832 | 4.595 | 0.000 | 0.000 | 11.495 | 28.575 | -5.510 | 3.359 | 0.521 | 12.350 |

### TRAIN — market-excess R_ex (same inference)

| side | H | session_mean_bp | nw_t | p_one_nw | mean_bp_event | median_bp_event |
|---|---|---|---|---|---|---|
| up_disp_short | 5 | 0.417 | 0.324 | 0.373 | -0.756 | 1.876 |
| up_disp_short | 10 | -1.077 | -0.594 | 0.723 | -3.474 | 1.223 |
| up_disp_short | 15 | -2.504 | -1.212 | 0.887 | -5.047 | 1.530 |
| up_disp_short | 30 | -3.726 | -1.205 | 0.885 | -6.823 | 2.229 |
| up_disp_short | 60 | -5.660 | -1.540 | 0.938 | -7.120 | 3.329 |
| down_disp_long | 5 | 3.353 | 1.861 | 0.032 | 3.947 | 4.754 |
| down_disp_long | 10 | 6.230 | 3.016 | 0.001 | 4.696 | 6.328 |
| down_disp_long | 15 | 6.148 | 2.424 | 0.008 | 5.096 | 6.220 |
| down_disp_long | 30 | 8.632 | 2.711 | 0.004 | 5.801 | 6.525 |
| down_disp_long | 60 | 13.516 | 3.509 | 0.000 | 5.120 | 6.556 |

### TRAIN — net session-mean bp by slippage scenario (kappa bp/side; statutory fees ~4.5 bp RT)

| side | H | net@k0.0 | net@k2.75 | net@k5.0 |
|---|---|---|---|---|
| down_disp_long | 5 | -0.431 | -5.931 | -10.431 |
| down_disp_long | 10 | 2.940 | -2.560 | -7.060 |
| down_disp_long | 15 | 3.676 | -1.824 | -6.324 |
| down_disp_long | 30 | 7.960 | 2.460 | -2.040 |
| down_disp_long | 60 | 15.250 | 9.750 | 5.250 |
| up_disp_short | 5 | -3.576 | -9.076 | -13.576 |
| up_disp_short | 10 | -4.154 | -9.654 | -14.154 |
| up_disp_short | 15 | -5.332 | -10.832 | -15.332 |
| up_disp_short | 30 | -5.864 | -11.364 | -15.864 |
| up_disp_short | 60 | -6.752 | -12.252 | -16.752 |

## VAL — primary cells (gross bp, reversion direction)

| side | H | n_events | n_names | n_sessions | session_mean_bp | nw_t | p_one_nw | p_holm_all10 | ci_lo | ci_hi | mean_bp_event | median_bp_event | frac_pos | mde_bp_80 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| up_disp_short | 5 | 1031 | 174 | 161 | 4.626 | 2.821 | 0.003 | 0.027 | 1.474 | 8.012 | 1.549 | 2.713 | 0.537 | 4.770 |
| up_disp_short | 10 | 1031 | 174 | 161 | 5.655 | 1.920 | 0.028 | 0.113 | -0.172 | 11.480 | 0.314 | 2.674 | 0.522 | 7.281 |
| up_disp_short | 15 | 1031 | 174 | 161 | 5.568 | 1.527 | 0.064 | 0.193 | -1.760 | 12.620 | 0.583 | 4.104 | 0.540 | 8.132 |
| up_disp_short | 30 | 1030 | 174 | 161 | 3.600 | 0.796 | 0.214 | 0.214 | -5.253 | 12.379 | -3.309 | 4.520 | 0.533 | 11.183 |
| up_disp_short | 60 | 1031 | 174 | 161 | 8.382 | 1.355 | 0.089 | 0.193 | -3.806 | 20.482 | -4.995 | 4.036 | 0.509 | 16.575 |
| down_disp_long | 5 | 1419 | 177 | 150 | 8.859 | 2.349 | 0.010 | 0.069 | 1.920 | 16.778 | 10.108 | 3.362 | 0.546 | 9.817 |
| down_disp_long | 10 | 1419 | 177 | 150 | 11.110 | 2.560 | 0.006 | 0.046 | 2.898 | 20.080 | 11.428 | 3.394 | 0.533 | 11.111 |
| down_disp_long | 15 | 1419 | 177 | 150 | 11.457 | 2.236 | 0.013 | 0.069 | 1.677 | 21.974 | 13.038 | 3.886 | 0.531 | 13.546 |
| down_disp_long | 30 | 1419 | 177 | 150 | 18.663 | 2.619 | 0.005 | 0.044 | 4.786 | 32.941 | 17.381 | 6.651 | 0.548 | 16.451 |
| down_disp_long | 60 | 1418 | 177 | 150 | 18.037 | 2.355 | 0.010 | 0.069 | 2.803 | 32.932 | 15.909 | 7.421 | 0.536 | 18.003 |

### VAL — market-excess R_ex (same inference)

| side | H | session_mean_bp | nw_t | p_one_nw | mean_bp_event | median_bp_event |
|---|---|---|---|---|---|---|
| up_disp_short | 5 | 3.961 | 2.503 | 0.007 | 1.760 | 2.816 |
| up_disp_short | 10 | 4.175 | 1.479 | 0.071 | 0.485 | 3.092 |
| up_disp_short | 15 | 3.305 | 0.981 | 0.164 | 0.773 | 6.457 |
| up_disp_short | 30 | -0.089 | -0.021 | 0.509 | -2.354 | 5.662 |
| up_disp_short | 60 | 1.901 | 0.326 | 0.372 | -3.564 | 3.920 |
| down_disp_long | 5 | 6.431 | 1.756 | 0.041 | 4.657 | 3.154 |
| down_disp_long | 10 | 7.744 | 1.824 | 0.035 | 5.448 | 2.945 |
| down_disp_long | 15 | 6.698 | 1.322 | 0.094 | 5.451 | 3.192 |
| down_disp_long | 30 | 10.697 | 1.629 | 0.053 | 7.352 | 4.336 |
| down_disp_long | 60 | 8.691 | 1.241 | 0.108 | 5.931 | 2.891 |

### VAL — net session-mean bp by slippage scenario (kappa bp/side; statutory fees ~4.5 bp RT)

| side | H | net@k0.0 | net@k2.75 | net@k5.0 |
|---|---|---|---|---|
| down_disp_long | 5 | 4.354 | -1.146 | -5.646 |
| down_disp_long | 10 | 6.605 | 1.105 | -3.395 |
| down_disp_long | 15 | 6.952 | 1.452 | -3.048 |
| down_disp_long | 30 | 14.158 | 8.658 | 4.158 |
| down_disp_long | 60 | 13.532 | 8.032 | 3.532 |
| up_disp_short | 5 | 0.119 | -5.381 | -9.881 |
| up_disp_short | 10 | 1.148 | -4.352 | -8.852 |
| up_disp_short | 15 | 1.060 | -4.440 | -8.940 |
| up_disp_short | 30 | -0.907 | -6.407 | -10.907 |
| up_disp_short | 60 | 3.874 | -1.626 | -6.126 |

## HOLDOUT — primary cells (gross bp, reversion direction)

| side | H | n_events | n_names | n_sessions | session_mean_bp | nw_t | p_one_nw | p_holm_all10 | ci_lo | ci_hi | mean_bp_event | median_bp_event | frac_pos | mde_bp_80 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| up_disp_short | 5 | 3332 | 219 | 362 | -2.019 | -1.555 | 0.940 | 1.000 | -4.610 | 0.433 | -1.837 | 1.060 | 0.509 | 3.095 |
| up_disp_short | 10 | 3332 | 219 | 362 | -1.151 | -0.842 | 0.800 | 1.000 | -3.920 | 1.508 | -1.082 | 1.477 | 0.514 | 3.409 |
| up_disp_short | 15 | 3332 | 219 | 362 | -0.537 | -0.335 | 0.631 | 1.000 | -3.808 | 2.521 | -0.458 | 2.736 | 0.527 | 4.277 |
| up_disp_short | 30 | 3332 | 219 | 362 | 1.896 | 0.872 | 0.192 | 1.000 | -2.461 | 6.079 | 0.376 | 4.354 | 0.535 | 5.722 |
| up_disp_short | 60 | 3330 | 219 | 362 | 7.694 | 2.731 | 0.003 | 0.033 | 2.166 | 13.222 | 2.956 | 7.301 | 0.545 | 7.174 |
| down_disp_long | 5 | 3120 | 215 | 342 | 0.722 | 0.354 | 0.362 | 1.000 | -3.125 | 4.979 | -0.529 | 1.265 | 0.512 | 4.422 |
| down_disp_long | 10 | 3120 | 215 | 342 | 1.742 | 0.715 | 0.238 | 1.000 | -2.703 | 6.933 | -0.326 | 1.218 | 0.512 | 5.650 |
| down_disp_long | 15 | 3120 | 215 | 342 | 2.566 | 0.896 | 0.186 | 1.000 | -2.972 | 8.437 | 0.401 | 2.081 | 0.519 | 6.527 |
| down_disp_long | 30 | 3120 | 215 | 342 | 4.088 | 1.089 | 0.138 | 1.000 | -3.383 | 11.483 | 1.475 | 1.952 | 0.513 | 8.511 |
| down_disp_long | 60 | 3120 | 215 | 342 | 7.644 | 2.029 | 0.022 | 0.195 | 0.500 | 15.265 | 0.257 | 2.010 | 0.511 | 8.377 |

### HOLDOUT — market-excess R_ex (same inference)

| side | H | session_mean_bp | nw_t | p_one_nw | mean_bp_event | median_bp_event |
|---|---|---|---|---|---|---|
| up_disp_short | 5 | -2.434 | -2.005 | 0.977 | -1.647 | 1.295 |
| up_disp_short | 10 | -1.948 | -1.502 | 0.933 | -0.685 | 2.112 |
| up_disp_short | 15 | -2.038 | -1.331 | 0.908 | -0.344 | 3.140 |
| up_disp_short | 30 | -0.543 | -0.255 | 0.601 | 0.829 | 5.014 |
| up_disp_short | 60 | 2.830 | 1.052 | 0.147 | 3.519 | 8.497 |
| down_disp_long | 5 | 0.225 | 0.113 | 0.455 | -0.152 | 1.533 |
| down_disp_long | 10 | 0.356 | 0.153 | 0.439 | -0.177 | 1.997 |
| down_disp_long | 15 | 0.557 | 0.203 | 0.420 | 0.315 | 2.148 |
| down_disp_long | 30 | 0.821 | 0.224 | 0.411 | 1.232 | 1.697 |
| down_disp_long | 60 | 1.534 | 0.415 | 0.339 | -0.377 | 2.184 |

### HOLDOUT — net session-mean bp by slippage scenario (kappa bp/side; statutory fees ~4.5 bp RT)

| side | H | net@k0.0 | net@k2.75 | net@k5.0 |
|---|---|---|---|---|
| down_disp_long | 5 | -3.746 | -9.246 | -13.746 |
| down_disp_long | 10 | -2.726 | -8.226 | -12.726 |
| down_disp_long | 15 | -1.903 | -7.403 | -11.903 |
| down_disp_long | 30 | -0.380 | -5.880 | -10.380 |
| down_disp_long | 60 | 3.176 | -2.324 | -6.824 |
| up_disp_short | 5 | -6.488 | -11.988 | -16.488 |
| up_disp_short | 10 | -5.619 | -11.119 | -15.619 |
| up_disp_short | 15 | -5.005 | -10.505 | -15.005 |
| up_disp_short | 30 | -2.573 | -8.073 | -12.573 |
| up_disp_short | 60 | 3.225 | -2.275 | -6.775 |

## Frozen classification

```json
{
 "label": "C6",
 "defects": [],
 "val_confirmed": [
  [
   "up_disp_short",
   5
  ],
  [
   "down_disp_long",
   10
  ],
  [
   "down_disp_long",
   30
  ]
 ],
 "holdout_confirmed_clean": [],
 "microstructure_contaminated": [],
 "economic_pass_cells": [],
 "holdout_positive_among_val_confirmed": [
  [
   "down_disp_long",
   10
  ],
  [
   "down_disp_long",
   30
  ]
 ],
 "net_lower_bounds_bp": {},
 "certified_only_share": 0.0
}
```