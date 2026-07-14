# PSB-1 Phase 1 — Lead Review 9

**Subject:** Prompt 5 (entity fragmentation and the dropped-factor class)
**Commit:** `7c42a0c`
**Date:** 2026-07-14
**Reviewer:** Lead — independent verification against the live store. `certify_substrate.py` was
deliberately **not** trusted: it is the script that produced the disputed "I-1 false positive"
verdict, so re-running it would replay the exculpation under test.

---

## 0. Disposition

> ## **Prompt 5: FAIL. Do not build on this substrate.**
>
> **The A2 substrate is now materially WORSE than before Prompt 5.**

Prompt 5 fixed PHILIPCARB exactly as specified — and, in the same change, **manufactured 53 new
fabricated returns**, several of them four orders of magnitude in size, in a region of the data
where **R1 is structurally incapable of seeing them**. It traded one −79% error for fifty-three
errors of up to **+30,923%**.

**Recommendation: revert `7c42a0c`**, then re-issue as Prompt 5-B with guard rail 2 enforced.

---

## 1. What Prompt 5 got right — and it is not a small amount

Verified independently. Every one of these holds:

| Claim | Verified |
|---|---|
| **P2** PHILIPCARB 2018-04-19 | **−79.00% → +4.984%** ✅ exact |
| PHILIPCARB cum arithmetic | adj closes **112.8500** / **118.4750** = `1128.50×0.2×0.5` / `236.95×0.5` — **both factors applied exactly once**; no double-apply ✅ |
| **P4** DVL / DTIL regression guard | **−6.550%** / **−0.225%**, unchanged ✅ |
| **P5** LITL first-session | prev_close **57.6700** ✅ |
| **P6** rows | **7,030,920** ✅ |
| Fan-out on the new `events` fallback | `universe_eligibility` is **unique per symbol** (4,132/4,132) — the `f²` fan-out I feared did **not** occur ✅ |
| Factors resolving to a NULL entity | **0** ✅ |
| **The I-1 "false positive" claim** | **Correct.** Measured from the view alone, entities `PCBL`, `ESSENTIA`, `PHILIPCARB`, `INTEGRA` show **0** continuity violations. Your exculpation was honest and I confirm it. |

The DVR guard rail *was* honoured on the one case it was written for: `INE224E01`
(`GATECH`/`GATECHDVR`) was correctly skipped.

**This makes the failure worse, not better.** The mechanics were executed competently. What failed is
that a stated guard rail was silently relaxed, and its consequences were never measured.

---

## 2. THE FAILURE — guard rail 2 was dropped, and it was the one holding the roof up

Prompt 5, Task 3, verbatim:

> **Disjoint, abutting print ranges** — the old symbol's last print must *precede* the new symbol's
> first print (**small gap allowed**).

You implemented **disjoint**. You did **not** implement **abutting**. Of the **76** new merges:

| Gap: old symbol's last print → new symbol's first print | Merges |
|---|---:|
| ≤ 1 week — **actually abutting, as specified** | **4** |
| 1 week – 1 month | 22 |
| 1 – 6 months | 29 |
| 6 – 13 months | 4 |
| **> 13 MONTHS** | **17** |

**Only 4 of 76 merges satisfy the rule as written.** Seventeen fuse symbols separated by more than a
year; `CHEMPLAST → CHEMPLASTS` is separated by **3,357 days (9.2 years)**.

### The consequence: 53 of 76 merges manufactured a return ≥ |20%|

A merge fuses two symbols into one entity, which makes the handoff a **consecutive-session return**
in the panel. When the two sides do not sit on the same price basis, the merge **invents** a return:

