# PSB-2 Phase 1 — Lead Review, Round 3 (Prompt 1R2 remediation)

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** `b9a84ba` → `c0dfb92` (Round 3; code at `323ec1c`, report regenerated at `c0dfb92`).
**Against:** `PSB2_PROTOCOL.md` FROZEN Rev 4 §11.2; `PSB2_IMPLEMENTATION_PROMPTS.md` §Prompt 1R2.
**Predecessors:** `PSB2_PHASE1_LEAD_REVIEW.md` (R1 — BLOCK), `PSB2_PHASE1_LEAD_REVIEW_2.md` (R2 — BLOCK).
**Date:** 2026-07-16. **Amended 2026-07-17** on re-review. Three changes: **R3-4** added (§9 exit band accepted but not wired); the **"five of six are real" fidelity count corrected** (a second loose test found — folded into R3-2); **R3-1 gains a fix-location note** (the heredocs are dead; the committed children are what run). R3-1, R3-2 and R3-3 were re-verified against the code and stand as written. Verdict unchanged.

---

## Verdict: **CONDITIONAL PASS** — recommend Phase 2 authorization once two small fixes land

**The substantive gate is met.** The harness demonstrably recovers a planted signal in all three candidates, the determinism proof is real, the §4.2 imputation path is live, and the fidelity suite now tests behavior instead of restating literals. R2-1 — the Round 2 blocker — is closed decisively.

Two items remain from the first pass, both narrow and precisely specified (R3-1, R3-2). Neither touches a scorer, a formula, or a §9 parameter.

**Amendment (2026-07-17):** re-review found a third item, **R3-4** — the §9-pinned exit band is accepted as a parameter and then dropped on the floor. It changes no Round 3 number, so the verdict below is unchanged, but it *is* a §9 parameter and it must be wired before Phase 2 scores real data. It is now the one item on this list that this review had itself declared an escalation trigger — see §R3-4.

**Before anything else: two of the report's `FAIL` labels are my errors, not defects.** The C2/C3 signal-recovery failures are artifacts of a hurdle I mis-specified in Prompt 1R. They should be corrected in the report, not chased in the code. §R3-3 below.

**Recommendation to the operator:** authorize Phase 2 once R3-1 and R3-2 land. They do not warrant a further full review round; a diff check suffices.

---

## The blocker is closed

R2-1 predicted that the planted boost cancelled in the forward return and that C2/C3 were being correlated against pure noise. The fix confirms the diagnosis:

| Candidate | Round 2 signal IC | Round 3 signal IC |
|---|---:|---:|
| C2 | 0.0044 | **+0.1638** |
| C3 | −0.0255 | **+0.1034** |
| C4 | −0.0137 | **+0.5302** |

Against a null IC standard error of ≈ 0.025 (30 entities, ~55 fortnightly dates), those are ≈ 6.5σ, ≈ 4.1σ, and ≈ 33σ. **All three candidates recover their planted signal decisively.** The pipeline works, and we now have evidence rather than assertion.

Also closed and verified:

- **S1 determinism (R2-3)** — digest `8453b3e86f4089a9`, identical across `PYTHONHASHSEED` 0/1. A real digest, not the empty hash; environment inherited; `returncode` checked at line 217. The Round 1 defect is genuinely gone.
- **Missing-forward panel (R2-7)** — primary IC 0.0129 vs imputed 0.0185, **different**. The §4.2 column can now differ from the primary, which is exactly what Round 1's `date_ic` bug made impossible. Criterion 9 met.
- **Panel restored** to 30 entities / 3500 days (criterion 6), with runtime still 73s against Round 1's 391s.
- **Null prediction restored** to the report and evaluated across two seeds (criterion 5), reported honestly including its failures.
- **Report stamp is true** (R2-8). `323ec1c` is the commit containing the code that generated the report; `c0dfb92` only regenerates the report itself. The stamp correctly identifies the code that ran — the chicken-and-egg is handled correctly.
- **Fidelity suite rebuilt** (R2-5) — every constant-vs-literal tautology is gone. The tests now drive the harness, and the strongest of them assert exact values (`abs(s − 0.20) < 0.01`, `abs(s1 − 0.10) < 0.02`). Arm D exists and tests both delivery regimes. *(Amendment: my first pass scored this "five of six are real." That was too generous — see the honest sort under R3-2.)*
- **Grid identity, fence, fees** — all PASS, fence limitation still correctly disclosed.

