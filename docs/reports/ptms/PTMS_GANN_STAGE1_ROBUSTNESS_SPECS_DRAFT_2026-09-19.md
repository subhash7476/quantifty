# PTMS — Gann Stage-1 Robustness Specifications (Robustness List §6.2) — DRAFT FOR RATIFICATION

**Date:** 2026-09-19 · **Branch:** `research/ptms-price-time-market-structure`

**Status: RATIFIED by the operator 2026-09-19 (§ Rulings at the end). NOT A FREEZE.**
- This document drafts the eight specifications left open by the robustness list (commit `7b86480`,
  §6.2).
- Each draft names its textual basis. Where the text supports more than one reading, the draft names
  the readings and marks the one used; the operator ratifies or picks another.
- No data was read and no variant was run.
- No choice is justified by coverage, counts or results.

**Common rule (robustness list §1):** each variant equals its primary cell except the named element.
It uses the same panel, eligibility, O-R10, exclusions (OPEN-M, G-6, G-7), statistic T_c and effect
size (R-A). Variants are off the pass path.

**Primary cells for reference** (memo §11.F; R-3, R-4, R-9):
- **GF-1.** Anchors are the running highest high and lowest low to date. Score at week-end *t* is 1 if
  any calendar date in the next 7 days equals an anchor date + *n*, with *n* ∈ P4 = {36, 48, 72, 96,
  108, 144} + 144*k* calendar days.
- **GF-4T/R8.** The anchor is the most recent confirmed K3 swing high or low. The score is 1 if any date
  in the next 7 days falls inside the nine printed Rule 8 windows (calendar days, inclusive).

---

## S-1 · V1-P8 — point set P8 (GF-1)

| Field | Draft |
|---|---|
| Basis | Definition §2 row 3: "A wider 'strongest points' set **P8** adds {54, 90, 126} (p. 3)". [MMPTC] p. 3 strongest points 1/4, 1/3, 3/8, 1/2, 5/8, 2/3, 3/4, 7/8, 1 of 144 |
| Specification | P8 = {36, 48, 54, 72, 90, 96, 108, 126, 144} + 144*k* calendar days. Everything else as the primary |
| Readings | None. The arithmetic is fixed by the text (3/8 · 144 = 54, 5/8 · 144 = 90, 7/8 · 144 = 126) |

## S-2 · V1-WK / V1-MO — weeks and months as the unit (GF-1)

