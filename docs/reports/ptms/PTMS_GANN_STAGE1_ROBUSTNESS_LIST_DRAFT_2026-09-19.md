# PTMS — Gann Stage-1 Robustness List (Freeze Item 12) — DRAFT FOR OPERATOR CONFIRMATION

**Date:** 2026-09-19 · **Branch:** `research/ptms-price-time-market-structure`

**Status: DRAFT — operator rulings R-A … R-G and N recorded 2026-09-19 (§6); specifications in §6.2 outstanding. NOT A FREEZE.**
- The list consolidates every robustness variant and diagnostic named in committed documents.
- Entries that later locks have superseded are marked as such.
- The list flags what still needs a specification.
- Candidates that no committed text names are listed separately (§5) so the operator can add or drop
  them **now**. A variant added after results cannot be declared off-path (checklist §5).
- No data read. No variant was run.

**Sources:**
- freeze checklist §5;
- memo `PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md` §5 row 11, §8.2 and §11.H item 12;
- design decisions `PTMS_GANN_PREREG_DESIGN_DECISIONS_2026-09-14.md` §D.4;
- ruling register R-4, R-5, R-9 and R-14;
- rulings of 2026-09-19;
- GF-10 record v0.8 (`c894a64`);
- spec draft OPEN-10 and OPEN-14;
- catalogue GX-4.

---

## 1. Ground rules (from committed text; to be transcribed)

| Rule | Source |
|---|---|
| Every variant and diagnostic is **off the pass path**. It is reported alongside the primary and can neither rescue a failed primary nor fail a passed one | Memo §8.2, §11.H item 12; design doc §D.4 heading |
| Variants are **not** entries in the multiplicity register. m = 3 is unchanged | R-12; memo §10 |
| Each variant is computed with the same code, panel, eligibility and exclusions (G-6, G-7, OPEN-M) as its primary, changing **only** the named element | Memo §8.2 ("identical code") |
| The set is closed at freeze: nothing is added after any read | Checklist §5 |

**Operator decision needed (R-A):** whether each variant also reports a surrogate p (B = 1999, seed 42)
or only its T_c and effect size. No committed text says which. The first multiplies surrogate compute
by the number of variants.

---

## 2. Variants

Status key:
- **CARRIED** — named in committed text and consistent with every current lock.
- **SUPERSEDED** — a later lock made it primary, part of the pass path, or moot.
- **NEEDS SPEC** — named, but not specified enough to compute.
- **CONFIRM** — named in the design doc's §D.4 but missing from checklist §5.

### 2.1 Common (all three primaries)

| ID | Variant | Changes | Source | Status |
|---|---|---|---|---|
| V-K3 | **Symmetric K3 switch.** Down-switch needs LL **and** LH, mirroring the up-switch's HH+HL. The primary reading is literal | K3 detector; everything downstream. For GF-10 this includes reaction detection, the symmetric reading 2.1-b in the OPEN-1/2/4 analysis | Memo §5 row 11; R-1; OPEN-1/2/4 analysis row 2.1-b | CARRIED |
| V-B5 / V-B60 | **Surrogate mean block 5 and 60** (primary 20) | Surrogate leg only | R-14; memo §8.2 | CARRIED |

### 2.2 GF-1 (Master Square time points)

