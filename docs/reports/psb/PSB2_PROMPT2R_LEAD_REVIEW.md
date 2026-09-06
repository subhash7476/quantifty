# PSB-2 Prompt 2R — Lead Review

**Reviewer:** Claude (Lead Reviewer, per standing two-party split)
**Date:** 2026-07-17
**Under review:** `a82190f` (code), `3e911cf` (regenerated reports)
**Baseline:** `dd7ce01` (Phase 2 Lead Review — ACCEPT)
**Prompt:** `PSB2_IMPLEMENTATION_PROMPTS.md` → Prompt 2R (`0e469dd`, corrected `1c3e16c`)

## Verdict: **ACCEPT**

The §9 pin is implemented as written. Every gating number is unchanged, the C2 digest is
byte-identical, and **§8 eligibility is untouched: C2 eligible, C3 and C4 not.**
**Prompt 3 is unblocked.**

One finding, below. It is a **reporting-accuracy** finding, not an implementation defect,
and **its root cause is this reviewer's prediction, not the implementation.**

---

## Verification — independently re-derived, not accepted on report

### Code sites (§1, §2)

| Check | Expected | Observed | Result |
|---|---|---|---|
| `harness.py:442` | `ac1 > AC1_TRIGGER`, length guard preserved | `if ac1 > AC1_TRIGGER and len(ic_arr) > 4:` | **PASS** |
| `run_phase2.py:176` | one-sided, constant imported | `nw_triggered = r.ac1 > H.AC1_TRIGGER` | **PASS** |
| `run_phase2.py:223` | label derived from constant | `f"\| NW t (AC₁ > {H.AC1_TRIGGER}) \| {nw_str} \|"` | **PASS** |
| `run_phase2.py:276` | paragraph prints observed `r.ac1` | `f"...AC₁ = {r.ac1:.6f} > {H.AC1_TRIGGER}..."` | **PASS** |
| `screening_harness.py` | unmodified | last touched `7c42a0c`, predates 2R | **PASS** |
| `AC1_TRIGGER` value | unchanged at `0.10` | `AC1_TRIGGER = 0.10` | **PASS** |
| Stamp discipline (1R6) | code committed before run | reports stamp `a82190f`; regenerated at `3e911cf` | **PASS** |

No `abs()` remains at either site. No sign-branching was added — correct: under a one-sided
trigger the "may be optimistic" branch cannot execute on negative AC₁.

### Predictions

| # | Prediction | Outcome |
|---|---|---|
| 1 | C3/C4 change on **exactly one line** (label), value stays `N/A` | **FAILED AS WRITTEN** — 3 lines each (see finding) |
| 2 | C2 changes in **exactly four places** | **FAILED AS WRITTEN** — 6 lines (same cause) |
| 3 | **C2 digest byte-identical** | **MET** — `41e3732909f9bf8d`, unchanged; no digest line appears in any report diff |
| 4 | All §6/§7/§8 numbers unchanged; eligibility unchanged | **MET** |
| 5 | Determinism re-confirmed | **MET** |

**Prediction 3 was the check with teeth and it held.** `compute_hash` (`run_phase2.py:47–65`)
covers `ac1` but not `nw_t`/`power_nw`, so a fix that moved a gating number would have moved
the digest. It did not move.

### Gating numbers — C2, re-read from the regenerated report

| Metric | `dd7ce01` | `3e911cf` | Moved? |
|---|---|---|---|
| Mean IC | 0.034892 | 0.034892 | no |
| SD IC | 0.104033 | 0.104033 | no |
| One-sided t | 2.4874 | 2.4874 | no |
| One-sided p | 7.994592e-03 | 7.994592e-03 | no |
| AC₁ | −0.181762 | −0.181762 | no |
| Noncentrality | 3.0740 | 3.0740 | no |
| Power at δ | 0.9198 | 0.9198 | no |
| Digest | `41e3732909f9bf8d` | `41e3732909f9bf8d` | no |

### §8 eligibility — unchanged across all three

| Cand | (i) Mean IC > 0 | (ii) Net spread > 0 | (iii) Power ≥ 0.80 | Eligible |
|---|---|---|---|---|
| C2 | 0.034892 ✓ | 0.045733 ✓ | 0.9198 ✓ | **YES** |
| C3 | 0.008312 ✓ | −0.011015 ✗ | 0.1816 ✗ | no |
| C4 | 0.046550 ✓ | 0.028667 ✓ | 0.4110 ✗ | no |

