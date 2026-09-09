# PSB-1 Phase 2 C4 Battery Report — Delivery-Conditioned Reversal

**Script-generated** — `scripts/psb1/run_c4.py`. Deterministic run (§10).

| Field | Value |
|---|---|
| Code commit | `ccb481c` |
| Store row count | 7,030,920 |
| Store fenced MAX(trade_date) | 2022-12-30 |
| Store unfenced MAX | 2026-07-09 |
| Candidate | C4 |
| Cadence | weekly |
| Dev window | 2020-04-01 to 2022-12-31 |
| N formation dates (n) | 143 |

Score: s = c1 · (1 − 2·p(c3)) — C1 reversal weighted by delivery percentile.
High-delivery (p→1) flips the reversal sign; low-delivery (p→0) passes reversal through.

## §6 Metrics

| Metric | Value |
|---|---|
| Mean IC | -0.003174 |
| SD IC | 0.089630 |
| One-sided t | -0.4234 |
| One-sided p | 6.636890e-01 |
| AC₁ | -0.102496 |
| NW t (|AC₁|>0.1) | -0.4618 |
| Imputed mean IC (§4.2) | -0.003136 |
| Sign flag | False |
| Min-names skipped | 0 |
| First-half mean IC | -0.005508 |
| Second-half mean IC | -0.000872 |

## §4.1 Exclusion counts

| Metric | Value |
|---|---|
| Formation-date exclusions (total) | 298 |
| Forward-missing (total) | 3 |
| CA-excluded forward (D5.8, total) | 0 |

Per-date excl: min=0 max=10
Per-date fwd-missing: min=0 max=1
Per-date ca-excl: min=0 max=0

## §6 Quintile spread

| Metric | Value |
|---|---|
| Net top-quintile spread (upper-bound) | -0.161439 (ann. return, net of fees) |
| Gross spread (top - base) | 0.003661 |
| Q1-Q5 spread | -0.003071 |
| Fee+slippage drag | 1677.2 bp/yr |
| One-way turnover | 0.7754 |

## §7 Power projection

| Metric | Value |
|---|---|
| n* (sealed grid [2023-2026]) | 183 |
| Power at δ (observed mean IC) | 0.0169 |
| Power at δ/2 | 0.0298 |
| Power-NW at δ | 0.0152 |

## Formation dates (143)

First: 2020-04-03, Last: 2022-12-23

## §10 Determinism compliance

This report is 100% script-generated. No hand-edited numbers.