---

## R3-1 — The S1 deliberate-break asserts nothing (`run_devproof.py:234-258`)

Criterion 4 required the S1 proof to be **observed to FAIL** on a deliberately broken child. It was not.

```python
def s1_deliberate_break(tmp_dir: Path) -> str:
    """Observe S1 FAIL on deliberately broken child (R2-3)."""
    ...
    # Should be "different" because the broken child produces constant output
    # but the real S1 should differ from this constant. We check that the
    # real S1 output differs from the broken output.
    return f"Deliberate break observed: stdout={r.stdout[:60]}... returncode={r.returncode}"
```

**The comment describes a check the code does not perform.** There is no comparison, no assertion, no branch. The function formats a string whose prefix — `"Deliberate break observed"` — is a **string literal**, emitted regardless of what happened.

And what happened was not a failure. The broken child writes valid JSON and exits cleanly, so the report reads:

```
Deliberate break: Deliberate break observed: stdout={"C2": null, "C3": null, "C4": null}... returncode=0
```

`returncode=0` is a **successful run**. S1's guards (`returncode != 0`, empty-digest rejection) are never tripped, so the break does not exercise the guard it is meant to validate. The label asserts an observation the run did not make.

This is the last surviving instance of the pattern this program has spent three rounds eliminating: **a PASS label that is a literal rather than a computed verdict.** It is small — everything around it is now genuinely verified — but it sits on the determinism proof, so it cannot stand.

**Fix:** break the child so it trips a guard S1 actually checks — e.g. `raise SystemExit(1)`, or emit an empty digest — then **assert** that `_s1_proof` returns FAIL, and report the assertion's outcome. If the break does not produce a FAIL, that is a finding about the guard.

**Fix location — read this before editing.** Both `s1()` and `s1_deliberate_break()` write their child only `if not child.exists()`, and `323ec1c` committed both children. **The heredocs in `run_devproof.py` are now dead code; the committed `scripts/psb2/_s1_broken.py` and `_s1_child.py` are what actually execute.** Editing the heredoc alone will change nothing and the run will silently keep using the old child. Fix the committed file (and keep the heredoc consistent, or delete it — a generator that never generates is the next tautology waiting to happen).

Related, worth correcting while you are in there: the committed `_s1_child.py:2` hardcodes `sys.path.insert(0, 'F:\\Nifty')` — an absolute path with the wrong case, which survives only on Windows' case-insensitive filesystem, where the heredoc it drifted from emits the correct `{ROOT!r}`. It will not run anywhere else.

## R3-2 — Arm E asserts existence, not turnover (`tests/psb2/test_fidelity.py:286`)

```python
assert res.turnover is not None, "No turnover"
```

Criterion 8 required **turnover ≈ 1/6 asserted**. This asserts that a number exists. It cannot fail unless `turnover` is `None`, and it would pass at turnover 0.0, 0.5, or 1.0 — i.e. it passes for every possible staggered implementation, correct or not.

Arm E is the acceptance test for 1R-8 (held-name retention) and for the code Prompt 1 called *"the highest-risk new code in this prompt."* It is the one check that independently confirms your own fix, and it currently confirms nothing. The dev-proof's §G reports C4 turnover at 0.0278 against the design expectation of ≈ 1/6 = 0.167 — a 6× gap that is plausibly explained by a strongly persistent planted momentum signal (the tranches keep re-selecting the same names), but **nothing in the suite tests it**, so the explanation is untested.

**Fix:** assert the turnover value against the staggered design (≈ 1/6 on a panel where rank drift forces genuine tranche churn), and mutation-verify it — set `C4_N_TRANCHES = 3`, confirm the test fails, restore.

### Amendment — the honest sort of the six, and a second loose test

My first pass wrote *"the other five tests were verified this way"* and *"five of six are real."* Re-reviewing the suite against the same standard I applied to Arm E, that count does not survive. Sorted honestly:

