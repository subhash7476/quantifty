# DRAFT declaration stock_straddle_m10 - per_trade_pnl, one-sided. NOT FROZEN.
# It freezes on operator approval (SHA-256 over this whole file, recorded in the
# gate report); until then it may be corrected, after that never.
# Gate report (whole-file digest): docs/reports/STOCK-STRADDLE-M10_RFA.md
from governance.rfa.declaration import Declaration

DECLARATION = Declaration(
    name="STOCK-STRADDLE-M10",
    methodology_version="2.0.0",
    metric="per_trade_pnl",
    test_type="one_sided",
    cadence="monthly (one equal-weight book of short ATM single-stock straddles "
            "per monthly expiry: entry at the close 10 sessions before expiry, "
            "exit at the T-1 close)",
    cadence_per_year=12,
    n_available=36,
    sharpe_lo=0.65,
    sharpe_hi=1.51,
    sharpe_provenance=(
        "Declared direction: POSITIVE - the short straddle earns the single-stock "
        "variance risk premium over the last ~9 sessions of the monthly cycle "
        "(OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md). One trade = one expiry "
        "cycle; its P&L is the equal-weight mean across names of the net seller "
        "return on premium (study fee model, 2% round-trip spread), so names "
        "within a cycle are never counted as independent trades.\n\n"
        "The band is NET annualized Sharpe at cadence 12. Every anchor below is "
        "reproducible from committed code (W6: "
        "scripts/research/options_seller_edge/ca_filter_split.py, crash cycles "
        "RESTORED - the outcome filter the 2026-09-24 audit flagged is removed):\n"
        "- OPTIMISTIC 1.51: the confirmation window 2023-01 -> 2026-08 "
        "(43 cycles, mean +8.07% of premium, t 2.85). It is the only genuinely "
        "out-of-sample read of this construct, and it is generous for a forward "
        "window because it is dominated by pre-reform cycles. The discovery "
        "window (2016-22) gave 1.73 and is not used: it chose the entry offset.\n"
        "- PESSIMISTIC 0.65: the post-reform (2024-11-20 ->) Sharpe under the "
        "audit's seller-hostile conservative exit (STOCK_STRADDLE_SELLING_"
        "EVIDENCE_AUDIT_2026-09-24.md s8, 'reproducible'). The same sub-window "
        "at the observed exit gives 1.02 (21 cycles). The pessimistic corner "
        "is the weakest claim consistent with the edge surviving the Nov-2024 "
        "F&O reform at all.\n"
        "- CENTRAL 1.08 (midpoint) sits at the observed post-reform 1.02.\n\n"
        "Stated threats to the band (why the optimistic corner is not a "
        "prediction):\n"
        "1. Regime. The forward window is entirely post-reform, where the "
        "observed Sharpe is ~1.0 on 21 cycles (t 1.35, not significant). The "
        "optimistic corner assumes the pre-reform edge returns.\n"
        "2. Shrinkage. Out-of-sample slopes run 0.44-0.80 of in-sample "
        "(Lewellen 2015 [summary]); the confirmation read is already OOS, but a "
        "further forward haircut is the base rate.\n"
        "3. Distribution. Per-cycle returns are negatively skewed (confirmation "
        "skew -1.19) and the book is short crash risk (W6 kinked beta: "
        "beta_down +0.55, se 0.08). Noncentral-t power assumes near-normal "
        "P&L; a short-gamma book's Sharpe overstates what a t-test can "
        "confirm (Brooks-Kat 2001).\n"
        "4. Costs. The 2% spread is a single-day measurement (audit s7.2); "
        "T-10 and T-1 spreads are unmeasured, and the fee model misses the "
        "0.15% options STT from 2026-04.\n\n"
        "PROCEED means 'not provably infeasible' - a floor, never authorization, "
        "and never a statement about the true effect size."
    ),
    prior_exposure=(
        "Every historical window of this construct has been read; there is NO "
        "unread history.\n"
        "(a) Discovery 2016-01 -> 2022-12: the entry offset (10 sessions before "
        "expiry) was selected here among six offsets (study s2.1).\n"
        "(b) Confirmation 2023-01 -> 2026-08-24: predictions written first "
        "(transcript-verified, audit s3), then read once -> SPENT. Liquidity "
        "cuts, the conservative exit and the >=100-contract screen were chosen "
        "after it was read (audit s4) and are descriptive only.\n"
        "(c) Post-reform sub-window 2024-11-20 -> 2026-08: spent with (b).\n"
        "(d) W6 (2026-09-27) re-read (a)-(c) for filter accounting only; it "
        "chose nothing.\n"
        "(e) The same 2023+ stock-option data underlies the Options-Wall and "
        "seller-edge index checks (index selling showed nothing).\n"
        "Consequence: confirmation can only be FORWARD, which is why "
        "n_available below counts future cycles."
    ),
    window=(
        "Forward window only: 36 monthly cycles, the first being the 2026-10-27 "
        "expiry (entry 2026-10-12 close, 10 sessions before expiry) if the "
        "pre-registration is frozen before 2026-10-12, through the Sep-2029 "
        "expiry. 36 is the shortest round horizon (3 years) and is chosen "
        "because the gate is hardest there; the report's n_required figures "
        "give the horizon at every corner.\n"
        "Instrument: NSE single-stock options, monthly expiry, ATM strike off "
        "the same-expiry future, both legs traded at entry; exit at T-1 close "
        "(physical settlement avoided). Forward fills must be at live bid/ask "
        "(the Sep-29 paper cycle was never run because no stock-option quotes "
        "were captured at entry - audit s5); capturing entry and exit quotes is "
        "a precondition the pre-registration must pin, not this RFA.\n"
        "Cadence note: at cadence 12, ncp = S*sqrt(T), so no cadence change can "
        "shorten the horizon."
    ),
)
