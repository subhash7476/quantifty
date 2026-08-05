# SE-3 — Research Feasibility Assessment

**VERDICT: PROCEED** — not provably infeasible — this is a floor, not authorization to build.

- Methodology version: `2.0.0`
- Declaration SHA-256: `fd91b1d5d15f2a5c0172ba211de0b34fd8331a4e01f325dff68e111e20e58089`
- Metric: rank_ic | Test: two_sided | Power hurdle: 0.8
- Formations available: 1701 (daily, CONFIRMATORY WINDOW: 2016-02-11 -> 2022-12-31, 1,701 daily formations, on both option legs. This is the PERMISSIVE reading, adopted by operator decision 2026-08-05 (recorded in SE3_BREADTH_PROBE_REVIEW_2.md).

THE STRICT READING IS n ~= 495 (2021-01-01 -> 2022-12-31), which treats Skew's 2016-2020 TRAIN as spent for any option-cross-section work. It is recorded as a SENSITIVITY, not the operative n. At the approved band it also clears the gate's optimistic corner (power 0.9569 at n=495), but the two readings are NOT equivalent: strict's CENTRAL power is 0.6203 against permissive's 0.9877.

FALSIFICATION CONDITION ON THE PERMISSIVE READING, stated before any construct code exists so it cannot be renegotiated later: IF SE-3's signal DRIFTS FROM ATM LEVEL RICHNESS TOWARD WING OR SKEW FEATURES, grounds (1) and (2) of the operator decision collapse, Skew's exposure becomes a SPEND, and n falls to ~495. The pre-registration must therefore PIN THE SIGNAL TO ATM LEVEL RICHNESS and either demonstrate low correlation with the 25-delta risk-reversal quantity Skew tested, or accept the strict reading from the outset.

CALENDAR CANNOT BE EXTENDED BACKWARD. NSE F&O history does not predate 2016-02-11 and is not obtainable (SFB-1/F1 lockdown finding), so n cannot be raised by sourcing more history. It grows only forward, and the 2026 tail is short.

WINDOWS SPENT AND PRESERVED AS AT THIS DECLARATION. Spent: OPTSTK 2023-2025 (the breadth probe). Already burned before SE-3: NIFTY index options 2023-2025. PRESERVED AND UNREAD: the 1,701-date index-option window above, the joint-clean OPTSTK 2021-01-01 -> 2022-12-31, and both legs 2026-01-01 -> 2026-07. NO MARKET DATA WAS READ FOR THIS DECLARATION OR FOR THE LITERATURE PASS THAT DEFENDS ITS DELTA BAND.

NO TRAIN/HOLDOUT SPLIT IS DECLARED HERE. The pre-registration that follows must pin every parameter -- moneyness band, DTE window, neutralization, banding, name minimum -- BEFORE the confirmatory window is opened, because the burned 2023-2025 window is the only surface on which a rule may be discovered and it is already spent.)

## Optimistic corner

| Quantity | Value |
|---|---|
| delta (high) | 0.0311 |
| SD (low) | 0.1877 |
| n (raw, no AC haircut) | 1701 |
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
| Optimistic corner | 288 |
| Central | 756 |
| Pessimistic | 2492 |
| **Available** | **1701** |

## Declared bands and provenance

**delta: [0.0146, 0.0311]**

Construct: index-versus-constituent dispersion, expressed as a DAILY cross-section of Nifty 50 constituents ranked on ATM option richness (IV rich relative to the name's own realized vol and the day's cross-sectional norm), against a vega-scaled delta-hedged forward return (Bakshi-Kapadia discrete). Declared direction: TWO-SIDED. The mechanism implies NEGATIVE (rich options subsequently underperform delta-hedged -- the variance risk premium), and that sign is fixed a priori; two-sided is declared as the conservative test because the IVOL sleeve SIGN-FLIPPED at SEALED on this same universe (TRAIN and HOLDOUT both PASS at negative sign, SEALED IC +0.018, net -13.78%), so a sign assumption on an option-vol construct in this universe has a demonstrated failure mode in this repository.

