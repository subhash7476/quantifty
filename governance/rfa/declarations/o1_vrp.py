from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="O1",
    methodology_version="1.0.0",
    delta_lo=0.002,
    delta_hi=0.005,
    sd_lo=0.025,
    sd_hi=0.060,
    delta_provenance=(
        "Short-premium Sharpes from the variance-risk-premium literature: "
        "Bakshi-Ju (2017) and Cheng (2018, JFE) on US index options report "
        "net-of-cost annualized Sharpes of 0.4-1.0 for defined-risk short "
        "variance. Indian short-premium studies (Kumar-Iyer et al) sit in "
        "the same range, sometimes higher on the unconditional premium but "
        "lower after regime clustering. The mean band [0.002, 0.005] per "
        "week on SPAN margin is the translation of Sharpe 0.5-1.0 at the "
        "declared SD band: weekly_mean = (S/sqrt(52)) * weekly_sd."
    ),
    sd_provenance=(
        "Per-trade weekly PnL SD on SPAN margin. Lower bound 0.025 (2.5%, "
        "annualized 18%) reflects a defined-risk iron-condor structure "
        "with bounded wings, computed against NseMarginEngine SPAN scans. "
        "Upper bound 0.060 (6%, annualized 43%) incorporates the Moreira-"
        "Muir (2017) vol-regime clustering haircut: losses arrive bunched "
        "in vol spikes, inflating the unconditional SD well above the "
        "calm-regime estimate."
    ),
    prior_exposure=(
        "Operator has read OPTIONS_STRATEGY_RESEARCH.md (the O1 candidate "
        "design at section 3.O1) and MSRP_PHASE7_FEE_TRIAGE.md (the "
        "unconditional short ATM straddle recorded net +Rs 110K over 695 "
        "dev days with fees at 6% of gross; 2023 was negative; tail risk "
        "unmodelled). The +Rs 158/day average translates to roughly 0.5% "
        "weekly on SPAN margin, which sits inside the delta band declared "
        "above; the band's center is therefore consistent with prior-"
        "exposed evidence, not independent of it. Operator has also read "
        "PSB-1 C5 and PSB-2 C2 reports, neither of which bear on this "
        "construct."
    ),
    n_available=380,
    cadence="weekly",
    window=(
        "2019-02-11 to 2026-07-17 (NSE F&O bhavcopy backfilled to 2016-02-11 "
        "during PSB-O0 on 2026-07-20; data inspection showed weekly Nifty "
        "options did not list until 2019-02-11 -- pre-2019 data has only "
        "monthly expiries. Original declaration assumed Feb 2016 launch and "
        "n=520; corrected post-backfill to n=380. Verdict unchanged: the "
        "optimistic corner clears comfortably either way.)"
    ),
    test_type="one_sided",
    metric="per_trade_pnl",
)
