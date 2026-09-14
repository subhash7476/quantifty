# PTMS — what experiment was the Nifty-100 PIT work preparing?

**Date:** 2026-09-14 · **Type:** governance / research-history audit.
**Scope honoured:** no outcome data read, no RFA, nothing frozen, PTMS-G-PTSQ unmodified, no
hypothesis designed, no parameters, TRAIN/HOLDOUT unchanged, no infrastructure built. The one
computation was a meta-level comparison of symbol lists: vendor 1m file names against PIT N100
members.

**Method.**
- **Transcript search.** A keyword search of every operator and assistant message in the session
  transcript (`982e8e90…jsonl`) between 2026-09-12 16:00 IST and 2026-09-13 22:10 IST. Terms:
  Gann, price-time, Family F, cross-section, rank-IC, stock-level, breadth, "test", "construct".
- **Repo read.** The PTMS reports, commits, register (current and at `385bd99`) and the P3
  catalogue.
- **Time bounded.** Evidence is used as it stood at the time; later options work is excluded (§11
  of the request).

**Stated limits.**
- **Operator rulings partly drafted in ChatGPT.** Some operator rulings were drafted in an external
  ChatGPT conversation (#7).
- **Membership builds done by another model.** The N200 and N100 membership builds were done by
  another model on the operator's instruction (#21, #24). Neither conversation is in the repo.
- **Rationale outside the record.** If the experiment was described there, this audit cannot see
  it. Wherever something is "not established" below, it means not established from the repo and
  this transcript. It does not mean no intention existed.

---

## A. EXECUTIVE ANSWER

> **YES — reasonably supported but not formally recorded** for *price-time structure tested across
> Nifty-100 stocks*.
> **NOT ESTABLISHED, but not contradicted,** for the *Gann-specific* part.

**Why "yes" for price-time on N100 stocks:**
1. **Family F is price-time on stocks by definition.** The only PTMS family that ever needed a PIT
   stock universe is **Family F, "Genuine stock-level cross-sectional Price-Time hypotheses"**
   (operator ruling #3, 09-12 13:49 IST). Its catalogue definition is "a price-time construct
   predicts the cross-section of stock returns" (`e9a4cd9`).
2. **The PIT work was aimed at F's blocker, in the operator's own words.** A1 — the circular
   `pit_membership` table — was *F's* substrate blocker. The operator tied the two together:
   "A1 `pit_membership` circularity: FAIL — permanent blocker; **Family F remains unavailable**"
   (#15, 17:39 IST). Nineteen minutes later the operator started the membership work "**so that we
   can solve the A1 problem**" (#16).
3. **The operator stated the test's scope.** "Use only nifty 100 **stocks** for **this test**"
   (#24) and "fix the **1m** coverage gap for nifty 100" (#26) are direct: a test on Nifty-100
   stocks, using 1-minute bars.
4. **The assistant framed it as F, and the framing stood.** I described it as a "Nifty-100
   cross-sectional intraday study" (`6c2ceb7`). In the A6 commit I wrote that the fence forecloses
   "**Family F's** normalization option" (`e3c8f8d`). The operator never corrected either framing.

**Why the Gann part is not established:**
1. **The word never appears.** "Gann" appears in no operator or assistant message anywhere in the
   PIT phase (09-12 16:00 → 09-13 21:44 IST).
2. **No experiment was written down.** "This test" and "this construct" are never defined.
3. **The formal record assigns Gann to the index.** The rulings put Gann on the index as a
   single-index test (#3 §4). Gann applied *per stock* with a cross-sectional outcome would
   therefore have been a **Family F candidate**, which the same ruling permits "only if it is
   genuinely a stock-level hypothesis in its own right". The record makes the operator's belief
   **admissible**, not **documented**.

---

## B. WHAT WE WERE ACTUALLY BUILDING

### B.1 Plain-language reconstruction

We were preparing a **Family F experiment**. It would be a price-time construct computed per stock
from intraday bars across the **point-in-time Nifty-100**, with a **cross-sectional outcome**
(stocks ranked against each other on each formation date).

Four things stood in its way, and every one had to be fixed before the experiment could mean
anything:
- **No trustworthy universe.** The panel had no PIT universe at all (A1).
- **Missing large caps.** The 1m store was missing about 11 constituents per session (`6c2ceb7`).
- **An unproven clock.** The timestamp convention was unproven (C1).
- **Unmarked synthetic bars.** Post-CAS carry-forward bars were unmarked (C3).

**What was never written:**
- the construct;
- the origin rule;
- the price/time normalization;
- the horizon;
- whether it was Gann geometry, price × elapsed time, or another price-time form;
- its multiplicity.

### B.2 Stage-by-stage: operator belief, assistant statement, repo definition

| Stage (IST) | Operator appeared to believe | Assistant said | Repo formally defined | Aligned? |
|---|---|---|---|---|
| **Charter** 09-12 13:37 | A battery; first family price-time structure, on the index (§10) | Alignment record: single-index `per_trade_pnl` is structurally dead; "the same geometry expressed as a daily cross-sectional rank-IC over the ~190-name panel is the only shape that can plausibly clear the gate", but only if genuinely stock-level; asks the operator to choose (Q4) | Alignment record `da7b3c6` (a proposal) | **Partly.** The cross-sectional reading of the geometry question originates with the assistant |
| **F created** 09-12 13:49 | "Gann = SINGLE-INDEX per_trade_pnl"; F = "Genuine stock-level cross-sectional Price-Time"; stock-level price-time allowed "only if genuinely stock-level in its own right" (#3) | Catalogue F: per-name price-time statistic, cross-sectional rank, forward return, eligibility via `pit_membership` | Catalogue `e9a4cd9`: F **CONDITIONAL** | **Yes** |
| **F removed** 09-12 16:06–16:21 | "Family F is now SUBSTRATE-BLOCKED … remove it from the list of potentially executable families. Do not attempt to rescue it without an independent PIT universe" (#11) | "Remedying it requires an independent PIT universe … built and certified" (`a41d033`) | Catalogue F **SUBSTRATE-BLOCKED (permanent)** (`4dd3525`) | **Yes** |
| **A1 pursuit / N200** 09-12 17:31 → 23:58 | Thinks in Nifty-200 terms ("outside Nifty200 universe", #14); "Family F remains unavailable" (#15); commissions N200 membership "so that we can solve the A1 problem" (#16, #19, #21) | N200 "cannot solve A1": A1 concerns the ~190-name F&O-shaped intraday panel, not N200 (`1038e96`, `63e44f4`, `5bf9971`). Build review: "partial progress … does not unblock Family F" (`74a8f46`) | Nothing new; F stays removed | **No.** The operator was building the remedy the F ruling named; the assistant was judging it against the existing panel's universe; the repo still read F as removed |
| **N100 decision** 09-13 13:45 | "use only nifty 100 stocks for this test" (#24) | "your Nifty-100 test would currently run on ~89 of 100 names"; "a Nifty-100 cross-sectional intraday study"; "breadth, dispersion or L/S construct" (`6c2ceb7`) | No test defined; A1 "satisfied for the Nifty-100 scope by substitution" | **Partly.** The assistant supplied "cross-sectional intraday" and the operator did not object. Neither party named a construct |
| **Backfill + certification** 09-13 14:11 → 21:40 | "fix the 1m coverage gap for nifty 100" (#26); "sector membership is not needed for this construct" (#51); "certify it, scoped to nifty 100" (#58) | Fence treated as F's: "Family F's normalization option is foreclosed here" (`e3c8f8d`); construct disclosures phrased for a cross-sectional book ("top-quintile", "spread") | Certificate for a **surface** (`ab700e7`): "certifies what the bars are, not that a construct…" | **Implicitly.** Operator and assistant spoke of one construct; the repo holds only the surface |
| **Reconciliation** 09-13 21:44 → 22:00 | "Now that PTMS N100 substrate is operator-certified … reconciliation for all seven PTMS families" (#59) | F: "substrate unblocked today, budget-blocked", same hypothesis class as ISD, MRLC multiply selected; recommends stopping MRLC "if F is ever to have a confirmatory window" and forward paper "if F is wanted"; G recommended (`2980acc`) | Reconciliation disposition (not a ruling) | **On facts, yes.** The operator acted on G and on stopping MRLC; F received no ruling |

### B.3 Was the certified N100 surface capable of the intended experiment? (§5 — no outcomes)

| Requirement | Status | Evidence |
|---|---|---|
| Per-stock historical price path | **Yes, 2023-01-02 → 2026-09-11 only.** Continuous 1m bars per name. **Corporate-action adjusted**, so the path is continuous across ex-dates, which a price-time origin needs | Certificate `ab700e7`; `4208278` |
| PIT membership applied per date | **Yes.** Independent of the candle store; 100/100 map to store keys. Four event dates are fixed only to ±30 days (immaterial for monthly formations, material for daily) | `6c2ceb7` §2, §4 |
| Observations assigned to the right stock and date | **Yes, with obligations:** native start-labelled clock resolved from the observed first bar; `is_synthetic = FALSE`; HDFC pinned at 99/100 for 130 sessions; 4 GAP sessions declared | Certificate §5; `bar_labeling.py` |
| Cross-sectional breadth | **99–100 names per session.** Twice CB-N50's 50 names; half ISD's ~190 | Census, `999bb9f` |
| Suits the price-time structures the charter contemplated | **Partly.** Intraday to multi-week constructs, per-stock origins, and normalized price/time scales are computable. **Not supported:** anything needing sector neutralization (A6 scoped out); multi-year cycles or long-horizon origins (3.7 years, one macro regime, with lookback warm-up eating the start); anything before 2023 | A6 §10; certificate §6 |

**In principle the surface could carry a stock-level price-time experiment.** Its limits are the
length of history and a single market regime, not integrity.

### B.4 How much history there really was (§6)

| Surface | Physical span | Certified for PTMS? | PIT N100 overlap | Notes |
|---|---|---|---|---|
| **Canonical 1m, stocks** (`NSE_EQ`) | **2023-01-02 → 2026-09-11** | **Yes, N100 scope** | **2023-01-02 → 2026-09-11** | Before the 13-09 backfill, ~11 N100 names per session were absent |
| Canonical 1m, index | 2012-01-02 → present | No (C1 vendor-era open) | n/a — two index symbols, no stocks | **The source of "we have 1m data from 2012". It is index data, not stock data** |
| **Vendor 1m** (`1m_vendor/`) | 2015-02-02 → 2025-08-06, 100 per-symbol files | **No** — store map: "provenance only", different schema, never stitch | 99 of the 100 files are ever-N100 names, **but they are a near-present list:** on 2015-02-02 only **56 of that day's 100 PIT members** have a file; on 2025-08-01, **99 of 100** | **Survivorship-shaped.** Read by the MRLC archive test (`2980acc` §1.2) |
| Equity EOD (bhavcopy / adjusted view) | 2010-01-04 → present, **daily only** | No PTMS certification; adjusted view certified by the PSB-1 contract suite | 2011-03-25 → present, physically | Daily, not intraday. Signal-level reads ≤ 2022-12-30 by PSB-1/PSB-2 (Q-1/Q-2) and 2011–2018 (Q-3), on a Nifty-200-style universe |
| **PIT N100 membership** | **2011-03-25 → present**; monthly MCWB gate 2010-01 → 2026-07 | Accepted (review `6c2ceb7`) | — | Membership exists **12 years before** the stock 1m data does |
| PIT N200 membership | 2011 → present; exact from 2018-06-29 | Reviewed, not adopted | — | Superseded by N100 for the test |

**The overlap that matters:** PIT N100 membership ∩ certified stock 1m = **2023-01-02 → 2026-09-11,
about 3.7 years.** PIT-correct Nifty-100 **1-minute** data does not exist before 2023 in any
certified store.

---

## C. EVIDENCE TABLE

Strength scale: **DIRECT** · **STRONG INFERENCE** · **WEAK INFERENCE** · **NOT ESTABLISHED**.

| Date (IST) | Evidence | What it indicates | Strength |
|---|---|---|---|
| 09-12 13:48 | Alignment record §7 L5: geometry "expressed as a daily cross-sectional rank-IC over the ~190-name panel is the only shape that can plausibly clear the gate", with the stock-level caveat; Q4 asks single-index or cross-sectional | The idea of carrying the geometry/price-time question to a stock cross-section enters the record, from the assistant | **DIRECT** (idea exists) · **STRONG INFERENCE** (seed of the operator's model) |
| 09-12 13:49 | Ruling #3: Gann pinned to single index; F = "Genuine stock-level cross-sectional Price-Time hypotheses"; stock-level price-time "only if genuinely stock-level in its own right" | A stock-level price-time family exists and is distinct from Gann-on-index | **DIRECT** |
| 09-12 15:16 | Catalogue F: "A price-time construct predicts the cross-section of stock returns"; eligibility `pit_membership` | F needs a PIT stock universe | **DIRECT** |
| 09-12 16:06–16:18 | C2-A1 fails; ruling #11: F substrate-blocked "unless an independent PIT universe is subsequently sourced and certified" | The PIT universe is F's blocker | **DIRECT** |
| 09-12 17:31 | #14: "they are outside Nifty200 universe" | The operator's working universe frame is Nifty-200 | **WEAK INFERENCE** |
| 09-12 17:39 | #15: "A1 … permanent blocker; Family F remains unavailable" | The operator ties A1 to F explicitly | **DIRECT** |
| 09-12 17:58 | #16: verify a Nifty-200 list "so that we can solve the A1 problem" | PIT work begins to solve A1, which is F's blocker | **DIRECT** (A1) · **STRONG INFERENCE** (purpose = F) |
| 09-12 18:22 → 22:51 | #19 "does this solve your PIT membership issue"; #21 "see whether A1 is satisfied" | Same objective, pursued through N200 | **DIRECT** |
| 09-13 13:45 | #24: "i have decided to use onlu nifty 100 **stocks** for **this test**" | A specific test on N100 stocks exists in the operator's plan; its content is unstated | **DIRECT** (a test) · **NOT ESTABLISHED** (content) |
| 09-13 13:54 | Assistant: "your Nifty-100 test"; "a Nifty-100 cross-sectional intraday study"; "breadth, dispersion or L/S construct" (`6c2ceb7`); not corrected | Shared understanding of a cross-sectional intraday test | **STRONG INFERENCE** |
| 09-13 14:11 | #26: "fix the 1m coverage gap for nifty 100" | The test uses 1m bars of N100 stocks | **DIRECT** |
| 09-13 19:40 | #51: "sector membership is not needed for this construct" | A defined-enough construct existed in the operator's mind; it is not sector-neutral | **DIRECT** (existence) · **NOT ESTABLISHED** (content) |
| 09-13 19:45 | Assistant A6 commit: "Family F's normalization option is foreclosed here"; not objected to | The fence was being treated as Family F's | **STRONG INFERENCE** |
| 09-13 21:44 | #59: "Now that PTMS N100 substrate is operator-certified … all seven PTMS families" | The N100 work was PTMS family work | **DIRECT** (PTMS) · **STRONG INFERENCE** (F) |
| 09-13 22:00 | #61: "stop/disable the MRLC paper scanner so it makes no further signal-level reads", following `2980acc`'s "if F is ever to have a confirmatory window, the scanner has to stop first" | F's future window was deliberately preserved | **WEAK INFERENCE** (F kept alive) |
| 09-12 16:00 → 09-13 21:44 | Transcript search: **"Gann" appears in no operator or assistant message** | No contemporaneous record ties Gann specifically to the N100 test | **NOT ESTABLISHED** |
| — | N100 store written to `data/isd/` beside the ISD `pit_universe` table | Location follows the table it replaced; could equally hint at an ISD-style intraday cross-section. Does not discriminate | **WEAK INFERENCE**, ambiguous |

**Alternative readings the record does not exclude.**
- "This test" could have been a non-Gann price-time construct (for example price × elapsed time per
  stock).
- It could have been an ISD-style intraday cross-sectional test, with no price-time content at all.

Nothing contemporaneous rules either out. Nothing contemporaneous supports either over the operator's
stated belief.

---

## D. WHY PIT MEMBERSHIP WAS NECESSARY

**Historically, at the moment the work started (09-12 17:58 IST):**

- **(A) The problem it was explicitly meant to solve.** A1: the breadth-1m surface had no
  non-circular PIT universe (#16 "solve the A1 problem"). Under ruling #11, that alone kept
  **Family F** off the executable list.
- **(B) The experiment the conversation implied it would enable.** A Family F experiment on the
  breadth-1m panel. The operator's own status note (#15) pairs A1 with "Family F remains
  unavailable". No other PTMS family depended on A1:
  - A–E are index families;
  - G uses no stock universe;
  - the catalogue's only `pit_membership` consumer is F.
- **(C) What the operator explicitly said.**
  - "so that we can solve the A1 problem" (#16);
  - "does this solve your PIT membership issue" (#19);
  - "see whether A1 is satisfied or not" (#21);
  - then, on 09-13, "use only nifty 100 stocks for this test" (#24) and "this construct" (#51).

**What "this test" most likely meant, from contemporaneous evidence only:** a Family F-type
experiment on Nifty-100 stocks using 1m bars, with a cross-sectional outcome.
- The operator stated the universe, the 1m grain, and "not sector-neutral".
- The assistant supplied "cross-sectional intraday", uncorrected.
- The only family the work could unblock was F.
- **Whether its construct was Gann geometry specifically cannot be established.**

**Was it necessary?** For the direction being pursued, **yes**. A stock cross-section cannot be
tested honestly on a universe derived from the files being tested (A1's circularity), and the
backfill then showed the store lacked ~11 constituents per session. Without the PIT universe that
hole was **unmeasurable**. The only alternative on record was a per-date F&O-eligibility universe
from `futures_bhavcopy` (`1038e96`). It was never commissioned, and it would have defined an F&O
universe, not the Nifty-100.

**What the historical record also shows (not hindsight):**
- **The budget question was on record but not adjudicated before the build.** Register v1
  (`385bd99`, 09-12 13:54 IST) already recorded E-1/E-2 (ISD, cross-sectional, signal,
  2023-01-02 → 2024-11-30) and E-3 (MRLC, signal, "2023-01-01 → present").
- **The catalogue flagged the need.** F's catalogue row said its window "must be negotiated against
  the register, not assumed".
- **The adopted phase order put it after the build.** Reconciliation came after P2 certification
  (#9, #10), so the build proceeded while that negotiation was pending.
- **The full extent of MRLC's read was not yet known.** 229 symbols, multiple parameters, a live
  scanner — measured only after certification (`2980acc`).

---

## E. WHY N100 WAS CHOSEN

**Why N200 first — documented:**
1. **The operator's frame was already Nifty-200.** #14 dispositions defective names as "outside
   Nifty200 universe".
2. **The repo's existing cross-sectional equity universe is Nifty-200-shaped.** `universe_membership`
   is the charter-locked top-200-by-turnover reconstruction used by CSMP/PSB (`a41d033` A6;
   `1038e96`).
3. **The downloadable artefacts were Nifty-200.** The operator's first downloads were the N200
   list and the N200 history CSV (#16, #17).

**Inference:** continuity with the repo's existing equity universe. **Rated WEAK INFERENCE** — no
message states it.

**Why N100 second — the documented statement is only:** "i have decided to use onlu nifty 100
stocks for this test" (#24). **No reason is recorded.**

| Candidate driver | Evidence | Rating |
|---|---|---|
| A scientific property of the intended Gann/price-time experiment | None recorded | **NOT ESTABLISHED** |
| Statistical power | N100 has **fewer** names than N200 (100 vs 200) and than the ~190-name panel, so lower cross-sectional density. **A power motive is contradicted by the direction of the change** | **Contradicted as a power gain** |
| Data availability / clean mapping | The N200 review (`74a8f46`, 09-12 23:09) had just measured the problem: N200 and the 1m panel "neither nested nor congruent", 31–53 N200 members absent from the panel. The N100 review then found 100/100 members map to store keys but ~11 per session had **no bars**. **Clean mapping could not have been known before the choice**, and bar coverage was worse than assumed | **WEAK INFERENCE** (N200's non-fit may have prompted a narrower universe) |
| Verifiability of the membership source | The N100 build gates against MCWB, NSE's monthly archives, which carry the Nifty 50 and Next 50 lists, i.e. exactly N100. MCWB zips were already in the repo on 09-12 (alignment record §4), though how far back they ran then is not recorded; the build extended them to 2010 (`b6cb8f4`). An absolute-state monthly check exists for N100 and not for N200 | **WEAK INFERENCE** — plausible, never stated |
| Assistant/model recommendation | No assistant message recommends N100 before #24. The choice came with a build already delivered by the other model | **NOT ESTABLISHED** for this assistant; the other model's prompt is not visible |
| Liquidity / large caps / execution realism | None recorded | **NOT ESTABLISHED** |

**Documented fact:** N200 was not dropped for a defect. Its defects D1–D5 were fixed that night
(`9493d7e`, `2cbf577`) and N100 was chosen the next morning. **The N100 rationale was never
recorded.**

---

## F. WAS THE N100 GANN EXPERIMENT EVER KILLED?

**No. There is no explicit ruling that the N100 experiment — Gann, price-time or otherwise — is
no longer being pursued.** No operator message, commit, catalogue edit or register row says so.

| State | Did it occur for F / N100? | Evidence |
|---|---|---|
| **Substrate blocked** | **Yes**, 09-12 16:18 IST (#11), **then discharged** for the N100 scope by the certificate (`ab700e7`, 09-13 21:40), which meets #11's rescue condition (`2980acc` §3.2) | Direct |
| **Hypothesis blocked** | **No** — no hypothesis was ever defined to block | — |
| **Budget spent** | **Historically, yes, as a finding** — the assistant's reconciliation (`2980acc` §3.2), resting on register rows E-1/E-2/E-3. That finding is **not an operator ruling**, and the E-3 extent correction is **not appended**. Under **GR-1.3** (appended 09-14), historical windows read at signal level cannot be confirmatory. **Forward calendar time can** | Direct (finding); rule later |
| **Experiment abandoned** | **No ruling** | Absence of record |
| **Research direction changed** | **Yes, implicitly.** #61 (22:00 IST) commissioned Family G certification. At the same moment #61 stopped the MRLC scanner, the action `2980acc` said F needed "if F is ever to have a confirmatory window" | Direct (action); intent not stated |

**How attention moved without a kill.** The reconciliation ranked blockers ("certification is
purchasable, budget is not") and recommended G as "the only one worth spending effort on now". The
operator took **both** of its practical recommendations that evening:
- start G;
- stop MRLC, the step that preserves F's future window.

It took **neither** of its F decisions: forward-paper pre-registration or recording F as closed.
**F was not killed; it was left without a ruling while effort went to G.**

---

## G. WHAT CHANGED AFTER N100 CERTIFICATION?

**Using only what was known on the evening of 09-13:**
1. **21:38 IST** — N100 surface certified (#58).
2. **21:44** — operator asks for a window reconciliation of all seven families against the newly
   certified surface (#59). This is a scheduled phase step: #9 and #10 required reconciliation
   "after P2".
3. **21:51** — reconciliation (`2980acc`):
   - F's substrate is unblocked, but its historical window is consumed by ISD (the same
     cross-sectional price-time class) and MRLC (to 2026-09-02, multiply selected, still running);
     7 sessions look clean and are shrinking.
   - A–E stay blocked.
   - G is blocked only on certification, with two unread index-options windows.
4. **22:00** — operator commissions G certification and stops MRLC (#61).

**Each transition, classified by what changed (§9–§10):**

| Transition | A universe | B instrument | C surface | D mechanism | E outcome | F hypothesis |
|---|---|---|---|---|---|---|
| Charter Gann (index) → Family F (stocks) | ✔ index → stocks | ✔ index → equities | ✔ index 1m → breadth 1m | — (none specified in either) | ✔ index per-trade P&L → stock cross-sectional return | ✔ **distinct family** |
| F on `pit_membership` / N200 → N100 | ✔ | — | — | — | — | — |
| N100 certified → G selected | ✔ | ✔ equities → index options | ✔ breadth 1m → options EOD | ✔ F price-time → catalogue G positioning | ✔ stock return → underlying forward return | ✔ family switch F → G |
| Catalogue G → 09-14 redefinition | — | — | — | ✔ positioning → price × time | ✔ forward return → option P&L | ✔ |
| Redefinition → PTSQ | — | — | — | instantiated (implied-vol overreaction) | instantiated (straddle overlay) | instantiated |

**Did the proposed sequence (§9 of the request) occur?** **Yes, with one correction:**
- **Supported as stated:** PIT build → N100 certification → budget reconciliation → G selected →
  options surface → price-time idea transplanted → PTSQ.
- **Not "F abandoned".** F was **left unruled**, not abandoned.
- **The cross-sectional N100 interpretation is not a documented step.** Its origin is the
  assistant's L5 steer and ruling #3's Family F, and its link to Gann specifically is not recorded.

**The research question changed:**
- **first** at charter → F: a new, distinct family, explicitly created;
- **then** at N100 → G: an implicit direction change by action, not ruling;
- **then** at the 09-14 redefinition (see the programme audit `5db7e65`).

**§10 — N100 versus the NIFTY index: same hypothesis or different?** Under the catalogue and
rulings, **distinct families, not one hypothesis with a different observation architecture.**
- **Family C (Gann):** "a price-time geometric relationship on a single index predicts the direction
  of its subsequent move … no cross-sectional rank-IC manufactured by applying an index rule to the
  equity universe". Label: per-trade P&L.
- **Family F:** "a price-time construct predicts the cross-section of stock returns. Must be a
  genuine stock-level hypothesis." Label: stock forward return, ranked.
- **Ruling #3 §4:** a stock-level price-time hypothesis needs "its own definition, multiplicity
  accounting, RFA and pre-registration".
- **CLAUDE.md's CB-N50 rule:** using stocks to power an index claim is invalid.

So the N100 experiment was **not** a legitimate higher-powered test of the index Gann hypothesis. If
it was Gann, it was **Gann's stock-level cousin: related in idea, distinct in family, slot and
null.**

---

## H. GOVERNANCE STATUS TODAY

**The N100 price-time research question: ALIVE BUT UNFORMALIZED.** It carries one binding
constraint: **its only possible confirmatory evidence is forward calendar time.**

| Candidate status | Applies? | Why |
|---|---|---|
| Alive but unformalized | **Yes — primary** | Operator intent is directly evidenced (#24, #26, #51); the substrate is certified; no hypothesis document exists; no kill ruling exists; its forward window was deliberately preserved (#61) |
| Formally blocked | No | The substrate block (#11) was discharged by the certificate; no other block was ruled |
| Spent | **Historically, yes, for confirmation**, per GR-1.3 on the E-1/E-2/E-3 reads | Not a prohibition (GR-1.1); does not reach sessions after 2026-09-11 |
| Abandoned | No | No ruling |
| Superseded | No | G was commissioned, never declared a replacement for F |
| Unresolved | Partly | Its construct (Gann or other price-time) is unresolved; its existence is not |

**Open nuance, not adjudicated here.** The ~10,000 (session, name) cells backfilled on 09-13 were
**not in the store** when ISD and MRLC read it. They are physically unread observations inside a
signal-read window. Whether that matters to a cross-section that also contains read names is part of
the open file-shaped versus observation-shaped exposure question.

---

## I. WHAT THIS MEANS FOR OUR NEXT DECISION

**Minimum governance decision:** an explicit operator ruling on the **disposition of the N100
price-time question**, recorded append-only. It is one of:
- register it as a Family F candidate — with its confirmatory route necessarily forward — and state
  whether its construct is Gann geometry, which under ruling #3 §4 must be a genuine stock-level
  hypothesis;
- formally close or park it.

Until that ruling exists, the certified N100 surface serves an experiment that is neither alive on
paper nor dead on paper. The Family G decisions already pending (programme audit §J) should not be
taken as if this question were closed.

---

## J. STOP

No outcome reads. No RFA. No hypothesis selection. No parameter selection. No freeze. No
infrastructure work.
