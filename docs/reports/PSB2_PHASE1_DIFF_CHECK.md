# PSB-2 Phase 1 — Diff Check (Prompt 1R3 close-out)

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** `4dae4bd` → `9cdbffa` (code at `875f9e3`; report regenerated at `9cdbffa`).
**Against:** `PSB2_IMPLEMENTATION_PROMPTS.md` §Prompt 1R3 acceptance criteria 1–12.
**Predecessor:** `PSB2_PHASE1_LEAD_REVIEW_3.md` (Round 3 — CONDITIONAL PASS, amended).
**Date:** 2026-07-17. **Scope:** diff check, not a review round, as Prompt 1R3 specified.

---

## Verdict: **ACCEPT**, with one corrective turn — not a further round

**R3-4 is genuinely closed.** That was the Phase 2 precondition and the only item with teeth. R3-1 and R3-3 are closed. Arm E is closed and I verified it by running the suite rather than taking the claim on trust.

**One criterion is not met: R3-2's C2-baseline test (criterion 8).** It is reported ✅ and it is not — the mutation it claims to be verified against **passes**. The fix is one line. It does not hold up Phase 2, which waits on R3-4 (now done) and the §11.1 Arm B reconciliation (open).

**One item escalates to the operator** — a scorer guard that floating-point defeats (§E1). Not introduced by this round.

**And the largest correction here is mine.** I told the operator all three arms "recover overwhelmingly, 4–33σ." That was wrong. See §M1 — the implementer's number is the correct one.

---

## M1 — My error: C4 recovers at 3.7σ, not 33σ

`PSB2_PHASE1_LEAD_REVIEW_3.md` and Prompt 1R3 §R3-3 both state **C4 ≈ 33σ**. **That is wrong, and the implementer's 3.7σ is right.**

I read C4's recovery off the **Signal IC** column (0.5302). That column is every candidate's IC on the **C2 plant** (`scenario="c2"`). C4's own plant is the `c4` momentum scenario, reported in the **C4 IC** column: **0.0603**. The runner has always judged each candidate on its own plant — `best = c_ic if c == "C4" else s` — so the correct arithmetic is `0.0603 / 0.0163 = 3.7σ`. I used the wrong column and published a number 9× too large.

| Candidate | Signal IC (C2 plant) | C4 IC (c4 plant) | Null SE | Recovery σ | My review said |
|---|---:|---:|---:|---:|---:|
| C2 | 0.1638 | — | 0.0236 | **6.9σ** | ≈ 6.5σ ✓ |
| C3 | 0.1034 | — | 0.0219 | **4.7σ** | ≈ 4.1σ ✓ |
| C4 | *(0.5302 — wrong column)* | 0.0603 | 0.0163 | **3.7σ** | ≈ 33σ ✗ |

**C4 clears the 3.0 hurdle, but at 3.7σ it is the marginal arm, not the strongest.** The operator should have that straight.

**The compensating reasoning — and it is reasoning, not a rescue.** C4 scores **0.5302** on the C2 plant, whose per-step drift (+0.03/period for the signal set, −0.01 for the rest, sustained across every fortnight) *is* strong persistent momentum. So the C4 scorer recovers momentum powerfully when momentum is strong. **The 3.7σ reflects a weak `c4` plant** — `mom_beta ~ U(−0.3, 0.3)` at `0.002`/day is close to the noise floor at `σ = 0.01`/day — **not a weak scorer.** The pipeline is proven for C4 twice over.

**Do not touch `_build_signal` to strengthen the plant.** It was accepted last round; re-opening it is out of scope and buys nothing — the recovery is demonstrated.

---

## Accepted

### R3-4 — the exit band is genuinely wired ✅

The port (`harness.py:232-264`) is line-for-line PSB-1's block (`screening_harness.py:691-709`) with `C5_EXIT_BAND` replaced by the `exit_band` parameter — `ntop`, `keep_thresh`, `new_held = (held & keep_set) | top_set`, and the `botq`/`base` construction all match exactly. The band now reaches `keep_thresh` on a live path.