| Field | Draft |
|---|---|
| Basis | Definition §1.2: T ∈ {calendar days, market days, calendar weeks, calendar months}; [MMPTC] pp. 1, 2, 6 ("days, weeks or months") |
| Specification, weeks | The anchor week is the ISO week (CAL-1) containing the anchor date. The point weeks are the anchor week + *n* weeks, *n* ∈ P4 + 144*k*. Score at formation week *w* = 1 if *w* + 1 (the next ISO week, the unit-level analogue of the primary's "next 7 days") is a point week |
| Specification, months | The anchor month is the calendar month containing the anchor date. The point months are the anchor month + *n* months. Score at *w* = 1 if any date in the next 7 days falls in a point month |
| **Reading to ratify (Q-1)** | **(a) Unit resolution** (used above): the whole week or month is the point, so month points flag about 4–5 consecutive formation weeks. **(b) Date-exact:** the anchor date + 7*n* days, or the same day-of-month *n* months later, then the primary's 7-day rule. (b) is closer to day counting; (a) is the literal reading of "weeks/months" as the unit |
| Note | Months reachable inside 2011–2022: *n* = 36, 48, 72, 96, 108 (144 months = 12 years is barely reachable). This is disclosed, not a reason for a choice |

## S-3 · V1-K3 — K3 turns as GF-1 anchors

| Field | Draft |
|---|---|
| Basis | Design doc §D.4 GF-1 robustness "K3 turns as anchors"; R-9(b)'s rationale for GF-4T/R8 ("any" over all recent swings flags nearly every date) |
| Specification | Two anchors, parallel to the primary's two: the **most recent confirmed K3 swing high** and the **most recent confirmed K3 swing low**. Each is usable from the session after its confirmation close (D−1 freeze). A newly confirmed swing replaces its anchor and restarts the count. P4 + 144*k* calendar days, as the primary |
| Alternative (not drafted) | All K3 turns in a lookback. Rejected on R-9(b)'s own reasoning |

## S-4 · V4-AS — all-swings anchor (GF-4T/R8)

| Field | Draft |
|---|---|
| Basis | R-9(b) "all-swings variant as robustness"; design doc §D.4 "All K3 turns in the last 185 days" |
| Specification | Anchors are **every** confirmed K3 swing high and low (usable after confirmation). The score is 1 if any date in the next 7 days falls inside any printed window counted from any anchor. **Overlap:** the union of windows; the score stays binary, and nothing is counted twice |
| Derived | "Last 185 days" is non-binding: no window from a swing older than 185 + 7 days can reach the next 7 days, because the largest window ends at 185. The specification needs no lookback parameter |
| Disclosure | R-9 recorded that this variant's coverage approaches 1. That is the reason it is off-path, and it is reported as such |

## S-5 · V4-CT — circle tier (GF-4T/R8 window set replaced)

| Field | Draft |
|---|---|
| Basis | Definition §5 row 3: "**D1** = {180, 360} (halves), then {120, 240} (thirds) and {90, 270} (quarters) as most important"; row 5: candidate "**D1 ∪ quarters**, justified by Gann's 'most important' wording"; [MMPTC] p. 8: halves, thirds and quarters "most important" |
| Specification | Anchor as the GF-4T/R8 primary (most recent confirmed K3 swing). Points: calendar days from the anchor in the set below. Score at *w* = 1 if any date in the next 7 days equals a point: exact-date points, as in GF-1, with the 7-day look-ahead as the only tolerance. No repetition beyond 360: a newer swing replaces the anchor first in practice, and a count beyond 360 is not scored |
| **Reading to ratify (Q-2)** | The committed text is ambiguous. **(a) {90, 180, 270, 360}**: the literal "D1 ∪ quarters", taking D1 = halves. **(b) {90, 120, 180, 240, 270, 360}**: halves, thirds and quarters, per p. 8's "most important" list, which row 3 also calls D1's tier |

## S-6 · D-PL — price-level strata (diagnostic, all three)

| Field | Draft |
|---|---|
| Basis | Memo §11.H item 12; [PC37] pp. 11–12 (low-priced vs high-priced stocks) |
| Specification | Each formation week, split the construct's scored stock-weeks at the **per-date median as-traded close** on the formation session D_L (from `equity_bhavcopy`, as-traded). Report T_c separately for the low and high halves |
| Why as-traded | Gann's distinction is the nominal price the market trades at. The adjusted series rescales old prices by later CA ratios and would misplace a stock's level (CLAUDE.md: the 1m store is adjusted, bhavcopy is as-traded). Using the price level as a stratifier only is not a join across a CA |
| Why a median split | Gann's text is binary (low vs high). A per-date split needs no rupee cut-offs, so it avoids the price-unit translation left open by R-15 |
| **To ratify (Q-3)** | The floor per stratum-date. Draft: **10** names, half of G-6b's 20, because each half holds about half the names. Alternative: 20 in each half |

## S-7 · D-AA — anchor-age strata (diagnostic)

| Field | Draft |
|---|---|
| Basis | R-3 "Frozen if accepted": "anchor-age strata as a pre-specified diagnostic"; memo §11.H item 12: GF-1's early "all-time-to-date extremes are left-censoring artifacts of the 2011-03-25 data start and listing dates" |
| Applies to | **GF-1 only.** GF-4T/R8 and GF-10 anchors are recent K3 swings by construction and are not left-censored in this sense |
| **Reading to ratify (Q-4)** | **(a) History depth** (targets the stated concern directly): stratify each stock-week by the length of the stock's store history at *t*: < 144 weeks, 144–288 weeks, ≥ 288 weeks (Gann squares of 144 in weeks). **(b) Anchor age:** stratify by *t* − anchor date in 144-day squares (first square, squares 2–3, square 4+), assigning a stock-week to the stratum of its **younger** anchor (a stock has two anchors) |

## S-8 · D-PS — per-stock heterogeneity (diagnostic, all three)

| Field | Draft |
|---|---|
| Basis | Catalogue GX-4 ("required diagnostic"); definition §1.8 |
| Specification | For each stock, the **φ coefficient** (binary score vs binary O-R10) over its scored stock-weeks. Report: the number of qualifying stocks; the median, interquartile range and share of φ > 0; the per-stock list in an appendix. Descriptive only; no test |
| **To ratify (Q-5)** | The minimum per stock to report φ: **≥ 5 score-1 and ≥ 5 score-0 weeks** (draft) or ≥ 10 and ≥ 10. GF-10 has at most one 1 per episode, so a stricter floor leaves few stocks |

---

## Summary for ratification

| Q | Item | Draft | Alternative |
|---|---|---|---|
| — | S-1 P8, S-3 V1-K3, S-4 V4-AS | As drafted (no genuine alternative in the text) | — |
| Q-1 | S-2 weeks/months resolution | (a) unit resolution | (b) date-exact |
| Q-2 | S-5 circle tier set | (a) {90, 180, 270, 360} | (b) with thirds {120, 240} |
| Q-3 | S-6 floor per stratum-date | 10 | 20 |
| Q-4 | S-7 anchor-age definition | (a) history depth | (b) anchor age, younger anchor |
| Q-5 | S-8 per-stock minimum | ≥ 5 / ≥ 5 | ≥ 10 / ≥ 10 |

## Rulings (operator, 2026-09-19)

| Item | Ruling |
|---|---|
| S-1, S-3, S-4 | **Ratified as drafted** |
| Q-1 (S-2) | **(a) Unit resolution**: the whole ISO week or calendar month is the point |
| Q-2 (S-5) | **(a) {90, 180, 270, 360}** (the literal D1 ∪ quarters) |
| Q-3 (S-6) | Floor **10** names per stratum-date |
| Q-4 (S-7) | **(a) History depth**: < 144, 144–288 and ≥ 288 weeks of store history; GF-1 only |
| Q-5 (S-8) | Per-stock φ reported for stocks with **≥ 5 score-1 and ≥ 5 score-0** weeks |

With these rulings, the robustness list (item 12) is **fully specified** and closes at the freeze.

**NO DATA READ. NO VARIANT RUN. NOT A FREEZE.**
