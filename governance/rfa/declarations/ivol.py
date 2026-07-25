from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="IVOL",
    methodology_version="2.0.0",
    metric="rank_ic",
    test_type="one_sided",
    cadence="monthly",
    n_available=42,
    delta_lo=0.040,
    delta_hi=0.060,
    sd_lo=0.10,
    sd_hi=0.18,
    delta_provenance=(
        "Declared direction: NEGATIVE rank-IC (long low-vol, short high-vol). "
        "High idiosyncratic volatility predicts LOW forward returns -- the "
        "high-IVOL-underperforms anomaly (Ang-Hodrick-Xing-Zhang 2006/2009; "
        "Frazzini-Pedersen 2014, Betting Against Beta). Delta is declared as a "
        "POSITIVE magnitude representing |IC|; the sign (negative) is committed "
        "in IVOL_PHASE0_PRE_REGISTRATION section 1 and cannot be flipped after "
        "a TRAIN read.\n\n"
        "Defense of magnitude [0.040, 0.060]: the BAB / high-IVOL anomaly is "
        "among the strongest documented cross-sectionally -- Ang et al. and "
        "Frazzini-Pedersen (t>5) report IC ~0.04-0.06. PSB-1 C5 (cash-equity "
        "low-vol, monthly banded) realized +0.068 on Indian data -- the "
        "highest IC of any candidate this repository has run -- clearing "
        "significance (t=3.14, p=0.001), sign, and net spread (+4.3%), and "
        "dying only on composite power projection (0.54). The pessimistic "
        "bound 0.040 is the literature floor; the optimistic 0.060 sits just "
        "under C5's realized 0.068, leaving room for the India-retail-"
        "amplification upside (lottery preference is the documented driver of "
        "low-vol, and India has among the highest retail participation "
        "globally) without overclaiming. Literature + C5 defended, not "
        "derived from an in-sample futures read."
    ),
    sd_provenance=(
        "Monthly cross-sectional IC dispersion for the same ~120-180 name SSF "
        "cross-section the engine trades. IC dispersion at this breadth is "
        "dominated by true time-variation rather than sampling noise; "
        "equity-factor monthly IC SD sits ~0.10-0.18. IVOL uses the identical "
        "substrate, cadence, and cross-section size as Carry/Trend/Flow/LAG, "
        "so the identical band [0.10, 0.18] keeps the RFA comparison "
        "apples-to-apples. Counterevidence disclosed: PSB-1 C5 (cash equity) "
        "realized higher dispersion (the reason its composite power was only "
        "0.54) -- the bet is that the futures substrate (liquid, filtered, "
        "beta-neutralized) has lower dispersion than cash. The gate-2 SD band "
        "check is the honest arbiter: realized SD > 0.18 fires the C2 "
        "wide-SD stop and halts the sleeve."
    ),
    prior_exposure=(
        "Closest prior read: PSB-1 C5 (cash-equity low-vol, monthly banded). "
        "C5 produced mean IC +0.068 (t=3.14, p=0.001), net +4.3% at 14 bp/yr "
        "drag -- it cleared significance + sign + net and died only on "
        "composite power (0.54). IVOL differs in substrate (futures vs cash), "
        "universe (SSF-liquid), fee structure, and explicit beta-neutralization "
        "(residual vol, the BAB construct). Disclosed as prior-adjacent; m "
        "counts this. With TREND (dead, own-name momentum) and LAG (dead, "
        "sector-leader diffusion) also in the vol/momentum neighborhood, the "
        "honest minimum is m >= 3 for the family-wise penalty. Carry "
        "(survived, residual basis) is a different economic family; "
        "correlation measured on TRAIN."
    ),
    window=(
        "Sealed projection window 2023-01-01 -> 2026-07-20 (~42 monthly "
        "formations). The futures continuous series spans 2016-02-11 -> "
        "2026-07-20 (futures_bhavcopy, 363 FUTSTK underlyings; roll-adjusted "
        "series reused unchanged from Trend, fourth use). After 252-day beta "
        "warmup, first feasible formation is 2017-02. NSE F&O history before "
        "2016 is not obtainable (SFB-1/F1 lockdown finding), so n* cannot be "
        "raised by pulling more calendar. Per the pre-reg section 9 "
        "acceptance rule (Flow/Skew/LAG allocation that maximizes the sealed "
        "window): TRAIN is 2017-02 -> 2020-12 (~47 monthly formations) and "
        "HOLDOUT is 2021-01 -> 2022-12 (24 monthly)."
    ),
)
