# MSRP Phase 7 — Gates (b) + (c): Options Fee Model and Fee-Impact Triage

*Generated: 2026-07-07T21:44:03.750568*

**Caveats (by design of the triage):** signal is IN-SAMPLE (frozen artifact coefficients were fit on this same dev window) so gross edges are optimistic; thresholds are dev-quantiles; bhavcopy open/close fills; no slippage; no margin denominator; 1 lot throughout (lot size era-accurate: 50/25/75).

- Dev window: 2023-01-02 -> 2025-12-31; tradable days: 695 (skipped 5 no-next-session, 0 no-valid-straddle)
- DTE of selected contracts: median 6, p10 2, p90 8
- Mean round-trip fee (short, 1 lot): Rs 125; mean |gross| per day: Rs 2188; **fee drag = 5.7% of mean absolute daily gross**

## Arms (1 lot, Rs, dev window total)

| Arm | Days | %Days | Gross | Fees | Net | Net/day | Hit% | Sharpe |
|---|---|---|---|---|---|---|---|---|
| Unconditional long straddle | 695 | 100% | -197,110 | 86,485 | -283,595 | -408 | 32.2 | -1.89 |
| Unconditional short straddle | 695 | 100% | 197,110 | 86,663 | 110,447 | 159 | 63.2 | 0.74 |
| Gated short (ratio <= q10) | 70 | 10% | -9,470 | 8,315 | -17,785 | -254 | 58.6 | -1.39 |
| Gated long (ratio >= q90) | 70 | 10% | -74,729 | 9,107 | -83,835 | -1,198 | 31.4 | -6.54 |
| Gated short (ratio <= q20) | 139 | 20% | 31,112 | 16,951 | 14,162 | 102 | 66.2 | 0.53 |
| Gated long (ratio >= q80) | 139 | 20% | -116,800 | 17,544 | -134,344 | -967 | 31.7 | -6.02 |
| Gated short (ratio <= q30) | 209 | 30% | -1,719 | 25,532 | -27,251 | -130 | 63.2 | -0.55 |
| Gated long (ratio >= q70) | 209 | 30% | -123,521 | 26,479 | -150,000 | -718 | 32.5 | -3.56 |
| Abstention short (implied > CI90 hi) | 538 | 77% | 85,813 | 66,697 | 19,116 | 36 | 62.3 | 0.16 |
| Abstention long (implied < CI90 lo) | 0 | 0% | 0 | 0 | 0 | 0 | 0.0 | 0.00 |

## Combined D1 rule (short <= q20, long >= q80)

- short leg: 139 days, gross 31,112, fees 16,951, net 14,162 (net/day 102, hit 66.2%, Sharpe 0.53)
- long leg: 139 days, gross -116,800, fees 17,544, net -134,344 (net/day -967, hit 31.7%, Sharpe -6.02)
- **combined net: Rs -120,182**

## Per-year (short arms)

| Year | Days | Lot | Uncond short net | Gated short net (q20) | Gated days | Avg fee RT | Avg &#124;gross&#124; |
|---|---|---|---|---|---|---|---|
| 2023 | 201 | 50 | -16,636 | -13,594 | 52 | 114 | 1,290 |
| 2024 | 246 | 25 | 42,434 | -13,112 | 43 | 118 | 1,805 |
| 2025 | 248 | 75 | 84,648 | 40,868 | 44 | 140 | 3,297 |

Rupee figures are per 1 lot with the era-accurate lot size, so per-year totals are not directly comparable across the 50/25/75 lot eras.

## Robustness — where the chain breaks

Rank (Spearman) correlations over the tradable days, in causal order:

1. `E[RV_t+1]` vs realized `RV_t+1` (the certified construct): **0.651** — the artifact does its job (in-sample).
2. Realized `RV_t+1` vs long-straddle open->close return (the transmission): **0.093** — even PERFECT next-day RV foresight barely predicts unhedged straddle P&L. This is the construct gap of research-doc finding 1, measured.
3. D1 signal `E[RV]/implied_vix` vs long-straddle return: **-0.027** — no exploitable rank relationship.
4. Straddle-implied denominator variant (`E[RV] / (entry_prem/spot/sqrt(DTE))`): rank 0.160; gated arms net short 19,799 / long 21,637 over 139+139 days (149/day vs 159/day unconditional short). Mechanically contaminated (entry premium in both signal and return denominators) and mildly look-ahead — an optimistic upper bound that STILL does not beat the dumb baseline.

## Verdict

- **Gate (b) — options fee model: PASS.** `core/execution/options/fees.py`, effective-dated statutory schedules (STT 0.05/0.0625/0.1/0.15%, NSE txn 0.0495/0.03503%, SEBI, GST, stamp), 12 unit tests green (`tests/execution/test_options_fees.py`).
- **Gate (c) — fee-impact triage: STOP CONDITION TRIGGERED.** Fees are NOT the binding constraint (drag ~6% of mean absolute daily gross; the unconditional short survives costs). The binding failure is the construct transmission: the Knowledge-gated D1 rule is net NEGATIVE in-sample while the no-Knowledge unconditional short-straddle baseline is net positive — the artifact adds nothing over the dumb premium seller in any variant tried, because next-day RV itself is nearly orthogonal to unhedged straddle P&L at this horizon.
- Per research-doc par.6.1: **do not pre-register D1 as specified.** The unconditional short-VRP result is not a rescue: it does not consume the Knowledge (fails the charter's Phase-7 definition), is era-concentrated (2023 negative), and carries unmodelled short-vol tail risk.
- Decision on how to proceed (delta-hedged construct needs intraday options data that does not exist; alternative transmissions; or stand down Phase 7) belongs to the operator.

