# PTMS — Gann Stage-1: G-1 → G-9 Gap-Definition Audit (already-defined vs operator decisions)

**Date:** 2026-09-15 · **Branch:** `research/ptms-price-time-market-structure`

**Type:** repository audit only — no definition is invented here. For each gap in
`PTMS_GANN_STAGE1_FREEZE_CHECKLIST_2026-09-15.md` §4 this records (a) whether any committed
document already defines the answer, (b) the closest committed text, and (c) the disposition:
**already defined** · **objectively auditable / engineering** · **operator or scientific decision**.

Sources searched: `docs/reports/ptms/*` (memo, ruling register, freeze checklist, construct
definition, design decisions, catalogue, feasibility audits), `governance/exposure/`,
`scripts/` (date filters and constants only). No market data, outcome or signal was read.

---

## 1. Gap-by-gap disposition

### G-1 — may a surrogate-pass / specificity-fail construct proceed to confirmation?

| | |
|---|---|
| Already defined? | **No.** |
| Closest committed text | Memo §10 kill rule: *"whether it proceeds to a confirmatory IUT pre-registration is an operator decision (R-12)"*; R-12 ruling: *"Not ruled: whether a surrogate-pass / specificity-fail construct may proceed to a confirmatory test (freeze checklist G-1)"* |
| Disposition | **Operator decision (scientific).** Must precede the screen read — deciding after results would be post-result selection (checklist §4) |

### G-2 — O-R10 direction for GF-1 and GF-4T/R8; GF-10 bear-mirror pooling — **RULED 2026-09-15**

| | |
|---|---|
| **Status update (2026-09-15)** | **RULED by the operator** — recorded in `PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md`, G-2 block. GF-1/GF-4T/R8: contemporaneous **K3 line state** gives the direction (UP → break of last K3 swing low; DOWN → cross of last K3 swing top; NO STATE → ineligible); S9 is not used for their direction. GF-10: state-conditioned binary pooling (audit formulation A1); score and outcome stay binary; opposite-direction events = 0; no-state / wrong-counter-move stocks ineligible, not zero; one per-date pooled Spearman IC; m stays 3. Recorded as a **pre-result specification**, not as literal Gann text |
| Already defined? | **No** at audit time (row above supersedes this row as of 2026-09-15). |
| Closest committed text | Definition §12.1: O-R10 is *"on K3, a break of the last swing low (trend was up) or a cross of the last swing top (trend was down)"* — no direction for constructs without their own direction. R-2 ruling: *"direction by construct"*, and its RULING row explicitly notes the gap. GF-10: *"bear mirror pooled with sign"* (R-5, memo §11.F) without a pooling formula. Whether "trend" is the K3 line state or the S9 state (which can be "no state") is not written |
| Disposition | **Operator decision (scientific).** Changes the outcome variable for all three primaries |

### G-3 — placebo sets for GF-1 and GF-4T/R8

| | |
|---|---|
| Already defined? | **No — and the checklist's arithmetic shows the leg as written cannot fire.** |
| Closest committed text | Memo §8.2: GF-1 *"non-Gann fractions of 144"*, GF-4T/R8 *"window set with identical widths, centres shifted to non-Gann day counts"*, both *"matched coverage"*; R-14 *"placebo definitions … not specified"*. Definition §2 row 11 lists fractions only as *"e.g. 0.29, 0.41, 0.59, 0.71, 0.83"* — illustrative. Catalogue §1085/§1162 name "equal-coverage placebo sets" generically; no fractions, centres, coverage-matching rule or **count** N is pinned |
| Disposition | **Operator decision (scientific).** Under R-14's one-sided +1 rank p, rank-p ≥ 1/(N+1) ⇒ N ≥ 59 to reach α = 0.05/3 (checklist §4). Binds GF-1 and GF-4T/R8 only; GF-10's p comes from the B = 1999 surrogate draws (G-4) |

### G-4 — GF-10 time-over-price contrast p-value

| | |
|---|---|
| Already defined? | **Partially.** The contrast statistic is defined; the null and the p-formula are not. |
| Closest committed text | R-10 frozen-if-accepted: *"contrast statistic = T(time) − T(price); one-sided p from the surrogate joint distribution"* (also memo §8.2). No committed text names the reference quantity the difference is tested against, the null hypothesis, or the rank formula (e.g. how many surrogate joint draws, whether the +1 convention applies) |
| Disposition | **Operator decision (scientific) — the formula must be computable exactly as frozen** (checklist §4). The statistic T(time) − T(price) is already ruled and needs no re-decision |

