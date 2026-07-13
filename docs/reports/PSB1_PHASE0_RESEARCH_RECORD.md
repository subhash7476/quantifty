# PSB-1 — Panel Screening Battery, Increment 1: Phase 0 Research Record

**Document type:** Program research record (Phase 0 — the brainstorm that shaped the program, and the operator decisions that gate it)

**Status:** Phase 0 OPEN — design approved by operator 2026-07-13; protocol freeze (the Phase 0 deliverable) not yet written.

**Date:** 2026-07-13

**Roles (standing, carried from MSRP/CSMP):** Implementation party: DeepSeek V4. Lead Reviewer: Claude (prompts and reviews only — does not implement gate deliverables). Decisions: Operator.

**Predecessor:** CSMP increment 1, CLOSED 2026-07-12 on the verdict `Inconclusive (Not Approved)` (`docs/reports/CSMP_PHASE6_OPERATOR_DECISION.md`). Before that: MSRP, STOPPED at D1 (transmission failure). PSB-1 is the third Knowledge program.

---

## 1. Why this program, why now

CSMP did not fail on the signal. The sealed point estimate was positive and close to dev (net spread +6.19% sealed vs +5.95% dev; mean_IC 0.0279). It failed on **statistical power**: a valid one-sided 95% test on 42 monthly observations was ~41% powered against the program's own point estimate, so "Inconclusive" was the pre-registered modal outcome (~59%) even under the hypothesis that momentum works exactly as well out-of-sample. The gate LB was −0.0147 — not > 0 — and the operator refused to promote a Not-Approved artifact on an encouraging point estimate.

Three lessons are now institutionalized, one per predecessor program:

1. **MSRP → transmission.** A correct forecast is worthless without a transmission to P&L. Choose constructs where the forecast and the trade are the same object (cross-sectional ranking → hold the top of the ranking).
2. **CSMP → power.** A construct must generate enough observations to be provable on the sealed window *before* the expensive phase begins. Power analysis is a pre-commitment artifact, not a post-mortem.
3. **Both → the methodology holds.** Two consecutive programs ended on their pre-committed stop rules rather than on wishful promotion. That discipline is an asset; PSB-1 keeps it and fixes the *sequencing* — rigor was spent on one hypothesis before knowing whether the test could ever clear.

PSB-1's answer: **screen cheap and wide first, then spend the heavyweight pre-registration machinery on the one survivor whose power case is already made.**

## 2. What PSB-1 inherits (unspent substrate)

From CSMP gates (a)–(e), none of it consumed by the sealed read:

| Asset | Detail | Source |
|---|---|---|
| Equity EOD store | 7,030,920 rows, 4,132 symbols, 2010-01-04 → 2026-07-09, **0 coverage holes** vs authoritative calendar | `CSMP_GATE_A_EQUITY_BHAVCOPY_AUDIT.md` |
| Delivery fields | `deliv_qty`, `deliv_pct` present in the SECFULL era: **2020-01-01 onward** (NULL before; NULL on some BE rows, expected) | gate (a) audit §2 |
| Corporate-action layer | 0 undocumented residue across dev *and* sealed windows (VOID precondition passed on unseen data) | gate (b); Phase 6 sealed read |
| Point-in-time universe | NIFTY-200 membership reconstructable at date *t* from information available at *t*; no survivor list as input | gate (c) |
| Delivery-equity fee model | Era-accurate: STT both sides, stamp (buy), NSE txn, SEBI, GST, DP per sell line | gate (d) |
| Panel loader lineage | `load_window()` with the Prompt-13 memory fix (price load restricted to ever-member entities) | `0ae1dc4` |
| Validation machinery | Content-addressed validation records, sealed-fence assertions, deterministic seeded runs, mechanical verdict tables | CSMP Prompts 8–13 |

Also available but **not used by PSB-1**: 1m index/equity candle stores, DayTypeEngine, options analytics, the execution stack. They are out of scope for this increment (see §7).

## 3. Operator decisions (LOCKED 2026-07-13)

Four decisions were put to the operator during Phase 0 brainstorming; all four locked as recommended.

