# FROZEN 2026-07-23. SHA-256: 4b589e2f2afc6282c3e0400c6d24052e34140f4769130239a59ae150d77df855
# sign=+1 (CARRY_V2_PRE_REGISTRATION.md §1). Immutable.
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
        "Declared direction: POSITIVE rank-IC (long high residual carry, short "
        "low). This is the canonical carry direction per KMPV 2018. The sign is "
        "committed per CARRY_V2_PRE_REGISTRATION.md §1 and cannot be flipped. "
        "v1 (negative sign) was falsified and closed; this is a clean "
        "re-registration with sign=+1, confirmed on HOLDOUT only (TRAIN is "
        "burned for sign discovery).\n\n"
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
        "v1 TRAIN (2016-03 -> 2020-12) has been read and is BURNED for Carry. "
        "v2 confirmation comes from HOLDOUT (2021-22) then SEALED (2023-26). "
        "The TRAIN IC was +0.041 (opposite v1's declared negative sign), "
        "establishing the positive direction discovered-on-TRAIN. HOLDOUT "
        "confirmed the positive sign with IC +0.046 (t=2.60, p=0.016). "
        "Multiplicity m=2 (v1 negative + v2 positive); Bonferroni alpha=0.025. "
        "Operator's non-Carry prior reads are PSB-1/PSB-2/SFB-1 momentum and "
        "delivery constructs — independent of the carry signal."
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