### The report-only column, before and after

C2's exposure paragraph is **gone**, correctly: AC₁ = −0.181762 is not > 0.1. The stale
`NW t (|AC₁|>0.10)` label is replaced by `NW t (AC₁ > 0.1)` in all three reports, with the
value `N/A` in all three. **AC₁ still prints in every table**, so the headline survives the
column's removal: **§7's disclosed AC₁ exposure did not materialize** — all three AC₁s are
negative (−0.182, −0.033, −0.024), and C2's is ~1.3 SE from zero at n=55.

---

## Finding 1 — Predictions 1 and 2 failed as written; the cause is the prompt, not the code

**Severity:** LOW (reporting accuracy). **No gate moves. Verdict unaffected.**

**What happened.** Prompt 2R predicted C3/C4 would change on "exactly one line each" and C2 in
"exactly four places." The observed diffs are **3 lines** per C3/C4 and **6** for C2. The extra
two lines in each are the **code-commit stamp**:

```
-**Script-generated** — ... Code commit `f29f0a7`.
+**Script-generated** — ... Code commit `a82190f`.
-| Code commit | `f29f0a7` |
+| Code commit | `a82190f` |
```

**The stamp change is required and correct.** 1R6's rule pins that a report must stamp the code
commit that produced it. Regenerating under `a82190f` *must* move the stamp. **The prediction was
wrong to omit it; the implementation was right to produce it.** This is the reviewer's error.

**The secondary point, which is the implementer's.** Prompt 2R's stop trigger read: *"C3 or C4
change **anywhere other than the line-27 NW-t label** → stop."* The stamp lines are such a change,
so the literal trigger fired. The implementer instead reported prediction 1 as met — *"only the
NW-t label line changed"* — which is **not accurate**: three lines changed.

The substantive judgement was **correct** (the stamp is mandatory; stopping would have been
pedantic). The reporting was not. The honest form was available and costs nothing:

> *"Prediction 1 met in substance; it failed as written — the code-commit stamp also changed,
> as 1R6 requires. Flagging rather than absorbing."*

**Why this is worth recording despite changing nothing.** A prediction that is quietly rounded to
"met" is the same failure mode as a paragraph that asserts a threshold it never evaluated — the
defect Prompt 2R was written to remove. The prompt's own acceptance criterion 7 said predictions
must be *"reported as met or failed — a failed prediction is reported as a failure, never quietly
fixed."* Two were smoothed. **The implementer's call was right and its report was tidier than the
truth.**

**Disposition:** no code change. Recorded here. Future prompts must state that the code-commit
stamp is expected to change on any regeneration, so the prediction is falsifiable rather than
trivially violated.

---

## Reviewer's own error rate this round — recorded, not buried

Prompt 2R required three corrections, **all three of them mine**:

1. **§9's trigger was asserted from recall, not read.** Last session's review claimed §9 pins the
   trigger one-sided while treating the fix as report-only prose. Both cannot hold. Reading
   `PSB2_PROTOCOL.md:111` and `:141` showed the pin is one-sided *and* therefore that the `abs()`
   was a live deviation — which reversed the operator's decision from (b) to (a).
2. **The first draft of the prompt contradicted itself** — it ordered the label fixed while
   predicting C3/C4 byte-identical, on a line that renders in all three reports. Caught before
   issue (`1c3e16c`).
3. **The predictions omitted the mandatory commit stamp** — Finding 1 above. Not caught before
   issue.

**This is the same failure each time: a plausible mechanism written as a conclusion and not
re-checked.** Prompt 2 §6 named this as the reviewer's recurring error and it recurred three times
inside the prompt written to fix it. The protocol's defence — falsifiable predictions checked
against a script-generated artifact — worked in all three cases. **That is the argument for the
mechanism, not against it.**

---

## Next

**Prompt 3 — the §8 selection report.** Unblocked and unchanged by this correction:

- Eligibility: **C2 only.**
- Power ranking, 0.02 tie band, declared-window vs sub-window comparison.
- **Bonferroni-deflated evidence floor at m = 3**: C2's `p = 7.994592e-03` → deflated
  `min(1, 3p) = 0.0240` < 0.05. **That arithmetic is Prompt 3's to perform and state, not this
  review's** — it is recorded here only as the reason the floor is reachable.
- **"No winner recommended" remains a valid and complete outcome** (§8).

Promotion, if any, happens only through a new full pre-registration (§12) — **never in this
battery.**
