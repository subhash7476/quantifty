# PSB-1 — Why the errors keep coming, and the method that ends it

**Status:** methodology decision, governs Prompt 5-C and the certification suite
**Date:** 2026-07-15
**Author:** Lead (Claude), after the operator's question at Review 10
**Reads:** `PSB1_PHASE1_LEAD_REVIEW_2..10.md`, `scripts/psb1/certify_substrate.py`, `PSB1_IMPLEMENTATION_PROMPTS.md`

---

## 1. The question

*"Why does a new error show up every time? Each fix reveals the next. We built a certification
runner and it still finds things. Both of us miss them. Why?"*

DeepSeek's answer — *"each layer was independent, each fix revealed the next, the next layer was
underneath the whole time"* — is half right and it hides the real cause. There is **not** a stack of
independent layers. There is **one contract**, tested with a different filter each time, and the next
hole was always behind the filter the last check carried.

## 2. The one contract

Every defect across Prompts 2 → 5-C is a violation of a single artifact contract:

> **The entity-grain adjusted price series is continuous. Every consecutive-print return is explained
> either by a documented adjustment factor that both matches the ratio *and corresponds to a real
> reprice*, or is a normal daily move. Nothing else.** And its companion: **`adj_prev_close(t) ==
> adj_close(t−1)` at entity grain.** *(The "corresponds to a real reprice" clause is the factor-evidence
> quadrant — a spurious factor is documented and matches its own ratio, so continuity alone cannot see
> it; §5 arm 4 does.)*

Map the whole history onto it:

| Prompt | Defect | Same contract, violated at… |
|---|---|---|
| 2 | rename-boundary bonus fabrication | a rename handoff |
| 3 | recycled ticker `DTIL`/`DVL` +50% | a co-trading splice + prev_close cell |
| 3-B | `BE→EQ` series migration prev_close | a series seam |
| 4 | mis-keyed `DVL`/`DTIL` bonus, evidence blind spot | a dropped/mis-keyed factor |
| 4 (F-7) | `LITL` first-session unadjusted prev_close | a first-session ex-date |
| 5 | `PHILIPCARB`/`PCBL` −79% dropped orphan factor | a face-value re-issue |
| 5-B | ISIN-merge splice fabrications | an ISIN-merge handoff |
| 5-C | `INDOSOLAR→WAAREEINDO` +16,406% | a rename-path handoff |

One contract. Eight locations.

## 3. The actual root cause — the suite is bug-shaped, not contract-shaped

`certify_substrate.py`'s own docstring says it: *"Invariants tested (ordered by discovery, roughly the
prompt chain)."* The suite is a **museum of past bugs**. Each invariant was written to *pass on the
store that motivated it*, and each carries a structural filter that made it tractable — and blind:

- **I-8** gate-(b) continuity → **20 mega-cap symbols** only (a sample).
- **F-7** `prev_close_col_violations` → `WHERE alag > 0` (structurally excludes every first session).
- **Prompt 3** found the old prev_close check **dedup'd co-trading symbols away before measuring**.
- **Prompt 3-B** found the check **partitioned by symbol**, so it couldn't see a cross-symbol seam.
- **Review 7** noted the gap check is satisfied **"by construction"** (the `cum` factor cancels) and
  *"carries no evidential weight alone"* — a check that cannot fail was left in the suite anyway.
- **Prompt 5-B** built the splice check as a **merge-admission gate**, so it never runs on the
  rename path.
- **Review 9→10** — the Lead's own splice probe was filtered `NOT IN symbol_changes`. *"Removing that
  filter is what surfaced these 4."*

That last line is the whole diagnosis in one sentence. **Every discovery in this project has the same
shape: someone removed a filter and found more.** The filters are the disease. A bug-shaped test can
only re-find its own bug; it is definitionally incapable of finding the next corner, because the next
corner is exactly what its filter excludes.

This is a **methodology failure, not an effort failure.** Example-based verification on a 7M-row
artifact has a false-pass rate that never reaches zero, no matter how carefully either party looks.
That is why *both* parties missed things (the operator reclassified a non-zero result; the Lead
over-counted 251→1 and wrongly predicted a prev_close was fine). You cannot spot-check your way to a
clean 7M-row artifact. The only thing that reaches zero is a **property quantified over the whole
population with no exclusions.**

## 4. Why not "just one global query" — the trap that repeats the mistake

The tempting fix — *"enumerate every entity-grain consecutive return over 20% and require a matching
factor"* — is itself bug-shaped in disguise. It fails two ways, and both matter:

- **Unfiltered, it floods.** Indian smallcaps, IPOs, and penny names hit ±20% circuits constantly.
  The residue is **thousands** of genuine moves — undispositionable — and the operator is right back
  to spot-checking. *(Confirm with a `COUNT(*)` of `|ret| > 20%` before trusting any single-query
  framing.)*
- **Shape-gated to control the flood, it misses `INDOSOLAR`.** +16,406% sits on **no** canonical CA
  ratio — it is a reverse-merger, not a split. A CA-shape filter re-blinds the check to the exact
  class Review 10 just caught.

No single query is both tractable and complete. The generality you want is **four arms sharing one
discipline** — and the fact that *no one arm covers all the classes* is itself the answer to "why
every time."

## 5. The method — four arms, one discipline

Run all four over the **finished** substrate, entity-grain, EQ∪BE union, **every** entity, **every**
handoff, **every factor**, with **zero structural filters**:

