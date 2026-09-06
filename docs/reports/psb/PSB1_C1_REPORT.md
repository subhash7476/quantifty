# PSB-1 Phase 2 C1 Battery Report

**Script-generated** — `scripts/psb1/run_c1.py`. Deterministic run (§10).

| Field | Value |
|---|---|
| Code commit | `187056f` |
| Store row count | 7,030,920 |
| Store fenced MAX(trade_date) | 2022-12-30 |
| Store unfenced MAX | 2026-07-09 |
| Candidate | C1 |
| Cadence | weekly |
| Dev window | 2012-01-01 to 2022-12-31 |
| N formation dates (n) | 569 |

## §6 Metrics

| Metric | Value |
|---|---|
| Mean IC | 0.023190 |
| SD IC | 0.147010 |
| One-sided t | 3.7628 |
| One-sided p | 9.274402e-05 |
| AC₁ | 0.096600 |
| NW t (|AC₁|>0.1) | N/A |
| Imputed mean IC (§4.2) | 0.023258 |
| Sign flag | False |
| Min-names skipped | 0 |
| First-half mean IC | 0.028735 |
| Second-half mean IC | 0.017665 |

## §4.1 Exclusion counts

| Metric | Value |
|---|---|
| Formation-date exclusions (total) | 38 |
| Forward-missing (total) | 22 |
| CA-excluded forward (D5.8, total) | 3 |

Per-date excl: min=0 max=2
Per-date fwd-missing: min=0 max=2
Per-date ca-excl: min=0 max=1

## §6 Quintile spread

| Metric | Value |
|---|---|
| Net top-quintile spread (upper-bound) | -0.168049 (ann. return, net of fees) |
| Gross spread (top - base) | -0.040122 |
| Q1-Q5 spread | 0.010526 |
| Fee+slippage drag | 1293.0 bp/yr |
| One-way turnover | 0.7717 |

## §7 Power projection

| Metric | Value |
|---|---|
| n* (sealed grid [2023-2026]) | 183 |
| Power at δ (observed mean IC) | 0.6848 |
| Power at δ/2 | 0.2803 |
| Power-NW at δ | N/A |

## Formation dates (569)

First: 2012-02-03, Last: 2022-12-23

## §10 Determinism compliance

This report is 100% script-generated. No hand-edited numbers. Re-running the identical code against the identical dev-fenced store yields byte-identical output.

