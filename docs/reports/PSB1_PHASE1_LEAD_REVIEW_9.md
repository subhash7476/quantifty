# PSB-1 Phase 1 — Lead Review 9

**Subject:** Prompt 5 (entity fragmentation and the dropped-factor class)
**Commit:** `7c42a0c`
**Date:** 2026-07-14
**Status:** **AMENDED** — the first issue of this review called for a revert. That instruction is
**withdrawn**; see §8. The FAIL stands, the remedy changed.
**Reviewer:** Lead — independent verification against the live store. `certify_substrate.py` was
deliberately **not** trusted: it is the script that produced the disputed "I-1 false positive"
verdict, so re-running it would replay the exculpation under test.

---

## 0. Disposition

> ## **Prompt 5: FAIL — but DO NOT REVERT. Patch forward.**
>
> A guard rail stated in the prompt was silently relaxed, and **53 fabricated returns** were
> introduced into the entity-grain adjusted series — the very artifact under certification —
> in a region where **R1 is structurally incapable of seeing them**.
>
> **None of the 53 reaches the scored panel.** On scored returns Prompt 5 is a net improvement
> (1 → 0). It is a FAIL on the artifact and on process, not on the panel.

**Action: Prompt 5-B patches forward from `7c42a0c`.** A literal revert would reinstate
PHILIPCARB's −79% in-panel error and discard correct work. See §7.

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

## 2. THE FAILURE — guard rail 2 was dropped

Prompt 5, Task 3, verbatim:

> **Disjoint, abutting print ranges** — the old symbol's last print must *precede* the new symbol's
> first print (**small gap allowed**).

You implemented **disjoint**. You did **not** implement **abutting**. Of the **76** new merges,
measured in **trading sessions** between the old symbol's last print and the new symbol's first:

| Session gap | Merges |
|---|---:|
| **≤ 10 sessions — a real rename** | **14** |
| > 10 sessions | **62** |
| … of which **> 13 months** | **17** |

`CHEMPLAST → CHEMPLASTS` is separated by **3,357 days (9.2 years)**.

### The consequence: 53 of 76 merges manufactured a return ≥ |20%|

A merge fuses two symbols into one entity, which makes the handoff a **consecutive-session return**
in the panel. When the two sides do not sit on the same price basis, the merge **invents** a return:

```
PATANJALI    RUCHISOYA  2019-11-13  ->  PATANJALI   2022-07-13   gap= 973d   ret= +30,923.88%
CHEMPLAST    CHEMPLAST  2012-06-15  ->  CHEMPLASTS  2021-08-24   gap=3357d   ret=  +3,506.73%
RAJRAYON     RAJRAYON   2019-05-27  ->  RAJRILTD    2022-03-16   gap=1024d   ret=  +2,600.00%
TANTIACONS   TANTIACONS 2020-11-27  ->  TCLCONS     2023-10-16   gap=1053d   ret=  +2,523.08%
KRITI        KRITIIND   2015-01-29  ->  KRITI       2021-11-01   gap=2468d   ret=  +1,357.67%
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
register to bridge them**. Splicing them produces a **+30,923% single-session return**.

**A multi-year gap is itself evidence of a corporate event** — insolvency, capital reduction,
suspension, re-listing — that the CA register does not carry. Abutting print ranges is what
distinguishes *"the ticker changed"* from *"the company was reconstructed."*

### 2a. And the gap rule alone is NOT sufficient — this is the finding that matters most

I set out to prove the ≤10-session rule was the fix. **It is not.**

```
PAISALO   SEINVEST 2011-10-03  ->  SEINV 2011-10-17   gap = 8 SESSIONS   ret = +854.46%
```

**Eight sessions — comfortably inside guard rail 2 — and it still fabricates +854%.** SEINVEST/SEINV
is a short suspension around a capital event, not a clean rename. And `SEINV` **is a universe
member** (2 rebalances, 2013).

> **A short gap does not guarantee a continuous price basis.** The gap rule is a *necessary*
> condition, not a *sufficient* one. The only check that actually holds the line is a **splice-return
> invariant**: across every symbol handoff inside an entity, the return must be **< |20%|**,
> *regardless of gap length*. That invariant would have caught all 53 — and PAISALO too.
>
> This is why the invariant is mandatory in 5-B, not a belt-and-braces addition.

---

## 3. Scope — how far does the damage actually reach?

This section corrects the first issue of this review, which asserted the substrate was "materially
worse" without holding the 53 to PHILIPCARB's own standard. **Held to that standard, they fail it.**

PHILIPCARB was load-bearing because two things were true: the fabricated return existed at entity
grain **and** its ex-date sat inside a `universe_membership` window — it **reached the scored panel**
(window `2018-03-28 .. 2018-04-30`, rank 182). For the 53 I had proved only the first.

Measured (membership window = `[rebalance_date, next global rebalance_date)`):

| The 53 fabricated splices | Count |
|---|---:|
| Splice date **inside** a membership window — **a scored return** | **0** |
| On a name that is a member at *other* times (contaminates its trailing history) | **4** |
| On a name **never** a universe member on either leg — cannot reach the panel at all | **49** |

**On scored returns, Prompt 5 went from 1 (PHILIPCARB, −79%, in-window) to 0.** The claim that the
substrate is "materially worse" is **withdrawn** — it was not supported by evidence and I should not
have written it before running this check.

### The FAIL rests on the artifact contract, and needs nothing else

**A substrate is certified as a substrate.** Its contract is *"the adjusted series is continuous at
entity grain"* — not *"continuous for the names that happen to be members today."* **53 fabricated
returns in that series is a failure of the artifact, whether or not the current universe selects
them.** No assumption about any downstream feature is required, and this argument alone carries the
FAIL. Membership is a *downstream selection* from the substrate; it is re-derived at each rebalance
and will change. Certifying data on the basis of who currently reads it is not certification.

### Supporting: how far the damage could reach downstream

Contingent, not established — **no feature spec exists yet** (the strategy layer is greenfield), so
these are exposures, not confirmed corruptions. The four splices on names that *are* scored members
sit in their **trailing adjusted price history**; a feature computed at scoring date *S* with an
*L*-session lookback would ingest the fabrication if the splice falls inside `[S−L, S]`:

```
ALOKINDS   ALOKTEXT -> ALOKINDS   2020-02-19   +410.61%   193 sessions before its 2020-11-27 scoring date
                                                          -> INSIDE a conventional 252-session lookback
