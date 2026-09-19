# PTMS — Gann Stage-1 Freeze Document — DRAFT FOR OPERATOR REVIEW (P-5)

**Date:** 2026-09-19 · **Branch:** `research/ptms-price-time-market-structure` · **Drafted at:** `5e41889`

**Status: DRAFT. NOT FROZEN. NOT APPROVED. NOT HASHED.**
- This document transcribes every freeze-checklist row marked RULED — TO TRANSCRIBE
  (`PTMS_GANN_STAGE1_FREEZE_CHECKLIST_2026-09-15.md` §3). It makes **no** new scientific choice.
- No market data, outcome, signal count, IC, p-value or event count was read to write it. No code was
  run except the text-assembly step that copies the verbatim excerpts (§0.2).
- It becomes the Stage-1 freeze only when **all** of the following hold:
  1. every item in §0.3 is ruled or confirmed by the operator and written into this file;
  2. items 14 (P-3 code) and 15 (P-4 G-S1) are done;
  3. the operator approves this file.

**Construct set:** GF-1, GF-4T/R8, GF-10. **m = 3.** Screen α = 0.05/3 per construct, one-sided.
**Label: NON-CONFIRMATORY (GR-1.4).**

---

## 0. How to read this document

### 0.1 Structure

Sections 1–19 mirror the freeze-checklist items 1–19, with the same numbers, so that P-5 approval can
tick through them in order. Each section gives:
- the **frozen text**, either written here or quoted verbatim from its source;
- the **source** (file, section, commit);
- any **transcription note**. A transcription note records a supersession or a derived consequence.
  It never records a new choice.

### 0.2 Verbatim excerpts and the source manifest

Blocks headed **VERBATIM** were copied mechanically from the source file's stated line range at the
commit in §0.4. Inside them only heading levels were lowered, to nest under this document's sections.
No other character was changed. Where a verbatim block and this document's own text differ, **the
verbatim block governs**, and the difference is a transcription error to be corrected before approval.

### 0.3 Items the operator must settle before approval (freeze review)

Transcribing the ruled rows exposed the items below. None is chosen here. Each is either a
confirmation the rulings already reserved for freeze review, or a place where the committed text stops
short of what the code needs. The same pattern was used for RR-1 … RR-3.

**A. Confirmations reserved for freeze review by earlier rulings**

| ID | Item | Reading on the table | Alternative(s) | Source |
|---|---|---|---|---|
| **OC-1** | G-7 dependency-span **start**, per construct | Rulings §2: GF-1 = the date of the running all-time extreme it counts from; GF-4T/R8 = the date of the confirmed K3 swing anchor; GF-10 = the earliest of d_ref and the start date d_h′ of the earliest member of 𝒰_T ∪ 𝒰_P (v0.8 §3.12). Span end = O_5 for all | See the note below | Rulings file §2; v0.8 §3.12 |
| **OC-2** | The robustness set (§12) is **complete** | Set as ruled and ratified 2026-09-19 | Add a variant now. Nothing can be added after a read | Checklist §5 last paragraph |

*Note on OC-1 (transcription finding, not a choice).* G-7's ruling text is: "from its earliest
**anchor or reference** date through O_5". Two points in the per-construct reading differ from that
text:
- **(i) The reference date.** GF-1 and GF-4T/R8 outcomes use the O-R10 reference swing (§4). Its date
  d_ref can be earlier than the anchor. For example, a GF-4T/R8 stock in K3 UP whose most recent swing
  is a swing **high**: the O-R10 reference is the earlier swing **low**. The reading on the table does
  not include d_ref for these two constructs. The GF-10 reading does.
- **(ii) Two anchors.** GF-1 scores against **both** running extremes (§2). "The running all-time
  extreme" (singular) does not say which of the two.

The options are:
- **(a)** the reading as tabled;
- **(b)** the literal G-7 text: span start = the earliest of every anchor date the score uses and
  d_ref. For GF-1 that is min(high-anchor date, low-anchor date, d_ref). For GF-4T/R8 it is
  min(anchor date, d_ref). For GF-10 it is as tabled, which already includes d_ref.

**B. Readings for ratification (the committed text reads one way literally; the code needs it pinned)**

| ID | Scope | Question | Literal reading on the table | Alternative | Why it is needed |
|---|---|---|---|---|---|
| **RR-4** | GF-1, GF-4T/R8 | Instant at which the K3 state, the anchors and the O-R10 reference are read at formation week *w* | **As of close(D_L), including D_L's bar.** Memo §5 row 4: a swing is "usable from the close of the 3rd qualifying session"; G-2(a): the **contemporaneous** K3 line state; memo §11.F: "anchor usable only once established" | The D−1-frozen state on D_L (≤ close(D_L⁻)), as GF-10 uses (OPEN-K(b)) | G-2(a) and memo §7 fix the state and the reference but not whether D_L's own bar counts. RR-1 … RR-3 and OPEN-K were ruled for GF-10 only |
| **RR-5** | GF-1, GF-4T/R8 | Is a low **equal** to the reference (bear: a high equal) a penetration? | **No — strictly beyond.** "Penetrated" read as for GF-10 (RR-1) | Touch counts (≤ / ≥) | RR-1 is a GF-10 lock. R-2's "any penetration" fixes the amount (any), not equality |
| **RR-6** | GF-1, GF-4T/R8 | Does a penetration of the reference **before** O_1 make y = 0? | **No.** G-2(a) literally: "outcome = 1 iff the last K3 swing low is penetrated intraday within the next 5 sessions". There is no prior-penetration clause. This is the "memo §7 as written" option that OPEN-K(b) declined **for GF-10 only** | GF-10's rule (OPEN-12d at f_w): a penetration in (d_ref, f_w] gives y = 0 | Without it the two GF-10-style readings could leak across constructs. If ratified, the asymmetry with GF-10 is disclosed (report X-6 already discloses the anchor difference) |
| **RR-7** | GF-1, GF-4T/R8 | (a) "The next 7 days"; (b) the PIT-membership instant | (a) The calendar dates cal(D_L) + 1 … cal(D_L) + 7. (b) PIT member on D_L, which is GF-10's A1 instant (OPEN-K(a)) | (a) Other 7-day spans. (b) Member on any session of *w* | Memo §11.F says "next 7 days" after week-end *t*; memo §7 says "PIT member" without an instant |
| **RR-8** | Surrogate and size check (all) | What "identical code" (memo §8.2) means for panel masks and for the size check's inner test | **(a)** Every surrogate and pseudo-real panel is scored by the same code, with the real calendar, real PIT and listing masks, **real** ex-dates for G-7, OPEN-M and the G-6b floor. **(b)** In the size check, each pseudo-real panel is tested exactly like the real panel: its own B = 1999 surrogates are resampled **from that pseudo-real panel** | (a) G-7 masks not applied inside surrogate panels. (b) Inner surrogates resampled from the real panel | Memo §8.2 says "identical code" and "run the full test", and G-9a says "exactly as the real test", but neither says which masks travel |

**C. Open definitions (no literal reading exists; options only, no recommendation)**

| ID | Scope | Gap | Options named | Why it matters |
|---|---|---|---|---|
| **OPEN-P** | All three primaries, the placebos, the contrast legs, every surrogate | The **per-date Spearman IC is undefined** when, on a formation date, every eligible name has the same score (for example, a GF-10 week with no P1 event) or the same outcome. Memo §8.2 defines T_c as "the mean over formation weeks of the per-date Spearman IC" and does not say what happens on such a date | (a) The date is dropped from T_c (the count is reported); (b) the date's IC is set to 0 and it stays in T_c | It changes T_c, and therefore p_sur, p_plac and Δ, on every panel. The G-6b floor (20 names) does not prevent it. **For GF-10 this is expected to be a common case, not an edge case.** Persistence A allows at most one P1 event per episode, and A1 keeps every active candidate eligible as a 0. So a formation date can carry ≥ 20 eligible names and no 1 at all. Options (a) and (b) therefore change which weeks make up GF-10's T_c substantially, not marginally. No count is estimated here, because that would need data |
| **OPEN-Q** | K3 (all), in real and surrogate panels | A stock with **no bar on a session of 𝒟** while listed and a member. Real data: one declared case, 2020-04-13 (R-13 certification, "unpriced member-days"). Surrogates: G-5 leaves "the stock missing on that surrogate date". Memo §5 row 12 compares "each session vs the previous session" and does not say what happens across a missing bar | (a) The missing session is skipped: comparisons run over the stock's own bars; (b) a missing session breaks every K3 run in progress | K3 is upstream of every score and outcome. G-5 makes this case reachable in every surrogate panel |

**D. Tasks and approvals (not definitions)**
- Item 14 (P-3): Stage-1 code committed from a clean tree, not run. Its path and commit go in §14.
- Item 15 (P-4): the **operator** appends G-S1 to the exposure register. The row text is in §15.
- Item 18 (P-5): operator approval, and the digest recorded **outside** this file (§18).

### 0.4 Source manifest

Every source below was read at the commit shown. SHA-256 is of the file bytes at that commit.

| File (`docs/reports/ptms/`) | Last commit | SHA-256 |
|---|---|---|
| `PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md` | `0d6a3b5` | `3ebb2c0d46b67d965c2a53eb426ace3963f31bbc88db1a8be71ff5efb23ac05c` |
| `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md` | `156a2ce` | `fe7be5dfa6744ff3e8143959c71fd81bae86b0080751a4f7a8618bddfe5c53c0` |
| `GF10_MECHANICAL_DECISION_RECORD_v0.8_2026-09-19.md` | `c894a64` | `59dab2dff0060e2e424922556c9c34852ba7d28162cb1b0942ea207aef7e83bf` |
| `PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md` | `cdf2b06` | `86ce713cbe1c7327430fb46a9a63b7b9808cd7d7390d1f7095e2c38fe8672474` |
| `PTMS_GANN_P2_CA_ENUMERATION_2026-09-19.md` | `156a2ce` | `89a6ad91349b91cdc691da7206311d19a4dc5027db5b02ba3e2cead731677d6d` |
| `PTMS_GANN_R13_LEFTOVERS_CLOSURE_2026-09-19.md` | `5e41889` | `3f67442e46069267521db5150dcecbbe255250e4b779be10a3e2ae3c1ed3b645` |
| `PTMS_GANN_STAGE1_ROBUSTNESS_LIST_DRAFT_2026-09-19.md` | `d25b420` | `4aad92cee35c852af78b59116ff1db4a5259765fcba67451ca18c89bf4f9d303` |
| `PTMS_GANN_STAGE1_ROBUSTNESS_SPECS_DRAFT_2026-09-19.md` | `d25b420` | `31afbce7c8648038f48c0cfe16f05e8b6e08efe1426dc029f10a4219a1e5f00b` |
| `PTMS_GANN_STAGE1_REPORT_TEMPLATE_AND_GR15_DISCLOSURE_2026-09-19.md` | `973c850` | `69992d014e899583ca890eac3b2a438be3feea670f0489cb6ee134cbbae0da6e` |
| `PTMS_GANN_P2_CA_EVENTS_2026-09-19.csv` | `156a2ce` | `2d9c14cbb3cd7f27a317b66750b79a2c13c6f315547dd8427690143f59ae3ada` |
| `PTMS_GANN_R13_N100_EOD_SCOPED_CERTIFICATION_2026-09-15.md` | `df3aae2` | `1f9a519d730aa36388943ece7de0c325e877a3a27b7ecf99ddb470e672424e7e` |
| `PTMS_GANN_R11_READER_DATE_AUDIT_2026-09-15.md` | `df3aae2` | `6ff0e4979f709f1b1e002961354d14d59d58822afaaf2e9f934bfbc515580d87` |

---

## 1. Rulings R-1 → R-14 recorded in writing

**Frozen:** the RULING rows of R-1 … R-14 in `PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md`,
together with their "Frozen if accepted" rows, and the G-1, G-2 and G-3 blocks. **R-15** stays open. It
is Stage 2 only and is not needed for Stage 1. **Ruling 7 is superseded by R-5.** The 2026-09-19
rulings (`PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`) are frozen in full, with their addenda.

*Transcription note.* Some of the verbatim rows below record the state of play on the day they were
written, e.g. R-11 "Not yet performed", R-13 "External CA enumeration: OUTSTANDING", R-12 "Not
ruled". Those states were closed later, by the R-11 audit and the freshness ruling of 2026-09-19, by
P-2 and the R-13 closure, and by G-1. Where a verbatim row and a later ruling differ, **the later
ruling governs**, as given in the section cited: §7 for R-13, §10 for G-1, §11 for R-11.

**VERBATIM — ruling register, RULING / status / "Frozen if accepted" rows of R-1 … R-14:**

<!-- VERBATIM (selected rows) PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md lines 35-190 -->

#### R-1 — Swing detector (K3)

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** Strict 3-Day Chart / K3 admitted as an **explicitly labelled approximation of Gann's discretionary historical detector**. Every implementation assumption in the "Frozen if accepted" row below is preserved, with the disclosure *"Gann's own record departs from the strict rule in ≥ 7 of 61 swings (1912–14)"* (a lower bound: holidays ignored). Memo §5 row 7's "declared departure" is read as this label |
| **Frozen if accepted** | The K3 algorithm of memo §5, including each IMPLEMENTATION ASSUMPTION: strict inequality (equal bar breaks a run); no gap handling; initialization at the first qualifying 3-session run; up-switch = 3 sessions of higher highs **and** higher lows, down-switch = 3 sessions of lower lows (literal reading; symmetric reading as robustness); day-over-day comparison; outside/inside-day handling; exception **not** applied; runs counted in sessions, durations in calendar days; swing usable from the close of the confirming session |

