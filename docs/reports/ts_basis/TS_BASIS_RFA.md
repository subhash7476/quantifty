# TS_BASIS — Research Feasibility Assessment

**VERDICT: PROCEED** — not provably infeasible — this is a floor, not authorization to build.

- Methodology version: `2.0.0`
- Declaration SHA-256: `88971bd805234e2d80b50889f93bcddb5603392b85d2a62a9d152c70814890e8`
- Metric: rank_ic | Test: one_sided | Power hurdle: 0.8
- Formations available: 42 (monthly, SEALED projection window 2023-01-01 -> 2026-07-20 (~42 monthly formations). The futures substrate spans 2016-02-11 -> 2026-07-20. NSE F&O history before 2016 is not obtainable. TRAIN: 2016-03-31 -> 2020-12-31, HOLDOUT: 2021-01 -> 2022-12 per TS_BASIS_PHASE0_PRE_REGISTRATION.md.)

## Optimistic corner

| Quantity | Value |
|---|---|
| delta (high) | 0.09 |
| SD (low) | 0.08 |
| n (raw, no AC haircut) | 42 |
| **Max achievable power** | **1.0000** |

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
| Optimistic corner | 7 |
| Central | 23 |
| Pessimistic | 137 |
| **Available** | **42** |

## Declared bands and provenance

**delta: [0.03, 0.09]**

Declared direction: POSITIVE rank-IC (long high z_ts, short low z_ts). High time-series basis z-score indicates unusually wide futures basis relative to the name's own history. The cross-sectional carry v2 established that high basis predicts positive forward returns in this market; TS Basis measures the same underlying phenomenon but through a time-series rather than cross-sectional lens. The sign is committed per TS_BASIS_PHASE0_PRE_REGISTRATION.md §1 and cannot be flipped.

Defense of magnitude [0.030, 0.090]: cross-sectional carry achieved +0.041 IC on TRAIN. TS Basis is a different processing of the same data - it could be higher (cleaner signal without noise from cross-sectional transformations) or lower (overfit benefit from seeing the carry TRAIN result). The lower bound 0.030 is the minimum for an investable signal; the upper bound 0.090 reflects the TRAIN realization as an optimistic ceiling. The true out-of-sample IC is expected between 0.030 and 0.050.

**SD: [0.08, 0.14]**

Monthly cross-sectional IC dispersion for a ~120-180 name SSF cross-section. Cross-sectional carry TRAIN SD_IC was ~0.10; TS Basis exhibits similar dispersion. The band [0.08, 0.14] reflects the expectation that dispersion is comparable to cross-sectional carry, with a slightly lower lower bound because the time-series signal removes some sources of cross-sectional noise (dividend estimates, common-financing removal, sector dummies).

**Prior exposure**

TRAIN (2016-03 -> 2020-12) has been read for CROSS-SECTIONAL CARRY sign discovery and is BURNED for that signal. TRAIN was ALSO seen for the TS Basis sign - the same underlying basis data was used, and the TRAIN IC +0.089 was observed before this declaration. TRAIN is therefore BURNED for TS Basis sign discovery as well. HOLDOUT (2021-2022, 24 formations) is the only clean out-of-sample window. SEALED (2023-2026, 42 formations) is untouched. Multiplicity: m >= 2 (cross-sectional carry sign + TS Basis sign, both discovered on TRAIN). Evidence floor: Bonferroni alpha = 0.025, one-sided.

TS_BASIS_PHASE0_PRE_REGISTRATION.md §7 records the full prior-exposure table.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
