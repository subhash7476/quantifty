# PSB-1 Phase 1 — Lead Review 10

**Subject:** Prompt 5-B (gap rule + splice-return check; F-14 / F-15)
**Commit:** `d408a68`
**Date:** 2026-07-15
**Reviewer:** Lead — independent verification against the live store. `certify_substrate.py` was
again **not** trusted for the disputed items; every number below is from a direct entity-grain query.

---

## 0. Disposition

> ## **Prompt 5-B: substantial PASS on its stated scope. A2 substrate: STILL NOT CERTIFIED.**
>
> 5-B did what it was asked: the ISIN-merge fabrications are gone (53 → 0 on that path), the 6
> surviving merges are legitimate, PHILIPCARB stays fixed, and F-14 / F-15 are correctly closed.
> 5-B built the splice check as a **merge-admission gate** — a fair reading of Review 9 §7, whose
> examples were all ISIN merges.
>
> **But a whole-substrate splice test — one that no prior review had run, mine included — surfaces
> 4 residual fabrications on a path the gate never touches: the `symbol_changes` rename path, which
> unions renames with no splice check at all.** Worst is `INDOSOLAR → WAAREEINDO` at **+16,406%**.
> They are a **pre-existing class outside 5-B's scope**, not a regression — but the certification
> suite contains **no standing splice invariant** that would fail on them, so A2 cannot be certified.

**Action: Prompt 5-C** — add a post-build splice invariant to the certification suite, over **every**
multi-ticker entity (both paths), HALT-for-disposition. Then disposition the 4. See §5.

---

## 1. What 5-B got right — verified independently, and it is most of the work

| Claim | Verified (direct entity-grain query) |
|---|---|
| ISIN merges 76 → 6 | **6** merges not in the rename register; **all splice-clean** ✅ |
| PHILIPCARB / PCBL survives gap+splice | **0-session handoff**, present among the 6 ✅ |
| PHILIPCARB 2018-04-19 | **+4.984%** ✅ |
| DVL / DTIL 2021-08-05 | **−6.550%** / **−0.225%** ✅ |
| LITL first-session prev_close | **57.6700** ✅ |
| rows | **7,030,920** ✅ |
| **F-14** orphan predicate `n_ent != 1` | Correct. The 4 known orphans are `n_ent = 1` (resolve via fallback); **0** symbols have `n_ent = 0` today, and the predicate would now flag them if they appeared ✅ |
| **F-15** `events` fallback reads `symbol_entity_intervals` | Correct. The one remaining `universe_eligibility` disagreement (`DTIL`) no longer feeds the view; DTIL resolves to **−0.225%**, the right company ✅ |

The 6 surviving merges:

```
PDSL       PDSMFL     2022-02-16 -> PDSL       2022-02-17   gap= 0 sess
SEPC       SHRIRAMEPC 2022-03-08 -> SEPC       2022-03-09   gap= 0 sess
PCBL       PHILIPCARB 2022-01-12 -> PCBL       2022-01-13   gap= 0 sess   <-- PHILIPCARB
ESSENTIA   INTEGRA    2022-02-28 -> ESSENTIA   2022-03-14   gap= 8 sess
CASTROL    CASTROL    2014-02-26 -> CASTROLIND 2014-03-14   gap=10 sess
SUBEX      SUBEX      2020-10-21 -> SUBEXLTD   2020-11-05   gap=10 sess
```

The 62 large-gap issuers are correctly left fragmented, and 8 of the 14 gap-passing candidates were
dropped by the splice check (`PAISALO` among them, as predicted). **On the ISIN-merge path, 5-B is
clean.** This is competent, correct work and I want that on the record before the finding.

---

## 2. THE FINDING — the check is a merge gate; no invariant covers the rename path

Review 9 §7 item 2, verbatim:

> **Add the splice-return invariant — this is the load-bearing one.** For every multi-ticker entity,
> the return across each symbol handoff must be **< |20%|**, *regardless of gap length*. **HALT**
> otherwise. It must **not** inherit R1's `MAX_GAP_DAYS` filter.

5-B implemented this inside `build_universe.build_entities`, in the ISIN-issuer-merge branch:

```python
if gap_ok and splice_ok:
    uf.union(e0, e1)
```

That is a **merge-admission gate** — it decides whether a *new ISIN-issuer link* is allowed. In the
context that spec was written, that is a defensible reading: every §7 example was an ISIN merge, §2a's
contrast was gap-rule-versus-return-check (PAISALO), and I did not call out the rename path. So this is
not "the implementer ignored the spec." **The gap is that a merge gate, by construction, never runs
over entities formed the *other* way** — by the `symbol_changes` rename register, which unions old and
new tickers unconditionally and is untouched by 5-B's diff. What is missing is a check over the
**finished substrate**, independent of how the entity was assembled: a gate guards the door it is
mounted on; an invariant guards the room. The certification suite has no such invariant.

**Consequence — the whole-substrate test (every multi-ticker entity, any gap) still finds 4:**

```
INDOSOLAR  INDOSOLAR -> WAAREEINDO  2025-06-19     1.0500 ->  173.3200   ret= +16,406.67%
CLCIND     SPENTEX   -> CLCIND      2026-01-30     0.7500 ->    8.9600   ret=  +1,094.67%
NEUEON     NTL       -> NEUEON      2025-12-23     2.7400 ->    5.7600   ret=    +110.22%
DELPHIFX   WEIZFOREX -> EBIXFOREX   2020-04-21    26.1267 ->   34.3200   ret=     +31.36%
```

