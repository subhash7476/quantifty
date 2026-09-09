# CSMP Prompt 12 — Lead Review: sealedness as an invariant

**Date:** 2026-07-12
**Reviewer:** Claude (Lead Reviewer) · **Implementer:** DeepSeek V4
**Verdict:** **PASS — all 8 criteria.** A mislabelled sealed run is now **impossible**, not merely discouraged. **The harness is cleared. Phase 6 is re-issued.**

---

## 1. The finding is closed, and I proved it by trying the attack

`check_phase_window()` is a **pure argument check**, invoked immediately after `parse_args()` and **before
`load_window()`** — verified by inspection *before* I ran anything, because otherwise my own test would have
read the window.

**Test A — the exact typo that would have spent the window** (`--phase sealed-read`, sealed dates):

```
PhaseWindowMismatchError: phase label 'sealed-read' implies DEV, but the window
(eval_hi=2026-06-30, price_cutoff=2026-06-30) is SEALED vs DEV_HI=2022-12-31.
Refusing to run — the code, not a typed label, decides what is sealed.
```

**Test B — the misleading dry run** (`--phase 6/sealed-read`, dev dates):

```
PhaseWindowMismatchError: phase label '6/sealed-read' implies SEALED, but the window
(eval_hi=2022-12-31, price_cutoff=2022-12-31) is DEV vs DEV_HI=2022-12-31.
```

**Both raised. Nothing was written. Nothing was read.** `git status` clean; still exactly one record.

The attack described in the Prompt-11 review — run Phase 6 with a label lacking a leading `6`, spend the
window, destroy the tripwire, and print *"The sealed window was not read"* in the artifact produced by the
run that read it — **now terminates on the arguments, before a single row is touched.**

`grep -rn 'startswith("6")'` returns **exactly one hit**: the cross-check itself
(`run_a2_validation.py:305`). Nothing else in the codebase branches on the label.

## 2. The science did not move — across three rounds of surgery

**This is the most important line in the review.** `results.json` is byte-identical across **all three**
record identities:

```
d0651e10…/results.json   be662698dc5eb793f612b67378a8fd5e99747e4b73cb3021117a239e4538d955   (Prompt 9)
65cefc37…/results.json   be662698dc5eb793f612b67378a8fd5e99747e4b73cb3021117a239e4538d955   (Prompt 11)
a5c113dc…/results.json   be662698dc5eb793f612b67378a8fd5e99747e4b73cb3021117a239e4538d955   (Prompt 12)
```

Three rounds of provenance and guard changes, three new content-addressed identities — and **not one byte of
the result moved**: n=131, mean_IC 0.0457, rule-1/2 21/1, +6.24% / +5.95%. The record's *name* is *supposed*
to change when the code changes; its *content* is not. **The guardrail did precisely the job it was designed
for — three times.**

## 3. Criteria

| # | Criterion | Result |
|---|---|---|
| 1 | `results.json` byte-identical (`be662698…`) | **PASS — dispositive** (§2) |
| 2 | No `startswith("6")` decides anything | **PASS** — one hit, the cross-check itself |
| 3 | `sealed` data-derived from `price_cutoff` / `eval_hi` vs `DEV_HI` | **PASS** — printed at runtime: `sealed=False (data-derived)` |
| 4 | `PhaseWindowMismatchError` raises **both** directions, on arguments alone | **PASS** — tested; neither test read data (§1) |
| 5 | `assert_grid_shape()` keys off derived `sealed`; still raises on n ≠ 42 | **PASS** |
| 6 | Exactly one dev record; §1.1 + Prompt 10 Step 0 re-pinned | **PASS** — `a5c113dc…` / `code_commit 983cca0` |
| 7 | Sealed window not read | **PASS** — fence asserted and printed, max `2022-12-30` |
| 8 | Construct fence held | **PASS** — dossier diff since the Rev-7 freeze is **one line**: the §1.1 pin row |

---

## 4. Verdict — and what this sequence actually demonstrated

**PASS. The harness is cleared. Phase 6 is re-issued with tripwire `a5c113dc…`.**

Prompts 10 → 12 were not a detour. They were the safeguards firing, in order, at the last moment each could
fire:

1. **DeepSeek refused a direct instruction** to run the sealed read, because the report generator was
   dev-hardcoded and would have produced a self-contradictory artifact — including the line *"The sealed
   window was not read"*, printed by the run that read it.
2. The Lead Review then found that **`n == 42` was a sentence in a prompt, not a guard in the code.**
3. And after that was fixed — that **sealedness itself was a typed string, not an invariant**, so a single
   typo could have re-armed every defect at once, on the one run that cannot be repeated.

Each was found **while the window was still sealed** — the only time any of them could be fixed for free.
**The recurring lesson, now enforced rather than merely stated: a safeguard that depends on a human typing
the right thing is not a safeguard.** Every protection standing between this program and an irreversible
mistake is now an invariant the machine enforces — the VOID gate, the dirty-tree guard, the grid-shape guard,
the sealed fence, and the phase/window cross-check.

**Phase 6 is now genuinely a ceremony, not a build.**

**The sealed window (2023-01 → 2026-06) has not been read.**
