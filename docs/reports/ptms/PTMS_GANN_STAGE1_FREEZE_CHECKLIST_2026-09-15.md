# PTMS — Gann Stage-1 Freeze Checklist

**Date:** 2026-09-15 · **Updated:** 2026-09-19 (all open definitions ruled — `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`; GF-10 items: row 19; §4 OPEN-J / OPEN-6 / OPEN-11 / OPEN-12 added, then
ruled the same day per GF-10 record v0.7; OPEN-K / OPEN-L / OPEN-M added; §6) · **Branch:** `research/ptms-price-time-market-structure`

**Status: NOT A FREEZE. Verdict: NOT READY TO FREEZE (§6).** This checklist lists what must exist
before the Stage-1 freeze document can be written, committed, hashed and approved. It becomes the
freeze only when every row in §3 is SATISFIED and the operator approves it.
- No market data, outcome, signal count or incidence read.
- No backtest, RFA, development screen, surrogate run, size check, optimization or threshold tuning.
- The exposure register was not edited.

**Authority:**
- Rulings: `PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md` (RULING rows, 2026-09-15).
- Freeze items: `PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md` §11.H (items 1–16), §5, §7, §8.2,
  §10, §11.F.
- Exposure: `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` (GR-1).

---

## 1. Stage-1 primary set (ruled)

| # | Construct | Arm | Rulings | Primary cell |
|---|---|---|---|---|
| 1 | **GF-1** Master Square time points | GANN-FAITHFUL | R-1, R-2, R-3, R-9(a) | Memo §11.F: running to-date extreme high and low (left-censored); P4 = {36, 48, 72, 96, 108, 144} + 144*k* calendar days; weekly score; O-R10 in next 5 sessions |
| 2 | **GF-4T/R8** Rule 8 day windows | GANN-FAITHFUL | R-1, R-2, R-4, R-9(b) | Memo §11.F: most recent confirmed K3 swing; nine printed windows, inclusive, calendar days; O-R10 in next 5 sessions |
| 3 | **GF-10** Rule 8 time overbalance | GANN-FAITHFUL (R-5; ruling 7 superseded) | R-1, R-2, R-5, R-10 | Memo §11.F: S9 bull, K3 decline, duration exceeds the immediately preceding completed decline; break of last K3 swing low in next 5 sessions; bear mirror |

**Multiplicity m = 3.** Screen α = 0.05/3 per construct, one-sided. Confirmatory α = 0.05/m_entered.

**Labels that travel with every report:**
- K3 is an *explicitly labelled approximation of Gann's discretionary detector*. Gann's own record
  departs from the strict rule in ≥ 7 of 61 swings (1912–14; lower bound).
- GF-1 calendar days and GF-4T/R8 last-swing anchoring are *design choices where Gann does not uniquely
  specify them*.
- GF-1 anchors are left-censored at 2011-03-25 or listing.

**Not in Stage 1:**

| Construct | Status | Ruling |
|---|---|---|
| GF-8, GF-9 | Arm-1 claims; excluded from Stage 1; deferred research items | R-6 |
| GF-7 | Arm-1 claim; excluded from Stage 1 | R-7 |
| GF-5, GF-6 | **Deferred, not retired** (never "permanently power-infeasible") | R-8 |
| GF-2; GF-3, GF-4P, TIM-10, point rules | Excluded / Stage 2 | R-15 open |

---

## 2. Ruling status

