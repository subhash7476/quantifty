# GEX-XS-5D — Research Feasibility Assessment

**VERDICT: PROCEED** — not provably infeasible — this is a floor, not authorization to build.

- Methodology version: `2.0.0`
- Declaration SHA-256: `b9e33df2d4825ed1e94c961caef4e7bb22541f4318fdcb16ab8841d9796da700`
- Metric: rank_ic | Test: one_sided | Power hurdle: 0.8
- Formations available: 184 (every 5th session, non-overlapping (one cross-sectional Spearman IC per formation over single-stock F&O names: normalized net GEX at the formation close vs the residualized ln(RV_{t+1..t+5} / IV_t) of the same name), SEALED window: non-overlapping formations every 5th session from 2023-01-02 to 2026-09-21, last target window ending 2026-09-28 = 184 formations (925 sessions to 2026-10-05, the common last date of the stock-option, equity and futures bhavcopy stores at drafting). RE-COUNT n_available at freeze against the minimum of the three stores' max dates; it only grows (~50 formations a year).
Substrate: data/market_data/stock_options_bhavcopy.duckdb (EOD chain, OI, close; 2016-02-11 -> present), equity_bhavcopy for t+1..t+5 high/low (each session's high/low ratio is same-day, so the as-traded basis is safe; ex-date sessions inside a window must be handled by the pre-registration), futures_bhavcopy for the parity forward. TRAIN 2016-2019 and HOLDOUT 2020-2022 are unread for this question.
Threats the pre-registration must pin, not this RFA:
- Autocorrelation. Targets do not overlap, but N and the RV/IV ranking persist across weeks, so ICs may still be serially correlated; the read must use Newey-West standard errors. At AC1 = 0.3 (n_eff ~99) the central corner falls from power 0.96 to ~0.79 - the margin is thin, unlike the daily draft.
- Mechanical coupling. Gamma per strike uses IV, and IV is the target's denominator; the ln IV control must be in both residuals.
- Results days. A 5-session window often contains a scheduled result; exclude or control, decided before any read, and only from a point-in-time calendar.
- Expiry inside the window / physical settlement (stock F&O since 2019): windows containing a monthly expiry are a pre-declared descriptive split, never a filter.
- Regime breaks: 2024-11-20 SEBI F&O reform, 2026-08-03 CAS - descriptive splits; the pass rule stays one test on the whole window.
A PASS would be a STATE-VARIABLE finding (like Stage A), not a trade: any long/short volatility book built on it needs its own declaration.)

## Optimistic corner

| Quantity | Value |
|---|---|
| delta (high) | 0.06 |
| SD (low) | 0.1 |
| n (raw, no AC haircut) | 184 |
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
| Optimistic corner | 19 |
| Central | 101 |
| Pessimistic | 2005 |
| **Available** | **184** |

## Declared bands and provenance

**delta: [0.01, 0.06]**

Declared direction: NEGATIVE - names with higher normalized net GEX at the formation close have LOWER realized variance over the next 5 sessions relative to the variance their options priced. The direction is fixed by GEX Stage A (index, spent windows), not chosen here. The gate takes the magnitude.

Construct (definitions and the control set are pinned HERE and bind the pre-registration; it pins only implementation detail - strike filters, IV solver bounds, exclusion lists):
- Formations: every 5th session starting 2023-01-02 (phase pinned here; other phases may be reported descriptively, never as the test). Targets never overlap.
- N_i,t: normalized net GEX per underlying, computed by core/analytics/gex_history.day_regime unchanged (Stage A sign convention: dealers long calls, short puts) on the EOD stock-option chain, all listed monthly expiries.
- y_i,t = ln(RV_i,t+1..t+5 / IV_i,t): RV = Parkinson variance averaged over sessions t+1..t+5, annualized; IV = ATM IV at the formation close from the nearest expiry with MORE than 5 sessions to go, so the pricing contract never expires inside the target window.
- Both N and y residualized cross-sectionally each formation on ln IV, ln rv5, ln rv20 (Stage A's controls minus VIX, which has no cross-section) PLUS the signed returns r_t and r_t-4..t. The signed returns are required, not optional: under the fixed convention N is a call-vs-put gamma balance that rises mechanically after a rally (spot moves toward call strikes), and stocks are calmer after rallies (leverage effect), so without them a negative IC can appear with no hedging at all. The rv controls carry only the size of past moves, not their sign. The IC is Spearman(N_resid, y_resid).

Defense of magnitude [0.010, 0.060]:
(a) Anchor - the index effect. Stage A's partial correlation of N with next-day y is t/sqrt(n): TRAIN 3.20/sqrt(953) = 0.104, HOLDOUT 2.65/sqrt(743) = 0.097 (GEX_REGIME_STAGE_A_{TRAIN,HOLDOUT}.md). That is a TIME-SERIES Pearson partial on one index at a ONE-day horizon; it is the ceiling, not the estimate. No horizon beyond one day has been read anywhere.
(b) Attenuation to the stock cross-section, each pushing the IC down:
  1. Stock options are monthly-only and their OI is small relative to the underlying's cash and futures turnover, so any dealer hedging flow is a smaller share of the tape than for NIFTY weeklies.
  2. The dealer-side sign is a fixed convention, not observed (the OI x price inference HedgeWall uses is not adopted). Misclassification attenuates IC toward zero; it is likely worse per stock than for the index because stock-option writers are more heterogeneous.
  3. Single-name RV is dominated by idiosyncratic news (results, corporate actions, block deals), and a 5-session window is more likely than one session to contain such an event.
  4. Part of the index effect may be a market-wide regime/sentiment effect with no cross-sectional counterpart (HEDGEWALL_BRIEF s4: the number was validated, not the dealer story). Cross-sectional residualization removes it by construction.
(c) The 5-session horizon moves the IC in two opposite directions:
  + Target noise falls. One-day Parkinson variance is a very noisy estimate; averaging 5 sessions shrinks the noise share of the target. If the forecastable part persisted unchanged across all 5 days, IC could rise by up to ~sqrt(5) = 2.2x when noise dominates.
  - The signal decays. Dealer books turn over, and the day-t gamma map is stale by t+5 (strikes roll, OI moves, an expiry may pass). Its persistence is unmeasured.
(d) Literature, direction only: Pearson, Poteshman & White, 'Does Option Trading Have a Pervasive Impact on Underlying Stock Prices?' (UIUC working paper, 2006; later published with Ni) find a significant NEGATIVE relation between US stock return volatility and the net purchased option positions of investors likely to hedge - the sign declared here. Direction checked against the working-paper abstract 2026-10-06; the published version's details and any magnitude were not read, and no magnitude is taken from it. Their hedger positions are observed from exchange data; ours are inferred by convention, so the effect here should be smaller. Not in the repo research library.

Band: optimistic 0.060 = the next-day optimistic 0.040 with half the maximum (c)+ gain retained (1.5x), still ~60% of the index ceiling. Pessimistic 0.010 = decay fully offsets the noise reduction and the effect barely survives the translation. Central 0.035. No stock-level GEX has ever been computed in this repo, so no in-sample read informs the band.

**SD: [0.1, 0.18]**

Per-formation Spearman IC over the usable cross-section. Coverage census (row counts only, no outcomes): names per session with a near-month chain carrying >= 10 OI strikes and >= 4 traded strikes - median 186 (2023), 182 (2024), 216 (2025), 209 (2026); minimum 178.

(a) Floor - sampling noise alone: SD of a rank correlation over ~180 names with true IC near 0 is ~1/sqrt(179) = 0.075. The horizon does not change this floor.
(b) Above the floor - cross-sectional dependence. In weeks with a market-wide vol event (budget, RBI, election, global gap) the cross-section of RV/IV moves together along beta and sector lines, so ICs are more dispersed than independent draws. A 5-session window averages out isolated daily shocks but catches a whole event week, so the net effect on dispersion versus a daily target is not signed; the band is kept at the daily draft's.
(c) Comparators: CB-N50 declared [0.15, 0.25] for 50 names daily (sampling floor 0.14); Carry declared [0.10, 0.18] for ~180 names monthly. This band uses Carry's - the cross-section is the same size.
sd_lo 0.10 = floor plus modest dependence; sd_hi 0.18 = event weeks dominate.

**Prior exposure**

1. GEX Stage A (2026-09-23): NIFTY index N vs next-day RV/IV, TRAIN 2016-19 and HOLDOUT 2020-22, both SPENT for that question. It fixes the sign and anchors the band ceiling. Index only, one-day horizon: no stock-option chain and no multi-day target was used.
2. GEX fly B1: NIFTY iron fly P&L 2019-02 -> 2022-12, STOP. Index only. Its memory note requires a fly successor to clear RFA on a defended gross Sharpe; this construct is a state-variable test on a different universe, not a fly successor, and claims no P&L.
3. Options seller-edge study + STOCK-STRADDLE-M10: read single-stock straddle P&L (equal-weight, unconditional) over 2016-22 AND the 2023-01 -> 2026-08 window - SPENT for that construct. That exposes the AVERAGE level of single-stock IV vs RV over ~9-session holds on the same sealed window - a horizon close to this one. It does not expose the cross-sectional ranking of RV/IV by GEX, which was never computed. Disclosed because it is the same data and the same broad quantity (IV vs RV) at a similar horizon.
4. IVOL sleeve: read 60-day realized-vol cross-section vs forward RETURNS on equity, sealed window spent. Different target (returns, not RV/IV); it exposes RV persistence, which the ln rv5 / ln rv20 controls absorb.
5. Options-Wall and HedgeWall claim-1: index-option OI/gamma walls and expiry-day concentration, 2024-01 -> 2026-09. Index only.
6. The coverage census in sd_provenance counted chain rows on 2016-2026 including the sealed window; it read no outcome and no GEX.
7. A next-day version (GEX-XS) was drafted the same day and replaced by this one before any freeze, gate report or data read; the horizon change was the operator's tradeability choice, not a response to results.
Not measured anywhere in the repo: stock-level GEX, its cross-sectional IC against RV/IV at any horizon, or any trade built on it.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
