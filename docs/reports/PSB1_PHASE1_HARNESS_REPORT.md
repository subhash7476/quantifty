# PSB-1 Phase 1 — Screening Harness Report (synthetic dev-proof)

**Script-generated** (protocol §10 — no hand-edited numbers). Code commit `11dc210`. Seed `20260713` (§10).

This report proves the harness on **synthetic data only**; no candidate score is computed on the real store. The only real-store touch is the P7 fence-check (dates only): observed `MAX(trade_date)=2022-12-30`.

Synthetic panels: 210 names x 260 weekly grids (5 trading days/week), scenarios null / reversal / delivery, each in its own DuckDB under `data/psb1_synthetic/` (gitignored).

## Falsifiable predictions

| # | Prediction | Evidence | Result |
|---|---|---|---|
| | P1 planted signal (C1 reversal scenario) | mean IC=0.0453 (target ~0.05, tol +/-0.02) | PASS |
| | P2 null (C1 null scenario) | mean IC=0.0015 95%CI[-0.0065,0.0095] covers 0 | PASS |
| | P3 sign wiring (C1>0 reversal; C3>0 delivery) | C1 mean IC=0.0453>0 ; C3 mean IC=0.0712>0 | PASS |
| | P4 F2 delisting machinery (imputed < primary for C1) | primary=0.0453 imputed=-0.0938 | PASS |
| | P5 fees (both legs charged; net < gross) | fees_topq=5756311.0 fees_base=428104.6 net_spread=-0.0313 < gross_spread=0.0977 | PASS |
| | P6 determinism (byte-identical on re-run) | sha256 run1=5c35070d2732cea7 run2=5c35070d2732cea7 | PASS |
| | P7 fence-check real store (dates only, no score) | MAX(trade_date)=2022-12-30 <= 2022-12-31 | PASS |

## Harness output by scenario

Net spread is an **upper bound on realizable economics** (same-close formation, no execution lag — §6/F5).

### Scenario: reversal (C1/C4 signal + planted delistings)

| Cand | n | mean IC | SD | t | p(1s) | AC1 | NW t | imputed IC | net spread | gross spread | Q1-Q5 | turnover | n* | power | power(d/2) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| C1 | 258 | 0.0453 | 0.0791 | 9.20 | 0.0000 | -0.011 | - | -0.0938 | -0.0313 | 0.0977 | 0.2000 | 0.813 | 183 | 1.000 | 0.987 |
| C2 | 207 | 0.0441 | 0.0764 | 8.29 | 0.0000 | 0.072 | - | -0.0925 | -0.0281 | 0.0994 | 0.2046 | 0.808 | 183 | 1.000 | 0.987 |
| C3 | 142 | 0.0048 | 0.0761 | 0.75 | 0.2261 | -0.027 | - | 0.0065 | -0.1066 | 0.0136 | 0.0241 | 0.827 | 183 | 0.214 | 0.112 |
| C4 | 142 | -0.0032 | 0.0758 | -0.51 | 0.6931 | 0.039 | - | -0.0007 | -0.1479 | -0.0356 | -0.0596 | 0.818 | 183 | 0.013 | 0.027 |
| C5 | 48 | -0.0248 | 0.0562 | -3.05 | 0.9981 | 0.002 | - | -0.0208 | -0.0343 | -0.0307 | -0.0544 | 0.141 | 42 | 0.000 | 0.001 |

### Scenario: delivery (C3 signal)

| Cand | n | mean IC | SD | t | p(1s) | AC1 | NW t | imputed IC | net spread | gross spread | Q1-Q5 | turnover | n* | power | power(d/2) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| C1 | 258 | -0.0017 | 0.0730 | -0.37 | 0.6440 | -0.025 | - | -0.0017 | -0.1270 | -0.0014 | 0.0053 | 0.801 | 183 | 0.025 | 0.036 |
| C2 | 207 | -0.0019 | 0.0741 | -0.37 | 0.6433 | -0.003 | - | -0.0019 | -0.1328 | -0.0090 | 0.0076 | 0.800 | 183 | 0.023 | 0.035 |
| C3 | 142 | 0.0712 | 0.0763 | 11.12 | 0.0000 | 0.020 | - | 0.0712 | 0.0448 | 0.1921 | 0.3524 | 0.803 | 183 | 1.000 | 1.000 |
| C4 | 142 | 0.0062 | 0.0690 | 1.07 | 0.1430 | 0.201 | 0.89 | 0.0062 | -0.1226 | 0.0017 | 0.0268 | 0.803 | 183 | 0.332 (NW 0.26) | 0.149 |
| C5 | 48 | -0.0060 | 0.0745 | -0.56 | 0.7108 | 0.039 | - | -0.0060 | -0.0132 | -0.0094 | -0.0105 | 0.123 | 42 | 0.015 | 0.029 |

### Scenario: null

| Cand | n | mean IC | SD | t | p(1s) | AC1 | NW t | imputed IC | net spread | gross spread | Q1-Q5 | turnover | n* | power | power(d/2) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| C1 | 258 | 0.0015 | 0.0658 | 0.37 | 0.3555 | 0.031 | - | 0.0015 | -0.1226 | 0.0048 | 0.0105 | 0.801 | 183 | 0.091 | 0.068 |
| C2 | 207 | 0.0036 | 0.0659 | 0.79 | 0.2145 | 0.010 | - | 0.0036 | -0.1137 | 0.0143 | 0.0183 | 0.804 | 183 | 0.183 | 0.101 |
| C3 | 142 | -0.0063 | 0.0654 | -1.16 | 0.8751 | -0.021 | - | -0.0063 | -0.1379 | -0.0133 | -0.0037 | 0.810 | 183 | 0.002 | 0.011 |
| C4 | 142 | 0.0035 | 0.0760 | 0.54 | 0.2938 | 0.140 | 0.48 | 0.0035 | -0.1383 | -0.0146 | 0.0158 | 0.803 | 183 | 0.151 (NW 0.13) | 0.091 |
| C5 | 48 | 0.0052 | 0.0684 | 0.52 | 0.3014 | -0.261 | 0.66 | 0.0052 | -0.0040 | 0.0001 | 0.0122 | 0.128 | 42 | 0.122 (NW 0.15) | 0.080 |

