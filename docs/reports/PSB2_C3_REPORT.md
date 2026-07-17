# PSB-2 Phase 2 C3 Battery Report

**Script-generated** — `scripts/psb2/run_phase2.py`. Deterministic run (§10). Code commit `f29f0a7`.

| Field | Value |
|---|---|
| Code commit | `f29f0a7` |
| Store row count | 7,030,920 |
| Store fenced MAX(trade_date) | 2022-12-30 |
| Store unfenced MAX | 2026-07-09 |
| Fence proven | YES — fenced != unfenced |
| Candidate | C3 |
| Cadence | fortnightly (24 ppy) |
| Dev window | 2020-09-04 to 2022-12-31 |
| N formation dates (grid) | 55 |
| Realized n (scored formations) | 55 |

## §6 Metrics

| Metric | Value |
|---|---|
| Mean IC | 0.008312 |
| SD IC | 0.102717 |
| One-sided t | 0.6001 |
| One-sided p | 2.754768e-01 |
| AC₁ | -0.032835 |
| NW t (|AC₁|>0.10) | N/A |
| Imputed mean IC (§4.2) | 0.008365 |
| Sign flag | False |
| Min-names skipped | 0 |
| First-half mean IC | 0.010860 |
| Second-half mean IC | 0.005854 |

## §4.1 Exclusion counts

| Metric | Value |
|---|---|
| Formation-date exclusions (total) | 291 |
| Forward-missing (total) | 2 |

Per-date excl: min=1 max=12
Per-date fwd-missing: min=0 max=1

## §6 Quintile spread

| Metric | Value |
|---|---|
| Net top-quintile spread | -0.011015 (ann. return, net of fees) |
| Gross spread (top - base) | 0.031002 |
| Fee+slippage drag | 444.7 bp/yr |
| One-way turnover | 0.4683 |

Design estimate (rationale, not prediction): turnover ~0.15, fee drag ~78 bp/yr.
Observed turnover 0.4683; observed drag 444.7 bp/yr.

## §7 Power projection

| Metric | Value |
|---|---|
| n* (sealed grid 2023-01-01 to 2026-06-30) | 84 |
| n* fortnightly / monthly | 84 / 42 |
| δ (observed mean IC) | 0.008312 |
| SD_dev | 0.102717 |
| Noncentrality (δ√ n* / SD) | 0.7416 |
| Power at δ | 0.1816 |
| Power at δ/2 | 0.1008 |
| Power-NW at δ | N/A |
| Power hurdle | ≥ 0.8 |


## §8 Eligibility

| Criterion | Threshold | Observed | Pass |
|---|---|---|---|
| (i) Mean IC > 0 | > 0 | 0.008312 | True |
| (ii) Net spread > 0 | > 0 | -0.011015 | False |
| (iii) Power ≥ 0.80 | ≥ 0.80 | 0.1816 | False |

**Not eligible:** one or more §8 criteria not met. C3 cannot be the winner.

**Robustness sub-window:** 2020-09-04 to 2022-12-31. For C2/C3 this is their entire declared window — the declared-window columns above are also the common sub-window columns and are not duplicated.

## Formation dates (55)

First: 2020-09-15, Last: 2022-12-15

## §10 Determinism compliance

Digest (sha256 of core metrics): `ff780cb8de509a98`

This report is 100% script-generated. No hand-edited numbers. Re-running the identical code against the identical dev-fenced store yields byte-identical output.