1. **Intra-symbol CA-shape arm.** Reuse gate-(b)/R1's existing classifier (`CA_RATIOS`, the tolerances,
   the open-ratio convention — do **not** invent new logic), run with every filter removed. Shape-gating
   is the *definition of the question* ("a CA-shaped move with no factor"); a non-CA-shaped intra-symbol
   move with no factor is **enumerated into `large_genuine` for operator disposition, never silently
   passed** (do not pre-bless it as "genuine by convention" — that is the same top-level filter that hid
   every prior miss). → catches **PHILIPCARB**, the **DTIL missing-factor** side, **P2**.
2. **Cross-symbol handoff arm.** Review 10's splice bound promoted to an invariant: every entity's
   *adjusted* return across each consecutive-symbol handoff **< |20%|, any gap, shape-free**,
   HALT-for-disposition. Handoffs are rare (~1,050 renames) so no flood; shape-free is what catches a
   non-CA-shaped capital event. → catches **INDOSOLAR**, the ISIN-merge splices, the **DTIL/DVL splice**.
3. **prev_close identity arm.** `adj_prev_close(t) == adj_close(t−1)` at entity grain, **no `alag>0`
   filter**. → catches **LITL/F-7**, **BE→EQ**, the **DVL +50%** prev_close gap.
4. **Factor-evidence arm — the quadrant arms 1–3 do not cover.** Arms 1–3 all **trust the factor
   register**; a factor that exists but corresponds to **no real reprice** (the DVL +40.2%
   spurious/mis-key class — the exact defect Prompt 4 fixed) passes all three silently. Import
   gate-(b)'s `fetch_evidence` (`implied_open = open(ex)/close(ex−1)`, frozen) and its
   `no_reprice`/`wrong_ratio` test, run over the **entire `adjustment_factors` register, unfiltered**
   (not the Prompt-4 `f ≥ 0.75` × membership suspect cut). Every recorded factor must correspond to a
   real reprice. → catches **DVL +40.2%**, **AHLEAST** wrong-ratio, the no-reprice class.

**Prompt 5-C, as scoped by Review 10, is still too narrow.** A splice-only invariant would miss a
*future* PHILIPCARB — an intra-symbol dropped factor four years from any handoff — and a *future* DVL,
a spurious factor no continuity arm can see. 5-C must add all four arms, not just the splice.

## 6. The discipline — the invariant on the invariants

1. **The only permitted exclusion is membership in a committed, reasoned disposition register.**
   Every structural filter — sample, `WHERE`, symbol-partition, `MAX_GAP_DAYS`, merge-gate mount,
   `NOT IN symbol_changes`, close-vs-open — is **banned**. Exceptions are **data, not code.**
2. **A check satisfied "by construction" carries zero evidential weight — delete it.** The gap check
   whose `cum` factor cancels (Review 7) gives false comfort. Out. **But never retire an invariant on an
   *assumed* "subsumed"** — demonstrate a named arm reproduces its coverage first. I-1 (adj-vs-raw
   continuity) itself trusts the factor register and does **not** catch a spurious factor; arm 4 does.
3. **Every number in every review comes from a committed, re-runnable, full-population query.** No
   disposition rests on a hand spot-check. This single rule kills the error class *both* parties made
   (251→1, the reclassification, "prev_close is fine"). It is a methodology fix, not an effort fix.

## 7. The termination proof — how we know it won't happen a ninth time

Belief is not evidence; this project holds that standard everywhere else, so hold it here.

**Rebuild the view at each pre-repair commit** (the machinery already exists — 3-B rebuilt `07572e4`
on a copy) and run all four arms against each historical store. **Require that every past defect
re-appears in the enumeration — including both directions of the DVL/DTIL event: the missing-factor
side (DTIL −33.5%) via arm 1 and the spurious-factor side (DVL +40.2%) via arm 4.** Collapsing them to
one row would let the backtest go green while the evidence direction is never exercised — the proof-hole
aligned with the coverage hole. If the suite re-finds every class from history, it is *demonstrably*
contract-shaped, not bug-shaped. If it misses one, the incompleteness is found now — cheaply, before
certification — instead of in Prompt 6. This converts *"I believe this is general"* into a falsifiable
check.

## 8. Dispositioning — one list, top-down, once

Run the four arms unfiltered **once** and get the **complete** residue (expect it larger than 4 —
that is the true population, finally visible, instead of arriving four rows at a time). Then adjudicate
**per name, by reason** — not by a blanket default:

- documented factor of matching ratio → explained, log;
- genuine dispositioned move → register with reason;
- missing/mis-keyed factor → re-key with two-source evidence (never on `rekey_candidate` alone);
- bad entity boundary → **fragment *only* for an *unbridged* capital event.**

**"Default to fragment" (Review 10 §5.3) is not the method — it is half the bug history.** Fragmenting
at a face-value re-issue is exactly what severed PHILIPCARB from its factor. A face-value re-issue with
a real CA must **merge and carry the factor across**; a recycled ticker (`DTIL`) stays **split**; an
unbridged capital event (`INDOSOLAR`) **fragments**. The invariant surfaces the discontinuity and
*forces the call*; merge-vs-fragment is per-name by the **reason**, never automatic.

## 9. One-paragraph answer for the record

The errors keep coming because the certification suite is built from the bugs already found, and every
check in it carries a filter that hides the next one. It is not a stack of independent layers — it is
one continuity contract, tested narrowly eight times. The fix is not another bug-shaped invariant
(#11 for the splice); it is to replace the suite with the contract itself, evaluated by four
complementary arms — intra-symbol CA-shape, cross-symbol handoff, prev_close identity, and
**factor-evidence** (the quadrant that catches a spurious factor no continuity check can see) — over the
whole population with **no structural filters**, the only allowed exception being a committed disposition
register, and to prove completeness by re-finding every historical defect (both directions of the
DVL/DTIL event included) from its pre-repair commit. After that, a green run means the contract holds,
not merely that the last bug is gone.
