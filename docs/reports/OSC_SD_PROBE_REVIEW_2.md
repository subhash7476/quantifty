# OSC SD/Breadth Probe — Lead Review, Round 2 (corrective run)

**Date:** 2026-08-02
**Reviewer:** Claude (review only, per standing role split)
**Reviews:** the C-1 … C-6 corrective run, against `OSC_SD_PROBE_REVIEW.md` §7
and `OSC_SD_PROBE_PROMPT.md` §3.4 / §3.6 / §8.
**Round 1:** `OSC_SD_PROBE_REVIEW.md`

---

## 1. Settled — the probe's stated question is answered

| Series | mean_IC | sd_IC | NW t |
|---|--:|--:|--:|
| Same-day (contaminated) | −0.0615 | 0.2032 | −8.49 |
| **Skip-a-day (ladder input)** | **+0.0198** | **0.2068** | **+2.73** |
| Backward (C-1b) | +0.0185 | 0.2067 | +2.57 |
| Trail-IV (C-2) | +0.0192 | 0.1976 | +2.70 |

- **CRITICAL-1 is confirmed and resolved.** `|mean_IC|` fell 67.8% — past the >60%
  rung pinned in round 1 §7 — so the same-day number is void, as pre-registered.
  The shift is in fact larger than that framing suggests: the artifact contributed
  **−0.0813**, exceeding the observed same-day IC outright and reversing its sign.
- **`sd_IC` = 0.2068 on the clean predictor ≤ 0.2207. Green stands.** It also lands
  where round 1 §2 predicted (essentially unchanged, marginally above 0.2032),
  which is a small independent check that the correction did what it claimed.
- All four series agree on `sd_IC` ≈ 0.20 ± 0.01. **The dispersion question is
  robust and closed.** MEDIUM-1, MEDIUM-3 and the LOW items are accepted as fixed.

**The probe delivered exactly what it was built for.** What follows does not undo
that; it concerns whether the *construct* survives, which is a separate question.

## 2. CRITICAL-2 — the feature is structurally blind to the effect that motivated OSC

**This is an error in my own prompt (§3.4), not in the implementation.** It is
load-bearing enough that Green must not be read as "proceed to design."

`_fit_iv_surface` regresses `iv ~ 1 + m + m² + tau + m·tau` per day
(`sd_probe.py:113` supplies the intercept). **A per-day intercept removes the
cross-sectional level of implied vol.** `richness` is the residual, so it has ~zero
mean every day by construction and carries **no information about whether the
surface as a whole is rich.**

The variance risk premium *is* a level effect: the whole surface is expensive
relative to subsequent realized vol. A daily cross-sectional rank IC cannot see it —
and as round 1 §4 already noted for `N_eff`, **rank correlation is invariant to a
common additive shift.** I drew that point for breadth and failed to draw it here,
where it matters more.

Consequences, all following directly:

1. **OSC as specified is not a VRP construct.** It is a relative-smile-value
   construct. The economic thesis in `INDEX_CONSTRUCT_DIAGNOSIS.md` §4 and
   `OPTIONS_STRATEGY_RESEARCH.md` (O1) — the documented, structurally-persistent
   Nifty variance risk premium — **does not transfer to this feature.**
2. **The δ anchor designated in prompt §8 is void.** Goyal & Saretto rank on
   IV-versus-realized-vol, a level measure; Bakshi & Kapadia measure delta-hedged
   gains on the level. Neither anchors the effect size of *a residual from a daily
   quadratic smile fit*. Prompt §8 called the δ anchor an open problem; it is now
   worse than open — the designated source does not apply.
3. **The prompt's "expected sign is NEGATIVE" (§3.6) was under-argued.** It was
   reasoned from VRP, which the intercept fits away. So the positive clean IC does
   not falsify a well-founded prior; there was no well-founded prior. P4 should be
   treated as void in both directions rather than as FAILED.

## 3. HIGH-1 — the backward IC does not confirm contamination, and it raises a new problem

