from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="LAG",
    methodology_version="2.0.0",
    metric="rank_ic",
    test_type="one_sided",
    cadence="monthly",
    n_available=42,
    delta_lo=0.035,
    delta_hi=0.045,
    sd_lo=0.10,
    sd_hi=0.18,
    delta_provenance=(
        "Declared direction: POSITIVE rank-IC (long high-gap names, short "
        "low-gap names). The signal is the sector-leader catch-up gap "
        "(leader_ret - own_ret, averaged over 63/126/252-day horizons). High "
        "gap = name lagged its sector leader and is predicted to catch up in "
        "the leader's direction (continuation/convergence); low/negative gap "
        "= name overshot and is predicted to fade back. Delta is declared as "
        "a POSITIVE magnitude representing |IC|; the sign is committed in "
        "LAG_PHASE0_PRE_REGISTRATION section 1 and cannot be flipped after a "
        "TRAIN read.\n\n"
        "Defense of magnitude [0.035, 0.045] -- the load-bearing structural "
        "bet. Hou-Moskowitz (2006, RFS -- Market Frictions, Price Delay, and "
        "the Cross-Section of Expected Returns) price delay is one of the "
        "most robust US cross-sectional anomalies at IC ~0.02-0.03, and its "
        "magnitude SCALES WITH MARKET FRICTIONS. India's structurally larger "
        "frictions (retail dominance, thinner mid/small SSF names, "
        "concentrated attention/coverage) predict a larger delay premium "
        "than the US baseline. The pessimistic bound 0.035 sits just above "
        "the US level; the optimistic 0.045 is the India-enlarged upside. "
        "This is literature-defended, not derived from an in-sample read -- "
        "and it is the falsifiable bet: if India's delay is not larger than "
        "the US's, the pessimistic bound is too high and TRAIN will say so."
    ),
    sd_provenance=(
        "Monthly cross-sectional IC dispersion for the same ~120-180 name SSF "
        "cross-section the engine trades. IC dispersion at this breadth is "
        "dominated by true time-variation rather than sampling noise; "
        "equity-factor monthly IC SD sits ~0.10-0.18. LAG uses the identical "
        "substrate, cadence, and cross-section size as Carry/Trend/Flow, so "
        "no defensible reason exists for its SD band to differ. Using the "
        "identical band [0.10, 0.18] ensures the RFA comparison is "
        "apples-to-apples across sleeves (same basis as the Carry/Trend/Flow "
        "declarations)."
    ),
    prior_exposure=(
        "Closest prior-adjacent read: TREND (SSF vol-scaled multi-horizon "
        "TSMOM, TRAIN FAIL p=0.131). Same substrate -- LAG reuses the "
        "continuous series at data/signal_engine/trend/continuous.duckdb "
        "and reads the same forward returns. Trend is own-name "
        "AUTOCORRELATION; LAG is CROSS-autocorrelation conditioned on the "
        "sector leader (the leader's past return residualized against the "
        "name's own). Statistically distinct objects, but disclosed as "
        "prior-adjacent -- m counts this (minimum m >= 2).\n\n"
        "Other priors in the momentum/reversal/diffusion neighborhood: PSB-1 "
        "C1 (weekly unconditional reversal, cash equity, dead on fees -- "
        "different substrate/cadence; no sector-leader conditioning); SFB-1/F1 "
        "(cash-synthesized 12-1 momentum, inconclusive -- single-horizon, "
        "no sector conditioning, <=10-name book); Carry (SSF residual basis, "
        "different economic family -- financing vs diffusion). No "
        "sector-lead / cross-autocorrelation diffusion construct has been "
        "screened on this data. Pre-reg prediction 3 guards against LAG "
        "collapsing into momentum-in-disguise: if LAG-IC residualized "
        "against Trend's signal drops below 60% of raw, same sign, LAG is "
        "not a new sleeve regardless of its standalone number."
    ),
    window=(
        "Sealed projection window 2023-01-01 -> 2026-07-20 (~42 monthly "
        "formations). The futures continuous series spans 2016-02-11 -> "
        "2026-07-20 (futures_bhavcopy, 363 FUTSTK underlyings; roll-adjusted "
        "series reused unchanged from Trend). After 12-month lookback "
        "warmup, first feasible formation is 2017-02. NSE F&O history before "
        "2016 is not obtainable (SFB-1/F1 lockdown finding), so n* cannot be "
        "raised by pulling more calendar. Per the pre-reg section 9 "
        "acceptance rule (Flow/Skew allocation that maximizes the sealed "
        "window): TRAIN is 2017-02 -> 2020-12 (~47 monthly formations) and "
        "HOLDOUT is 2021-01 -> 2022-12 (24 monthly)."
    ),
)
