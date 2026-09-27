# OSC — Feasibility Verdict: ABANDON

**Date:** 2026-08-02 | **Author:** Claude (review only)
**Status:** Terminal for OSC as specified. **No pre-registration was written. No
declaration was frozen. The 2016-02-11 → 2022-12-31 window (1,701 formations)
remains UNREAD.**

---

## 1. The verdict, in one line

At the E-3 feature's own measured `sd_IC = 0.2502` and `n = 1701`, **power 0.80
requires δ ≥ 0.01701 two-sided (0.01509 one-sided). The TRAIN measurement of that
feature, cleaned of the moneyness artifact, is +0.0167 — and that is the
*un-shrunk in-sample* number.** OSC clears the gate only if the out-of-sample IC is
assumed to equal or exceed the in-sample IC. That is not defensible, so the
construct is not demonstrable on the available window.

## 2. The contradiction in the closing summary

The three closing items are mutually inconsistent, and item 1 is the correct one:

- **Item 1** states `sd_IC = 0.2502` is **Amber — "feasible only if δ ≥ 0.020 is
  independently defended."** Correct.
- **Item 2** states that at **δ = 0.015, power at n=1701 clears 0.80.** **This is
  false.** Computed from `scripts/rfa/power.py`: δ=0.015, sd=0.2502, n=1701 gives
  **power 0.6954** two-sided (0.7958 one-sided, also short). `n_required` = 2,186
  against 1,701 available.

Item 2's δ = 0.015 was carried over from the earlier arithmetic, which was run at
`sd = 0.2068` — the **level** feature's dispersion. Once the feature changed to
E-3, its own sd (0.2502) applies, and the δ that clears moves with it. The two
numbers were combined across features.

## 3. Full arithmetic (n = 1701, sd = 0.2502)

| δ | power (2-sided) | n_required | power (1-sided) |
|---|--:|--:|--:|
| 0.0084 (51% haircut) | 0.2823 | 6,966 | 0.3971 |
| 0.0100 | 0.3773 | 4,916 | 0.5012 |
| 0.0125 (25% haircut) | 0.5396 | 3,147 | 0.6609 |
| 0.0150 | 0.6954 | 2,186 | 0.7958 |
| **0.0167 (TRAIN, no haircut)** | **0.7856** | **1,764** | **0.8658** |
| 0.0200 | 0.9091 | 1,231 | 0.9506 |

**Minimum δ clearing power 0.80:** 0.01701 two-sided, 0.01509 one-sided.

**It fails at the most generous possible reading.** With *zero* shrinkage —
asserting the confirmatory IC will exactly match the in-sample one — the
noncentrality is `(0.0167/0.2502)·√1701 = 2.7527` against the ~2.80 required.
**It misses by about 2%.** Every honest adjustment moves it further away, never closer.

## 4. Why zero shrinkage is not available

CB-N50 measured the shrinkage empirically on the *same repo, same market, same daily
cross-sectional rank-IC methodology*: **TRAIN +0.059 → HOLDOUT +0.029, a 50.8%
haircut.** Applying that to +0.0167 gives δ ≈ 0.0082 and power **0.27**.

Even a token 10% haircut gives δ = 0.01503 → power 0.6971. **No non-zero shrinkage
clears the gate two-sided.** One-sided (defensible now that the sign is pinned)
clears only at literally zero haircut.

This is the C2 lesson stated in `CLAUDE.md` verbatim: *"the gate's verdict is only
as good as the declared SD, which is why SD must be independently defended rather
than inherited from a short in-sample read."* Here it is δ rather than SD, and the
inheritance would have to be not merely un-defended but anti-conservative.

## 5. What was actually established — this is not nothing

The measurement work stands and should not be re-run:

| Finding | Value | Status |
|---|---|---|
| Same-day IC contamination | artifact = −0.0813, sign-reversing | Confirmed, removed |
| Clean level IC (skip-a-day) | +0.0198, sd 0.2068 | Sound |
| Static-tilt hypothesis | rejected — E-4 level component insignificant (t −1.05) | Sound |
| Incremental daily signal | E-3 +0.0395, t 4.19 | Sound but 58% moneyness artifact |
| Moneyness-controlled signal | **+0.0167, t 2.06, sd 0.2502** | **The honest effect size** |

**There is probably a real effect here.** t = 2.06 on a moneyness-controlled,
contamination-free, 737-day TRAIN read is not nothing. **OSC fails on
demonstrability, not on absence of signal** — the same distinction
`INDEX_CONSTRUCT_DIAGNOSIS.md` §1 draws for every prior index construct.

## 6. The structural lesson — the escape route was narrower than it looked

`INDEX_CONSTRUCT_DIAGNOSIS.md` §1 argued that `rank_ic` over a genuine cross-section
escapes the index power wall because `√n` does the work. **It does — and it was still
not enough.**

The cross-section delivered n = 1,701 and √n = 41.2. But the effect size after
honest cleaning is δ/sd = 0.0167/0.2502 = **0.067**, and 0.067 × 41.2 = 2.75 < 2.80.
The wall was not escaped; it was approached from the other side and met at almost
exactly the same place.

Two specific reasons the cross-section under-delivered:

1. **`N_eff ≈ 1.9`.** The option surface has ~2 independent directions of movement,
   so 283 cells/day is nominal, not effective breadth (`OSC_SD_PROBE_REVIEW.md` §4).
2. **The moneyness control cost more than it saved.** Bucketing into deciles removed
   the artifact (58% of the raw IC) *and* raised `sd_IC` from 0.2068 to 0.2502 by
   shrinking the effective cross-section per bucket. Both movements hurt.

## 7. Why this is not being re-run again

One further estimator change is technically available: **residualize `richness` on
`m` and `m²` before ranking, instead of bucketing into deciles.** Bucketing discards
cross-sectional information; residualizing does not, and would plausibly restore
`sd_IC` toward 0.21 while keeping the artifact controlled — at sd = 0.2068 and
δ = 0.0167 power would be 0.9145.

**It is not authorized, and it should not be run.** Four corrective rounds have now
been taken on this burned window (contamination fix, regime diagnostic, D-4
re-spec, moneyness control). The first three were **defect corrections** and are
legitimate. A fifth change motivated by *"we need a lower sd to clear the gate"*
is results-driven, and the multiple-comparisons burden across five estimator
variants is real and unaccounted for. **By the time a variant clears, the α means
nothing.** That is the line, and it has been reached.

If OSC is ever revisited, it starts as a fresh pre-registration that pins the
estimator *before* seeing results and discloses all five variants tried here as
prior exposure.

## 8. Standing

- **OSC: ABANDON.** No declaration frozen; nothing to withdraw.
- **2016-02-11 → 2022-12-31 (1,701 formations): UNREAD and preserved.** The entire
  sequence — probe, three reviews, two corrective runs — ran on the already-burned
  2023–2025 window. **Cost to the confirmatory budget: zero.** This is the RFA gate
  doing exactly what it was built for, on a construct that looked Green twice.
- **Still open and independently valuable:** the BankNifty options ingest gap
  (`INDEX_CONSTRUCT_DIAGNOSIS.md` §5 — dropped by an ingest filter, not absent from
  source). Recovering it widens the index-option surface and is unaffected by this
  verdict.
