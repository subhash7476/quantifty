# TREND — Research Feasibility Assessment

**VERDICT: PROCEED** — not provably infeasible — this is a floor, not authorization to build.

- Methodology version: `2.0.0`
- Declaration SHA-256: `051b316a27f11fa83f8f3168ccfc50332ad34c180062ce74e205efc8d445ef37`
- Metric: rank_ic | Test: one_sided | Power hurdle: 0.8
- Formations available: 31 (monthly, Sealed projection window 2024-01-01 -> 2026-07-20 (~31 monthly formations). Continuous futures series built from raw bhavcopy (2016-02-11 -> 2026-07-20, 363 FUTSTK underlyings, same roll methodology as Carry). After 12-month TSMOM lookback warmup, first feasible formation is 2017-02. NSE F&O history before 2016 is not obtainable (SFB-1/F1 lockdown finding). Per the pre-reg section 9 acceptance rule, TRAIN is 2017-02 -> 2021-12 (~59 monthly formations) and HOLDOUT is 2022-01 -> 2023-12 (24 monthly).)

## Optimistic corner

| Quantity | Value |
|---|---|
| delta (high) | 0.055 |
| SD (low) | 0.1 |
| n (raw, no AC haircut) | 31 |
| **Max achievable power** | **0.9110** |

The corner is **intentionally unrealistic.** This independence holds for
`rank_ic` because IC mean and IC dispersion are separately estimable — a
declaration coupling them (e.g. deriving one from the other) is invalid and
the gate's `validate()` will reject it. With independence established,
(delta_hi, sd_lo) describes a large edge with unusually stable outcomes —
the least plausible combination in practice and the most generous to the
construct. This maximizes the burden of proof for ABANDON, so a firing gate
is unarguable, while correspondingly weakening PROCEED to its stated meaning
of *not provably infeasible*.

## Formations required for power 0.80

| Band point | n required |
|---|---|
| Optimistic corner | 22 |
| Central | 88 |
| Pessimistic | 503 |
| **Available** | **31** |

## Declared bands and provenance

**delta: [0.02, 0.055]**

Declared direction: POSITIVE rank-IC (long high trend, short low). Vol-scaled multi-horizon TSMOM captures under-reaction and risk-transfer (MOP 2013). Delta is declared as a POSITIVE magnitude representing |IC|; the sign is committed in TREND_PHASE0_PRE_REGISTRATION section 1 and cannot be flipped after a TRAIN read.

Defense of magnitude [0.020, 0.055]: cross-sectional TSMOM rank-IC in equity futures globally sits ~0.02-0.06 (MOP 2013 Table 2; Baltas-Kosowski 2013). The vol-scaling and multi-horizon averaging reduce noise, supporting the upper bound. PSB-1 C1 (plain weekly reversal on cash equity) showed mean rank-IC |~0.023|; vol-scaled multi-horizon TSMOM on SSF (lower noise, longer horizon, vol-scaling) is expected to be higher. The band is literature-defended, not derived from an in-sample read.

**SD: [0.1, 0.18]**

Monthly cross-sectional IC dispersion for a ~120-180 name SSF cross-section. Same regime as Carry: IC dispersion at this breadth is dominated by true time-variation rather than sampling noise; equity-factor monthly IC SD is ~0.10-0.18. Using the identical band as Carry ensures the RFA comparison is apples-to-apples across sleeves.

**Prior exposure**

Operator's prior reads are in cash-equity delivery constructs (PSB-1 C1-C5, PSB-2 C2/C4, SFB-1/F1) and the recently completed Carry TRAIN read. The F1 cash-synthetic screen tested 12-1 cross-sectional momentum with an intraday bracket but on a concentrated <=10-name book with single-horizon and no vol-scaling -- not equivalent to this TSMOM construct. No TSMOM/vol-scaled-multi-horizon construct has been screened on this data. The SSF substrate (363 underlyings, spot join 100%) is identical to Carry's; the Trend TRAIN will read the same forward returns against a different signal.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
