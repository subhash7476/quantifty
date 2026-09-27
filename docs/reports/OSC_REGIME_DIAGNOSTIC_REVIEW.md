# OSC Regime Diagnostic — Lead Review

**Date:** 2026-08-02 | **Reviewer:** Claude (review only)
**Reviews:** D-1…D-4 run against `OSC_REGIME_DIAGNOSTIC_PROMPT.md` §2

**Verdict: the GENUINE SIGNAL rung did NOT fire. The static-tilt hypothesis is
neither confirmed nor rejected — D-4 cannot test it as specified, and that is my
spec error.**

---

## 1. The rung is a conjunction, and half of it failed

Prompt §2, third row, verbatim:

> D-4 IC < 40% of level IC **and** D-2 change IC materially non-zero (NW t ≥ 2)
> → Genuine daily cross-sectional signal.

**D-2 came in at NW t = 1.32.** The report itself calls it "below threshold." The
`and` is not decorative — it was pinned precisely because D-4 alone cannot separate
"the live signal carries new information" from "D-4 is measuring something else."
Firing the rung on the D-4 clause alone is post-hoc rung selection.

Second problem with the same reading: **D-4 = −0.0398 is outside the space the
ladder contemplated.** The rungs (≥80%, 40–80%, <40%) were written for a stale
ranking explaining *some fraction* of a live signal — a positive ratio. A ratio of
−200% is technically "< 40%," but that is a degenerate satisfaction of the
inequality, not the condition it encoded. A ladder does not apply outside its domain
just because an inequality happens to evaluate true.

## 2. CRITICAL — D-4's window cannot be populated, and is confounded with DTE

The probe pins `7 ≤ DTE ≤ 60` (`OSC_SD_PROBE_PROMPT.md` §3.1). A cell —
`(expiry_dt, strike, option_type)` — therefore enters the panel at DTE 60 and leaves
at DTE 7. **Maximum lifetime in the panel is 53 calendar days ≈ 38 trading days.**

D-4 asks for a **60-day trailing mean rank.** That window can never be fully
populated for *any* cell, and for most is filled by far fewer observations.

Worse than sparsity, it is **systematically biased in DTE**. A cell's trailing
window is drawn from the earlier, longer-dated part of its life, while the return
being predicted sits at a later, shorter DTE. So the "frozen ranking" is not a stale
version of the live ranking — it is largely *a measurement of the cell at higher
DTE*. If richness-versus-forward-return flips sign across the term structure (which
is entirely ordinary), D-4 reproduces that flip and reports it as anti-prediction.

**Consequence: D-4 = −0.0398 (t = −2.19) is not evidence that the standing tilt is
anti-predictive. It is not evidence about the standing tilt at all.** The decisive
diagnostic did not run. This is my error — I specified a 60-day window without
checking it against the DTE band that bounds cell lifetime.

## 3. What the *valid* diagnostics say — and it leans the other way

D-1 and D-3 are unaffected by the above and both bear directly on persistence:

- **D-1: lag-1 autocorrelation 0.79**, ~7-day half-life.
- **D-3: lag-1 rank ρ = 0.88** — the cross-sectional ranking is near-identical
  day to day.

Prompt §2's corroborating expectation under the static hypothesis was "lag-1 > 0.7,
still elevated at lag 20." **Lag-1 is 0.79 and 0.88 — the static-hypothesis
expectation is met at lag 1.** The lag-5 and lag-20 figures were not reported and are
required before anything is concluded; a 7-day half-life implies ρ is still
materially positive at lag 5 and decayed by lag 20, which would be the more
reassuring shape.

High persistence alone is **not** disqualifying — Carry and CB-N50 both have
persistent rankings, and a 7-day half-life means the signal genuinely does move. But
the valid evidence currently points *toward* the concern that prompted this
diagnostic, not away from it, and D-2's insignificance (t = 1.32) is consistent with
that: the one-day change carries little.

## 4. The result is nonetheless interesting — a two-component reading

Taking D-4 at face value would be wrong, but the *pattern* suggests a decomposition
worth testing properly. Live richness and a trailing mean of it must be highly
correlated (D-1 = 0.79). Two strongly correlated predictors with opposite-signed ICs
implies the live signal splits into components with different content:

- a **persistent level** (structurally rich cells — the classic OTM-put overpricing
  tilt) predicting *under*performance, and
- a **deviation from that level** predicting *out*performance — plausibly implied
  vol moving ahead of realized vol, which is economically sensible.

If real, that is a better outcome than "not a static tilt": it is two separable
effects rather than one. But D-2, the only clean test of a deviation component, is
insignificant — and D-2 measures a *one-day* change, which is noisy and not the same
quantity as "deviation from a multi-week norm." So the story is **suggested, not
established.** The quantity that would establish it was never computed.

## 5. Corrective run — required before the rung is read at all

Same constraints throughout: fence 2023-01-02…2025-12-31, skip-a-day convention, no
tuning, 2016–2022 untouched, `build_paired_panel()` parity preserved.

**E-1 — report D-1 and D-3 at lags 5 and 20.** Already computed per the prompt;
simply absent from the summary. Needed to judge persistence shape.

**E-2 — D-4 re-specified (D-4R).** Two changes, both required:
1. Trailing window of **10 trading days**, which fits inside typical cell lifetime.
2. Ranks computed **within DTE tercile**, so the frozen predictor is not a proxy for
   "this cell at higher DTE."
   Report the median number of observations actually populating each cell's window —
   if it is not ≥ 8, the test is still not running and must be reported as such
   rather than interpreted.

**E-3 — the decisive test, which was missing: residual IC.** Rank IC of
`richness_rank_{t−1} − trailing_mean_rank_{t−1}` (the deviation-from-own-norm,
10-day window, within DTE tercile) against `dh_return` over `t → t+1`. This is the
direct measure of incremental daily information and the direct test of §4's
two-component reading.

**E-4 — level-component IC.** Same, for the trailing mean rank alone. E-3 and E-4
together decompose the +0.0198 and are the only basis on which a δ band could later
be argued for either component.

### Pre-registered interpretation — fixed now

| Result | Reading |
|---|---|
| E-3 IC significantly positive (NW t ≥ 2) | Genuine incremental daily signal. §4's two-component reading holds. Proceed to the feature decision (`OSC_SD_PROBE_REVIEW_2.md` §5). |
| E-3 IC insignificant, E-4 IC significant | The +0.0198 is a standing tilt. `per_trade_pnl`, index power wall, kill. |
| Both insignificant | The +0.0198 does not survive decomposition. Kill. |
| Both significant, opposite signs | Two separable effects; each needs its own declaration and its own δ. Do not net them. |

**Do not adjust these after seeing results. Do not re-fire the §2 ladder — it is
retired; E-3/E-4 replace it.**

## 6. Standing

`sd_IC = 0.2068` Green remains banked and is untouched by any of this. The
2016–2022 window (1,701 formations) remains unread. Nothing has been spent.

OSC is **not cleared**. It is also **not killed** — the test that would decide it has
not yet run.

## 7. My errors, recorded

1. **§2's 60-day D-4 window is incompatible with the 7–60 DTE band** I pinned in the
   probe. I specified a test whose window exceeds the maximum lifetime of the units
   it measures.
2. **§2's ladder had no domain guard** — no rung for a negative D-4, so an
   out-of-domain value satisfied an inequality and produced a verdict.

Both belong in the pre-registration's list of retired diagnostics so a later reader
does not resurrect them.