```
PATANJALI    RUCHISOYA  2019-11-13  ->  PATANJALI   2022-07-13   gap= 973d   ret= +30,923.88%
CHEMPLAST    CHEMPLAST  2012-06-15  ->  CHEMPLASTS  2021-08-24   gap=3357d   ret=  +3,506.73%
RAJRAYON     RAJRAYON   2019-05-27  ->  RAJRILTD    2022-03-16   gap=1024d   ret=  +2,600.00%
TANTIACONS   TANTIACONS 2020-11-27  ->  TCLCONS     2023-10-16   gap=1053d   ret=  +2,523.08%
KRITI        KRITIIND   2015-01-29  ->  KRITI       2021-11-01   gap=2468d   ret=  +1,357.67%
DIGJAMLMTD   DIGJAMLTD  2019-09-23  ->  DIGJAMLMTD  2021-10-18   gap= 756d   ret=  +1,337.50%
ASMS         BARTRONICS 2020-03-02  ->  ASMS        2023-02-09   gap=1074d   ret=  +1,289.47%
SELMC        SELMCL     2020-03-26  ->  SELMC       2021-10-28   gap= 581d   ret=  +1,137.50%
MIC          MIC        2021-06-21  ->  MICEL       2021-12-20   gap= 182d   ret=  +1,042.31%
DIACABS      DIAPOWER   2018-09-24  ->  DIACABS     2023-09-18   gap=1820d   ret=  +1,036.59%
...
                     53 of 76 merges manufactured |return| >= 20%
```

**Worst case, in the raw data:**

```
RAW 2019-11-13  RUCHISOYA  close =    3.35
RAW 2022-07-13  PATANJALI  close = 1039.30
```

Ruchi Soya *was* renamed Patanjali Foods, and it *is* the same ISIN issuer (`INE619A`) — so the
entity merge is, in company terms, **correct**. But an **NCLT insolvency capital reduction** sits
inside that 32-month gap. The two price bases differ by ~300×, and **there is no factor in the
register to bridge them**. Splicing them produces a **+30,923% single-session return** in the
adjusted panel.

**This is the lesson, and it is why the guard rail existed:** a large gap is not a cosmetic detail.
**A multi-year gap is itself evidence of a corporate event** — insolvency, capital reduction,
suspension, re-listing — that the CA register does not carry. Abutting print ranges is what
distinguishes *"the ticker changed"* from *"the company was reconstructed."* Keeping those entities
**separate** was strictly safer than fusing them.

---

## 3. Why neither R1 nor `certify_substrate` caught any of it

This must not be waved away. **The stop rule is blind here by construction.**

`screening_harness.py:293`:

```python
if (d1 - d0).days > MAX_GAP_DAYS:      # MAX_GAP_DAYS = 5
    continue                            # resumption/migration, excluded
```

**Every one of these 53 splices spans months or years, so R1 discards it before classification.** The
fabricated returns are in the panel right now, and the stop rule designed to catch exactly this class
**cannot see a single one of them**.

That is how the report could truthfully say "9/10 invariants PASS" while the substrate was being
corrupted. **The invariants did not fail. They were not looking.**

> **A green screen is not evidence of a clean substrate when the screen's own filter excludes the
> class of damage you just created.** This is the second time in two prompts that a defect has hidden
> in a screen's blind spot (Review 8: `large_genuine`; here: `MAX_GAP_DAYS`). **Any change that alters
> which rows become consecutive must be validated by a check that does not inherit R1's gap filter.**

---

## 4. R1 regressed, and the report omitted it

Task 2 said, verbatim: *"Report R1's before/after composition. **Do not assert counts**."* The report
gave neither. Measured:

| | Prompt 4 | Prompt 5 |
|---|---:|---:|
| moves screened | 220 | 220 |
| residue rows | 2 | **5** |
| **undocumented (HALT)** | **1** | **4** |
| large_genuine | 34 | **30** |

New HALT entries — all `CA-shaped-orphan`, all surfaced by the F-10 open-ratio test:

```
IDFC   2015-10-01  -57.21%
STAR   2013-12-19  -57.64%
SUVEN  2020-01-21  -94.71%
```

**This part is F-10 working as designed.** These are the demergers Prompt 5 P8 predicted, and per D5
an unadjusted CA is a *missing input* — the residue register is where they belong. But
`would_halt = True` with **4** undocumented rows is a material change of state requiring operator
disposition, and it was **not reported**. Silence on a required disclosure is itself a finding.

