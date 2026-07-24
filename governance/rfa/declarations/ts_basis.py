# FROZEN 2026-07-23. SHA-256: 07265b507179667588d06cb35c1e98c72bd065a3bbf95cf9a6c7d8b996a1ad84
# sign=+1 (TS_BASIS_PHASE0_PRE_REGISTRATION.md §1). Immutable.
from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="TS_BASIS",
    methodology_version="2.0.0",
    metric="rank_ic",
    test_type="one_sided",
    cadence="monthly",
    n_available=42,
    window=(
        "SEALED projection window 2023-01-01 -> 2026-07-20 (~42 monthly formations). "
        "The futures substrate spans 2016-02-11 -> 2026-07-20. NSE F&O history before "
        "2016 is not obtainable. TRAIN: 2016-03-31 -> 2020-12-31, HOLDOUT: 2021-01 -> "
        "2022-12 per TS_BASIS_PHASE0_PRE_REGISTRATION.md."
    ),
    delta_lo=0.030,
    delta_hi=0.090,
    sd_lo=0.08,
    sd_hi=0.14,
    delta_provenance=(
        "Declared direction: POSITIVE rank-IC (long high z_ts, short low z_ts). "
        "High time-series basis z-score indicates unusually wide futures basis "
        "relative to the name's own history. The cross-sectional carry v2 "
        "established that high basis predicts positive forward returns in this "
        "market; TS Basis measures the same underlying phenomenon but through "
        "a time-series rather than cross-sectional lens. The sign is committed "
        "per TS_BASIS_PHASE0_PRE_REGISTRATION.md §1 and cannot be flipped.\n\n"
        "Defense of magnitude [0.030, 0.090]: cross-sectional carry achieved "
        "+0.041 IC on TRAIN. TS Basis is a different processing of the same "
        "data - it could be higher (cleaner signal without noise from "
        "cross-sectional transformations) or lower (overfit benefit from "
        "seeing the carry TRAIN result). The lower bound 0.030 is the minimum "
        "for an investable signal; the upper bound 0.090 reflects the TRAIN "
        "realization as an optimistic ceiling. The true out-of-sample IC is "
        "expected between 0.030 and 0.050."
    ),
    sd_provenance=(
        "Monthly cross-sectional IC dispersion for a ~120-180 name SSF "
        "cross-section. Cross-sectional carry TRAIN SD_IC was ~0.10; TS Basis "
        "exhibits similar dispersion. The band [0.08, 0.14] reflects the "
        "expectation that dispersion is comparable to cross-sectional carry, "
        "with a slightly lower lower bound because the time-series signal "
        "removes some sources of cross-sectional noise (dividend estimates, "
        "common-financing removal, sector dummies)."
    ),
    prior_exposure=(
        "TRAIN (2016-03 -> 2020-12) has been read for CROSS-SECTIONAL CARRY "
        "sign discovery and is BURNED for that signal. TRAIN was ALSO seen "
        "for the TS Basis sign - the same underlying basis data was used, and "
        "the TRAIN IC +0.089 was observed before this declaration. TRAIN is "
        "therefore BURNED for TS Basis sign discovery as well. "
        "HOLDOUT (2021-2022, 24 formations) is the only clean out-of-sample "
        "window. SEALED (2023-2026, 42 formations) is untouched. "
        "Multiplicity: m >= 2 (cross-sectional carry sign + TS Basis sign, "
        "both discovered on TRAIN). Evidence floor: Bonferroni alpha = 0.025, "
        "one-sided.\n\n"
        "TS_BASIS_PHASE0_PRE_REGISTRATION.md §7 records the full prior-exposure "
        "table."
    ),
)