### G-5 — missing-bar rule ("same block neighbourhood")

| | |
|---|---|
| Already defined? | **No.** |
| Closest committed text | Memo §8.2: a drawn bar that does not exist *"is redrawn from that stock's own bars in the same block neighbourhood (IA)"* — "neighbourhood" undefined. R-14: *"missing-bar rule … not specified in the text accepted"* |
| Disposition | **Operator decision.** Affects every surrogate panel |

### G-6 — burn-in length and minimum names per date

| | |
|---|---|
| Already defined? | **No.** |
| Closest committed text | Memo §11.H item 6 lists both, no value. K3 memo §5 row 8 fixes only the *detector* initialization ("per-stock burn-in from its data start") — that is not the formation-eligibility burn-in. R-3 fixes left-censoring (2011-03-25 or listing) but not a burn-in length. Nothing pins minimum names per date |
| Disposition | **Operator decision.** Changes n and which dates enter T_c |

### G-7 — CA exclusion-window rule

| | |
|---|---|
| Already defined? | **No.** |
| Closest committed text | Definition §1.4: *"exclude windows that span them, under every policy"* — the *policy* (exclude spans of non-ratio events) exists; length and anchoring around ex-dates are not specified anywhere. R-13: *"exclusion windows"* required, not defined. Catalogue line 1331: external enumeration required, store incomplete pre-2022 |
| Disposition | **Operator decision** (part of R-13). This session completed the R-13 **store-level certification and in-store enumeration** (`PTMS_GANN_R13_N100_EOD_SCOPED_CERTIFICATION_2026-09-15.md`); the external enumeration needs operator authorization, and G-7's rule must come with it |

### G-8 — seed value for B = 1999

| | |
|---|---|
| Already defined? | **No** (no value recorded anywhere; repo precedent seeds exist — e.g. MSRP 42, CSMP 20260711 — but none is assigned to this surrogate). |
| Closest committed text | R-14: *"B = 1999 with a recorded seed"*; memo §8.2: *"fixed seed recorded, no extension after seeing p"* |
| Disposition | **Operator decision — clerical, not scientific** (checklist §4). Any fixed integer recorded in the freeze before any run |

### G-9 — blind size check: inner draws and failure action

| | |
|---|---|
| Already defined? | **No.** |
| Closest committed text | R-14: *"200 pseudo-real panels, rejection ≤ 2α"*, *"size-check procedure and threshold"* to be finalized. Not written: whether each pseudo-real test runs its own B = 1999 surrogates; per-construct or joint; the action on a rejection rate > 2α (stop / respecify / proceed with disclosure) |
| Disposition | **Operator decision.** Without a failure rule a failed size check forces a post-hoc decision |

---

## 2. Disposition summary

| Class | Items |
|---|---|
| **Already defined (transcription only)** | Contrast *statistic* T(time) − T(price) (part of G-4) · all "RULED — TO TRANSCRIBE" checklist rows (items 3, 4-minus-direction, 5, 11-minus-G-1) · the exclusion *policy* concept behind G-7 |
| **Objectively auditable / engineering (this or a later session)** | R-11 audit (**done — finding: 2023-01-02 → 2026-09-11 equity EOD signal-spent; ruling still the operator's**) · R-13 store-level certification + in-store CA enumeration (**done**; G1/G3/G5 persistence and external enumeration remain) · checklist items 12, 13, 14, 16 (research work with fixed wording) |
| **Genuinely requiring operator/scientific decision** | **G-1, G-3, G-4 (null + p-formula), G-5, G-6, G-7, G-8, G-9** (**G-2 ruled 2026-09-15** — ruling register, G-2 block) · R-11 freshness ruling · R-13 external-enumeration authorization · G-S1 register append (operator-owned) · freeze approval (item 18) |

No gap above can be closed by this audit without inventing a definition; none is filled by this
audit. **G-2 was subsequently closed by operator ruling on 2026-09-15** (ruling register, G-2 block;
checklist §4 row marked RESOLVED).

---

## 3. Governance

- No market data, outcome, signal count, backtest, RFA, surrogate, placebo, optimization or
  threshold run.
- The exposure register was **not edited** — G-S1 remains operator-owned.
- No existing committed definition was changed or reinterpreted.
