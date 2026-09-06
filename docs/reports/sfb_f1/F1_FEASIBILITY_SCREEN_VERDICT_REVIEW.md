# Verdict Review — F1 Feasibility Screen (run of 2026-07-20T16:09:08)

**Reviewed:** 2026-07-20
**Artifact:** `docs/reports/F1_FEASIBILITY_SCREEN_REPORT.md`, first valid run after the R1–R12 / B1–N2 / A1 corrective passes.
**Scope:** the verdict itself. All prior code findings are closed; the instrument is sound. This reviews the measurement.

**Opinion: the reported GO is spec-compliant as coded but should not trigger the vendor purchase. My recommendation is NO-GO — or at minimum "not on this evidence."**

The mechanics are now trustworthy: TRAIN n=83 matches 2012–2018 formations, `DaysH` 18.8/18.5 is a plausible monthly hold, and the HOLDOUT drag fell from the broken 1005 bp/yr to 769 bp/yr under the corrected `n_yr`. The problem is no longer the code. It is what the numbers say.

## V1 — CRITICAL: §6's third GO condition was never evaluated

Spec §6 defines GO as three conjoined conditions:

> net expectancy robustly positive across the *full* band on **both** TRAIN and HOLDOUT, **with a MaxDD-scaled return that a real, power-deflated battery could plausibly clear.**

`decide()` (`:451-483`) evaluates the first two and **never references `max_dd`**. The clause is not advisory — it is part of the GO definition, and it is the condition this run most clearly fails:

| Fold | Net/formation (pess.) | ≈ Annualized | MaxDD | Return/MaxDD |
|---|--:|--:|--:|--:|
| TRAIN | +0.0087 | ~+10.3% | **−45.7%** | **0.23** |
| HOLDOUT | +0.0267 | ~+31.4% | −29.7% | 1.06 |

A 45.7% drawdown on a ≤10-name book for ~10%/yr net is not a return profile a power-deflated battery plausibly clears — it is the profile that killed C4 on demonstrability. The screen issued a GO without testing the criterion that discriminates hardest against it.

This is the mirror image of R1, and I want to be explicit that it is not the same error. R1 faulted gating on a threshold **absent from §6**; V1 faults **omitting a condition present in §6**. Adding invented criteria and dropping written ones are both ways of not applying the spec.

## V2 — CRITICAL: the bracket is inert, so what was screened is ≈ PSB-2 C4

`max_hold` is `n=5`: `_apply_bracket` (`:279-299`) can exit only within the first 5 bars, after which the trade falls through to the month-end fallback at `len(bars)` days. Reported `DaysH` is **18.8**.

**No arithmetic is needed to see the implication: nothing but the fallback can produce a holding period above 5 days, so a mean of 18.8 means the large majority of trades never trigger the bracket at all.** (A rough envelope puts the fire rate in the single digits to high-teens percent, depending on trading days per month — but the cap-versus-mean logic settles it without that estimate.)

The TRAIN grid search selected n=5 (grid minimum) with k_sl=2.5 and k_tp=5.0 (both maxima) — the shortest window with the widest levels, i.e. the configuration that fires least. The report's own boundary note flags this; its significance is larger than a tuning caveat.

The consequence is structural. Strip the near-inert bracket and F1 reduces to plain monthly-rebalanced 12-1 cross-sectional momentum, long-only, ≤10 names — the same signal family whose binding constraint on this panel has always been **demonstrability, not fees**. (Not literally PSB-2 C4, which used a staggered 6-month hold against F1's 1-month; and C4's power figure came from the rank-IC/noncentral-t framework F1 explicitly retired in §5, so that number does not transfer. The family-level lesson does.) Spec §0 states the trap directly:

> C4 died on *power* (demonstrability), not fees — so a favorable assumed fee model cannot by itself resurrect the construct.

The screen swapped delivery-equity STT for a futures fee stack and found the economics survive. But fees were never this signal family's binding constraint on this panel. **The screen answered a question that was not the one blocking the construct** — and V3 shows the demonstrability question failing again, this time in F1's own bootstrap terms.

This also touches the CLAUDE.md guard note: F1's licence to exist rather than being "a C2 reopen" rested on brackets being ATR-scaled and TRAIN-fold-selected. That is satisfied *procedurally* — but a mechanic selected into near-inactivity does not differentiate the construct in substance.