| Ruling | Operator decision | What it still leaves to do |
|---|---|---|
| R-1 | Accepted | Transcribe §5 rows 1–13 into the freeze |
| R-2 | Accepted | Outcome direction for GF-1 / GF-4T/R8 and GF-10 bear pooling **ruled 2026-09-15** (ruling register, G-2 block) — transcribe |
| R-3 | Accepted | Transcribe |
| R-4 | Accepted | Transcribe |
| R-5 | Accepted; ruling 7 superseded | Transcribe |
| R-6, R-7, R-8 | Accepted | None |
| R-9 | Accepted | Transcribe with design-choice label |
| R-10 | Accepted | Contrast p-value formula not written (**G-4**) |
| R-11 | Accepted | **Audit performed 2026-09-15** (`PTMS_GANN_R11_READER_DATE_AUDIT_2026-09-15.md`) — finding: 2023-01-02 → 2026-09-11 signal-spent; audit complete; **freshness ruling still the operator's** |
| R-12 | Accepted in principle only; not to be run | Sub-question **ruled via G-1 (2026-09-15): surrogate-pass / specificity-fail → retired, no confirmatory test**; preconditions P-1 to P-5 |
| R-13 | Accepted | **Store-level N100 EOD certification + in-store CA enumeration COMPLETE 2026-09-15** (`PTMS_GANN_R13_N100_EOD_SCOPED_CERTIFICATION_2026-09-15.md`); external CA enumeration **OUTSTANDING** (operator authorization); G-7 open |
| R-14 | Accepted for finalization only; not to be executed | Placebo sets (**G-3**: GF-1 and GF-4T/R8 families ruled 2026-09-15), missing-bar rule, seed, size-check failure rule (**G-5, G-8, G-9**) |
| R-15 | Open | Stage 2 only |

---

## 3. Freeze checklist (memo §11.H items 1–16, plus items the rulings add)

Status key:
- **SATISFIED**: done and committed.
- **RULED — TO TRANSCRIBE**: fully specified by the rulings and the memo; only needs writing into the
  freeze document, with no new choice.
- **OPEN — DEFINITION MISSING**: needs an operator specification; §4 lists what is missing and does not
  choose it.
- **OUTSTANDING TASK**: work not yet done.

