# O1 — Research Feasibility Assessment

> **⚠️ WITHDRAWN 2026-07-21 — this verdict must not be cited.** The PROCEED below is an artifact
> of a crossed optimistic corner. `delta` was derived from `sd` via a Sharpe translation, making
> the bands coupled; the gate assumed independence and evaluated `(delta_hi, sd_lo)`, implying
> annualized Sharpe **1.442** — above the declaration's own stated ceiling of 1.0. Read coherently,
> the declared endpoints both sit at Sharpe ≈ 0.59 → max power ≈ 0.49 → **ABANDON**. Reasoning:
> `RFA_GATE_O1_REVIEW.md` §1. The declaration file is preserved unedited so its digest still
> verifies. **No successor declaration is authorized by this withdrawal.**

**VERDICT: PROCEED** — not provably infeasible — this is a floor, not authorization to build.

- Methodology version: `1.0.0`
- Declaration SHA-256: `25d4a723679ade9dedcabcf94d9968074e3e0e350f158630e301f697b64f2dad`
- Metric: per_trade_pnl | Test: one_sided | Power hurdle: 0.8
- Formations available: 380 (weekly, 2019-02-11 to 2026-07-17 (NSE F&O bhavcopy backfilled to 2016-02-11 during PSB-O0 on 2026-07-20; data inspection showed weekly Nifty options did not list until 2019-02-11 -- pre-2019 data has only monthly expiries. Original declaration assumed Feb 2016 launch and n=520; corrected post-backfill to n=380. Verdict unchanged: the optimistic corner clears comfortably either way.))

## Optimistic corner

| Quantity | Value |
|---|---|
| delta (high) | 0.005 |
| SD (low) | 0.025 |
| n (raw, no AC haircut) | 380 |
| **Max achievable power** | **0.9877** |

The corner is **intentionally unrealistic.** Because the bands are declared
independently, (delta_hi, sd_lo) may describe a large edge with unusually stable
outcomes — the least plausible combination in practice and the most generous to the
construct. This is deliberate: it maximizes the burden of proof for ABANDON, so a
firing gate is unarguable, while correspondingly weakening PROCEED to its stated
meaning of *not provably infeasible*.

## Formations required for power 0.80

| Band point | n required |
|---|---|
| Optimistic corner | 156 |
| Central | 913 |
| Pessimistic | 5566 |
| **Available** | **380** |

## Declared bands and provenance

**delta: [0.002, 0.005]**

Short-premium Sharpes from the variance-risk-premium literature: Bakshi-Ju (2017) and Cheng (2018, JFE) on US index options report net-of-cost annualized Sharpes of 0.4-1.0 for defined-risk short variance. Indian short-premium studies (Kumar-Iyer et al) sit in the same range, sometimes higher on the unconditional premium but lower after regime clustering. The mean band [0.002, 0.005] per week on SPAN margin is the translation of Sharpe 0.5-1.0 at the declared SD band: weekly_mean = (S/sqrt(52)) * weekly_sd.

**SD: [0.025, 0.06]**

Per-trade weekly PnL SD on SPAN margin. Lower bound 0.025 (2.5%, annualized 18%) reflects a defined-risk iron-condor structure with bounded wings, computed against NseMarginEngine SPAN scans. Upper bound 0.060 (6%, annualized 43%) incorporates the Moreira-Muir (2017) vol-regime clustering haircut: losses arrive bunched in vol spikes, inflating the unconditional SD well above the calm-regime estimate.

**Prior exposure**

Operator has read OPTIONS_STRATEGY_RESEARCH.md (the O1 candidate design at section 3.O1) and MSRP_PHASE7_FEE_TRIAGE.md (the unconditional short ATM straddle recorded net +Rs 110K over 695 dev days with fees at 6% of gross; 2023 was negative; tail risk unmodelled). The +Rs 158/day average translates to roughly 0.5% weekly on SPAN margin, which sits inside the delta band declared above; the band's center is therefore consistent with prior-exposed evidence, not independent of it. Operator has also read PSB-1 C5 and PSB-2 C2 reports, neither of which bear on this construct.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
