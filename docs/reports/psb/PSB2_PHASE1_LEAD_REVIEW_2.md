# PSB-2 Phase 1 — Lead Review, Round 2 (Prompt 1R remediation)

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** `5671026` (Phase 1 remediation, Prompt 1R), `947b99a` (debug-artifact removal).
**Against:** `PSB2_PROTOCOL.md` FROZEN Rev 4 §11.2; `PSB2_IMPLEMENTATION_PROMPTS.md` §Prompt 1R.
**Predecessor:** `PSB2_PHASE1_LEAD_REVIEW.md` (Round 1 — BLOCK).
**Date:** 2026-07-16.

---

## Verdict: **BLOCK** — but the round did its job

Phase 1 still does not pass §11.2: the harness does not recover a planted signal for C2 or C3, and three acceptance criteria are self-declared unmet.

**This is nonetheless a good round, and the reason matters.** Round 1's dev-proof reported all-PASS on a harness that could not have failed it. Round 2's dev-proof **reports FAIL** — it stated a prediction, ran, and published a result that blocks its own gate. That is the culture fix Prompt 1R existed to produce, and it worked: a dev-proof that can fail found a real defect on its first honest run.

The blocker is now **scaffolding, not the harness.** The C2/C3 signal is planted in a way that mathematically cancels before it reaches the forward return (R2-1). The strongest evidence the pipeline itself is sound is in the same report: **C4, whose signal is planted correctly, recovers it (IC 0.1147 vs null −0.0144).** Same harness, same scorers, same IC path — the difference is entirely in how the two scenarios plant.

Fix R2-1 and C2/C3 should recover, or the failure becomes a real finding about the scorers. Right now the arm cannot tell us which, because it is measuring against a signal that isn't there.

---

## R2-1 — BLOCKER: the C2/C3 planted signal cancels exactly in the forward return

`run_devproof.py:59-73`. The price path is built as a random walk first, then overwritten at grid dates:

```python
price = np.ones((len(entities), len(cal))) * 100.0
for j in range(1, len(cal)):
    price[:, j] = price[:, j - 1] * (1 + rng.normal(0, 0.01, len(entities)))   # W(·)

if scenario in ("c2", "c3"):
    for j, d in enumerate(cal):
        if d in fwd_fg:                       # d is a grid date
            tp = fwd_fg[d]                    # the NEXT grid date
            tp_idx = cal_pos[tp]
            for i, e in enumerate(entities):
                boost = 0.04 if e in sig_set else -0.02
                price[i, tp_idx] = price[i, tp_idx - 1] * (1 + boost)
```

`fwd_fg` maps **every** grid date to its successor, so **every grid date except `fg[0]` is overwritten** with `W(tp−1) × (1+boost)`.

Now take any formation `t = fg[i]` with forward `tp = fg[i+1]`. Both are grid dates, so both carry the same factor:

```
price(t)  = W(t−1)  × (1 + boost)
price(tp) = W(tp−1) × (1 + boost)

fwd = price(tp)/price(t) − 1 = W(tp−1)/W(t−1) − 1        ← (1+boost) cancels
```

**The planted boost cancels exactly, for all 54 of ~55 formations** (only `fg[0]`, never a successor, escapes). The forward return is the bare random walk. C2's delivery z-score is being correlated against **pure noise** — hence signal IC = 0.0044, indistinguishable from the null.

A second, independent defect in the same lines: because the overwrite happens *after* the walk is generated, `price[:, tp_idx+1]` was already computed from the **un-boosted** `price[:, tp_idx]`. The boost is a one-day spike that reverts the next day and never propagates. Prompt 1R named this explicitly — *"the current planting writes single-cell spikes after the random walk is generated, so the jump reverts the next day and never propagates — build the path with the signal in it, don't overwrite cells afterward"* — and the instruction was not applied to the C2/C3 branch.

**The fix already exists in this file.** The C4 branch does it correctly (`run_devproof.py:74-79`):

```python
elif scenario == "c4":
    mom_beta = {e: rng.uniform(-0.3, 0.3) for e in entities}
    for j in range(1, len(cal)):
        drift = np.array([mom_beta[e] * 0.002 for e in entities])
        rets = rng.normal(0, 0.01, len(entities)) + drift
        price[:, j] = price[:, j - 1] * (1 + rets)      # signal built INTO the path
```