| # | Item | Status | Closed by | Owner |
|---|---|---|---|---|
| 1 | Rulings R-1 → R-14 recorded in writing | **SATISFIED** — R-12's sub-question ruled via G-1 (2026-09-15) | Ruling register; G-1 block | Operator (ruled) |
| 2 | Construct set, m, primary cell per construct | Set and m **SATISFIED**; cells **RULED — TO TRANSCRIBE** (G-2 ruled 2026-09-15) | Ruling register, G-2 block | Research |
| 3 | Complete K3 algorithm incl. every IMPLEMENTATION ASSUMPTION | **RULED — TO TRANSCRIBE** (memo §5 rows 1–13; symmetric switch as robustness) | Freeze doc | Research |
| 4 | S9 state rule; O-R10 (direction, penetration, intraday basis, 5-session horizon) | All elements ruled, including direction (**G-2**, 2026-09-15): contemporaneous K3-line-state anchor for GF-1/GF-4T/R8 (S9 not used); state-conditioned binary pooling for GF-10 — **RULED — TO TRANSCRIBE** | Ruling register, G-2 block | Research |
| 5 | Anchors (sense, left-censoring, replacement, confirmation lag), time unit, window lists | **RULED — TO TRANSCRIBE** (R-3, R-4, R-9; K3 lag memo §5 row 4) | Freeze doc | Research |
| 6 | Formation schedule; eligibility (PIT N100, listing start, burn-in, minimum names per date) | Weekly formation and PIT N100 specified; **G-6 RULED 2026-09-19**: no extra burn-in; minimum 20 eligible names per date. CAL-1 RULED (ISO Mon–Sun) — **RULED — TO TRANSCRIBE** | G-6 | Research |
| 7 | Price basis and CA handling; external CA enumeration with exclusion windows; scoped certification | Price basis ruled (ratio-adjusted as-of-*t*). Store-level certification + in-store CA enumeration COMPLETE (2026-09-15). **G-7 RULED 2026-09-19** (full-span exclusion for non-ratio CAs). **External CA enumeration COMPLETE 2026-09-19** (`PTMS_GANN_P2_CA_ENUMERATION_2026-09-19.md`: NSE CF-CA, 115 G-7 events; P2-a…d ruled). **R-13 FULLY CLOSED 2026-09-19** (`PTMS_GANN_R13_LEFTOVERS_CLOSURE_2026-09-19.md`): G1/G3/G5 persisted (`54ef174`, rebuild identity-verified); 2016-04-19 confirmed (NSE/CMTR/31297); boundary / BE / DVR dispositions ruled — **RULED — TO TRANSCRIBE** | P-2 (external part) | Research |
| 8 | Surrogate spec: bar vector, synchronized stationary bootstrap, mean block 20, missing-bar rule, B = 1999, seed | Bar vector, synchronization, block 20 (5 and 60 off-path), B = 1999 ruled. **G-5 RULED** (nearest bar in block) and **G-8 RULED** (seed 42), 2026-09-19 — **RULED — TO TRANSCRIBE** | G-5; G-8 | Research |
| 9 | Placebo sets (GF-1, GF-4T/R8) and the GF-10 contrast | GF-1 / GF-4T/R8 placebo families ruled (G-3). **G-4 RULED 2026-09-19** (raw difference rank, +1 convention, B = 1999). **OPEN-L RULED** (shared f_w outcome) — **RULED — TO TRANSCRIBE** | Ruling register, G-3 blocks; G-4 | Research |
| 10 | Statistic, IUT pass rule, α, one-sidedness, blind size-check procedure and threshold | Statistic T_c, IUT, α = 0.05/3, one-sided, 200 panels ≤ 2α ruled. **G-9 RULED 2026-09-19** (full B = 1999 per pseudo-real test, per construct; failure → stop that construct) — **RULED — TO TRANSCRIBE** | G-9 | Research |
| 11 | Screen window; kill rule and wording; confirmatory α = 0.05/m_entered; no screen estimates in a later δ band | **RULED — TO TRANSCRIBE** (R-12, memo §10). The surrogate-pass / specificity-fail path is ruled by **G-1** (2026-09-15): such a construct is **retired and may NOT proceed to a confirmatory test** | Ruling register, G-1 block | Research |
| 12 | Robustness list (off the pass path) with pre-specified diagnostics | **Set ruled 2026-09-19** (`PTMS_GANN_STAGE1_ROBUSTNESS_LIST_DRAFT_2026-09-19.md` §6: R-A … R-G, N-DIR, N-SZ). Specifications **ratified 2026-09-19** (`PTMS_GANN_STAGE1_ROBUSTNESS_SPECS_DRAFT_2026-09-19.md`) — **RULED — TO TRANSCRIBE** | Freeze doc | Research → operator |
| 13 | Report template: NON-CONFIRMATORY label, §8.2 limitation statement, K3 approximation label | **APPROVED 2026-09-19** (`PTMS_GANN_STAGE1_REPORT_TEMPLATE_AND_GR15_DISCLOSURE_2026-09-19.md` §A) — **RULED — TO TRANSCRIBE** | Freeze doc | Research |
| 14 | Code committed from a clean tree; outputs written by script only | **DONE 2026-09-19 — NOT RUN.** `scripts/ptms/gann/` at `357174a` (entry point `run_screen.py`, two phases, guarded); synthetic-bar tests only. The readings it needed (PENDING-1/2, IR-1 … IR-5, IR-4b, RB-1 … RB-4) were ruled by the operator (rulings §5) and written into the draft (§0.5) | P-3 | Research |
| 15 | Exposure register row G-S1 appended **by the operator** before any read | **OUTSTANDING TASK** — draft row in memo §10 | P-4 | **Operator only** |
| 16 | GR-1.5 disclosure text for any later confirmatory pre-registration | **APPROVED 2026-09-19** (same file, §B; five consequences) — **RULED — TO TRANSCRIBE** | Freeze doc | Research |
| 17 | R-11 reader-date audit performed and freshness of 2023-01-02 → 2026-09-11 ruled (R-12 precondition) | **AUDIT DONE** (2026-09-15) and **freshness RULED 2026-09-19: signal-spent** — **SATISFIED** | P-1 → `PTMS_GANN_R11_READER_DATE_AUDIT_2026-09-15.md` | Operator (ruled) |
| 18 | Freeze document committed, SHA-256 recorded, operator-approved | **DRAFT WRITTEN 2026-09-19** (`PTMS_GANN_STAGE1_FREEZE_DOCUMENT_DRAFT_2026-09-19.md`; all RULED — TO TRANSCRIBE rows transcribed; 22 verbatim blocks machine-checked against their sources). The freeze-review items (OPEN-P, OPEN-Q, RR-4 … RR-8, OC-1, OC-2) and the P-3 rulings were **ruled 2026-09-19 and applied in the draft**. **Blocked only by item 15**, then operator approval. Record here, at approval: the document's path in backticks with its `docs/reports/ptms/` prefix, the freeze commit and the SHA-256 of its git blob (64 hex), in the form the screen's guard reads (draft §14, §18). The digest is recorded here, not inside the document | P-5 | Operator |
| 19 | GF-10 mechanical definition complete (detector, ledger, legs, latches, P1–P4 populations, formal contrast, timestamps, weekly score, outcome) | **LOCKED — TO TRANSCRIBE** from `GF10_MECHANICAL_DECISION_RECORD_v0.8_2026-09-19.md` (70 GF-10 locks; audit PASS; primary score complete at the definitional level). OPEN-N (exclude) and RR-3 (ratified) **RULED 2026-09-19** — no GF-10 definition open. GF-10 G-7 span start for confirmation at freeze review (v0.8 §3.12). Item 2 caution stands (transcribe from v0.8 §11.2, not R-5) | §4 OPEN-N; RR-3 | Research |

