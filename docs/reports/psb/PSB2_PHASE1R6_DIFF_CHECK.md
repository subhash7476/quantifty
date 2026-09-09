# PSB-2 / PSB-1 — Prompt 1R6 Diff Check

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** `cfbbcee` → `fe01255` (code at `e1c7728`; report regenerated at `fe01255`).
**Against:** `PSB2_IMPLEMENTATION_PROMPTS.md` §Prompt 1R6, acceptance criteria 1–8.
**Date:** 2026-07-17. **Scope:** diff check, as Prompt 1R6 specified.

---

## Verdict: **ACCEPT. Phase 1 is closed. Phase 2 is authorized.**

C1, C2 and C3 are all closed. **The watch item held: no number moved.**

---

## The watch item — prediction 3 ✅

The certification report's diff `cfbbcee..fe01255` contains **exactly three changes**, and none is a number:

```diff
-Code commit `0d155b9`.
+Code commit `3c5092b`.
-78 CA-shaped moves ... **Undocumented (HALT): 0**.
+78 CA-shaped moves ... **Undocumented: 0**.
-4 dispositioned; **0** undocumented (HALT).
+4 dispositioned; **0** undocumented.
```

Arm B stays at **4 splices / 4 dispositioned / 0 undocumented**, boundaries at **+65.1% / −88.1% / +110.2% / +31.4%**, Arms A/C/D clean, continuity invariant **0**, `SUBSTRATE CERTIFIED`. **This round touched provenance and labels, exactly as specified.**

## C1 — the stamp is true, and the guard is real ✅

**Ordering followed.** Code committed at `e1c7728`, report regenerated and committed separately at `fe01255` — the forced two-commit pattern.

**The stamp reads `3c5092b`, which is correct and slightly better than what I asked for.** `3c5092b` was `HEAD` at run time (a docs-only commit sitting on top of the code at `e1c7728`), so `git show 3c5092b:scripts/psb1/certify_substrate.py` **is** the file that ran. Stamping the actual tree state is more truthful than naming the code commit, which would have described a tree that never existed at run time. Criterion 1 met.

**The guard — verified by the reviewer, because the implementer did not report it.** Criterion 3 required it *observed to fire*. The commit messages describe the code, not the observation. I ran it directly against `_git_commit()` rather than the full suite:

```
--- tree now dirty; calling _git_commit() ---
DIRTY SOURCE: scripts/psb1/certify_substrate.py (M scripts/psb1/certify_substrate.py) — certification has no provenance.
HALT. Commit dirty sources before re-running.
RESULT: SystemExit(1) — GUARD FIRED as specified
--- restored; tree clean; calling again ---
RESULT: clean tree returns 'fe01255'
```

**It fires on a dirty source and returns a hash on a clean one.** Source file restored; tree clean. **The structural fix is in place: a false stamp is now impossible, and a fourth occurrence of R2-8 cannot happen.**

## C2 — the halt is real ✅

```python
    try:
        _assert_boundaries(arm_b2, arm_b_excl2, "§2 (inverted)")
        print("  !! §2 assertion PASSED — check lacks teeth. HALTING.")
        cc.close()
        SCRATCH.unlink(missing_ok=True)
        raise SystemExit(1)
    except AssertionError as e:
        print(f"  §2 assertion FAILED as expected: {e}")
```

**The one way this could have silently failed is closed:** `raise SystemExit(1)` sits inside the `try`, but `SystemExit` derives from `BaseException`, **not** `AssertionError` — so the `except` cannot swallow it and the halt propagates. Scratch is unlinked before exit; nothing reaches the real store. This is decidable by language semantics rather than observation, so the unreported verification (criterion 4) costs nothing here.

## C3 — both seams closed ✅

```diff
-"SELECT COUNT(*) FROM adjustment_factors WHERE symbol='NTL' AND action_type='SPLIT'"
+"SELECT COUNT(*) FROM adjustment_factors WHERE symbol='NTL'"
```

**The query now matches its message.** The FV-only finding forbids *every* price factor for NTL, not only SPLITs; the assertion now covers any `action_type` by construction.

The `(HALT)` labels are conditional (`f"**Undocumented{' (HALT)' if a_halt else ''}: {len(a_halt)}**"`) across Arms A, B **and D** — D was not in my list, and folding it in was correct rather than scope creep, since it carried the identical defect.

---

## Process note — non-blocking

**Criteria 3, 4 and 5 said "observed and reported". The observations were not reported.** The commit messages state what the code does, not what was seen. Three rounds ago that pattern produced a false "mutation-verified" claim, which is why the criteria are worded that way.

It costs nothing this time: I ran the guard myself (above), and C2/C3 are decidable by inspection — `SystemExit` is not an `AssertionError`, and `WHERE symbol='NTL'` covers every `action_type`. **The verification exists; it is recorded in this review rather than in the implementer's output.** Not worth another round — that would be ceremony, not rigor. Worth naming so the next prompt's "report the observation" is read as the requirement it is.

## Acceptance criteria

| # | Criterion | Status |
|---|---|:--:|
| 1 | Stamp names the commit whose code produced it; code before, report after | ✅ |
| 2 | Certifier refuses to stamp silently when sources are dirty | ✅ HALT |
| 3 | Dirty-tree guard observed to fire | ✅ *(by reviewer)* |
| 4 | §2's PASSED branch halts, non-zero, nothing applied | ✅ *(by inspection)* |
| 5 | NTL assertion covers any `action_type` | ✅ |
| 6 | `(HALT)` label conditional on non-zero count | ✅ *(A, B and D)* |
| 7 | Every number identical to `cfbbcee` | ✅ |
| 8 | No candidate score on real data; no §9 change | ✅ |

## Phase gates — final

| Gate | Status |
|---|---|
| **§11.1** — substrate certified | ✅ **SUBSTRATE CERTIFIED** — four arms PASS, Arm B 4/4/0, continuity 0, true stamp |
| **§11.2** — harness dev-proof + Lead Review | ✅ **Met** — C2 6.9σ, C3 4.7σ, C4 3.7σ; fidelity suite mutation-verified |

**Phase 1 is closed. Phase 2 is authorized.** Prompt 2 is drafted at `3c5092b` and may be issued.

---

## Reviewer's note

**Six rounds, and the shape of the work changed at 1R5.** The rounds before it produced literals, tautologies, and transcribed numbers; the two since produced a mutation more precise than my own estimate, a guard that fires, and a scope-creep-that-wasn't (Arm D's label). The variable was never the implementer — it was whether the prompt made the check the deliverable.

**The C1 fix is the one worth remembering.** R2-8 was corrected twice by regenerating the report, and came back twice, because both corrections addressed the artifact instead of the cause. The cause was that the certifier stamps `HEAD` while the working tree is what runs. **The third fix made the failure impossible rather than absent** — and that is the difference between a repair and a contract, which is the same lesson the four-arm suite taught about Arm B.
