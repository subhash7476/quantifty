# PTMS — Gann Stage-1 Operator Rulings, 2026-09-19

**Date:** 2026-09-19 · **Branch:** `research/ptms-price-time-market-structure`

**Status: OPERATOR RULINGS, RECORDED VERBATIM IN SUBSTANCE. NOT A FREEZE.**
- The operator made these rulings interactively in one session on 2026-09-19, choosing from the options
  put to them.
- No market data, outcome, event count or statistic was read before or during the rulings.
- No earlier lock is reopened.

**Companion documents:**
- `PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md` (R-1 … R-15; G-1 … G-3).
- `GF10_MECHANICAL_DECISION_RECORD_v0.7_2026-09-19.md` (OPEN-6, OPEN-11, OPEN-J, OPEN-12a–d).
- `GF10_OPEN_K_A_ELIGIBILITY_ANALYSIS_2026-09-19.md` (the analysis behind OPEN-K(a)).
- `PTMS_GANN_STAGE1_FREEZE_CHECKLIST_2026-09-15.md`.

---

## 1. GF-10 rulings

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

## 2. Rulings for all three primaries

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

## 3. What remains before the freeze

No open **definition** remains among the items listed in the checklist as of this session. What
remains:

| Item | Owner | Nature |
|---|---|---|
| P-2 external CA enumeration (authorized) + applying G-7 | Research | Task |
| Item 12: consolidated robustness list (checklist §5), then operator confirmation that it is complete | Research → operator | Task + confirmation |
| Item 13: report template; item 16: GR-1.5 disclosure text | Research | Task (wording fixed by memo §8.2, §10, R-1) |
| G-7 "earliest anchor or reference date" per construct (§2) | Operator | Confirmation at freeze review |
| GF-10 record v0.8 recording these rulings; transcription of the GF-1 and GF-4T/R8 cells | Research | Task |
| P-3 Stage-1 code, committed from a clean tree, not run | Research | Task |
| P-4 exposure-register row G-S1 | **Operator only** | Task |
| P-5 freeze document committed, hashed and approved | Operator | Approval |

**NO DATA READ. NO CODE. NOT A FREEZE.**
