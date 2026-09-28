# STOCK-STRADDLE-M10 — Research Feasibility Assessment

**VERDICT: PROCEED** — not provably infeasible — this is a floor, not authorization to build.

- Methodology version: `2.0.0`
- Declaration SHA-256: `a2015e0f135f470a13c2ad388d7bb4bc6c9b00328897c46f2f42adb2c4a891c5`
- Metric: per_trade_pnl | Test: one_sided | Power hurdle: 0.8
- Formations available: 36 (monthly (one equal-weight book of short ATM single-stock straddles per monthly expiry: entry at the close 10 sessions before expiry, exit at the T-1 close), Forward window only: 36 monthly cycles, the first being the 2026-10-27 expiry (entry 2026-10-12 close, 10 sessions before expiry) if the pre-registration is frozen before 2026-10-12, through the Sep-2029 expiry. 36 is the shortest round horizon (3 years) and is chosen because the gate is hardest there; the report's n_required figures give the horizon at every corner.
Instrument: NSE single-stock options, monthly expiry, ATM strike off the same-expiry future, both legs traded at entry; exit at T-1 close (physical settlement avoided). Forward fills must be at live bid/ask (the Sep-29 paper cycle was never run because no stock-option quotes were captured at entry - audit s5); capturing entry and exit quotes is a precondition the pre-registration must pin, not this RFA.
Cadence note: at cadence 12, ncp = S*sqrt(T), so no cadence change can shorten the horizon.)

## Optimistic corner

| Quantity | Value |
|---|---|
| Annualized Sharpe (high) | 1.51 |
| Cadence per year | 12 |
| Per-formation Sharpe | 0.435899 |
| Elapsed time T = n/c | 3.0000 years |
| n (raw, no AC haircut) | 36 |
| **Max achievable power** | **0.8211** |

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
| Optimistic corner | 1.51 | 34 |
| Central | 1.08 | 65 |
| Pessimistic | 0.65 | 177 |
| **Available** | — | **36** |

Equivalently (because cadence cancels): power 0.80 is reachable **iff** the
true annualized Sharpe clears the threshold implied by T alone. A longer time
window helps; a higher cadence does not.

## Declared Sharpe band and provenance

**Annualized Sharpe: [0.65, 1.51]** at cadence
12 formations/year.

Declared direction: POSITIVE - the short straddle earns the single-stock variance risk premium over the last ~9 sessions of the monthly cycle (OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md). One trade = one expiry cycle; its P&L is the equal-weight mean across names of the net seller return on premium (study fee model, 2% round-trip spread), so names within a cycle are never counted as independent trades.

The band is NET annualized Sharpe at cadence 12. Every anchor below is reproducible from committed code (W6: scripts/research/options_seller_edge/ca_filter_split.py, crash cycles RESTORED - the outcome filter the 2026-09-24 audit flagged is removed):
- OPTIMISTIC 1.51: the confirmation window 2023-01 -> 2026-08 (43 cycles, mean +8.07% of premium, t 2.85). It is the only genuinely out-of-sample read of this construct, and it is generous for a forward window because it is dominated by pre-reform cycles. The discovery window (2016-22) gave 1.73 and is not used: it chose the entry offset.
- PESSIMISTIC 0.65: the post-reform (2024-11-20 ->) Sharpe under the audit's seller-hostile conservative exit (STOCK_STRADDLE_SELLING_EVIDENCE_AUDIT_2026-09-24.md s8, 'reproducible'). The same sub-window at the observed exit gives 1.02 (21 cycles). The pessimistic corner is the weakest claim consistent with the edge surviving the Nov-2024 F&O reform at all.
- CENTRAL 1.08 (midpoint) sits at the observed post-reform 1.02.

Stated threats to the band (why the optimistic corner is not a prediction):
1. Regime. The forward window is entirely post-reform, where the observed Sharpe is ~1.0 on 21 cycles (t 1.35, not significant). The optimistic corner assumes the pre-reform edge returns.
2. Shrinkage. Out-of-sample slopes run 0.44-0.80 of in-sample (Lewellen 2015 [summary]); the confirmation read is already OOS, but a further forward haircut is the base rate.
3. Distribution. Per-cycle returns are negatively skewed (confirmation skew -1.19) and the book is short crash risk (W6 kinked beta: beta_down +0.55, se 0.08). Noncentral-t power assumes near-normal P&L; a short-gamma book's Sharpe overstates what a t-test can confirm (Brooks-Kat 2001).
4. Costs. The 2% spread is a single-day measurement (audit s7.2); T-10 and T-1 spreads are unmeasured, and the fee model misses the 0.15% options STT from 2026-04.

PROCEED means 'not provably infeasible' - a floor, never authorization, and never a statement about the true effect size.

**Prior exposure**

Every historical window of this construct has been read; there is NO unread history.
(a) Discovery 2016-01 -> 2022-12: the entry offset (10 sessions before expiry) was selected here among six offsets (study s2.1).
(b) Confirmation 2023-01 -> 2026-08-24: predictions written first (transcript-verified, audit s3), then read once -> SPENT. Liquidity cuts, the conservative exit and the >=100-contract screen were chosen after it was read (audit s4) and are descriptive only.
(c) Post-reform sub-window 2024-11-20 -> 2026-08: spent with (b).
(d) W6 (2026-09-27) re-read (a)-(c) for filter accounting only; it chose nothing.
(e) The same 2023+ stock-option data underlies the Options-Wall and seller-edge index checks (index selling showed nothing).
Consequence: confirmation can only be FORWARD, which is why n_available below counts future cycles.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
