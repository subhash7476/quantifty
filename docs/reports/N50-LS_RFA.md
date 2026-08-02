# N50-LS — Research Feasibility Assessment

**VERDICT: ABANDON** — The construct cannot be demonstrated at the declared bands. Do not build it.

- Methodology version: `2.0.0`
- Declaration SHA-256: `5727e29ff9e467e94244bce60a416437b4251817508726f271a9f14fc2290ecf`
- Metric: per_trade_pnl | Test: two_sided | Power hurdle: 0.8
- Formations available: 887 (daily, SEALED window 2023-01-01 → 2026-07-31 (887 verified daily formations, ~3.52 years). Nifty 50 point-in-time membership via MCWB substrate (one-month-lagged), same as CB-N50. SSF execution via near-month futures on Nifty 50 constituents (FUTSTK bhavcopy 2016-02-11 → 2026-07-20).

Window split: TRAIN 2016-2019, HOLDOUT 2020-2022, SEALED 2023-2026. TRAIN and HOLDOUT are prior-exposed (CB-N50 read the ranking IC there); neither is a clean gate. The single clean one-shot is SEALED. SSF history cannot predate 2016 (SFB-1/F1 lockdown finding), so the total calendar is fixed at ~10.5 years — no additional unread window remains for this construct family.

The 887 count is CB-N50's verified number for the same Nifty 50 daily cross-section on the same window (CB_N50_RFA.md). CB-N50 verified this against nifty50_pit_membership.json (one-month-lagged MCWB membership) and the NSE trading calendar. Counting formations is permitted by the gate; reading the book's P&L on SEALED is not.)

## Optimistic corner

| Quantity | Value |
|---|---|
| Annualized Sharpe (high) | 1.4 |
| Cadence per year | 252 |
| Per-formation Sharpe | 0.088192 |
| Elapsed time T = n/c | 3.5198 years |
| n (raw, no AC haircut) | 887 |
| **Max achievable power** | **0.7466** |

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
| Optimistic corner | 1.4 | 1012 |
| Central | 0.875 | 2586 |
| Pessimistic | 0.35 | 16149 |
| **Available** | — | **887** |

Equivalently (because cadence cancels): power 0.80 is reachable **iff** the
true annualized Sharpe clears the threshold implied by T alone. A longer time
window helps; a higher cadence does not.

## Declared Sharpe band and provenance

**Annualized Sharpe: [0.35, 1.4]** at cadence
252 formations/year.

Declared direction: POSITIVE (long top-quintile, short bottom-quintile by the combined reversal + cross-sectional-basis + time-series-basis score). All three features are pre-registered with positive sign (N50_LS_PRE_REGISTRATION.md §1.3); the equal-weight combination inherits that sign. Note: test_type is two_sided per the pre-reg §2.2 wording, though the pinned signs make a one_sided test defensible — this is a conservative choice that does not benefit the gate.

Derivation (Grinold-Kahn, IR = IC × √BR):

Anchor IC: +0.029 (CB-N50 HOLDOUT 2020-2022, 2 features, daily cross-sectional rank IC over Nifty 50 constituents; NW t=4.35). This is the least contaminated available IC — the TRAIN +0.059 is selection-inflated by the lookback/feature-drop choices (the C2 lesson: defend the effect size, do not inherit the largest in-sample read). The +0.029 is itself possibly optimistic since it was measured on the features the battery kept, not all features attempted.

The third feature (time-series basis) adds a genuinely different dimension (cross-sectional vs. time-series cheapness) and could modestly lift the combined IC, but the equal-weight dilution from 1/2 → 1/3 per feature works against it. The net effect on IC is unsigned; this derivation anchors on +0.029 with no inflation.

Effective breadth (N_eff): the number of independent daily bets after accounting for sector correlations, factor overlap, and within-day return noise. Nifty 50 spans ~12 sectors; stocks within a sector share factor exposure (daily correlation 0.3-0.6), so each sector contributes roughly 1-2 independent bets. Cross-sector correlations (e.g. banks↔financials) further reduce independence.

Floor: N_eff ≈ 1 (all 50 positions collapse to one factor-level bet after beta neutralization and sector concentration). Ceiling: N_eff ≈ 8 (3 feature dimensions × ~3 genuinely independent sector/factor groupings, with some within-sector diversification).

Sharpe estimates (IR = IC × √BR, BR = N_eff × 252):
- Floor: N_eff=1 → IR = 0.029 × √252 ≈ 0.46. Degraded for implementation costs and IC erosion in a book context → sharpe_lo = 0.35.
- Ceiling: N_eff=8 → IR = 0.029 × √(8×252) ≈ 0.029 × 44.90 ≈ 1.30. Generously rounded to 1.40 to reflect the multi-signal construction, beta-neutral isolation of residual alpha, and the gate's design intention that the optimistic corner be 'more generous than anyone believes.'

Literature anchor: liquid single-name daily cross-sectional L/S (reversal + carry/basis) realise annualised Sharpe ~0.5-1.5 gross (Koijen-Moskowitz-Pedersen-Vrugt 2018 for carry; Jegadeesh 1990, Lehmann 1990 for short-horizon reversal; Asness-Moskowitz-Pedersen 2013 for diversified multi-signal). The ceiling of 1.40 is within the literature's upper range for multi-signal approaches.

These bands are derived from the HOLDOUT IC and independently defended breadth assumptions. They are NOT reverse-engineered from the ~1.47 threshold that would clear power 0.80 — in fact, even at the 1.40 optimistic ceiling the gate returns ABANDON (max power 0.75). The derivation and the verdict are independent.

**Prior exposure**

The Nifty 50 long-short book P&L has NEVER been read on any window — the 2023-2026 SEALED book-P&L read is genuinely unspent. The following prior reads on overlapping data are fully disclosed:

1. CB-N50 TRAIN (2016-2019) and HOLDOUT (2020-2022): daily cross-sectional rank IC of the same 2/3 features (reversal + basis) on the same Nifty 50 universe. The operator has seen the ranking IC (TRAIN +0.059, HOLDOUT +0.029) but NOT the book P&L, turnover, or MaxDD derived from those rankings.

2. TS-Basis (monthly, SSF ~180): basis-level signal incl. a spent sealed read (2026-07-24). The operator has seen the monthly basis signal on the full SSF panel. This construct borrows only the time-series basis calculation, on a different universe (Nifty 50 vs. 180 SSF) and at a different frequency (daily vs. monthly).

3. TS-Basis Daily (~180 SSF, daily): selection-burned TRAIN/HOLDOUT; research-only by operator decision. The operator has seen daily basis-level dynamics on the full SSF panel but never on the Nifty 50 subset. The SEALED window for this construct is preserved (unspent).

4. Carry sleeve (~180 SSF, monthly): residual-basis IC experience. Prior exposure to the general cross-sectional carry effect at monthly horizon, different frequency and universe.

5. PSB-1/PSB-2 (equity cash, monthly): cross-sectional ICs for delivery-percent, reversal, momentum on NIFTY-200. General exposure to equity cross-sectional predictability at a different frequency and for different signals. Not a read on Nifty 50 SSF book P&L.

6. SFB-1/F1 (stock-futures, monthly): momentum at monthly horizon with bracketed exits. General exposure to equity momentum difficulty. Not a read on this construct.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