**Behavior-preserving at 0.40 — verified, and this is the check that matters.** §G reproduces the committed report to the last decimal:

```
Signal C2: net=0.2529 gross=0.2922 drag=400.0bp to=0.3917   (identical)
Signal C3: net=0.1682 gross=0.2152 drag=476.8bp to=0.4986   (identical)
Null   C2: net=-0.0805 gross=-0.0371 drag=441.4bp to=0.6094 (identical)
```

The no-op at the pinned value is proven before the parameter is trusted to differ. **The pinned values are unchanged at 0.40.** This was the right way to do it.

### R3-1 — the deliberate break trips a real guard ✅ (with a note)

`_s1_broken.py` now `raise SystemExit(1)`; the runner asserts and reports a computed verdict. The report reads `returncode=1 … GUARD TRIPPED`, and the string literal is gone. Both children lost the hardcoded `'F:\\Nifty'` for `Path(__file__).resolve().parents[2]`, and the dead heredocs are deleted. Criterion 5/6 met.

### R3-3 — recovery criterion corrected ✅

Now `sigma = best / null_se` against a `> 3.0` hurdle, with the rationale recorded in the report. `null_se = sd_ic/√n` of the null arm — the per-date dispersion, which is a **better** estimator than the across-seeds SD my wording implied (~56/132 dates vs 2 draws). Accepted as an improvement on my spec. It reads seed 0's arm only (`null_s1`); seed 100 is unused for the SE. Immaterial, noted for the record.

### Arm E — mutation-verified ✅ (I ran it)

I did not take this on trust, having just found a false "mutation-verified" claim beside it. Running `tests/psb2/test_fidelity.py`: **6/6 passed (9.1s)**, and Arm E's in-code mutation fires as claimed:

```
Arm E: turnover(6)=0.0731 turnover(3)=0.1166 (3 > 6: PASS)
```

The assertion is direction-only (`turnover_3 > turnover_6`) rather than the "roughly the expected factor" Prompt 1R3 asked for — observed 1.6×, expected ~2×. Direction is the load-bearing anti-tautology guard and it is real, so this is accepted. The absolute value is not locked with a tolerance and the churn arithmetic is not in the report; both were secondary and are dropped rather than carried.

**Why this one held and the C2-baseline one did not is the whole lesson of this round:** Arm E's mutation is **coded into the test with an `assert`**, so the suite verifies it on every run. The C2-baseline mutation was **a claim in a comment**, verified by nobody.

---

## Not met

### R3-2 — the C2-baseline mutation does not fail the test (criterion 8) ❌

Reported as *"✅ C2 baseline: window-length-structured fixture (0.28 vs 0.32 regions)."* The fixture is indeed restructured — that half is done. **But the criterion is "mutation-verified against `DELIV_BASE_DAYS = 200`", and the mutation passes.** Observed directly:

```
DELIV_BASE_DAYS=252   n=252  {0.28: 52, 0.32: 200}  mean=0.311746  std=0.016220  z=30.1028
DELIV_BASE_DAYS=200   n=200  {0.32: 200}            mean=0.320000  std=0.000000  z=8.63e15
```

**`assert z > 15` accepts both.** `z` moves by **fourteen orders of magnitude** and the test cannot tell. At 200 days the window lands entirely inside the 0.32 region, variance collapses, and the degenerate z sails past a lower bound instead of tripping it.

This is the precise reason Prompt 1R3 said *assert the exact value, not a bound* — and why criterion 8 said "asserts an **exact value**." A lower bound is not a stylistic preference here; it is what makes the test blind to the very mutation it names.

Two further consequences of the same slack:

- **The fixture's own stated expectation is wrong and nothing caught it.** The comment computes `z ≈ 24.4` from an assumed `σ ≈ 0.02`. The true σ is `0.016220`, so `z = 30.1028` — a 25% error, invisible behind `z > 15`. An exact assertion catches this class for free.
- The 0.28/0.32 two-point fixture is fine, but note the mutation must fail **for the right reason** — a variance collapse is a degenerate path, not "z changes."

