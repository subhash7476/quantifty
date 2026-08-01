# FROZEN 2026-08-01. SHA-256: 67e3854b7805eea9b77c93c4b996f4eb9ddfca2ec91d224d76aff7d3bcc2b344
# ABANDONED by RFA gate — max power 0.337 < 0.80 hurdle.
from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="RS-MOM",
    methodology_version="2.0.0",
    metric="per_trade_pnl",
    test_type="one_sided",
    cadence="weekly",
    cadence_per_year=52,
    n_available=186,
    sharpe_lo=0.25,
    sharpe_hi=0.65,
    sharpe_provenance=(
        "Declared direction: POSITIVE (long the relatively stronger index, short "
        "the weaker). The intraday pair-research finding (ratio TRENDS, does not "
        "revert — mean-reversion-up slope +1.10, down slope +1.17) motivates a "
        "momentum rather than mean-reversion formulation.\n\n"
        "Defense of magnitude [0.25, 0.65]:\n"
        "Time-series momentum on single assets (Moskowitz-Ooi-Pedersen 2012) "
        "reports Sharpe ~0.5-0.7 for equity indices; Asness-Moskowitz-Pedersen "
        "(2013) reports similar for a diversified TS-MOM portfolio. A TWO-ASSET "
        "spread (long one index, short the other) is a zero-beta, "
        "dollar-neutral portfolio that removes the common equity risk premium "
        "— leaving only the relative-strength signal. This structurally reduces "
        "volatility (two correlated legs partially cancel) but also removes the "
        "unconditional equity risk premium that inflates long-only TS-MOM Sharpe.\n"
        "The band [0.25, 0.65] acknowledges: (a) the lower bound represents the "
        "case where relative-strength is a weak but positive effect at ~0.25 "
        "Sharpe — still above zero, but a 'follow the flow' rather than a "
        "strong predictor; (b) the upper bound at 0.65 represents the case "
        "where the index-pair isolates a genuine lead-lag or sector-rotation "
        "premium — comparable to but slightly below single-asset TS-MOM Sharpe "
        "because the two-index universe offers no diversification across time "
        "series.\n"
        "These are literature-defended bands, not derived from an in-sample "
        "read. No TRAIN data has been consumed for RS-MOM."
    ),
    prior_exposure=(
        "The operator conducted a mean-reversion pair-research screen on the "
        "same Nifty/BankNifty 1d data (2016-2026, 2,620 obs). That screen "
        "exhaustively tested ratio z-score mean reversion and returned NO "
        "OPPORTUNITY (NIFTY_BANKNIFTY_PAIR_RESEARCH.md). The screen read the "
        "full data set, so the operator HAS SEEN the ratio trajectory and its "
        "descriptive statistics.\n\n"
        "However, the screen tested ONLY mean-reversion (fade the spread) — it "
        "never tested momentum (follow the spread). The observed trends "
        "(intraday slope +1.10, daily continuation) are descriptive statistics "
        "of price behaviour, not a formal momentum read. The operator has NOT "
        "measured a momentum signal's IC, Sharpe, or net spread on this data.\n\n"
        "Prior exposure to momentum as an asset-pricing factor comes from "
        "PSB-1/PSB-2 (equity cross-sectional momentum at monthly horizon) and "
        "SFB-1/F1 (stock-futures momentum). None of these involved a two-index "
        "relative-strength construct at weekly horizon. The general finding "
        "that cross-sectional equity momentum requires ~29 years to demonstrate "
        "is methodological, not a read on the Nifty-BankNifty spread."
    ),
    window=(
        "Sealed projection window 2023-01-01 -> 2026-07-31 (~186 weekly "
        "formations, ~3.58 years). The index 1d substrate spans 2016-01-01 -> "
        "2026-07-31 (2,620 daily observations); futures substrate spans "
        "2016-02-11 -> 2026-07-20. NSE F&O history before 2016 is not "
        "obtainable (SFB-1/F1 lockdown finding), so the total calendar is "
        "fixed. Within that: TRAIN 2016-2019 (208 weeks), HOLDOUT 2020-2022 "
        "(156 weeks), SEALED 2023-2026 (186 weeks).\n\n"
        "Note: if the two-index construct is limited to per_trade_pnl metric, "
        "the sealed window may be too short to achieve RFA power 0.80 under "
        "any defensible Sharpe band. The gate is designed to catch this."
    ),
)