EVERY CANDIDATE DELTA IS A DERIVATION, NOT A CITATION. No paper in this literature reports a daily cross-sectional Spearman rank IC. The translation is therefore stated in full rather than asserted, because an undisclosed derivation is exactly the crossed-corner error that withdrew O1.

PRIMARY ANCHOR -- Cao & Han (JFE 2013), 'Cross section of option returns and idiosyncratic stock volatility'. Jan 1996 - Oct 2009, 213,640 call observations over 6,141 stocks, ATM ~50-day options, monthly formation, DAILY delta-rebalancing. Their VOL_deviation = ln(VOL/IV) is the closest published analogue to variant A's richness residual. Fama-MacBeth coefficient on VOL_deviation (calls): 0.0512 (t=17.93) for the gain to month-end; cross-sectional SD of that gain is 5.13%; SD of VOL_deviation is 0.29.
  SIGN. The coefficient is POSITIVE on ln(RV/IV), so the delta-hedged return is DECREASING in richness. This independently confirms the pre-registered negative sign. Recorded because a secondary source (Cao 2018, HEC working paper) states this relation backwards; the primary table was checked rather than the secondary trusted.

STEP 1 -- monthly cross-sectional correlation, two independent routes.
  Route A (coefficient): 0.0512 * 0.29 = 1.485% against sigma_cs 5.13% -> IC_monthly = 0.2894.
  Route B (R^2 increment): average adj. R^2 rises 0.0242 -> 0.0757 when VOL_deviation is added -> sqrt(0.0515) = 0.2269.
  Route B (conservative) sets the floor; Route A the ceiling.

STEP 2 -- horizon, monthly -> daily. If edge accrues linearly in h and noise as sqrt(h), IC ~ sqrt(h), giving a factor sqrt(1/21) = 0.2182. Cao & Han also publish an 'until next week' coefficient (0.0168, t=15.01), which PARTIALLY grounds this step. It is only partial and is declared as such: they do NOT publish sigma_cs at the weekly horizon, so computing IC_week requires imputing sigma_cs(week) with the very sqrt(h) law under test. The apparent exponent that falls out (h^0.2765, implying a daily IC of 0.1247) is therefore contaminated by its own imputation and IS NOT USED. What is genuinely independent is the coefficient ratio 0.0168/0.0512 = 0.3281 against a horizon ratio 5/21 = 0.2381: the mean effect decays slower than linearly in h, supporting a front-loaded signal directionally without pinning an exponent. sqrt(h) is used at BOTH ends of the band; the slower-decay evidence is recorded as an upside NOT claimed.

STEP 3 -- haircuts.
  Out-of-sample shrinkage 0.492: CB-N50 measured 50.8% shrinkage (TRAIN +0.059 -> HOLDOUT +0.029) on the SAME daily cross-sectional rank-IC method in THIS repository. This is the 'SD must be independently defended, not inherited from a short in-sample read' lesson that retired C2, applied to delta.
  US->India transport + univariate-vs-multivariate 0.60: Cao & Han's coefficient is a PARTIAL effect estimated with controls, whereas the measured quantity here is a univariate rank IC; and the Indian single-stock option panel is ~46 PIT-eligible names against 6,141. APPLIED TO THE FLOOR ONLY -- defending it on the ceiling would assert the effect is no larger in a less efficient market, which is not established either way.

THE BAND.
  delta_lo = 0.2269 * 0.2182 * 0.492 * 0.60 = 0.01462
  delta_hi = 0.2894 * 0.2182 * 0.492        = 0.03107
  CORNERS ARE NOT CROSSED. delta_hi takes the optimistic IC route and the lighter haircut but HOLDS THE HORIZON MODEL AT THE CONSERVATIVE sqrt(h). Taking the apparent exponent as well would give 0.0614, which is not claimed.

