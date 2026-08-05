# SE-1 — Research Feasibility Assessment

**VERDICT: ABANDON** — The construct cannot be demonstrated at the declared bands. Do not build it.

- Methodology version: `2.0.0`
- Declaration SHA-256: `5fbf35ace227f6af4eed7e12dfca567361e3c33c5aaad9d307d47bad1c5758a3`
- Metric: per_trade_pnl | Test: one_sided | Power hurdle: 0.8
- Formations available: 22 (event_driven, Event span 2016-04 -> 2025-09, 9.42 years, 22 announcement clusters / 66 genuine name-events (Nifty 50). The count is a FLOOR: the 2018-05 MCWB gap was not crossed, the TATAMOTORS->TMPV demerger was collapsed to one entity, and MCWB is month-resolution -- all three push the true count up, none down.

CALENDAR IS FIXED AND CANNOT BE EXTENDED BACKWARD. The MCWB archive begins 2016-01 and NSE F&O history before 2016 is not obtainable (SFB-1/F1 lockdown finding), so the execution leg cannot predate 2016 even if membership history could. n therefore grows only at ~2.3 clusters per year going forward.
  CORRECTED 2026-08-04: an earlier draft of this field asserted that waiting could not rescue SE-1. scripts/rfa/power.py falsifies that. At the band ceiling S_ann=0.80, n_required is 24 clusters against 22 available -- TWO more clusters, roughly ten months (the March and September 2026 reviews), not the twelve the draft claimed. Waiting does move the arithmetic.
  It does not, however, rescue the construct on its own, because the gate reads the OPTIMISTIC corner: reaching power 0.80 at n=24 still requires the true Sharpe to sit at the very top of a band whose centre (~0.55) projects power ~0.50. Waiting buys n; it supplies no evidence that the ceiling is the truth. Both halves of the revisit condition in the file header are required.

NO TRAIN/HOLDOUT/SEALED SPLIT IS DECLARED. Unlike the calendar-panel constructs, the whole event set is the confirmatory sample; there is no separate window in which to discover a rule and no reserve to hold back at this n. Any parameterization (event window length, weighting, add-vs-drop treatment) must therefore be pinned in a pre-registration BEFORE any return is computed, because there is no second sample in which to correct a choice made after seeing one.

Announcement-date coverage is currently 13.6% (9/66) programmatically. At cluster resolution only ~22 dates are required and 58 of 66 events are scheduled reviews with a published four-week notice convention, so this is a sourcing task of roughly 22 lookups -- not a data-availability constraint. It does NOT bear on this gate, which is decided on n and the Sharpe band alone.)

## Optimistic corner

| Quantity | Value |
|---|---|
| Annualized Sharpe (high) | 0.8 |
| Cadence per year | 2.335 |
| Per-formation Sharpe | 0.523536 |
| Elapsed time T = n/c | 9.4218 years |
| n (raw, no AC haircut) | 22 |
| **Max achievable power** | **0.7674** |

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
| Optimistic corner | 0.8 | 24 |
| Central | 0.575 | 46 |
| Pessimistic | 0.35 | 120 |
| **Available** | — | **22** |

Equivalently (because cadence cancels): power 0.80 is reachable **iff** the
true annualized Sharpe clears the threshold implied by T alone. A longer time
window helps; a higher cadence does not.

## Declared Sharpe band and provenance

**Annualized Sharpe: [0.35, 0.8]** at cadence
2.335 formations/year.

Construct: forced passive rebalancing flow. Long index additions / short deletions from the announcement date to the effective-date close, expressed in single-stock futures to avoid the delivery-equity STT wall. Declared direction: POSITIVE, fixed a priori by the mechanism (index funds are mandated to buy the addition at the effective-date print irrespective of price), not chosen from data.

OBSERVATION UNIT. The measured event structure (SE1_EVENT_COUNTING_REPORT.md, 2026-08-04) is 66 genuine Nifty-50 name-events collapsing into 22 announcement clusters (ratio 3.0) over 2016-04 -> 2025-09. Names inside one review share a single market environment, so the conservative unit is the CLUSTER. n_available=22 and cadence_per_year=2.335 encode that conservative choice. Because ncp = S*sqrt(T) and T = n/cadence = 9.42 years either way, the unit choice does not change the verdict — only the Sharpe band does. That is the intended behaviour of contract v2.

