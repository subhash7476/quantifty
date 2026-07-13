# PSB-1 Phase 1 — Screening Harness Report (synthetic dev-proof + real R1)

**Script-generated** (protocol §10). Code commit at generation `6fcef84` — when the report is committed together with the code this is the **parent** of the commit that adds this file (Lead Review D3); re-run post-commit to stamp the exact commit. Seed `20260713` (§10).

Candidate scores are proved on **synthetic data only**. The real store is read only for: the P7 fence-check and real n* (dates/counts), and the R1 §11.3 scan (adjusted prices, **not** a candidate score — Prompt 1-B).

**Real-store stamp (D3/S3):** rows **7,030,920**, unfenced `MAX(trade_date)=2026-07-09`, loader fenced observed max `2022-12-30` (≤ 2022-12-31). 3.5y of sealed data is physically present and excluded.

**Real n\* (R2, real `trading_calendar`, dates only):** weekly **183**, monthly **42** in [2023-01-01, 2026-06-30]. (The per-candidate n\* in the tables below is the *synthetic* calendar's count — a synthetic artifact.)

Synthetic panels: 210 names x 260 weekly grids (5 trading days/week), scenarios null / reversal / delivery, each in its own DuckDB under `data/psb1_synthetic/` (gitignored).

## Falsifiable predictions

| Prediction | Evidence | Result |
|---|---|---|
| S1/P6 determinism (two interpreters, PYTHONHASHSEED 0 vs 1, whole-file bytes) | sha256 seed0=07d02dd9907b7924 seed1=07d02dd9907b7924 | PASS |
| P1 planted signal (C1 reversal) | mean IC=0.0453 (target ~0.05, tol +/-0.02) | PASS |
| P2 null (C1 null scenario) | mean IC=0.0015 95%CI[-0.0065,0.0095] covers 0 | PASS |
| P3 sign wiring (C1>0 reversal; C3>0 delivery) | C1=0.0453>0 ; C3=0.0712>0 | PASS |
| P4 F2 delisting machinery (imputed < primary for C1) | primary=0.0453 imputed=-0.0938 | PASS |
| P4b §4.2 sign-flag fires on reversal C1, not on null C1 | reversal C1 flag=True ; null C1 flag=False | PASS |
| P5 fees (both legs charged; net < gross) | fees_topq=5756311.0 fees_base=428104.6 net=-0.0313 < gross=0.0977 | PASS |
| P7 fence-check real store (fenced <= cutoff < unfenced) | fenced=2022-12-30 <= 2022-12-31 < unfenced=2026-07-09; rows=7,030,920 | PASS |

## R1 — §11.3 data-integrity classification (REAL dev window)

Gate-(b)'s five-bucket classifier (`audit_corporate_actions.py:279-296`), reused via `classify_move`, run on the real dev-fenced adjusted panel exactly as `load_panel` builds it (rn=1 dedup, ever-member, ≤ 2022-12-31). The scan reads prices but computes **no candidate score** (Prompt 1-B).

Screened >|20%| moves: **235**. Bucket counts:

| Bucket | Count | Residue? |
|---|--:|:--:|
| CA-explained | 0 | no |
| genuine | 228 | no |
| magnitude-mismatch | 0 | **yes** |
| direction-mismatch | 1 | **yes** |
| CA-shaped-orphan | 6 | **yes** |

**Residue: 7** (1 documented in `ca_scope_exclusions`, 6 undocumented). The full residue register (documented + undocumented) is the **D5 missing-input set** (7 rows); the §11.3 **HALT** set is the 6 undocumented rows only.

| Entity | Move date | Adjusted move | Class | Disposition |
|---|---|--:|---|---|
| ANGELBRKG | 2021-11-11 | -90.1% | CA-shaped-orphan | **UNDOCUMENTED — HALTs (§11.3)** |
| COFORGE | 2020-08-20 | -80.1% | CA-shaped-orphan | **UNDOCUMENTED — HALTs (§11.3)** |
| SHRIRAMFIN | 2022-12-20 | -79.8% | CA-shaped-orphan | **UNDOCUMENTED — HALTs (§11.3)** |
| SINTEX | 2017-05-25 | -75.2% | CA-shaped-orphan | documented (still a missing input, D5.1) |
| VAKRANGEE | 2013-11-27 | -49.4% | CA-shaped-orphan | **UNDOCUMENTED — HALTs (§11.3)** |
| DEWANHOUS | 2012-05-22 | -49.3% | CA-shaped-orphan | **UNDOCUMENTED — HALTs (§11.3)** |
| KWALITY | 2010-06-15 | +45.9% | direction-mismatch | **UNDOCUMENTED — HALTs (§11.3)** |

> **§11.3 status (Prompt 1-B item 6, reported not acted on):** a correct R1 **HALTs** on the 6 undocumented residue rows above. Their disposition is governed by operator decision **D5** (unadjusted CA = missing input); the register is threaded into scoring (D5.2-7) and exercised by `tests/psb1/test_scoring.py`.

**Honest disclosure (Prompt 1-B item 6) — large moves gate-(b) classifies `genuine`, therefore NOT in the register and NOT excluded by D5:**

Gate-(b)'s CA-ratio test is strict (±`CA_RATIO_TOLERANCE`=0.02) and disabled below Rs 5 (the tick-grid floor). Several very large negative adjusted moves fall just outside the canonical-ratio band or have a backward-adjusted `prev_close` < Rs 5, so gate-(b) classes them `genuine`. They remain in the scored panel. This is gate-(b)'s pinned classification (§9); flagged for the operator, **not** silently reclassified.

| Entity | Move date | Adjusted move | Surviving ratio |
|---|---|--:|--:|
| BAJAUTOFIN | 2010-09-29 | -99.0% | 0.0098 |
| AURUM | 2020-12-23 | -98.8% | 0.0124 |
| PAISALO | 2018-01-24 | -95.3% | 0.0472 |
| SUVEN | 2020-01-21 | -94.7% | 0.0529 |
| ABSHEKINDS | 2011-05-03 | -90.4% | 0.0965 |
| GFLLIMITED | 2019-08-06 | -89.1% | 0.1089 |
| INFOSYSTCH | 2011-06-29 | -87.4% | 0.1257 |
| FEL | 2016-05-11 | -87.4% | 0.1258 |
| ADANIENT | 2015-06-03 | -82.8% | 0.1723 |
| PHILIPCARB | 2018-04-19 | -79.0% | 0.2100 |
| ANDHRAPAP | 2020-03-05 | -78.9% | 0.2109 |
| CHOLADBS | 2010-06-22 | -78.4% | 0.2159 |
| CGPOWER | 2016-03-15 | -71.7% | 0.2833 |
| CCAVENUE | 2018-09-28 | -70.8% | 0.2917 |
| MASTEK | 2015-06-12 | -66.0% | 0.3400 |
| ARVIND | 2018-11-28 | -65.1% | 0.3491 |
| 63MOONS | 2013-08-01 | -64.5% | 0.3550 |
| GLOBALTELE | 2011-06-20 | -62.2% | 0.3782 |
| JSL | 2015-11-19 | -60.9% | 0.3913 |
| STAR | 2013-12-19 | -57.6% | 0.4236 |


## §4.2 sign-discrepancy flags (D2)

> **FLAG (§4.2 sign discrepancy) — reversal/C1:** primary mean IC +0.0453 vs imputed -0.0938 — sign differs; surfaced to the operator, not dropped.
> **FLAG (§4.2 sign discrepancy) — reversal/C2:** primary mean IC +0.0441 vs imputed -0.0925 — sign differs; surfaced to the operator, not dropped.


## Harness output by scenario

Net spread is an **upper bound on realizable economics** (same-close formation, no execution lag — §6/F5). Three distinct counters (D5.8): `skip` = <5-scored-name dates (I2); `fwd_miss` = §4.2 missing-forward; `ca_excl` = D5 CA-register forward exclusions. All 0 on the synthetic panels (no CAs planted); the D5 register path is exercised in `tests/psb1/test_scoring.py`.

### Scenario: reversal (C1/C4 signal + planted delistings)

| Cand | n | skip | fwd_miss | ca_excl | mean IC | SD | t | p(1s) | AC1 | NW t | imputed IC | flag | net spread | gross spread | Q1-Q5 | turnover | n* | power | power(d/2) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|--:|--:|--:|--:|--:|--:|--:|
| C1 | 258 | 0 | 2427 | 0 | 0.0453 | 0.0791 | 9.20 | 0.0000 | -0.011 | - | -0.0938 | FLAG | -0.0313 | 0.0977 | 0.2000 | 0.813 | 183 | 1.000 | 0.987 |
| C2 | 207 | 0 | 1937 | 0 | 0.0441 | 0.0764 | 8.29 | 0.0000 | 0.072 | - | -0.0925 | FLAG | -0.0281 | 0.0994 | 0.2046 | 0.808 | 183 | 1.000 | 0.987 |
| C3 | 142 | 0 | 2849 | 0 | 0.0048 | 0.0761 | 0.75 | 0.2261 | -0.027 | - | 0.0065 | - | -0.1066 | 0.0136 | 0.0241 | 0.827 | 183 | 0.214 | 0.112 |
| C4 | 142 | 0 | 1307 | 0 | -0.0032 | 0.0758 | -0.51 | 0.6931 | 0.039 | - | -0.0007 | - | -0.1479 | -0.0356 | -0.0596 | 0.818 | 183 | 0.013 | 0.027 |
| C5 | 48 | 0 | 394 | 0 | -0.0248 | 0.0562 | -3.05 | 0.9981 | 0.002 | - | -0.0208 | - | -0.0343 | -0.0307 | -0.0544 | 0.141 | 42 | 0.000 | 0.001 |


### Scenario: delivery (C3 signal)

| Cand | n | skip | fwd_miss | ca_excl | mean IC | SD | t | p(1s) | AC1 | NW t | imputed IC | flag | net spread | gross spread | Q1-Q5 | turnover | n* | power | power(d/2) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|--:|--:|--:|--:|--:|--:|--:|
| C1 | 258 | 0 | 0 | 0 | -0.0017 | 0.0730 | -0.37 | 0.6440 | -0.025 | - | -0.0017 | - | -0.1270 | -0.0014 | 0.0053 | 0.801 | 183 | 0.025 | 0.036 |
| C2 | 207 | 0 | 0 | 0 | -0.0019 | 0.0741 | -0.37 | 0.6433 | -0.003 | - | -0.0019 | - | -0.1328 | -0.0090 | 0.0076 | 0.800 | 183 | 0.023 | 0.035 |
| C3 | 142 | 0 | 0 | 0 | 0.0712 | 0.0763 | 11.12 | 0.0000 | 0.020 | - | 0.0712 | - | 0.0448 | 0.1921 | 0.3524 | 0.803 | 183 | 1.000 | 1.000 |
| C4 | 142 | 0 | 0 | 0 | 0.0062 | 0.0690 | 1.07 | 0.1430 | 0.201 | 0.89 | 0.0062 | - | -0.1226 | 0.0017 | 0.0268 | 0.803 | 183 | 0.332 (NW 0.26) | 0.149 |
| C5 | 48 | 0 | 0 | 0 | -0.0060 | 0.0745 | -0.56 | 0.7108 | 0.039 | - | -0.0060 | - | -0.0132 | -0.0094 | -0.0105 | 0.123 | 42 | 0.015 | 0.029 |


### Scenario: null

| Cand | n | skip | fwd_miss | ca_excl | mean IC | SD | t | p(1s) | AC1 | NW t | imputed IC | flag | net spread | gross spread | Q1-Q5 | turnover | n* | power | power(d/2) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|--:|--:|--:|--:|--:|--:|--:|
| C1 | 258 | 0 | 0 | 0 | 0.0015 | 0.0658 | 0.37 | 0.3555 | 0.031 | - | 0.0015 | - | -0.1226 | 0.0048 | 0.0105 | 0.801 | 183 | 0.091 | 0.068 |
| C2 | 207 | 0 | 0 | 0 | 0.0036 | 0.0659 | 0.79 | 0.2145 | 0.010 | - | 0.0036 | - | -0.1137 | 0.0143 | 0.0183 | 0.804 | 183 | 0.183 | 0.101 |
| C3 | 142 | 0 | 0 | 0 | -0.0063 | 0.0654 | -1.16 | 0.8751 | -0.021 | - | -0.0063 | - | -0.1379 | -0.0133 | -0.0037 | 0.810 | 183 | 0.002 | 0.011 |
| C4 | 142 | 0 | 0 | 0 | 0.0035 | 0.0760 | 0.54 | 0.2938 | 0.140 | 0.48 | 0.0035 | - | -0.1383 | -0.0146 | 0.0158 | 0.803 | 183 | 0.151 (NW 0.13) | 0.091 |
| C5 | 48 | 0 | 0 | 0 | 0.0052 | 0.0684 | 0.52 | 0.3014 | -0.261 | 0.66 | 0.0052 | - | -0.0040 | 0.0001 | 0.0122 | 0.128 | 42 | 0.122 (NW 0.15) | 0.080 |

