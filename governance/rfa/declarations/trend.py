from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="TREND",
    methodology_version="2.0.0",
    metric="rank_ic",
    test_type="one_sided",
    cadence="monthly",
    n_available=31,
    delta_lo=0.020,
    delta_hi=0.055,
    sd_lo=0.10,
    sd_hi=0.18,
    delta_provenance=(
        "Declared direction: POSITIVE rank-IC (long high trend, short low). "
        "Vol-scaled multi-horizon TSMOM captures under-reaction and risk-transfer "
        "(MOP 2013). Delta is declared as a POSITIVE magnitude representing |IC|; "
        "the sign is committed in TREND_PHASE0_PRE_REGISTRATION section 1 and "
        "cannot be flipped after a TRAIN read.\n\n"
        "Defense of magnitude [0.020, 0.055]: cross-sectional TSMOM rank-IC in "
        "equity futures globally sits ~0.02-0.06 (MOP 2013 Table 2; "
        "Baltas-Kosowski 2013). The vol-scaling and multi-horizon averaging reduce "
        "noise, supporting the upper bound. PSB-1 C1 (plain weekly reversal on cash "
        "equity) showed mean rank-IC |~0.023|; vol-scaled multi-horizon TSMOM on "
        "SSF (lower noise, longer horizon, vol-scaling) is expected to be higher. "
        "The band is literature-defended, not derived from an in-sample read."
    ),
    sd_provenance=(
        "Monthly cross-sectional IC dispersion for a ~120-180 name SSF "
        "cross-section. Same regime as Carry: IC dispersion at this breadth is "
        "dominated by true time-variation rather than sampling noise; equity-factor "
        "monthly IC SD is ~0.10-0.18. Using the identical band as Carry ensures "
        "the RFA comparison is apples-to-apples across sleeves."
    ),
    prior_exposure=(
        "Operator's prior reads are in cash-equity delivery constructs "
        "(PSB-1 C1-C5, PSB-2 C2/C4, SFB-1/F1) and the recently completed Carry "
        "TRAIN read. The F1 cash-synthetic screen tested 12-1 cross-sectional "
        "momentum with an intraday bracket but on a concentrated <=10-name book "
        "with single-horizon and no vol-scaling -- not equivalent to this TSMOM "
        "construct. No TSMOM/vol-scaled-multi-horizon construct has been screened "
        "on this data. The SSF substrate (363 underlyings, spot join 100%) is "
        "identical to Carry's; the Trend TRAIN will read the same forward returns "
        "against a different signal."
    ),
    window=(
        "Sealed projection window 2024-01-01 -> 2026-07-20 (~31 monthly "
        "formations). Continuous futures series built from raw bhavcopy "
        "(2016-02-11 -> 2026-07-20, 363 FUTSTK underlyings, same roll methodology "
        "as Carry). After 12-month TSMOM lookback warmup, first feasible formation "
        "is 2017-02. NSE F&O history before 2016 is not obtainable (SFB-1/F1 "
        "lockdown finding). Per the pre-reg section 9 acceptance rule, TRAIN is "
        "2017-02 -> 2021-12 (~59 monthly formations) and HOLDOUT is 2022-01 -> "
        "2023-12 (24 monthly)."
    ),
)