The summary reads C-1b (+0.0185) as independent confirmation of the bounce
mechanism. **By the threshold I pinned in round 1 §7, it is not.** That rule was:

> Large positive backward IC (say `> +0.04`) → contamination confirmed, near-proof.
> Backward IC near zero → the same-day number is largely exonerated.

+0.0185 clears neither branch. Worse, the simple bounce model makes a *quantitative*
prediction that fails: if the artifact contributed −0.0813 forward, symmetry implies
roughly **+0.08** backward. Observed is **+0.0185** — about a quarter of that.

Part of the gap is expected asymmetry: the forward return carries `ε_t` through
*three* channels (`−settle_t`, `delta_t`, and the `vega_t` denominator), while the
backward return carries it through one (`+settle_t`). That widens forward
contamination relative to backward. It does not obviously account for a 4× gap.

**Contamination is nonetheless established** — by C-1 itself, where a 0.0813 sign-
reversing shift admits no other explanation. C-1b simply did not behave as modelled,
and that discrepancy is unexplained.

**The new problem is what C-1b actually shows.** Backward IC (+0.0185) is
statistically indistinguishable from forward skip-a-day IC (+0.0198). **A predictor
that "predicts" the previous day's return as well as it predicts the next day's is
not forecasting.** That is the signature of `richness` and `dh_return_scaled` both
loading on a persistent, slow-moving state variable — a vol-regime or
liquidity-regime term — rather than of genuine predictive content. Trail-IV (+0.0192)
sits in the same narrow band and is consistent with the same reading.

This does not prove +0.0198 is spurious. It does mean **+0.0198 has not been shown
to be forecasting power**, and it is the only number that would justify a δ band.

## 4. MEDIUM-1 — the sign is now a discovered parameter (Carry v1 precedent)

The pre-registered direction was negative; the clean measurement is positive. Whatever
sign a future declaration pins, **it will have been chosen after seeing 2023–2025
data.** This is precisely Carry: *"TRAIN | Burned | v1 sign discovery (IC +0.041,
wrong sign); v2 registered positive sign."*

The damage is limited — 2023–2025 was already burned by the MSRP triage, so nothing
new was spent, and Carry went on to pass SEALED after re-registration. But two
things are now mandatory rather than optional:

1. The sign must be **pinned in the pre-registration before any 2016–2022 read**, and
2. the declaration must state **in plain words** that the sign was discovered on
   2023–2025 and is not derived from theory — especially given §2, where the theory
   that would have supplied it does not apply.

## 5. Standing and what is actually needed next

**Green on `sd_IC` is accepted and closed.** 0.2068, robust across all four series.
Round 1's suspension on that ground is lifted.

**OSC is not cleared to proceed to design**, on §2 and §3 — which are about the
construct, not the measurement:

- **§2 must be resolved by a decision, not a measurement.** Either (a) respecify the
  feature so it retains the level — e.g. richness against a *realized-vol* reference
  rather than a same-day fitted surface, which restores the VRP thesis and the
  Goyal–Saretto anchor but is a materially different construct needing its own
  RFA; or (b) keep the residual feature and build an honest economic case for
  relative smile value, accepting there is no literature δ anchor and finding one
  elsewhere. **(a) is the more defensible path**, and note it changes what OSC is.
- **§3 needs one diagnostic before +0.0198 counts as forecasting:** report the
  autocorrelation of `richness` at the cell level, and the forward IC computed on
  *changes* in richness (`richness_t − richness_{t−1}`) rather than its level. If a
  persistent state variable is driving both sides, the level IC survives and the
  change IC collapses. That is cheap, stays on the burned window, and is the
  difference between a signal and a shared regime term.

Neither is a reason to stop. Both are reasons not to write a declaration yet.

## 6. Note on my own error

Prompt §3.4 specified an intercept in the surface fit, and prompt §8 designated a
δ anchor from VRP literature. Those two choices are mutually inconsistent, and I
made both. The corrective run is what surfaced it — the sign flip forced the
question of what the feature actually measures. Recorded here so the pre-registration
does not inherit the same inconsistency.
