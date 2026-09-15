# PTMS — Gann Stage-1 Operator Ruling Register (R-1 → R-14 RULED, R-15 open)

**Date:** 2026-09-15 · **Branch:** `research/ptms-price-time-market-structure`

**Status (2026-09-15): OPERATOR RULINGS RECORDED — NOT A FREEZE.** The operator ruled R-1 → R-14 on
2026-09-15; each ruling is the **RULING** row of its block, in the operator's terms. R-1 to R-11 and
R-13 accepted; **R-14 accepted for finalization only** (not to be executed); **R-12 accepted in
principle only** (not to be run). R-15 remains open, Stage 2 only. **G-1 (surrogate-pass /
specificity-fail path: retired, no confirmatory test), G-2 (O-R10 direction for GF-1/GF-4T/R8 and
GF-10 bear-mirror pooling) and G-3's GF-1 placebo family ruled 2026-09-15** — see the G-1, G-2 and
G-3 blocks after R-15.
**This record is authoritative for
the rulings; other PTMS-Gann documents point here.** Accepted rulings are not a freeze: nothing is
frozen until the freeze document is committed, hashed and operator-approved. Freeze status and the
gaps found while applying the rulings: `PTMS_GANN_STAGE1_FREEZE_CHECKLIST_2026-09-15.md`.

**Original status (as first committed, `bf6b0a5`, preserved):** RULING SHEET. No ruling was made in
the sheet. Each "recommendation" is the
research recommendation of `PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md` §11.E (commit `3d4a300`),
which is authoritative. "Frozen if accepted" states what the ruling would *allow* to be written into the
§11.H freeze; nothing is frozen until that freeze document is itself committed and approved.

No market data or outcomes read. No backtest, RFA, development screen, optimization, or new source
research.

**Source keys:** [45Y] *45 Years in Wall Street* (1949; register §§27–28) · [MMPTC] 1953 Calculator
(§26) · [PC37] *Puts and Calls* (1937; §29) · [WSSS] 1930 · [NSTD] 1936. Register = the primary-source
claim register.

**Ruling order:** R-1 first (gates all of Stage 1) → R-2 → R-3 to R-10 (constructs and cells) → R-11,
R-13, R-14 (data, exposure, method) → R-12 last.

---

## R-1 — Swing detector (K3)

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** Strict 3-Day Chart / K3 admitted as an **explicitly labelled approximation of Gann's discretionary historical detector**. Every implementation assumption in the "Frozen if accepted" row below is preserved, with the disclosure *"Gann's own record departs from the strict rule in ≥ 7 of 61 swings (1912–14)"* (a lower bound: holidays ignored). Memo §5 row 7's "declared departure" is read as this label |
| **Question** | Is a strict 3-Day Chart, run on NSE's 5-session week, admissible as an explicitly labelled *approximation* of Gann's discretionary 3-Day detector — or are all constructs that depend on it excluded? |
| **Primary basis** | [45Y] p. 63 (construction rule); p. 61 ("except when extreme highs or lows are reached … we sometimes use 1 and 2-day moves"; "based on calendar days"); pp. 66–67 record: ≥ 7 of 61 swings (1912–14) shorter than the strict rule allows; 6-day NYSE week (register Δ3-01, Δ3-02, Δ3-14) |
| **Recommendation** | Admit, labelled *"approximation of a discretionary Gann detector; Gann's own record departs in ≥ 7 of 61 swings"* |
| **Frozen if accepted** | The K3 algorithm of memo §5, including each IMPLEMENTATION ASSUMPTION: strict inequality (equal bar breaks a run); no gap handling; initialization at the first qualifying 3-session run; up-switch = 3 sessions of higher highs **and** higher lows, down-switch = 3 sessions of lower lows (literal reading; symmetric reading as robustness); day-over-day comparison; outside/inside-day handling; exception **not** applied; runs counted in sessions, durations in calendar days; swing usable from the close of the confirming session |
| **If rejected** | No faithful swing detector exists for Stage 1. GF-1, GF-4T/R8 and GF-10 all lose their outcome (R-2) and GF-4T/R8 and GF-10 lose their anchors → **Stage 1 has no testable construct**; the faithful battery stops at definition |

