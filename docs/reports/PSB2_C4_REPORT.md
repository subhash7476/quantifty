# PSB-2 Phase 2 C4 Battery Report

**Script-generated** — `scripts/psb2/run_phase2.py`. Deterministic run (§10). Code commit `1235b3d`.

| Field | Value |
|---|---|
| Code commit | `1235b3d` |
| Store row count | 7,030,920 |
| Store fenced MAX(trade_date) | 2022-12-30 |
| Store unfenced MAX | 2026-07-09 |
| Fence proven | YES — fenced != unfenced |
| Candidate | C4 |
| Cadence | monthly (12 ppy) |
| Dev window | 2012-01-01 to 2022-12-31 |
| N formation dates (grid) | 131 |
| Realized n (scored formations) | 131 |

## §6 Metrics

| Metric | Value |
|---|---|
| Mean IC | 0.046550 |
| SD IC | 0.208949 |
| One-sided t | 2.5499 |
| One-sided p | 5.968292e-03 |
| AC₁ | -0.024403 |
| NW t (|AC₁|>0.10) | N/A |
| Imputed mean IC (§4.2) | 0.046154 |
| Sign flag | False |
| Min-names skipped | 0 |
| First-half mean IC | 0.044083 |
| Second-half mean IC | 0.048981 |

## §4.1 Exclusion counts

| Metric | Value |
|---|---|
| Formation-date exclusions (total) | 375 |
| Forward-missing (total) | 21 |

Per-date excl: min=0 max=9
Per-date fwd-missing: min=0 max=2

## §6 Quintile spread

| Metric | Value |
|---|---|
| Net top-quintile spread | 0.028667 (ann. return, net of fees) |
| Gross spread (top - base) | 0.030824 |
| Fee+slippage drag | 35.2 bp/yr |
| One-way turnover | 0.0776 |

Design estimate (rationale, not prediction): turnover ~0.17, fee drag ~2.5 pp/yr.
Observed turnover 0.0776; observed drag 35.2 bp/yr.

## §7 Power projection

| Metric | Value |
|---|---|
| n* (sealed grid 2023-01-01 to 2026-06-30) | 42 |
| n* fortnightly / monthly | 84 / 42 |
| δ (observed mean IC) | 0.046550 |
| SD_dev | 0.208949 |
| Noncentrality (δ√ n* / SD) | 1.4438 |
| Power at δ | 0.4110 |
| Power at δ/2 | 0.1749 |
| Power-NW at δ | N/A |
| Power hurdle | ≥ 0.8 |


## §8 Eligibility

| Criterion | Threshold | Observed | Pass |
|---|---|---|---|
| (i) Mean IC > 0 | > 0 | 0.046550 | True |
| (ii) Net spread > 0 | > 0 | 0.028667 | True |
| (iii) Power ≥ 0.80 | ≥ 0.80 | 0.4110 | False |

**Not eligible:** one or more §8 criteria not met. C4 cannot be the winner.

**Robustness sub-window:** 2020-09-04 to 2022-12-31 (28 monthly grid dates for C4). See Prompt 3 for the sub-window column.

## Formation dates (131)

First: 2012-01-31, Last: 2022-11-30

## §10 Determinism compliance

Digest (sha256 of core metrics): `b3569ade45003899`

This report is 100% script-generated. No hand-edited numbers. Re-running the identical code against the identical dev-fenced store yields byte-identical output.