| Test | Assertion | Grade |
|---|---|---|
| `test_c3_21_day_horizon` | `abs(s − 0.10) < 0.02` | **Tight** — exact value |
| `test_c4_lookback` | `abs(s − 0.20) < 0.01` | **Tight** — exact value |
| `test_c2_min_8_nonnull` | asserts the entity is skipped | **Real** — boolean gate, fails if the rule moves |
| `test_arm_d_c3_sign` | `s_low > 0.02`, `s_high > 0.05` | **Loose** — one-sided, but does catch a sign flip in both regimes |
| `test_c2_baseline_252_t21` | `z > 10` | **Loose — and insensitive to the parameter it names** (below) |
| `test_arm_e_staggered` | `turnover is not None` | **Existence-only** — R3-2 |

Three are unambiguous. **`test_c2_baseline_252_t21` is a second instance of R3-2's pattern**, settleable by arithmetic without a run: the baseline is `uniform(0.28, 0.32)` on *every* day of the window (mean ≈ 0.30, σ ≈ 0.04/√12 ≈ 0.0115) and the recent 15 days are a constant `0.80`, so `z ≈ (0.80 − 0.30)/0.0115 ≈ 43` against a hurdle of `10` — roughly 4× slack. Its own print string advertises the mutation *"change 252 to 200, z changes"* — but a 200-day window over that fixture is still uniform on the same interval, so mean and σ are unchanged, `z` is still ≈ 43, and **the test still passes.** It is not sensitive to `DELIV_BASE_DAYS`, which is the one constant it exists to pin, and the print string claiming otherwise is decorative.

**Fold into the R3-2 fix — it is the same instruction:** assert the value, not a loose bound. Tighten to `abs(z − 43) < 1` (or whatever the fixture actually implies), then mutation-verify `DELIV_BASE_DAYS = 200` **fails**. To make it bite, the fixture's baseline must vary across the window — a uniform draw everywhere cannot distinguish window lengths by construction. If a mutation cannot fail the test, the test does not pin the constant.

**This changes no verdict.** The substantive Phase 1 gate is the signal-recovery proof, not the fidelity suite's tightness, and recovery holds at 4–33σ. But a review that flags one decorative label while repeating a generous count of the rest is doing the thing it criticizes, so the count is corrected here.

## R3-4 — The §9 exit band is accepted as a parameter and then discarded (`harness.py:234-241`) — *added on amendment*

```python
def _quintile_sequences_psb2(scored_by_date: list, banded: bool = False, exit_band: float | None = None):
    """Thin wrapper around PSB-1's _quintile_sequences with explicit band parameter.

    Changed from PSB-1: band is a parameter, not a module-level constant.
    """
    from scripts.psb1.screening_harness import _quintile_sequences as _qs
    return _qs(scored_by_date, banded)
```

`exit_band` is accepted and never passed on. PSB-1's `_quintile_sequences(scored_by_date, banded)` takes two arguments and reads its band from its own module-level `C5_EXIT_BAND` (`screening_harness.py:65,699`). So the full chain —

`C2_EXIT_BAND = 0.40` → `exit_band = C2_EXIT_BAND` (`:323`) → `_quintile_sequences_psb2(..., exit_band=exit_band)` (`:436`) → **dropped**

— terminates in nothing. **`C2_EXIT_BAND` and `C3_EXIT_BAND` are dead constants: no code path reads either one for effect.** The band that actually governs C2/C3 hysteresis is PSB-1's `C5_EXIT_BAND`.

The module docstring makes the claim explicitly, and the claim is false:

> *"This is a diff-clean copy with one parameter added and the band switched from a module-level constant to a parameter; the change is declared here."*

The change was declared and not made. This is the same defect class as R3-1 — **prose describing behavior the code does not perform** — but where R3-1 sits on a proof label, this one sits on a §9 pinned parameter.

**Severity — stated precisely, because this is easy to over- and under-sell.**

