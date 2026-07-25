# IVOL — Research Feasibility Assessment

**VERDICT: PROCEED** — not provably infeasible — this is a floor, not authorization to build.

- Methodology version: `2.0.0`
- Declaration SHA-256: `d7ebcbcc743dc708ab6bb0896bf5bde8187d72f38d6b62fe58a24e203e48989f`
- Metric: rank_ic | Test: one_sided | Power hurdle: 0.8
- Formations available: 42 (monthly, Sealed projection window 2023-01-01 -> 2026-07-20 (~42 monthly formations). The futures continuous series spans 2016-02-11 -> 2026-07-20 (futures_bhavcopy, 363 FUTSTK underlyings; roll-adjusted series reused unchanged from Trend, fourth use). After 252-day beta warmup, first feasible formation is 2017-02. NSE F&O history before 2016 is not obtainable (SFB-1/F1 lockdown finding), so n* cannot be raised by pulling more calendar. Per the pre-reg section 9 acceptance rule (Flow/Skew/LAG allocation that maximizes the sealed window): TRAIN is 2017-02 -> 2020-12 (~47 monthly formations) and HOLDOUT is 2021-01 -> 2022-12 (24 monthly).)

## Optimistic corner

| Quantity | Value |
|---|---|
| delta (high) | 0.06 |
| SD (low) | 0.1 |
| n (raw, no AC haircut) | 42 |
| **Max achievable power** | **0.9853** |

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
| Optimistic corner | 19 |
| Central | 50 |
| Pessimistic | 127 |
| **Available** | **42** |

## Declared bands and provenance

**delta: [0.04, 0.06]**

Declared direction: NEGATIVE rank-IC (long low-vol, short high-vol). High idiosyncratic volatility predicts LOW forward returns -- the high-IVOL-underperforms anomaly (Ang-Hodrick-Xing-Zhang 2006/2009; Frazzini-Pedersen 2014, Betting Against Beta). Delta is declared as a POSITIVE magnitude representing |IC|; the sign (negative) is committed in IVOL_PHASE0_PRE_REGISTRATION section 1 and cannot be flipped after a TRAIN read.

Defense of magnitude [0.040, 0.060]: the BAB / high-IVOL anomaly is among the strongest documented cross-sectionally -- Ang et al. and Frazzini-Pedersen (t>5) report IC ~0.04-0.06. PSB-1 C5 (cash-equity low-vol, monthly banded) realized +0.068 on Indian data -- the highest IC of any candidate this repository has run -- clearing significance (t=3.14, p=0.001), sign, and net spread (+4.3%), and dying only on composite power projection (0.54). The pessimistic bound 0.040 is the literature floor; the optimistic 0.060 sits just under C5's realized 0.068, leaving room for the India-retail-amplification upside (lottery preference is the documented driver of low-vol, and India has among the highest retail participation globally) without overclaiming. Literature + C5 defended, not derived from an in-sample futures read.

**SD: [0.1, 0.18]**

Monthly cross-sectional IC dispersion for the same ~120-180 name SSF cross-section the engine trades. IC dispersion at this breadth is dominated by true time-variation rather than sampling noise; equity-factor monthly IC SD sits ~0.10-0.18. IVOL uses the identical substrate, cadence, and cross-section size as Carry/Trend/Flow/LAG, so the identical band [0.10, 0.18] keeps the RFA comparison apples-to-apples. Counterevidence disclosed: PSB-1 C5 (cash equity) realized higher dispersion (the reason its composite power was only 0.54) -- the bet is that the futures substrate (liquid, filtered, beta-neutralized) has lower dispersion than cash. The gate-2 SD band check is the honest arbiter: realized SD > 0.18 fires the C2 wide-SD stop and halts the sleeve.

**Prior exposure**

Closest prior read: PSB-1 C5 (cash-equity low-vol, monthly banded). C5 produced mean IC +0.068 (t=3.14, p=0.001), net +4.3% at 14 bp/yr drag -- it cleared significance + sign + net and died only on composite power (0.54). IVOL differs in substrate (futures vs cash), universe (SSF-liquid), fee structure, and explicit beta-neutralization (residual vol, the BAB construct). Disclosed as prior-adjacent; m counts this. With TREND (dead, own-name momentum) and LAG (dead, sector-leader diffusion) also in the vol/momentum neighborhood, the honest minimum is m >= 3 for the family-wise penalty. Carry (survived, residual basis) is a different economic family; correlation measured on TRAIN.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
