# FROZEN — TS Basis Daily RFA declaration.
# SHA-256 will be computed after freeze.
# sign=+1 (time-series basis z-score, long high z_ts, short low z_ts).
# Daily cadence mirror of TS Basis (governance/rfa/declarations/ts_basis.py).
from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="TS_BASIS_DAILY",
    methodology_version="2.0.0",
    metric="rank_ic",
    test_type="one_sided",
    cadence="daily",
    n_available=850,
    window=(
        "SEALED projection window 2023-01-01 -> 2026-07-20 (~850 daily formations). "
        "The futures substrate spans 2016-02-11 -> 2026-07-20. NSE F&O history before "
        "2016 is not obtainable. TRAIN: 2016-03-31 -> 2020-12-31, HOLDOUT: 2021-01 -> "
        "2022-12. Daily formations are every FUTSTK trading day."
    ),
    delta_lo=0.005,
    delta_hi=0.020,
    sd_lo=0.12,
    sd_hi=0.20,
    delta_provenance=(
        "Declared direction: POSITIVE rank-IC (long high z_ts, short low z_ts). "
        "Same signal construction as TS Basis (monthly): z_ts = (basis - trailing_mean) "
        "/ trailing_std with 504-day calendar lookback and 12-observation minimum. "
        "The TS Basis monthly variant established +0.041 IC on TRAIN (cross-sectional "
        "carry, same underlying basis data). TS Basis monthly SEALED was +0.077 IC. "
        "At daily cadence the per-formation IC is expected to be substantially smaller "
        "because daily forward returns are noisier than monthly. The lower bound 0.005 "
        "reflects a tiny but nonzero daily signal; the upper bound 0.020 reflects an "
        "optimistic scenario where the daily signal retains ~25% of the monthly IC.\n\n"
        "The daily TS Basis has NOT been read on TRAIN or HOLDOUT. The monthly TS Basis "
        "TRAIN was burned for the monthly variant's sign discovery — this daily variant "
        "is a new construct and its TRAIN window is unread."
    ),
    sd_provenance=(
        "Daily cross-sectional IC dispersion for a ~120-180 name SSF cross-section. "
        "Monthly IC SD for TS Basis was ~0.10-0.14. At daily cadence, IC dispersion is "
        "expected to be higher because daily returns contain more noise. The band "
        "[0.12, 0.20] reflects this expectation: the lower bound is comparable to the "
        "monthly upper bound, and the upper bound allows for substantial daily noise. "
        "This is a defensible structural prior: the signal is identical but the forward "
        "return window is shorter, increasing the noise-to-signal ratio per formation."
    ),
    prior_exposure=(
        "TRAIN (2016-03 -> 2020-12) has been read for cross-sectional carry sign "
        "discovery and for monthly TS Basis sign discovery — both are BURNED for their "
        "respective constructs. The daily TS Basis has NOT been read on TRAIN. "
        "However, the same underlying basis data (futures ↔ spot joins from "
        "futures_bhavcopy + equity_bhavcopy) was used in both prior reads, so there "
        "is structural prior exposure on the substrate. The daily TS Basis TRAIN "
        "window is therefore partially burned (data seen, signal not seen). "
        "HOLDOUT (2021-2022) is unread for the daily variant. "
        "SEALED (2023-2026, ~850 daily formations) is untouched for all daily constructs. "
        "Multiplicity: m >= 1 (daily TS Basis is the first daily-basis construct; "
        "monthly TS Basis is a different cadence/family and does not count toward m). "
        "Evidence floor: α = 0.05, one-sided."
    ),
)