## V3 — HIGH: TRAIN CI spans zero at every slippage level, including optimistic

| Slippage | TRAIN Exp | CI low |
|---|--:|--:|
| optimistic | +0.0154 | **−0.0024** |
| mid | +0.0132 | **−0.0047** |
| pessimistic | +0.0087 | **−0.0091** |

In the prior run only mid and pessimistic straddled zero. Now **no TRAIN slippage setting produces a CI excluding zero** — the fold offers no statistically distinguishable evidence of positive expectancy at any cost assumption.

**What this does *not* establish.** Spec §4's conservatism invariant fires only if the construct "survives *only* at the optimistic end of the slippage sweep." TRAIN point estimates are positive at all three settings, pessimistic included (+0.0087), so §4 is **satisfied, not violated** — the construct does survive the full band. An earlier draft of this section claimed §4 was engaged; that was wrong, and it repeated the B4 error: importing statistical significance as a criterion the spec nowhere states. I hold the B4 resolution — §6's "robustly positive" most plainly means *point estimate positive at every slippage setting*, and on that reading the code's GO is correct.

**What it does establish.** TRAIN expectancy is not statistically distinguishable from zero anywhere in the band. That is not a spec violation; it is the reason the undefined word "robustly" cannot be left unpinned. Note this is the same underlying weakness as V2 — demonstrability, measured now in F1's own bootstrap terms rather than an imported one. Pin CI-exclusion-of-zero (or explicitly reject it) in the real battery's pre-registration, before results are visible.

## V4 — MEDIUM: the GO rests almost entirely on one favorable regime

HOLDOUT carries the verdict — 3× TRAIN's expectancy with cleanly positive CIs. But HOLDOUT is 2019–2022, n=47 formations across ~4 years, spanning the COVID crash and the 2020–21 momentum rally: an unusually favorable regime for concentrated long-only momentum.

The TRAIN-weak / HOLDOUT-strong inversion is the opposite of the usual overfitting signature, so it is not evidence of curve-fitting. But the benign reading (the construct is genuinely fine and TRAIN is noisy) and the adverse reading (HOLDOUT caught one hospitable regime) are not distinguishable at n=47 — and the screen has no mechanism to separate them, having retired power analysis by design (§5). Buying vendor data to test a construct whose entire positive evidence comes from one four-year regime is exactly the spend the screen exists to prevent.

## V5 — LOW: report/code text discrepancies

- Caveat 6 and the Configuration block describe the open-gap step as "approximated via daily low/entry" and "via daily bar low." The code actually uses the **open** price (`_op_cache`, `open_p <= sl` at `:285-289`) — a real improvement. Both the report strings and the stale note in `_apply_bracket`'s docstring (`:272-273`) understate what was implemented.
- The HOLDOUT table prints the `* CI lower bound <= 0` footnote (`:546`) unconditionally, though no HOLDOUT row is flagged.

## Recommendation

**Do not purchase vendor data on this result.** The GO is produced by a decision function implementing two of §6's three GO conditions, applied to a construct whose distinguishing mechanic fires on ~7% of trades, on evidence whose TRAIN fold cannot exclude zero at any cost assumption and whose positive signal comes from a single favorable regime.

Concretely, before this question is reopened:

1. **Evaluate §6's MaxDD condition in `decide()`** (V1). Pin the threshold before re-running, not after seeing this table.
2. **Resolve whether an inert bracket is acceptable** (V2). If the grid keeps selecting the bracket away, either widen the grid so the mechanic can be tested honestly, or accept that F1 ≈ C4 and confront the power question C4 died on — a fee model cannot substitute for it.
3. **Decide the "robustly positive" question** (V3) — CI-exclusion-of-zero or point estimate — and pin it in the real battery's pre-registration.
4. Fix V5's text so the report describes the code.

A NO-GO here costs nothing and is the outcome the screen was built to produce cheaply. Per §0/§2, the screen's optimistic biases (over-inclusive universe proxy, prior-exposed signal, assumed costs) mean a NO-GO from it is robust while a GO is not — the asymmetry runs against acting on this result.