COUNTER-EVIDENCE, recorded rather than buried. Driessen, Maenhout & Vilkov (JF 2009, and their 2013 companion) find the CONSTITUENT-leg variance risk premium statistically indistinguishable from zero: individual realized 41.99% vs implied 43.38%, not significantly different, with the null of zero VRP not rejected for 503 of 919 S&P 500 stocks (27 of 43 for DJ30), against a strongly significant index premium (20.69% vs 23.09%). Bakshi & Kapadia (JoD 2003) concur: the individual-equity delta-hedged loss is 0.03% of underlying value against 0.07% for the index, 'much smaller than for index options'.
  WHY THIS DOES NOT VOID THE BAND: SE-3's demonstrable form does not bet on the LEVEL. The index-versus-basket dispersion trade is one number per day and is already blocked. The cross-sectional form needs richness DISPERSION to predict return DISPERSION, which is a different claim and is the one Cao & Han establishes at t~18.
  THE CONSEQUENCE THAT MUST SURVIVE INTO DESIGN: SE-3 does NOT inherit the index VRP, and India's special mechanism (retail dominance of INDEX options, Agarwal/Ghosh/Prabhala/Zhao 2025) applies to the leg SE-3 cannot bet on. The constituent cross-section rests on a US-documented effect with NO Indian amplification, and this band is not inflated by the retail evidence.

IVOL-IN-DISGUISE, asked because the repo has standing reason to ask (IVOL sign-flipped at SEALED; LAG died on subsumption). Cao & Han answers it favourably: IVOL (t=-15.78) and VOL_deviation (t=+17.12) are JOINTLY significant with OPPOSITE signs in the same Fama-MacBeth specification, so richness is not subsumed by vol level. This is NOT a discharge -- a subsumption guard against this repo's own Trend and IVOL signals must still run at design time, as LAG's did. The literature establishes only that the guard is not expected to fire.

NOT INHERITED FROM ANY IN-SAMPLE READ. The SE-3 breadth probe measured a skip-a-day mean_IC of -0.113 on the burned 2023-2025 window. That number is PROHIBITED as the anchor by SE3_BREADTH_PROBE_PROMPT.md section 7, and no component above was chosen with reference to it. Its magnitude happens to sit near the pre-haircut daily range [0.063, 0.125], which is reported in the literature pass as a consistency check and NOT as evidence.

**SD: [0.1877, 0.26]**

MEASURED, not assumed. sd_lo = 0.1877 is variant A's own measured time-series SD of the daily cross-sectional rank IC from the SE-3 breadth probe (SE3_BREADTH_PROBE_REPORT.md), over 712 formation dates on 2023-01-02 -> 2025-12-31, keyed on the SKIP-A-DAY construction.

WHY SKIP-A-DAY. The same-day IC is contaminated: the settle price V_t enters both the signal (via IV inversion) and the return (via the delta-hedged P&L) with opposite signs, so settle bounce mechanically pushes the same-day IC negative. The corrective run re-keyed the measurement on richness at t against the return over t+1 -> t+2, which removes V_t from the return entirely. Lead review verified the construction rather than the output, and confirmed the specific failure mode it was checking for -- a stale Delta_t hedging a later move, which would have reintroduced a gamma term -- is absent. Same-day sd was 0.1938; the clean value is 0.1877.

sd_lo IS NOT SET BELOW THE MEASUREMENT. The gate reads the OPTIMISTIC corner (high delta, LOW sd), so sd_lo is precisely where a verdict can be silently manufactured. An earlier draft set it to 0.18, which was a CROSSED CORNER on two counts: 0.18 is below both measured values, and it took the floor from variant B's measurement (0.1814) while taking delta from variant A's analogue. Corrected to variant A's own 0.1877. The correction costs nothing (ncp 6.83 permissive, 3.68 strict) and is recorded because the error class matters more than the magnitude.

sd_hi = 0.26 (~+39%) CARRIES THE C2 LESSON EXPLICITLY. C2 was retired because an SD estimated on a short window did not survive re-estimation on a wider one. This sd comes from a single three-year window (2023-2025) and is projected onto a confirmatory window (2016-2022) that SPANS COVID, which 2023-2025 does not. Cross-sectional IC dispersion is regime-dependent and a wider window should RAISE it, so the upper end is set well above the measurement rather than bracketing it symmetrically.