DEFENSE OF THE BAND [0.35, 0.80]. The band is an annualized Sharpe band, as contract v2 requires for per_trade_pnl; delta and sd are NOT declared separately, precisely so a crossed corner cannot smuggle in an effect size nobody defended (the O1 withdrawal error).
  Anchor: published Indian index-change event studies report a TEMPORARY price-pressure pattern -- inclusion gains fade within ~60 days, deletion effects dissipate in ~10 days, excluded stocks show +4-7% reversal over 60-240 days (IJAR 2025 'How does inclusion in the Nifty 50 index influence company stock returns 2010-2024'; Managerial Finance, 'Associated effects of index composition changes: evidence from the S&P CNX Nifty 50'; ScienceDirect S1042444X20300049 on institutional ownership around Indian index rebalancing). The sign and the transience are well established; a clean published delta/sd ratio is NOT, so the band below is derived, and the derivation is stated rather than hidden.
  Per-event effect over the ~4-week announcement-to-effective window is taken at 2-4% mean abnormal return against 8-12% cross-sectional dispersion of 4-week abnormal returns for Indian large caps, i.e. a per-event delta/sd of roughly 0.25-0.30. Numerator and denominator are deliberately NOT crossed at their most favourable values.
  LOWER 0.35 -- the conservative case: within-cluster correlation of abnormal returns is high (rho -> 1), so averaging names inside a review buys nothing. Cluster-unit delta/sd ~0.25 at 2.335 events/yr annualizes to ~0.38; 0.35 is set marginally below to avoid flattering the floor.
  UPPER 0.80 -- the optimistic case: abnormal returns are market-adjusted by construction, which strips the dominant shared component, so within-cluster correlation may be near zero (rho -> 0). Then a cluster average of ~3 names has dispersion sigma/sqrt(3), the effective unit is the name (n=66, 7.0/yr), and delta/sd ~0.30 annualizes to ~0.79.
  The band therefore spans the full rho in [0,1] range at a defended effect size. It is NOT an in-sample read: no price, return, or futures data has been consumed for SE-1. The counting pass measured event COUNTS only and computed no return, by explicit prohibition (SE1_COUNTING_PASS_AND_SPAN_INGEST_PROMPT.md section B.2).

WHY THE UPPER BOUND IS NOT SET HIGHER. Raising sharpe_hi to 0.85 flips the verdict to PROCEED. That would require either a per-event delta/sd above 0.32 or a rho below zero. The first crosses the corner (best-case numerator against best-case denominator) -- the specific error that withdrew O1. The second is not physical. The lead judged 0.80 the honest ceiling and flags the sensitivity in the file header rather than resolving it by choice of band.

**Prior exposure**

HEAVY, and it must be disclosed in full.

1. Two structural-alpha dossiers (STRUCTURAL_ALPHA_DOSSIER.md 2026-08-03; STRUCTURAL_ALPHA_DOSSIER_2.md 2026-08-04) were written before this declaration. Their author has read the outcomes of ten failed or closed constructs (O1, RS-MOM, N50-LS, FLOW, OSC, Trend, Skew, LAG, IVOL, CB-N50) plus Carry and TS Basis. SE-1 was ranked #1 in the second dossier on an arithmetic claim that has since been FALSIFIED.

2. The SE-1 counting pass (scripts/se1/count_index_events.py, 2026-08-04) has been run and read. It measured 66 genuine events, 22 clusters, ratio 3.0, and required delta/sd of 0.3501 (name) / 0.6264 (cluster). This declaration is written WITH that knowledge. The pass read MCWB membership only -- no price data, no returns, no P&L -- so the effect size in this declaration is not inherited from it. The counting pass constrains n, not delta.

3. Equity substrate exposure: PSB-1 and PSB-2 read the equity_bhavcopy_adjusted panel 2012-2022 extensively for cross-sectional constructs (C1-C5, C2-C4). None was an event study on index membership changes, and none measured announcement-window returns. The event-time axis is unburned, but the underlying price panel is not novel to this operator.

4. No index-rebalancing return has ever been computed in this repository. There is no in-sample SE-1 read of any kind.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
