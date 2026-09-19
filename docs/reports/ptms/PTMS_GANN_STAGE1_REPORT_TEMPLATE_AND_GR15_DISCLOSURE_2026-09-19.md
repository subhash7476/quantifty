# PTMS — Gann Stage-1 Report Template (Item 13) and GR-1.5 Disclosure Text (Item 16) — DRAFT

**Date:** 2026-09-19 · **Branch:** `research/ptms-price-time-market-structure`

**Status: APPROVED by the operator 2026-09-19 (A.2, A.5, B incl. consequence 4). To be transcribed into the freeze document. NOT A FREEZE.**
- The wording is transcribed from committed sources, and each source is cited.
- Where a later ruling superseded a memo sentence, the ruling's wording is used and the supersession is
  noted (§C).
- No data read. No number in this document comes from data.

**Rule for the generated report:** every `{{…}}` field is filled **by the screen script only**. There
are no hand-edited numbers (repo convention, as for PSB-1/PSB-2). Every fixed statement below is
reproduced verbatim in the generated report.

---

## A. Report template (item 13)

### A.0 Title block (fixed)

> # PTMS — Gann Stage-1 Screen Report — **NON-CONFIRMATORY**
>
> **Label: NON-CONFIRMATORY (GR-1.4). This screen is never confirmation, validation, or evidence
> that a Gann construct works.** *(memo §10 "Description"; exposure label "signal —
> non-confirmatory (GR-1.4)")*
>
> Frozen protocol: `{{freeze document path}}`, SHA-256 `{{digest}}`. Register row G-S1 appended
> `{{date}}` before this read. Script: `{{path}}` at commit `{{sha}}`. Seed 42. B = 1999.

### A.1 Fixed statements (verbatim in every report)

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

### A.2 Per-construct outcome wording (fixed; chosen by rule, never by judgement)

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

### A.3 Section skeleton (every number script-generated)

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

### A.4 GF-10 disclosures (fixed text, with script-filled counts)

| # | Disclosure | Source |
|---|---|---|
| X-1 | **Structural zeros.** The 0 population includes stock-weeks that could not have scored 1: candidates with no earlier same-type move (`{{n}}`) and weeks after the episode's one event (`{{n}}`). A 1 appears once per episode; these zeros can repeat weekly. N-SZ reports T_c without them | v0.8 NC-25; K(a)-P1/P2 |
| X-2 | **Mixed anchoring.** Score-1 weeks measure O-R10 from the event timestamp; score-0 weeks measure it from the week-end | v0.8 NC-26; OPEN-K(b) |
| X-3 | **The contrast's outcome differs from the primary's.** The time-vs-price contrast uses one week-end-anchored outcome for every stock-week | v0.8 NC-27; OPEN-L |
| X-4 | **An event already past its reference scores 0 by construction.** A decline long enough to overbalance in time may have broken the prior swing low first | v0.8 NC-18 |
| X-5 | **Bull and bear pooling.** Gann's wording differs between the bull and bear clauses: "first time" and "at least temporarily" appear only in the bear clauses, "reaction" only in the bull price clause. Pooling is a research decision (G-2(b)). The bear "first time" is mirrored into bull by OD-6. N-DIR reports bull-only and bear-only T_c | Spec draft OPEN-10; OD-6 |
| X-6 | **The outcome anchor differs across primaries.** GF-10 anchors to its event; GF-1 and GF-4T/R8 anchor to the formation week-end | v0.8 NC-22 |
| X-7 | **The 20-name floor is counted on the last-session eligible set** (A1), the narrowest reading | v0.8 NC-28 |

### A.5 Forbidden phrasing (a generated report must not contain)

- "Gann's rule is false / true", "validated", "confirmed", "works", "edge" (memo §10).
- Any reading of a robustness variant or diagnostic as rescuing or failing a primary (F-8).
- Any reading of screen estimates as a δ band for later confirmation (memo §10, winner's curse).

---

## B. GR-1.5 disclosure text (item 16)

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

---

## C. Supersessions applied in this draft (transcription notes, not new decisions)

| Memo text | Superseded by | Used here |
|---|---|---|
| §10 kill rule: surrogate-pass / placebo-fail → "whether it proceeds to a confirmatory IUT pre-registration is an operator decision (R-12)" | **G-1** (2026-09-15): retired, no confirmatory test | A.2 row 2 |
| §10 selection bias (1): "Confirmation must use disjoint data (2023+ if fresh, else forward)" | **R-11 = signal-spent** (2026-09-19) | B consequence 1: forward only |
| §10 window "less per-stock burn-in" | **G-6a** (2026-09-19): no extra burn-in | A.3 item 3 (exclusion-loss share instead) |
| §10 power paragraph (α = 0.05/4, m = 4 if GF-7 re-admitted) | R-7 (GF-7 excluded); m = 3 | Not reproduced; α = 0.05/3 throughout |

**Operator review (2026-09-19):** A.2, A.5 and B (all five consequences) **approved**.

**NO DATA READ. NOT A FREEZE.**
