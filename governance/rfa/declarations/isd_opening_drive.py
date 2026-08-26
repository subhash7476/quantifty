# FROZEN declaration isd_opening_drive - rank_ic, one-sided.
# Body SHA-256 (excludes this header): 4ea18ec1ec24176828975251a60428bc8ad487ec6ed2f75e26013b9ac7851871
# Gate report (whole-file digest): docs/reports/ISD-OPEN-DRIVE_RFA.md
from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="ISD-OPEN-DRIVE",
    methodology_version="2.0.0",
    metric="rank_ic",
    test_type="one_sided",
    cadence="daily",
    n_available=317,
    delta_lo=0.020,
    delta_hi=0.035,
    sd_lo=0.15,
    sd_hi=0.25,
    delta_provenance=(
        "Family 1 (opening-drive continuation): daily cross-sectional rank IC of "
        "the 09:15-10:00 opening-period stock return (window-end bar CLOSE - "
        "09:15 auction open)/09:15 open against the SAME-DAY hold-leg return "
        "(entry = next bar open after the window-end close, i.e. 10:01 open, "
        "-> 15:29 close). The label starts AFTER the signal window ends - no "
        "overlap, no look-ahead (the review's R2 pin; pre-registration S4). "
        "Sign is pinned to continuation by mechanism (intraday momentum / "
        "order-flow propagation); the test is one-sided positive. A negative "
        "TRAIN read closes the family - no sign-flip fishing.\n\n"
        "Defense of magnitude [0.020, 0.035]:\n"
        "This is a plausibility envelope anchored on the nearest in-house "
        "out-of-sample cross-sectional read - CB-N50 HOLDOUT IC +0.029 (daily "
        "close-to-close cross-section, 50 Nifty-50 names, reversal + basis "
        "features, 2020-2022). CB-N50's features are NOT this family's features; "
        "no direct prior estimate exists for intraday opening-drive or gap "
        "cross-sectionals. The band asserts plausibility, not precedent "
        "(ISD_PHASE0_CANDIDATE_RANKING_REVIEW R7).\n\n"
        "(a) Academic anchor: intraday momentum (Gao, Han, Li & Zhou 2018, JFE) - "
        "first-half-hour market return predicts last-half-hour return at index "
        "level, robust in their international checks. Index-level intraday "
        "momentum is a modest, robust effect (IC-equivalent ~0.03-0.05 at market "
        "level); single-stock cross-sectional versions are thinner in the "
        "literature - hence the central band sits near the CB-N50 anchor rather "
        "than above it.\n"
        "(b) NSE-specific: the 09:15 pre-open call auction concentrates opening "
        "information into one auction print, sharpening exactly the signal this "
        "family uses; in-house index-pair work found intraday index moves TREND "
        "(+1.10/+1.17 slopes) - the strongest empirical hint in this repo that "
        "NSE intraday flow persists rather than mean-reverts.\n"
        "(c) Counterweight: CB-N50 found daily close-to-close cross-sectional "
        "momentum NEGATIVE (-0.02 IC) - scoped out by horizon (that construct "
        "ran 1-day-lagged close-to-close; this family runs same-day 45-min-window "
        "to 5h-hold). The sign pin therefore rests on mechanism + index analogs, "
        "not on any stock-level in-house read; the one-sided TRAIN gate is the "
        "load-bearing guard.\n\n"
        "Directionally, intraday-derived features carry more information than "
        "EOD features, so the band is more likely conservative than generous - "
        "an argument, not a measurement (review R7)."
    ),
    sd_provenance=(
        "Daily cross-sectional IC dispersion over the ~200-name F&O-eligible "
        "native 1m panel (certified PIT membership, ISD Phase-1 G5). IC "
        "dispersion has two components: true time-variation in signal quality "
        "and sampling noise from ranking a finite cross-section.\n\n"
        "The band [0.15, 0.25] reuses the CB-N50 RFA band. At ~200 names the "
        "cross-section is WIDER than CB-N50's 50 names, which REDUCES the "
        "sampling-noise component of the IC estimator (each daily IC is a rank "
        "correlation over 200 observations, not 50) - so sd_lo = 0.15 is "
        "defensible, arguably conservative. sd_hi = 0.25 keeps the honest "
        "upper bound: daily-frequency return noise and regime variation in "
        "intraday cross-sectional predictability (post-2020 microstructure "
        "shifts) can inflate IC dispersion.\n\n"
        "No TRAIN read has been taken; the SD estimate will be re-measured on "
        "TRAIN (474 formations -> SE(sd) ~ 0.7%) and the pre-registered band is "
        "frozen at this declaration, not revised in response to that estimate "
        "(RFA bands are frozen at approval; the C2 lesson is SD precision off "
        "the same substrate, which the TRAIN window provides)."
    ),
    prior_exposure=(
        "Complete prior-exposure inventory for the ISD program (see "
        "ISD_PHASE0_CANDIDATE_RANKING.md v3):\n\n"
        "1. The native equity 1m store (2023-01-02 -> 2026-08-24, 903 sessions, "
        "~200 names) has been read ONLY by Phase-1 certification (G1-G7: "
        "contiguity, validity, PIT mapping, slippage measurement). NO signal-level "
        "read - no rank IC, no return-prediction statistic - has been taken. "
        "Ops/paper infrastructure (NiftyShield index bars, day-type publisher) "
        "consumed index 1m bars, not equity 1m bars, per spec S4.\n\n"
        "2. CB-N50 (CLOSED): daily close-to-close cross-sectional IC on 50 "
        "Nifty-50 constituents, TRAIN 2016-2019 + HOLDOUT 2020-2022 BOTH burned "
        "(reversal + basis, HOLDOUT IC +0.029; momentum dropped at daily "
        "frequency, IC -0.02). This is the nearest in-house OOS anchor and the "
        "closest conceptual prior (cross-sectional daily predictability); its "
        "feature family differs from this construct.\n\n"
        "3. Index-pair research (COMPLETE): Nifty/BankNifty ratio, EOD 2016-2026 "
        "+ intraday 2023-2026; found intraday ratio TRENDS (momentum-flavored, "
        "no mean reversion). Index-level prior for intraday continuation.\n\n"
        "4. FTMO corpus (external): 0/41 single-instrument intraday pattern cells "
        "significant (ORB, gap-fade, VWAP reversion, vol-spike, drift) on "
        "USTEC/XAUUSD - a high-power null for TIME-SERIES intraday patterns; the "
        "cross-sectional version this program tests was never in that corpus.\n\n"
        "5. PSB-1/2 (CLOSED): monthly/fortnightly EOD delivery-equity "
        "cross-sectionals - died on delivery-equity STT (0.1%/leg) and "
        "demonstrability. Delivery-% is a READ factor (spec S4): this construct "
        "does NOT use it as a covariate (v1 has no conditioning covariates).\n\n"
        "6. CARRY + TS Basis (production / research-only): monthly and daily "
        "cross-sectional carry/basis over ~180 SSF names. TS Basis Daily is "
        "research-only and selection-contaminated; neither overlaps this "
        "feature space (basis vs opening-drive/gap).\n\n"
        "7. The SEALED window 2026-01-01 -> spend date (n >= 317) is genuinely "
        "unread by any strategy research."
    ),
    window=(
        "Fences (frozen in the pre-registration, ISD_PHASE0_PRE_REGISTRATION): "
        "TRAIN 2023-01-02 -> 2024-11-30 (474 daily formations); HOLDOUT "
        "2024-12-01 -> 2025-12-31 (270); SEALED 2026-01-01 -> present, spent "
        "ONLY when n_sealed >= 317 (power floor; central 0.8000, optimistic "
        "0.9937 at the floor - power.py, one-sided) AND the Q5 forward-paper "
        "interval is complete. n_available = 317 = the declared sealed "
        "formation count at spend.\n\n"
        "Substrate: certified native 1m equity store (903 sessions, ~200 "
        "names, PIT membership via G5). The vendor deep archive (2015-2025) is "
        "EXCLUDED by rule (Q1: substrate frozen native-only; unread reserve).\n\n"
        "AC1 disclosure (consistent with CB-N50/CARRY declarations): daily "
        "cross-sectional IC is serially correlated; the harness computes "
        "Newey-West / AC1-corrected t-statistics, and the RFA gate does not "
        "haircut for AC. Margin: at AC1 = 0.3, effective n ~ 317 x 0.54 ~ 171; "
        "corner power (0.035, 0.15, 171) ~ 0.92 - the optimistic corner still "
        "clears the 0.80 hurdle."
    ),
)