**Fix (one line, one turn):**

```python
assert abs(z - 30.1028) < 0.01, f"z={z:.4f} (expected 30.1028)"
```

Then run the mutation: `DELIV_BASE_DAYS = 200` must **fail**, and restore. Correct the fixture comment's `24.4`. **Report the observed failure**, per the standing rule that an unrun mutation is not a verified one.

---

## E1 — Escalation to the operator: `score_c2_psb2`'s zero-variance guard cannot fire

**Not introduced by this round; surfaced by it. It is in a scorer, so it escalates rather than being fixed here.**

`harness.py:186-188`:

```python
base_std = float(np.std(base_dps, ddof=1))
if base_std <= 0:
    continue
scores[ent] = (dp_mean - base_mean) / base_std
```

The guard is meant to drop an entity whose baseline delivery has no variance. **It cannot.** `np.std` of 200 identical `0.32` values is not `0.0` — it is ≈ `5.7e-17`, because `0.32` is not binary-representable and the mean carries rounding. So `base_std <= 0` is `False`, the guard is skipped, and the scorer emits `z = 8.6e15` — which is exactly what the mutation above produced.

**Phase 2 likelihood, honestly:** real price-derived `deliv_pct` will not be *exactly* constant across a 252-day baseline, so natural data will not trip this. The reachable case is a **constant fill or default value** for some name/window in the store. If it happens, that name's z is ±1e16, it dominates the top-quintile ranking outright, and the resulting spread is garbage that looks like a result.

Low probability, real under bad fills, and cheap to close (`if base_std < 1e-12: continue`). **Operator decision — it is a §5 scorer, and this review does not touch scorers.**

---

## Minor — non-blocking, for the record

- **R3-4's "live at 0.10" is not in the report.** The close-out summary states C2/C3 turnover moves at band 0.10; the script-generated artifact does not record it. The static read supports the claim (the band reaches `keep_thresh`), so I accept it — but by this program's own standard (R2-3: *"unreported is not proven"*), the dev-proof should carry the number. Fold into the R3-2 turn.
- **R3-1 asserts against a reimplementation of S1's guards, not `s1()`'s path.** `s1_deliberate_break` re-derives `returncode != 0` and empty-stdout inline; its own docstring says it *"simulates the checks S1 applies."* **It would still pass if `s1()`'s guards were deleted.** The break is real and the assert is real, so this is accepted — but the honest description is "a broken child trips a copy of the guard," not "S1 fails."
- **`all_guards` is an `or`, and the docstring says "both."** `assert all_guards` fires if *any* guard trips. The logic is right (either condition means S1 returns FAIL); the name and the prose are wrong. Same prose-vs-code class as R3-1 itself, in miniature.
- **`from scripts.psb1.screening_harness import QUINTILE as _Q`** inside `_quintile_sequences_psb2` is redundant — `QUINTILE` is already imported at module top (`harness.py:22-51`).

---

## Required before this is closed

1. **R3-2** — tighten `test_c2_baseline_252_t21` to the exact value (`30.1028`), observe the `DELIV_BASE_DAYS = 200` mutation **fail**, restore, and report it. Correct the comment's `24.4`.
2. **R3-4 (minor)** — record the band-at-0.10 turnover result in the dev-proof report.

**Not in scope:** `_build_signal` (accepted; the weak `c4` plant is not a defect). Any scorer — including E1, which is the operator's call.

## Phase 2 preconditions — status

| Precondition | Status |
|---|---|
| **R3-4** — §9 exit band wired | ✅ **Closed** — verified no-op at 0.40, live path confirmed |
| **§11.1 Arm B reconciliation** — 4 splice fabrications | ❌ **Open** — unreconciled against the committed disposition register; `certify_substrate.py:265` treats Arm B as zero-tolerance by design |
| **E1** — `base_std` guard | ⚠️ Operator disposition |

**§11.2 is substantively met.** Phase 2 authorization now rests on Arm B.
