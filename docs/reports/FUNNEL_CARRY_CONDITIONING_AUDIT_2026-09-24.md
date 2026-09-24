# Funnel Audit — CB-N50 → Carry → TS Basis / C5

**Date:** 2026-09-24 · **Branch:** `research/funnels-filter` (fast-forwarded to `main` `b02b519`)
**Standing:** repo audit plus research-design critique. **No market data was read, no backtest run,
no parameter touched.** The only computation is power arithmetic from `scripts/rfa/power.py`,
which takes no data (§7).

**Evidence tags used throughout:**
- **[E] Established**: gated result, or code verified directly.
- **[I] Inconclusive**: measured, but in-sample, provenance-unclear, or underpowered.
- **[H] Hypothesis**: not measured anywhere in the repo.

---

## 0. Bottom line

1. **The funnel as proposed is not defensible, and it fails before statistics.**
   - CB-N50 cannot act as a market or context filter. Its breadth score is pinned near 0.5 by
     construction, and its strongest feature *is* a basis signal.
   - TS Basis is largely the same factor as Carry.
   - C5 was never measured on the Carry universe. Its closest measured relative (IVOL) failed
     its sealed read.
2. **Even if the funnel were well-formed, it could not be tested.**
   - No unread historical window exists for anything that touches single-stock-futures basis data.
   - A month-level state-filter test on Carry needs **65–740 monthly formations** (5–60 years)
     for 80% power (§7).
3. **The anchor itself has two open measurement questions that come before any funnel.**
   - Carry's validated edge is measured on **spot** equity returns, but the book trades
     **futures**.
   - The v2 sign's "canonical carry" defense appears to invert the literature's definition.

---

## 1. Exact mechanics and timing

| | **Carry (v2)** | **TS Basis (monthly)** | **CB-N50** | **C5 low-vol** |
|---|---|---|---|---|
| Pre-reg | v1 `02f85f5b…` + v2 `74c7311c…` (sign only) | `07265b50…` | `CB_N50_PRE_REGISTRATION.md` | `PSB1_PROTOCOL.md` Rev 2 §C5 |
| Universe | PIT F&O stocks, 20-d median futures turnover ≥ ₹5 cr (~120–200 names) | Same as Carry, `liquid = TRUE` | PIT **Nifty 50** (MCWB), ≥30 eligible | PIT **NIFTY-200 cash equity** |
| Raw input | `(F−S)/S × 365/DTE`, near-month, roll T−3 | Same `raw_ann_basis` | Features at close *t*: reversal, basis (median-demeaned, annualised); momentum dropped at TRAIN | σ of 252-d daily returns (≥200 obs) |
| Transform | − ex-date dividends in (t, expiry] → cross-sectional demean → winsorise ±3 → z → **OLS residual on 252-d beta + sector** | Own-history z: (b − μ)/σ over prior 504 calendar days, ≥12 obs, clip ±3. **No neutralisation** | Per-feature cross-sectional z, clip ±3, equal-weight sum; breadth = free-float-weighted share of names with S>0 | s = −σ |
| Sign | + (long high residual basis) | + (long high z_ts) | + on the composite score | + (long low vol) |
| Formation | **Last trading day of calendar month** (not roll-aligned, `CARRY_TSBASIS_PAPER_PLAN.md` §1.4) | Same | **Daily**, after close *t* | Month-end |
| Target / horizon | Spot adjusted close(t) → close(next formation), `fwd_ret_1m` | Same `fwd_ret_1m` | Stock **open(t+1) → open(t+2)**, one day | Cash forward 1 month |
| Portfolio | Weights ∝ z, beta/sector/dollar neutral, 10% ADV cap, 0.25σ band | Quintile L/S equal-weight, ADV cap, 0.25σ band | Rank IC only; the breadth→Nifty-futures leg was never evaluated | **Long-only** top quintile vs base, banded exit 0.40 |
| Windows read | TRAIN 2016-03→2020-12 (burned for sign), HOLDOUT 2021–22, **SEALED 2023-01→2026-07** | TRAIN, HOLDOUT, **SEALED** (de-authorised) | TRAIN 2016–19, HOLDOUT 2020–22; sealed unread | Dev 2012–2022 (all of it); cash sealed unread |
| Headline | HOLDOUT IC +0.046, t 2.60, p 0.016; SEALED IC +0.061, net +20.52% | HOLDOUT IC +0.041, p 0.031 (fails α 0.025); SEALED IC +0.077, net +22.57% | TRAIN IC +0.059 (selection-inflated); HOLDOUT **+0.029** | Mean IC +0.068, SD 0.246, power 0.54 (fails 0.80) |

