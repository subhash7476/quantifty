from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="CARRY",
    methodology_version="2.0.0",
    metric="rank_ic",
    test_type="one_sided",
    cadence="monthly",
    n_available=42,
    delta_lo=0.020,
    delta_hi=0.045,
    sd_lo=0.10,
    sd_hi=0.18,
    delta_provenance=(
        "Declared direction: NEGATIVE rank-IC (short high residual carry, long "
        "low). A rich residual basis signals crowded leveraged longs / expensive "
        "borrow, which mean-reverts. Delta is declared as a POSITIVE magnitude "
        "representing |IC|; the sign is committed in CARRY_PHASE0_PRE_REGISTRATION "
        "section 1 and cannot be flipped after a TRAIN read.\n\n"
        "Defense of magnitude [0.020, 0.045]: cross-sectional carry/basis IC in "
        "the equity and futures literature (Koijen-Moskowitz-Pedersen-Vrugt 2018; "
        "Asness-Moskowitz-Pedersen 2013) sits ~0.02-0.05 for a single "
        "well-constructed factor. Residual-basis in Indian single-stock futures "
        "is defended at the same range, upper end reflecting India's stronger "
        "borrow-demand dispersion across the ~180-name SSF universe. The band "
        "is literature-defended, not derived from an in-sample read."
    ),
    sd_provenance=(
        "Monthly cross-sectional IC dispersion for a ~120-180 name SSF "
        "cross-section. IC dispersion at this breadth is dominated by true "
        "time-variation rather than sampling noise; equity-factor monthly IC "
        "SD is ~0.10-0.18 (same basis cited in the Carry pre-reg section 7). "
        "No special tightening is defensible -- the residual basis inherits "
        "the general equity-factor IC dispersion regime."
    ),
    prior_exposure=(
        "Operator's prior reads are momentum/delivery constructs (PSB-1 C1-C5, "
        "PSB-2 C2/C4, SFB-1/F1). NONE is a carry/basis construct -- carry has "
        "not been screened on this data, so prior exposure to THIS signal is "
        "nil. The general finding that monthly cross-sectional equity is "
        "demonstrability-constrained (RFA retrospective, CLAUDE.md) is "
        "methodological, not a peek at carry's realized numbers, and is "
        "already priced into the pre-reg section 7.1."
    ),
    window=(
        "Sealed projection window 2023-01-01 -> 2026-07-20 (~42 monthly "
        "formations). The futures substrate spans 2016-02-11 -> 2026-07-20 "
        "(futures_bhavcopy, 363 FUTSTK underlyings). NSE F&O history before "
        "2016 is not obtainable (SFB-1/F1 lockdown finding), so n* cannot be "
        "raised by pulling more calendar. Per the pre-reg section 9 "
        "acceptance rule, TRAIN is 2016-03-31 -> 2020-12-31 (~58 monthly "
        "formations) and HOLDOUT is 2021-01 -> 2022-12 (24 monthly)."
    ),
)
