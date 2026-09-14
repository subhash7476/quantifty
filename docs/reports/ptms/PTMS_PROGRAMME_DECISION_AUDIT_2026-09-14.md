# PTMS — programme decision audit: how we got from the charter to PTMS-G-PTSQ

**Date:** 2026-09-14 · **Type:** governance / research audit. No outcome data read, no RFA, nothing
frozen, PTMS-G-PTSQ unmodified, no hypothesis selected, no parameters proposed.

**Evidence base.**
- The 53 commits on `research/ptms-price-time-market-structure` (`da7b3c6` → `7a15a62`).
- Every PTMS report under `docs/reports/index_research/` and `docs/reports/ptms/`.
- `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md`, including its content at `385bd99` and
  `e9a4cd9`.
- `docs/DATA_STORE_MAP.md`.
- The session transcript `982e8e90…jsonl`, which carries the operator's charter and every operator
  message verbatim, with UTC timestamps. Times below are converted to IST.

**Stated limits of the evidence.**
- **Some operator rulings were drafted in an external ChatGPT conversation** (operator message #7,
  09-12 15:09 IST: "what shall I send as reply to Chatgpt").
- **The N200 and N100 membership builds were done by another model** (#21, #24). Its prompts are not
  in the repo.
- Rationale that lives only in those places is **not visible here**. Where this audit says "not
  recorded", it means not recorded in the repo or this transcript, not that no reason ever existed.

---

## A. EXECUTIVE VERDICT

**Why did we end up here?** Because at two points the object of study moved to the surface that was
*available*, not the surface the question required. Neither move was recorded as a change of
research question.

1. **PTMS did not start as one hypothesis.** It started as a programme: a battery of hypothesis
   families, with Gann/price-time on the **index** as the first family. **Options appeared in the
   charter only as a later "derivatives / market-state" family**, and as a *trading-layer* choice
   that the charter explicitly said not to jump to (§17).
2. **The N100 PIT effort served Family F**, a stock-level cross-sectional family. F was **introduced
   on day one by the operator's ruling, following a steer in the assistant's alignment record**
   (cross-sectional `rank_ic` is the only shape that clears the power gate).
   - F was ruled **removed** at 16:18 IST on 09-12 unless an independent PIT universe was sourced.
   - The operator then set out to source one. **No F hypothesis was ever written down.** The
     operator referred to "this test" and "this construct", but neither is defined anywhere in the
     repo or transcript.
   - The ~28 hours of PIT work certified a surface whose confirmatory budget turned out to be
     already spent (ISD, MRLC). The register had recorded both reads *before* the PIT work began;
     their full extent was pinned only afterwards.
3. **The move to options was a budget decision, not a scientific one, and it came from the
   assistant's recommendation.** The P3 reconciliation (`2980acc`, 21:51 IST 09-13) found every
   family blocked except G, whose only blocker was "purchasable" certification, and recommended G.
   Nine minutes later the operator commissioned Family G certification. **No economic reason for
   options is recorded.**
4. **The price-time question was then carried onto the options surface.** The P3 prompt
   (13:20 IST 09-14) defined Family G as "NIFTY INDEX-OPTIONS EOD · Price × Time × Market-Structure"
   with an **option outcome**. The catalogue's Family G is **derivatives positioning** predicting a
   **forward return**, with a mandatory price-only control. The prompt changed the family's
   mechanism and label **without recording that a change was being made.** PTSQ was then designed
   by the assistant to fit that surface's constraints.

**Research-surface drift occurred, and the evidence for it is strong.** It is not misconduct: every
step was individually governed and documented. What is missing is a record, at each surface change,
that **the question had changed**. The single-index power wall that made the Gann family "likely
ABANDON" on day one (alignment record §7 L5; catalogue C row at `e9a4cd9`) applies unchanged to
PTSQ, on a shorter window.

## B. ORIGINAL PTMS HYPOTHESIS

**Earliest explicit proposal.** The operator's charter, "PROJECT BRIEF — PRICE × TIME × MARKET
STRUCTURE RESEARCH", 2026-09-12 13:37 IST (transcript message #1). It is not committed as a file;
its first repo trace is the alignment record `da7b3c6` (13:48 IST), which responds to it section by
section.

| Question | What the charter actually says |
|---|---|
| What were we trying to test? | **Not one hypothesis.** A "research battery" to discover whether price, time, price×time relationships, cross-market structure and derivatives/market-state data carry genuine out-of-sample predictive information (§1). **First family: PRICE–TIME STRUCTURE** (§10: time alone, price × elapsed time, Gann-style geometry, temporal cycles, interactions). Second: cross-market, starting Nifty↔Bank (§11). Third: derivatives/market-state (§12) |
| Stated economic mechanism | **None.** Gann concepts are listed as "hypotheses, not facts" (§2A). No mechanism is proposed for any family |
| Intended market / instrument | Index: "2012 → 2024-10-16 = index-pair intraday research only" (§4); Nifty↔Bank (§11); EOD options/futures/OI "where appropriate" (§12). **Options as a traded instrument are explicitly downstream:** "Do NOT jump to options implementation before the underlying signal itself has demonstrated edge" (§17) |
| Intended observation unit | **Not specified** |
| Intended outcome | "Future market behavior" (§1); for derivatives, "future **underlying** behavior" and "price vs price + derivatives" (§12) |
| Data surface required | 1m index pair (2012→), 1d cross-index (2016→), EOD derivatives. The charter believed equity breadth began 2024-10-17 and called it "too short / regime-limited for many proper TRAIN/HOLDOUT experiments" (§4) |
| Why N100 / PIT was needed at that point | **It was not.** §9 states a general rule, "For equity research use … PIT universe membership where applicable." No charter family is a stock cross-section |
| First established by | Charter (#1, 09-12 13:37 IST) → alignment record `da7b3c6` (13:48) → operator ruling "PTMS ALIGNMENT" (#3, 13:49) → P3 catalogue `e9a4cd9` (15:16), accepted in #9 (15:36) |

**The premise "we started PTMS to test a hypothesis" is not supported by the record.** We started a
programme, and the nearest thing to a first hypothesis is the Gann/price-time family **on the
index**.

## C. DECISION TIMELINE

Each row notes whether the change was **explicit** (the question change was stated) or **implicit**
(a surface or instruction changed and the question changed with it, without being stated). Driver
codes follow §8 of the audit request: A economic hypothesis · B market-structure interpretation ·
C data availability · D historical-data limits / budget · E statistical power · F implementation
convenience · G existing infrastructure · H researcher/assistant suggestion · I other ·
**N/E** not established.

| Date (IST) | Decision | Old question | New question | Surface | Reason | Evidence |
|---|---|---|---|---|---|---|
| 09-12 13:37 | Charter issued | — | Is there information in price, time, price×time, cross-market and derivatives? First family: price-time structure on the index | Index 1m pair; 1d cross-index; EOD derivatives | Programme definition. **Explicit** | Transcript #1 |
| 09-12 13:48 | Alignment record corrects breadth start to 2023-01-02. It states single-index `per_trade_pnl` is structurally dead ("√T ≈ 1.89 → Sharpe ≥ 1.3") and that cross-sectional `rank_ic` over ~190 names is "the only shape that can plausibly clear the gate", with the veneer caveat | Price-time on index | Same, plus an open question to the operator: Gann as single-index or as a genuine stock-level cross-section? | + equity breadth 1m 2023→ | **E, C, H.** **Explicit** proposal | `da7b3c6`, §0 C1, §7 L5, closing Q4 |
| 09-12 13:49 | Ruling: Gann = single-index `per_trade_pnl`, "test that claim directly"; seven families A–G adopted, including **F "genuine stock-level cross-sectional Price-Time"** and **G "EOD derivatives/market-state"** | As above | Seven families; Gann pinned to the index | Index; breadth 1m (F); EOD derivatives (G) | Gann form: **A** (fidelity to the claim), reason recorded. F: no reason recorded in the ruling; follows the L5 steer, so **E, H** by inference. **Explicit** | Transcript #3 §3–§4 |
| 09-12 15:16–15:36 | Catalogue: A–E **BUDGET-BLOCKED** (index 1m spent in both eras); F and G **CONDITIONAL**; catalogue frozen at seven | — | Which families have a fresh window? | Per family | **D** (budget). **Explicit** | `e9a4cd9`; #9 |
| 09-12 16:06–16:18 | C2-A1: `pit_membership` circular. Assistant: remedy "requires an independent PIT universe". **Ruling: Family F SUBSTRATE-BLOCKED, removed from the executable list**, "not to be rescued without an independent PIT universe" | F conditional | F removed | Breadth 1m | **D.** Remedy named by assistant (**H**). **Explicit** | `a41d033`; #11; `4dd3525` |
| 09-12 17:31–17:58 | Operator frames defects by "outside Nifty200 universe" (#14), then asks to verify a Nifty-200 list "so that we can solve the A1 problem" (#16) | F removed | **Rescue A1**, i.e. rescue F's substrate. **No F hypothesis stated** | Breadth 1m + N200 membership | **N/E** for why F was pursued after removal. **Implicit** | #14, #16; `1038e96` (18:00: assistant writes that A1's "permanent blocker status deserves re-examination") |
| 09-12 18:22 → 23:58 | NSE index press-release corpus assessed; **another model builds N200 PIT membership**; assistant reviews (A1 not satisfied: N200 and the 1m panel are "neither nested nor congruent") and fixes D1–D5 | — | Same (A1) | N200 membership store | Instruction explicit; research purpose **N/E** | #19, #21–#23; `5bf9971`, `74a8f46`, `9493d7e`, `2cbf577` |
| 09-13 13:45 | **"i have decided to use onlu nifty 100 stocks for this test"**; another model builds N100 membership | N200 universe | **N100 universe "for this test". The test is not defined anywhere** | N100 membership + breadth 1m | **Not recorded.** A plausible motive (N100 maps 100/100 to store keys while N200 did not, per `74a8f46`) is inference only. **Explicit** decision, **no rationale** | #24; `b6cb8f4` |
| 09-13 13:54 → 21:40 | N100 review ("A1 satisfied … blocking defect **for the test**"); 1m coverage backfill; C1/C3 repairs; A6 scoped out ("sector membership is not needed for **this construct**", #51); **certify N100 surface** (#58) | — | Substrate for an undefined N100 test | Breadth 1m, N100, 2023-01-02 → 2026-09-11 | **F, G.** Test **N/E**. The phrase "Nifty-100 **intraday** construct" is the **assistant's** paraphrase (transcript 09-13 19:45), not the operator's words. **Explicit** actions, **implicit** hypothesis | `6c2ceb7`, `14b720d`, `e3c8f8d`, `ab700e7`; #51, #58 |
| 09-13 21:44 → 21:51 | P3 window reconciliation, all seven families. **F: substrate unblocked but budget-dead** (ISD E-1/E-2 the same hypothesis class; MRLC E-3 multiply selected, live). **G: "the only one worth spending effort on now … its blocker is certification, which is work you can commission"** | Undefined N100 test | Which family can still be confirmed? | All | **D** (budget) + **H** (recommendation). **Explicit** | #59; `2980acc` §3.2, §3.3, §5 |
| 09-13 22:00 → 22:17 | **Family G index-options certification commissioned** (#61); MRLC stopped; "We have now decided to GO AHEAD with PTMS Family G — NIFTY INDEX-OPTIONS EOD" (#62) | N100 / F | **Family G on NIFTY index options** | NIFTY index options EOD | **C, D, H.** No economic reason recorded. The narrowing from the catalogue's "options + futures EOD" to index options follows `2980acc` §3.3 (futures and stock options spent). **Explicit** surface change; question change **implicit** | #60, #61, #62; `f448c07`, `4632193` |
| 09-14 13:20 | **P3 prompt redefines G**: "NIFTY INDEX-OPTIONS EOD · Price × Time × Market-Structure"; "original motivation … price and elapsed time … Gann-style"; outcome = **NIFTY index-option outcomes**; spot, VIX and futures banned as covariates | Catalogue G: positioning (OI, OI change, term structure) → forward return, nested price-only control | **Price×time (families B/C's question) → option P&L, on G's surface** | NIFTY index options EOD | **N/E** — no reason recorded for moving B/C's question onto G. Consistent with G being the only unblocked surface (**C, D**). **Implicit**: the prompt does not say it changes G | #64; catalogue G row |
| 09-14 13:20 → 13:42 | **Assistant designs PTSQ**: parity-implied forward, ATM straddle as √-time scale, overlay outcome; OI excluded from primary; mechanism (IV overreaction) attached; power computed **before** writing (n = 35 → ABANDON) | Price×time on options | PTMS-G-PTSQ | Same | **F, C** (only within-surface price proxy under the covariate ban), **A** (Gann "square"; mechanism supplied during design), **H.** **Explicit** document | `a47fd61`, `3e08f63`; first transcript trace of "price-time square" is 09-14 13:33 |
| 09-14 13:59 → 14:19 | Operator challenges the spent-window premise → GR-1; observation-architecture analysis **first flags that PTSQ does not test the catalogue's G mechanism** | — | Governance | — | **Explicit** | #66, #67; `b4aded5`, `7a15a62` |

## D. PIT MEMBERSHIP DECISION

**What required PIT membership.** Only **Family F** (stock-level cross-sectional price-time). A
cross-section needs a survivorship-free universe, and C2-A1 proved the existing one circular.
Families A–E (index) and G (index options) need none.

**Required by the original hypothesis? No.** The charter has no stock cross-sectional family. The
requirement came from a later design decision:

- the alignment record's power steer (`da7b3c6` §7 L5), which is assistant-originated (**H, E**);
- the operator's adoption of F (#3, 13:49 IST, 09-12);
- C2-A1 making it binding (`a41d033`).

This is **case B** of the audit request: *"we decided to include a stock cross-section, therefore
PIT membership became necessary."*

**Necessary dependency or infrastructure expansion?** For F, necessary. For the programme at the
moment work began, **an expansion.** F had been **removed** 100 minutes earlier (#11, 16:18 IST)
and no F hypothesis existed.

**What we intended to test when PIT work started** (17:58 IST, #16): **not recorded.** The stated
aim was "solve the A1 problem", a substrate objective. On 09-13 the operator wrote "this test" (#24)
and "this construct" (#51). Neither is defined in the repo or transcript. It may exist in the
external ChatGPT thread or the other model's prompts; this audit cannot see those.

**Could it have been tested without PIT membership?** For a genuine stock cross-section, no. A
non-circular universe was required. But **cheaper non-circular options were on record**:
- `fno_member` in `pit_universe` was already independent (`a41d033` A1);
- per-date F&O eligibility from `futures_bhavcopy` was proposed (`1038e96`).

Why N200 and then N100 were chosen instead is **not recorded**.

**The decisive historical point: budget was knowable before the build.** Register v1 (`385bd99`,
09-12 13:54) already recorded:
- **E-1/E-2**: ISD, cross-sectional, signal-level, 2023-01-02 → 2024-11-30;
- **E-3**: MRLC, signal-level, "2023-01-01 → present";
- the unread-surface table: breadth 1m 2024-12-01 → present "touched by E-3 (MRLC, signal)".

The catalogue marked F CONDITIONAL, "must be negotiated against the register, not assumed". **That
negotiation was not done before the PIT build.** The adopted sequence placed it after P2
certification (#9, #10). When it was done (`2980acc`), F's window turned out to be spent and
multiply selected.

**Today's perspective:**

| If PTMS becomes… | PIT membership required? |
|---|---|
| Bare NIFTY index research | **No** |
| N100 cross-sectional research | **Yes**, and it now exists and is certified. That surface's historical confirmatory budget is spent; only forward time could supply a window (`2980acc` §3.2) |
| Options / NIFTY derivatives research | **No** (index options carry no universe) |

**Classification:** **(2) essential to a later branch (Family F)** and **(3) unnecessary for the
branch eventually chosen (G)**. A large share of the work was also **(4) useful shared
infrastructure**, independent of any PTMS hypothesis:
- canonical CA downloader (`9a02f9b`);
- universe/mapping refresh repair (`5f9431d`);
- the February chunk bug that truncated every 1m historical fetch (`14b720d`);
- documentation that the 1m store is CA-adjusted (`4208278`);
- session-schedule Muhurat overrides (`778a54a`);
- 548 false synthetic marks cleared (`37f04e5`).

It was **not (1) essential to the original research.**

## E. NIFTY-ONLY TRANSITION

**There is no single "N100 → NIFTY-only" decision, and the suspected ordering is wrong.**

1. **NIFTY single-index framing came first, on day one**, for the Gann family, with a recorded
   reason: "If Gann's actual claim is that price-time geometry predicts direction on an index, test
   that claim directly" (#3 §4, 13:49 IST 09-12). Driver **A**. The surface was index 1m, not
   options.
2. **The N100 work was a detour through Family F**, not a step on the path to NIFTY.
3. **The move away from N100** is observable: certify N100 (#58, 21:38 IST 09-13) → reconciliation
   (`2980acc`, 21:51) → Family G certification (#61, 22:00). **The only recorded reason is the
   reconciliation's budget finding** (F budget-dead; G's blocker purchasable) plus its
   recommendation (**D, H**). No record states a research reason for leaving the N100 surface.
4. **"NIFTY-only" on options is a store fact, not a decision.** `DATA_STORE_MAP.md` already recorded
   "options `NIFTY` index" at P1 (09-12). The certification confirmed "there is no BANKNIFTY"
   (`f448c07`). Narrowing G from "options + futures EOD" to index options is recorded with a budget
   reason: futures and stock options spent (`2980acc` §3.3).

**For the switch of the research object from the N100 cross-section to a NIFTY-options hypothesis:
the switch is observable, but its causal rationale is not explicitly recorded beyond research-budget
availability and the assistant's recommendation.**

## F. OPTIONS TRANSITION

| Question | Finding | Evidence strength |
|---|---|---|
| Were options part of the original programme? | **As a family, yes**: charter §12 "derivatives / market-state", with questions about positioning predicting *underlying* behaviour. **As the outcome instrument, no**: charter §17 places option choice in the trading layer and says not to jump there before an underlying edge exists | Direct text |
| When did options become the primary PTMS surface? | **2026-09-13 22:00 IST** (#61), made explicit at 22:17 (#62: "GO AHEAD with PTMS Family G — NIFTY INDEX-OPTIONS EOD") | Direct |
| What introduced it? | The P3 window reconciliation `2980acc` (21:51 IST), §5 recommendation 1: G is "the only one worth spending effort on now. Its blocker is certification, which is work you can commission." | Direct; nine minutes separate report and instruction |
| What problem was it meant to solve? | **Research budget.** Every other family was blocked on budget (A–F) or on certification plus budget; G's index options held unread 2021–2022 and 2026 windows | Direct (`2980acc` §3, §5) |
| Intended role: (a) market structure, (b) positioning/OI, (c) better expression of a hypothesis, (d) an available historical data source? | **(d)** is the only role recorded at the moment of the switch. **(b)** is the catalogue's original G mechanism, but **nothing at the switch mentions OI**. **(a)/(c)** appear only in the 09-14 P3 prompt ("Price × Time × Market-Structure"), 15 hours later, with no stated argument that options express price×time better than the index | Direct for (d); absence of record for (a)–(c) |
| Derived from the original hypothesis, or a change of direction? | **A change of direction.** The price×time question (B/C) was blocked on its own surface. It reappeared on the options surface after that surface was found to be the unblocked one, and the outcome changed from future underlying behaviour to **option P&L** | Strong: the sequence and the unchanged catalogue G row are documentary |

**Answer to the key question.** The record supports the second reading: *options were available and
the question was reformulated around them.* It does not support the first reading, that the
scientific question called for options. **The documented reason is availability; any
scientific-question rationale is retrospective.**

## G. PTSQ ORIGIN

- **Prior hypothesis it descends from:** Families **B/C** (price × elapsed time; Gann geometry), via
  the P3 prompt's statement that "the original motivation is the claim that price and elapsed time
  can interact … including the broad Gann-style idea of price-time equilibrium" (#64).
- **Why options:** because G's certified surface was the task. The prompt fixed the surface ("Family
  G is: NIFTY INDEX-OPTIONS EOD") and the outcome ("NIFTY index-option outcomes") before any
  construct was considered.
- **Why the specific PTSQ mechanism** (assistant design, 09-14 13:20 → 13:42 IST):
  1. The covariate ban on spot, VIX and futures left **put-call parity** as the only within-surface
     price of the underlying. This is a **surface constraint (C, F)**.
  2. The ATM straddle is the market's own **√-time price scale**, which lets a Gann "price-time
     square" be written without a free unit. This is the **Gann framing (A)**.
  3. The Thursday→Tuesday change forced a **session clock (D)**.
  4. The "minimal hypothesis" instruction led OI to be **excluded** from the primary.
  5. The **economic mechanism** (implied-vol overreaction; Stein 1989, Poteshman 2001) was
     **attached during design, after the surface and outcome were fixed**.
- **Genuine thesis or testability?** **Primarily testability on the available surface, dressed in a
  mechanism.** The mechanism is real literature and is stated honestly, but it did not *select*
  options; options were selected first (§F).
- **Did Gann material motivate it?** Yes, explicitly, via #64's framing and the "price-time square"
  construction.
- **Does it match the catalogue's Family G?** **No.** The catalogue G row is "Derivatives
  positioning (OI, OI change, term structure) carries forward-return information beyond price";
  label a forward return; mandatory `price` vs `price + derivatives` control. PTSQ uses no OI, has
  an option-P&L label, and has no nested control.
- **When did the mismatch become apparent?** It was **introduced by the P3 prompt** on 09-14 13:20
  IST. It **was not flagged** in `a47fd61` (which only states that OI is excluded, §4). It was
  **first flagged** in `7a15a62` at 14:19 IST, 59 minutes after the prompt and 37 minutes after
  `a47fd61`. Charter §17's prohibition on
  option outcomes has **never been flagged before this audit**.
- **Power was knowable before design.** The assistant computed n = 35 → ABANDON during orientation,
  before writing the definition (session summary, 09-14 13:33 IST). This is the same single-index
  wall recorded on day one (alignment record §7 L5; catalogue C row at `e9a4cd9`), now at
  √T = 0.82 instead of 1.89.

## H. RESEARCH-SURFACE DRIFT

**Drift occurred, at two points.**

| # | Where | What drifted | Evidence strength |
|---|---|---|---|
| **D-1** | 09-12 17:58 IST → 09-13 21:40 IST | **Substrate work detached from a hypothesis.** A1 was pursued after F was ruled removed, with no F hypothesis recorded, and F's recorded budget exposure (E-1/E-2/E-3) was never adjudicated first. The objective became a *fixable problem* (A1) rather than a *question*. The operator named a "test" and a "construct" on 09-13 without defining either | **Strong** on the absence of a hypothesis record and on the budget being on record beforehand. **Motive not established** |
| **D-2** | 09-13 21:51 IST → 09-14 13:42 IST | **The price-time question relocated to the unblocked surface, and its outcome changed.** Budget reconciliation → G recommended → G certified → G redefined as price×time with an option outcome → PTSQ built to fit | **Strong.** Each link is a dated document or message. The absence of any record acknowledging the change of G's mechanism, label or charter §17 is itself documentary |

**Not drift:**
- The day-one architecture (charter → alignment → catalogue): explicit and justified.
- The Gann single-index pin: explicit, reason recorded.
- The NIFTY-only property of the options store: a data fact.
- The narrowing of G to index options: recorded, with a budget reason.

**Contribution of assistant suggestions (H), stated plainly.** The assistant:
1. proposed the cross-sectional steer that seeded F (`da7b3c6` §7);
2. named the independent-PIT remedy (`a41d033`) and suggested A1's permanence be re-examined
   (`1038e96`);
3. recommended G on budget grounds (`2980acc` §5);
4. designed PTSQ to fit the surface (`a47fd61`).

Each was offered as analysis for operator decision. Taken together, they are part of the causal
chain.

## I. GOVERNANCE CONSEQUENCES

| Transition | Should have been treated as | Treated as | Discrepancy |
|---|---|---|---|
| Charter → seven-family catalogue | Programme definition; seven family slots | Same | None |
| Family F adopted (ruling #3) | New family slot | Same | None |
| A1 / N200 / N100 PIT work | Substrate infrastructure (ingest/meta; no budget spend) **serving a declared F hypothesis** | Substrate certification with **no declared hypothesis** | **The "test" / "construct" that N100 scope and the A6 scope-out rest on is undefined.** The A6 ruling ("not needed for this construct") conditions a certificate on an unrecorded object |
| N100 1m backfill, prunes, synthetic clears | Ingest-level register rows | Recorded in reports and commits only | Register has **no rows** for these writes (E-5 covers CAS marking only) |
| N100 / F → G | **Change of active family**; F parked as budget-blocked | Operator instruction | No decision-log entry records that F was set aside, or why |
| G narrowed to NIFTY index options | Catalogue amendment (surface scoping inside G) | Stated in `2980acc` §3.3 | **Catalogue G row never amended.** It still reads "options + futures EOD", positioning, "stall at 2026-07-17" |
| **G redefined as price×time with an option outcome** (#64) | **A new hypothesis family, or an explicit catalogue amendment ruling**, with its own multiplicity slot. The catalogue is frozen ("Do not expand the catalogue after seeing results", #3; "Do not add families or expand candidate surfaces", #10) | Continuation of Family G | **Largest discrepancy.** Moving B/C's question onto G's surface after the reconciliation showed B/C blocked expands G's candidate surface after seeing budget results. **Whether that breaches the freeze is the operator's ruling**; the facts are not in dispute |
| PTSQ | A candidate inside whatever family #64 is ruled to be; one slot; unfrozen | Candidate in G | Slot ownership (B, C, or G) undetermined |
| Exposure of PTSQ's windows | **Observation-shaped question.** B/C were blocked because the NIFTY index path is spent (I-5/I-8/D-2 on 2021–2022; I-2/I-3 on 2026). PTSQ's construct is a function of that same path, observed through option prices | File-shaped register: G windows recorded fresh | **Open since `2980acc` §1.2.** Under an observation-shaped ruling, relocating the question to options would not create fresh budget: the "manufactured freshness" #64 itself prohibits |

**Is the exposure register an accurate record of what was explored?** Not fully:

1. The corrections listed in `2980acc` §4 remain unappended: E-3 (MRLC to 2026-09-02, live), O-1
   (stock options from 2016-02-26), O-2 windows unpinned, and no row type for a live consumer.
2. The observation-shaped reading is unruled.
3. The alignment record's proposed **PTMS multiplicity register / trial ledger** (§7 L5) was **never
   created**, so no document counts PTMS slots.
4. The certification §8 correction (orphaned 2026-03-26 / 2026-03-31 listings) is unappended.
5. Ingest rows for the N100 backfill and the G0 options ingest are absent.

**No window has been spent at signal level by PTMS itself.** Every PTMS read to date is meta,
ingest or structural. Nothing above invalidates data; it concerns what the record says the
programme is testing.

## J. WHAT WE SHOULD DO NOW

**One governance step: an operator adjudication, recorded as an append-only PTMS decision log,
before any further hypothesis work.** It should settle, in this order:

1. **The status of the 09-14 redefinition of Family G.** Either amend the frozen catalogue by
   explicit ruling, deciding which family owns a price×time-on-options hypothesis and its
   multiplicity slot, or rule it outside the catalogue. Amend the stale G row either way.
2. **The observation-shaped exposure question.** It decides whether *any* price×time hypothesis on
   NIFTY options has an unspent window at all, and so decides whether item 1 matters.
3. **The undefined N100 "test".** Either register it as a Family F candidate or record that none
   exists, so that the N100 certificate's A6 condition refers to something.
4. **The outstanding register appends:** `2980acc` §4; the §8 orphan correction; ingest rows for
   the N100 and G0 writes; a PTMS multiplicity register.

PTMS-G-PTSQ stays unfrozen and un-gated until items 1 and 2 are ruled.

## K. STOP

No research or design recommendation beyond the governance step in §J. No hypothesis selected, no
RFA, no freeze, no register modification, no outcome data read.