**Timing facts verified in code [E]:**
- **Carry's return is spot, not futures.** `build_carry.py:341-355` builds `fwd_ret_1m` from
  `equity_bhavcopy_adjusted` close-to-close. `run_sealed.py:175-203`, `run_net_spread.py:191` and
  the production rebalancer (`carry_rebalancer.py:668`, which feeds the +0.0 bp parity gate) all
  book P&L from that spot series. Futures data is used only for ADV.
- **Carry assumes same-close execution.** The signal uses close *t*, and the return starts at
  close *t*. No execution-lag sensitivity exists. `CARRY_CADENCE_DECAY_REPORT.md` shows 1-week IC
  close to 1-month IC, so the cost is probably small, but a one-day lag is **[H] unmeasured**.
- **Cross-sections require a known future.** Carry's research cross-section and TS Basis's entire
  build (`build_ts_signals.py:66-69`) require `fwd_ret_1m IS NOT NULL`. A name is scored at *t* only
  if it has a price at the next formation. The rebalancer's own docstring calls this
  "HISTORICAL-REPLAY-ONLY" (`carry_rebalancer.py:624`).

---

## 2. Pairwise relationships

| Pair | What exists | Tag |
|---|---|---|
| **Carry ↔ TS Basis** | `MULTI_FACTOR_COMBINATION_ASSESSMENT.md`, repaired monthly store, fenced ≤2022-12-30, 71 formations: **ρ(signal) +0.617, ρ(IC) +0.534, equal-weight blend lift 0.986** (below Carry alone). The earlier figures (L/S return ρ +0.46, blend Sharpe 2.09 vs 1.72; `BASIS_MOMENTUM_DECISION_REVIEW.md`) were computed on 2026-07-26, the day `03fc76a` repointed `ts_signals.duckdb` to the weekly source. Their store provenance cannot be confirmed. | **[I]**. Treat the matrix as primary and the 0.46 / 2.09 figures as unverified. The CLAUDE.md "Sharpe ~2.09" line is superseded. |
| **Carry ↔ C5** | **Never measured.** C5 exists only on NIFTY-200 cash, 2012–2022. The nearest proxy is IVOL (60-d idiosyncratic vol, beta+sector neutral, SSF): ρ(signal) −0.036, ρ(IC) +0.09 to +0.23, blend lift 0.928, and **SEALED sign-flip** (IC +0.018, net −13.78%). | **[H]** for C5 itself. The IVOL proxy is **[E]** negative. |
| **Carry ↔ CB-N50** | Never measured. But CB-N50's `basis` feature (TRAIN IC +0.056 alone vs +0.059 combined) is a daily, non-dividend-adjusted, median-demeaned version of Carry's raw input on a Nifty-50 subset. Overlap is by construction. | **[E]** structural overlap; **[H]** magnitude. |
| **TS Basis ↔ C5**, **CB-N50 ↔ others** | Not measured | **[H]** |

The matrix measured **additive equal-weight blends only**. It says nothing about conditioning,
state filters or name-intersection funnels. Those remain untested, not refuted.

---

## 3. Does CB-N50 condition Carry returns?

**No evidence exists either way [H].** No report conditions Carry's IC or spread on any CB-N50
quantity. Three structural facts make it a poor candidate before any test [E]:

1. **Breadth is mechanically near-constant.** Every feature is cross-sectionally demeaned, so
   about half the names score above zero every day.
   - TRAIN breadth: mean 0.540, SD ~0.07. It fired 5.1% of days, with inverted direction
     (LONG −2.4 bp, SHORT +49.4 bp on n = 2).
   - A market-neutral score carries no information about the market (`CB_N50_TRAIN_REVIEW.md`).
   - So CB-N50 is not a market or context filter. It never predicted Nifty futures either: G4 was
     deliberately not evaluated.
2. **Horizon mismatch.** CB-N50's validated object is a **one-day open-to-open** stock IC. A
   month-end value of it, used to gate a one-month hold, discards all but one day of its decay
   window. Nothing in the repo says a one-day cross-sectional signal carries monthly state
   information.