#### R-2 — Outcome ("change in trend")

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** Rule 10 is the Stage-1 minor / temporary change-in-trend outcome. **No main-trend trading-range outcome is invented.** (Direction for GF-1 and GF-4T/R8, and GF-10's bear pooling, are not fixed by the text accepted — freeze checklist G-2) |
| **Frozen if accepted** | O-R10: direction by construct; **any** penetration (Gann's 3-point example is point-based → Stage 2); intraday high/low basis (matches "tops and bottoms"; close basis not used); horizon = next 5 sessions; binary outcome; report wording "minor change in trend" |

#### R-3 — Sense of "extreme" (anchors)

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** GF-1 anchors are the running highest high and lowest low to date; left-censoring (2011-03-25 or listing) disclosed |
| **Frozen if accepted** | GF-1 anchors = running highest high and lowest low from each stock's first date in the store (left-censored at 2011-03-25 or listing, disclosed per stock); a new extreme restarts its count; anchor-age strata as a pre-specified diagnostic |

#### R-4 — Rule 8 window widths (GF-4T/R8)

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** The complete nine-window printed Rule 8 set is primary. Worked-example windows are robustness only |
| **Frozen if accepted** | The nine printed windows, inclusive, in calendar days from the anchor date; no additional tolerance; robustness set = printed list with 57–65 → 60–67/60–72 and 85–92 → 90–98, off the pass path |

#### R-5 — GF-10 status (supersedes ruling 7)

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** Ruling 7 is **SUPERSEDED**. GF-10 = **GANN-FAITHFUL**. Primary comparison: current decline vs the immediately preceding decline |
| **Frozen if accepted** | GF-10 primary cell (memo §11.F): S9 bull state (last two K3 highs and lows rising); in a K3 decline; score = 1 once the calendar-day duration from the current swing high to *t* exceeds the preceding completed decline's duration, before any up-switch; outcome = break of last K3 swing low within 5 sessions; bear mirror pooled with sign. Ruling 7 recorded as superseded |

#### R-6 — GF-8 and GF-9

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** GF-8 and GF-9 excluded from Stage 1; retained as Arm-1 claims / deferred research items |
| **Frozen if accepted** | Exclusion recorded with reason; GF-8/GF-9 absent from the construct set and from *m*; a per-stock mechanized mode of swing durations labelled Arm 2 if ever built |

#### R-7 — GF-7

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** GF-7 excluded from Stage 1, because "sections" cannot be faithfully mapped to K3 swings |
| **Frozen if accepted** | Exclusion recorded; GF-7 absent from the construct set; any K3-upswing version labelled Arm 2 |

#### R-8 — GF-5 and GF-6

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** GF-5 and GF-6 are **DEFERRED, NOT RETIRED**. They must not be described as permanently power-infeasible |
| **Frozen if accepted** | Status wording; exclusion from Stage-1 *m*; the assumptions behind the power figures listed as the conditions for any revival |

#### R-9 — GF-1 time unit; GF-4T/R8 anchor scope

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** (a) GF-1 uses calendar days. (b) GF-4T/R8 uses only the most recent confirmed K3 swing. Both are labelled **design choices where Gann does not uniquely specify them** |
| **Frozen if accepted** | (a) GF-1 points P4 = {36, 48, 72, 96, 108, 144} + 144*k* in calendar days; market days as robustness. (b) GF-4T/R8 anchor = last confirmed K3 swing extreme; all-swings variant as robustness; both labelled design choices |

#### R-10 — GF-10 specificity check

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** GF-10 specificity uses Gann's own time-over-price contrast, not ratio placebos. (The contrast's p-value mechanics are not written as a formula — freeze checklist G-4) |
| **Frozen if accepted** | Price-overbalance score (current decline's points exceed the preceding decline's, same K3 swings, ratio-adjusted series); contrast statistic = T(time) − T(price); one-sided p from the surrogate joint distribution; used in confirmatory tests, reported but not a kill criterion in the screen |

#### R-11 — Exposure of equity EOD 2023-01-02 → 2026-09-11

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** The reader-date / exposure audit is to be performed from code, date filters and saved artifacts only; **no outcome statistics**. **Not yet performed.** *(as of the ruling — superseded by the Status update row below.)* The freshness ruling on 2023-01-02 → 2026-09-11 follows the audit; until then the span stays UNRESOLVED |
| **Status update (2026-09-15)** | **Audit performed — complete.** `PTMS_GANN_R11_READER_DATE_AUDIT_2026-09-15.md`. **Finding: 2023-01-02 → 2026-09-11 equity EOD is signal-spent** — Carry/TS-Basis/IVOL SEALED evaluations consumed equity-EOD-derived forward returns on 2023+ formations; Trend/LAG/TS-Basis-Daily stores carry the score↔forward-return linkage on 2023+ dates; the MRLC scanner 1d track read bhavcopy 2026-04-27 → 2026-09-02. **The audit itself is complete; the formal freshness ruling remains an operator decision.** Until ruled, the span's register standing stays UNRESOLVED |
| **Frozen if accepted** | Audit scope (read code paths, date filters and saved artifacts' date ranges only; compute no statistic); appended register rows; the resulting freshness ruling as the confirmatory-window input |

#### R-12 — Development screen

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED IN PRINCIPLE ONLY.** The non-confirmatory 2011-03-25 → 2022-12-30 screen may proceed only after R-1 → R-11, R-13 and R-14 are fully frozen **and** the operator has appended register row G-S1. **Not to be run now.** **Not ruled:** whether a surrogate-pass / specificity-fail construct may proceed to a confirmatory test (freeze checklist G-1) *(as of the ruling — since ruled by G-1, 2026-09-15; see the G-1 block.)* |
| **Frozen if accepted** | Window end 2022-12-30; statistic and α = 0.05/*m*; kill rule on the surrogate leg; specificity leg reported separately; B = 1999; confirmatory α = 0.05/*m*_entered; no screen estimate may feed a later δ band; NON-CONFIRMATORY label and wording; GR-1.5 disclosure; the draft G-S1 row text |

#### R-13 — Data certification and corporate actions

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** Scoped N100 EOD certification and corporate-action enumeration with exclusion windows are required before any outcome read. **Neither exists yet** *(as of the ruling — superseded by the Status update row below.)* |
| **Status update (2026-09-15)** | **Store-level N100 EOD certification: COMPLETE** (all gates PASS) and **in-store CA enumeration: COMPLETE** — `PTMS_GANN_R13_N100_EOD_SCOPED_CERTIFICATION_2026-09-15.md` (runner: `scripts/research/ptms_gann/certify_eod_n100.py`, read-only). **External CA enumeration: OUTSTANDING — requires operator authorization** (the store cannot prove absence pre-2022 and omits the 2023 RELIANCE→JIOFIN demerger). **G-7 exclusion-window rule: still OPEN.** Remaining items: G1/G3/G5 persistence into `n100_audit`, 2016-04-19 holiday confirmation, and the ±1-month boundary / BE-series / DVR dispositions if the cadence requires them |
| **Frozen if accepted** | Price basis (ratio-adjusted as-of-*t* series for Stage 1); certified window and universe; the enumerated corporate-action list with exclusion windows; calendar artifacts declared (2012-11-11; 2016-04-19 check) |

#### R-14 — Statistical specification

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED FOR FINALIZATION ONLY — do NOT execute.** The synchronized block-bootstrap design, specificity checks, B = 1999 with a recorded seed, placebo definitions and the blind 200-panel size check are to be finalized. **Finalization is incomplete:** the GF-1 and GF-4T/R8 placebo sets *(both since ruled by G-3, 2026-09-15)*, the GF-10 contrast p-value, the missing-bar neighbourhood, the seed value and the size-check failure rule are not specified in the text accepted (freeze checklist G-3 to G-5, G-8, G-9). Not filled here |
| **Frozen if accepted** | Bar-vector definition; synchronized resampling; mean block 20 (5 and 60 reported off-path); missing-bar rule; B = 1999 and seed; placebo sets (GF-1 non-Gann fractions of 144; GF-4T/R8 shifted windows of equal width) and the GF-10 contrast; one-sided +1 rank p-values; size-check procedure and threshold |
<!-- END VERBATIM PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md -->

**VERBATIM — ruling register, G-1 block:**

<!-- VERBATIM PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md lines 201-213 -->
#### G-1 — Surrogate-pass / specificity-fail path

**RULED by the operator 2026-09-15** — closes freeze checklist G-1. A **pre-result
scientific/operator specification**. Stage 1 is intended to establish evidence for the specified
Gann-faithful construct, not merely evidence of a generic temporal/market phenomenon.

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED: A Stage-1 construct that passes the surrogate leg but fails the Gann-specificity leg is retired and may NOT proceed to a confirmatory test.** Rationale: failure of the pre-specified specificity leg means the construct has not demonstrated the required Gann-specific property |
| **Basis** | Freeze checklist §4 G-1; R-12 (the sub-question posed in the ruling sheet was not ruled there); memo §10 (the screen's kill rule rests on the surrogate leg alone and a surrogate-pass / specificity-fail construct was labelled *"timing effect not shown to be Gann-specific"*, with the onward path left to the operator) — this ruling decides that path |
| **Frozen if accepted** | A construct reaches a confirmatory IUT pre-registration only if both legs pass. Report wording for a surrogate-pass / specificity-fail construct: the memo's label plus the retirement disposition — *"timing effect not shown to be Gann-specific — RETIRED; may not proceed to a confirmatory test"* |
| **Recorded interaction (no new definition)** | G-3 was OPEN when this ruling was made and this ruling does not define G-3, change any placebo set, or change α or m. As the checklist §4 G-3 row records, the specificity leg as written cannot reach p_plac ≤ α for GF-1/GF-4T/R8 — so under this G-1 ruling those constructs would be retired by construction unless G-3 is fixed before the freeze *(GF-1's part was subsequently fixed by the G-3 ruling of the same date — 132-set phase-shift family; GF-4T/R8 was fixed by the same day's G-3 GF-4T/R8 ruling — 162-set rigid-translation family)* |

<!-- END VERBATIM PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md -->

**VERBATIM — operator rulings of 2026-09-19, §1–§2 (all addenda):**

<!-- VERBATIM PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md lines 19-93 -->
#### 1. GF-10 rulings

| ID | Question | RULING | Options not chosen |
|---|---|---|---|
| **OPEN-K(a)** | Eligibility instant for a formation week with no P1 event | **A1 — state on the week's last session.** The stock is eligible iff a qualifying candidate (S9 BULL ∧ K3 decline, or S9 BEAR ∧ K3 rally) is active on the last session D_L of *w*, in the D−1-frozen state used on D_L. OPEN-11's "last eligible trading session" means the last **NSE** session of the week | A2 (state after close(D_L)); B (any session of *w*) |
| **K(a)-P1** | Candidate with an empty reference universe (𝒰_T = ∅; OPEN-1 = A "cannot trigger") | **Eligible → 0** | Ineligible → excluded |
| **K(a)-P2** | Later weeks of an episode after its P1 event (λ set) | **Eligible → 0** | Ineligible → excluded |
| **OPEN-K(b)** | O-R10 for a score-0 stock-week | **OPEN-12b/c/d applied at f_w = close(D_L)** in place of t_e (the DB-event analogue). The reference is the last swing of the G-2(b) type confirmed ≤ close(D_L⁻). A penetration in (d_ref, f_w] gives 0. The result is 1 iff the first penetration after f_w falls in the next five sessions | Memo §7 as written (no prior-penetration rule) |
| **OPEN-K(c)** | Two P1 events of one stock in one formation week | **The first event** (smaller t_e) anchors O-R10 and its direction. The later event is recorded, not scored | Last event; exclude the stock-week |
| **RR-1** | Is a low equal to x_ref (bear: a high equal) a penetration? | **No — strictly beyond** (L < x_ref; bear H > x_ref) | Touch counts (≤ / ≥) |
| **RR-2** | An HF event whose reference first breaks later the same session | **Literal: y = 0.** The first post-event penetration must fall inside O_1 … O_5 | Window-only reading |
| **OPEN-L** | Outcome input to the time-vs-price contrast | **One shared outcome anchored at f_w for both legs.** Every contrast stock-week uses O-R10 per the OPEN-K(b) rule at f_w, so T(time) − T(price) differs only in the score | Per-leg anchors at the P3/P4 instants. A third option, reusing the P1-based y, was excluded because the contrast may not read P1 |

**Derived with the rulings (no new choice):**
- Under A1, a score-0 observation always has a unique direction, the active candidate's.
- By the same derivation as v0.7 §3.10, the reference of a 0 is the swing immediately preceding the
  active candidate's starting extreme. A 1 and a 0 on the same candidate therefore use the same
  reference.
- K(a)-P1 and K(a)-P2 make structural zeros part of the primary 0 population: stock-weeks that could
  not have scored 1. This must be disclosed in the report. It is not a defect to revise after results.
- The contrast's 0s use the same A1 instant, applied to contrast-eligible candidates. Unmatched
  candidates stay out of P3/P4 (NC-8). The primary and contrast 0 populations therefore differ by
  design (NC-13/NC-14).

**Addendum (same day, after the GF-10 v0.8 audit):**

| ID | Question | RULING | Options not chosen |
|---|---|---|---|
| **OPEN-N** | Direction of a contrast stock-week whose contributing candidates have opposite directions | **Exclude** the stock-week from the contrast | First contrast instant; A1 state on D_L |
| **RR-3** | What T(·) is in R-10's contrast T(time) − T(price) | **Ratified:** T(leg) = the T_c formula on the leg's score and the shared y, per profile, 20-name floor | Another statistic |

#### 2. Rulings for all three primaries

| ID | Question | RULING | Options not chosen |
|---|---|---|---|
| **OPEN-M** | Outcome window running past the sample end Z | **Exclude** any observation whose O_5 > Z. This is decidable from the NSE calendar alone, and no session after Z is read. Applies to GF-1, GF-4T/R8 and GF-10 | Truncate at Z; read past Z |
| **CAL-1** | The week a Sunday NSE session belongs to | **ISO Monday–Sunday.** A Sunday session is the last session of its week, and f_w is its close | Sunday–Saturday |
| **R-11** | Freshness of equity EOD 2023-01-02 → 2026-09-11 | **Signal-spent** (the audit finding accepted). The span can host only non-confirmatory use | Defer |
| **G-4** | GF-10 contrast p-value | **Raw difference rank.** Δ = T(time) − T(price) on real data; Δ_b is the same quantity on each of the B = 1999 joint surrogate panels; p = (1 + #{b : Δ_b ≥ Δ}) / (B + 1), one-sided | Studentized difference |
| **G-5** | Missing-bar "block neighbourhood" | **Nearest existing bar of that stock within the same drawn block**, ties to the earlier bar. If the block holds none, the stock is missing on that surrogate date | Seeded random within the block |
| **G-6a** | Formation-eligibility burn-in | **None extra.** A stock enters as soon as its state rules make it eligible. Left-censoring is carried by the existing labels (R-3) | 252 or 126 sessions |
| **G-6b** | Minimum eligible names per formation date | **20.** Dates with fewer than 20 eligible names are dropped from T_c (per construct; per profile for GF-10) | 10; 30 |
| **G-7** | CA exclusion window for non-ratio corporate actions | **Full span.** Exclude any observation whose full dependency span, from its earliest anchor or reference date through O_5, contains a non-ratio ex-date | ±5 or ±20 sessions |
| **P-2** | External CA enumeration (Nifty-100 PIT names, 2011-03-25 → 2022-12-30; CA metadata only) | **AUTHORIZED** | Not now |
| **G-8** | Seed for B = 1999 | **42** | 20260919 |
| **G-9a** | Size-check inner draws | **Full B per construct.** Each of the 200 pseudo-real panels is tested with its own B = 1999 surrogates, exactly as the real test | Inner B = 199 |
| **G-9b** | Size-check failure action (rejection > 2α) | **Stop that construct.** It is not screened, and a size-check failure is recorded. No respecification in Stage 1 | Respecify and re-freeze; proceed with disclosure |

**Consequences to carry into the freeze (derived, not new choices):**
- **R-11 = signal-spent.**
  - No fresh Nifty-100 equity EOD window exists for a confirmatory Gann test.
  - The 2011–2022 screen stays non-confirmatory (R-12).
  - Any confirmatory pre-registration needs a window that does not yet exist, such as forward data
    after 2026-09-11.
- **G-7 = full span.** The "earliest anchor or reference date" must be transcribed per construct. The
  following reading is **for operator confirmation at freeze review**:
  - GF-1: the date of the running all-time extreme it counts from;
  - GF-4T/R8: the date of the confirmed K3 swing anchor;
  - GF-10: the earliest of X_ref's date and the start of the earliest ledger member in 𝒰_T ∪ 𝒰_P.
  - For GF-1 a single demerger can exclude a stock for years. This is accepted by the ruling.
- **OPEN-M = exclude.** Because this exclusion depends only on the calendar, the last formation weeks
  of the screen (O_5 > 2022-12-30) are dropped for all three primaries.

**P-2 addendum (same day, after the enumeration ran — `PTMS_GANN_P2_CA_ENUMERATION_2026-09-19.md`):**

| ID | Question | RULING | Options not chosen |
|---|---|---|---|
| **P2-a** | Are buybacks (40 events) non-ratio G-7 events? | **Not non-ratio.** Listed for completeness only | Non-ratio (exclude) |
| **P2-b** | Are in-kind distributions non-ratio G-7 events? These are bonus debentures via scheme, bonus preference shares and CCDs (5 rows) | **Non-ratio (exclude)** | Not non-ratio |
| **P2-c** | Special dividends identified by the exchange's "special" label only (no size screen, which would need prices) | **Accept text-only** | Add a size screen later |
| **P2-d** | NSE CF-CA as the single authoritative source that closes P-2 | **Accept.** The limitation is disclosed | Require a second source |

Result: **115 distinct (entity, ex-date) G-7 events** among 179 member entities, 2011-03-25 →
2022-12-30. The enumeration is script-generated (`scripts/ptms/enumerate_nonratio_ca.py`) with
SHA-256 provenance for every raw file.
<!-- END VERBATIM PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md -->

---

## 2. Construct set, m and primary cells

### 2.1 Set and multiplicity

| # | Construct | Arm | Rulings |
|---|---|---|---|
| 1 | **GF-1** Master Square time points | GANN-FAITHFUL | R-1, R-2, R-3, R-9(a), G-2(a), G-3 |
| 2 | **GF-4T/R8** Rule 8 day windows | GANN-FAITHFUL | R-1, R-2, R-4, R-9(b), G-2(a), G-3 |
| 3 | **GF-10** Rule 8 time overbalance | GANN-FAITHFUL SOURCE CONCEPT + EXPLICIT OPERATOR/RESEARCH CONVENTIONS | R-1, R-2, R-5 (ruling 7 superseded), R-10, G-2(b), GF-10 record v0.8 |

**m = 3.** Nothing below adds to m. Not in Stage 1:
- **GF-7** and **GF-8 / GF-9** are excluded (R-7, R-6). Any K3-upswing version of GF-7 is Arm 2.
- **GF-5 / GF-6** are **deferred, not retired**. They are never to be described as permanently
  power-infeasible (R-8).
- **GF-2** is excluded. **GF-3, GF-4P, TIM-10** and the point rules are Stage 2 (R-15 open).

Robustness variants are not entries in the multiplicity register (§12).

### 2.2 GF-1 primary cell (memo §11.F with R-3, R-9(a), G-2(a); formation per §6)

- **Anchors.** Each stock's running highest high and running lowest low to date, from its first date
  in the store. They are left-censored at 2011-03-25 or at listing, and the censoring is disclosed per
  stock (R-3). A new extreme replaces its anchor and restarts that anchor's count. An anchor is usable
  only once established.
- **Points.** anchor date + *n* calendar days, *n* ∈ P4 + 144*k* with P4 = {36, 48, 72, 96, 108, 144}
  and *k* = 0, 1, 2, … (R-9(a); calendar days is a **design choice where Gann does not uniquely
  specify one**). The residue-0 point is 144, 288, …, never day 0 (G-3 GF-1).
- **Score** at formation week *w*: 1 if any calendar date in the next 7 days (RR-7) equals a point of
  either anchor, else 0.
- **Eligibility.** A PIT N100 member (RR-7) with a confirmed K3 state (**K3 NO STATE ⇒ ineligible**,
  not 0) and an established anchor.
- **Outcome.** O-R10 per §4 (G-2(a)), window = the five NSE sessions after D_L.

### 2.3 GF-4T/R8 primary cell (memo §11.F with R-4, R-9(b), G-2(a))

- **Anchor.** The most recent confirmed K3 swing high **or** low, whichever is more recent. This
  **last-swing** anchoring is a **design choice where Gann does not uniquely specify it** (R-9(b)).
- **Windows.** The nine printed Rule 8 windows, inclusive, in calendar days from the anchor date, with
  no additional tolerance (R-4): {7–12, 18–21, 28–31, 42–49, 57–65, 85–92, 112–120, 150–157, 175–185}.
  They are one-shot from the anchor: no periodicity, no repetition (G-3 GF-4T/R8).
- **Score** at *w*: 1 if any calendar date in the next 7 days (RR-7) falls inside a window, else 0.
- **Eligibility and outcome:** as GF-1 (K3 NO STATE ⇒ ineligible; O-R10 per §4).

### 2.4 GF-10 primary cell — transcribed from GF-10 record v0.8, NOT from R-5's sentence

**Transcription rule (v0.8 §11.2, freeze-checklist items 2 and 19).** R-5's sentence (memo §11.F)
describes a **state** score. The locked chain replaced it with an **event** score. These supersessions
are cited here, and **R-5's sentence must not be implemented**:

| Lock | Replaces in R-5's cell |
|---|---|
| C-5 / OD-1 | "immediately preceding" → the **greatest** qualifying same-type K3 move in the current episode |
| C-6 / OD-7 | evaluation "at week-end *t*" → the **first objectively observable crossing** |
| OD-4 / λ (with RQ-11 = D) | a run of weeks → **at most one P1 event per episode** |
| OPEN-11a (persistence A) | → a score of 1 **only in the formation week containing the event** |
| OPEN-12a–d; OPEN-K(b) | R-5's outcome sentence → the event-anchored O-R10 (§3.10) and the f_w rule for 0s (§3.11) |

The weeks in which R-5's state score would have printed repeating 1s now print one 1 followed by
structural 0s (NC-25). This is disclosed in the report (X-1).

**The GF-10 primary cell, contrast, outcome and exclusions are the whole of v0.8 §1.1 – §3.12**,
reproduced verbatim below. They comprise **72 locks** (v0.8 §7.8). Parts of the record not reproduced
(§4 state machine, §5 history, §6 checks, §6.11 disclosure notes NC-1 … NC-28, §7 audit, §8 – §11)
are frozen **by reference** at the manifest SHA-256.

*Transcription note (derived, no choice).* The Stage-1 screen window ends at Z = 2022-12-30. The 1m
equity store begins 2023-01-02 (CLAUDE.md, Data Layout). So every screen observation is **DB profile**,
and the HF rules below are part of the definition but are never reached in Stage 1. The operator
ruling R-F records the same ("the screen is DB-only").

**VERBATIM — GF-10 record v0.8, §1 – §3.12 (lines 86 – 538):**

<!-- VERBATIM GF10_MECHANICAL_DECISION_RECORD_v0.8_2026-09-19.md lines 86-538 -->
#### 1. Locked mechanical model

##### 1.1 Causal chain

```text
Authoritative EOD daily bars, R-13 as-of-t basis
  └─► K3 line state and confirmed swing points (R-1)
        └─► confirmed S9; changes only at a K3 switch close (OPEN-3b = A)
              └─► D−1 freeze; historical values re-based to as-of-D (RQ-9 = x)
                    └─► current K3 move from its first-occurrence swing extreme (OPEN-4.1/4.5)
                          └─► episode ledger: members by confirmation/completion close (RQ-1 = A, SC-3 = A); completed ≤ d_S (RQ-5 = A)
                                ├─► R_T = greatest same-type K3 duration on K3 swing dates (OD-1, OPEN-2.4 = A, OPEN-A = A)
                                └─► R_P = one combined maximum (RQ-2 = A) of literal-window magnitudes (RQ-8 = A, OPEN-A = A)
                                    over K3 moves (+ bull reactions: strictly-new-high anchor, top before reaction,
                                    outside-day continuation — RQ-6 = A, RQ-7 = B, OPEN-D = A, OPEN-E = A)
                                      └─► candidate-level conditions TC_M(D) (time) and PC_M(τ) (price)
                                            │   first objectively observable strict crossing (OD-7, OD-9)
                                            │   HF: EOD history + normalized genuine 1m on D; no genuine bar → no price evaluation (RQ-9, OPEN-C = A)
                                            │   DB: EOD
                                            ├─► P1 OPERATIONAL: time crossing ⇒ GF-10 EVENT; time latch λ (OD-4, C-7)
                                            │     HF no-bar session ⇒ no event, λ set (RQ-11 = D)
                                            ├─► P2 OPERATIONAL: price crossing ⇒ price flag, recorded independently; price latch μ (RQ-3 = C, RQ-4 = A)
                                            │     HF substrate start: λ = μ = FALSE (RQ-10 = B, OPEN-G = A);
                                            │     pre-substrate-crossed candidates spent per leg (OPEN-B = B)
                                            └─► P3/P4 FORMAL CONTRAST on matched, substrate-homogeneous candidates (RQ-3 = C, R-10):
                                                  eligibility: active span entirely DB or entirely HF; crossing S_HF ⇒ excluded (OPEN-I(b) = B-ii)
                                                  P3 time score  = TC_M holds for M; independent of λ (OPEN-H = B);
                                                                   HF: recognized only at a genuine 1m bar (OPEN-I(a) = A-ii)
                                                  P4 price score = PC_M holds for M; independent of μ (OPEN-F wording; CONF-1 resolved);
                                                                   HF: genuine 1m bar only (OPEN-C = A, built into PC_M)
                                                  incomplete at the sample end ⇒ right-censored, excluded (OPEN-J)

Timestamps and weekly scores (OPEN-6, OPEN-11):
  every instant = bar end (HF: end of the genuine 1m bar; DB: close of the session)
  s(i, w) = 1 in the formation week containing the P1 event only; 0 eligible, no event; excluded if not eligible
  formation instant f_w = close of the week's last trading session; an event with t_e ≤ f_w belongs to w

Outcome of a P1 event (OPEN-12a–d), in strict time order:
  reference K3 swing confirmed (close ≤ D_e⁻)  →  candidate M formed (close of c)  →  M active (D_e ≥ c⁺)
    →  event observable; t_e = bar end  →  remainder of D_e (never outcome)  →  O_1 … O_5 = next five sessions
    →  O-R10 = 1 iff the reference is unpenetrated through t_e and first penetrated in O_1 … O_5
```

##### 1.2 Stage table with provenance

| # | Stage | Locked content | Provenance |
|---|---|---|---|
| 1 | Data | **HF:** genuine 1m on the observation session for detection; EOD for K3/S9 and all history, pre-substrate allowed. **DB:** EOD where 1m is unavailable. Populations never pooled; HF may use EOD lookback; DB-era observations never become HF events | [LOD] X-1 = A, X-2 = A, RQ-9 = A; [NES] |
| 2 | Price basis | All prices compared on D on the as-of-D basis; HF 1m normalized first | [LOD] R-13, RQ-9 = x; [NES] |
| 3 | K3 | Strict 3-Day Chart (memo §5 rows 1–13) | [GS] Δ2-10; [LOD] R-1; [GS] Δ3-02 |
| 4 | S9 | Confirmed tops and bottoms strictly rising = BULL; strictly falling = BEAR; else NONE; changes only at a switch close | [GS] Rule 9; [LOD] OPEN-3b = A; precondition [NES] |
| 5 | Bear condition | S9 BEAR | [LOD] OD-3; [GS] "declining for a long period of Time"; equivalence [NES] |
| 6 | D−1 freeze | Daily-derived facts on D as of D⁻ | [LOD]; [NES] |
| 7 | Current move | Bull: K3 decline from its swing high. Bear: K3 rally from its swing low | [GS] p. 11, p. 63; [LOD] C-4, OPEN-4.1 |
| 8 | Starting-extreme ties | First occurrence | [LOD] OPEN-4.5; [NES] |
| 9 | Time clock | Integer calendar days from the starting-extreme date to the observation date | [GS] Δ3-06, p. 61; [LOD] OPEN-4.2/4.4 |
| 10 | Termination | Confirmed opposite K3 switch; no intraday break | [LOD] OPEN-4.3 |
| 11 | Episode | Constant S9 ∈ {BULL, BEAR}; resets on reversal or cessation | [LOD] OD-5; [NES] |
| 12 | Membership | By confirmation close (K3 move) or completion close (reaction) in [a, b). SC-3 included; a move confirmed under the previous episode is not carried | [LOD] SC-3 = A, RQ-1 = A; [NES] |
| 13 | Ledger | Completed previous same-type members, completed ≤ d_S; no carryover; the first qualifying move cannot trigger | [GS] Δ2-01/02, Δ2-04; [LOD] OD-1, OPEN-1, RQ-1, RQ-5; [NES] |
| 14 | Time reference | R_T = greatest dur over ledger K3 moves; dur on **K3 swing dates** | [GS] "decline"; [GS] p. 63 (inference); [LOD] OPEN-2.4 = A, OPEN-A = A |
| 15 | Reaction (bull only) | 1–2 consecutive strict LL sessions in a K3 UP line, starting on the session immediately after a session that set a **strictly new** running leg high. Top = that high (reaction-session highs excluded). A reaction session that is an outside day **continues normally** (a following LL is its 2nd session, same top). A 3rd LL → K3 switch | [GS] Δ2-02, Δ2-10, Δ3-01; [LOD] OD-2, OPEN-2.1/2.2/2.3/2.5, RQ-6 = A, RQ-7 = B, OPEN-D = A, OPEN-E = A; [NES] |
| 16 | Magnitudes | Current: P_S to the literal extreme after the start session through the observation instant. Reference K3 move: literal extreme over its window through its terminating close (**not** K3 swing values). Reaction: top − last-session low. HF: EOD history + normalized genuine 1m on D (**no 1m term without a genuine bar**). DB: EOD | [GS] p. 63 (inference); [LOD] OD-8, RQ-8 = A, RQ-9 = A+x, OPEN-A = A, OPEN-C = A; [NES] |
| 17 | Price reference | Bull: one combined maximum over ledger K3 declines and reactions. Bear: maximum over ledger K3 rallies | [GS] Δ2-02; [LOD] C-4, OPEN-2.4, RQ-2 = A; "greatest" for price [NES] |
| 18 | Triggers | Strict `>` | [GS]; [LOD] OD-9 |
| 19 | Event timing | First objectively observable crossing. **Timestamp = bar end** (HF: end of the 1m bar; DB: close of the session, derived) | [GS] (inference); [LOD] OD-7, C-6, **OPEN-6** |
| 20 | GF-10 event (P1) | Time crossing. HF: first genuine 1m bar of the crossing session, t_e = its bar end; no genuine bar → no event, λ set. DB: the crossing session, t_e = its close | [GS] p. 12; [LOD] R-5, R-10, RQ-11 = D, **OPEN-6**; [NES] |
| 21 | Time latch λ | One GF-10 event per stock per episode; reset only at a new episode; HF: FALSE at substrate start. **Governs P1 only** | [GS] "first time" (bear only); [LOD] OD-4/6, C-7, RQ-10 = B, RQ-11 = D, OPEN-H = B; [NES] |
| 22 | Price flag (P2) and latch μ | Recorded independently of time eligibility; independent first-per-episode latch; HF: FALSE at substrate start; not evaluated on no-bar HF sessions. **μ governs P2 only** | [LOD] RQ-3 = C, RQ-4 = A, OPEN-C = A, OPEN-G = A, OPEN-F; [NES] |
| 23 | HF substrate start | λ = μ = FALSE. A candidate whose leg crossing held on a pre-substrate session is **spent for that leg** (no HF event or flag from it; no latch set). Applies to P1/P2. **For P3/P4, every candidate whose active span crosses S_HF is ineligible** (OPEN-I(b) = B-ii), so spent status never reaches P3/P4 | [LOD] RQ-10 = B, OPEN-B = B, OPEN-G = A, X-2 = A, **OPEN-I(b) = B-ii**; [NES] |
| 24 | Formal contrast (P3, P4) | T(time) − T(price) over **contrast-eligible** candidates: matched (𝒰_T ≠ ∅ ∧ 𝒰_P ≠ ∅) **and** substrate-homogeneous over the active span (all DB or all HF). Formed per profile, never pooled. **P3:** whether TC_M holds in the active span, **independent of λ**; in HF, recognized only at a genuine 1m bar (a no-bar date-level crossing is recognized at the next genuine bar in the span, if any). **P4:** whether PC_M holds in the active span, **independent of μ**; in HF, genuine bars only (OPEN-C). Both are candidate-level underlying conditions, not latch or reporting state. P1 is GF-10's primary score; P3/P4 exist only as R-10's specificity contrast. A candidate still active on the last session of the evaluation sample is **right-censored and excluded** (not 0, not carried). Weekly mapping: OPEN-11 (§3.9). Outcome: **one shared y per stock-week at f_w** (OPEN-L, §3.11). p: G-4. T(·) = T_c formula (**RR-3**). Opposite-direction weeks excluded (**OPEN-N**) | [GS] p. 12 ranking only; [LOD] RQ-3 = C, R-10, OPEN-F (wording; CONF-1 resolved), OPEN-H = B, **OPEN-I(a) = A-ii, OPEN-I(b) = B-ii, OPEN-J, OPEN-11**; [NES] |
| 25 | Move reset | Each qualifying K3 move is an independent candidate | [LOD] C-7 |
| 26 | Outcome | **Score-1 week (primary):** O-R10 per R-2 / G-2(b), anchored to the (first, OPEN-K(c)) P1 event: window = the five NSE sessions after D_e (remainder of D_e excluded); reference = last K3 swing of the G-2(b) type confirmed before the event; prior penetration ⇒ 0; 1 iff first penetration (strictly beyond) falls in the window (§3.10). **Score-0 week and every contrast stock-week:** the same rule at f_w (§3.11). O_5 > Z ⇒ excluded (OPEN-M) | [GS] Rule 10 (a separate rule); [NES]; [LOD] R-2, G-2(b), **OPEN-12a = B, 12b = B, 12c = C, 12d = B**, OPEN-6, **RR-1, RR-2, OPEN-K(b), OPEN-K(c), OPEN-L, OPEN-M** |
| 27 | Weekly score | 1 only in the formation week (ISO) containing the P1 event; **0 iff a qualifying candidate is active on the week's last session D_L and there is no event** (A1), including candidates with 𝒰_T = ∅ and post-event weeks of a latched episode; excluded otherwise; f_w = close(D_L); final-session events belong to that week (§3.9) | [LOD] **OPEN-11, OPEN-K(a) = A1, K(a)-P1, K(a)-P2, CAL-1**, G-2(b); [NES] |
| 28 | Panel rules | At least 20 eligible names per formation date, counted on the A1 set, per profile (G-6); no extra burn-in; full-span exclusion for non-ratio CAs (G-7; §3.12) | Panel rulings G-6, G-7 |
| 29 | Contrast statistic | T(leg) = T_c formula on the leg's score and the shared y (**RR-3**); a contrast stock-week with opposite-direction contributors is excluded (**OPEN-N**) | [LOD] RR-3, OPEN-N; [NES] |

---

#### 2. Source fact vs operator decision

| Rule | GANN SOURCE | LOCKED OPERATOR / RESEARCH | NOT ESTABLISHED BY SOURCE |
|---|---|---|---|
| Stocks as well as averages | ✔ p. 11 | — | — |
| Duration vs a previous decline/rally | ✔ Δ2-01 | Greatest; episode; membership; completed ≤ d_S; K3 swing dates (OD-1, OPEN-1, RQ-1, RQ-5, OPEN-A) | All of those |
| Points vs the previous decline or reaction (bull) / a previous rally (bear) | ✔ Δ2-02 | Combined maximum; literal extremes (RQ-2, RQ-8, OPEN-A) | "Greatest" for price; windows |
| Strict exceedance | ✔ | Equality = no trigger | Equality treatment |
| "The first time" | ✔ bear time and price clauses only | λ and μ per episode, both directions; λ/μ govern the operational populations P1/P2 only (OD-4, RQ-4, OPEN-H = B, OPEN-F) | Bull use; scope; any latch in the contrast |
| Time more important than price | ✔ p. 12 (**the ranking only**) | Roles; matched contrast; four populations; candidate-level P3 independent of λ and P4 independent of μ; HF observability in P3; substrate-homogeneous contrast eligibility (R-10, RQ-3, OPEN-F, CONF-1, OPEN-H = B, OPEN-I(a) = A-ii, OPEN-I(b) = B-ii) | Any statistic; the matched set; candidate-level scoring; latch treatment; observability rule; eligibility |
| Calendar days | ✔ p. 61; Δ3-06 | Applied to Rule 8 | Rule 8's own unit |
| High/low measurement | ✔ p. 11, p. 63 (inference) | Running form, literal windows, ties | Form; windows; ties |
| 3-Day Chart | ✔ (discretionary) | Strict K3 | K3 as Rule 8's detector |
| Market state | Rule 9 | S9 | Precondition; bear equivalence |
| Reactions | "decline or reaction"; near-extreme 2-day moves; "3-day reaction" | Bound; ≠ K3; strictly-new-high anchor; top before reaction; outside-day continuation (OD-2, OPEN-2.x, RQ-6/7, OPEN-D/E) | Every mechanical element |
| Episodes, latches, D−1, HF/DB, 1m, basis, substrate start, substrate homogeneity, spent candidates, no-bar rules, termination | — | ✔ | ✔ |
| Rule 10 outcome; horizon; pooling; event-anchored window; reference timing; prior-penetration rule | Separate rule | ✔ (R-2, G-2(b), OPEN-12a–d) | ✔ |
| Bar-end timestamps; weekly score mapping; sample-end censoring | — | ✔ (OPEN-6, OPEN-11, OPEN-J) | ✔ |

---

#### 3. Mathematical definitions

##### 3.1 Primitives

| Symbol | Definition | Provenance |
|---|---|---|
| 𝒟; d⁻; cal(d) | NSE sessions; previous session; calendar date | [LOD] |
| H_d^(D), L_d^(D) | EOD high/low of session d < D, as-of-D basis | [LOD] R-13, RQ-9 |
| h_τ^(D), l_τ^(D) | HF: genuine 1m bar τ on D, normalized to as-of-D | [LOD] RQ-9 = A+x |
| G(D) | HF: TRUE iff D has ≥ 1 genuine (`is_synthetic = FALSE`) 1m bar for the stock | [LOD] RQ-11, OPEN-C |
| LL, HH, HL | Strict day-over-day comparisons on EOD bars | [LOD] R-1 |
| ℓ_d; c; u | K3 line state; down-switch close; up-switch close | [GS] Δ2-10; [LOD] R-1 |
| X⁺ = (h, d_h, c); X⁻ = (l, d_l, u) | K3 swing high/low; first-occurrence dates | [LOD] R-1, OPEN-4.1/4.5 |
| S9_d | Per OPEN-3b = A | [LOD] |
| S_HF | First session of the HF substrate for the stock | [LOD] X-1 |
| A(M) | Active span of M: sessions D ∈ (c, u] | [LOD] OPEN-4.3 |
| prof(D) | Observation profile of session D for the stock: **DB** if D < S_HF (or the stock has no HF substrate), **HF** if D ≥ S_HF. This is the state line "Profile: DB \| HF (from S_HF)" of §4; the observation boundary is S_HF | [LOD] X-1, X-2; [NES] |
| 𝒯_M | HF: the genuine 1m bars τ with d(τ) ∈ A(M) | [LOD] OPEN-I(a) = A-ii |
| ts(τ) | Timestamp of 1m bar τ = its **bar end** (start label + 1 minute for the store's start-labelled bars, resolved through `core/market/bar_labeling.py`) | [LOD] OPEN-6 |
| close(D) | End of session D per `core/market/session_schedule.py` (special sessions by date). The DB instant for session D and the bar end of the daily bar | [LOD] OPEN-6 (DB analogue, derived) |
| e = (M, t_e, D_e) | A P1 event: its candidate, timestamp t_e (HF: ts of the event bar; DB: close(D_e)) and session D_e = d(t_e) | [LOD] OD-7, OPEN-6 |
| w; f_w | Formation week (calendar week); formation instant f_w = close of its last NSE session | [LOD] memo §7, OPEN-11 |
| O_k(e) | k-th session of 𝒟 after D_e, k = 1 … 5 | [LOD] R-2, OPEN-12b |
| X_ref(e) = (x_ref, d_ref) | O-R10 reference swing of e: level and first-occurrence date | [LOD] G-2(b), OPEN-12c |
| sample end Z | Last session of the evaluation sample (for the R-12 screen: 2022-12-30) | [LOD] R-12, OPEN-J |

**Basis note.** Every historical value used on D is expressed as of D. CA exclusion windows are
imported from G-7.

##### 3.2 Episode and membership — unchanged (SC-3 = A, RQ-1 = A)

- E = (σ, a, b) is a maximal [a, b) with S9 = σ ∈ {BULL, BEAR}; reset on reversal or cessation.
- K3 move membership: confirmation close ∈ [a, b).
- Reaction membership: completion close ∈ [a, b). A completion close cannot coincide with a switch
  close. — RESOLVED
- A move confirmed before a is never a member. — RESOLVED

##### 3.3 Current move — unchanged

- M = (X⁺, c, u) bull (S9_c = BULL, member of E), with P_S = h, d_S = d_h. Bear mirror.
- Active on D ∈ A(M) = (c, u].
- S9 constant inside the active span.

##### 3.4 Time leg (OPEN-A = A) — unchanged

| Symbol | Definition | Status |
|---|---|---|
| el_M(D) | cal(D) − cal(d_S) | LOCKED |
| dur(M′) | Bull: cal(d_l′) − cal(d_h′) on the **K3 swing dates**; bear mirror | LOCKED (OPEN-A = A) |
| 𝒰_T(M) | Same-type K3 members of E completed ≤ d_S | LOCKED |
| R_T(M) | max dur over 𝒰_T; undefined if empty | LOCKED |
| TC_M(D) | M active on D ∧ 𝒰_T ≠ ∅ ∧ el_M(D) > R_T | LOCKED |

R_T is constant while M is active (u′ ≤ d_S). — RESOLVED

TC_M(D) is a **date-level** condition. It contains no λ term and no G(D) term. Because el_M rises
strictly with D and R_T is constant, TC_M(D) ⇒ TC_M(D′) for every later active D′ (derived). Its
HF **observability** for the contrast is set by OPEN-I(a) = A-ii (§3.7), not by TC_M itself.

##### 3.5 Magnitudes (RQ-8 = A, RQ-9 = A+x, OPEN-A = A, OPEN-C = A) — unchanged

```
Current bull M, instant τ on session D:
  LowHist_M(D) = min{ L_d^(D) : d_S < d ≤ D⁻ }                               (+∞ if empty)
  HF:  if G(D):  LowObs_M(τ) = min{ l_τ′^(D) : genuine 1m bars τ′ ≤ τ on D }
                 run_M(τ)    = P_S^(D) − min(LowHist_M(D), LowObs_M(τ))
       if ¬G(D): no price evaluation on D                                     (OPEN-C = A)
  DB:  run_M(D) = P_S^(D) − min(LowHist_M(D), L_D^(D))                        (observable at D's close)
Reference K3 decline M′ (literal extreme; OPEN-A = A):
  mag^(D)(M′) = h′^(D) − min{ L_d^(D) : d_h′ < d ≤ u′ }
Reference bull reaction ρ:
  mag^(D)(ρ) = Top_ρ^(D) − L_{s_k}^(D)
Bear: mirrors with highs.
```

**Dual endpoint (OPEN-A = A, disclosed).** For the same reference move, the time leg uses the K3
swing-low date d_l′. The price leg uses the literal minimum over (d_h′, u′], which can fall on an
earlier session than d_l′ (NC-10).

##### 3.6 Reaction (bull only) — RQ-6 = A, RQ-7 = B, OPEN-D = A, OPEN-E = A — unchanged

| Element | Definition | Status |
|---|---|---|
| Running leg high | RH(d) = max{ H_x : x in the current K3 UP line, x ≤ d } | LOCKED |
| Establishing session | Session e with H_e **strictly greater** than RH(e⁻). The up-switch close establishes the line's first RH. An equal high does not establish | LOCKED (OPEN-D = A) |
| Reaction ρ | s₁ = e⁺ (immediately after an establishing session e) with LL(s₁); s₂ = s₁⁺ with LL(s₂) optional; k ∈ {1, 2}; completed at the first following non-LL close; a 3rd consecutive LL → K3 switch | LOCKED (OPEN-2.1/2.3, RQ-7) |
| Top_ρ | H_e (highs of s₁ … s_k excluded) | LOCKED (RQ-6) |
| Outside-day session | If s₁ (or s₂) is LL and also has H > RH, the reaction **continues normally**: a following LL session is the next session of the same ρ with Top_ρ = H_e. The outside day raises RH for **later** reactions only; it does not start a new reaction inside ρ | LOCKED (OPEN-E = A) |
| Establishing inside ρ | Sessions of ρ are never establishing sessions for a reaction that overlaps ρ | RESOLVED (follows from OPEN-E = A) |
| After ρ completes | The completing non-LL session (or any later session) establishes a new anchor only if its high is strictly > RH, where RH already includes any outside-day high inside ρ | RESOLVED (OPEN-D = A with RH definition) |
| Membership / precedence | Completion close ∈ [a, b) (RQ-1); ≤ d_S (RQ-5) | LOCKED |
| Bear HH structures | Not operative | NC-1 |

##### 3.7 Price leg and the formal contrast

| Symbol | Definition | Status |
|---|---|---|
| 𝒰_P(M) bull | Ledger K3 declines ∪ qualifying reactions of E, completed ≤ d_S | LOCKED |
| 𝒰_P(M) bear | Ledger K3 rallies of E, completed ≤ d_S | LOCKED |
| R_P^(D)(M) | One combined maximum of mag^(D) over 𝒰_P | LOCKED (RQ-2 = A) |
| PC_M(τ) | M active on d(τ) ∧ 𝒰_P ≠ ∅ ∧ run_M(τ) > R_P^(D) (HF only when G(d(τ))) | LOCKED (OD-8/9, OPEN-C) |
| Matched candidate | 𝒰_T ≠ ∅ ∧ 𝒰_P ≠ ∅ (⇔ 𝒰_T ≠ ∅, derived v0.3 §3.7) | LOCKED |
| Substrate-homogeneous | prof(D) is constant over D ∈ A(M): **DB-homogeneous** iff u < S_HF (or no HF substrate); **HF-homogeneous** iff min A(M) ≥ S_HF (i.e. c⁺ ≥ S_HF); **crossing** iff min A(M) < S_HF ≤ u | **LOCKED (OPEN-I(b) = B-ii)** |
| CE(M) — contrast-eligible | Matched ∧ substrate-homogeneous. CE(M) assigns M to exactly one contrast, prof(A(M)) ∈ {DB, HF}. A crossing candidate has CE = FALSE and is not reassigned, split or cross-scored | **LOCKED (OPEN-I(b) = B-ii)** |

**Substrate homogeneity principle (OPEN-I(b) = B-ii).** A formal-contrast candidate must have a
homogeneous observation substrate across its active span. Homogeneity is judged on the **active span
A(M) = (c, u]** only. References (R_T, R_P, ledger) built from EOD history before S_HF are permitted
for an HF-homogeneous candidate, because HF may use EOD lookback (X-1 = A, X-2 = A). CE(M) is an
eligibility rule for P3/P4. **It does not invalidate M and has no effect on P1 or P2.**

**The four populations (OPEN-H = B, OPEN-F wording, OPEN-I(a) = A-ii, OPEN-I(b) = B-ii).** These
populations are distinct. None of them is derived from another's latch state.

| Pop. | Name | Membership / value | Latch | Role | Status |
|---|---|---|---|---|---|
| **P1** | Operational GF-10 event population | Per episode E, at most one event: the first observable time crossing by any candidate while λ(E) = FALSE, under the HF/DB, no-bar (RQ-11 = D) and spent-leg (OPEN-B = B) rules of §3.8. **Includes candidates crossing S_HF**, as those rules already provide | λ(E), first-per-episode | GF-10's **primary score** (R-5, R-10) | LOCKED (OD-4, OD-7, C-7, RQ-10, RQ-11, OPEN-B) — unchanged by OPEN-I |
| **P2** | Operational (independent) price-flag population | Per episode E, at most one flag: the first observable price crossing by any candidate while μ(E) = FALSE, **whether or not the candidate is matched or contrast-eligible**, under OPEN-C, OPEN-B and OPEN-G | μ(E), first-per-episode, independent of λ | Recorded fact; not a score | LOCKED (RQ-3 = C, RQ-4 = A, OPEN-C, OPEN-G) — unchanged by OPEN-I |
| **P3** | Contrast time score (candidate-level) | For each candidate with **CE(M)**: s_T(M) ∈ {0, 1}, per profile | **None.** Independent of λ | Specificity contrast only (R-10) | LOCKED (OPEN-H = B, OPEN-I(a) = A-ii, OPEN-I(b) = B-ii) |
| **P4** | Contrast price score (candidate-level) | For each candidate with **CE(M)**: s_P(M) ∈ {0, 1}, per profile | **None.** Independent of μ | Specificity contrast only (R-10) | LOCKED (OPEN-F wording; CONF-1 resolved; OPEN-I(b) = B-ii) |

**Deterministic formulation of P3 / P4, per candidate M with CE(M):**

```
DB-homogeneous M (DB contrast):
  s_T(M) = 1  iff  ∃ D ∈ A(M) : TC_M(D)                             else 0
  s_P(M) = 1  iff  ∃ D ∈ A(M) : run_M(D) > R_P^(D)  (DB rule)        else 0
  instants: the first such session D (instant = close(D), OPEN-6)

HF-homogeneous M (HF contrast):
  s_T(M) = 1  iff  ∃ τ ∈ 𝒯_M : TC_M(d(τ))                           else 0      (OPEN-I(a) = A-ii)
  s_P(M) = 1  iff  ∃ τ ∈ 𝒯_M : PC_M(τ)                              else 0      (OPEN-C = A, built into PC_M)
  instants: the first such genuine 1m bar τ (OD-7); instant = ts(τ), OPEN-6

Crossing M (CE = FALSE): no s_T, no s_P; absent from both contrasts                (OPEN-I(b) = B-ii)

In every case λ and μ are never consulted (OPEN-H = B; OPEN-F).
```

- **HF time observability (OPEN-I(a) = A-ii).** If TC_M first becomes true at the date level on a
  session D with ¬G(D), that date-level crossing is **not** an HF-observable crossing. Because TC_M is
  monotone in D (§3.4), it still holds at every later active session. The time score is recognized at
  the first genuine 1m bar τ ∈ 𝒯_M with d(τ) > D. If no genuine bar remains in A(M), s_T(M) = 0. This
  is the formula above; nothing further is chosen.
- **Symmetry (derived).** With A-ii, the HF time and price legs follow the same rule: each counts only
  at a genuine 1m bar in A(M). A no-bar price crossing surfaces at the next genuine bar through
  LowHist (NC-11), and a no-bar time crossing surfaces at the next genuine bar through TC_M's
  monotonicity. The v0.5 observability asymmetry (v0.5 OPEN-I(a)) is removed.
- **Derived, not chosen (carried from v0.5).** OPEN-H = B asks *"whether the underlying time condition
  TC_M(D) is satisfied for that candidate"*, which is an existential over the active span, so the
  score is a binary indicator. OPEN-F applies the same candidate-level, latch-free treatment to price.
- **Spent flags never reach P3/P4 (derived).** A candidate is time- or price-spent only if it is
  active at S_HF with a crossing on some active D < S_HF (§3.8). Such a candidate is crossing, so
  CE = FALSE (NC-16).
- **Instants and weekly mapping (OPEN-6, OPEN-11; §3.9).** Every P3/P4 instant is a bar end (HF) or a
  session close (DB). s_T(i, w) = 1 in the week containing the P3 instant; s_P(i, w) = 1 in the week
  containing the P4 instant.
- **Statistic and outcome.** p: G-4 (§3.12). Outcome: one shared y per contrast stock-week by the f_w
  rule (OPEN-L, §3.11); the P3/P4 instants set scores, never the outcome. T(·) = the T_c formula
  (RR-3). A stock-week whose contributing candidates disagree in direction is excluded (OPEN-N).
- **Consistency with P1 (derived).** Every P1 event comes from a matched candidate with s_T = 1 at
  the same instant **if that candidate is contrast-eligible**. A later eligible candidate in the same
  episode can have s_T = 1 with no P1 event (NC-13). An eligible HF candidate whose time condition
  first held on a no-bar session has no P1 event (RQ-11 = D) but can have s_T = 1 at a later genuine
  bar (NC-15).
- **Consistency with P2 (derived).** A P2 flag from an eligible candidate implies s_P = 1 for it. An
  eligible candidate can have s_P = 1 with no P2 flag (μ already set). Unmatched and crossing
  candidates can produce P2 flags but contribute nothing to P4.
- **Sample-end censoring (OPEN-J, LOCKED).** A candidate still active on the last session Z of the
  evaluation sample (u > Z) is right-censored: **excluded from P3 and P4**, not scored 0, not carried
  beyond the sample. A candidate with u ≤ Z is complete. The test "still active at Z" needs only
  sessions ≤ Z (u is a confirmation close, observable when it happens), so OPEN-J reads nothing past
  the sample (derived). P1 and P2 are unchanged.

##### 3.8 Events, latches and profile rules (operational populations P1, P2)

| Rule | Definition | Status |
|---|---|---|
| D*_M | min{ D : TC_M(D) } | LOCKED |
| λ(E), μ(E) | FALSE when E opens | LOCKED |
| Latch scope | λ governs P1 only. μ governs P2 only. **Neither is consulted by P3 or P4** | LOCKED (OPEN-H = B; OPEN-F) |
| DB GF-10 event | ¬λ → event at D*_M; λ := TRUE | LOCKED |
| HF GF-10 event | ¬λ ∧ G(D*_M) ∧ D*_M ≥ S_HF ∧ M not time-spent → event at the first genuine 1m bar; λ := TRUE | LOCKED |
| HF no-bar time crossing | ¬λ ∧ ¬G(D*_M) ∧ D*_M ≥ S_HF ∧ M not time-spent → no event; λ := TRUE. **Unchanged by OPEN-I(a)**: the A-ii deferral applies to P3 only, never to P1 | LOCKED (RQ-11 = D) |
| HF price flag | ¬μ ∧ G(D) ∧ PC_M(τ) ∧ M not price-spent → flag at genuine bar τ; μ := TRUE | LOCKED (RQ-4, OPEN-C) |
| HF no-bar price | No evaluation; μ unchanged; D's EOD low enters LowHist from D⁺ | LOCKED (OPEN-C = A) |
| HF substrate start | At S_HF, for every open episode: λ := FALSE, μ := FALSE. K3, S9, ledger and candidates carried from EOD | LOCKED (RQ-10 = B, OPEN-G = A) |
| Spent candidate (per leg) | M active at S_HF is **time-spent** if ∃ D < S_HF with D active and el_M(D) > R_T. It is **price-spent** if ∃ D < S_HF with D active and the EOD run (DB rule) exceeds R_P^(D). A spent leg emits no HF event or flag from M and sets no latch. The other leg of M, and every other candidate, are unaffected. For P3/P4: not applicable, since every spent candidate crosses S_HF and is ineligible (OPEN-I(b) = B-ii) | LOCKED for P1/P2 (OPEN-B = B) |
| Contrast eligibility at S_HF | Every candidate whose active span crosses S_HF, spent or not, is excluded from P3/P4. Its P1/P2 treatment is exactly the preceding rows | **LOCKED (OPEN-I(b) = B-ii)** |
| DB end / separation | DB events stop at the end of DB availability; never pooled with HF. P3/P4 are formed **per profile** from substrate-homogeneous candidates only and are never pooled | RESOLVED; NC-6; OPEN-I(b) = B-ii |


##### 3.9 Timestamps and weekly scores (OPEN-6, OPEN-11) — new in v0.7

**Timestamp (OPEN-6).** A 1m bar τ is observable at ts(τ), its bar end: the 09:15–09:16 bar is
timestamped 09:16. Everything inside τ, including its high and low, is dated ts(τ). A DB observation
is a session. The derived bar-end analogue is close(D), which is v0.6's "observable at D's close".

**Clock unit (draft OPEN-8a, closed by derivation).** el_M(D) = cal(D) − cal(d_S) is an integer number
of calendar days fixed for the whole session D (OPEN-4.2/4.4). The time condition TC_M(D) therefore
holds from the session's first bar or not at all. OPEN-6 sets the **instant** at which a crossing is
recognized and the outcome anchor. It never changes the clock unit. HF P1 event: t_e = ts of the
first genuine 1m bar of D*_M (09:16 when the 09:15 bar is genuine). DB P1 event: t_e = close(D*_M).

**Weekly scores (OPEN-11).**

| Score | Value 1 | Value 0 | Excluded | Source population |
|---|---|---|---|---|
| s(i, w): GF-10 primary | A P1 event of stock *i* with t_e ∈ (f_{w−1}, f_w] | *i* eligible in *w* and no P1 event in *w* | *i* not eligible in *w* | **P1 only** |
| s_T(i, w): contrast time | A P3 instant (§3.7) of a CE candidate of *i* in (f_{w−1}, f_w] | per OPEN-11 | not eligible, or the candidate is OPEN-I(b)-crossing or OPEN-J-censored | **P3 only** |
| s_P(i, w): contrast price | A P4 instant of a CE candidate of *i* in (f_{w−1}, f_w] | per OPEN-11 | as s_T | **P4 only** |

- **Persistence A:** the score is 1 only in the week containing the instant. Later weeks of the same
  move or episode do not inherit it.
- **Formation instant:** f_w = close of the last NSE session of calendar week *w* (memo §7; OPEN-11).
  Every bar end on that session is ≤ f_w, so an event anywhere in the final session, including its
  last bar, belongs to *w*. A DB event on the final session has t_e = f_w and also belongs to *w*.
- **Source separation (derived from NC-13, NC-14).** OPEN-11's "event/crossing" is read as: *event* =
  P1 event, for s(i, w); *crossing* = P3/P4 instant, for s_T and s_P. Substituting one for the other
  would break the locked separation of the four populations. **P2 flags are never a score.**
- **A score of 1 is event-based (derived).** It does not re-test eligibility at f_w. A stock whose
  move ended after its event, inside *w*, still scores 1 for *w*.
- **Eligibility of a 0 (OPEN-K(a) = A1).** *i* scores 0 in *w* iff it has no P1 event in *w* and
  E(i, D_L) holds on the week's last NSE session D_L. E(i, D) is PIT membership plus an active candidate
  with (S9 BULL ∧ K3 decline) or (S9 BEAR ∧ K3 rally), read in the D−1-frozen state. Otherwise *i* is
  excluded. Eligibility cannot change inside a session (F-1 of the OPEN-K(a) analysis), so only the
  state on D_L matters. Consequences:
  - a candidate with u = D_L is still active on D_L and counts;
  - a candidate confirmed at c = D_L (first active session in *w*+1) does not.
- **Structural zeros (K(a)-P1, K(a)-P2).** Both of these are eligible, and score 0 when active on D_L:
  - a candidate with 𝒰_T = ∅ (it cannot trigger, by OPEN-1 = A);
  - any week of an episode after its P1 event (λ = TRUE; no further event is possible, by OD-4).

  They are 0s that could not have been 1 (NC-25).
- **Direction of a 0 (derived).** Under A1 the observation's direction is that of the candidate active
  on D_L. S9 is constant within a candidate and only one candidate is active on a session, so the
  direction is unique.
- **Two P1 events in one week (OPEN-K(c)).** The score is 1. The **first** event (smaller t_e) sets the
  direction and anchors O-R10. The later event is recorded, not scored.
- **Calendar (CAL-1).** Weeks are ISO Monday–Sunday. A Sunday session is the last session of its week,
  and f_w is its close.
- **1s and 0s are tested at different instants (disclosed, NC-26).** A 1 is certified at t_e; a 0 is
  tested at D_L.

##### 3.10 Outcome of a P1 event (OPEN-12a–d) — new in v0.7

For a P1 event e = (M, t_e, D_e). Bull is shown; bear mirrors with highs and swing highs.

| Element | Definition | Status |
|---|---|---|
| Direction | Bull (S9 BULL, current K3 decline): the reference is a K3 **swing low**. Bear: a K3 **swing high** | LOCKED (G-2(b)) |
| Reference X_ref(e) | The last K3 swing low whose **confirmation close ≤ close(D_e⁻)**, i.e. the swing in the D−1-frozen state on D_e. Level x_ref^(D) on the common basis; first-occurrence date d_ref | LOCKED (OPEN-12c = C) |
| Excluded swings | Any swing confirmed at close(D_e) or later. HF: close(D_e) > t_e, so the swing is confirmed **after** the event. DB: close(D_e) = t_e, so it is confirmed **simultaneously**. OPEN-12c excludes both. The D−1 freeze excludes the same set (derived) | LOCKED (OPEN-12c; C-3) |
| Penetration | A low **strictly below** x_ref (bear: a high strictly above x_ref) on the intraday high/low basis. Equality is not a penetration | R-2 (intraday basis; "any" = any amount); **RR-1 LOCKED (2026-09-19): strict** |
| Prior penetration | A penetration at any observation in (d_ref, t_e]. HF: EOD sessions d_ref < d < D_e, plus genuine 1m bars of D_e with ts ≤ t_e. DB: EOD sessions d_ref < d ≤ D_e | LOCKED (OPEN-12d = B) |
| Window | O_1 … O_5 = the five sessions of 𝒟 after D_e. The remainder of D_e (instants in (t_e, close(D_e)]) is **not** Session 1 | LOCKED (OPEN-12a = B, OPEN-12b = B; R-2) |
| O-R10 | y(e) = 1 iff there is no prior penetration **and** the first penetration after t_e falls in O_1 … O_5. Otherwise y(e) = 0 | LOCKED (OPEN-12d = B; operator formula) |

**Derived — reference identity.** Swing lows are confirmed only at up-switch closes. D_e ∈ A(M) = (c, u],
and K3 has no switch strictly inside (c, u), so M's own swing low is confirmed at close(u) ≥ close(D_e)
and is excluded. The reference is therefore the K3 swing low confirmed at the **last up-switch before
c**, i.e. the swing low immediately preceding M's starting high X⁺. Bear mirror: the swing high
immediately preceding the current rally's starting low. The reference is fixed for all of M, whatever
session the event falls on.

**Derived — existence.** A P1 event needs 𝒰_T(M) ≠ ∅: a completed same-type K3 member of E, completed
≤ d_S. Its end is a K3 swing low confirmed at an up-switch before c. So X_ref(e) exists for every P1
event, and no P1 event has an undefined reference.

**Derived — EOD form.** On a common basis (below), for bull:

```
y(e) = 1  ⇔  min{ L_d : d_ref < d ≤ D_e } ≥ x_ref   ∧   min{ L_d : d ∈ O_1 … O_5 } < x_ref
```

*Proof by cases.* A penetration before D_e, or on D_e at or before t_e, is prior, so y = 0. A penetration
on D_e after t_e (HF only) is the first post-event penetration and falls outside O_1 … O_5, so y = 0.
Otherwise nothing is penetrated through close(D_e), and y = 1 iff some O_k penetrates. D_e's EOD low
covers every trade on D_e, including every genuine 1m low. Consequences:
- y(e) is the **same rule in HF and DB**. 1m data affects y only through which session D_e is.
- The order of events **inside the event bar** is immaterial: everything in it is dated t_e.
- **No 1m bar after t_e is read** for y. The outcome needs EOD bars through O_5 only.

**Derived — basis.** The test compares the reference with later lows. Ratio adjustment multiplies both
sides of every comparison by the same factor, so y is the same on any single ratio-adjusted basis
dated at or after the last ex-date ≤ O_5 (R-13). Whether events with an ex-date inside (d_ref, O_5] are
excluded is imported **G-7**.

**Derived reading — sessions.** "Full trading session" is read as a whole session of 𝒟: the NSE
calendar, including special sessions. It is the same session set K3 counts. "Full" contrasts with the
remainder of D_e. It is not a minimum-length rule.

**"First penetrated" — RR-2 LOCKED (2026-09-19), literal reading (NC-19).** Under the operator's formula, an HF event whose
reference is first broken later **the same session** scores **0**, not 1: that penetration is the first
one after t_e and it lies outside the window. For DB events this case cannot arise, because t_e =
close(D_e).

**Scope.** This section defines O-R10 for the score-1 weeks of the primary score. §3.11 covers score-0
weeks and the contrast; §3.12 covers exclusions (OPEN-M, G-7).

##### 3.11 O-R10 for score-0 weeks and for the contrast (OPEN-K(b), OPEN-L) — new in v0.8

**The f_w rule (OPEN-K(b)).** This is §3.10 with the instant t_e replaced by f_w = close(D_L), the
DB-event analogue:

| Element | Definition |
|---|---|
| Direction | The direction of the observation (§3.9 for a 0). A contrast week whose contributing candidates disagree is excluded (OPEN-N) |
| Reference | The last K3 swing of the G-2(b) type with **confirmation close ≤ close(D_L⁻)** |
| Prior penetration | Any penetration (strictly beyond, RR-1) in (d_ref, f_w] gives y = 0 |
| Window | O_1 … O_5 = the five sessions after D_L |
| y | 1 iff there is no prior penetration and the first penetration after f_w falls in O_1 … O_5 |

- **Reference identity (derived, same argument as §3.10).** When the observation's candidate M is
  active on D_L, its own swing is confirmed at close(u) ≥ close(D_L) and is excluded. The reference is
  then the swing immediately preceding M's starting extreme, the same swing a P1 event of M would use.
  If a contrast week's crossing candidate ended before D_L, the reference is the last swing confirmed ≤
  close(D_L⁻). That can be the ended candidate's own swing: the rule is applied as written.
- **Existence (derived; closes the question of whether a first candidate has a reference).** A
  candidate is a member only if S9_c ∈ {BULL, BEAR} (§3.3). S9 BULL requires confirmed, strictly rising
  **bottoms**. Those bottoms are swing lows confirmed at up-switches before c. So a swing low confirmed
  ≤ close(D_L⁻) exists for every eligible bull observation. This includes an episode's first candidate
  (𝒰_T = ∅, K(a)-P1) and a stock whose data begin at 2011-03-25 or at listing. Bear mirror (falling
  tops). **No eligible observation lacks a reference.**
- **EOD form (derived).** y = 1 ⇔ min{L_d : d_ref < d ≤ D_L} ≥ x_ref ∧ min{L_d : d ∈ O_1 … O_5} < x_ref
  (bull). The f_w rule never reads 1m data.

**The contrast's outcome (OPEN-L).**
- Every contrast stock-week (i, w) — s_T = 1 or 0, and s_P = 1 or 0 — uses **one** y(i, w), computed
  by the f_w rule.
- T(time) and T(price) are formed from the same (i, w, y) set and differ only in the score column.
- The P3/P4 instants set the scores (§3.9), never the outcome.
- The contrast never reads P1 (Q-7): its y is computed from the f_w rule, not from the primary's
  event-anchored y.
- A contrast 0 is tested by A1 on contrast-eligible candidates. Unmatched candidates stay out of P3/P4
  (NC-8), so the primary and contrast 0 sets differ by design (NC-13/NC-14).

**Primary score-1 weeks are anchored at t_e, everything else at f_w (disclosed).**
- In the primary score, a 1 uses the event-anchored y (§3.10) and a 0 uses the f_w rule. This mixed
  anchoring is a consequence of OPEN-12a + OPEN-K(b) (NC-26).
- The contrast uses f_w throughout, so for the same stock-week, **y in T(time) can differ from y in
  the primary T_c** (NC-27).

##### 3.12 Exclusions and panel rules applied to GF-10 (OPEN-M, G-6, G-7) — new in v0.8

| Rule | Applied to GF-10 |
|---|---|
| **OPEN-M** | Exclude any observation (primary 1 or 0; contrast week) whose O_5 > Z. O_k are counted from D_e (score-1 primary) or D_L (all others) on the NSE calendar alone, so no session after Z is read |
| **G-6a** | No burn-in beyond the state rules. A stock contributes from its first eligible observation; left-censoring labels per R-3 |
| **G-6b** | A formation date enters T_c only if **≥ 20 names** are in the score's population on it: 1s plus A1-eligible 0s. Per profile (DB/HF never pooled). The same floor applies to each contrast leg's per-date set (RR-3) |
| **G-7** | Exclude any observation whose **dependency span** contains a non-ratio CA ex-date. GF-10 span start (the research reading in the rulings file §2, **for operator confirmation at freeze review**): the earliest of d_ref and the start date d_h′ of the earliest member of 𝒰_T ∪ 𝒰_P. The span runs through O_5. For a 0 with 𝒰_T = ∅, the start is d_ref |
| **G-4** | p = (1 + #{b : Δ_b ≥ Δ}) / (B + 1), Δ = T(time) − T(price), B = 1999 joint surrogates, one-sided |

<!-- END VERBATIM GF10_MECHANICAL_DECISION_RECORD_v0.8_2026-09-19.md -->

### 2.5 Memo §11.F cells as originally written (for provenance; superseded where §2.2–§2.4 say so)

**VERBATIM — memo §11.F:**

<!-- VERBATIM PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md lines 464-470 -->
| Construct | Primary cell |
|---|---|
| **GF-1** | Anchor: each stock's all-time-to-date extreme high and extreme low (left-censored at data start; a replaced extreme restarts its count). Score at week-end *t* = 1 if any calendar date in the next 7 days equals anchor date + *n*, *n* ∈ {36, 48, 72, 96, 108, 144} + 144*k*, counted in calendar days, anchor usable only once established. Outcome O-R10 within the next 5 sessions |
| **GF-4T/R8** | Anchor: the most recent confirmed K3 swing high or low. Score = 1 if any calendar date in the next 7 days falls inside {7–12, 18–21, 28–31, 42–49, 57–65, 85–92, 112–120, 150–157, 175–185} calendar days from the anchor date. Outcome O-R10 within the next 5 sessions |
| **GF-10** | Stock in S9 bull state and in a K3 decline. Score = 1 at week-end *t* if the calendar-day duration from the current decline's swing-high date to *t* exceeds the duration of the immediately preceding completed K3 decline, and no up-switch has occurred. Outcome: break of the last K3 swing low within the next 5 sessions. Bear mirror pooled with sign |

Statistic and inference for all: §8.2, α = 0.05/m, m = 3.
<!-- END VERBATIM PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md -->

---

## 3. K3 — the complete algorithm with every IMPLEMENTATION ASSUMPTION

**Frozen:** memo §5 rows 1–13, the "proposed pin" column, as accepted by R-1. The primary is the
literal switch reading of row 11. The symmetric reading is a robustness variant (V-K3, §12). Row 7's
"declared departure" is read as R-1's label. Two open items bear on K3: OPEN-Q (a stock with a missing
bar) and RR-4 (the formation-instant reading).

**Label (travels with every report):** *K3 is an explicitly labelled approximation of Gann's
discretionary historical detector. Gann's own record departs from the strict rule in ≥ 7 of 61 swings
(1912–14; a lower bound, holidays ignored).*

**VERBATIM — memo §5 table:**

<!-- VERBATIM PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md lines 171-185 -->
| # | Item | Gann | Status | Proposed pin (if R-1 accepts strict K3) |
|---|---|---|---|---|
| 1 | Construction | p. 63 rule as above | G (core); exception discretionary | Two-state machine: UP line / DOWN line, updated once per completed session |
| 2 | Swing high | The line's highest top before the switch to DOWN | G | Swing high = max daily high while UP; date = day of that high |
| 3 | Swing low | Mirror | G (by mirror; text is written for the advancing case) | Swing low = min daily low while DOWN |
| 4 | Confirmation timing | Switch happens on the 3rd day | G | Swing extreme **usable from the close of the 3rd qualifying session**; time counts run from the extreme's own date (G, p. 11 "from any high or low"); causality lag is required (IA) |
| 5 | Equal highs / lows | Silent | **IMPLEMENTATION ASSUMPTION** | Strict inequality; an equal value breaks the run |
| 6 | Gaps | Silent | **IMPLEMENTATION ASSUMPTION** | No special handling; daily high/low as recorded |
| 7 | 2-day exception | "sometimes", "we wish to catch a turn", "especially if the fluctuations were very wide"; applied in the record including cases not shown to be near extremes (F1, F2) | **Discretionary — not mechanizable** | Not applied. **Declared departure**; any mechanized exception rule would be an invention (Arm 2) |
| 8 | Initialization | Silent | **IMPLEMENTATION ASSUMPTION** | No state until the first 3-session run of higher highs + higher lows, or of lower lows; first swing extreme usable only after the first switch; per-stock burn-in from its data start |
| 9 | Calendar vs sessions | Construction counts "days" of price bars; time periods are calendar days (p. 61; F7) | G for time counting; **IA** for construction on a 5-day NSE week (F20) | Runs counted in consecutive NSE sessions; all durations in calendar days |
| 10 | Construction vs time-counting | Distinct in the text | G | As item 9 |
| 11 | Up-switch vs down-switch conditions | Up: higher bottoms **and** higher tops. Down: "3 days lower Bottoms" only | **Ambiguous** (literal asymmetry or shorthand) | **IMPLEMENTATION ASSUMPTION**: literal — up needs HH+HL, down needs LL (and mirror: from DOWN, switch up needs HH+HL; from UP, switch down needs LL). Symmetric HH+HL / LL+LH as robustness |
| 12 | Day-over-day comparison | "higher Bottoms and higher Tops for 3 consecutive days" | **IA** | Each session vs the previous session |
| 13 | Outside / inside days | Silent | **IMPLEMENTATION ASSUMPTION** | Outside day (HH + LL): extends a DOWN run's lower-low count and breaks an UP-switch run; inside day breaks both runs |
<!-- END VERBATIM PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md -->

**S9 (GF-10 only):** as v0.8 §1.2 row 4 (§2.4 above). S9 is **not** used for the direction of GF-1 or
GF-4T/R8 (G-2(a)).

---

## 4. O-R10 — the outcome, per construct

**Frozen:** R-2 (Rule 10 minor-trend outcome; binary; **any** penetration; intraday high/low basis;
the next 5 sessions; report wording "minor change in trend"; no main-trend outcome) and G-2, verbatim
below.

**Per-construct anchoring (G-2's recorded observation: "The freeze transcription must state each
construct's anchor explicitly so the two cannot drift together"):**

| | GF-1 and GF-4T/R8 | GF-10 |
|---|---|---|
| Direction set by | **Contemporaneous K3 line state** at *w* (RR-4). **S9 not used** | The observation's candidate: **S9 BULL ∧ K3 decline** → bull; **S9 BEAR ∧ K3 rally** → bear (G-2(b)) |
| Reference, "up" case | K3 UP → the last K3 **swing low** | Bull → the K3 swing low immediately preceding the current decline's starting high. The K3 **line** is DOWN at this point, but the reference is still the swing **low** (G-2 recorded observation) |
| Reference, "down" case | K3 DOWN → the last K3 **swing top** | Bear → the swing high immediately preceding the current rally's starting low |
| K3 NO STATE / S9 NONE | Ineligible, not 0 | Ineligible, not 0 |
| Reference read as of | close(D_L) including D_L (RR-4, for ratification) | Confirmation close ≤ close(D_e⁻) for a 1; ≤ close(D_L⁻) for a 0 and for contrast weeks (OPEN-12c; OPEN-K(b)) |
| Window anchored at | D_L: O_1 … O_5 = the five sessions after D_L | Score 1: D_e (OPEN-12a/b). Score 0 and contrast: D_L (OPEN-K(b), OPEN-L) |
| Penetration | Any amount, intraday basis (R-2); strictness per **RR-5** (for ratification) | **Strictly beyond** (RR-1) |
| Prior penetration | Per **RR-6** (literal G-2(a): none; for ratification) | A penetration in (d_ref, t_e] (or (d_ref, f_w]) gives y = 0 (OPEN-12d; OPEN-K(b)); RR-2 literal |
| Opposite-direction O-R10 event | Not applicable (one direction per stock-week) | Outcome **0** (G-2(b)) |
| Pooling | One per-date IC per construct | Bull and bear pooled into **one** per-date Spearman IC. GF-10 stays one construct |

**VERBATIM — ruling register, G-2 block:**

<!-- VERBATIM PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md lines 216-232 -->
#### G-2 — O-R10 direction (GF-1 / GF-4T/R8) and GF-10 bear-mirror pooling

**RULED by the operator 2026-09-15** — closes freeze checklist G-2. Recorded as the operator's
**pre-result specification**: it is **not** an empirical result, and it is **not claimed to have
been literally explicit in Gann's original text**. It was chosen because it is compatible with the
existing frozen constraints (R-1 K3, R-2 binary O-R10, memo §8.2 single pooled T_c, R-5 GF-10 cell).
It supersedes the parenthetical in R-2's RULING row and resolves freeze checklist §4 G-2.

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** (a) **GF-1 and GF-4T/R8:** the **contemporaneous K3 line state** determines the O-R10 direction — **K3 UP** → outcome = 1 iff the last K3 swing low is penetrated intraday within the next 5 sessions; **K3 DOWN** → outcome = 1 iff the last K3 swing top is penetrated intraday within the next 5 sessions; **K3 NO STATE** → no eligible directional outcome. **S9 is not used for GF-1/GF-4T/R8 direction.** (b) **GF-10:** the state-conditioned binary pooling (audit formulation A1) — **S9 bull + K3 decline** → bull GF-10 score/outcome; **S9 bear + K3 rally** → mirrored bear GF-10 score/outcome; the score stays binary {0,1}; the outcome stays binary {0,1}; bull outcome = break of the last K3 swing low within 5 sessions; bear outcome = cross of the last K3 swing top within 5 sessions; an O-R10 event opposite to the construct's direction is outcome **0**; S9 no-state stocks and stocks not in the required counter-move are **ineligible, not zero**; bull and bear observations pool into **one per-date cross-sectional Spearman IC**; GF-10 remains **one construct, m stays 3** |
| **Basis** | Freeze checklist §4 G-2; definition §12.1 (O-R10, S9); R-2 ("binary outcome"); memo §8.2 (single pooled per-date T_c); claim register Δ2-01 (Gann's bear-mirror sentence); the G-2(b) pooling audit of 2026-09-15 (A1 identified as the formulation consistent with all frozen constraints) |
| **Recorded observation (not a challenge to the ruling)** | The two limbs anchor the direction differently, by design: GF-1/GF-4T/R8 use the **contemporaneous** K3 line state, while GF-10's outcome follows its ruled cell — for a bull-eligible GF-10 stock the K3 line is DOWN (mid-decline) yet the outcome is the **break of the last swing low** (O-R10's "(trend was up)" reading, i.e. the last **completed** swing direction). The freeze transcription must state each construct's anchor explicitly so the two cannot drift together |
| **Frozen if accepted** | Exactly the RULING text above, transcribed verbatim into the freeze document's items 2 and 4 (primary cells + O-R10 definition), with no further choice |

**Multiplicity:** m remains 3. GF-10's bear mirror adds no multiplicity — GF-10 remains one construct.

<!-- END VERBATIM PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md -->

---

## 5. Anchors, time unit and window lists

**Frozen:** §2.2 (GF-1: R-3 sense, left-censoring, replacement, P4 + 144*k*, calendar days),
§2.3 (GF-4T/R8: last confirmed K3 swing, nine printed windows), §2.4 (GF-10: v0.8 §1.2 rows 7–17).
**Confirmation lag:** memo §5 row 4. A swing extreme is usable from the close of its confirming
session, and time counts run from the extreme's own date. **Every duration is in calendar days;
K3 runs are counted in NSE sessions** (memo §5 rows 9–10).

**Labels:** GF-1's calendar-day unit and GF-4T/R8's last-swing anchoring are *design choices where Gann
does not uniquely specify them* (R-9). GF-1 anchors are left-censored at 2011-03-25 or at listing
(R-3).

---

## 6. Formation schedule and eligibility

| Element | Frozen text | Source |
|---|---|---|
| Panel | Nifty-100 point-in-time membership (`n100_membership`), per stock-entity, time-aware symbol → entity (`symbol_entity_intervals`) | Memo §7; R-13 |
| Calendar week | **ISO Monday–Sunday.** A Sunday session is the last session of its week, and f_w is its close | CAL-1 |
| Formation instant | f_w = close(D_L), where D_L is the last **NSE** session of ISO week *w* | Memo §7; OPEN-11; OPEN-K(a) |
| Session calendar | 𝒟 = NSE sessions, **including special sessions**. Known in-window artifacts: **2012-11-11 is a non-session** (Sunday, 14 gold-ETF rows) and is dropped. **2016-04-19 is a holiday** (NSE/CMTR/31297, 7 Dec 2015). **2016-10-30 (Sunday) is a Muhurat session.** It is the last session of its ISO week. Its session window must come from a stated source, because `SPECIAL_SESSIONS` covers only 2023–2025. That is a **P-3 implementation obligation**, not a definition | R-13 certification; R-13 closure §2; CAL-1 |
| Burn-in | **None beyond the state rules.** A stock enters as soon as its state rules make it eligible. Left-censoring is carried by the R-3 labels | G-6a |
| Minimum names | A formation date enters T_c only if **≥ 20** names are eligible for that construct. GF-10: counted on the A1 set (1s plus A1-eligible 0s), per profile. The same floor applies to each GF-10 contrast leg | G-6b; v0.8 §3.12; RR-3 |
| Eligibility | GF-1 / GF-4T/R8: §2.2, §2.3 (K3 NO STATE ⇒ ineligible). GF-10: OPEN-K(a) = A1, K(a)-P1, K(a)-P2 (v0.8 §3.9) | As cited |
| Membership boundaries | The ±1-month boundaries R5 (2017-05-26) and R7 (2020-09-25 / 2020-11-02) use **the recorded dates**, and this is disclosed. R8 lies outside the window | R-13 closure §3.1 |
| BE series | The 304 BE-series member-days are **eligible sessions** | R-13 closure §3.1 |
| TATAMTRDVR | Included **as its own stock** (2016-04-01 → 2017-09-29), with its close tracking of TATAMOTORS disclosed. The implementation **must not** filter through `universe_eligibility`, which classes it `non_equity_isin` | R-13 closure §3.1 |

**VERBATIM — memo §7, common paragraph:**

<!-- VERBATIM PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md lines 225-228 -->
Common to all three: per-stock construction on the N100 PIT panel; formation at the last session of
each calendar week; outcome **O-R10** = a K3 trend-change signal in the construct's direction during
the next 5 sessions (binary); statistic and inference per §8; eligibility = PIT member with a
confirmed K3 state and the construct's anchor available.
<!-- END VERBATIM PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md -->

---

## 7. Price basis, corporate actions and certification

| Element | Frozen text | Source |
|---|---|---|
| Price basis | **Ratio-adjusted as-of-*t*.** Every price compared on session D is expressed on the as-of-D basis. Derived (v0.8 §3.10): ratio adjustment scales both sides of every comparison, so any single ratio-adjusted basis dated at or after the last ex-date ≤ O_5 gives identical results | R-13; v0.8 §1.2 row 2 |
| Substrate | Store-level N100 × EOD certification complete (2026-09-15; all gates PASS). G1/G3/G5 membership-build gates persisted (`54ef174`), and the rebuild was identity-verified (263 = 263 intervals) | R-13 certification; R-13 closure §1 |
| Non-ratio CA list | **115 distinct (entity, ex-date) G-7 events**, 2011-03-25 → 2022-12-30, from NSE CF-CA. Script `scripts/ptms/enumerate_nonratio_ca.py` (`156a2ce`); the event list `PTMS_GANN_P2_CA_EVENTS_2026-09-19.csv` (the rows with `g7_event = True`) is frozen by the SHA-256 in §0.4 | P-2; P2-a … P2-d |
| Classes | G-7 events: DEMERGER, SCHEME, RIGHTS, SPECIAL_DIVIDEND (the exchange's "special" label only, with no size screen; P2-c), IN_KIND (P2-b). **Buybacks are not G-7 events** (P2-a). Single source NSE CF-CA accepted, limitation disclosed (P2-d) | P2 addendum |
| Exclusion | **Full span.** Exclude any observation whose full dependency span, from its earliest anchor or reference date through O_5, contains a non-ratio ex-date. **Span start per construct: OC-1 (pending)** | G-7 |
| Ratio CAs | Bonus, split and consolidation are handled by the ratio-adjusted basis and are **not** exclusions | R-13 |

**VERBATIM — P-2 enumeration, classes and notes:**

<!-- VERBATIM PTMS_GANN_P2_CA_ENUMERATION_2026-09-19.md lines 13-31 -->
#### Classified events (ratio events and ordinary dividends excluded)

| Class | Events | G-7 status |
|---|--:|---|
| DEMERGER | 5 | **G-7 event** (non-ratio) |
| SCHEME | 12 | **G-7 event** (non-ratio) |
| RIGHTS | 15 | **G-7 event** (non-ratio) |
| SPECIAL_DIVIDEND | 81 | **G-7 event** (non-ratio) |
| IN_KIND | 5 | **G-7 event** (non-ratio) |
| BUYBACK | 40 | Not a G-7 event (operator ruling 2026-09-19) |

#### Classification notes

- Classification is by PURPOSE text only. **Special dividends are those the exchange labels special**; no size screen is applied, because a size screen needs prices, which P-2 excludes.
- One feed row can carry two classes. "Scheme of Arrangement – Bonus Debentures" (NTPC 2015, BRITANNIA 2019/2021) is both SCHEME and IN_KIND. Its G-7 status therefore follows whichever class is non-ratio; both are (IN_KIND ruled non-ratio 2026-09-19).
- `in_membership = no` rows are still in scope. G-7 excludes any observation whose dependency span contains the ex-date, and spans can reach back before a membership start.
- Buybacks are listed for completeness but are **not** G-7 events (operator ruling 2026-09-19).
- Single source, **accepted by the operator 2026-09-19**: the NSE feed is the exchange's own record. The BSE cache in the same directory is a shallow per-scrip summary (the latest few actions) and cannot cross-check 2011–2022.

<!-- END VERBATIM PTMS_GANN_P2_CA_ENUMERATION_2026-09-19.md -->

**VERBATIM — R-13 closure, operator dispositions:**

<!-- VERBATIM PTMS_GANN_R13_LEFTOVERS_CLOSURE_2026-09-19.md lines 77-85 -->
##### 3.1 Operator rulings (2026-09-19)

| Item | Ruling | Not chosen |
|---|---|---|
| ±1-month boundaries in the screen window: R5 (2017-05-26), R7 (2020-09-25 / 2020-11-02). R8 (2023, 2025) falls outside the window and is moot | **Use the recorded dates**, disclosed in the report | Exclude the uncertain month |
| 304 BE-series member-days | **Include** as eligible sessions | Exclude |
| TATAMTRDVR, 2016-04-01 → 2017-09-29 | **Include as its own stock.** Disclose that it tracks TATAMOTORS closely. Note that `universe_eligibility` classes it `non_equity_isin`, so the implementation must **not** filter through that table | Exclude |

**R-13 is fully closed.**
<!-- END VERBATIM PTMS_GANN_R13_LEFTOVERS_CLOSURE_2026-09-19.md -->

---

## 8. Surrogate specification

| Element | Frozen text | Source |
|---|---|---|
| Bar vector | For each session and stock, (ln H/C₋₁, ln L/C₋₁, ln C/C₋₁) | Memo §8.2 |
| Resampling | **Synchronized stationary block bootstrap**: the same resampled date blocks for every stock. Paths are rebuilt per stock from its first observed close and placed on the **real** trading calendar | Memo §8.2; R-14 |
| Mean block length | **20 sessions**, a priori. 5 and 60 are off-path (V-B5, V-B60, §12) | Memo §8.2; R-14 |
| Missing bars | PIT membership and listing masks come from the real calendar. A drawn bar that does not exist is replaced by the **nearest existing bar of that stock within the same drawn block**, ties to the earlier bar. If the block holds none, the stock is missing on that surrogate date (then OPEN-Q applies) | G-5 |
| Draws | **B = 1999**, no extension after seeing p | Memo §8.2; R-14 |
| Seed | **42.** Every random stream is derived deterministically from it. The stream layout is fixed in the P-3 code at its commit | G-8 |
| Identical code | Surrogate panels go through the same K3, anchors, scores, outcomes and exclusions as the real panel (memo §8.2). Which masks travel: **RR-8** | Memo §8.2 |
| p_sur | (1 + #{b : T_c(b) ≥ T_c}) / (B + 1), one-sided | Memo §8.2 |

**VERBATIM — memo §8.2 table and limitation statement:**

<!-- VERBATIM PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md lines 288-304 -->
| Element | Recommendation | Reason |
|---|---|---|
| **Test statistic** | T_c = mean over formation weeks of the per-date Spearman IC (φ) of score vs O-R10 across eligible names | Single statistic, no differencing |
| **Null distribution (mechanics)** | Recompute T_c on **B** surrogate panels through identical code (K3, anchors, scores, outcomes). p_sur = (1 + #{T_c(b) ≥ T_c}) / (B + 1) | Monte Carlo rank test; valid to the extent the surrogate generates data from the null; no normal approximation |
| **Surrogate** | **Synchronized stationary block bootstrap of daily bar vectors**: for each session, the vector (ln H/C₋₁, ln L/C₋₁, ln C/C₋₁) per stock; the **same** resampled date blocks for all stocks; paths rebuilt per stock from its first observed close; placed on the **real** trading calendar (weekends and holidays unchanged, so calendar-day counts behave as in real data) | Preserves each stock's own distribution, intra-bar geometry incl. gaps, volatility clustering up to the block scale, and contemporaneous cross-sectional dependence |
| **Missing bars** | PIT membership and listing masks taken from the real calendar; a stock's drawn bar that does not exist is redrawn from that stock's own bars in the same block neighbourhood (IA) | Small for N100 (most names listed before 2011); declared |
| **Mean block length** | Pinned a priori at **20 sessions**; 5 and 60 reported off the pass path | Not estimated from data. 20 sessions spans Gann's own "11 to 35 days" most-common swing band ([45Y] p. 89), a source-based scale |
| **Draws** | **B = 1999**, fixed seed recorded, no extension after seeing p | At α = 0.0125 (m = 4) the rejection region holds 25 draws; Monte Carlo SE of p at α ≈ 0.0025. At m = 3 (α ≈ 0.0167) the same B is adequate |
| **Gann-specificity (placebo) leg** | On **real** data: T_c recomputed with a pinned placebo point set of matched coverage (GF-1: non-Gann fractions of 144; GF-4T/R8: window set with identical widths, centres shifted to non-Gann day counts). p_plac = rank of T_c among the placebo sets. For GF-10: **Gann's own contrast** — T_c(time overbalance) > T_c(price overbalance), p from the surrogate joint distribution (**R-10**; alternative: ratio placebos 0.75× / 1.33×) | Separates "Gann's numbers matter" from "any swing-timing regularity" |
| **Pass rule** | **Intersection-union test** (confirmatory tests): pass iff p_sur ≤ α **and** p_plac ≤ α. **The screen's kill rule uses the surrogate leg only** (§10) | IUT controls size at α without further adjustment; both nulls must fall. Its power is at most the weaker leg's, and the placebo leg's power is not computable a priori |
| **Date clustering / dependence** | Carried by the synchronized surrogate up to the block scale; no Newey–West or normal approximation | The null spread comes from the resampled panel |
| **Effect size report** | T_c − median T_c(b), with the 2.5–97.5% surrogate interval | **Descriptive only**, off the pass path |
| **Size calibration (pre-read, blind)** | After freeze and before the real statistic is computed: treat 200 surrogate panels as pseudo-real and run the full test; the rejection rate must be ≤ 2α. Record the result before unblinding | Checks the bootstrap test's size on this panel's dependence structure. Computes no real-data score-outcome association |

**Limitation to state in every report:** passing the surrogate leg means the real data differ from a
weakly dependent stationary process in the way the statistic detects. Only the conjunction with the
placebo leg supports Gann-specific content.
<!-- END VERBATIM PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md -->

---

## 9. Specificity legs: placebo families (GF-1, GF-4T/R8) and the GF-10 contrast

| Construct | Specificity leg | p |
|---|---|---|
| GF-1 | The **132-set phase-shift orbit** of P4 modulo 144, computed by rule on **real** data | p_plac = (1 + #{placebo sets with T_c ≥ real T_c}) / (132 + 1); minimum 1/133 |
| GF-4T/R8 | The **162-set rigid-translation family** of the nine-window pattern, d = 1 … 179 less the 17 centre collisions, on **real** data | p_plac = (1 + #{placebo sets with T_c ≥ real T_c}) / (162 + 1); minimum 1/163 |
| GF-10 | Gann's own **time-over-price contrast** (R-10): Δ = T(time) − T(price), where T(leg) = the T_c formula on the leg's score and the shared f_w outcome, per profile, with the 20-name floor (RR-3). Contrast-week exclusions: OPEN-J, OPEN-N, OPEN-M, G-7 | p = (1 + #{b : Δ_b ≥ Δ}) / (B + 1), where Δ_b comes from the B = 1999 **joint** surrogate panels (G-4) |

Each placebo set changes **only** the point set or the window set. Panel, eligibility, anchors,
outcome and exclusions are the primary's. The families are generated by rule, not stored as lists,
and use no RNG. Ratio placebos for GF-10 (R_T × 0.75, × 1.33) are **off-path controls only** (§12),
not the specificity leg (R-10).

**VERBATIM — ruling register, G-3 GF-1 block:**

<!-- VERBATIM PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md lines 235-248 -->
#### G-3 — GF-1 placebo family

**RULED by the operator 2026-09-15.** A **pre-result scientific/operator specification**. (The
GF-4T/R8 part of G-3 was ruled the same day — see the G-3 GF-4T/R8 block below.)

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** The GF-1 specificity placebo family is the **exhaustive phase-shift orbit of P4 modulo 144**, exactly: real P4 offsets are `{36, 48, 72, 96, 108, 144}` calendar days; 144 is represented as residue 0 modulo 144 for phase construction; for every integer `d ∈ {0,…,143}`, `P4_d = {(p + d) mod 144 : p ∈ P4}`; **exclude every `d` for which `P4_d ∩ P4 ≠ ∅`**; therefore the family contains exactly **132 distinct placebo sets** — exhaustive, no subset selection. Each placebo has exactly six distinct offsets per 144-day cycle and repeats with the same unbounded `+144*k` structure as the real GF-1 construct. The real residue-0 point is expanded as `144, 288, 432, …`; it is never interpreted as day 0. No decimal fractions and no rounding convention are used. The null is **P4 phase-specificity**; other Gann day counts, including P8 `{54, 90, 126}`, are NOT excluded from the placebo family. Coverage is structurally matched by construction (same six points per 144-day cycle, same 7-day score window, same repetition and eligibility rules); actual realized coverage is reported as a diagnostic. The 132-placebo family is fixed by this mathematical rule and involves no RNG or seed |
| **Basis** | Freeze checklist §4 G-3; memo §8.2 (*"non-Gann fractions of 144"*, matched coverage, *"p_plac = rank of T_c among the placebo sets"*); definition §2 row 11 (*"avoiding Gann fractions"*); the G-3 family verification of 2026-09-15 (144 − 12 = 132; forbidden shifts = `P4 − P4` = 12ℤ₁₄₄; the disjointness exclusion is the reading that yields 132 and keeps every placebo free of P4 points) |
| **Operator disclosure (recorded)** | The phase-shift null tests whether the specific P4 **phase** is special. It is **not** a test of whether the P4 spacing pattern itself is unique among arbitrary six-point patterns |
| **Statistical consequence** | Under the frozen one-sided +1 rank-p convention, `N = 132` gives minimum placebo p = `1/133 ≈ 0.00752`, below `α = 0.05/3 = 1/60 ≈ 0.01667`; the real statistic must rank first or second of 133 to reject |
| **Frozen if accepted** | Exactly the RULING text above, transcribed verbatim into the freeze document's item 9 (GF-1 placebo sets); the family is computed by the rule, not stored as a hand-written list |
| **Not ruled at the time** | GF-4T/R8's placebo construction was OPEN when this part was ruled — **since ruled by the G-3 GF-4T/R8 block below** (162-set rigid-translation family). G-4 (GF-10 contrast p-value) is untouched by this ruling |

<!-- END VERBATIM PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md -->

**VERBATIM — ruling register, G-3 GF-4T/R8 block:**

<!-- VERBATIM PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md lines 251-424 -->
#### G-3 — GF-4T/R8 placebo family

**RULED by the operator 2026-09-15 — G-3 GF-4T/R8 is CLOSED; G-3 is therefore CLOSED for the
complete Stage-1 primary set.** A **pre-result scientific/operator specification**. Recorded
verbatim:

##### Construction

The GF-4T/R8 specificity placebo family is the **rigid whole-pattern integer translation** of the
complete nine-window Rule-8 pattern.

Let P be the union of:

[7–12], [18–21], [28–31], [42–49], [57–65],
[85–92], [112–120], [150–157], [175–185]

calendar days relative to the most recent confirmed K3 swing.

For integer d:

```
P_d = {[a_i + d, b_i + d]}
```

The nine windows are translated as one rigid object.

Independent per-window shifts are NOT permitted.

Reflection is NOT permitted.

##### Translation domain

The placebo translation domain is:

```
d ∈ {1, 2, ..., 179}
```

d = 0 is the real construct and is excluded.

The upper bound 179 is operator-selected because it is also the intrinsic first full-span /
first-disjoint translation of the construct:

```
P − P = [−178, 178]
```

Therefore d = 179 is the smallest positive integer translation for which the translated pattern is
fully disjoint from the original.

The domain is deliberately bounded at this first full-span displacement.

This is NOT imported from GF-1's 144-periodicity and does NOT imply any periodicity for GF-4T/R8.

##### Non-Gann / centre-avoidance rule

Exclude any translation d for which any translated window centre equals any of the nine original
Rule-8 window centres.

The nine original centres are:

9.5, 19.5, 29.5, 45.5, 61, 88.5, 116, 153.5, 180.

For integer d this excludes exactly:

{10, 16, 20, 26, 36, 43, 55, 59, 64, 65, 69, 79, 108, 119, 124, 134, 144}.

Thus:

```
179 candidate translations
− 17 forbidden centre-collision translations
= 162 distinct placebo sets.
```

N = 162.

The confirmatory minimum N ≥ 59 is therefore satisfied.

##### Overlap

Placebo windows MAY overlap the original Rule-8 windows in covered calendar days.

Covered-day disjointness is NOT required.

This is intentional.

The specificity null tests whether the exact Rule-8 placement is special relative to other
placements of the same rigid nine-window structure, including nearby translations that share some
covered days.

Overlap is therefore part of the pre-specified null and is not leakage, post-result selection, or
double-counting.

##### Interpretation

The null tested by this family is:

**Rule-8 phase specificity within the positive integer rigid-translation domain d = 1…179, with
centre-collision translations excluded.**

It does NOT test:

- uniqueness of the nine-window spacing pattern;
- all possible non-Gann calendars;
- all documented Gann day counts;
- the complete Gann methodology.

The scientific interpretation is:

Does the exact documented Rule-8 placement outperform other positive integer placements of the
identical nine-window structure through the first full-span displacement?

A generic effect of the nine-window pattern that is also present in nearby translations should
therefore not pass this specificity leg.

##### Coverage

Primary structural coverage is 67 calendar days per anchor.

Every rigid translation preserves exactly 67 covered calendar days.

No clipping, wraparound, modulo operation, or coverage tolerance is introduced.

Realized coverage differences caused by anchor replacement or data-span truncation are reported
only as diagnostics and do not alter the placebo-family definition.

##### Periodicity

GF-4T/R8 has NO periodicity.

No modulo arithmetic or +k repetition is permitted.

The placebo pattern is one-shot from the anchor, exactly as the primary construct is one-shot.

##### Reproducibility

No RNG.

No seed.

No subset selection.

No researcher-selected placebo sample.

The family is deterministically generated from the fixed nine-window pattern and the fixed integer
domain d = 1…179, followed by the fixed centre-collision exclusion rule.

All surviving translated sets are distinct.

##### Disclosure

Record explicitly that this test is a **phase-specificity test for the Rule-8 window placement**,
not a test of the uniqueness of the Rule-8 spacing pattern.

Also record explicitly that the use of centre avoidance rather than covered-day disjointness
permits overlap between placebo and real Rule-8 windows by design.

##### STATUS

G-3 GF-4T/R8 is now CLOSED.

G-3 GF-1 remains CLOSED.

G-3 is therefore CLOSED for the complete Stage-1 primary set.

Do not make any other scientific rulings.

| Field | Entry |
|---|---|
| **Basis** | Freeze checklist §4 G-3; memo §8.2 (*"window set with identical widths, centres shifted to non-Gann day counts"*, matched coverage); R-14 (*"GF-4T/R8 shifted windows of equal width"*); the G-3 GF-4T/R8 design and domain audits of 2026-09-15 (`P − P = [−178, 178]`; 17 centre-collision shifts; N = 162 ≥ 59) |
| **Frozen if accepted** | Exactly the RULING text above, transcribed verbatim into the freeze document's item 9 (GF-4T/R8 placebo sets); the family is computed by the rule, not stored as a hand-written list |
| **Not ruled** | G-4, G-5, G-6, G-7, G-8 and G-9 are untouched by this ruling; no other scientific definition changed |

<!-- END VERBATIM PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md -->

---

## 10. Statistic, pass rule, α and the blind size check

| Element | Frozen text | Source |
|---|---|---|
| Statistic | **T_c = the mean over formation weeks of the per-date cross-sectional Spearman IC of the binary score vs the binary O-R10** across eligible names. For binary–binary data, with average ranks, this equals φ. Undefined per-date IC: **OPEN-P** | Memo §8.2; R-14 |
| Dates entering | Formation dates with ≥ 20 eligible names (G-6b), after all exclusions | G-6b |
| α | **0.05/3** per construct, **one-sided** | R-12; m = 3 |
| Confirmatory pass rule (IUT; not used in Stage 1) | Pass iff p_sur ≤ α **and** specificity p ≤ α | Memo §8.2 |
| Screen kill rule | **Surrogate leg only.** A construct survives the screen iff p_sur ≤ 0.05/3. The specificity leg is computed and reported | Memo §10; R-12 |
| Surrogate-pass / specificity-fail | **Retired; may NOT proceed to a confirmatory test** | **G-1** (supersedes memo §10's "operator decision") |
| Size check | After the freeze and **before** the real statistic is computed: 200 surrogate panels are treated as pseudo-real, and each is run through the full test with **its own B = 1999** surrogates (G-9a; RR-8). This is done per construct. The rejection rate must be ≤ 2α. The result is **recorded before unblinding** | Memo §8.2; R-14; G-9a |
| Size-check failure | Rejection > 2α ⇒ **that construct is stopped**: not screened, failure recorded, no respecification in Stage 1 | G-9b |
| Effect size | T_c − median T_c(b), with the 2.5–97.5% surrogate interval. **Descriptive only** | Memo §8.2 |

---

## 11. Screen window, kill rule, wording and what carries forward

| Element | Frozen text | Source |
|---|---|---|
| Window | **2011-03-25 → 2022-12-30.** Z = 2022-12-30 | R-12; memo §10 |
| Sample-end exclusion | Any observation with **O_5 > Z** is excluded, for all three primaries. This is decided from the NSE calendar alone; no session after Z is read. GF-10 P3/P4 candidates still active at Z are right-censored and excluded (OPEN-J) | OPEN-M; OPEN-J |
| Exposure | 2011-03-25 → 2022-12-30 is **signal-spent**. **2023-01-02 → 2026-09-11 is signal-spent** (R-11, ruled 2026-09-19). No fresh Nifty-100 equity EOD window exists for a confirmatory Gann test; **confirmation is forward-only** | R-11; GR-1.3 |
| Kill wording | Report template A.2 (§13), chosen **by rule, never by judgement** | Memo §10; G-1; G-9b |
| Carry-forward | Confirmatory α = **0.05 / m_entered** (m_entered = 3). **No screen estimate may set or narrow a later δ band.** A retired construct is not re-entered under a new name. GR-1.5 disclosure per §16 | Memo §10; template §B |
| Description | The screen must never be described as confirmation, validation or evidence that a Gann construct works | Memo §10 |

**VERBATIM — memo §10 table (superseded rows noted in the template's §C, reproduced in §13):**

<!-- VERBATIM PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md lines 361-375 -->
| Element | Specification |
|---|---|
| **Window** | **2011-03-25 → 2022-12-30 only**, less per-stock burn-in. **Correction:** design doc §E.5 proposed 2011-03-25 → 2026-09-11; that would spend 2023-01-02 → 2026-09-11, the only span that could still be confirmatory (R-11) |
| **Constructs entering** | GF-1, GF-4T/R8, GF-10 (m = 3; m = 4 if GF-7 re-admitted). Pinned before the screen |
| **Statistic** | T_c per §8.2 |
| **Null** | IUT of the surrogate null and the placebo / contrast null, §8.2 |
| **Threshold** | **Kill decision on the surrogate leg only:** a construct survives iff p_sur ≤ 0.05/m, one-sided. The placebo / contrast leg (p_plac ≤ 0.05/m) is computed and reported as a **separate Gann-specificity finding**; it does not retire a construct |
| **Kill rule** | A construct whose surrogate leg does not reject is **retired from forward testing under this protocol**. Report wording: *"no evidence, against a surrogate null, of an effect of the optimistic size that confirmation would need"* — **never** "Gann's rule is false". A construct that survives the surrogate leg but not the placebo leg is labelled *"timing effect not shown to be Gann-specific"*; whether it proceeds to a confirmatory IUT pre-registration is an operator decision (R-12) |
| **Power** | **Proxy for the surrogate leg only** (noncentral t, `gf_screen_power.py`), dev-only window, α = 0.05/4: optimistic 1.00 for all; central GF-1 0.72, GF-4T/R8 0.77, GF-10 0.39 (GF-7 0.34). **These are upper bounds:** n takes no burn-in haircut, and dependence is assumed away. At m = 3 the threshold 0.05/3 is less strict than the 0.05/4 used here, so on that count the figures understate. **The IUT's power is not established** — the placebo leg's power depends on how far Gann's day counts differ from shifted placebo windows, which no stated assumption pins. That is why the kill rule rests on the surrogate leg alone. A central-size effect can still be missed |
| **Surrogate uncertainty** | B = 1999 fixed; +1 rank formula; no extension; size calibration (§8.2) recorded before unblinding |
| **Use of historical N100** | Legitimate: operator exposure ruling ("may be used freely … not pristine confirmation"); GR-1.1, GR-1.4. The window is already signal-spent on this surface, so the screen spends nothing new |
| **Exposure label** | **signal — non-confirmatory (GR-1.4)** |
| **Register row (draft; operator-owned; must be appended before the read)** | `\| G-S1 \| Equity EOD panel (N100 PIT, ratio-adjusted as-of-t) \| 2011-03-25 → 2022-12-30 \| **signal** (non-confirmatory, GR-1.4) \| PTMS-Gann Stage-1 screen: GF-1, GF-4T/R8, GF-10 \| <committed screen script paths> \| <frozen protocol path + SHA-256>; report labelled NON-CONFIRMATORY; feeds no gate \|` — seven fields, matching register §5c (#, Surface, Window, Level, Hypothesis family, Consumer, Evidence) |
| **Selection bias into confirmation** | (1) Confirmation must use disjoint data (2023+ if fresh, else forward). (2) **Confirmatory α = 0.05/m_entered** (pinned before the screen), not 0.05/m_survivors. (3) Winner's curse: the confirmatory δ band must **not** use screen estimates. (4) GR-1.5: the confirmatory pre-registration must disclose the screen and its results |
| **Description** | The screen must never be described as confirmation, validation, or evidence that a Gann construct works |
<!-- END VERBATIM PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md -->

---

## 12. Robustness variants and diagnostics (off the pass path)

**Frozen:** the ruled set and the ratified specifications, verbatim below. Every variant and
diagnostic is **off the pass path**. None enters the multiplicity register. Each changes **only** its
named element. **The set is closed at freeze** (OC-2).

| Construct | Variants and controls | Diagnostics |
|---|---|---|
| All | **V-K3** (symmetric switch); **V-B5, V-B60**: each gets its own B = 1999 run (seed 42) and reports p_sur and effect size (R-A′) | D-ES; D-BH (exclusion-loss share) |
| GF-1 | V1-MD (market days); V1-P8 = {36, 48, 54, 72, 90, 96, 108, 126, 144} + 144*k*; V1-WK and V1-MO (unit resolution: the whole ISO week or calendar month is the point); V1-K3 (anchors at the last confirmed swing high and low) | D-PL; D-AA (history depth < 144 / 144–288 / ≥ 288 weeks); D-PS |
| GF-4T/R8 | V4-WE67; V4-WE72; V4-AS (the union of windows from every confirmed swing); V4-CT = exact-date points {90, 180, 270, 360} from the last swing, 7-day look-ahead, no repetition | D-PL; D-PS |
| GF-10 | V10-IP (the immediately preceding comparator); V10-H15 (h = 15; OPEN-M then applies at O_15); ratio placebos R_T × 0.75 and × 1.33; N-DIR (bull-only and bear-only T_c); N-SZ (T_c without structural zeros) | D-PL; D-PS |

Reporting (R-A): every variant except V-B5/V-B60 reports **T_c and effect size against the primary's
surrogate distribution**, with no per-variant surrogate run. D-PL splits each formation date at the
per-date median **as-traded** close on D_L from `equity_bhavcopy`, with a floor of 10 names per half.
D-PS reports per-stock φ for stocks with ≥ 5 score-1 and ≥ 5 score-0 weeks. Dropped: V10-GP, V10-PO,
V10-DC (not applicable) and V4-IW.

**VERBATIM — robustness list, ground rules (§1):**

<!-- VERBATIM PTMS_GANN_STAGE1_ROBUSTNESS_LIST_DRAFT_2026-09-19.md lines 27-32 -->
| Rule | Source |
|---|---|
| Every variant and diagnostic is **off the pass path**. It is reported alongside the primary and can neither rescue a failed primary nor fail a passed one | Memo §8.2, §11.H item 12; design doc §D.4 heading |
| Variants are **not** entries in the multiplicity register. m = 3 is unchanged | R-12; memo §10 |
| Each variant is computed with the same code, panel, eligibility and exclusions (G-6, G-7, OPEN-M) as its primary, changing **only** the named element | Memo §8.2 ("identical code") |
| The set is closed at freeze: nothing is added after any read | Checklist §5 |
<!-- END VERBATIM PTMS_GANN_STAGE1_ROBUSTNESS_LIST_DRAFT_2026-09-19.md -->

**VERBATIM — robustness list, operator rulings and resulting set (§6, §6.1):**

<!-- VERBATIM PTMS_GANN_STAGE1_ROBUSTNESS_LIST_DRAFT_2026-09-19.md lines 133-156 -->
#### 6. Operator rulings (2026-09-19)

| # | Ruling |
|---|---|
| R-A | Variants report **T_c and effect size only** (effect size against the primary's surrogate distribution). No per-variant surrogate runs |
| R-A′ | **Exception:** V-B5 and V-B60 change only the surrogate draws, so under R-A they would reproduce the primary. They are **exempt**: each gets its own B = 1999 surrogate run (seed 42) and reports p_sur and effect size, off-path and not counted for multiplicity (consistent with R-14, "5 and 60 reported off-path") |
| R-B | **Add V10-IP** (immediately preceding completed same-type K3 move) |
| R-C | **Keep V4-CT** (circle tier D1 + quarters); **drop V4-IW** |
| R-D | **Two variants:** V4-WE67 and V4-WE72 |
| R-E | **Keep** the GF-10 ratio placebos (R_T × 0.75, × 1.33) as off-path controls |
| R-F | V10-DC is **not applicable** to Stage 1 (the screen is DB-only) |
| R-G | D-BH is restated as the **exclusion-loss share**: observations lost to left-censoring labels, the G-6b floor, G-7 and OPEN-M, per construct |
| N | **Add N-DIR** (GF-10 bull-only / bear-only T_c) and **N-SZ** (GF-10 T_c excluding structural zeros) |

##### 6.1 Resulting set (closed at freeze once §6.2 is specified)

| Construct | Variants and controls | Diagnostics |
|---|---|---|
| All | V-K3; V-B5, V-B60 | D-ES; D-BH (exclusion-loss share) |
| GF-1 | V1-MD; V1-P8; V1-WK; V1-MO; V1-K3 | D-PL; D-AA; D-PS |
| GF-4T/R8 | V4-WE67; V4-WE72; V4-AS; V4-CT | D-PL; D-PS |
| GF-10 | V10-IP; V10-H15; ratio placebos × 0.75 and × 1.33; N-DIR; N-SZ | D-PL; D-PS |

Dropped or superseded: V10-GP, V10-PO, V10-DC and V4-IW.
<!-- END VERBATIM PTMS_GANN_STAGE1_ROBUSTNESS_LIST_DRAFT_2026-09-19.md -->

**VERBATIM — robustness specifications S-1 … S-8 and rulings:**

<!-- VERBATIM PTMS_GANN_STAGE1_ROBUSTNESS_SPECS_DRAFT_2026-09-19.md lines 26-119 -->
#### S-1 · V1-P8 — point set P8 (GF-1)

| Field | Draft |
|---|---|
| Basis | Definition §2 row 3: "A wider 'strongest points' set **P8** adds {54, 90, 126} (p. 3)". [MMPTC] p. 3 strongest points 1/4, 1/3, 3/8, 1/2, 5/8, 2/3, 3/4, 7/8, 1 of 144 |
| Specification | P8 = {36, 48, 54, 72, 90, 96, 108, 126, 144} + 144*k* calendar days. Everything else as the primary |
| Readings | None. The arithmetic is fixed by the text (3/8 · 144 = 54, 5/8 · 144 = 90, 7/8 · 144 = 126) |

#### S-2 · V1-WK / V1-MO — weeks and months as the unit (GF-1)

| Field | Draft |
|---|---|
| Basis | Definition §1.2: T ∈ {calendar days, market days, calendar weeks, calendar months}; [MMPTC] pp. 1, 2, 6 ("days, weeks or months") |
| Specification, weeks | The anchor week is the ISO week (CAL-1) containing the anchor date. The point weeks are the anchor week + *n* weeks, *n* ∈ P4 + 144*k*. Score at formation week *w* = 1 if *w* + 1 (the next ISO week, the unit-level analogue of the primary's "next 7 days") is a point week |
| Specification, months | The anchor month is the calendar month containing the anchor date. The point months are the anchor month + *n* months. Score at *w* = 1 if any date in the next 7 days falls in a point month |
| **Reading to ratify (Q-1)** | **(a) Unit resolution** (used above): the whole week or month is the point, so month points flag about 4–5 consecutive formation weeks. **(b) Date-exact:** the anchor date + 7*n* days, or the same day-of-month *n* months later, then the primary's 7-day rule. (b) is closer to day counting; (a) is the literal reading of "weeks/months" as the unit |
| Note | Months reachable inside 2011–2022: *n* = 36, 48, 72, 96, 108 (144 months = 12 years is barely reachable). This is disclosed, not a reason for a choice |

#### S-3 · V1-K3 — K3 turns as GF-1 anchors

| Field | Draft |
|---|---|
| Basis | Design doc §D.4 GF-1 robustness "K3 turns as anchors"; R-9(b)'s rationale for GF-4T/R8 ("any" over all recent swings flags nearly every date) |
| Specification | Two anchors, parallel to the primary's two: the **most recent confirmed K3 swing high** and the **most recent confirmed K3 swing low**. Each is usable from the session after its confirmation close (D−1 freeze). A newly confirmed swing replaces its anchor and restarts the count. P4 + 144*k* calendar days, as the primary |
| Alternative (not drafted) | All K3 turns in a lookback. Rejected on R-9(b)'s own reasoning |

#### S-4 · V4-AS — all-swings anchor (GF-4T/R8)

| Field | Draft |
|---|---|
| Basis | R-9(b) "all-swings variant as robustness"; design doc §D.4 "All K3 turns in the last 185 days" |
| Specification | Anchors are **every** confirmed K3 swing high and low (usable after confirmation). The score is 1 if any date in the next 7 days falls inside any printed window counted from any anchor. **Overlap:** the union of windows; the score stays binary, and nothing is counted twice |
| Derived | "Last 185 days" is non-binding: no window from a swing older than 185 + 7 days can reach the next 7 days, because the largest window ends at 185. The specification needs no lookback parameter |
| Disclosure | R-9 recorded that this variant's coverage approaches 1. That is the reason it is off-path, and it is reported as such |

#### S-5 · V4-CT — circle tier (GF-4T/R8 window set replaced)

| Field | Draft |
|---|---|
| Basis | Definition §5 row 3: "**D1** = {180, 360} (halves), then {120, 240} (thirds) and {90, 270} (quarters) as most important"; row 5: candidate "**D1 ∪ quarters**, justified by Gann's 'most important' wording"; [MMPTC] p. 8: halves, thirds and quarters "most important" |
| Specification | Anchor as the GF-4T/R8 primary (most recent confirmed K3 swing). Points: calendar days from the anchor in the set below. Score at *w* = 1 if any date in the next 7 days equals a point: exact-date points, as in GF-1, with the 7-day look-ahead as the only tolerance. No repetition beyond 360: a newer swing replaces the anchor first in practice, and a count beyond 360 is not scored |
| **Reading to ratify (Q-2)** | The committed text is ambiguous. **(a) {90, 180, 270, 360}**: the literal "D1 ∪ quarters", taking D1 = halves. **(b) {90, 120, 180, 240, 270, 360}**: halves, thirds and quarters, per p. 8's "most important" list, which row 3 also calls D1's tier |

#### S-6 · D-PL — price-level strata (diagnostic, all three)

| Field | Draft |
|---|---|
| Basis | Memo §11.H item 12; [PC37] pp. 11–12 (low-priced vs high-priced stocks) |
| Specification | Each formation week, split the construct's scored stock-weeks at the **per-date median as-traded close** on the formation session D_L (from `equity_bhavcopy`, as-traded). Report T_c separately for the low and high halves |
| Why as-traded | Gann's distinction is the nominal price the market trades at. The adjusted series rescales old prices by later CA ratios and would misplace a stock's level (CLAUDE.md: the 1m store is adjusted, bhavcopy is as-traded). Using the price level as a stratifier only is not a join across a CA |
| Why a median split | Gann's text is binary (low vs high). A per-date split needs no rupee cut-offs, so it avoids the price-unit translation left open by R-15 |
| **To ratify (Q-3)** | The floor per stratum-date. Draft: **10** names, half of G-6b's 20, because each half holds about half the names. Alternative: 20 in each half |

#### S-7 · D-AA — anchor-age strata (diagnostic)

| Field | Draft |
|---|---|
| Basis | R-3 "Frozen if accepted": "anchor-age strata as a pre-specified diagnostic"; memo §11.H item 12: GF-1's early "all-time-to-date extremes are left-censoring artifacts of the 2011-03-25 data start and listing dates" |
| Applies to | **GF-1 only.** GF-4T/R8 and GF-10 anchors are recent K3 swings by construction and are not left-censored in this sense |
| **Reading to ratify (Q-4)** | **(a) History depth** (targets the stated concern directly): stratify each stock-week by the length of the stock's store history at *t*: < 144 weeks, 144–288 weeks, ≥ 288 weeks (Gann squares of 144 in weeks). **(b) Anchor age:** stratify by *t* − anchor date in 144-day squares (first square, squares 2–3, square 4+), assigning a stock-week to the stratum of its **younger** anchor (a stock has two anchors) |

#### S-8 · D-PS — per-stock heterogeneity (diagnostic, all three)

| Field | Draft |
|---|---|
| Basis | Catalogue GX-4 ("required diagnostic"); definition §1.8 |
| Specification | For each stock, the **φ coefficient** (binary score vs binary O-R10) over its scored stock-weeks. Report: the number of qualifying stocks; the median, interquartile range and share of φ > 0; the per-stock list in an appendix. Descriptive only; no test |
| **To ratify (Q-5)** | The minimum per stock to report φ: **≥ 5 score-1 and ≥ 5 score-0 weeks** (draft) or ≥ 10 and ≥ 10. GF-10 has at most one 1 per episode, so a stricter floor leaves few stocks |

---

#### Summary for ratification

| Q | Item | Draft | Alternative |
|---|---|---|---|
| — | S-1 P8, S-3 V1-K3, S-4 V4-AS | As drafted (no genuine alternative in the text) | — |
| Q-1 | S-2 weeks/months resolution | (a) unit resolution | (b) date-exact |
| Q-2 | S-5 circle tier set | (a) {90, 180, 270, 360} | (b) with thirds {120, 240} |
| Q-3 | S-6 floor per stratum-date | 10 | 20 |
| Q-4 | S-7 anchor-age definition | (a) history depth | (b) anchor age, younger anchor |
| Q-5 | S-8 per-stock minimum | ≥ 5 / ≥ 5 | ≥ 10 / ≥ 10 |

#### Rulings (operator, 2026-09-19)

| Item | Ruling |
|---|---|
| S-1, S-3, S-4 | **Ratified as drafted** |
| Q-1 (S-2) | **(a) Unit resolution**: the whole ISO week or calendar month is the point |
| Q-2 (S-5) | **(a) {90, 180, 270, 360}** (the literal D1 ∪ quarters) |
| Q-3 (S-6) | Floor **10** names per stratum-date |
| Q-4 (S-7) | **(a) History depth**: < 144, 144–288 and ≥ 288 weeks of store history; GF-1 only |
| Q-5 (S-8) | Per-stock φ reported for stocks with **≥ 5 score-1 and ≥ 5 score-0** weeks |

With these rulings, the robustness list (item 12) is **fully specified** and closes at the freeze.
<!-- END VERBATIM PTMS_GANN_STAGE1_ROBUSTNESS_SPECS_DRAFT_2026-09-19.md -->

---

## 13. Report template

**Frozen:** template §A (A.0 – A.5) and the supersession table §C, verbatim. The generated report's
`{{…}}` fields are filled **by the screen script only**. These include `{{freeze document path}}` and
`{{digest}}`, which take the values recorded under §18.

**VERBATIM — template §A:**

<!-- VERBATIM PTMS_GANN_STAGE1_REPORT_TEMPLATE_AND_GR15_DISCLOSURE_2026-09-19.md lines 17-103 -->
#### A. Report template (item 13)

##### A.0 Title block (fixed)

> # PTMS — Gann Stage-1 Screen Report — **NON-CONFIRMATORY**
>
> **Label: NON-CONFIRMATORY (GR-1.4). This screen is never confirmation, validation, or evidence
> that a Gann construct works.** *(memo §10 "Description"; exposure label "signal —
> non-confirmatory (GR-1.4)")*
>
> Frozen protocol: `{{freeze document path}}`, SHA-256 `{{digest}}`. Register row G-S1 appended
> `{{date}}` before this read. Script: `{{path}}` at commit `{{sha}}`. Seed 42. B = 1999.

##### A.1 Fixed statements (verbatim in every report)

| # | Statement | Source |
|---|---|---|
| F-1 | "Passing the surrogate leg means the real data differ from a weakly dependent stationary process in the way the statistic detects. Only the conjunction with the placebo leg supports Gann-specific content." | Memo §8.2, limitation statement |
| F-2 | "K3 is an explicitly labelled approximation of Gann's discretionary historical detector. Gann's own record departs from the strict rule in ≥ 7 of 61 swings (1912–14; a lower bound, holidays ignored)." | R-1 ruling |
| F-3 | "GF-1's calendar-day unit and GF-4T/R8's last-swing anchoring are design choices where Gann does not uniquely specify them." | R-9 ruling |
| F-4 | "GF-1 anchors are left-censored at 2011-03-25 or at listing; per-stock left-censoring is disclosed." | R-3 ruling |
| F-5 | "GF-10 = Gann-faithful source concept plus explicit operator/research conventions; it is not Gann's exact rule." | GF-10 record v0.8, construct label |
| F-6 | "Pooling across the Nifty-100 panel is a statistical device for power, not a Gann claim." | Definition §1.8 |
| F-7 | "The 2011-03-25 → 2022-12-30 window is signal-spent on this surface. This screen spends nothing new and can confirm nothing (GR-1.3)." | Memo §10; GR-1.3; R-11 |
| F-8 | "Robustness variants and diagnostics are off the pass path. They are reported alongside the primary and can neither rescue a failed primary nor fail a passed one." | Robustness list §1 |
| F-9 | "A positive result would support Gann-specific content only if the construct beats its placebo or contrast controls as well as the surrogate null on the primary cell. A result driven by a few stocks, or matched under non-Gann scales, fractions or lags, is not Gann-specific." | Definition §9.3 |

##### A.2 Per-construct outcome wording (fixed; chosen by rule, never by judgement)

| Outcome | Wording | Source |
|---|---|---|
| p_sur > 0.05/3 | **Retired from forward testing under this protocol.** *"No evidence, against a surrogate null, of an effect of the optimistic size that confirmation would need."* **Never** "Gann's rule is false" | Memo §10 kill rule |
| p_sur ≤ 0.05/3 and specificity p > 0.05/3 | *"Timing effect not shown to be Gann-specific."* **Retired; no confirmatory test** | Memo §10 wording; **G-1 ruling** (supersedes memo §10's "operator decision", §C) |
| p_sur ≤ 0.05/3 and specificity p ≤ 0.05/3 | *"Survived the non-confirmatory screen on both legs."* Eligible to **propose** a confirmatory pre-registration on disjoint forward data (§B). This is **not** evidence that the construct works | Memo §10; R-12; R-11 |
| Size check failed (> 2α) | *"Size check failed; construct not screened."* | G-9b ruling |

The specificity leg is:
- GF-1: p_plac over the 132-set phase-shift orbit (G-3);
- GF-4T/R8: p_plac over the 162-set rigid-translation family (G-3);
- GF-10: the time-vs-price contrast p (G-4, raw difference rank; T(·) per RR-3).

##### A.3 Section skeleton (every number script-generated)

1. **Protocol and provenance.** The freeze hash, the G-S1 row, the commit, the seed, and the raw-input
   hashes, including the P-2 CA enumeration (`156a2ce`).
2. **Blind size check (recorded before unblinding).**
   - Per-construct rejection rate over 200 pseudo-real panels, each with B = 1999: `{{rate}}` vs 2α.
   - The action taken per G-9b.
3. **Panel and exclusions**, per construct:
   - eligible stock-weeks `{{n}}`;
   - formation dates `{{n}}`, and dates dropped by the 20-name floor `{{n}}` (G-6b);
   - observations excluded by OPEN-M `{{n}}` and by G-7 `{{n}}` (from the 115 G-7 events);
   - GF-10 contrast weeks excluded by OPEN-N `{{n}}`;
   - the exclusion-loss share (D-BH).
4. **Primary results**, per construct:
   - T_c;
   - p_sur;
   - specificity p;
   - effect size T_c − median T_c(b) with the 2.5–97.5% surrogate interval (D-ES);
   - the A.2 outcome wording, selected by rule.
5. **Robustness variants** (F-8 heading repeated). T_c and effect size for each; block-5 and block-60
   also report p_sur (R-A′).
6. **Diagnostics:**
   - price-level halves (floor 10);
   - GF-1 history-depth strata;
   - per-stock φ (≥ 5 / ≥ 5), with the number of qualifying stocks.
7. **GF-10 disclosures** (§A.4).
8. **Limitations** (F-1 … F-9 repeated in full).

##### A.4 GF-10 disclosures (fixed text, with script-filled counts)

| # | Disclosure | Source |
|---|---|---|
| X-1 | **Structural zeros.** The 0 population includes stock-weeks that could not have scored 1: candidates with no earlier same-type move (`{{n}}`) and weeks after the episode's one event (`{{n}}`). A 1 appears once per episode; these zeros can repeat weekly. N-SZ reports T_c without them | v0.8 NC-25; K(a)-P1/P2 |
| X-2 | **Mixed anchoring.** Score-1 weeks measure O-R10 from the event timestamp; score-0 weeks measure it from the week-end | v0.8 NC-26; OPEN-K(b) |
| X-3 | **The contrast's outcome differs from the primary's.** The time-vs-price contrast uses one week-end-anchored outcome for every stock-week | v0.8 NC-27; OPEN-L |
| X-4 | **An event already past its reference scores 0 by construction.** A decline long enough to overbalance in time may have broken the prior swing low first | v0.8 NC-18 |
| X-5 | **Bull and bear pooling.** Gann's wording differs between the bull and bear clauses: "first time" and "at least temporarily" appear only in the bear clauses, "reaction" only in the bull price clause. Pooling is a research decision (G-2(b)). The bear "first time" is mirrored into bull by OD-6. N-DIR reports bull-only and bear-only T_c | Spec draft OPEN-10; OD-6 |
| X-6 | **The outcome anchor differs across primaries.** GF-10 anchors to its event; GF-1 and GF-4T/R8 anchor to the formation week-end | v0.8 NC-22 |
| X-7 | **The 20-name floor is counted on the last-session eligible set** (A1), the narrowest reading | v0.8 NC-28 |

##### A.5 Forbidden phrasing (a generated report must not contain)

- "Gann's rule is false / true", "validated", "confirmed", "works", "edge" (memo §10).
- Any reading of a robustness variant or diagnostic as rescuing or failing a primary (F-8).
- Any reading of screen estimates as a δ band for later confirmation (memo §10, winner's curse).

<!-- END VERBATIM PTMS_GANN_STAGE1_REPORT_TEMPLATE_AND_GR15_DISCLOSURE_2026-09-19.md -->

**VERBATIM — template §C (supersessions):**

<!-- VERBATIM PTMS_GANN_STAGE1_REPORT_TEMPLATE_AND_GR15_DISCLOSURE_2026-09-19.md lines 135-142 -->
#### C. Supersessions applied in this draft (transcription notes, not new decisions)

| Memo text | Superseded by | Used here |
|---|---|---|
| §10 kill rule: surrogate-pass / placebo-fail → "whether it proceeds to a confirmatory IUT pre-registration is an operator decision (R-12)" | **G-1** (2026-09-15): retired, no confirmatory test | A.2 row 2 |
| §10 selection bias (1): "Confirmation must use disjoint data (2023+ if fresh, else forward)" | **R-11 = signal-spent** (2026-09-19) | B consequence 1: forward only |
| §10 window "less per-stock burn-in" | **G-6a** (2026-09-19): no extra burn-in | A.3 item 3 (exclusion-loss share instead) |
| §10 power paragraph (α = 0.05/4, m = 4 if GF-7 re-admitted) | R-7 (GF-7 excluded); m = 3 | Not reproduced; α = 0.05/3 throughout |
<!-- END VERBATIM PTMS_GANN_STAGE1_REPORT_TEMPLATE_AND_GR15_DISCLOSURE_2026-09-19.md -->

---

## 14. Code (P-3) — OUTSTANDING

| Field | Value |
|---|---|
| Stage-1 screen script(s) | `{{P-3: path(s)}}` |
| Commit (clean tree) | `{{P-3: sha}}` |
| Run | **Not run.** Outputs are written by the script only; no hand-edited numbers |

P-3 must implement this document as frozen, including the operator's rulings on §0.3, and nothing
else. Implementation obligations carried from the rulings:
- the 2016-10-30 Muhurat session window comes from a stated source (§6);
- `universe_eligibility` is not used as a filter (§6, TATAMTRDVR);
- D-PL reads as-traded closes (§12);
- no session after Z = 2022-12-30 is read (§11);
- every random stream derives from seed 42 (§8).

---

## 15. Exposure register row G-S1 (P-4) — OUTSTANDING, OPERATOR ONLY

The operator appends the row below to `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` **before any
read**. Research does not edit the register. Draft text from memo §10, with the fields filled from this
document:

`| G-S1 | Equity EOD panel (N100 PIT, ratio-adjusted as-of-t) | 2011-03-25 → 2022-12-30 | **signal** (non-confirmatory, GR-1.4) | PTMS-Gann Stage-1 screen: GF-1, GF-4T/R8, GF-10 | {{P-3 script paths}} | {{this file's path}} + SHA-256 {{§18 digest}}; report labelled NON-CONFIRMATORY; feeds no gate |`

---

## 16. GR-1.5 disclosure text

**Frozen:** template §B, verbatim, with all five consequences, approved 2026-09-19.

**VERBATIM — template §B:**

<!-- VERBATIM PTMS_GANN_STAGE1_REPORT_TEMPLATE_AND_GR15_DISCLOSURE_2026-09-19.md lines 106-131 -->
#### B. GR-1.5 disclosure text (item 16)

**Where it goes:** the prior-exposure section of **any** later pre-registration whose design was
informed by this screen, even if it never reads the screen window (GR-1.5).

> **Prior exposure (GR-1.5).** This hypothesis's design was informed by the PTMS Gann Stage-1
> non-confirmatory screen:
> - Frozen protocol `{{path}}`, SHA-256 `{{digest}}`, read under register row G-S1 on `{{date}}`.
> - The screen used Nifty-100 point-in-time equity EOD data, **2011-03-25 → 2022-12-30**, which is
>   signal-spent (GR-1.3).
> - Its results, reproduced here verbatim from the screen report: `{{per-construct outcome wording,
>   T_c, p_sur, specificity p}}`.
>
> Consequences binding on this pre-registration:
> 1. **No confirmatory read may use 2011-03-25 → 2022-12-30, nor 2023-01-02 → 2026-09-11**, which
>    was ruled signal-spent on 2026-09-19 (R-11). Confirmation must use **forward** data dated after
>    this pre-registration's freeze.
> 2. The confirmatory α is **0.05 / m_entered**, where m_entered is the number of constructs that
>    entered the screen (3), not the number that survived it (memo §10).
> 3. **No screen estimate may set or narrow this hypothesis's effect-size (δ) band** (the winner's
>    curse; memo §10). The band is defended independently of the screen.
> 4. A construct retired by the screen, on either leg (G-1), is not re-entered under a new name. Any
>    materially different construct starts its own pre-registration and multiplicity slot.
>    *(Research proposal, accepted by the operator 2026-09-19.)*
> 5. The RFA power pre-check (CLAUDE.md, RFA section) must be run on the forward window actually
>    available before any construct code is written.
<!-- END VERBATIM PTMS_GANN_STAGE1_REPORT_TEMPLATE_AND_GR15_DISCLOSURE_2026-09-19.md -->

---

## 17. R-11 freshness — SATISFIED

The audit was done on 2026-09-15 (`PTMS_GANN_R11_READER_DATE_AUDIT_2026-09-15.md`). The operator ruled
on 2026-09-19 that 2023-01-02 → 2026-09-11 is **signal-spent**. The consequences are carried in §11 and
§16.

---

## 18. Freeze approval and digest (P-5) — OUTSTANDING

**The digest is not recorded in this file,** because a file cannot contain its own hash. On approval:
1. the operator's §0.3 rulings are written into this file, and the "DRAFT" status line is replaced;
2. the file is committed. Its **SHA-256 is computed over the file exactly as committed** at that
   commit;
3. the digest, the commit and the approval date are recorded in the freeze checklist (item 18) and in
   the G-S1 row (§15). They are **not** added to this file afterwards. Any later edit to this file
   voids the digest.

| Field | Value (recorded outside this file) |
|---|---|
| Freeze commit | `{{P-5}}` |
| SHA-256 of this file at that commit | `{{P-5}}` |
| Operator approval | `{{P-5: date}}` |

---

## 19. GF-10 mechanical definition — LOCKED, transcribed in §2.4

The record is v0.8 (72 locks; audit PASS; OPEN-N and RR-3 ruled 2026-09-19). No GF-10 definition is
open. The GF-10 part of OC-1 (the G-7 span start) is pending. **v0.8 governs over R-5's sentence**
(§2.4).

---

**NO MARKET DATA, OUTCOME, COUNT, IC OR p-VALUE READ. NO CODE RUN EXCEPT TEXT ASSEMBLY. NOT FROZEN.**
