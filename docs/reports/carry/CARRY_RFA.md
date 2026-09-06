# CARRY — Research Feasibility Assessment

**VERDICT: PROCEED** — not provably infeasible — this is a floor, not authorization to build.

- Methodology version: `2.0.0`
- Declaration SHA-256: `fffa8343b42af74636a971595970554d3827fdbf0a652de7d1188b3f4f089924`
- Metric: rank_ic | Test: one_sided | Power hurdle: 0.8
- Formations available: 42 (monthly, Sealed projection window 2023-01-01 -> 2026-07-20 (~42 monthly formations). The futures substrate spans 2016-02-11 -> 2026-07-20 (futures_bhavcopy, 363 FUTSTK underlyings). NSE F&O history before 2016 is not obtainable (SFB-1/F1 lockdown finding), so n* cannot be raised by pulling more calendar. Per the pre-reg section 9 acceptance rule, TRAIN is 2016-03-31 -> 2020-12-31 (~58 monthly formations) and HOLDOUT is 2021-01 -> 2022-12 (24 monthly).)

## Optimistic corner

| Quantity | Value |
|---|---|
| delta (high) | 0.045 |
| SD (low) | 0.1 |
| n (raw, no AC haircut) | 42 |
| **Max achievable power** | **0.8893** |

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
| Optimistic corner | 32 |
| Central | 117 |
| Pessimistic | 503 |
| **Available** | **42** |

## Declared bands and provenance

**delta: [0.02, 0.045]**

Declared direction: NEGATIVE rank-IC (short high residual carry, long low). A rich residual basis signals crowded leveraged longs / expensive borrow, which mean-reverts. Delta is declared as a POSITIVE magnitude representing |IC|; the sign is committed in CARRY_PHASE0_PRE_REGISTRATION section 1 and cannot be flipped after a TRAIN read.

Defense of magnitude [0.020, 0.045]: cross-sectional carry/basis IC in the equity and futures literature (Koijen-Moskowitz-Pedersen-Vrugt 2018; Asness-Moskowitz-Pedersen 2013) sits ~0.02-0.05 for a single well-constructed factor. Residual-basis in Indian single-stock futures is defended at the same range, upper end reflecting India's stronger borrow-demand dispersion across the ~180-name SSF universe. The band is literature-defended, not derived from an in-sample read.

**SD: [0.1, 0.18]**

Monthly cross-sectional IC dispersion for a ~120-180 name SSF cross-section. IC dispersion at this breadth is dominated by true time-variation rather than sampling noise; equity-factor monthly IC SD is ~0.10-0.18 (same basis cited in the Carry pre-reg section 7). No special tightening is defensible -- the residual basis inherits the general equity-factor IC dispersion regime.

**Prior exposure**

Operator's prior reads are momentum/delivery constructs (PSB-1 C1-C5, PSB-2 C2/C4, SFB-1/F1). NONE is a carry/basis construct -- carry has not been screened on this data, so prior exposure to THIS signal is nil. The general finding that monthly cross-sectional equity is demonstrability-constrained (RFA retrospective, CLAUDE.md) is methodological, not a peek at carry's realized numbers, and is already priced into the pre-reg section 7.1.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