- **It changes no Round 3 number.** PSB-1's `C5_EXIT_BAND` is `0.40` and PSB-2 pins `0.40`. The dev-proof's C2/C3 turnover and net spread were computed with the correct band **by coincidence of the two constants agreeing**. Nothing in the report is wrong, and no result needs re-running. The verdict above stands.
- **It is a Phase 2 precondition, not a Phase 1 one.** The band drives hysteresis → turnover → net spread. That is the fee-survivability question PSB-2 exists to answer — the one constraint PSB-1 proved is binding. Phase 2 is where these bands first touch real data, and a band that silently ignores its pinned value is exactly the defect that must not be live at that moment.
- **The coincidence is the hazard.** Two constants agreeing today is not wiring. The failure is silent and arrives later: if the operator ever re-pins PSB-2's band under §9, or if PSB-1's `C5_EXIT_BAND` is touched, PSB-2 keeps using PSB-1's number and every §9 artifact says otherwise. A parameter that only works while nobody changes it is not pinned.

**Fix:** wire it. Either pass the band through to a PSB-1 function that accepts it, or implement the band locally in the wrapper. Then **mutation-verify**: set `C2_EXIT_BAND = 0.10`, confirm C2 turnover moves, restore. If turnover does not move, the parameter is still not wired. Delete the docstring claim or make it true. If PSB-1 must stay git-clean, the band belongs in the PSB-2 wrapper as real code, not as a forwarded argument to a function without the parameter.

**Escalation note.** This review's own scope line reads: *"Not in scope: any scorer, formula, plant, or §9 parameter. If a proposed fix touches one, that is the escalation trigger."* R3-4 touches a §9 parameter. It is therefore **operator-visible by this review's own rule** — flagged here rather than waved through as a diff check. My first pass missed it, which is the honest reason this amendment exists.

While in `evaluate_candidate_psb2`: line 436 hardcodes `banded=True` and ignores the local `banded` computed at `:322/:329/:336`. Inert today — C4 takes the staggered branch and never reaches line 436, so the only callers are C2/C3, which are both `banded=True`. Same smell as R3-4: a variable computed, then ignored at the call site. Fix it in the same pass; it needs no separate ceremony.

## R3-3 — The C2/C3 `FAIL` labels are my specification error. Correct the report; change no code.

The report marks C2 and C3 `FAIL` on signal recovery. **Both are artifacts of the hurdle I wrote in Prompt 1R, and neither indicates a defect.**

I specified: *"signal-arm mean IC > +0.10 **and ≥ 3× the null-arm |IC|**."* The second clause **divides by a noise draw**, and that makes it incoherent:

| Candidate | Signal IC | Null (seed 0) | 3× → hurdle | Null (seed 100) | 3× → hurdle |
|---|---:|---:|---:|---:|---:|
| C2 | 0.1638 | −0.0198 | 0.059 → **PASS** | −0.0727 | 0.218 → **FAIL** |
| C3 | 0.1034 | −0.0556 | 0.167 → **FAIL** | 0.0417 | 0.125 → **FAIL** |

The null IC is a random draw around zero with SE ≈ 0.025. Multiplying it by three produces a hurdle that swings between 0.006 and 0.22 depending on which noise draw you land on — C2's verdict **flips on the seed**. A criterion whose pass/fail depends on the magnitude of a noise estimate in its denominator is not a test of anything.