| # | Decision | Locked choice | Rationale recorded |
|---|---|---|---|
| D1 | Rigor allocation | **Screen first, then commit.** A cheap, explicitly-exploratory screening battery over 3–5 declared candidates on dev data, with honest multiplicity accounting; only the survivor enters full CSMP-grade pre-registration. | Power problems get caught before the expensive phase. CSMP discovered its ~41% power *after* five gates and a frozen dossier. |
| D2 | Sealed-data policy | **2023-01→2026-06 is usable as a sealed window for new construct families.** It is spent only for the momentum construct. Any new-family pre-registration that seals it must disclose the one prior momentum read as prior exposure (and may apply an α penalty if strictness is wanted). | One read of one unrelated statistic leaks almost nothing; the alternative (forward-only data) delays any confirmation by 1.5–2 years. Momentum-family constructs remain banned from this window outright. |
| D3 | Cadence | **Weekly-centered, test both ways.** Screening runs primarily at weekly cadence (~180 sealed observations vs CSMP's 42); each candidate declares its natural cadence; a power projection is a mandatory per-candidate artifact. | Weekly buys ~4× the observations of monthly while delivery-equity turnover remains survivable. The power calculation is now structural, not remembered. |
| D4 | Data scope | **Existing panel only.** Candidates must be computable from the current equity store (+ delivery fields). No new ingestion this increment. | Zero ingestion cost; screening starts immediately on a CSMP-audited substrate. The delivery fields are the freshest untapped asset already inside it. |

### D5 — Unadjusted corporate actions in the scored panel (LOCKED 2026-07-13, post-freeze, **pre-result**)

Raised by the second Lead Review (`PSB1_PHASE1_LEAD_REVIEW_2.md`). The harness's panel reads
`equity_bhavcopy_adjusted` unfiltered, and it contains **~18 unadjusted corporate-action
moves** inside the ever-member universe on the dev window — every one a large *negative*
move (BAJAUTOFIN −99.0%, AURUM/ex-MAJESCO −98.8%, ADANIENT −82.8%, SHRIRAMFIN −79.8%, …),
mostly demergers and special capital returns that gate-(b) never adjusted **by charter, not
by bug** (its scope was splits/bonuses/rights). Because C1 scores `s = −r(t−5,t)`, a
fabricated −99% return is the *highest possible* C1 score — the name goes straight into the
top-quintile long book on a move that never happened. C2/C4 inherit it; C5 sees an inflated
252-day σ.

| # | Decision | Locked choice | Rationale recorded |
|---|---|---|---|
| D5 | Unadjusted CAs in the panel | **Missing input under the §4.1 formation-complete rule.** A price-derived input window that spans an unadjusted corporate action is an **absent input**: the name is simply not scorable across that window, exactly as if a price were missing. No new parameter is introduced. | §4.1 already excludes names whose required inputs are absent, and an adjusted price that does not describe a continuous claim on the same asset **is** an absent input. The alternatives were rejected: documenting the rows in `ca_scope_exclusions` clears the *gate* without cleaning the *data* (the −99% would still be scored), and adding demerger factors is new adjustment work plausibly barred by **D4**. |

**§9 status:** recorded as an *interpretation* of the frozen §4.1, not an amendment — no
candidate definition, parameter, window, or metric changes. It nonetheless moves results,
so it is locked **before any candidate result exists**, which is the only moment it can be
settled for free. The affected `(entity, move_date)` rows are carried in a register and
reported. Implementation semantics are pinned in **Prompt 1-B** (§"D5 disposition") — the
implementer must not resolve any of its edges in code.

## 4. The central research insight — `deliv_pct`

NSE is one of the very few major exchanges that publishes **daily per-stock delivery data**: the fraction of traded volume actually taken to demat (real position-taking) versus intraday churn. The US market has no equivalent public field; it barely exists in the international factor literature. Indian academic work finds delivery-based measures predict returns — high-delivery price moves read as informed accumulation; low-delivery moves read as noise that tends to revert.

This field was ingested and audited to CSMP standard at gate (a) and **never used by any program**. It is the comparative advantage of this repository's data substrate and the anchor of the PSB-1 slate.

**Honest caveat, recorded up front:** delivery fields exist only from 2020-01-01 (SECFULL era). Delivery-based candidates therefore screen on a **2020–2022 dev window** (~150 weekly cross-sections × ~200 names), not the full 2012–2022 window available to price/volume candidates. That is still an order of magnitude more effective observations than CSMP's 42 sealed months, but the two dev windows must not be compared as if equal — the protocol freeze must state how cross-candidate comparison handles this (e.g., compare on the common 2020–2022 sub-window as a robustness column).

## 5. The candidate slate (5, declared now; formulas pinned at protocol freeze)

| # | Construct | Natural cadence | Dev window | Rationale |
|---|---|---|---|---|
| 1 | **Short-term reversal** — cross-sectional rank of trailing ~1-week return, long losers / measure spread | Weekly | 2012–2022 | The strongest documented weekly panel effect internationally. Fees are its known killer; the gate-(d) model decides its fate honestly rather than by assumption. |
| 2 | **Residual reversal** — reversal computed on market-stripped (residual) returns | Weekly | 2012–2022 | Same family; literature reports roughly half the turnover for similar gross spread — the fee-survivable variant. Declared separately so the reversal-vs-residual choice is not a silent post-hoc fork. |
| 3 | **Delivery-percentage anomaly** — rank of `deliv_pct` level and/or abnormal delivery vs own history | Weekly | 2020–2022 | The India-specific informed-flow proxy (§4). |
| 4 | **Delivery-conditioned reversal** — reversal signal gated by delivery: revert low-delivery moves, don't fight high-delivery moves | Weekly | 2020–2022 | The interaction bet and the genuine novelty: uses delivery to separate noise moves (revert) from informed moves (persist). |
| 5 | **Low-volatility** — trailing volatility rank, buffered rebalancing | Monthly | 2012–2022 | Low turnover, strong Indian evidence (NIFTY LowVol 30 index live for years). The fee-lightest fallback; its monthly cadence makes its power hurdle the hardest to clear, and that is a fair test of the D3 discipline. |

**Excluded by decision:** anything momentum-family (including 52-week-high proximity, George & Hwang). The CSMP closure binds future momentum work to fresh forward data with a new pre-registration; a "different but momentum-adjacent" construct on the 2023–2026 window would spend credibility, not alpha. Recorded so the exclusion is a fence, not a memory.

## 6. Screening design — the chosen approach and the rejected ones

**Chosen — A: Pre-registered screening battery.** One protocol document, written and Lead-Reviewed **before any candidate code runs**, containing:

- the five candidate definitions with exact formulas — no free parameters left implicit; a candidate that needs its formula "fixed" after seeing results is dead for this increment (re-enterable in a future battery);
- universe: point-in-time NIFTY-200 (gate-c artifact), no exceptions;
- metric: weekly cross-sectional rank IC **and** net top-quintile spread under the gate-(d) fee model (+ slippage convention carried from CSMP);
- dev windows per candidate as in §5, plus a common-sub-window robustness comparison (§4 caveat);
- the selection rule: **at most one winner**, chosen by the maximum multiplicity-deflated statistic across the five declared candidates — the deflation method named in the protocol, not chosen after results exist;
- the **power hurdle**: a candidate advances only if its dev effect size projects **≥ 80% power** for a one-sided 95% gate on the 2023–2026 sealed window at its natural cadence. A beautiful dev IC with a failing power projection is a **drop**, by rule.

**Rejected — B: Sequential deep-dives** (one candidate at a time, full exploratory treatment each). Richer per-candidate understanding, but by the third candidate the analyst has made a hundred silent decisions and the multiplicity accounting is fiction — the garden of forking paths.

**Rejected — C: Factor-zoo sweep** (30–50 signals, rank or ML-combine). Torches the thin-vertical-slice principle; with ~50 candidates the deflation penalty exceeds any effect size Indian equities have plausibly shown; unfalsifiable in practice.

## 7. Program structure and boundaries

**Phases:**

- **Phase 0 — Protocol freeze.** Write the screening protocol (§6 contents), Lead Review, freeze. *This document is Phase 0's research record; the protocol is Phase 0's deliverable.*
- **Phase 1 — Screening harness.** DeepSeek V4 builds one harness against the existing panel loaders (the `load_window()` lineage with the Prompt-13 memory fix). Reviewed and dev-proven on synthetic data before touching real candidates.
- **Phase 2 — The battery run.** All five candidates run identically through the frozen protocol; one report per candidate; no peeking-driven tweaks.
- **Phase 3 — Selection report + operator decision.** Ranked results, deflated statistics, power projections. Operator chooses: promote the winner to a full pre-registration (a **new** program, not a PSB-1 continuation), run a second battery, or stop.

**Boundaries (what PSB-1 is not):**

- **No sealed read.** 2023-01→2026-06 stays untouched; PSB-1 only earns the right to spend it. The sealed window is consumed, if ever, by the successor pre-registration program.
- **No consumer, no strategy code.** Nothing lands in `core/strategies/`; no PaperBroker wiring.
- **No new data ingestion** (D4).
- **No momentum-family constructs** (§5).
- **Everything exploratory is labeled exploratory.** No PSB-1 output may appear in Approved / Deployable / certified language.

**Artifacts:** all reports land as `docs/reports/PSB1_*.md`, in the CSMP mold (audited reports, Lead Reviews, operator decisions as separate documents).

## 8. Next actions

1. Claude drafts the **PSB-1 screening protocol** (`docs/reports/PSB1_PROTOCOL.md`) with the §6 contents, including pinned formulas for all five candidates and the named deflation method.
2. Lead Review of the protocol; operator ratifies; protocol **FROZEN**.
3. Claude writes Prompt 1 (screening harness) for DeepSeek V4; Phase 1 begins.