Signal in the per-step return, compounding through the path, never overwritten. **C4 is the only scenario built this way and the only one that passes.** Build C2/C3's return signal the same way: add a per-step drift to the names that should outperform over `(t, tp]`, so the boost survives into `price(tp)/price(t)`.

## R2-2 — The delivery plant is a constant-group ramp, not a per-date signal

`run_devproof.py:87-91`:

```python
if scenario in ("c2", "c3") and e in sig_set:
    frac = j / max(len(cal) - 1, 1)
    dp = 0.10 + frac * (0.70 - 0.10) + rng.normal(0, 0.05)
else:
    dp = 0.35 + rng.normal(0, 0.05)
```

`sig_set` is `entities[:n_sig]` — **fixed for all time**. The plant is therefore a permanent two-group split with a secular ramp, not a signal that varies per formation date.

Two consequences, both of which will bite even after R2-1 is fixed:

1. **The ramp is a trend, not an anomaly.** C2 measures a *deviation from a stable baseline* — recent fortnight mean vs. a 252-day baseline ending *t*−21. Against a linear ramp of slope ≈ 0.0002/day, the recent-minus-baseline gap is a near-**constant** ≈ +0.03, while the ramp inside the baseline window inflates σ. The result is a roughly constant z ≈ +0.5 for every `sig_set` name at every date — weak, and with no cross-sectional dispersion *within* the group to rank on.
2. **Constant membership cannot test what C2 is for.** With `sig_set` fixed, the "signal" degenerates to group identity. C2 is designed to detect a name whose delivery is *abnormal right now*.

**Cleaner plant:** hold `deliv_pct` stationary (0.35 + noise) for everyone, then at each formation date `t`, elevate `deliv_pct` over the fortnight `(prev_grid, t]` **for the names that will outperform over `(t, tp]`**, with the outperformance built into the price path per R2-1. That makes the z-score a genuine per-date predictor and lets the recovery prediction mean what it says.

## R2-3 — The S1 determinism result is absent from the report

The report's §H reads, in full:

```
## H — S1 Determinism (1R-1)

See S1 section below (run via `_s1_child.py`).
```

**There is no S1 section below.** The next heading is §F. The forward reference dangles and no digest, comparison, or verdict appears anywhere in the document. The summary also lists `_s1_child.py` as a **pending** item, so it is unclear the child runs at all.

Round 1 proved determinism vacuously; Round 2 does not report it. Acceptance criterion 1 required more than a working S1 — it required the proof to have been **observed to FAIL** when the child is deliberately broken. Neither the failure observation nor the passing result is present. The code fixes (`{**os.environ, ...}`, `returncode == 0`, empty-digest rejection) may well be correct — but an unreported result is not evidence. **Criterion 1 unmet.**

## R2-4 — The null arm now exceeds its own historical bound, and its prediction was dropped

| Candidate | Null IC |
|---|---|
| C2 | **−0.0687** |
| C3 | **−0.0811** |

Prompt 1's C-P1 required `null |IC| < 0.05` for all. Both C2 and C3 now breach it — and **the null prediction no longer appears in the report at all** (Round 1's Predictions table is gone; only the signal-recovery prediction survives). A bound that was being asserted in Round 1 is now silently unasserted at exactly the point it started failing. That is the Round 1 pattern in miniature, and it should not survive into Round 3 even though I am confident it was inadvertent.

The magnitude is suspicious but not damning: with `N_ENTITIES = 20` a per-date Spearman has SD ≈ 0.23, so over ~55 dates the SE of the mean is ≈ 0.031 and −0.069 sits ≈ 2.2 SE from zero. That is within reach of one unlucky seed — but it is also consistent with a systematic bias, and the two candidates lean the same way. **Restore the null prediction to the table and diagnose the sign before Round 3.** Note the panel shrank from 30 entities/3500 days to 20/3000, which makes every IC in this report noisier and puts quintiles at 4 names; the runtime win (391s → 38s) is real and welcome, but not at the cost of the dev-proof's own resolution.

## R2-5 — Formula fidelity is now entirely unreported

Round 1's report carried `## A — Formula-Fidelity Tests` (10/10, albeit tautological). **Round 2's report has no §A at all.** Combined with 1R-10 being self-declared pending, the position is: the tautological suite was correctly condemned, and nothing has replaced it. Fidelity coverage has gone from misleading to absent.