My `|null IC| < 0.05` bound (inherited as Prompt 1's C-P1) is mis-specified for the same reason: at SE ≈ 0.025 it is a ~2σ bound, so it false-alarms ≈ 5% per candidate per seed. Across four C2/C3 draws, the chance of at least one breach is ≈ 19%. Observing one at −0.0727 (≈ 2.9σ) is unremarkable — especially as C2 and C3's nulls are **not independent** (C3 consumes C2's percentile rank), so they lean together. C4's nulls are tiny (−0.0023, −0.0068) precisely because it has 132 monthly dates and is an independent construct.

**The correct test** compares the signal IC to the null's dispersion, not to a single null draw: C2 ≈ 6.5σ, C3 ≈ 4.1σ, C4 ≈ 33σ. All three recover overwhelmingly.

**Disposition — and note what is *not* in scope here.** The dev-proof's recovery hurdle is **Phase 1 scaffolding I specified in a prompt**; it is *not* a §9 pinned parameter, and the protocol pins nothing about the dev-proof's internal thresholds. Correcting it therefore touches no frozen text and requires no operator ratification. Restate the prediction as:

> **Signal-arm mean IC > +0.10, and > 3× the null-arm IC standard error** (computed across the null seeds, not a single draw).

Re-label C2 and C3 **PASS** under the corrected criterion and note the correction and its rationale in the report. **No scorer, no plant, and no constant changes.** This is a reporting fix.

Precedent: Prompt 0R2 §S1 recorded a defect originating in Prompt 0R's own wording rather than in the implementation. Same category, same handling.

---

## Round 3 credit

The two prior rounds asked for a culture change and got it. This round is the evidence:

- **The blocker was diagnosed from the review and fixed at the root** — the plant was rebuilt on the C4 template rather than patched, and the recovery numbers moved from noise to 4–33σ.
- **The failures were reported, not tuned.** C2/C3 are marked FAIL on a hurdle that, as it turns out, was mine and wrong — and the honest thing was done anyway. That is precisely the behavior Prompt 1R demanded under pressure, and it is why R3-3 is a five-minute correction rather than an undetected false PASS.
- **The two-seed null diagnosis** was run as asked and its uncomfortable result published.
- **The tautologies are gone.** The fidelity suite went from five literal-vs-literal assertions and four mutation-insensitive tests to three unambiguously real tests, two loose ones, and one existence check (R3-2). That is a large step, not a finished job — but the tests now drive the harness instead of restating constants to themselves.

Against Round 1 — where every claim in the report was unfalsifiable — this is a different artifact entirely.

---

## Required before Phase 2

1. **R3-1** — the S1 deliberate break must trip a real guard and **assert**; report the assertion's outcome. **Edit the committed `_s1_broken.py`, not the dead heredoc** (see R3-1 fix-location note).
2. **R3-2** — Arm E must assert turnover against the staggered design, mutation-verified. **Also tighten `test_c2_baseline_252_t21`** (`z > 10` where z ≈ 43, insensitive to `DELIV_BASE_DAYS`) to an exact bound with a fixture whose baseline varies across the window, and mutation-verify `252 → 200` fails. Same instruction, two call sites.
3. **R3-3** — correct the recovery criterion in the report (my error) and re-label C2/C3. Reporting only; no code.
4. **R3-4** — wire the §9 exit band, or implement it in the wrapper; mutation-verify that `C2_EXIT_BAND` changes turnover. Delete or correct the false docstring claim. *(Added on amendment.)*

**Not in scope:** any scorer, formula, plant, or §9 parameter — **except R3-4, which is on this list precisely because it is a §9 parameter that is not wired.** Its fix must restore the pinned value's authority and must not change it: `C2_EXIT_BAND` and `C3_EXIT_BAND` stay at `0.40`. If the fix requires re-pinning any §9 value, stop and escalate to the operator.

**Sequencing.** R3-1, R3-2 and R3-3 remain a diff check — they do not warrant a further full review round. **R3-4 does not need to block Phase 2 authorization, but it must land before Prompt 2 runs**, alongside the §11.1 Arm B reconciliation below. Both are now Phase 2 preconditions and should be verified together.

## Open items carried forward (not blocking Phase 1)

- **§11.1 Arm B reconciliation** (R1 T1.5 / 1R-5) — the 4 splice fabrications remain unreconciled against the committed disposition register, and `certify_substrate.py:265` treats Arm B as zero-tolerance by design. **This is a Phase 2 precondition, not a Phase 1 one** — §11.1 gates "before any candidate score touches real data," which is exactly what Phase 2 begins. It must be closed or dispositioned by the operator before Prompt 2 runs.
- **§1 sole-exception wording vs. `fence_check`'s real-store aggregate read** — flagged for operator disposition, correctly, by the implementer. Protocol is FROZEN; this needs a recorded decision, not an edit.
- `docs/reports/PSB1_SUBSTRATE_CERTIFICATION.md` still carries a content-neutral uncommitted modification (stamp refresh + two reordered disposition rows).
