# RESEARCH-ONLY — NOT A CANDIDATE. Operator decision, 2026-08-01.
#
# TS Basis Daily has no promotion path. It is not to be frozen, not to be gated,
# and no sealed read is authorized. The 876-formation SEALED window
# (2023-01-01 -> 2026-07-24) is PRESERVED UNSPENT; scripts/signal_engine/
# ts_basis_daily/run_sealed.py refuses to run and must stay that way absent an
# explicit reversal recorded in TS_BASIS_REAUTHORIZATION_ASSESSMENT.md.
#
# This file is retained as the record of what was declared and where it was
# wrong — not as a live candidate declaration. It must NOT be revived by
# editing: a future daily-basis construct starts its own pre-registration,
# declares its own bands, and inherits nothing from here.
#
# NOT FROZEN. No SHA-256 has ever been computed for this file.
# Corrected 2026-08-01: the prior-exposure statement was false (it claimed TRAIN
# and HOLDOUT were unread) and delta_provenance described the monthly construct's
# 504-day calendar lookback rather than this one's 252-row window. See
# docs/reports/TS_BASIS_REAUTHORIZATION_ASSESSMENT.md section C.1.
# The delta/sd bands are UNCHANGED by that correction and are NOT yet defended
# against the selection history now disclosed below — see sd_provenance.
# sign=+1 (time-series basis z-score, long high z_ts, short low z_ts).
# Daily cadence mirror of TS Basis (governance/rfa/declarations/ts_basis.py).
from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="TS_BASIS_DAILY",
    methodology_version="2.0.0",
    metric="rank_ic",
    test_type="one_sided",
    cadence="daily",
    n_available=876,
    window=(
        "SEALED projection window 2023-01-01 -> 2026-07-24: 876 daily formations "
        "carrying a non-null z_ts, counted from ts_signals.duckdb on 2026-08-01. "
        "The end date is 2026-07-24 rather than 2026-07-20 because the construct was "
        "created 2026-07-27 (commit d81859b) and the operator has since observed the "
        "live /ts-basis-daily/ panel; the 5 formations after 2026-07-24 are excluded "
        "as observed. "
        "The futures substrate spans 2016-02-11 -> present. NSE F&O history before "
        "2016 is not obtainable, so this window cannot be extended backwards; it can "
        "only be extended forwards at ~20.8 formations/month. "
        "TRAIN: 2016-03-31 -> 2020-12-31 (1,202 formations), HOLDOUT: 2021-01-01 -> "
        "2022-12-31 (495). Daily formations are every FUTSTK trading day; measured "
        "accrual is 20.4/month and stable (245 / 246 / 248 formations in 2023 / 2024 / "
        "2025).\n\n"
        "WARNING — n_available = 876 IS NOT YET PINNED, BECAUSE IT IS OPTION-DEPENDENT. "
        "876 is the count of the EXISTING sealed window only, which is what a gate run "
        "today would score (central power 0.7472, i.e. 'central fails'). If the operator "
        "adopts Option 1b from TS_BASIS_REAUTHORIZATION_ASSESSMENT.md §B.4 — freeze now, "
        "read once after a pinned forward horizon — then n_available becomes ~1,015 "
        "(876 existing + ~139 forward) and the gate verdict changes. "
        "Whichever option is chosen, n_available is pinned AT FREEZE and never revised "
        "afterwards. Editing this number after seeing a gate verdict would be the "
        "band-adjacent post-hoc move that withdrew O1, even though n_available is not "
        "itself a band."
    ),
    delta_lo=0.005,
    delta_hi=0.020,
    sd_lo=0.12,
    sd_hi=0.20,
    delta_provenance=(
        "Declared direction: POSITIVE rank-IC (long high z_ts, short low z_ts). "
        "z_ts = (basis - trailing_mean) / trailing_std, winsorized to +/-3. "
        "NOTE: the window is NOT the monthly construct's 504-calendar-day lookback. "
        "build_ts_basis_daily.py uses LOOKBACK_ROWS = 252 as a ROW-count window per "
        "underlying (SQL: ROWS BETWEEN 252 PRECEDING AND 1 PRECEDING, ordered by "
        "formation_date, excluding the current row), with MIN_OBS = 12. On daily "
        "formations 252 rows is roughly one trading year, not two. "
        "The TS Basis monthly variant established +0.041 IC on TRAIN (cross-sectional "
        "carry, same underlying basis data). TS Basis monthly SEALED was +0.077 IC. "
        "At daily cadence the per-formation IC is expected to be substantially smaller "
        "because daily forward returns are noisier than monthly. The lower bound 0.005 "
        "reflects a tiny but nonzero daily signal; the upper bound 0.020 reflects an "
        "optimistic scenario where the daily signal retains ~25% of the monthly IC.\n\n"
        "CORRECTION 2026-08-01: an earlier revision of this file claimed the daily "
        "variant had not been read on TRAIN or HOLDOUT. That claim was false when "
        "written and is retained here only as a record of the error. Both windows have "
        "been read repeatedly — see prior_exposure below for the commit-level detail."
    ),
    sd_provenance=(
        "Daily cross-sectional IC dispersion for a ~120-180 name SSF cross-section. "
        "Monthly IC SD for TS Basis was ~0.10-0.14. At daily cadence, IC dispersion is "
        "expected to be higher because daily returns contain more noise. The band "
        "[0.12, 0.20] reflects this expectation: the lower bound is comparable to the "
        "monthly upper bound, and the upper bound allows for substantial daily noise. "
        "This is a defensible structural prior: the signal is identical but the forward "
        "return window is shorter, increasing the noise-to-signal ratio per formation.\n\n"
        "CAVEAT ADDED 2026-08-01 — THIS BAND IS NOT YET DEFENDED. It was written when "
        "the file still asserted TRAIN and HOLDOUT were unread. Now that the selection "
        "history in prior_exposure is disclosed, the band must be re-argued before "
        "freeze, because a band inherited from the monthly variant cannot absorb the "
        "overfitting introduced by five accept/reject decisions taken on HOLDOUT. "
        "The band is left UNCHANGED here deliberately: widening or narrowing it now, "
        "after the power arithmetic below has been seen, would be the same post-hoc "
        "move the RFA contract exists to prevent.\n"
        "Power at the declared band and n=876 (one-sided, α=0.05, scripts/rfa/power.py): "
        "optimistic corner 0.9995, central 0.7472, pessimistic 0.1826. PROCEED would "
        "therefore rest ENTIRELY on the crossed corner (delta_hi paired with sd_lo) — "
        "the exact artifact that withdrew O1 (RFA_GATE_O1_REVIEW.md §1). At the central "
        "assumption 1,015 formations are needed for power 0.80; 876 exist, so the "
        "shortfall is 139 formations ≈ 6.7 months of forward data."
    ),
    prior_exposure=(
        "TRAIN AND HOLDOUT ARE BOTH BURNED FOR THIS CONSTRUCT, AND HOLDOUT IS BURNED "
        "AS A SELECTION SURFACE — NOT MERELY AS A SINGLE READ.\n\n"
        "Substrate exposure: TRAIN (2016-03 -> 2020-12) was read for cross-sectional "
        "carry sign discovery and for monthly TS Basis sign discovery. The same "
        "underlying basis data (futures <-> spot joins from futures_bhavcopy + "
        "equity_bhavcopy) feeds this construct.\n\n"
        "Direct exposure of the DAILY construct, by commit:\n"
        "  80f5e86 (2026-07-28) — failure analysis over TRAIN, 117,809 signals bucketed "
        "by ADV tier, VIX, sector, |z| strength and overnight gap, producing explicit "
        "tuning directives ('raise the |z| threshold', 'higher ADV floor').\n"
        "  48f83bb (2026-07-28) — recovery-state filter (basis_reverting) SELECTED on "
        "TRAIN and PROMOTED after a HOLDOUT acceptance check. HOLDOUT was the accept/"
        "reject surface, not a confirmation.\n"
        "  4521b86 (2026-07-28) — TakeProfitExitPolicy TP@0.5% chosen on TRAIN/HOLDOUT "
        "(+4-5pp net on both).\n"
        "  80f5e86 (2026-07-28) — ML reject model trained across TRAIN/VAL/HOLDOUT. "
        "Discarded as noise, but the windows were consumed.\n"
        "  9c97c98 -> e113f6b — sector cap (max 2/leg) added, evaluated, then reverted.\n\n"
        "Consequence for multiplicity: the earlier 'm >= 1' claim is void. Every "
        "component of the current stack (base z_ts, basis_reverting filter, TP exit, "
        "ranking rule, ADV floor, |z| threshold) was chosen on seen data, and at least "
        "five accept/reject decisions were taken against HOLDOUT. m is materially "
        "greater than 1 and must be enumerated and priced by the operator BEFORE any "
        "freeze. The evidence floor of α = 0.05 one-sided stated below is therefore "
        "NOT yet justified and is carried forward only as a placeholder.\n\n"
        "SEALED (2023-01-01 -> 2026-07-24, 876 daily formations) is UNSPENT. Verified "
        "2026-08-01 by sweeping all 19 daily scripts: run_sealed.py is the only file "
        "referencing any post-2022 date, and it has never been executed to a committed "
        "artifact (no TS_BASIS_DAILY_SEALED_REPORT.md or _SNAPSHOT.json exists on any "
        "branch). Every other daily script hard-stops at 2022-12-31. The 5 formations "
        "after 2026-07-24 are excluded as observed via the live panel.\n\n"
        "Nothing frozen from this point may claim TRAIN or HOLDOUT as out-of-sample "
        "evidence. Only the SEALED window, and forward data not yet in existence, can "
        "serve that role."
    ),
)
