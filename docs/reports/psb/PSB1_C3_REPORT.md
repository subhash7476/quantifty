# PSB-1 Phase 2 C3 Battery Report — Delivery Ratio Z-Score

**Script-generated** — `scripts/psb1/run_c3.py`. Deterministic run (§10).

| Field | Value |
|---|---|
| Code commit | `5eecf79` |
| Store row count | 7,030,920 |
| Store fenced MAX(trade_date) | 2022-12-30 |
| Store unfenced MAX | 2026-07-09 |
| Candidate | C3 |
| Cadence | weekly |
| Dev window | 2020-04-01 to 2022-12-31 |
| N formation dates (n) | 143 |

## §6 Metrics

| Metric | Value |
|---|---|
| Mean IC | 0.024808 |
| SD IC | 0.101335 |
| One-sided t | 2.9275 |
| One-sided p | 1.990357e-03 |
| AC₁ | -0.035019 |
| NW t (|AC₁|>0.1) | N/A |
| Imputed mean IC (§4.2) | 0.024628 |
| Sign flag | False |
| Min-names skipped | 0 |
| First-half mean IC | 0.024044 |
| Second-half mean IC | 0.025562 |

## §4.1 Exclusion counts

| Metric | Value |
|---|---|
| Formation-date exclusions (total) | 297 |
| Forward-missing (total) | 4 |
| CA-excluded forward (D5.8, total) | 0 |

Per-date excl: min=0 max=10
Per-date fwd-missing: min=0 max=1
Per-date ca-excl: min=0 max=0

## §6 Quintile spread

| Metric | Value |
|---|---|
| Net top-quintile spread (upper-bound) | -0.024512 (ann. return, net of fees) |
| Gross spread (top - base) | 0.111233 |
| Q1-Q5 spread | 0.174532 |
| Fee+slippage drag | 1383.7 bp/yr |
| One-way turnover | 0.5872 |

## §7 Power projection

| Metric | Value |
|---|---|
| n* (sealed grid [2023-2026]) | 183 |
| Power at δ (observed mean IC) | 0.9510 |
| Power at δ/2 | 0.5019 |
| Power-NW at δ | N/A |

## Formation dates (143)

First: 2020-04-03, Last: 2022-12-23

## §10 Determinism compliance

This report is 100% script-generated. No hand-edited numbers.