3. **Circularity.** Its dominant feature is basis. "Filter Carry on CB-N50" therefore partly
   means "filter basis on basis." A conditional effect found this way could not be read as
   independent context.

---

## 4. Do TS Basis or C5 add information beyond Carry?

- **TS Basis: probably little [I].**
  - IC correlation is +0.53, and the additive blend loses (lift 0.986).
  - The honest out-of-sample effect is HOLDOUT IC +0.041, which failed its own α.
  - Its sealed number is the favourably selected read and must not be used for planning
    (`TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` §A.5).
  - The right question is a *residualised* one: does TS Basis orthogonalised on Carry still rank
    returns? That has never been computed. It is **[H]**, and in-sample it could only kill, never
    confirm.
  - In a funnel (intersecting Carry Q5 with TS-high), ρ 0.62 means the second screen mostly
    re-selects Carry's own extremes. The book gets narrower, idiosyncratic variance rises, and
    little new information comes in.
- **C5: unknown on this universe [H], with an unfavourable prior [I].**
  - Raw 252-d total vol is heavily beta-loaded, and Carry is beta-neutralised. Conditioning Carry
    on C5 reintroduces the exposure Carry's construction removed.
  - The measured cousin (IVOL) sign-flipped out of sample.
  - C5's own IC SD (0.246) is three times Carry's (0.08), so as a conditioning variable it mostly
    adds noise.

---

## 5. Incompatibilities

| # | Issue | Affects | Tag |
|---|---|---|---|
| 1 | **Spot vs futures return.** All Carry and TS Basis evidence (IC, net spread, parity) is spot close-to-close. The book trades futures, which converge to spot: a long rich-basis future pays its residual basis over the month. No report quantifies the Q5−Q1 residual-basis spread, so the gap between spot-measured and futures-realised spread is **unknown**. Paper forward marks use futures (`CARRY_LAST_RECOMMENDATION_REPORT.md`), so paper and research are not measuring the same quantity. | Carry, TS Basis | [E] mismatch, [H] size |
| 2 | **Sign rationale.** v2 §1 defends "long high basis" as the canonical Koijen–Moskowitz–Pedersen–Vrugt (2018) carry direction. That paper defines futures carry as ≈ (S−F)/F, so a high F−S basis is *low* carry, which is v1's sign. **Operator to confirm against the paper.** If correct, the effect is real (spot IC [E]) but its economic story is demand pressure or momentum, not carry. That matters for #1: a demand-pressure premium earned in spot may be partly paid away in futures convergence. | Carry, TS Basis | [H], needs confirmation |
| 3 | **Survivorship-type filter.** `fwd_ret_1m IS NOT NULL` gates cross-section membership at *t* (Carry research, all of TS Basis). This conditions on next-month price availability. | Carry, TS Basis | [E] present, [H] size |
| 4 | **TS Basis cannot score a live formation.** `build_ts_signals.py:66-69` requires `fwd_ret_1m IS NOT NULL`, which is NULL at every live formation, so no forward z_ts can come from this builder. `CARRY_TSBASIS_FORWARD_BUILD_REVIEW.md` HIGH-3 flagged the missing forward path. Whether later commits (e.g. `bf3d9d7`) supply another route was not checked. | TS Basis | [E] for the builder |
| 5 | **Reproducibility.** `run_holdout.py` and `run_sealed.py` read `ts_signals.duckdb`, which now holds the **weekly** store (`03fc76a`). The registered monthly store is `ts_signals_monthly.duckdb`. Re-running either script today reads the wrong construct. | TS Basis | [E] |
| 6 | Cadence/horizon: daily 1-day (CB-N50) vs monthly (others) | CB-N50 | [E] |
| 7 | Universe: Nifty 50 (MCWB) vs SSF-ADV vs NIFTY-200 cash; C5 is long-only, so its spread doesn't transfer to an L/S futures book | CB-N50, C5 | [E] |
| 8 | Neutralisation: Carry beta+sector, TS none, C5 raw (beta-loaded) | all | [E] |
| 9 | Dividend PIT: ex-date-known, no announcement date; 1.55% of cells, large when present, disclosed and bounded (`CARRY_DATA_GAP_AUDIT.md` §4) | Carry | [E] bounded |
| 10 | Formation calendar: month-end, not roll; the spurious 2026-07-20 formation class needs its guard kept | all monthly | [E] |
| 11 | Post-CAS basis: TS Basis Daily now prices spot at the continuous close (last bar before 15:15). Monthly Carry uses the official (auction) close against a futures close that trades until 15:40. Two basis definitions now coexist for forward data. | Forward data only | [H] size |
| 12 | CB-N50 breadth weights: one-month-lagged bulletin requirement flagged open at TRAIN review | CB-N50 | [I] |

