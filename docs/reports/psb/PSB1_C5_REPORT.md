# PSB-1 Phase 2 C5 Battery Report — Low-Vol Anomaly (Monthly, Banded)

**Script-generated** — `scripts/psb1/run_c5.py`. Deterministic run (§10).

| Field | Value |
|---|---|
| Code commit | `4394bb3` |
| Store row count | 7,030,920 |
| Store fenced MAX(trade_date) | 2022-12-30 |
| Store unfenced MAX | 2026-07-09 |
| Candidate | C5 |
| Cadence | monthly |
| Dev window | 2012-01-01 to 2022-12-31 |
| N formation dates (n) | 131 |

Score: s = −σ_i (252-day daily vol). Low vol → high score. Banded holding
(C5_EXIT_BAND=0.40): entities within top 40% of prior period are retained.

## §6 Metrics

| Metric | Value |
|---|---|
| Mean IC | 0.067639 |
| SD IC | 0.246232 |
| One-sided t | 3.1440 |
| One-sided p | 1.032529e-03 |
| AC₁ | -0.021839 |
| NW t (|AC₁|>0.1) | N/A |
| Imputed mean IC (§4.2) | 0.067712 |
| Sign flag | False |
| Min-names skipped | 0 |
| First-half mean IC | 0.064580 |
| Second-half mean IC | 0.070651 |

## §4.1 Exclusion counts

| Metric | Value |
|---|---|
| Formation-date exclusions (total) | 292 |
| Forward-missing (total) | 22 |
| CA-excluded forward (D5.8, total) | 3 |

Per-date excl: min=0 max=7
Per-date fwd-missing: min=0 max=2
Per-date ca-excl: min=0 max=1

## §6 Quintile spread

| Metric | Value |
|---|---|
| Net top-quintile spread (upper-bound) | 0.043373 (ann. return, net of fees) |
| Gross spread (top - base) | 0.043487 |
| Q1-Q5 spread | 0.162176 |
| Fee+slippage drag | 14.3 bp/yr |
| One-way turnover | 0.0375 |

## §7 Power projection

| Metric | Value |
|---|---|
| n* (sealed grid [2023-2026]) | 42 |
| Power at δ (observed mean IC) | 0.5422 |
| Power at δ/2 | 0.2208 |
| Power-NW at δ | N/A |

## Formation dates (131)

First: 2012-01-31, Last: 2022-11-30

## §10 Determinism compliance

This report is 100% script-generated. No hand-edited numbers.

