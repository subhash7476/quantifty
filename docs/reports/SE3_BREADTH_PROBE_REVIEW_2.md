# SE-3 Breadth Probe — Lead Review (Round 2, corrective run)

**Reviewer:** Claude (review only, per standing role split)
**Implementer:** DeepSeek V4
**Date:** 2026-08-05
**Reviewed:** the corrective run against `SE3_BREADTH_PROBE_REVIEW.md` §Disposition
**Predecessor:** Round 1 — implementation ACCEPTED, measurement PROVISIONAL

---

## Verdict

**All three dispositions ACCEPTED. The ladder reading is no longer provisional: it is final
at Green (permissive, n=1,701) / Red-amber (strict, n≈495), on the clean skip-a-day
`sd_IC`.**

**One new finding (MEDIUM-2): P7's FAILED verdict is confounded and does not establish what
it appears to.** It does not affect the ladder. It does affect a design decision the
pre-registration would otherwise make on this evidence.

---

## CRITICAL-1 — resolved, and correctly

I checked the construction rather than the reported numbers, because the failure mode I was
most worried about would have reproduced plausible-looking output.

```python
panel_skip["dh_skip"] = panel_skip.groupby("underlying")["dh_return_scaled"].shift(-1)
```

`dh_return_scaled` on row `t` is the `t → t+1` return built from `Delta_t`, `vega_t`,
`V_t`. Shifting `-1` **within name** therefore places, on row `t`, the return over
`t+1 → t+2` built entirely from `Delta_{t+1}`, `vega_{t+1}`, `V_{t+1}`.

**`V_t` is absent from the return.** The signal keeps it, the return does not, and the
mechanical negative link is broken.

The specific defect I was checking for — reusing a **stale `Delta_t`** to hedge a
`t+1 → t+2` move, which would reintroduce a directional/gamma term and quietly
recontaminate the measurement — **is not present.** The delta, vega, and base price all
belong to the return's own window.

Minor, non-blocking: `shift(-1)` takes the *next available row for that name*, not
necessarily the next calendar session, so a name absent on an intervening date gets a
wider-than-one-day skip. At 0.3% leg attrition this is negligible and does not warrant a
re-run.

### The result

| Variant | same-day `sd_IC` | skip-a-day `sd_IC` | Δ | Rung (permissive / strict) |
|---|---|---|---|---|
| A | 0.1938 | **0.1877** | −3.1% | Green / Red-amber |
| B | 0.1989 | **0.1814** | −8.8% | Green / Red-amber |

Against the boundaries frozen in Round 1 *before* this run (`4dd6148`): Green requires
`sd_IC ≤ 0.2207` permissive; strict stays Red-amber until 0.2303. Both variants clear
comfortably. **The Round-1 prediction that the verdict would survive the fix is confirmed,
and it was pre-committed rather than asserted afterward.**

### On the persistent negative mean

`mean_IC` stays at −0.113 (A) / −0.079 (B) in the clean construction, so the sign is **not
purely** the bounce artifact — the implementer is right about that, and it is the correct
thing to have reported.

It should still be treated as a flag, not a finding. A sustained daily cross-sectional rank
IC of −0.113 is roughly **6× OSC's clean +0.0198** and **4× CB-N50's TRAIN +0.059**. The
*direction* is economically expected (rich options underperform delta-hedged — the variance
risk premium, Goyal & Saretto). The *magnitude* is not something a burned-window read can
establish. §7/§8 already forbid it becoming the δ anchor, which disposes of it for gate
purposes; I am recording it so that a design-time reader does not mistake "survived the
skip-a-day fix" for "independently corroborated."

---

## MEDIUM-1 (leg-level attrition) — resolved

73,446/73,644 legs paired, 0.3% attrition, replacing the name-level 0.1% (47 names). P9 is
now evaluated on the rate §3.7 actually asked for. Correct.

---

## MINOR-1 (`N_eff` bias direction) — resolved

Recorded as an upper estimate with the mechanism stated. Correct, and the
between-OSC-and-nominal conclusion is unaffected.

---

## MEDIUM-2 (NEW) — P7's FAILED verdict is confounded by sample, not established

P7 predicted `sd_IC(B) ≥ sd_IC(A)`, reasoning that the trailing-β estimate **adds
estimation noise**. That is a claim about an *estimator*, and it is only testable **holding
the sample fixed**.

The measurement does not hold the sample fixed. Per §3.6, variant B drops every name
failing the 40-paired-observation minimum in the trailing 60 days, and it is reported on
**484 dates against A's 713**. So A and B differ in *three* ways at once — estimator,
name universe, and date set — and P7 attributes the whole difference to the first.

**The most likely alternative explanation runs the opposite way.** B's 40-observation
minimum preferentially excludes names with short or patchy IV history — the thinnest,
noisiest single-stock chains. Dropping the noisiest names would **lower** `sd_IC` on its
own, with no help from the estimator. The observed gap is 0.1814 vs 0.1877 — **3.4%**,
small enough to be fully accounted for by that selection.

