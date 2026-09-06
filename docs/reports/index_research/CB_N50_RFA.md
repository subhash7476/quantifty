# CB-N50 — Research Feasibility Assessment

**VERDICT: PROCEED** — not provably infeasible — this is a floor, not authorization to build.

- Methodology version: `2.0.0`
- Declaration SHA-256: `e37cc68bdc9a51b3`
- Metric: rank_ic | Test: two_sided | Power hurdle: 0.8
- Formations available: 887 (daily, Sealed window 2023-01-01 -> 2026-07-31 (~887 daily formations). The equity bhavcopy substrate spans 2010-01-04 -> 2026-07-31 (equity_bhavcopy.duckdb, 7,030,920 rows). Nifty 50 point-in-time membership via NIFTY-200 universe (CSMP build_universe.py). Futures execution via Nifty futures (NSE FO segment, 2016-02-11 onwards).

Window split: TRAIN 2016-2019 (~1,008 daily formations), HOLDOUT 2020-2022 (~748 daily formations), SEALED 2023-2026 (~887 daily formations). TRAIN is consumed for feature selection and aggregation rule fitting; HOLDOUT for confirmation; SEALED preserved for one-shot read.

CAUTION: Daily IC is serially correlated (signal persistence across adjacent days). The noncentral-t power computation assumes independent observations; autocorrelation inflates the effective n. The actual research MUST use Newey-West or AC1-corrected standard errors (as the PSB-1/PSB-2 harnesses do). The RFA gate does not haircut for AC — this is disclosed and consistent with prior declarations (Carry, FLOW). The high n_available (887) provides margin against the AC haircut; even at AC1=0.3 (effective n ≈ 887×(1-0.3)/(1+0.3) ≈ 477), the optimistic corner still clears (ncp ≈ 5.1, power ≈ 1.00).)

## Optimistic corner

| Quantity | Value |
|---|---|
| delta (high) | 0.035 |
| SD (low) | 0.15 |
| n (raw, no AC haircut) | 887 |
| **Max achievable power** | **1.0000** |

The corner is **intentionally unrealistic.** This independence holds for
`rank_ic` because IC mean and IC dispersion are separately estimable — a
declaration coupling them (e.g. deriving one from the other) is invalid and
the gate's `validate()` will reject it. With independence established,
(delta_hi, sd_lo) describes a large edge with unusually stable outcomes —
the least plausible combination in practice and the most generous to the
construct. This maximizes the burden of proof for ABANDON, so a firing gate
is unarguable, while correspondingly weakening PROCEED to its stated meaning
of *not provably infeasible*.

## Formations required for power 0.80

| Band point | n required |
|---|---|
| Optimistic corner | 147 |
| Central | 623 |
| Pessimistic | 4908 |
| **Available** | **887** |

## Declared bands and provenance

**delta: [0.01, 0.035]**

Declared direction: TWO-SIDED (detecting both positive and negative cross-sectional rank IC). The aggregate breadth rule maps stock-level IC to a signed index position via a pre-registered threshold, but the underlying hypothesis is that stock-level signals predict the cross-section of next-day returns — the IC can be positive, negative, or null depending on the feature.

Defense of magnitude [0.010, 0.035]:
This is a daily cross-sectional rank IC for a combined signal over Nifty 50 constituents. The band reflects three features (relative momentum, futures basis, volatility) whose individual daily ICs are small (0.003-0.015 each) but whose combination should achieve higher aggregate IC via orthogonal information sources.

(a) Cross-sectional equity momentum at DAILY frequency is weaker than monthly because daily returns are dominated by microstructure noise. Jegadeesh-Titman (1993) reports monthly IC ~0.02-0.05; daily momentum IC is ~0.005-0.015 for a 50-stock cross-section.
(b) Futures basis/carry at daily frequency: the residual basis signal that powers the carry sleeve (monthly IC ~0.04 across 180 SSF names) becomes weaker at daily horizon because the basis changes slowly and daily return noise dominates. Daily carry IC over 50 stocks is ~0.005-0.010.
(c) Volatility/reversal: short-term reversal at daily frequency has IC ~0.003-0.010 (Jegadeesh 1990; daily reversal is weaker than weekly because of bid-ask bounce).

The COMBINED signal benefits from the (approximate) orthogonality of these features (momentum = continuation, reversal = mean-reversion, carry = structural). The upper bound 0.035 reflects an optimistic but defensible combination where each feature adds independent information — plausible under the assumption that the correlation between daily IC streams of momentum, carry, and vol features is low (<0.2). The lower bound 0.010 reflects a pessimistic case where only one feature carries signal and the others add noise.

These are literature-defended bands; no TRAIN read has been taken on Nifty 50 constituent daily IC.

**SD: [0.15, 0.25]**

Daily cross-sectional IC dispersion for a 50-stock panel. IC dispersion has two components: (a) true time-variation in signal quality, and (b) sampling noise from ranking a finite cross-section.

For the monthly 180-name F&O panel, IC SD is ~0.10-0.18 (Carry declaration). Switching to a 50-stock panel narrows the cross-section, increasing sampling noise: each IC observation is the rank correlation across 50 stocks, and the smaller N increases the sampling variance of the rank correlation estimator. At daily frequency, return noise further inflates IC dispersion because daily stock returns have higher idiosyncratic variance relative to the signal.

The band [0.15, 0.25] is wider than the monthly 180-name band [0.10, 0.18] to reflect both effects: narrower cross-section (50 vs 180) and higher-frequency sampling (daily vs monthly). The lower bound 0.15 is the same as the monthly sd_lo — the optimistic case where the combined signal's daily IC is unusually stable. The upper bound 0.25 acknowledges that daily IC for 50 stocks is inherently noisier.

**Prior exposure**

The operator has conducted and recorded the following prior reads on the same or overlapping data:

1. NIFTY_BANKNIFTY_PAIR_RESEARCH: Read the full Nifty/BankNifty 1d ratio data (2016-2026, 2,620 obs) for mean-reversion testing. This exposure is to INDEX-LEVEL ratio behaviour, NOT to constituent-level cross-sectional ranking. The pair research never ranked individual stocks or computed cross-sectional ICs.

2. PSB-1 & PSB-2: Measured equity cross-sectional ICs at MONTHLY frequency on the full NIFTY-200 panel (7M+ rows). Read delivery-%, reversal, and momentum ICs at monthly horizon. These are prior exposures to the general concept of equity cross-sectional predictability but at a different frequency (monthly vs daily), on a different panel (200 vs 50), and for different signals (delivery anomaly vs combined momentum/carry/vol). The finding that monthly equity momentum requires ~29 years to demonstrate is methodological, not a peek at daily Nifty 50 ICs.

3. SFB-1/F1: Stock-futures momentum at monthly horizon with bracketed exits. Exposed to the general difficulty of demonstrating equity momentum. Not a read on daily Nifty 50 constituent IC.

4. Carry sleeve: Validated cross-sectional carry/basis IC on ~180 SSF names at MONTHLY horizon. The carry signal construction (residual basis) is a feature candidate for this construct, but at a different frequency and on a different universe. The Carry TRAIN read was on the FULL SSF panel, not just Nifty 50 constituents.

The operator has NOT measured: (a) daily cross-sectional IC on Nifty 50 constituents; (b) combined multi-feature IC; (c) the mapping from stock-level IC to index futures P&L.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
