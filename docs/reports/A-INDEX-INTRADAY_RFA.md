# A-INDEX-INTRADAY — Research Feasibility Assessment

**VERDICT: PROCEED** — not provably infeasible — this is a floor, not authorization to build.

- Methodology version: `2.0.0`
- Declaration SHA-256: `221c6ca97108fee6a9ee0e357a982a4cee1c3f3879e1f38c0523513ad6342d8b`
- Metric: per_trade_pnl | Test: one_sided | Power hurdle: 0.8
- Formations available: 873 (daily (1 trade per session; measured 237/yr with the session-validity + 15:14-exit-bar rules, 2012-2026), Sealed projection window 2023-01-01 -> spend date. n_available = 873 sessions measured 2026-08-27 (cadence 237/yr -> T ~ 3.68 yr; grows ~20 sessions/month; spend-floor mechanics are pre-registration business, not RFA business).
Substrate: NSE_INDEX|Nifty 50 1m, 2012-01-02 -> 2026-08-21 (3,574 Nifty-bearing files; certification FAIL-with-register as disclosed above). Fences: TRAIN 2012-01-02 -> 2018-12-31 (1,699 tradeable sessions measured), HOLDOUT 2019-01-01 -> 2022-12-31 (988), SEALED 2023-01-01 -> present (873). Exit re-pinned to the 15:14 bar close (D6) — last continuous print in all three structural eras (vendor 2012-01-02..2023-01-31 / native 2023-03-01..2026-08-02 / CAS 2026-08-03+); the CAS auction window is deliberately untraded.
Cost lane (measured): futures fees 3.81 bp/trip at the canonical Rs 2Cr notional, entry slippage p90 0.66-0.78 bp/side, exit pays the same band, basis mean ~0.4 bp (dispersion disclosed, D5). Basis pre-2016 held at the 2016+ measured figures as the disclosed assumption.
Note: this construct clears the RFA's power hurdle on measurement density (873 daily trades from the same 3.6-year sealed window that yields only ~186 weekly RS-MOM formations) — the RS-MOM/FLOW walls (Sharpe >= 1.3 on a single series at weekly cadence) do not bind at daily cadence, but the band defense above is what the gate actually judges.)

## Optimistic corner

| Quantity | Value |
|---|---|
| Annualized Sharpe (high) | 1.45 |
| Cadence per year | 237 |
| Per-formation Sharpe | 0.094188 |
| Elapsed time T = n/c | 3.6835 years |
| n (raw, no AC haircut) | 873 |
| **Max achievable power** | **0.8720** |

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
| Optimistic corner | 1.45 | 699 |
| Central | 1.075 | 1270 |
| Pessimistic | 0.7 | 2992 |
| **Available** | — | **873** |

Equivalently (because cadence cancels): power 0.80 is reachable **iff** the
true annualized Sharpe clears the threshold implied by T alone. A longer time
window helps; a higher cadence does not.

## Declared Sharpe band and provenance

**Annualized Sharpe: [0.7, 1.45]** at cadence
237 formations/year.

Declared direction: POSITIVE — opening-drive continuation on NSE Nifty 50 (single-index time series), sign pinned by mechanism (D1, A_CONSTRUCT_DEFINITION.md): the opening call auction concentrates the overnight information set into one print, and the in-house index-pair research measured NSE index intraday flow TRENDING (+1.10/+1.17 slopes — NIFTY_BANKNIFTY_PAIR_RESEARCH.md). Negative TRAIN closes the family; no sign-flip fishing.

The band is declared on NET per-trade Sharpe, annualized at cadence 237 (per-trade S = S_ann / sqrt(237) = sqrt(237) ~ 15.4): S_ann 0.70 / 1.075 / 1.45 corresponds to per-trade S 0.045 / 0.070 / 0.094, i.e. mean net returns of ~4.5 / 7 / 9.4 bp per trade at a ~100 bp per-trade SD (the Nifty 50 intraday-hold SD anchor: public index realized vol ~12-18% annualized; the ~5.4h hold captures most of the daily move; the exact SD is a TRAIN-period measurement, not needed for this defense).

Defense of the band, bottom-up:
- PESSIMISTIC 0.70 (per-trade 0.045, ~4.5 bp mean net): the weakest claim consistent with ANY exploitable effect after the measured hard costs (~5.3 bp/session fees+slippage; A_COST_SUBSTRATE_MEASUREMENTS.md). Below this, the net-spread gate at TRAIN is structurally negative and the construct cannot survive regardless of power.
- CENTRAL 1.075 (per-trade 0.070, ~7 bp mean net): the literature-consistent middle. The closest academic anchor is Gao-Han-Li-Zhou (2018) intraday momentum — opening-period returns predict later-session returns at statistically significant but economically modest magnitudes; ~7 bp on a ~100 bp intraday move is that scale for a single index.
- OPTIMISTIC 1.45 (per-trade 0.094, ~9.4 bp mean net): the strongest defensible reading of the mechanism, anchored to the strongest fresh-window effect this repo has ever measured — ISD F4 (equity overnight-gap fade, TRAIN IC -0.029, NW t -6.09, 3.2-6.0 bp gross per-session book spread on a ~200-name cross-section). The index is a single name whose per-trade move is ~1% (an order of magnitude larger than the equity book's per-session spread); a 9.4 bp mean on a 100 bp move is the same order of magnitude as that measured effect translated to the single-name scale. This corner means 'the NSE auction-concentration mechanism delivers'.

Standing falsifications, stated (the reason the center is modest): the FTMO corpus (0/41 time-series intraday patterns on USTEC/gold) is the out-of-repo null for this quadrant; ISD F1 (equity opening-drive CONTINUATION, the cross-sectional cousin of this hypothesis) closed with a NEGATIVE TRAIN sign; and the cash-proxy basis dispersion (full-day within-contract |d| p90 19.2 bp, D5 decision) is invisible to the cash-series backtest and must be defended against — the optimistic corner is therefore not a prediction but the most generous reading consistent with the evidence. PROCEED means 'not provably infeasible' — a floor, never authorization, and never a statement about the true effect size.

No TRAIN data has been consumed for this declaration. The band is declared pre-read and frozen at approval; it will never be revised in response to results.

**Prior exposure**

Full inventory in A_INDEX_INTRADAY_PRIOR_EXPOSURE_AUDIT.md (2026-08-27). Summary:
(a) The index 1m store (2012-2026) was read STRUCTURALLY by the NiftyShield DayType pipeline (build_intraday_features.py output CSVs prove 2012-01-04 -> 2025-12-31): checkpoint partial-day features computed from the same OHLC, target = day-type regime classification (cluster_id), NOT returns — no trading rule was ever scored. The feature space overlaps A's (partial returns, ranges, slopes); the target does not.
(b) The 2023-2026 window carries the only SIGNAL-level read: the index-pair research (844 sessions of 1m) tested 27 ratio mean-reversion combos — all net-negative (the pair does not revert); byproduct: intraday trending slopes +1.10/+1.17, direction-favorable to continuation, disclosed as prior evidence.
(c) ISD F1/F4 (equity 1m, 2023-2026, TRAIN-only): F1 opening-drive continuation NEGATIVE (the cross-sectional cousin of this hypothesis failed on sign); F4 overnight-gap fade was the strongest fresh-window effect ever measured (IC -0.029, NW t -6.09) yet net-negative after costs — the cost-wall finding that closed cash-equity intraday and motivated A. Both are different instruments (stocks vs index) and different levels (cross-section vs time series).
(d) The FTMO corpus (0/41 time-series intraday patterns) is the standing out-of-repo falsification prior; A is its cheap NSE test.
(e) No trading-rule evaluation of index 1m data exists on ANY window — pre-2023 windows are structurally exposed / evaluatively clean; 2023+ is pair-exposed for the ratio hypothesis only.
(f) Substrate certification of the index slice is FAIL-with-register (A_INDEX_SLICE_CERTIFICATION.md): permanent holes (2018-05, 22 sessions, absent from source; 2023-02, 20 sessions, vendor/native transition), 12 out-of-shape specials, 66 partials, 3 native first-bar defects — all excluded mechanically by the session-validity rules; vendor-era boundary fidelity (opening print vs auction: med 3.2 bp / p99 25 bp / max 74 bp; last bar vs official close: med 5.4 / p99 32 / max 108 bp) absorbed via the opening-print base (D3) and the 15:14 exit (D6, CAS-era: the 15:29 bar is the closing-auction print since 2026-08-03). Availability: TRAIN -25, HOLDOUT -4, SEALED -21 in-scope sessions; fences unchanged.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
