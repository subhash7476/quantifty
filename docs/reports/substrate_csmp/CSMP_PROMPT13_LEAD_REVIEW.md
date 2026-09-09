# CSMP Prompt 13 — Lead Review: `load_window()` memory fix (steps 1–5)

**Date:** 2026-07-12 · **Reviewer:** Claude (Lead Reviewer) · **Implementer:** DeepSeek V4
**Verdict:** **PASS — all 6 criteria + the Lead-Review amendment. Cleared for step 6, the sealed read.**

---

## 1. The amendment — the bug the dispositive test was structurally blind to

I required proof that the entity subquery is **date-unfiltered**. DeepSeek asserted it; it was not evidenced.
Verified directly:

```
entities EVER in universe          : 592
entities in universe by 2022-12-31 : 509
FIRST enter universe AFTER 2022-12 :  83   <-- exist ONLY in the sealed era
```

Code confirmed date-unfiltered (`run_a2_validation.py:79-81`), so **all 592 survive** — including the 83.

**Why this mattered.** Had the subquery been date-scoped (to `price_cutoff`, to dev, or by some later
"optimization"), **83 companies — 14% of the scorable universe — would have been silently price-dropped from
the sealed run.** The IC would have been computed over a truncated cross-section, and the top-40 could have
been missing genuinely eligible names.

**And the dispositive dev test would still have passed, byte-identical, green.** Those 83 entities never
appear in dev-period `memb[t]`, so the dev guardrail *cannot see them*. This is the one failure mode the
primary safeguard is structurally blind to, and it is now closed by direct evidence rather than assertion.

## 2. Criteria

| # | Criterion | Result |
|---|---|---|
| 1 | **Dev `results.json` byte-identical** | **PASS — DISPOSITIVE.** `be662698dc5eb793…` — **a fourth consecutive round of surgery with not one byte moved.** n=131, mean_IC 0.0457, rule-1/2 21/1, +6.24% / +5.95%. The entity restriction is identity-preserving, as claimed. |
| 2 | Fix = scope restriction only | **PASS** — diff `983cca0..0ae1dc4` touches **only** `run_a2_validation.py` (+10 lines). **Zero `core/msi/` diffs**: no scoring, gate, VOID, or record changes. |
| 3 | Sealed load below the working dev load | **PASS** — sealed restricted **1,846,148** rows vs the **5,075,370** unrestricted dev load that already runs successfully. The failing configuration was 7,009,336. **Headroom demonstrated, not asserted.** |
| 4 | All five guards fire | **PASS** — the phase/window cross-check raises in **both** directions (re-tested; nothing read); dirty-tree, grid-shape, VOID, and sealed fence intact. |
| 5 | One dev record + re-pins | **PASS** — `f8153e11…` / `code_commit 0ae1dc4`; §1.1 and Prompt-10 Step-0 re-pinned; tree clean. |
| 6 | No sealed statistic observed | **PASS** — shape-fact counts only. No score, return, IC, spread, or verdict. |

## 3. Verdict

**PASS. Cleared for the sealed read.**

The window was never spent. The prices across 2023-01 → 2026-06 are certified clean (VOID: **0 undocumented
residue** — §12.1's scariest inherited assumption, discharged). The harness now loads only what it can
legitimately use, at roughly a quarter of the load that failed and well below one already proven on this
machine. The scorable universe is provably intact — all 592 entities, including the 83 that exist only in the
sealed era.

**Every number in the study is unchanged, for the fourth consecutive round.**

**Step 6 — the single irreversible read — is authorized to proceed.**

**The sealed window (2023-01 → 2026-06) has not been read.**