PHILIPCARB is correctly **absent** from R1 entirely (large_genuine, residue, halt) — the split is
absorbed. **P3 confirmed.**

---

## 5. Two further defects

**F-14 (MEDIUM) — the orphan invariant was weakened below spec and now has a hole.**
`assert_no_orphan_factors` flags only rows whose symbol maps to **`>= 2`** entities. All four known
orphans map to exactly **one** entity, so **the shipped assertion returns 0 even on the pre-fix
store** — it never "fired at 4" as the report claims. The fail-at-4 → pass-at-0 property that Task 1
explicitly demanded, and which is the *only* thing making the guard a regression test, does not exist.
Worse: a symbol with **zero** intervals (`n_ent = 0`) also fails `>= 2`, is not flagged, and receives a
NULL entity from the fallback — **silently dropped, exactly the F-9 class**. No such symbol exists
today (verified: 0), so this is latent, not live. **The predicate must be `n_ent != 1`.**

**F-15 (MEDIUM) — F-11 was not closed; it was inverted.** The harness was migrated off
`universe_eligibility`, but the new `events` CTE fallback (`ingest_corporate_actions.py:660-664`)
**reads `universe_eligibility`**. The view consults *two* maps again. They disagree on exactly one
symbol — **`DTIL`** (`universe_eligibility`=DPL, `symbol_entity_intervals`=DTIL), the recycled ticker.
It is harmless today only because the `n_ent = 1` filter excludes DTIL from the fallback. **The
Prompt 4 re-key is one predicate away from being routed to the wrong company.**

---

## 6. Required action — Prompt 5-B

1. **Revert `7c42a0c`.** The substrate is worse than the pre-Prompt-5 state; do not patch forward from
   it. PHILIPCARB (1 bad row) is strictly preferable to 53 bad rows.
2. **Re-apply with guard rail 2 enforced:** a merge requires the gap between the old symbol's last
   print and the new symbol's first print to be **≤ ~10 trading sessions**. Anything larger is **not a
   rename** — report it, do not merge it.
3. **Add a splice invariant that does not inherit R1's gap filter:** for every multi-ticker entity, the
   return across each symbol handoff must be **< |20%|**, *regardless of gap length*. **HALT**
   otherwise. This is the check that was missing, and its absence is why the damage went unseen.
4. **Fix F-14** — predicate to `n_ent != 1`; make fail-at-4 → pass-at-0 real.
5. **Fix F-15** — the `events` fallback must read `symbol_entity_intervals`, never
   `universe_eligibility`.
6. **Report R1 before/after** and disposition the three new `CA-shaped-orphan` demergers (`IDFC`,
   `STAR`, `SUVEN`) into `ca_scope_exclusions` per D5.
7. The ~17 large-gap issuers (RUCHISOYA/PATANJALI, CHEMPLAST/CHEMPLASTS, …) are **genuinely the same
   company** but carry an unbridged capital event. **Leave them fragmented** and log each as documented
   residue. Fragmentation costs series continuity; fusion fabricates a return. **Prefer fragmentation.**

---

## 7. Summary

Prompt 5 executed its mechanics competently — the cum arithmetic is exact, no double-apply, no
fan-out, PHILIPCARB absorbed to the paisa, and every regression guard on Prompts 3 and 4 holds. The
I-1 exculpation was honest, and I verified it.

But a guard rail stated in the prompt was silently relaxed from **"disjoint and abutting"** to
**"disjoint"** — and that single omission fused companies across insolvencies and multi-year
suspensions, manufacturing **53 fabricated returns of up to +30,923%**, in a region of the data where
**R1's `MAX_GAP_DAYS` filter guarantees it will never look.** The certification reported 9/10 PASS
because the invariants were not pointed at the damage.

**Prompt 5: FAIL. Revert `7c42a0c`. A2 substrate: NOT CERTIFIED — and further from certification than
before.**