## R-2 — Outcome ("change in trend")

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** Rule 10 is the Stage-1 minor / temporary change-in-trend outcome. **No main-trend trading-range outcome is invented.** (Direction for GF-1 and GF-4T/R8, and GF-10's bear pooling, are not fixed by the text accepted — freeze checklist G-2) |
| **Question** | Is the Stage-1 outcome Gann's Rule 10 minor-trend signal — break of the last K3 swing low (trend up) or cross of the last K3 swing top (trend down) — with no main-trend / trading-range rule invented? |
| **Primary basis** | [45Y] p. 13 (Rule 10); p. 63; p. 66 (signal after a recorded 3-day reaction); pp. 61–62 (main trend unchanged until a trading-range breakout — "trading range" undefined); [PC37] pp. 8–9, 15–16 (ranges described by duration and point width) (Δ3-03, Δ3-04, Δ4-03, Δ4-07) |
| **Recommendation** | Accept Rule 10 as a *minor / "at least temporary"* change; no main-trend outcome |
| **Frozen if accepted** | O-R10: direction by construct; **any** penetration (Gann's 3-point example is point-based → Stage 2); intraday high/low basis (matches "tops and bottoms"; close basis not used); horizon = next 5 sessions; binary outcome; report wording "minor change in trend" |
| **If rejected** | Either (a) a main-trend outcome is required — none is mechanizable scale-free, so Stage 1 has no outcome; or (b) a non-Gann outcome (e.g. forward return) is chosen — that is an **Arm-2** design and cannot be reported as a test of Gann |

## R-3 — Sense of "extreme" (anchors)

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** GF-1 anchors are the running highest high and lowest low to date; left-censoring (2011-03-25 or listing) disclosed |
| **Question** | For GF-1, is the anchor the stock's highest high and lowest low **to date**? (Gann uses "extreme" as all-time, calendar-year, and campaign extreme.) |
| **Primary basis** | [MMPTC] p. 4 wheat example counts from the all-time low 28 and high 325; [45Y] pp. 85–88 (calendar-year extremes), pp. 92–93 and pp. 50, 54, 131 (campaign extremes) (Δ-07, Δ3-07, Δ3-08) |
| **Recommendation** | GF-1: highest/lowest to date. GF-5 and GF-8 stay deferred/excluded until a separate ruling |
| **Frozen if accepted** | GF-1 anchors = running highest high and lowest low from each stock's first date in the store (left-censored at 2011-03-25 or listing, disclosed per stock); a new extreme restarts its count; anchor-age strata as a pre-specified diagnostic |
| **If rejected** | GF-1 needs another anchor sense. Calendar-year extremes are mechanizable (cell change, recompute of design only); campaign extremes need an undefined campaign detector → GF-1 excluded |

## R-4 — Rule 8 window widths (GF-4T/R8)

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** The complete nine-window printed Rule 8 set is primary. Worked-example windows are robustness only |
| **Question** | Is the primary window set Rule 8's **printed** list — 7–12, 18–21, 28–31, 42–49, **57–65**, **85–92**, 112–120, 150–157, 175–185 calendar days — with the worked-example windows (60–67, 90–98, 60–72) as robustness only? |
| **Primary basis** | [45Y] p. 11 (printed list); pp. 46, 48, 55 (inconsistent citations of "Rule 8") (Δ2-06, Δ3-05) |
| **Recommendation** | Printed list primary; worked-example windows robustness. **Note:** the recommendation is the whole printed list; 57–65 and 85–92 are the two windows where Gann's examples disagree, not the complete primary set |
| **Frozen if accepted** | The nine printed windows, inclusive, in calendar days from the anchor date; no additional tolerance; robustness set = printed list with 57–65 → 60–67/60–72 and 85–92 → 90–98, off the pass path |
| **If rejected** | Either the wider example windows become primary (higher coverage, weaker contrast, still Gann-sourced) or the tolerance is judged unresolvable → GF-4T/R8 excluded; the [MMPTC] circle-division form would need its own tolerance ruling |

## R-5 — GF-10 status (supersedes ruling 7)

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** Ruling 7 is **SUPERSEDED**. GF-10 = **GANN-FAITHFUL**. Primary comparison: current decline vs the immediately preceding decline |
| **Question** | Does Rule 8 supersede ruling 7 ("keep relative time-overbalance unresolved / Arm 2"), making GF-10 Gann-faithful, with the current decline compared against the **immediately preceding** decline? |
| **Primary basis** | [45Y] p. 11 ("When a Time period on a decline exceeds the Time period of a previous decline it indicates a change in trend"; bear mirror); p. 12 ("The Time change is more important than reversal in price"); alternatives p. 39 ("greatest TIME PERIOD"), p. 53 ("sharpest reaction since") (Δ2-01, Δ2-02, Δ2-04) |
| **Recommendation** | Accept: GF-10 = GANN-FAITHFUL; "previous" primary, "greatest" robustness. Mechanization conditional on R-1 |
| **Frozen if accepted** | GF-10 primary cell (memo §11.F): S9 bull state (last two K3 highs and lows rising); in a K3 decline; score = 1 once the calendar-day duration from the current swing high to *t* exceeds the preceding completed decline's duration, before any up-switch; outcome = break of last K3 swing low within 5 sessions; bear mirror pooled with sign. Ruling 7 recorded as superseded |
| **If rejected** | Ruling 7 stands: relative time overbalance stays Arm 2. Stage 1 = GF-1, GF-4T/R8 (m = 2); R-10 lapses |

## R-6 — GF-8 and GF-9

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** GF-8 and GF-9 excluded from Stage 1; retained as Arm-1 claims / deferred research items |
| **Question** | Are GF-8 (percentage levels) and GF-9 (modal swing duration) recorded as Arm-1 *claims* but excluded from the Stage-1 experiment? |
| **Primary basis** | GF-8: [45Y] p. 8 Rule 3 ("any high level"), pp. 50, 54, 125 (campaign tops), [PC37] p. 10 Rule 7 (40–50% of last advance) — four anchor senses (Δ2-09, Δ3-07, Δ4-05). GF-9: [45Y] p. 57; pp. 88–89 ("mostly the major swings"; overlapping bins) (Δ2-14, Δ3-09) |
| **Recommendation** | Exclude both from Stage 1; keep both as Arm-1 claims |
| **Frozen if accepted** | Exclusion recorded with reason; GF-8/GF-9 absent from the construct set and from *m*; a per-stock mechanized mode of swing durations labelled Arm 2 if ever built |
| **If rejected** | Each admitted construct needs an unresolvable pin: GF-8 an anchor chosen among four Gann senses; GF-9 a swing population and binning Gann did not specify. Under the assumed flag rate GF-8 is also under-powered; *m* rises |

## R-7 — GF-7

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** GF-7 excluded from Stage 1, because "sections" cannot be faithfully mapped to K3 swings |
| **Question** | Is GF-7 (Rule 5/Rule 8 culmination: smaller price and shorter time at the 3rd/4th section) excluded from Stage 1 because "sections" cannot be faithfully mapped to 3-Day swings? |
| **Primary basis** | [45Y] p. 9 Rule 5 ("Stock market campaigns move in 3 to 4 Sections"); p. 12 (diminishing section); p. 49 (a 56-month bull campaign) (Δ2-05) |
| **Recommendation** | Exclude from Stage 1; remains an Arm-1 claim |
| **Frozen if accepted** | Exclusion recorded; GF-7 absent from the construct set; any K3-upswing version labelled Arm 2 |
| **If rejected** | GF-7 re-enters with sections = K3 upswings as a declared assumption another researcher would reasonably dispute; *m* = 4; the memo's power figures at *m* = 4 apply |

## R-8 — GF-5 and GF-6

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** GF-5 and GF-6 are **DEFERRED, NOT RETIRED**. They must not be described as permanently power-infeasible |
| **Question** | Are GF-5 (anniversary) and GF-6 (absolute reaction duration) recorded as "deferred — under-powered under declared assumptions; not retired", replacing the earlier "power-infeasible" wording? |
| **Primary basis** | GF-5: [WSSS] p. 55; [NSTD] p. 14; [45Y] pp. 13, 85–88, 92–93. GF-6: [45Y] pp. 8–9 Rule 4; [WSSS] p. 50; [NSTD] p. 38. Power: design doc §E.3 (optimistic corner > 10 years under assumed δ, *q*, *k*, *p*) |
| **Recommendation** | Accept the deferral wording; neither is declared permanently infeasible |
| **Frozen if accepted** | Status wording; exclusion from Stage-1 *m*; the assumptions behind the power figures listed as the conditions for any revival |
| **If rejected** | Either (a) admitted to Stage 1 — adds constructs with optimistic-corner power below 0.80 inside 10 years and an unresolved anchor sense (GF-5) → *m* = 5; or (b) recorded as permanently infeasible — not supported, since no Gann text fixes an effect size |

## R-9 — GF-1 time unit; GF-4T/R8 anchor scope

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** (a) GF-1 uses calendar days. (b) GF-4T/R8 uses only the most recent confirmed K3 swing. Both are labelled **design choices where Gann does not uniquely specify them** |
| **Question** | (a) Does GF-1 count in calendar days (Gann admits calendar or market days)? (b) Does GF-4T/R8 count only from the most recent confirmed K3 swing high or low? |
| **Primary basis** | (a) [MMPTC] p. 6 ("144 market days or 144 calendar days"); [45Y] p. 61 and pp. 46–55 arithmetic (calendar days in 1949 usage) (Δ-10, Δ3-06). (b) [45Y] p. 11 ("from any high or low"; importance weighting not mechanizable) |
| **Recommendation** | (a) Calendar days. (b) Most recent K3 swing only — a design choice, because "any" over all recent swings flags nearly every date |
| **Frozen if accepted** | (a) GF-1 points P4 = {36, 48, 72, 96, 108, 144} + 144*k* in calendar days; market days as robustness. (b) GF-4T/R8 anchor = last confirmed K3 swing extreme; all-swings variant as robustness; both labelled design choices |
| **If rejected** | (a) Market days primary (valid Gann option; cell change only). (b) All-swings anchor has coverage near 1 and no contrast → GF-4T/R8 effectively untestable; if the last-swing choice is judged arbitrary, **exclude GF-4T/R8** |

## R-10 — GF-10 specificity check

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** GF-10 specificity uses Gann's own time-over-price contrast, not ratio placebos. (The contrast's p-value mechanics are not written as a formula — freeze checklist G-4) |
| **Question** | Is GF-10's Gann-specificity check Gann's own claim that time outranks price — the time-overbalance statistic must exceed the price-overbalance statistic — rather than ratio placebos (0.75× / 1.33× the previous decline)? |
| **Primary basis** | [45Y] p. 12 ("The Time change is more important than reversal in price"); price overbalance p. 11 (Δ2-02) |
| **Recommendation** | Time-over-price contrast (uses no invented threshold) |
| **Frozen if accepted** | Price-overbalance score (current decline's points exceed the preceding decline's, same K3 swings, ratio-adjusted series); contrast statistic = T(time) − T(price); one-sided p from the surrogate joint distribution; used in confirmatory tests, reported but not a kill criterion in the screen |
| **If rejected** | Ratio placebos become the check: invented thresholds, not coverage-matched, and a smooth duration hazard would make 1.33× look as good → harder to interpret; or no specificity check → a GF-10 result could not be called Gann-specific |

## R-11 — Exposure of equity EOD 2023-01-02 → 2026-09-11

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** The reader-date / exposure audit is to be performed from code, date filters and saved artifacts only; **no outcome statistics**. **Not yet performed.** *(as of the ruling — superseded by the Status update row below.)* The freshness ruling on 2023-01-02 → 2026-09-11 follows the audit; until then the span stays UNRESOLVED |
| **Status update (2026-09-15)** | **Audit performed — complete.** `PTMS_GANN_R11_READER_DATE_AUDIT_2026-09-15.md`. **Finding: 2023-01-02 → 2026-09-11 equity EOD is signal-spent** — Carry/TS-Basis/IVOL SEALED evaluations consumed equity-EOD-derived forward returns on 2023+ formations; Trend/LAG/TS-Basis-Daily stores carry the score↔forward-return linkage on 2023+ dates; the MRLC scanner 1d track read bhavcopy 2026-04-27 → 2026-09-02. **The audit itself is complete; the formal freshness ruling remains an operator decision.** Until ruled, the span's register standing stays UNRESOLVED |
| **Question** | Will the operator commission a reader-date audit (code and artifacts only, no outcomes) recording which equity-EOD dates the 19 `scripts/signal_engine/` and 4 `scripts/mrlc_test/` readers actually touched, and then rule whether 2023-01-02 → 2026-09-11 is fresh or spent for Gann? |
| **Primary basis** | Governance, not Gann: `RESEARCH_EXPOSURE_REGISTER.md` §5b (reader clusters), §6 ("largely unread at signal level by the cash-equity batteries"), GR-1.2/1.3; EOD feasibility audit §K–§L ("the single item the confirmatory answer turns on") |
| **Recommendation** | Commission the audit before any confirmatory design; rule after it |
| **Frozen if accepted** | Audit scope (read code paths, date filters and saved artifacts' date ranges only; compute no statistic); appended register rows; the resulting freshness ruling as the confirmatory-window input |
| **If rejected** | Confirmation must be treated as forward-only (the conservative default); no historical span can enter an RFA `n_available` |

## R-12 — Development screen

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED IN PRINCIPLE ONLY.** The non-confirmatory 2011-03-25 → 2022-12-30 screen may proceed only after R-1 → R-11, R-13 and R-14 are fully frozen **and** the operator has appended register row G-S1. **Not to be run now.** **Not ruled:** whether a surrogate-pass / specificity-fail construct may proceed to a confirmatory test (freeze checklist G-1) *(as of the ruling — since ruled by G-1, 2026-09-15; see the G-1 block.)* |
| **Question** | Is a non-confirmatory development screen on **2011-03-25 → 2022-12-30 only** authorized in principle, to run only after R-1–R-11, R-13, R-14 and the §11.H freeze — with retirement decided by the surrogate check alone, and a separate decision on whether a surrogate-pass / specificity-fail construct may proceed to a confirmatory test? Not to be run now |
| **Primary basis** | Governance: GR-1.1, GR-1.4 (non-confirmatory use of a spent window; register row first); register Q-1–Q-3, Q-5 (window already signal-spent); memo §10 |
| **Recommendation** | Authorize in principle with those preconditions; operator appends row G-S1 before any read |
| **Frozen if accepted** | Window end 2022-12-30; statistic and α = 0.05/*m*; kill rule on the surrogate leg; specificity leg reported separately; B = 1999; confirmatory α = 0.05/*m*_entered; no screen estimate may feed a later δ band; NON-CONFIRMATORY label and wording; GR-1.5 disclosure; the draft G-S1 row text |
| **If rejected** | No development evidence; the only path is a forward-only confirmatory design (≥ 5 years; low central-band power) or stopping at definition |

## R-13 — Data certification and corporate actions

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** Scoped N100 EOD certification and corporate-action enumeration with exclusion windows are required before any outcome read. **Neither exists yet** *(as of the ruling — superseded by the Status update row below.)* |
| **Status update (2026-09-15)** | **Store-level N100 EOD certification: COMPLETE** (all gates PASS) and **in-store CA enumeration: COMPLETE** — `PTMS_GANN_R13_N100_EOD_SCOPED_CERTIFICATION_2026-09-15.md` (runner: `scripts/research/ptms_gann/certify_eod_n100.py`, read-only). **External CA enumeration: OUTSTANDING — requires operator authorization** (the store cannot prove absence pre-2022 and omits the 2023 RELIANCE→JIOFIN demerger). **G-7 exclusion-window rule: still OPEN.** Remaining items: G1/G3/G5 persistence into `n100_audit`, 2016-04-19 holiday confirmation, and the ±1-month boundary / BE-series / DVR dispositions if the cadence requires them |
| **Question** | Is a scoped N100 × EOD substrate certification, plus an external enumeration of spin-offs, demergers, rights and special dividends with exclusion windows, required before any outcome read? |
| **Primary basis** | Governance/data: EOD feasibility audit §L condition 2; store omits the 2023 RELIANCE/JIOFIN demerger and treats special dividends inconsistently; Gann silent on adjustment ([45Y] p. 60, p. 123; Δ4 none) |
| **Recommendation** | Require both |
| **Frozen if accepted** | Price basis (ratio-adjusted as-of-*t* series for Stage 1); certified window and universe; the enumerated corporate-action list with exclusion windows; calendar artifacts declared (2012-11-11; 2016-04-19 check) |
| **If rejected** | Swing detection and durations may be corrupted around unadjusted events; any read would have an uncertified substrate and could not pass lead review |

## R-14 — Statistical specification

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED FOR FINALIZATION ONLY — do NOT execute.** The synchronized block-bootstrap design, specificity checks, B = 1999 with a recorded seed, placebo definitions and the blind 200-panel size check are to be finalized. **Finalization is incomplete:** the GF-1 and GF-4T/R8 placebo sets *(GF-1 family since ruled by G-3, 2026-09-15; GF-4T/R8 still open)*, the GF-10 contrast p-value, the missing-bar neighbourhood, the seed value and the size-check failure rule are not specified in the text accepted (freeze checklist G-3 to G-5, G-8, G-9). Not filled here |
| **Question** | Is the memo §8.2 specification accepted for finalization (not execution): average per-date Spearman IC of binary score vs outcome; Monte Carlo test against 1,999 synchronized stationary block-bootstrap panels of daily bar vectors (high/low/close relative to prior close, mean block 20 sessions, real calendar); specificity check per construct; both checks required in confirmatory tests; blind size check (200 pseudo-real panels, rejection ≤ 2α) before unblinding? |
| **Primary basis** | Methodological. Block scale cites [45Y] p. 89 ("11 to 35 days" most common swing band); per-date differencing rejected as ill-defined (memo §8.1) |
| **Recommendation** | Accept for finalization; do not execute |
| **Frozen if accepted** | Bar-vector definition; synchronized resampling; mean block 20 (5 and 60 reported off-path); missing-bar rule; B = 1999 and seed; placebo sets (GF-1 non-Gann fractions of 144; GF-4T/R8 shifted windows of equal width) and the GF-10 contrast; one-sided +1 rank p-values; size-check procedure and threshold |
| **If rejected** | The earlier per-date surrogate-differenced IC is ill-defined; a normal/Newey–West approach understates dependence from synchronized swings; without a specificity check no result can be called Gann-specific |

---

## R-15 — Price ↔ chart-space translation (Stage 2 only; remains open)

Is "1 quoted point = ₹1 per chart space (daily chart)" admissible as a declared assumption for
GF-3, GF-4P, TIM-10 and the point rules? Basis: [MMPTC] pp. 1, 5; [45Y] pp. 8, 48, 51; [PC37] pp. 11–12,
17 (point rules depend on price level without conversion). **Not needed for Stage 1. Remains OPEN (operator, 2026-09-15) — Stage 2 only.**

---

## G-1 — Surrogate-pass / specificity-fail path

**RULED by the operator 2026-09-15** — closes freeze checklist G-1. A **pre-result
scientific/operator specification**. Stage 1 is intended to establish evidence for the specified
Gann-faithful construct, not merely evidence of a generic temporal/market phenomenon.

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED: A Stage-1 construct that passes the surrogate leg but fails the Gann-specificity leg is retired and may NOT proceed to a confirmatory test.** Rationale: failure of the pre-specified specificity leg means the construct has not demonstrated the required Gann-specific property |
| **Basis** | Freeze checklist §4 G-1; R-12 (the sub-question posed in the ruling sheet was not ruled there); memo §10 (the screen's kill rule rests on the surrogate leg alone and a surrogate-pass / specificity-fail construct was labelled *"timing effect not shown to be Gann-specific"*, with the onward path left to the operator) — this ruling decides that path |
| **Frozen if accepted** | A construct reaches a confirmatory IUT pre-registration only if both legs pass. Report wording for a surrogate-pass / specificity-fail construct: the memo's label plus the retirement disposition — *"timing effect not shown to be Gann-specific — RETIRED; may not proceed to a confirmatory test"* |
| **Recorded interaction (no new definition)** | G-3 was OPEN when this ruling was made and this ruling does not define G-3, change any placebo set, or change α or m. As the checklist §4 G-3 row records, the specificity leg as written cannot reach p_plac ≤ α for GF-1/GF-4T/R8 — so under this G-1 ruling those constructs would be retired by construction unless G-3 is fixed before the freeze *(GF-1's part was subsequently fixed by the G-3 ruling of the same date — 132-set phase-shift family; GF-4T/R8 remains open)* |

---

## G-2 — O-R10 direction (GF-1 / GF-4T/R8) and GF-10 bear-mirror pooling

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

---

## G-3 — GF-1 placebo family

**RULED by the operator 2026-09-15 (GF-1 part only — the GF-4T/R8 placebo construction remains
OPEN).** A **pre-result scientific/operator specification**.

| Field | Entry |
|---|---|
| **RULING (operator, 2026-09-15)** | **ACCEPTED.** The GF-1 specificity placebo family is the **exhaustive phase-shift orbit of P4 modulo 144**, exactly: real P4 offsets are `{36, 48, 72, 96, 108, 144}` calendar days; 144 is represented as residue 0 modulo 144 for phase construction; for every integer `d ∈ {0,…,143}`, `P4_d = {(p + d) mod 144 : p ∈ P4}`; **exclude every `d` for which `P4_d ∩ P4 ≠ ∅`**; therefore the family contains exactly **132 distinct placebo sets** — exhaustive, no subset selection. Each placebo has exactly six distinct offsets per 144-day cycle and repeats with the same unbounded `+144*k` structure as the real GF-1 construct. The real residue-0 point is expanded as `144, 288, 432, …`; it is never interpreted as day 0. No decimal fractions and no rounding convention are used. The null is **P4 phase-specificity**; other Gann day counts, including P8 `{54, 90, 126}`, are NOT excluded from the placebo family. Coverage is structurally matched by construction (same six points per 144-day cycle, same 7-day score window, same repetition and eligibility rules); actual realized coverage is reported as a diagnostic. The 132-placebo family is fixed by this mathematical rule and involves no RNG or seed |
| **Basis** | Freeze checklist §4 G-3; memo §8.2 (*"non-Gann fractions of 144"*, matched coverage, *"p_plac = rank of T_c among the placebo sets"*); definition §2 row 11 (*"avoiding Gann fractions"*); the G-3 family verification of 2026-09-15 (144 − 12 = 132; forbidden shifts = `P4 − P4` = 12ℤ₁₄₄; the disjointness exclusion is the reading that yields 132 and keeps every placebo free of P4 points) |
| **Operator disclosure (recorded)** | The phase-shift null tests whether the specific P4 **phase** is special. It is **not** a test of whether the P4 spacing pattern itself is unique among arbitrary six-point patterns |
| **Statistical consequence** | Under the frozen one-sided +1 rank-p convention, `N = 132` gives minimum placebo p = `1/133 ≈ 0.00752`, below `α = 0.05/3 = 1/60 ≈ 0.01667`; the real statistic must rank first or second of 133 to reject |
| **Frozen if accepted** | Exactly the RULING text above, transcribed verbatim into the freeze document's item 9 (GF-1 placebo sets); the family is computed by the rule, not stored as a hand-written list |
| **Not ruled** | **GF-4T/R8's placebo construction remains OPEN** — its own family and coverage rule must be specified separately. G-4 (GF-10 contrast p-value) is untouched by this ruling |

---

## Governance

- As first committed (`bf6b0a5`): no ruling made; nothing frozen.
- **2026-09-15:** operator rulings recorded in the RULING rows. Ruling 7 superseded by R-5 on the
  operator's instruction; no other prior ruling changed. **G-1, G-2 and G-3's GF-1 part ruled the same
  day (see the G-1, G-2 and G-3 blocks
  above)** — each recorded as a pre-result specification, not as a claim that the formulation was
  literally explicit in Gann's text. No family definition changed. The exposure
  register was not edited — G-S1 remains a draft for the operator to append. **Nothing is frozen.**
- Exposure status preserved: equity EOD 2011-03-25 → 2022-12-30 signal-spent (a spent window can
  host only non-confirmatory use); 2023-01-02 → 2026-09-11: the R-11 audit (2026-09-15) found the
  span **signal-spent**; the formal freshness ruling is still the operator's, so the span's register
  standing stays UNRESOLVED until ruled.
- No market data or outcomes read; no backtest, RFA, screen or optimization.
