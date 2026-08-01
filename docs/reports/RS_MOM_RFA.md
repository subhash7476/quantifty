# RS-MOM — Research Feasibility Assessment

**VERDICT: ABANDON** — The construct cannot be demonstrated at the declared bands. Do not build it.

- Methodology version: `2.0.0`
- Declaration SHA-256: `0e0085d2ed56bfb4`
- Metric: per_trade_pnl | Test: one_sided | Power hurdle: 0.8
- Formations available: 186 (weekly, Sealed projection window 2023-01-01 -> 2026-07-31 (~186 weekly formations, ~3.58 years). The index 1d substrate spans 2016-01-01 -> 2026-07-31 (2,620 daily observations); futures substrate spans 2016-02-11 -> 2026-07-20. NSE F&O history before 2016 is not obtainable (SFB-1/F1 lockdown finding), so the total calendar is fixed. Within that: TRAIN 2016-2019 (208 weeks), HOLDOUT 2020-2022 (156 weeks), SEALED 2023-2026 (186 weeks).

Note: if the two-index construct is limited to per_trade_pnl metric, the sealed window may be too short to achieve RFA power 0.80 under any defensible Sharpe band. The gate is designed to catch this.)

## Optimistic corner

| Quantity | Value |
|---|---|
| Annualized Sharpe (high) | 0.65 |
| Cadence per year | 52 |
| Per-formation Sharpe | 0.090139 |
| Elapsed time T = n/c | 3.5769 years |
| n (raw, no AC haircut) | 186 |
| **Max achievable power** | **0.3372** |

**There is no crossed corner for `per_trade_pnl`.** The noncentrality
parameter reduces to `ncp = (S/√c)·√(c·T) = S·√T`, so cadence cancels and
power depends only on annualized Sharpe and elapsed time. Declaring separate
`delta` and `sd` bands for a PnL metric would re-introduce a redundant degree
of freedom the gate does not inspect (the O1 defect, `RFA_GATE_O1_REVIEW.md`
§1); the contract forbids it. SD is *not* a free parameter here — it is
fully determined once Sharpe and the per-formation mean are pinned.

## Formations required for power 0.80

| Band point | Annualized Sharpe | n required |
|---|---|---|
| Optimistic corner | 0.65 | 763 |
| Central | 0.45 | 1589 |
| Pessimistic | 0.25 | 5146 |
| **Available** | — | **186** |

Equivalently (because cadence cancels): power 0.80 is reachable **iff** the
true annualized Sharpe clears the threshold implied by T alone. A longer time
window helps; a higher cadence does not.

## Declared Sharpe band and provenance

**Annualized Sharpe: [0.25, 0.65]** at cadence
52 formations/year.

Declared direction: POSITIVE (long the relatively stronger index, short the weaker). The intraday pair-research finding (ratio TRENDS, does not revert — mean-reversion-up slope +1.10, down slope +1.17) motivates a momentum rather than mean-reversion formulation.

Defense of magnitude [0.25, 0.65]:
Time-series momentum on single assets (Moskowitz-Ooi-Pedersen 2012) reports Sharpe ~0.5-0.7 for equity indices; Asness-Moskowitz-Pedersen (2013) reports similar for a diversified TS-MOM portfolio. A TWO-ASSET spread (long one index, short the other) is a zero-beta, dollar-neutral portfolio that removes the common equity risk premium — leaving only the relative-strength signal. This structurally reduces volatility (two correlated legs partially cancel) but also removes the unconditional equity risk premium that inflates long-only TS-MOM Sharpe.
The band [0.25, 0.65] acknowledges: (a) the lower bound represents the case where relative-strength is a weak but positive effect at ~0.25 Sharpe — still above zero, but a 'follow the flow' rather than a strong predictor; (b) the upper bound at 0.65 represents the case where the index-pair isolates a genuine lead-lag or sector-rotation premium — comparable to but slightly below single-asset TS-MOM Sharpe because the two-index universe offers no diversification across time series.
These are literature-defended bands, not derived from an in-sample read. No TRAIN data has been consumed for RS-MOM.

**Prior exposure**

The operator conducted a mean-reversion pair-research screen on the same Nifty/BankNifty 1d data (2016-2026, 2,620 obs). That screen exhaustively tested ratio z-score mean reversion and returned NO OPPORTUNITY (NIFTY_BANKNIFTY_PAIR_RESEARCH.md). The screen read the full data set, so the operator HAS SEEN the ratio trajectory and its descriptive statistics.

However, the screen tested ONLY mean-reversion (fade the spread) — it never tested momentum (follow the spread). The observed trends (intraday slope +1.10, daily continuation) are descriptive statistics of price behaviour, not a formal momentum read. The operator has NOT measured a momentum signal's IC, Sharpe, or net spread on this data.

Prior exposure to momentum as an asset-pricing factor comes from PSB-1/PSB-2 (equity cross-sectional momentum at monthly horizon) and SFB-1/F1 (stock-futures momentum). None of these involved a two-index relative-strength construct at weekly horizon. The general finding that cross-sectional equity momentum requires ~29 years to demonstrate is methodological, not a read on the Nifty-BankNifty spread.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