This is the criterion that most directly guards the frozen §9 parameters — Prompt 1's framing stands: *"after the freeze, a wrong constant is a code defect that produces authoritative-looking results from a spec nobody violated on paper."* **Criterion 8 unmet.**

## R2-6 — Arms D and E still missing

Self-declared pending. **Criterion 3 unmet.** Arm E remains the one that would independently confirm 1R-8's fix — it is the acceptance test for the code Prompt 1 called "the highest-risk new code in this prompt."

## R2-7 — Criterion 4 has no evidence

No section demonstrates the missing-forward panel, and none shows the primary and §4.2-imputed columns **differing**. The 1R-6 code fix is reported as done, but the check that would prove the §4.2 path is live and non-degenerate is absent. **Criterion 4 unmet.**

## R2-8 — The report's commit stamp points at pre-remediation code

`PSB2_PHASE1_DEVPROOF.md:2` reads **"Commit `f961d19`"**. The remediation is `5671026`; `f961d19` is the *previous* commit — the Round 1 code this review round exists to replace. `run_devproof.py` captures `git rev-parse HEAD` at runtime, so the report was generated before the work was committed and now permanently cites code that does not contain the changes it describes. For a script-generated artifact whose authority rests on provenance, this breaks the chain. Regenerate after commit, or stamp the tree state (`git describe --dirty`) and note it.

---

## What is right — and should be preserved

Substantial and real. None of this should be re-opened:

- **The report tells the truth when the truth is FAIL.** The single most valuable change in this round. A prediction was stated, it failed, and the failure was published rather than tuned away. Prompt 1R's line — *"If a candidate cannot clear it, that is a result to report, not a threshold to lower"* — was honored under pressure. **Criterion 2 met structurally.**
- **The fence disclosure is exactly right** (§F). The `load_panel` tautology is stated as a known limitation, `fence_check` is named as the real protection, and the §1 sole-exception question is flagged for operator disposition rather than resolved unilaterally. This is precisely what R1's T1.6 asked for. **Criterion 10 met.**
- **Grid identity now reads the real `trading_calendar`** — 56/132/28 with first/last dates, all PASS. **Criterion 9 met.**
- **C4's planting is textbook** and is the template for R2-1's fix.
- **The four correctness fixes are reported done** (1R-6 `None`-preserving forwards; 1R-7 `(prev_grid_date, t]` with the grid passed in and no unpinned constants; 1R-8 held names retained via direct `_ret`; 1R-9 explicit band parameter with the route declared). Code-level verification of 1R-6/1R-7 deferred to Round 3, when the fidelity suite (R2-5) can assert them behaviorally rather than by inspection.
- **Runtime 391s → 38s** via CSV `COPY`, and the debug artifacts were cleaned up in `947b99a`.

---

## Required for Round 3

1. **R2-1** — build the C2/C3 return signal into the price path (the C4 branch is the template). This is the blocker; everything downstream of it is unmeasurable until it lands.
2. **R2-2** — make the delivery plant a per-date signal on a stationary baseline, not a constant-group ramp.
3. **R2-3** — report the S1 result, including the deliberate-break observation criterion 1 requires.
4. **R2-4** — restore the null prediction to the table; diagnose the −0.07/−0.08 sign; restore panel size unless the runtime win can be kept at 30/3500.
5. **R2-5 / 1R-10** — the fidelity suite, mutation-verified.
6. **R2-6** — arms D and E.
7. **R2-7** — the missing-forward panel showing primary ≠ imputed.
8. **R2-8** — regenerate the report after commit so the stamp is true.

**Scope discipline:** R2-1 and R2-2 are edits to `run_devproof.py`'s scaffolding only. **No scorer, no formula, no pinned constant is in scope** — if a proposed change would touch one, that is the escalation trigger, not a fix. The harness may well be correct; this round cannot tell, because the C2/C3 arms were never given a signal to find.

---

## Note on the prior round's open items

`docs/reports/PSB1_SUBSTRATE_CERTIFICATION.md` carries an uncommitted working-tree modification: the code-commit stamp refreshed `680139f` → `b39aefe` and two disposition rows reordered (`HDFCSENETF`). **Content-neutral** — it does not bear on the Arm B reconciliation that R1's T1.5 / 1R-5 requires, which remains open and is unaddressed in this round.