**Screen preconditions (R-12), all unmet:** items 1–19 SATISFIED, including R-11 frozen after its
audit, R-13 complete, and R-14 finalized; G-S1 appended by the operator. The screen then still needs the
blind size check (item 10) recorded before unblinding.

---

## 4. Definitional gaps found while applying the rulings — STOP items, not resolved here

Each gap is a place where the accepted ruling text stops short of an executable definition. **Filling
any of them would invent a scientific definition, so none is filled.** Options are named only where an
existing committed document already names them, and none is recommended.

| ID | Gap | Where the ruling text stops | Why it matters |
|---|---|---|---|
| **G-1 — RESOLVED (operator ruling 2026-09-15; ruling register, G-1 block)** | May a construct that passes the surrogate leg but fails the specificity leg proceed to a confirmatory test? | R-12 was accepted in principle; this sub-question, posed in the ruling sheet, was not answered | Must be fixed before the screen is read. Deciding it after the results would be a post-result selection |
| **G-2 — RESOLVED (operator ruling 2026-09-15; ruling register, G-2 block)** | O-R10 **direction** for GF-1 and GF-4T/R8, and GF-10's **bear-mirror pooling** | O-R10 is "break of the last swing low (trend was up) or cross of the last swing top (trend was down)" with "direction by construct". GF-1 and GF-4T/R8 have no direction of their own. Whether "trend" means the K3 line state or the S9 state is not written: definition §12.1 says "on K3", while GF-10 uses S9. S9 can be "no state". GF-10's "bear mirror pooled with sign" does not say how a binary score and a direction-specific binary outcome are pooled in one per-date IC | It changes the outcome variable itself, for all three primaries |
| **G-3 — RESOLVED (operator rulings 2026-09-15; ruling register, G-3 blocks): GF-1 (132-set phase-shift orbit) and GF-4T/R8 (162-set rigid-translation family) both ruled** | **Placebo sets** for GF-1 and GF-4T/R8 | Memo §8.2 says "non-Gann fractions of 144" and "window set with identical widths, centres shifted to non-Gann day counts", with matched coverage. Definition §2 (GF-1) row 11 gives fractions only as "e.g. 0.29, 0.41, 0.59, 0.71, 0.83". No committed text pins the fractions, the shifted centres, the coverage-matching rule, or the **number of placebo sets** | p_plac is "rank of T_c among the placebo sets". **Arithmetic:** under R-14's one-sided +1 rank p-values, a rank p over N sets is at least 1/(N+1). To reach α = 0.05/3 = 1/60 needs **N ≥ 59**. Five exemplary fractions could never reject. This binds **GF-1 and GF-4T/R8 only**: GF-10's contrast takes its p from the B = 1999 surrogate draws (G-4). Consequences: for those two constructs the confirmatory IUT (p_sur ≤ α **and** p_plac ≤ α) cannot pass as specified, and every one would be a specificity-fail by construction, which makes G-1 more urgent. **G-3 is a rule that cannot fire, not merely a missing value** |
| **G-4** — **RESOLVED (operator ruling 2026-09-19; `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`)** | GF-10 time-over-price **contrast p-value** | R-10: "contrast statistic = T(time) − T(price); one-sided p from the surrogate joint distribution". No formula names the reference quantity or the null it tests | The one GF-10 specificity decision must be computable exactly as frozen |
| **G-5** — **RESOLVED (operator ruling 2026-09-19; `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`)** | **Missing-bar rule** | Memo §8.2: a drawn bar that does not exist "is redrawn from that stock's own bars in the same block neighbourhood (IA)". "Neighbourhood" is undefined | Changes every surrogate panel |
| **G-6** — **RESOLVED (operator ruling 2026-09-19; `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`)** | **Burn-in** length and **minimum names per date** | Memo §11.H item 6 lists both; no value is written anywhere | Changes n and which dates enter T_c |
| **G-7** — **RESOLVED (operator ruling 2026-09-19; `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`)** | CA **exclusion-window** rule | R-13 requires exclusion windows; their length and anchoring (around ex-date) are not specified. Nor is the enumeration source | Changes the eligible panel. Belongs to the R-13 certification task |
| **G-8** — **RESOLVED (operator ruling 2026-09-19; `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`)** | **Seed value** for B = 1999 | R-14 says "seed"; no value is recorded | Clerical, not scientific. Any fixed integer, recorded in the freeze document before any run |
| **G-9** — **RESOLVED (operator ruling 2026-09-19; `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`)** | Blind size check: **inner draws and failure action** | R-14 accepts "200 pseudo-real panels, rejection ≤ 2α". Not written: whether each pseudo-real test uses its own B = 1999 surrogates; whether the check is per construct or joint; **what happens if the rejection rate exceeds 2α** (stop, respecify, or proceed with disclosure) | Without a failure rule, a failed size check would force a post-hoc decision |
| **OPEN-J** (GF-10; added 2026-09-19) — **RESOLVED (operator ruling 2026-09-19; GF-10 record v0.7 §5.2)** | **Sample-end censoring of P3/P4 candidates** | GF-10 record v0.6 §5.3: s_T(M) and s_P(M) are existential indicators over the whole active span (c, u], and contrast eligibility is fixed at u. A candidate still active on the last session of the evaluation sample has no observed u. The record does not say whether it enters P3/P4, or with what scores. Options named in v0.6 §5.3: (i) score the observed part of the span; (ii) exclude candidates whose u falls after the sample end; (iii) defer to the window/freeze definitions; (iv) other | Censored candidates entering as 0s bias T(time) and T(price) toward 0, and not symmetrically. It changes P3/P4 membership at every window boundary the freeze uses. P1/P2 are unaffected. [NES]; coupled to G-4, OPEN-11, OPEN-12 |
| **OPEN-6** (GF-10; added 2026-09-19) — **RESOLVED (operator ruling 2026-09-19; GF-10 record v0.7 §5.2)** | **Event timestamp convention** | GF-10 spec draft F3 / v0.6 §5.4: the event *date* is the session of the event bar (OD-7), but whether the timestamp is bar start, bar end or the first instant the crossing becomes knowable is not ruled. The outcome window (OPEN-12) must use the same convention | Changes where the outcome window starts and the causal ordering of event vs outcome |
| **OPEN-11** (GF-10; added 2026-09-19) — **RESOLVED (operator ruling 2026-09-19; GF-10 record v0.7 §5.2)** | **Score mapping to the weekly formation grid** | GF-10 spec draft F8 / v0.6 §5.4: how intra-week events become s(*i*, w) (persistence, formation instant), including how P3/P4 candidate indicators map to s_T(*i*, w) and s_P(*i*, w) | Changes the score entering T_c and the GF-10 contrast; C-6 routes the weekly-cell supersession here |
| **OPEN-12** (GF-10; added 2026-09-19) — **RESOLVED (operator ruling 2026-09-19; GF-10 record v0.7 §5.2)** | **Outcome window anchoring** | GF-10 spec draft §12 / v0.6 §5.4: 12a start anchor; 12b event-session inclusion; 12c reference-swing timing; 12d coincident penetration. R-2 fixes 5 sessions but not the anchor | Changes the outcome variable y(*i*, w) itself; also governs window-boundary cases (spec draft X16) |
| **OPEN-K** (GF-10; added 2026-09-19, v0.7 audit) — **RESOLVED (operator ruling 2026-09-19; `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`)** | **Outcome and eligibility of score-0 observations** | GF-10 record v0.7 §5.3. OPEN-11 scores an eligible stock-week with no P1 event as 0, and that 0 enters the IC. OPEN-12a/12c anchor O-R10 and its reference to "the GF-10 event", which a 0 does not have. Memo §7 anchored every eligible name at the formation week-end; whether that still governs GF-10 0s is not ruled. Also the eligibility instant for a 0, and the anchor when one stock has two P1 events in one week | Without y for 0s, the primary T_c is not computable. Retaining memo §7 for 0s would give mixed anchoring (events on t_e, 0s on f_w) |
| **OPEN-L** (GF-10; added 2026-09-19, v0.7 audit) — **RESOLVED (operator ruling 2026-09-19; `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`)** | **Outcome input to the P3/P4 contrast** | GF-10 record v0.7 §5.3. OPEN-12 is worded on the P1 event. P3/P4 instants differ from P1 (A-ii) and from each other, and s = 0 candidates have none. Which outcome T(time) and T(price) use is not ruled | Changes both terms of the only GF-10 specificity decision; coupled to G-4 |
| **OPEN-M** (GF-10; added 2026-09-19, v0.7 audit) — **RESOLVED (operator ruling 2026-09-19; `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`)** | **Outcome windows past the evaluation-sample end** | GF-10 record v0.7 §5.3 (spec draft X16). An event in the last five sessions before 2022-12-30 has a window into 2023, a span R-12 keeps out of the screen. OPEN-J covers P3/P4 candidate spans only | Changes the P1 observation set at every window boundary and touches exposure (R-11/R-12) |
| **CAL-1** (all primaries; added 2026-09-19, from GF-10 record v0.7 §5.5) — **RESOLVED (operator ruling 2026-09-19; `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`)** | **Calendar-week convention for the formation instant** | Memo §7: "last NSE session of each calendar week". The convention for a week containing a **Sunday** session (e.g. some Diwali Muhurat sessions) is not recorded, whether ISO Monday–Sunday or another. `SPECIAL_SESSIONS` covers only 2023–2025, so earlier special sessions need an explicit session-window source | Sets f_w, and so every weekly score, for GF-1, GF-4T/R8 and GF-10 |
| **OPEN-N** (GF-10; added 2026-09-19, v0.8 audit) — **RESOLVED (operator ruling 2026-09-19: exclude)** | **Direction of a contrast stock-week whose legs disagree** | GF-10 record v0.8 §5.3. OPEN-L gives each contrast stock-week one shared y, which needs one direction. If S9 changes inside the week, the P3 instant, the P4 instant and the A1 state on D_L can belong to opposite-direction candidates. OPEN-K(c) covers P1 only, and the contrast may not read P1 | Without it the shared y is undefined for those stock-weeks. Options (v0.8 §5.3): first contrast instant; A1 state on D_L; exclude |
| **RR-3** (GF-10; added 2026-09-19, v0.8 audit) — **RESOLVED (ratified 2026-09-19)** | **T(·) in R-10's contrast** (ratification of a reading) | R-10 names T(time) − T(price); G-4 fixed its p; no text defines T(·). v0.8 reads T(leg) = the T_c formula (mean weekly Spearman IC) on the leg's score and the shared y, with the 20-name floor | Fixes Δ and so the G-4 p-value |
| **OPEN-P** (all primaries; added 2026-09-19, freeze-document transcription) — **RESOLVED (operator ruling 2026-09-19, `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md` §4: (a) drop the date, count reported)** | **Undefined per-date IC** | Memo §8.2: T_c = the mean over formation weeks of the per-date Spearman IC. When every eligible name on a date has the same score, or the same outcome, the IC is 0/0, and no text says what happens then. Options: (a) drop the date (count reported); (b) set the date's IC to 0 | It changes T_c, p_sur, p_plac and Δ on every panel, and G-6b does not prevent it. **For GF-10 it is expected to be common:** at most one P1 event per episode, with every A1-active candidate eligible as a 0 |
| **OPEN-Q** (K3, all; added 2026-09-19, freeze-document transcription) — **RESOLVED (operator ruling 2026-09-19, `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md` §4: (a) skip the session)** | **A stock with no bar on a session while listed and a member** | Memo §5 row 12 ("each session vs the previous session") is silent. The real data have one declared case (2020-04-13, R-13 certification). In surrogate panels, G-5 leaves the stock "missing on that surrogate date". Options: (a) skip the session and compare over the stock's own bars; (b) the missing session breaks every run in progress | K3 is upstream of every score and outcome, and G-5 makes the case reachable in every surrogate panel |
| **RR-4 … RR-8, OC-1, OC-2** (added 2026-09-19, freeze-document transcription) — **RESOLVED (2026-09-19, `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md` §4): RR-4 … RR-8 ratified as read; OC-1 = (b) literal G-7 text; OC-2 confirmed complete** | Readings of the GF-1 and GF-4T/R8 outcome (the instant, strictness, prior penetration, "next 7 days" and the membership instant), the masks in surrogate and pseudo-real panels, the G-7 span start (OC-1, which now also asks whether d_ref and both GF-1 anchors are in the span) and robustness completeness (OC-2) | Freeze draft §0.3 A–B. RR-1 … RR-3 and OPEN-K were ruled for GF-10 only | They pin the GF-1 and GF-4T/R8 outcome and the surrogate layer exactly as the code will implement them |

