from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="SKEW",
    methodology_version="2.0.0",
    metric="rank_ic",
    test_type="two_sided",
    cadence="monthly",
    n_available=42,
    delta_lo=0.020,
    delta_hi=0.045,
    sd_lo=0.10,
    sd_hi=0.18,
    delta_provenance=(
        "Two-sided test: the sign is NOT pre-committed. TRAIN establishes existence "
        "AND reveals the sign in a single read; HOLDOUT confirms the sign persists. "
        "This is the explicit lesson from v1-Carry, where a one-sided bet on an "
        "ambiguous sign burned a whole registration when the data came in the other "
        "way.\n\n"
        "Defense of magnitude [0.020, 0.045] (declared as |IC|): option-skew return "
        "predictability literature (Xing–Zhang–Zhao 2010; An–Ang–Bali–Cakici 2014; "
        "Bali–Hovakimian) documents cross-sectional IC ~0.02-0.05 for skew/IV-spread "
        "signals. The metric is risk-reversal skew = IV(25Δ put) − IV(25Δ call). "
        "Two-sided raises the critical value (~1.96 vs 1.645 one-sided), costing power, "
        "but buys immunity to sign error. The band is literature-defended, not derived "
        "from an in-sample read."
    ),
    sd_provenance=(
        "Monthly cross-sectional IC dispersion for a ~50-100 name liquid-options "
        "cross-section (narrower than Carry/Trend). IC dispersion at this breadth is "
        "dominated by true time-variation rather than sampling noise; equity-factor "
        "monthly IC SD is ~0.10-0.18. The skew sleeve's narrower cross-section does not "
        "justify a tighter SD bound — time-variation of the skew signal is at least as "
        "large as broader signals. No special tightening is defensible."
    ),
    prior_exposure=(
        "Operator's prior reads are momentum/delivery constructs (PSB-1 C1-C5, "
        "PSB-2 C2/C4, SFB-1/F1) and basis signals (Carry). NONE is an option-skew "
        "construct -- option-implied skew has not been screened on this data, so "
        "prior exposure to THIS signal is nil. The general finding that monthly "
        "cross-sectional equity is demonstrability-constrained (RFA retrospective, "
        "CLAUDE.md) is methodological, not a peek at skew's realized numbers."
    ),
    window=(
        "Sealed projection window 2023-01-01 -> 2026-07-20 (~42 monthly formations). "
        "The options substrate spans 2016-02-11 -> 2026-07-20 (stock_options_bhavcopy, "
        "98,320,092 rows, 363 underlyings). Options history before 2016 is not "
        "obtainable (same constraint as futures), so n* cannot be raised by pulling more "
        "calendar. Per the pre-reg section 6 acceptance rule, TRAIN is 2016-07 -> "
        "2020-12 (~54 monthly formations, adjusted for liquidity-warmup) and HOLDOUT is "
        "2021-01 -> 2022-12 (24 monthly)."
    ),
)