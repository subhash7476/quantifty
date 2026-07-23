"""TS Basis — RFA power pre-check declaration.

Effect-size bands declared BEFORE any HOLDOUT read. Metric = rank_ic
per RFA contract v2 (independent delta/SD bands defensible for IC).

Lookback: 504d. Min obs: 12. Winsorize: +/-3σ.
"""
DECLARATION_ID = "ts_basis"
METRIC = "rank_ic"
METHODOLOGY_VERSION = "2.0.0"

# Declared bands (frozen at approval):
#   delta = mean rank-IC band
#   sd = IC standard deviation band
#   n_star = formations available at target horizon
DELTA_BAND = [0.030, 0.090]     # optimistic → central → pessimistic
SD_BAND = [0.08, 0.14]           # Lower SD = narrower IC dispersion
N_STAR = 42                      # monthly formations in SEALED window
N_HOLDOUT = 24                   # monthly formations in HOLDOUT window

# Defended rationale:
# - delta lower bound 0.030: cross-sectional carry achieved +0.041 on TRAIN.
#   TS basis is a different processing of the same underlying data; IC could
#   be lower on out-of-sample. 0.030 is the minimum for a useful signal.
# - delta upper bound 0.090: the TRAIN IC +0.089 was seen on the same data
#   used for carry sign discovery. This is an optimistic estimate inflated
#   by prior exposure; genuine OOS IC likely between 0.030 and 0.050.
# - sd lower bound 0.08: cross-sectional carry TRAIN SD_IC was ~0.10.
#   TS basis observed TRAIN SD_IC 0.105. Similar dispersion expected.
# - sd upper bound 0.14: conservative. HOLDOUT at 24 formations may show
#   wider dispersion than TRAIN at 47.
# - n_star 42: 2023-01 --> 2026-07 spans ~42 monthly formations.

# Cadence invariance (RFA v2): ncp = S·sqrt(T), cadence cancels.
# Higher cadence buys no statistical power. Monthly is correct.
