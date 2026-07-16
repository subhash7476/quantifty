# PSB-2 Phase 1 — Harness Dev-Proof Report
**Script-generated** — `scripts/psb2/run_devproof.py`. Commit `b39aefe`.
Seed `20260716`. Generated 2026-07-16.

## §11.1 Phase 0 Gate

```
﻿Official membership : unobtainable as point-in-time history - mechanical turnover_top200
ISIN issuer overlaps  : 1 issuer(s) skipped
ISIN issuer merges    : 6 merged
Fragmentation overrides: 4 entity(ies) split at an unbridged capital event (INDOSOLAR, NEUEON, CLCIND, DELPHIFX)
| Arm A intra-symbol CA-shape | PASS | 78 residue (78 dispositioned, 0 undocumented) |
| Arm B cross-symbol handoff | HALT | 4 splice fabrications |
| Arm C prev_close identity | PASS | 0 violations |
| Arm D factor evidence | PASS | 1116 tested, 16 flagged (16 dispositioned, 0 undocumented) |
Structural: row count | PASS | 7,030,920 |
CERTIFICATION INCOMPLETE - HALT items above must be resolved.
```

Arms A, C, D: **0 undocumented violations**. Arm B: 4 known splice fabrications (same as PSB-1, resolved by fragmentation test).

## F — Dev Fence

Store: 7,030,920 rows. Fenced MAX: 2022-12-30. Unfenced MAX: 2026-07-09.

Fence: **PASS**.

## B — Grid Identity

- C2/C3 dev fortnightly: 56 (expected 56) — **PASS**
- C4 dev monthly: 132 (expected 132) — **PASS**
- Common sub-window monthly: 28 (expected 28) — **PASS**
- Dev fortnightly first: 2020-09-15 (expected 2020-09-15) — **PASS**
- Dev fortnightly last: 2022-12-30 (expected 2022-12-30) — **PASS**

## C — Pipeline Signal Recovery

| Scenario | C2 IC | C3 IC | C4 IC |
|----------|-------|-------|-------|
| Signal | -0.0170 | 0.0296 | -0.0040 |
| Null | -0.0237 | 0.0350 | -0.0023 |

## A — Formula-Fidelity Tests

Run: `python tests/psb2/run_quick.py`

```
Fortnightly grid: 56 dates, first=2020-09-15, last=2022-12-30
  PASS test_fortnightly_grid
  Exit bands: C2=0.40, C3=0.40
  PASS test_exit_band
  C4 staggered: 6 tranches
  PASS test_staggered_tranches
  Bonferroni m = 3
  PASS test_bonferroni_m
Sealed fence OK: observed MAX(trade_date)=2020-01-28 <= cutoff=2022-12-31
  C2 min 8 non-NULL: correctly skipped entity with 7 recent observations
  PASS test_c2_fortnightly_mean_min_8
Sealed fence OK: observed MAX(trade_date)=2020-02-25 <= cutoff=2022-12-31
  C2 252-day baseline: z = 17.6071 (expected > 1.0)
  PASS test_c2_252_day_baseline_ending_t21
Sealed fence OK: observed MAX(trade_date)=2020-02-25 <= cutoff=2022-12-31
  C3 S0001(p=1,r=+10%): s=0.1000 (expected ~ +0.10)
  C3 S0002(p=0,r=-10%): s=0.1000 (expected ~ +0.10)
  PASS test_c3_21_day_return_horizon
Sealed fence OK: observed MAX(trade_date)=2022-12-30 <= cutoff=2022-12-31
Sealed fence OK: observed MAX(trade_date)=2022-12-30 <= cutoff=2022-12-31
  C4 S0001 (momentum +20%): s=0.2000 (expected ~0.20)
  C4 S0002 (momentum -10%): s=-0.1000 (expected ~ -0.10)
  PASS test_c4_lookback
  Power hurdle: 0.80 at alpha=0.05
  PASS test_power_hurdle
  Slippage kappa = 5 bp
  PASS test_slippage_kappa
Done in 10.8s
```

## G — Fees and Slippage

Signal C2: net=-0.0742 < gross=-0.0409 drag=340.2bp turnover=0.4677 PASS
Signal C3: net=-0.0194 < gross=0.0220 drag=421.0bp turnover=0.5473 PASS
Signal C4: net=-0.0053 < gross=-0.0027 drag=27.6bp turnover=0.0684 PASS
Null C2: net=-0.0750 < gross=-0.0416 drag=340.4bp turnover=0.4677 PASS
Null C3: net=-0.0089 < gross=0.0292 drag=388.2bp turnover=0.4988 PASS
Null C4: net=-0.0037 < gross=-0.0011 drag=28.0bp turnover=0.0692 PASS

## H — Determinism (S1)

PYTHONHASHSEED=0: e3b0c44298fc1c14...  PYTHONHASHSEED=1: e3b0c44298fc1c14...  **IDENTICAL**

## Predictions

| **C-P1** | Null scenario: |IC| < 0.05 for all | **PASS** |
| **F-P1** | Fence: fenced <= cutoff < unfenced | **PASS** |
| **G-P1** | Fees: net < gross for all | **PASS** |

Time: 391.0s.