**G-1, G-2, and G-3 (both placebo families) were resolved by operator rulings on 2026-09-15** and are
recorded in the ruling register (G-1, G-2 and G-3 blocks); their rows above are preserved as the gap
history. **G-3 is CLOSED for the complete Stage-1 primary set.** The rulings are
**pre-result specifications** compatible with the frozen constraints — they are not claimed to have
been literally explicit in Gann's text.

---

## 5. Robustness variants already named in committed documents (to consolidate, item 12)

Recorded for completeness, not chosen here. All are off the pass path.
- **K3:** symmetric up/down switch (memo §5 row 11).
- **GF-1:** market days (R-9); P8; weeks and months as units; K3 turns as anchors (design doc §D.4).
- **GF-4T/R8:** worked-example windows 60–67 / 60–72 and 90–98 (R-4); all-swings anchor (R-9).
- **GF-10:** greatest prior decline (R-5); *h* = 15 sessions (design doc §D.4).
- **Surrogate:** mean block 5 and 60 (R-14).
- **Diagnostics:** price-level strata; anchor-age strata; per-stock heterogeneity; realized burn-in
  haircut to n (memo §11.H item 12).

The operator should confirm that this list is complete before the freeze, since a variant added after
results cannot be declared off-path.

---

## 6. Verdict