---

## 6. Role of each input

| Input | Recommended role | Why |
|---|---|---|
| **Carry** | **Sole alpha anchor**, pending #1 and #2 | The only construct with a clean TRAIN→HOLDOUT→SEALED chain [E]. But "edge in futures P&L" is **[I]** until #1 is measured. |
| **TS Basis** | **Not a funnel stage.** At most a pre-registered *incremental* (residualised) name-level test | Same factor family (ρ(IC) 0.53) [I]; no forward signal path [E] |
| **C5** | **Drop** from this architecture | Wrong universe and instrument, beta-loaded, noisy, unfavourable proxy evidence |
| **CB-N50** | **Reject** as filter and as stage | Breadth is market-neutral by construction; its basis feature is circular with Carry; horizon mismatch |

---

## 7. Is the funnel statistically and economically defensible? No.

**Statistically.** A state filter works by making Carry's IC different across states. The
detectable difference depends on months, not names. Required monthly formations for 80% power,
one-sided α = 0.05 (`scripts/rfa/power.py`, two-group split, state fraction *f*):

| SD(IC) | f | ΔIC 0.02 | ΔIC 0.03 | ΔIC 0.05 |
|--:|--:|--:|--:|--:|
| 0.08 | 0.5 | 398 (33 y) | 178 (15 y) | 65 (5.4 y) |
| 0.08 | 0.3 | 473 (39 y) | 211 (18 y) | 77 (6.4 y) |
| 0.10 | 0.5 | 620 (52 y) | 277 (23 y) | 101 (8.4 y) |

- SD 0.08 is Carry's measured SD(IC) from the matrix; 0.10 is its pre-registered floor.
- At the 42-month length of the spent sealed window, a ΔIC of 0.03 has power **0.33**.
- ΔIC 0.05 is **larger than Carry's entire mean IC (~0.048)**. Only a filter that switches Carry
  fully off in one state and doubles it in the other would be detectable in about 5 years.
- A filter that drops months also cuts T directly (ncp = S·√T). The conditional Sharpe has to rise
  by 1/√f just to break even.

Name-level interactions (Carry IC within TS-high vs TS-low names, paired within each month) do
better but are still slow: 27–156 months for ΔIC 0.05–0.02 at a difference-series SD of 0.10, and
58–350 at 0.15. The SD of that series is unmeasured.

**Economically.** Every stage after Carry either reuses Carry's data (TS Basis, CB-N50 basis) or
reintroduces exposure Carry removed (C5 beta). A funnel also creates free parameters: which state
threshold, which intersection, which quintile. Choosing any of them on 2016–2022 is exactly the
TS Basis Daily failure (selection surfaces, m ≫ 1).

**Budget.**
- SSF 2023-01→2026-07 has been read three times (Carry, TS Basis, IVOL). Any funnel involving Carry
  that reads it is in-sample.
- CB-N50's "preserved" sealed window reuses the same basis data.
- The August 2026 forward Carry formation has already been viewed.
- **The only clean confirmatory data is forward time after a new freeze date.**

**Concentration risk.** In HOLDOUT, Carry's top five months produce 129% of total return
(`CARRY_DRAWDOWN_REPORT.md`). Any in-sample state split is largely a statement about which state
those five months fell in.

---

## 8. What to reject or change before any pre-registration

**Reject:**
- CB-N50 as a market or context filter.
- CB-N50's breadth score in any form.
- Name-intersection funnels (Carry ∩ TS).
- C5 as a conditioning variable on the SSF book.
- Any threshold or state cut-point chosen on 2016–2022 data.
- Any use of the TS Basis sealed figure as an effect size.
- Any composite gate other than the lift-first `composite_gate.py` (LIFT → SIGN → POWER).

**Change first (no signal search; these repair measurement of the anchor):**
1. **Quantify #1.** Descriptively, on TRAIN+HOLDOUT only, measure the Q5−Q1 residual-basis
   convergence per formation. Report Carry's spot spread next to the implied futures spread. This
   is a measurement of an existing, frozen construct, not a backtest variant.
