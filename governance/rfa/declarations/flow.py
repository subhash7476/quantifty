from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="FLOW",
    methodology_version="2.0.0",
    metric="rank_ic",
    test_type="one_sided",
    cadence="monthly",
    n_available=42,
    delta_lo=0.015,
    delta_hi=0.030,
    sd_lo=0.10,
    sd_hi=0.18,
    delta_provenance=(
        "Declared direction: NEGATIVE rank-IC (crowding reversal). Names with "
        "high accumulated positioning pressure (long buildup or short buildup "
        "accumulated over a lookback) are crowded and predicted to underperform; "
        "the tradeable signal is SHORT high pressure, LONG low pressure. Delta "
        "is declared as a POSITIVE magnitude representing |IC|; the sign is "
        "committed here and cannot be flipped after a TRAIN read.\n\n"
        "Defense of magnitude [0.015, 0.030], argued on positioning/crowding "
        "literature NOT informed-flow. Per-name futures OI dynamics (signed "
        "dOI against dP) identify positioning regime per name -- long buildup, "
        "short buildup, long unwinding, short covering. Accumulated pressure "
        "in one direction signals crowding, which mean-reverts as late "
        "entrants are forced to unwind (Stein 2009, 'Presidential Address: "
        "Spotting Bubbles'; cross-sectional reversal Jegadeesh 1990, Lehmann "
        "1990). Monthly cross-sectional reversal IC is typically 0.01-0.03 -- "
        "lower than weekly reversal because mean-reversion decays with "
        "horizon.\n\n"
        "Why this band sits below Carry's [0.020, 0.045]: (1) the original "
        "Flow economics ('informed positioning') rested on participant "
        "attribution (FII/DII/Client/Pro), which NSE does not publish "
        "per-name -- the replacement carries NO attribution and cannot "
        "distinguish informed from uninformed flow; (2) dOI-vs-dP positioning "
        "is one of the most heavily-mined retail heuristics in the Indian "
        "market, competing the residual edge toward the lower end; (3) "
        "monthly-horizon reversal is structurally weaker than the weekly "
        "effects that dominate the reversal literature. The band reflects a "
        "crowding/reversal signal without attribution -- not the informed-flow "
        "construct the 4-sleeve 0.86 projection was originally written against."
    ),
    sd_provenance=(
        "Monthly cross-sectional IC dispersion for the same ~120-180 name SSF "
        "cross-section the engine trades. IC dispersion at this breadth is "
        "dominated by true time-variation rather than sampling noise; equity-"
        "factor monthly IC SD sits ~0.10-0.18 (same basis as the Carry "
        "declaration). Positioning signals may exhibit slightly higher "
        "dispersion than carry because positioning regime shifts are episodic "
        "and cluster in bursts, but the band already encompasses that -- no "
        "special tightening is defensible, and inflating sd_hi to cover "
        "additional noise would be the crossed-corner the contract forbids."
    ),
    prior_exposure=(
        "The original Flow sleeve was specced as 'informed positioning' based "
        "on participant-wise OI (FII/DII/Client/Pro). That framing is WITHDRAWN "
        "-- SIGNAL_ENGINE_DESIGN.md section 2.2 documents that the NSE "
        "participant-OI file (fao_participant_oi_*.csv) contains exactly four "
        "aggregate rows with no per-underlying breakdown, so participant "
        "attribution is not available and the informed-flow economics do NOT "
        "transfer to the replacement. The replacement (per-name aggregate OI "
        "from futures_bhavcopy.open_int / chg_in_oi) has NOT been screened on "
        "this data -- no TRAIN read has been taken, no IC measured.\n\n"
        "Operator's prior reads are momentum/delivery constructs (PSB-1 C1-C5, "
        "PSB-2 C2/C4, SFB-1/F1). None is a futures-OI positioning construct, "
        "so prior exposure to THIS signal is nil. The general demonstrability "
        "finding (RFA retrospective, CLAUDE.md) is methodological, not a peek "
        "at OI positioning's realized numbers."
    ),
    window=(
        "Sealed projection window 2023-01-01 -> 2026-07-20 (~42 monthly "
        "formations). The futures substrate spans 2016-02-11 -> 2026-07-20 "
        "(futures_bhavcopy, 363 FUTSTK underlyings). NSE F&O history before "
        "2016 is not obtainable (SFB-1/F1 lockdown finding), so n* cannot be "
        "raised by pulling more calendar. Per-name open_int and chg_in_oi are "
        "100% populated across 1,422,979 FUTSTK rows in the substrate -- no "
        "ingest blocker (SIGNAL_ENGINE_DESIGN.md section 2.1)."
    ),
)
