# PSB-2 Phase 2 C2 Battery Report

**Script-generated** — `scripts/psb2/run_phase2.py`. Deterministic run (§10). Code commit `ca34557`.

| Field | Value |
|---|---|
| Code commit | `ca34557` |
| Store row count | 7,030,920 |
| Store fenced MAX(trade_date) | 2022-12-30 |
| Store unfenced MAX | 2026-07-09 |
| Fence proven | YES — fenced != unfenced |
| Candidate | C2 |
| Cadence | fortnightly (24 ppy) |
| Dev window | 2020-09-04 to 2022-12-31 |
| N formation dates (grid) | 55 |
| Realized n (scored formations) | 55 |

## §6 Metrics

| Metric | Value |
|---|---|
| Mean IC | 0.034892 |
| SD IC | 0.104033 |
| One-sided t | 2.4874 |
| One-sided p | 7.994592e-03 |
| AC₁ | -0.181762 |
| NW t (|AC₁|>0.10) | 2.8217 |
| Imputed mean IC (§4.2) | 0.034781 |
| Sign flag | False |
| Min-names skipped | 0 |
| First-half mean IC | 0.025894 |
| Second-half mean IC | 0.043569 |

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
| Net top-quintile spread | 0.045733 (ann. return, net of fees) |
| Gross spread (top - base) | 0.070309 |
| Fee+slippage drag | 270.3 bp/yr |
| One-way turnover | 0.2701 |

Design estimate (rationale, not prediction): turnover ~0.15, fee drag ~78 bp/yr.
Observed turnover 0.2701; observed drag 270.3 bp/yr.

## §7 Power projection

| Metric | Value |
|---|---|
| n* (sealed grid 2023-01-01 to 2026-06-30) | 84 |
| n* fortnightly / monthly | 84 / 42 |
| δ (observed mean IC) | 0.034892 |
| SD_dev | 0.104033 |
| Noncentrality (δ√ n* / SD) | 3.0740 |
| Power at δ | 0.9198 |
| Power at δ/2 | 0.4521 |
| Power-NW at δ | 0.9651 |
| Power hurdle | ≥ 0.8 |

**AC₁ exposure (§7):** AC₁ > 0.10. Adjacent fortnightly formations overlap in their 252-day delivery baseline. The simple-t projection may be optimistic — a fortnightly candidate can clear the 0.80 hurdle on a projection its own reported AC₁ shows is optimistic. The gating power remains simple-t. The operator reads every power number with this exposure in view.

## §8 Eligibility

| Criterion | Threshold | Observed | Pass |
|---|---|---|---|
| (i) Mean IC > 0 | > 0 | 0.034892 | True |
| (ii) Net spread > 0 | > 0 | 0.045733 | True |
| (iii) Power ≥ 0.80 | ≥ 0.80 | 0.9198 | True |

**Eligible:** all three §8 criteria met. C2 proceeds to §8 ranking in Prompt 3.

**Robustness sub-window:** 2020-09-04 to 2022-12-31. For C2/C3 this is their entire declared window — the declared-window columns above are also the common sub-window columns and are not duplicated.

## Formation dates (55)

First: 2020-09-15, Last: 2022-12-15

## §10 Determinism compliance

Digest (sha256 of core metrics): `41e3732909f9bf8d`

This report is 100% script-generated. No hand-edited numbers. Re-running the identical code against the identical dev-fenced store yields byte-identical output.