**My own §3.6 anticipated this and I still wrote the confounded prediction.** It says the
two universes *"are not the same panel and must not be silently merged."* P7 compares them
directly. That is a defect in the prompt, not in the implementation — the implementer
reported the comparison exactly as pinned and correctly marked it FAILED.

### Why it matters, and why it is not urgent

- **No effect on the ladder.** Both variants land on the same rung under both readings. The
  gate arithmetic is untouched.
- **Real effect on design.** P7 existed to answer *"does the index anchor earn its keep?"* —
  a live choice for the eventual pre-registration. On the current evidence the honest answer
  is **not established either way**, and a reader could easily take "B costs less
  dispersion" as a reason to adopt the index-anchored form. That would be a construct choice
  made on a confounded comparison.

### Recommended resolution — cheap, and not now

Recompute both variants on the **common `(date, name)` subset**: restrict A to B's universe
and dates, leaving the estimator as the only difference. Same burned window, no new data, no
purity cost.

**This is not a blocking corrective and should not trigger a third round.** It belongs with
the design work if and when SE-3 proceeds past the gate. Recording it here so the
pre-registration inherits the caveat rather than the headline.

---

## Disposition

- Round 1's three items: **closed.**
- Ladder: **final** — Green (n=1,701) / Red-amber (n≈495), keyed on skip-a-day `sd_IC`
  0.1877 (A) / 0.1814 (B).
- Predictions: **9/10 HELD, P7 FAILED-but-confounded** (see MEDIUM-2). P5 re-keyed to the
  informative skip-a-day reading, which resolves the Round-1 objection that it was
  unfalsifiable.
- **MEDIUM-2 carries forward to design time, not to another probe round.**
- Transportable output of this probe: **`sd_IC` only.** `mean_IC` and `N_eff` carry stated
  caveats (δ-anchor prohibition; upper-estimate bias respectively).
- Windows: the 1,701-date unread index-option window and the 2021–2022 joint-clean
  stock-option window remain untouched. Nothing written under `data/`.

**The probe has answered its question.** SE-3's effective breadth is 5.9 (upper estimate),
its clean dispersion is 0.1877, and the demonstrability arithmetic is feasible under the
permissive window reading and not under the strict one. The δ half remains open and must be
sourced externally at design time (§8).

---

## Operator decision, 2026-08-05 — the permissive reading is adopted

**Decision:** the permissive `n = 1,701` reading is **defensible and adopted.** SE-3's
confirmatory window is therefore **2016-02-11 → 2022-12-31, 1,701 daily formations, on both
option legs**, and the Skew sleeve's 2016-07-31 → 2020-12-31 TRAIN read is treated as
**disclosed prior exposure, not a spent window.**

**Grounds** (recorded so a future reader can test them rather than inherit them):
1. Skew measured a **different quantity** — 25-delta risk-reversal, a wing/asymmetry
   feature — against SE-3's **ATM level richness**.
2. At a **different cadence** — monthly formations against daily.
3. Skew **failed** at §9 gate 2 (IC −0.018, t = −1.15), so no selection pressure was applied
   toward a surviving variant on that surface. A failed read leaks less than a successful
   one, because nothing was chosen on the strength of it.

### Ladder consequence

At `n = 1,701` both variants sit at **Green** — feasible even at a pessimistic δ = 0.015.
The strict-reading Red-amber is now a **recorded sensitivity, not the operative verdict.**

### What this does NOT authorize

**Green is a floor, not a decision.** Verbatim from §8 of the prompt: this probe *"cannot by
itself authorize SE-3 even if it returns Green — it supplies the SD half of the RFA input and
leaves the δ half open."* Before any construct code exists, SE-3 still requires:

1. A **δ band from external literature** — Goyal & Saretto (JFE 2009), Bakshi & Kapadia
   (RFS 2003). **Not** this probe's `mean_IC`, **not** CB-N50's +0.029, **not** OSC's
   +0.0167.
2. A **frozen declaration** under contract v2, SHA-256 pinned.
3. A **passing RFA gate run.** Probe-ladder Green and gate PROCEED are different tests
   against different inputs. FLOW, RS-MOM and SE-1 all show the gate rejecting things that
   looked reachable beforehand.

### The condition that would retroactively invalidate this decision

Stated now, before the construct is designed, so it cannot be negotiated later:

> **If SE-3's eventual signal drifts from ATM level richness toward wing or skew features,
> grounds (1) and (2) collapse and Skew's exposure becomes a spend.** `n` then falls to
> ≈ 495, the rung falls to **Red-amber**, and the construct is not demonstrable at any
> defensible δ.

The pre-registration must therefore **pin the signal to ATM level richness** and either
demonstrate low correlation with the risk-reversal quantity Skew tested, or accept the
strict reading from the outset. This is a falsifiable guard on the decision above, not a
caveat about it.

### One further selection to declare

The probe measured **two variants** and the eventual construct will adopt one. That choice
is legitimate — it is made on the burned window, which is what a burned window is for — but
it is a selection with **m = 2** and must be declared as such. **MEDIUM-2 means the
comparison that would naturally inform that choice is confounded**, so the variant should be
chosen on *a priori* grounds (which quantity the mechanism actually implies), not on the
0.1877-vs-0.1814 gap.