**All 4 are in `symbol_changes`** (the authoritative NSE rename register), **not** among the ISIN
merges. They are genuine renames that carry an **unbridged capital event**: Indosolar was
reverse-merged into the Waaree group (penny-stock basis → ₹173), and the `SUJANATWR→NTL→NEUEON` and
`WEIZFOREX→EBIXFOREX→DELPHIFX` chains each cross a reconstruction. `DELPHIFX` at +31.36% is the
borderline one — a real April-2020 move and a capital event are not distinguishable from the return
alone, which is exactly why the remedy is **HALT-for-disposition, not an automatic rule**.

---

## 3. Scope and severity — held to the PHILIPCARB standard

Same test Review 9 established: does the fabrication **reach the scored panel**?

| The 4 residual fabrications | |
|---|---|
| In `symbol_changes` (rename path, unguarded) | **4 of 4** |
| In a `universe_membership` window at the splice | **0 of 4** |
| Ever a universe member on either leg | **0 of 4 — never** |
| A 5-B regression? | **No** — 5-B's diff to `build_universe.py` is entirely inside the ISIN-merge block; the rename-path unioning is untouched, so these are not on the code path 5-B modified |

So, exactly as with the 53: **none is a scored return.** The FAIL rests on the **artifact contract**
— *the adjusted series must be continuous at entity grain* — not on the panel. Four fabricated returns
of up to +16,406% in the certified series is a failure of the artifact whether or not today's
universe selects those names.

**Intellectual honesty:** this class was always present, and neither the implementer nor I had tested
it. My own Review 9 splice probes were filtered to `NOT IN symbol_changes` — I was hunting the new
merges and explicitly excluded the rename path. Removing that filter is what surfaced these 4. I am
not charging 5-B with creating them; I am charging it with shipping a gate where the spec asked for an
invariant that would have **caught** them. The distinction is the finding.

---

## 4. Why the certification still read green

`certify_substrate.py` reports **9/10** invariants, the tenth being the known I-1 formula limitation.
**There is no splice-return invariant in that suite** — the check lives only as a merge filter in
`build_universe`. So the substrate's own acceptance gate has no assertion that fails on a +16,406%
entity handoff. This is the third consecutive prompt in which a defect sat in a screen's blind spot
(Review 8: `large_genuine`; Review 9: `MAX_GAP_DAYS`; here: the check is a gate, not an invariant, and
never runs over the rename path). **The remedy closes the pattern: a standing invariant, in the
certification suite, over every multi-ticker entity.**

Note also that 5-B rewrote its own acceptance harness — `entity_ret` (entity-grain) → `adj_ret_direct`
(symbol-grain), and P3 from a before/after transition to a bare "absent after." Both are defensible on
a store where Prompt 5 already absorbed PHILIPCARB, and the regression values still verify at entity
grain (§1). But a harness that measures symbol-grain returns structurally cannot see a cross-symbol
splice — which is the very class at issue. The invariant must be entity-grain and cross-symbol.

---

## 5. Required action — Prompt 5-C (small, well-scoped)

1. **Promote the splice check to a post-build invariant.** Over **every** multi-ticker entity —
   rename-path and ISIN-merge alike — assert that the return across each consecutive-symbol handoff is
   **< |20%|**, regardless of gap. Put it **in the certification suite** as invariant #10, entity-grain
   and cross-symbol. It must fail today (4 entities) and pass only once they are dispositioned.
2. **HALT-for-disposition, not auto-anything.** Each tripped handoff is an operator item. These 4 are
   register-authoritative renames, so declining to splice **overrides the NSE rename register for that
   entity** — a decision the operator must make per name, not the code. `DELPHIFX` (+31.36%) may be a
   genuine move; the other three are clearly capital reconstructions.
3. **Disposition the 4.** Default to **fragment** — split the entity at the discontinuity, leaving the
   pre-rename ticker as its own entity (Indosolar's history does not belong on Waaree's basis). Record
   each in the residue register with its reason. *Fragmentation costs continuity; fusion fabricates a
   return. Prefer fragmentation* — and here it also means not trusting a rename register across an
   unbridged capital event.
4. **Do not touch the 6 ISIN merges, PHILIPCARB, DVL/DTIL/LITL, F-14, or F-15** — all verified correct.

---

## 6. Summary

Prompt 5-B is good work on its stated scope: the ISIN-merge fabrications are gone, the 6 survivors are
legitimate, PHILIPCARB is fixed to the paisa, and F-14 and F-15 are correctly closed. Every regression
value holds at entity grain.

The splice check was built as a **merge-admission gate** — a defensible reading of a §7 spec whose
examples were all ISIN merges. What is missing is a **substrate-wide invariant**: the gate guards the
ISIN-merge door but never runs over the `symbol_changes` rename path, which unions renames with no
splice check. A whole-substrate test — which no prior review had run, mine included — finds **4
fabricated returns** in the certified series, up to **+16,406%**, invisible to a certification suite
that contains no splice invariant. They are pre-existing and out of 5-B's scope, and none reaches the
scored panel, so this is an artifact-contract failure, not a scored-return one — but the artifact is
what is being certified.

**Prompt 5-B: PASS on scope. The missing piece is a standing splice invariant. Patch forward via
Prompt 5-C. A2 substrate: NOT CERTIFIED.**