2. **Settle #2 in writing.** Record what the effect is (spot demand pressure vs carry) and what
   that implies for futures P&L.
3. **Fix #5** (point the TS scripts at the monthly store). **Fix or drop #4.** Do not claim TS
   Basis shadow evidence until a forward z_ts exists.
4. **Wire `composite_gate.py` into whatever is registered.** CARRY v1 §13 rule 3 still reads as
   an absolute 0.80 rule.
5. Add an explicit **"Acceptance rule (what authorizes the next window)"** section, per
   `TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` §C.4.

---

## 9. The smallest clean experiment

**Stage A: exploratory kill-screen (non-confirmatory, data fenced ≤ 2022-12-30).** Propose, don't
run yet. Freeze the kill criteria in writing before any query.
- **A1. TS Basis incremental IC.** Per formation, residualise z_ts on z_carry_neut, then compute
  the Spearman IC of the residual. **Kill if the upper 95% CI bound of the mean residual IC
  < 0.02.** An equivalence-style kill, because at 71 months only a bound, not a significance
  test, is informative.
- **No state-split screen.** The CB-N50 conditioning question is already settled without reading
  any data: breadth is market-neutral by construction, the basis feature is circular (§3), and a
  state-filter test cannot be demonstrated forward (§7). An in-sample state split could only
  produce an attractive ΔIC with no legitimate next step, which is the post-hoc temptation the
  repo's C2 guard note warns against.
- Label every Stage A output **"in-sample, cannot confirm."** It can end the line of research,
  never promote it.

**Stage B: confirmatory, forward only.** Only after Q1 (§10) and only if A1 doesn't kill.
- Freeze date F. Monthly formations after F. The August 2026 formation was already viewed and is
  excluded.
- **Testing scheme: fixed sequence.** Test the primary at α 0.05 one-sided. Test the secondary at
  α 0.05 only if the primary passes.
- **Primary: Carry main effect measured against near-month futures returns.** Using the spot IC
  0.048 / SD 0.08 as effect size, power is 0.62 / 0.89 / 0.97 at 12 / 24 / 36 months (α 0.05);
  under a Bonferroni alternative (α 0.025) it would be 0.48 / 0.80 / 0.94. **These are upper
  bounds.** They use the in-sample *spot* IC, and the futures IC is lower by an amount Q1 has not
  yet measured.
- **The horizon N is pinned through the RFA gate after Q1 exists**, using an effect-size band
  defended from the futures-return measurement. It is not pinned now.
- **Secondary:** the A1 residual IC, only if a forward z_ts exists (§5 #4).
- No state-filter test at all unless an effect of ΔIC ≥ 0.05 can be **defended ex-ante** through
  the RFA gate. On §7's arithmetic it will ABANDON.

---

## 10. Recommendation and pre-registration questions

**Architecture.** Replace the funnel with **Carry alone as the anchor**, first re-measured in the
currency it trades (futures), and **at most one incremental, name-level, residualised test**,
confirmed only on forward data. Drop CB-N50 and C5 from this line. Keep TS Basis only as the
residualised secondary test, and only once it has a forward signal path. Don't build state
filters: they cannot be demonstrated on monthly Carry within any horizon that matters.

**Questions to pre-register (in this order):**
1. *Measurement, pre-condition.* On TRAIN+HOLDOUT, what is the mean per-formation Q5−Q1
   residual-basis convergence, and what fraction of Carry's spot spread does it consume?
   (Descriptive, no gate. Frozen before running.)
2. *Primary, forward.* After freeze date F, is the mean monthly Spearman IC of frozen
   `z_carry_neut` against **near-month futures** returns > 0 (one-sided, α 0.05), and is the net
   quintile spread under the canonical futures fee model > 0? Horizon N is fixed through the RFA
   gate once Q1 exists, and the window is read once.
3. *Secondary, forward (fixed sequence).* Only if Q2 passes: over the same months, is the mean IC
   of z_ts **residualised on z_carry_neut** > 0 (one-sided, α 0.05)? Only if Stage A1 did not kill
   and a forward z_ts exists.
4. *Kill rule.* Written before Stage A: the A1 equivalence bound in §9, and the statement that no
   other variant, threshold or state variable will be examined.
5. *Explicitly not asked:* any CB-N50 state filter, any C5 conditioning, any funnel intersection,
   any weight or threshold. Each would need its own RFA with an ex-ante defended effect size.