| ID | Variant | Source | Status |
|---|---|---|---|
| V1-MD | **Market (trading) days** instead of calendar days | R-9(a) | CARRIED |
| V1-P8 | **Point set P8** (the broader "strongest points" list) instead of P4 | Design doc §D.4 | CARRIED — the P8 membership list must be transcribed from definition §2 |
| V1-WK / V1-MO | **Weeks, months** as the time unit | Design doc §D.4 | **NEEDS SPEC**: how P4 counts map to weeks and months (e.g. 36 weeks from the anchor's week; the rounding rule) |
| V1-K3 | **K3 turns as anchors** instead of the running to-date extremes | Design doc §D.4 | **NEEDS SPEC**: which K3 turn — last confirmed, or every turn in a lookback — and how many |

### 2.3 GF-4T/R8 (Rule 8 day windows)

| ID | Variant | Source | Status |
|---|---|---|---|
| V4-WE | **Worked-example windows:** the printed list with 57–65 → 60–67 (and 60–72), and 85–92 → 90–98 | R-4 "Frozen if accepted" | CARRIED. Note that R-4 names **two** replacements for 57–65 (60–67 and 60–72). Transcribe as **two** variants, V4-WE67 and V4-WE72, unless the operator rules one |
| V4-AS | **All-swings anchor:** windows counted from every K3 turn in the last 185 days, not only the last confirmed one | R-9(b); design doc §D.4 | CARRIED — overlap handling (a union of windows) to be stated |
| V4-CT | **[MMPTC] circle tier D1 + quarters** as the window set | Design doc §D.4 | **CONFIRM** (not in checklist §5) and **NEEDS SPEC** (the day list for D1 + quarters) |
| V4-IW | **Importance weighting** of windows ([45Y] p. 11) | Design doc §D.4; definition §2 GF-4T | **CONFIRM** (not in checklist §5) and **NEEDS SPEC** (weights; a weighted score is not binary, so it changes the statistic's input form) |

### 2.4 GF-10 (Rule 8 time overbalance)

| ID | Variant | Source | Status |
|---|---|---|---|
| ~~V10-GP~~ | Greatest prior decline | R-5; design doc §D.4 | **SUPERSEDED.** Greatest is now the **primary** (OD-1, C-5) |
| V10-IP | **Immediately preceding** completed same-type K3 move as the time reference (R-5's original primary) | Spec draft OPEN-14 asks exactly this: "What replaces 'greatest-prior as robustness' now that greatest is primary?" | **CONFIRM** — the natural swap, but not ruled |
| ~~V10-PO~~ | Price-overbalance leg | Design doc §D.4 | **SUPERSEDED.** It is now R-10's specificity contrast, on the confirmatory pass path (P4) |
| V10-H15 | **h = 15 sessions** (Rule 4's three weeks) instead of 5, for the O-R10 window | Design doc §D.4; design decisions horizon row | CARRIED. OPEN-M then excludes observations with O_15 > Z, so the variant's panel ends 10 sessions earlier than the primary's. Say so in the report |
| V10-DC | Daily-clock variant of the event | Spec draft OPEN-14 | **Moot for the Stage-1 screen.** The screen window (≤ 2022-12-30) is entirely DB profile, which already uses the daily clock. Recommend recording as not applicable |

### 2.5 Controls named as alternatives (not variants)

| Item | Source | Status |
|---|---|---|
| GF-10 ratio placebos 0.75× / 1.33× of R_T | Memo §8.2 ("alternative: ratio placebos"), set aside by R-10's contrast | **CONFIRM**: include as an off-path control, or drop |

---

## 3. Diagnostics (required, off the pass path)

Memo §11.H item 12 requires "**pre-specified** diagnostics". Each needs its definition pinned before
the freeze.

| ID | Diagnostic | Source | Status |
|---|---|---|---|
| D-PL | **Price-level strata:** T_c within price-level bands ([PC37] pp. 11–12, where Gann treats low- and high-priced stocks differently) | Memo §11.H item 12 | **NEEDS SPEC**: the band definition, either per-date cross-sectional terciles of as-of-t price or fixed rupee bands; the price basis (as-traded vs adjusted matters here, CLAUDE.md) |
| D-AA | **Anchor-age strata:** T_c by the age of the anchor. Targets GF-1's left-censored early "all-time-to-date" extremes at 2011-03-25 or listing | Memo §11.H item 12 | **NEEDS SPEC**: age bins (e.g. < 1 y, 1–3 y, > 3 y from the data start) and which constructs it applies to (GF-1 certainly; GF-4T/R8 and GF-10 anchors are recent by construction) |
| D-PS | **Per-stock heterogeneity** (catalogue GX-4, "required diagnostic") | Memo §11.H item 12; catalogue GX-4 | **NEEDS SPEC**: the statistic, e.g. the distribution of per-stock time-series score–outcome association with its dispersion, and the minimum observations per stock to report |
| D-BH | **Realized burn-in haircut to n** | Memo §11.H item 12 | **Restate:** G-6a ruled no extra burn-in, so the haircut is zero by definition. The live analogue is the share of observations lost to **left-censoring labels, the G-6b 20-name floor, G-7 and OPEN-M**. Confirm the restatement or drop |
| D-ES | Effect size T_c − median T_c(b) with the 2.5–97.5% surrogate interval | Memo §8.2 | CARRIED (descriptive) |

---

## 4. Summary of what the operator is asked to settle

| # | Decision | Options |
|---|---|---|
| R-A | Surrogate p for variants? | Report p for each variant / T_c + effect size only |
| R-B | GF-10: add V10-IP (immediately preceding) as the replacement robustness? | Add / no GF-10 comparator variant |
| R-C | GF-4T/R8: V4-CT (circle tier) and V4-IW (importance weighting), in the design doc but not in checklist §5 | Include both (then specify) / include one / drop both |
| R-D | GF-4T/R8 worked-example 57–65 replacement | Both 60–67 and 60–72 as two variants / one |
| R-E | GF-10 ratio placebos 0.75×/1.33× | Include as an off-path control / drop |
| R-F | V10-DC daily-clock variant | Record as not applicable to Stage 1 / keep |
| R-G | D-BH restatement | Restate as the exclusion-loss share / drop |
| R-H | NEEDS SPEC items (V1-WK/MO, V1-K3, V4-AS overlap, D-PL, D-AA, D-PS) | Research drafts the specifications for operator ratification in the next pass |

---

## 5. Candidates not named in any committed document (add now or never)

The locks point to these, but no committed text lists them. Research does not recommend them. They
appear here only because they cannot be added after results.

| ID | Candidate | Pointer |
|---|---|---|
| N-DIR | GF-10 **per-direction descriptive breakdown** (bull-only and bear-only T_c) | Spec draft OPEN-10: "A per-direction descriptive breakdown is off the pass path, **if listed in checklist §5**". It was never listed |
| N-SZ | GF-10 T_c **excluding structural zeros** (K(a)-P1 unmatched candidates and K(a)-P2 latched weeks) | v0.8 NC-25 discloses the structural zeros. This would show their effect on T_c |

---

## 6. Operator rulings (2026-09-19)

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

### 6.1 Resulting set (closed at freeze once §6.2 is specified)

| Construct | Variants and controls | Diagnostics |
|---|---|---|
| All | V-K3; V-B5, V-B60 | D-ES; D-BH (exclusion-loss share) |
| GF-1 | V1-MD; V1-P8; V1-WK; V1-MO; V1-K3 | D-PL; D-AA; D-PS |
| GF-4T/R8 | V4-WE67; V4-WE72; V4-AS; V4-CT | D-PL; D-PS |
| GF-10 | V10-IP; V10-H15; ratio placebos × 0.75 and × 1.33; N-DIR; N-SZ | D-PL; D-PS |

Dropped or superseded: V10-GP, V10-PO, V10-DC and V4-IW.

### 6.2 Still to specify (research drafts, operator ratifies) — R-H

| Item | What must be pinned |
|---|---|
| V1-P8 | The P8 point list, transcribed from definition §2 |
| V1-WK / V1-MO | The mapping of P4 counts to weeks and months; rounding; the anchor week or month |
| V1-K3 | Which K3 turn(s) anchor GF-1, and the lookback |
| V4-AS | The union of windows from all K3 turns in the last 185 days; overlap handling |
| V4-CT | The [MMPTC] D1 + quarter-division day list, and its widths |
| D-PL | The band definition (per-date terciles vs rupee bands) and the price basis |
| D-AA | Age bins, and which constructs they apply to |
| D-PS | The per-stock statistic and the minimum observations per stock |

**NO DATA READ. NO VARIANT RUN. NOT A FREEZE.**