> **NOT READY TO FREEZE — no open definition remains (again), 2026-09-19.** The freeze-review items below were ruled the same day (`PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md` §4) and applied in the freeze draft. Remaining: **P-3** (code, committed, not run), **P-4** (G-S1, operator only), **P-5** (approval, digest recorded here).
>
> *Earlier the same day:* **the definitional gate REOPENED.** Transcribing the ruled rows into the freeze draft (`PTMS_GANN_STAGE1_FREEZE_DOCUMENT_DRAFT_2026-09-19.md` §0.3) exposed two unruled definitions: **OPEN-P**, the undefined per-date IC, and **OPEN-Q**, a missing bar in K3. It also exposed five readings for ratification (**RR-4 … RR-8**) and the two confirmations reserved for freeze review (**OC-1**, **OC-2**). Once these are ruled, what remains is tasks and approvals: P-3, P-4 (operator), P-5.
>
> *Earlier the same day:* **no open definition remained.** The GF-10 v0.8 audit surfaced OPEN-N and RR-3, and both were ruled on 2026-09-19 (exclude; ratified).
>
> **Earlier the same day: no open definition remained (2026-09-19).** All the listed operator
> definitions were ruled on 2026-09-19 (`PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`): G-4 … G-9, OPEN-K/L/M, RR-1/RR-2, CAL-1 and
> the R-11 freshness ruling. What remains is tasks and approvals: P-2 external CA enumeration
> (authorized), items 12/13/16, GF-10 record v0.8, P-3 code, P-4 G-S1 (operator), P-5 freeze
> approval, plus the operator's confirmation of the per-construct G-7 span start at freeze review.
>
> *History below (as of 2026-09-19, before the rulings):*
>
> **NOT READY TO FREEZE.**
>
> **Definitions missing (operator):** G-4, G-5, G-6, G-7, G-9; G-8 is clerical. **GF-10:** OPEN-K,
> OPEN-L, OPEN-M (record v0.7 §5.3). OPEN-J, OPEN-6, OPEN-11 and OPEN-12a–d were ruled 2026-09-19;
> the rest of GF-10's mechanical definition is locked (62 locks, v0.7); RR-1/RR-2 await ratification.
> **All primaries:** CAL-1 (calendar-week convention). **G-1, G-2 and G-3 are
> ruled** (2026-09-15; ruling register, G-1/G-2/G-3 blocks); **G-3 is closed for the complete Stage-1
> primary set** (GF-1: 132-set phase-shift orbit; GF-4T/R8: 162-set rigid-translation family).
>
> **Tasks outstanding:**
> - P-1: R-11 **audit performed 2026-09-15** (`PTMS_GANN_R11_READER_DATE_AUDIT_2026-09-15.md`; finding:
>   2023-01-02 → 2026-09-11 signal-spent). **The freshness ruling remains the operator's.**
> - P-2: R-13 **store-level certification and in-store CA enumeration COMPLETE 2026-09-15**
>   (`PTMS_GANN_R13_N100_EOD_SCOPED_CERTIFICATION_2026-09-15.md`); **external CA enumeration and the
>   remaining certification items remain** (operator authorization required).
> - P-3: Stage-1 code committed from a clean tree (after the definitions are fixed, not run).
> - P-4: operator appends G-S1.
> - P-5: freeze document committed, hashed and approved.
> - Items 12, 13 and 16 to be written.

Every Stage-1 ruling has been made, and the ruled primary set is GF-1, GF-4T/R8, GF-10 (m = 3). That
closes the **ruling** gate, not the **freeze** gate.

---

## 7. Governance

- No empirical test, market outcome, signal count, RFA, screen, surrogate run, size check or
  optimization.
- No prior operator ruling changed, except ruling 7, superseded by R-5 on the operator's instruction.
- No family definition modified. No construct called faithful because of a result.
- Exposure status preserved:
  - Equity EOD 2011-03-25 → 2022-12-30 is signal-spent, so it can host only non-confirmatory use.
  - 2023-01-02 → 2026-09-11: the R-11 audit (2026-09-15) found the span **signal-spent**; the formal
    freshness ruling is still the operator's, so the span stays UNRESOLVED until ruled.
  - Observations are spent; the Stage-1 hypotheses are fresh.
- The exposure register was not edited. G-S1 is operator-owned.
- The screen, if it is ever run, is never confirmation. A positive result from any Arm-2 variant is
  never evidence that Gann's documented method worked.
