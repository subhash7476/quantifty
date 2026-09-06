# PSB-1 Phase 2 C2 Battery Report — Residual Reversal

**Script-generated** — `scripts/psb1/run_c2.py`. Deterministic run (§10).

| Field | Value |
|---|---|
| Code commit | `b41682c` |
| Store row count | 7,030,920 |
| Store fenced MAX(trade_date) | 2022-12-30 |
| Store unfenced MAX | 2026-07-09 |
| Candidate | C2 |
| Cadence | weekly |
| Dev window | 2012-01-01 to 2022-12-31 |
| N formation dates (n) | 529 |

## §6 Metrics

| Metric | Value |
|---|---|
| Mean IC | 0.035153 |
| SD IC | 0.121938 |
| One-sided t | 6.6306 |
| One-sided p | 4.141093e-11 |
| AC₁ | 0.098113 |
| NW t (|AC₁|>0.1) | N/A |
| Imputed mean IC (§4.2) | 0.035216 |
| Sign flag | False |
| Min-names skipped | 0 |
| First-half mean IC | 0.043272 |
| Second-half mean IC | 0.027065 |

## §4.1 Exclusion counts

| Metric | Value |
|---|---|
| Formation-date exclusions (total) | 9147 |
| Forward-missing (total) | 21 |
| CA-excluded forward (D5.8, total) | 3 |

Per-date excl: min=0 max=200
Per-date fwd-missing: min=0 max=2
Per-date ca-excl: min=0 max=1

## §6 Quintile spread

| Metric | Value |
|---|---|
| Net top-quintile spread (upper-bound) | -0.086010 (ann. return, net of fees) |
| Gross spread (top - base) | 0.054791 |
| Q1-Q5 spread | 0.149504 |
| Fee+slippage drag | 1421.6 bp/yr |
| One-way turnover | 0.7872 |

## §7 Power projection

| Metric | Value |
|---|---|
| n* (sealed grid [2023-2026]) | 183 |
| Power at δ (observed mean IC) | 0.9875 |
| Power at δ/2 | 0.6171 |
| Power-NW at δ | N/A |

## Formation dates (529)

First: 2012-11-09, Last: 2022-12-23

## §10 Determinism compliance

This report is 100% script-generated. No hand-edited numbers.

