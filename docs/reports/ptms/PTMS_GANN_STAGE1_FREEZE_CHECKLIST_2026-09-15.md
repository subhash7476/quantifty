# PTMS — Gann Stage-1 Freeze Checklist

**Date:** 2026-09-15 · **Branch:** `research/ptms-price-time-market-structure`

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
| R-14 | Accepted for finalization only; not to be executed | Placebo sets (**G-3**: GF-1 family ruled 2026-09-15; GF-4T/R8 open), missing-bar rule, seed, size-check failure rule (**G-5, G-8, G-9**) |
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
| 6 | Formation schedule; eligibility (PIT N100, listing start, burn-in, minimum names per date) | Weekly formation and PIT N100 specified; burn-in and minimum names **OPEN — DEFINITION MISSING** | G-6 | Operator |
| 7 | Price basis and CA handling; external CA enumeration with exclusion windows; scoped certification | Price basis ruled (ratio-adjusted as-of-*t*). **Store-level certification + in-store CA enumeration COMPLETE** (2026-09-15); **external CA enumeration OUTSTANDING** (requires operator authorization); exclusion-window rule **OPEN** | P-2 (external part); G-7 | Operator |
| 8 | Surrogate spec: bar vector, synchronized stationary bootstrap, mean block 20, missing-bar rule, B = 1999, seed | Bar vector, synchronization, block 20 (5 and 60 off-path), B = 1999 ruled. Missing-bar neighbourhood **OPEN**; seed value not recorded | G-5; G-8 | Operator |
| 9 | Placebo sets (GF-1, GF-4T/R8) and the GF-10 contrast | **GF-1 placebo family RULED — TO TRANSCRIBE** (G-3, 2026-09-15; 132-set exhaustive phase-shift orbit); **GF-4T/R8 placebo sets OPEN** (G-3 remainder); GF-10 contrast ruled in principle, contrast p **OPEN** (G-4) | Ruling register, G-3 block; G-4 | Operator / Research |
| 10 | Statistic, IUT pass rule, α, one-sidedness, blind size-check procedure and threshold | Statistic T_c, IUT (confirmatory), α = 0.05/3, one-sided, 200 panels ≤ 2α ruled. Size-check inner draws and failure action **OPEN** | G-9 | Operator |
| 11 | Screen window; kill rule and wording; confirmatory α = 0.05/m_entered; no screen estimates in a later δ band | **RULED — TO TRANSCRIBE** (R-12, memo §10). The surrogate-pass / specificity-fail path is ruled by **G-1** (2026-09-15): such a construct is **retired and may NOT proceed to a confirmatory test** | Ruling register, G-1 block | Research |
| 12 | Robustness list (off the pass path) with pre-specified diagnostics | Variants named across the memo and register; **OUTSTANDING TASK**: consolidate the full list for operator confirmation (§5) | Freeze doc | Research → operator |
| 13 | Report template: NON-CONFIRMATORY label, §8.2 limitation statement, K3 approximation label | **OUTSTANDING TASK** (wording already fixed by memo §8.2, §10 and R-1) | Freeze doc | Research |
| 14 | Code committed from a clean tree; outputs written by script only | **OUTSTANDING TASK** — no Stage-1 code exists | P-3 | Research |
| 15 | Exposure register row G-S1 appended **by the operator** before any read | **OUTSTANDING TASK** — draft row in memo §10 | P-4 | **Operator only** |
| 16 | GR-1.5 disclosure text for any later confirmatory pre-registration | **OUTSTANDING TASK** | Freeze doc | Research |
| 17 | R-11 reader-date audit performed and freshness of 2023-01-02 → 2026-09-11 ruled (R-12 precondition) | **AUDIT DONE** (2026-09-15, finding: signal-spent); **freshness ruling PENDING** | P-1 → `PTMS_GANN_R11_READER_DATE_AUDIT_2026-09-15.md` | Operator (ruling) |
| 18 | Freeze document committed, SHA-256 recorded, operator-approved | **OUTSTANDING TASK** — blocked by the rows above | P-5 | Operator |

**Screen preconditions (R-12), all unmet:** items 1–18 SATISFIED, including R-11 frozen after its
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
| **G-3 — GF-1 PART RESOLVED (operator ruling 2026-09-15; ruling register, G-3 block); GF-4T/R8 OPEN** | **Placebo sets** for GF-1 and GF-4T/R8 | Memo §8.2 says "non-Gann fractions of 144" and "window set with identical widths, centres shifted to non-Gann day counts", with matched coverage. Definition §2 (GF-1) row 11 gives fractions only as "e.g. 0.29, 0.41, 0.59, 0.71, 0.83". No committed text pins the fractions, the shifted centres, the coverage-matching rule, or the **number of placebo sets** | p_plac is "rank of T_c among the placebo sets". **Arithmetic:** under R-14's one-sided +1 rank p-values, a rank p over N sets is at least 1/(N+1). To reach α = 0.05/3 = 1/60 needs **N ≥ 59**. Five exemplary fractions could never reject. This binds **GF-1 and GF-4T/R8 only**: GF-10's contrast takes its p from the B = 1999 surrogate draws (G-4). Consequences: for those two constructs the confirmatory IUT (p_sur ≤ α **and** p_plac ≤ α) cannot pass as specified, and every one would be a specificity-fail by construction, which makes G-1 more urgent. **G-3 is a rule that cannot fire, not merely a missing value** |
| **G-4** | GF-10 time-over-price **contrast p-value** | R-10: "contrast statistic = T(time) − T(price); one-sided p from the surrogate joint distribution". No formula names the reference quantity or the null it tests | The one GF-10 specificity decision must be computable exactly as frozen |
| **G-5** | **Missing-bar rule** | Memo §8.2: a drawn bar that does not exist "is redrawn from that stock's own bars in the same block neighbourhood (IA)". "Neighbourhood" is undefined | Changes every surrogate panel |
| **G-6** | **Burn-in** length and **minimum names per date** | Memo §11.H item 6 lists both; no value is written anywhere | Changes n and which dates enter T_c |
| **G-7** | CA **exclusion-window** rule | R-13 requires exclusion windows; their length and anchoring (around ex-date) are not specified. Nor is the enumeration source | Changes the eligible panel. Belongs to the R-13 certification task |
| **G-8** | **Seed value** for B = 1999 | R-14 says "seed"; no value is recorded | Clerical, not scientific. Any fixed integer, recorded in the freeze document before any run |
| **G-9** | Blind size check: **inner draws and failure action** | R-14 accepts "200 pseudo-real panels, rejection ≤ 2α". Not written: whether each pseudo-real test uses its own B = 1999 surrogates; whether the check is per construct or joint; **what happens if the rejection rate exceeds 2α** (stop, respecify, or proceed with disclosure) | Without a failure rule, a failed size check would force a post-hoc decision |

**G-1, G-2, and the GF-1 part of G-3 were resolved by operator rulings on 2026-09-15** and are
recorded in the ruling register (G-1, G-2 and G-3 blocks); their rows above are preserved as the gap
history. **G-3's GF-4T/R8 placebo construction remains OPEN.** The rulings are
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

> **NOT READY TO FREEZE.**
>
> **Definitions missing (operator):** G-3 (**GF-4T/R8 part only**), G-4, G-5, G-6, G-7, G-9; G-8 is
> clerical. **G-1, G-2, and G-3's GF-1 part are ruled** (2026-09-15; ruling register, G-1/G-2/G-3
> blocks). **G-3 (GF-4T/R8) still blocks that construct's specification:** until its placebo family
> is defined, its specificity leg cannot reject.
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