RELATION TO N_eff, because the two look contradictory and are not. The probe's raw N_eff is 5.9, which would imply sd_IC ~ 1/sqrt(N-1) = 0.45. The observed 0.1877 implies a breadth of 29.4. They measure DIFFERENT THINGS: N_eff was computed on the LEVELS of the delta-hedged return panel, so a market-wide vol shock that moves all names together inflates rho_bar and collapses N_eff -- but a Spearman rank IC depends only on the within-day ORDERING of returns, and a common additive shift leaves that ordering unchanged. The IC-implied 29.4 sits between the raw 5.9 and the demeaned 44.1, which is where a rank statistic should land. No derivation of sd from N_eff is required or performed; sd is measured directly.
  THE COROLLARY IS BINDING ON DESIGN: N_eff = 5.9 (itself an UPPER estimate -- per-name V_t noise dilutes cross-name correlation) remains the honest breadth for anything expressed in P&L. A rank_ic PROCEED here DOES NOT imply a per_trade_pnl PROCEED, and CB-N50's binding constraint #3 applies in full: the primary hypothesis must genuinely be stock-level cross-sectional prediction, not an index view wearing a cross-sectional veneer.

**Prior exposure**

HEAVY, and disclosed in full.

1. TWO STRUCTURAL-ALPHA DOSSIERS (STRUCTURAL_ALPHA_DOSSIER.md 2026-08-03; STRUCTURAL_ALPHA_DOSSIER_2.md 2026-08-04) were written before this declaration. Their author has read the outcomes of ten failed or closed constructs (O1, RS-MOM, N50-LS, FLOW, OSC, Trend, Skew, LAG, IVOL, CB-N50) plus Carry and TS Basis. SE-3 is ranked best-mechanism in the second dossier and simultaneously held at #3 for want of a breadth measurement.

2. THE SE-3 BREADTH PROBE HAS BEEN RUN AND READ, and it SPENT the OPTSTK stock-option leg on 2023-01-02 -> 2025-12-31 (the index leg there was already burned by the MSRP fee triage and OSC's SD probe). It measured sd_IC, N_eff, mean_IC, implied-correlation diagnostics and per-variant date counts. This declaration is written WITH that knowledge. sd IS inherited from it -- deliberately, and that is what the probe was for. mean_IC is NOT, by explicit prohibition.

3. THE SKEW SLEEVE read the OPTSTK TRAIN surface 2016-07-31 -> 2020-12-31 (25-delta risk-reversal, monthly, IC -0.018, t=-1.15, FAILED at section 9 gate 2). This overlaps the confirmatory window declared below. The operator decision of 2026-08-05 treats it as DISCLOSED PRIOR EXPOSURE rather than a spent window, on three recorded grounds: a different quantity (wing/asymmetry vs ATM level richness), a different cadence (monthly vs daily), and a FAILED read -- which leaks less than a successful one because nothing was selected on its strength. See the window field for the falsification condition attached to that decision.

4. OSC (option surface cross-section) was probed and abandoned on the same 2023-2025 index-option window, producing sd_IC 0.2502, N_eff 1.9, and a documented same-day bounce-contamination finding. SE-3's probe REUSES OSC's tested Black-76 code and its skip-a-day correction, and SE-3's decision ladder was keyed to OSC's delta anchors so the two are comparable. OSC's abandonment is the reason SE-3's breadth was measured before anything was declared.

5. THE VARIANT CHOICE IS A SELECTION WITH m = 2. The probe measured variants A and B; this declaration adopts A. That choice was made on the burned window, which is what a burned window is for, but it must be declared. It was made on A PRIORI GROUNDS -- the literature anchor exists for A's construction and not for B's -- and NOT on the 0.1877-vs-0.1814 sd gap, which round-2 lead review established is CONFOUNDED (A and B differ in estimator, name universe AND date set simultaneously: 712 dates vs 483).

6. NO SE-3 RETURN HAS EVER BEEN COMPUTED OUTSIDE THE BURNED WINDOW. The confirmatory window declared below is unread on the index leg and Skew-exposed but unspent on the stock leg.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