PAISALO    SEINVEST -> SEINV      2011-10-17   +854.46%   489 sessions before scoring  (needs 504+)
PATANJALI  RUCHISOYA-> PATANJALI  2022-07-13 +30923.88%   590 sessions before scoring  (needs 756)
DALBHARAT  OCLINDIA -> DALBHARAT  2019-01-22    -21.10%   686 sessions before scoring  (needs 756)
```

`ALOKINDS` (31 memberships) is the only one that bites under a **conventional** window: a
**+410.61%** fabrication **193 sessions** before its next scoring date, inside any 252-session
lookback. `PATANJALI` and `DALBHARAT` are sealed-holdout members (2024–25, 2021–23) but are reachable
only by a **756-session (~3-year)** lookback — atypical, and speculative until a feature spec exists.
Flagged as exposure should long-lookback features ever be built; **not** load-bearing for this FAIL.

---

## 4. Why neither R1 nor `certify_substrate` caught any of it

**The stop rule is blind here by construction.** `screening_harness.py:293`:

```python
if (d1 - d0).days > MAX_GAP_DAYS:      # MAX_GAP_DAYS = 5
    continue                            # resumption/migration, excluded
```

**Every one of these splices spans months or years, so R1 discards it before classification.**

That is how the report could truthfully say "9/10 invariants PASS" while fabricated returns were
being written into the series. **The invariants did not fail. They were not looking.**

> **A green screen is not evidence of a clean substrate when the screen's own filter excludes the
> class of damage you just created.** This is the second time in two prompts that a defect has hidden
> in a screen's blind spot (Review 8: `large_genuine`; here: `MAX_GAP_DAYS`). **Any change that alters
> which rows become consecutive must be validated by a check that does not inherit R1's gap filter.**

---

## 5. R1 regressed, and the report omitted it

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

## 6. Two further defects

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

To be precise about the blast radius: the Prompt 4 DTIL re-key is **safe by rule 1** — its ex-date
(2021-08-05) lies inside DTIL's own interval, so it resolves on the strict interval join and never
reaches the fallback at all. It is *not* being held safe by the `n_ent = 1` filter. The defect is the
**two-map design**, which is real fragility on a resolver we have already had to repair twice.
**The `events` fallback must read `symbol_entity_intervals`, never `universe_eligibility`.**

---

## 7. Required action — Prompt 5-B (patch forward from `7c42a0c`)

**Do not revert.** `PHILIPCARB → PCBL` is a **0-session handoff** (last print 2022-01-12, first print
2022-01-13 — consecutive sessions). It satisfies guard rail 2 and survives any abutting rule, so the
PHILIPCARB fix is **kept**. Reverting would reinstate a −79% *in-panel* error to remove 53
*out-of-panel* ones — a strictly worse trade. Prompt 5's correct sub-fixes (F-9, F-10, F-11, F-12, the
open-ratio CA-shape test) all stand.

1. **Un-merge the 62 merges whose session gap exceeds 10.** Of the 76, **14** clear the gap rule.
   Leave the other **62** issuers **fragmented** and log each as documented residue. *Fragmentation
   costs series continuity; fusion fabricates a return. Prefer fragmentation.*
2. **Add the splice-return invariant — this is the load-bearing one.** For every multi-ticker entity,
   the return across each symbol handoff must be **< |20%|**, *regardless of gap length*. **HALT**
   otherwise. It must **not** inherit R1's `MAX_GAP_DAYS` filter. Per §2a the gap rule alone is
   insufficient: **`PAISALO` passes the gap rule at 8 sessions and still fabricates +854%** — this
   invariant is what catches it.
   - **Do not hardcode 14.** The gap rule admits 14; this invariant then culls at least `PAISALO`
     from them, so **≤ 13** merges actually land. The final count is whatever survives *both* gates —
     derive it, do not assert it.
   - **HALT for operator disposition — do not auto-exclude.** A genuine rename whose first
     new-symbol session happens to hit a **±20% circuit** will trip this invariant (this is exactly
     the F-12 pattern: a circuit limit is numerically indistinguishable from an `f=0.80`/`f=1.20`
     CA ratio). Auto-excluding on trip would silently re-fragment a real rename. Every trip is a
     **disposition item**, not a decision the code makes.
3. **Fix F-14** — predicate to `n_ent != 1`; make fail-at-4 → pass-at-0 real.
4. **Fix F-15** — the `events` fallback must read `symbol_entity_intervals`, never
   `universe_eligibility`.
5. **Report R1 before/after** and disposition the three new `CA-shaped-orphan` demergers (`IDFC`,
   `STAR`, `SUVEN`) into `ca_scope_exclusions` per D5.
6. **Report the residue explicitly**: the fragmented issuers (RUCHISOYA/PATANJALI,
   CHEMPLAST/CHEMPLASTS, …) are **genuinely the same company** but carry an unbridged capital event.
   They stay split, by design, and that is the correct answer until a bridging factor exists.

---

## 8. Correction log — what this review got wrong on first issue

Recorded because a review that hides its own errors is worth nothing.

| First issue said | Corrected |
|---|---|
| *"The A2 substrate is now materially WORSE than before Prompt 5."* | **Withdrawn.** **0 of the 53** fabricated splices land inside a `universe_membership` window; PHILIPCARB's −79% did. On scored returns Prompt 5 is **1 → 0**, a net improvement. I asserted a regression without holding the 53 to the same in-scope test I had applied to PHILIPCARB. |
| *"Revert `7c42a0c`. Do not patch forward."* | **Withdrawn.** `PHILIPCARB → PCBL` is a **0-session** handoff and survives guard rail 2. A revert reinstates the in-panel −79% and throws away the correct fixes. **Patch forward.** |
| Gap rule presented as the fix | **Insufficient.** `PAISALO` clears it at 8 sessions and still fabricates **+854%**. The **splice-return invariant** is the real guard. |
| F-15: *"one predicate away from being routed to the wrong company"* | **Overstated.** The DTIL factor resolves by rule 1 (ex-date inside DTIL's own interval) and never reaches the fallback. The two-map design is still the defect; the factor is not held safe by `n_ent`. |

**What stands unchanged:** the guard rail was silently relaxed (14/76 conform); 53 fabricated returns
are in the certified artifact; 4 contaminate the trailing history of scored members, `ALOKINDS`
(+410.61%) inside a 252-session lookback and two of them in the **sealed holdout**; R1 is
structurally blind to all of it; R1 regressed unreported; F-14 and F-15 hold.

---

## 9. Summary

Prompt 5 executed its mechanics competently — the cum arithmetic is exact, no double-apply, no
fan-out, PHILIPCARB absorbed to the paisa, every regression guard on Prompts 3 and 4 holds, and the
I-1 exculpation was honest and correct.

But a guard rail stated in the prompt was silently relaxed from **"disjoint and abutting"** to
**"disjoint"**, fusing companies across insolvencies and multi-year suspensions and writing **53
fabricated returns** into the entity series — in a region where **R1's `MAX_GAP_DAYS` filter
guarantees it will never look.** The certification reported 9/10 PASS because the invariants were not
pointed at the damage.

None of the 53 is a scored return today, and PHILIPCARB — which *was* — is now fixed. That is why the
remedy is **patch forward, not revert**. But 53 fabricated returns in the artifact under
certification is a FAIL, and the check that closes it is not the gap rule (`PAISALO` clears that at 8
sessions and still fabricates +854%) — it is the **splice-return invariant**.

**Prompt 5: FAIL. Patch forward via Prompt 5-B. A2 substrate: NOT CERTIFIED.**
