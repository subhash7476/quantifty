# JEV-NMS-1 — Forensic Post-Mortem

**POST-MORTEM / NON-CONFIRMATORY.** This document is descriptive analysis of immutable records
only:
- no Jev, API or network call;
- no stage re-run;
- no refit or selection;
- no protocol, configuration, template, draw, label, feature, cache or stage-artifact change;
- no new confirmatory test.

Every number is labelled **[O]** (observed directly in a committed record, or computed
mechanically from one) or **[I]** (inference or interpretation).

## 1. Executive finding
**[O] Jev read its inputs, but through a recent-return continuation mapping that the
development data does not support.**
- Jev's up-minus-down probability tilt has Spearman ρ = **0.80** with `ret_15_bp` and **0.86**
  with `ret_30_bp`. The realized up-minus-down outcome has ρ = **−0.04** with `ret_15_bp`.
- As a result, Jev predicts trending classes 52% of the time; they occur 32% of the time.
- Its class-ranking ability is near chance for the two trend classes: AUC 0.51 for
  trending_up and 0.52 for trending_down.
- **Its confidence does not track correctness.** Its most confident predictions (≥ 0.75) are
  86% trending_down and are correct only 24% of the time.

**[I] Under the §16 pool this left essentially nothing to add to B3.**
- b̂ is small and sign-unstable across folds.
- The out-of-fold ΔLL of −0.000499 nats is about the size one would expect from fitting one
  pure-noise parameter.

**No implementation defect was found.** Re-applying the stored fold parameters reproduces the
recorded out-of-fold ΔLL exactly at all three horizons.

## 2. Immutable JEV-NMS-1 result
- **Development result:** NULL under §24 rule 4.
  - h15 out-of-fold ΔLL: −0.000499 nats.
  - b̂: +0.0101.
  - n_req: not computable.
  - Invalid responses: 0 of 1,600.
- **Pre-development probes:**

  | Probe | Result |
  |---|---|
  | L1 | Passed |
  | L2 | PASS (28/90, p = 0.709) |
  | L3 | Baseline 46/50 = 0.92 (A3); L5 threshold 41/50 |

- **Status:** F₂ not set, P not run, 1,800 Jev calls in total.
- **Not reopened:** nothing in this document changes or reinterprets that result.

## 3. Evidence inventory
- **Inputs, all hash-verified:**

  | File | SHA-256 |
  |---|---|
  | `development_step6.json` | `3fc16a45…` |
  | `cache.jsonl` | `fd27d793…` |
  | `l3_step5.json` | `cb67b555…` |
  | `dfit_constants_step2.json` | `656ed4dd…` |
  | `b2_b3_step2.json` | `23e32d10…` |

  Also used: the three B3 pickles (frozen hashes) and `features_step2.json`, `draws_step2.json`
  and `eligibility_step1.json` (their accepted hashes). Store files are read with their step-1
  SHA-256 checks.
- **Reports:** the protocol, Amendment 2, the A3 ruling, the L1/L2/L3 reports, the Development
  report and the Development call audit.
- **New outputs:**
  - `scripts/jev_nms_1/postmortem.py`, which is read-only. It only *applies* the frozen B3 and
    *re-applies* the stored fold pool parameters; it fits nothing.
  - `data/jev_market_state/postmortem_diagnostics.json` (create-only), SHA-256
    `645637f036cc4e79edb80e6ab4ab06d79a84ba2eca3639733028746873934d43`.
  - `tests/jev_nms_1/test_postmortem.py`.
- **Reproducibility:** a second in-memory run gives an identical artifact.

## 4. Information content (h15, 1,000 development observations)

| Class | ρ(p_J, p_B3) [O] | AUC J [O] | AUC B3 [O] | AUC B3* [O] | Mean p_J when true / when false [O] |
|---|---|---|---|---|---|
| trending_up | −0.04 | 0.513 | 0.599 | 0.594 | 0.178 / 0.174 |
| trending_down | 0.39 | 0.520 | 0.580 | 0.572 | 0.292 / 0.276 |
| range_bound | 0.43 | 0.607 | 0.714 | 0.710 | 0.401 / 0.333 |
| disorderly | 0.17 | 0.546 | 0.778 | 0.772 | 0.201 / 0.171 |

- **How far Jev is from B3** [O]:
  - they pick the same top class on 44.1% of observations;
  - the mean total-variation distance between J and B3 is 0.378;
  - mean KL(J‖B3) is 0.495 nats.
- **How Jev responds to its inputs** [O]:

  | Relationship | Spearman ρ |
  |---|---|
  | J's up-minus-down tilt vs `ret_15_bp` | 0.80 |
  | J's up-minus-down tilt vs `ret_30_bp` | 0.86 |
  | J's total trend probability vs `er_30` | 0.61 |
  | J's disorderly probability vs `rv_30_bp` | 0.31 |
  | B3's up-minus-down tilt vs `ret_15_bp` | 0.12 |
  | Realized up-minus-down outcome vs `ret_15_bp` | −0.04 |

- **[I] Jev's output is very different from B3's, not redundant with it.** Nearly all of the
  difference is a strong, systematic response to recent direction and efficiency. That is a
  continuation reading of "trend", which the 15-minute forward labels do not bear out.
- **[I] What discrimination J does have is weaker than B3's and partly shared with it.** It is
  concentrated in range_bound (AUC 0.61, ρ = 0.43 with B3).
- **[I] Systematic, not noise.** The difference from B3 is systematic (ρ ≈ 0.8 with the
  inputs). It is not noise, but it is not *informative* about the labels.
- **[I] Does any incremental information exist?** None that the pool could detect (§6). No
  descriptive quantity points to a systematic incremental signal.

## 5. Jev against B0, B1, B2 and B3 (h15)
**Recorded log-losses and gaps** [O]:
- Jev's log-loss is 1.5349. B0–B3 score 1.1544, 1.1071, 1.0737 and 1.0665.
- Jev minus each baseline, in nats: 0.380, 0.428, 0.461 and 0.468. Jev is worse than all four.

**Per true class** [O]:

| True class | J log-loss | B3 log-loss | J recall |
|---|---|---|---|
| trending_up | **2.703** | 1.851 | 0.226 |
| trending_down | 1.911 | 1.907 | 0.323 |
| range_bound | **1.043** | 0.485 | 0.490 |
| disorderly | 1.821 | 1.740 | 0.119 |

**[I] Where the loss comes from:**
- **range_bound.** It is 57% of observations. J gives it a mean probability of 0.37, against a
  realized 0.57, so J pays about +0.56 nats per range_bound observation relative to B3.
- **trending_up.** J's probability for it is uninformative (AUC 0.51) and often low when it
  occurs, costing about +0.85 nats relative to B3.

## 6. Pool and b̂
**What the pool fits show** [O]:
- **Full-sample fit:** b̂ = +0.0101 and a = 0.816. B3* alone has a = 0.820.
- **In-sample gain from adding J:** 0.0408 nats in total negative log-likelihood over 1,000
  observations, or 4.1e-5 per observation.
- **Fold b̂:** +0.011, +0.028, −0.004, −0.005, +0.019. Three are positive and two negative.
- **Scale:** the centered ln p_J has standard deviation 1.26, so J's term moves the logits by
  about 0.013 (SD). B3's term moves them by about 0.75.

**[I] How to read this:**
- **The in-sample gain is smaller than chance would give.** The likelihood-ratio quantity
  2 × 0.041 = 0.08 is below the value of about 1 expected from adding one pure-noise parameter.
- **The out-of-fold loss has the expected size.** The expected out-of-sample cost of such a
  parameter is roughly 1/(2 × 800) ≈ 0.0006 nats per observation. The observed ΔLL is −0.0005.
- **Fold b̂ values** straddle zero.
- **Conclusion:** everything is consistent with J having negligible incremental weight under
  this formulation.
- **Not evidence:** b̂ is not predictive evidence of anything. Its positive sign on the full
  sample is not meaningful.

## 7. Calibration and confidence (h15)

**Calibration summary** [O]:
- J's ECE is 0.191, against 0.025 for B3* and 0.045 for B3.
- J's reliability bins, from the Development artifact:

  | Mean confidence | n | Accuracy |
  |---|---|---|
  | 0.37 | 65 | 0.31 |
  | 0.45 | 257 | 0.39 |
  | 0.54 | 284 | 0.38 |
  | 0.64 | 210 | 0.48 |
  | 0.74 | 136 | 0.32 |
  | 0.83 | 48 | 0.17 |

**Confidence against correctness** [O]:

| J confidence | n | J accuracy | Share predicted trending_down | B3* accuracy on the same observations |
|---|---|---|---|---|
| < 0.45 | 156 | 0.333 | 0.15 | 0.487 |
| 0.45–0.55 | 312 | 0.381 | 0.15 | 0.577 |
| 0.55–0.65 | 249 | 0.470 | 0.20 | 0.610 |
| 0.65–0.75 | 173 | 0.382 | 0.51 | 0.642 |
| ≥ 0.75 | 110 | **0.236** | **0.86** | 0.473 |

- **Rank correlation of confidence with correctness** [O]: −0.02 at h15, **−0.22** at h5 and
  **−0.18** at h30.
- **[I] Why J's AURC is poor** (0.659, against 0.273 for B3*): J is most confident exactly
  where it predicts continuation of a recent fall, and those predictions are mostly wrong. The
  AURC reflects that confidence inversion.
- **J's high-confidence observations are harder for B3\* too** [O]: B3* accuracy there is
  0.47. [I] These are large-move states, which are harder for every model, but J's error rate
  there is far higher.

**Rounding, clipping and renormalization** [O]:
- **Rounding:** all of J's probabilities are two-decimal (90 distinct values). Raw sums lie in
  [0.99, 1.00], and 1% of vectors do not sum to 1.
- **Renormalization:** it changes any log-probability by at most 0.010.
- **Clipping:** 15 raw zero probabilities were clipped. Only 2 of them were on the true class.
  Those 2 contribute 0.018 of J's 1.535 nats; without them J's log-loss is still 1.519.
- **[I] None of these mechanics materially explains the result.**

## 8. Class usage and base rates (h15) [O]

| | trending_up | trending_down | range_bound | disorderly |
|---|---|---|---|---|
| Realized base rate | 0.164 | 0.155 | 0.572 | 0.109 |
| J mean probability | 0.175 | **0.279** | **0.372** | 0.175 |
| J arg-max share | 0.216 | **0.304** | 0.432 | 0.048 |
| B3 mean probability | 0.151 | 0.146 | 0.585 | 0.118 |
| B3 arg-max share | 0.006 | 0.018 | **0.871** | 0.105 |
| B3* mean probability | 0.164 | 0.156 | 0.572 | 0.108 |
| B3* arg-max share | 0.010 | 0.021 | 0.906 | 0.063 |

**[I] Reading the table:**
- J under-uses range_bound, which is also the protocol's residual class.
- J over-uses trending_down in particular, a down-side asymmetry. Its mean probability for
  trending_down is 0.28 against 0.18 for trending_up, while the base rates are nearly equal.
- The same pattern holds at h5 and h30 (J's mean range_bound probability is 0.35 and 0.31).
- B3 and B3* track the base rates closely. Their arg-max concentrates on range_bound, as a
  calibrated model with weak signal should.
- The template deliberately gives no base rates or thresholds (§11A items 2–3). So J's class
  prior is its own.

## 9. Slots and horizons
**Per-slot ΔLL (h15)** [O]:

| 10:00 | 10:30 | 11:00 | 11:30 | 12:00 | 12:30 | 13:00 | 13:30 | 14:00 | 14:30 |
|---|---|---|---|---|---|---|---|---|---|
| −0.0023 | +0.0012 | −0.0048 | −0.0007 | +0.0008 | −0.0001 | +0.0005 | +0.0016 | −0.0011 | −0.0002 |

- 6 of 10 slots are negative, and every value is within ±0.005.
- 42 of 100 sessions are positive.
- [I] The result is broad, a near-zero effect everywhere. It is not driven by a few slots. No
  favourable subset is claimed.

**By horizon** [O]:

| h | Out-of-fold ΔLL | Full b̂ | Fold b̂ | J − B3 log-loss | J AUC range across classes |
|---|---|---|---|---|---|
| 5 | −0.00617 | +0.041 | all 5 ≥ 0 (0.004–0.146) | +0.500 | 0.49–0.61 |
| 15 | −0.00050 | +0.010 | 3 positive, 2 negative | +0.468 | 0.51–0.61 |
| 30 | −0.00056 | −0.011 | all 5 < 0 | +0.625 | 0.43–0.59 |

- [I] Directionally consistent: ΔLL is negative at every horizon. This is not horizon-specific.
- At h30, J's AUC is below 0.5 for disorderly (0.43) and trending_down (0.45); its ranking is
  mildly anti-aligned there.
- No cross-horizon test is performed.

## 10. L3 repeatability relevance [O, descriptive]
- **L3 figures:** replicate argmax agreement 46/50 (A3 baseline, unchanged); maximum
  |Δp| 0.14; median 0.04.
- **Replicate differences on the 50 L3 states,** scored against their frozen h15 labels:
  - mean |replicate log-loss difference| is 0.102 nats per state (maximum 0.405);
  - the mean signed difference is −0.006 (standard error 0.019).
- [I] That per-state noise is real, but it is roughly symmetric and averages out. It is two
  orders of magnitude smaller than J's 0.47-nat deficit to B3. Averaging repeated calls would
  reduce noise; it cannot create discrimination that single calls lack (AUC ≈ 0.51–0.61).
  Variability is not a plausible cause of the NULL.

## 11. Pipeline integrity audit [O]

| Check | Result |
|---|---|
| Feature construction | L1 (6,850 states), the pre-development request audit (1,600) and this post-mortem all find **0 mismatches**. Each cached request's state equals the sealed `features_step2.json` state. |
| Label construction and alignment | The label path reproduced the stored D-fit labels with 0 mismatches (pre-call check). L1 verified input/label disjointness on 13,260 label checks. D-eval labels use the same code with frozen constants. |
| Class mapping | Raw response probabilities are keyed by class name and equal the stored parse for all 1,600. B2/B3 columns are mapped by class name, and the frozen models reproduce their recorded D-fit log-loss exactly. |
| Clipping | 1e-4 floor, then renormalize, applied to every model (tests `test_clip_floors_and_renormalizes`). |
| Out-of-fold construction | 5 × 200 test observations at h15. Each fold's parameters were fit on the other 800 (`test_crossfit_is_out_of_fold`). |
| Pool calculation | Re-applying the stored fold parameters to the cached J, frozen B3 and labels reproduces the recorded out-of-fold ΔLL **exactly** (bit-identical) at h5, h15 and h30. The gradient is verified against finite differences. |
| Session weighting | Every session has 10 valid observations, so session-weighted equals observation-weighted (`test_dll_is_session_weighted_mean_of_session_means`). |
| Cache and response association | Keys are the SHA-256 of the stored request bytes. The analysis indexes records by the pre-registered key and asserts state and template. [I] J's 0.80–0.86 correlation with its own state's returns would be impossible if responses were attached to the wrong states. |

**[I] No defect was found. There is no ground to classify JEV-NMS-1 as potentially INVALID on
implementation grounds.**

## 12. TypeSafe call-provenance status
- **What the repository shows** [O]: `JEV_NMS_1_DEVELOPMENT_CALL_AUDIT.md` verified all 12
  items.
  - 1,600 distinct pre-registered keys.
  - 1,600 HTTP 200 responses, with 1,600 distinct server request IDs whose embedded timestamps
    fall within 0.16 s of the local send times.
  - Server `Date` headers consistent with local timing.
  - Content-Length equal to the body length.
  - No fabrication path in the code.
- **What cannot be checked locally:** server-side accounting. The usage-dashboard discrepancy
  remains **unexplained locally**. Call provenance is **internally verified but not
  independently verifiable** without TypeSafe's logs; the stored request IDs allow that
  reconciliation.
- [I] The Development result does not depend on the dashboard.

## 13. Explanatory hypotheses
Ranked by evidentiary support.

**A. Jev adds little or no incremental information for this formulation.**
- **Evidence for:** b̂ ≈ 0.01 and sign-unstable across folds; the in-sample gain is smaller
  than a noise parameter would give; ΔLL is negative at all three horizons; J's AUCs are
  0.51–0.61, against B3's 0.58–0.78.
- **Evidence against:** none observed.
- **Confidence: HIGH.**
- **To distinguish in future:** only a larger or different sample could narrow the effect-size
  bound. This is the recorded outcome, not an explanation.

**F. Jev applies a continuation prior that the forward labels contradict.** This is the
mechanism behind A and C.
- **Evidence for:** J's tilt has ρ = 0.80–0.86 with recent returns, while realized direction
  has ρ ≈ −0.04; J over-uses trending classes, 52% against 32%; J's most confident predictions
  are continuation calls, mostly down, at 24% accuracy.
- **Evidence against:** J's range_bound ranking has some signal (AUC 0.61).
- **Confidence: HIGH as a description of the observed input→output mapping. MEDIUM as the
  cause.** Whether a different framing would change the mapping is untested.
- **To distinguish:** measure J's mapping on controlled inputs, and compare framings, under a
  separate pre-registration.

**C. Jev's probabilities are poorly calibrated for this task.**
- **Evidence for:** ECE 0.19; confidence does not track correctness (and is inverted at h5 and
  h30); class-prior mismatch.
- **Evidence against:** the pool's a and c_k recalibrate B3, not J, so J's miscalibration is
  not what bounds the pool. With AUC ≈ 0.5 for trends, recalibration alone could not create
  much signal.
- **Confidence: HIGH that J is miscalibrated; LOW-MEDIUM that this explains the NULL.**
- **To distinguish:** a pre-registered comparison of J's discrimination (AUC) against its
  calibration on fresh data.

**B. Jev has the information, but the representation prevents extracting it.**
- **Evidence for:** none direct.
- **Evidence against:** J demonstrably parses and responds to the fields (ρ up to 0.86), so the
  JSON representation is read.
- **Confidence: LOW.** Unfalsifiable with these records.
- **To distinguish:** a pre-registered comparison of representations on identical states.

**D. Jev is too variable to be useful.**
- **Evidence for:** per-state replicate log-loss noise of 0.10 nats; 4/50 arg-max flips.
- **Evidence against:** the noise is symmetric (mean −0.006, standard error 0.019) and far
  smaller than the 0.47-nat deficit; canary agreement was 20/20.
- **Confidence: LOW.**
- **To distinguish:** replicate-averaged scoring, pre-registered.

**E. A pipeline or implementation problem affected the result.**
- **Evidence for:** none.
- **Evidence against:** exact reproduction of the out-of-fold ΔLL; all audits and tests pass;
  0 feature mismatches; name-keyed mapping; J–input correlations prove correct association.
- **Confidence: LOW** that it occurred.

## 14. What JEV-NMS-1 establishes
- Under the sealed formulation, on the D-eval development sample, adding Jev's probabilities to
  a recalibrated B3 did **not** lower out-of-fold log-loss (ΔLL −0.0005 at h15; negative at h5
  and h30). §24 rule 4 closed the experiment as NULL before any prospective data.
- Jev alone is materially worse than climatology and every deterministic baseline on these
  labels.
- The pipeline, fences, caching and call provenance are internally sound, and the result is
  exactly reproducible from the committed records.
- L2 found no evidence of year memorization at the preregistered threshold.

## 15. What it does NOT establish
- That Jev lacks market-judgment capability in general, with other inputs, other tasks or
  other framings (§2, disclosure 1).
- A confirmatory test of H0. There was no P, and development evidence is not confirmatory.
- Anything about economic value.
- That the continuation mapping is an inherent model property rather than a response to this
  template. That is an inference (§13 F), not a finding.
- Anything from the post-mortem statistics themselves, which are descriptive and not tests.

## 16. Future research directions
At most three. Each is a **new hypothesis** needing its own pre-registration; **none is
evidence from JEV-NMS-1.**

1. **Input→output characterization.**
   - *Question:* is Jev's class tilt a stable, near-deterministic function of recent return and
     efficiency (a fixed continuation rule)?
   - *What would change:* a measurement study on controlled or synthetic feature vectors, with
     no predictive claim. It would decide whether any fixed-feature framing can add beyond a
     same-input model.
2. **Framing sensitivity.**
   - *Question:* does giving the numeric label definition or base rates, which §11A deliberately
     excluded, change Jev's discrimination (AUC), not merely its calibration?
   - *What would change:* the template, which is a new protocol. Scoring would have to separate
     discrimination from calibration.
3. **Information Jev has that B3 lacks.**
   - *Question:* can Jev add value when the input includes information a same-input
     deterministic model cannot use, such as textual context?
   - *What would change:* the information channel and the comparator design, which amounts to a
     different experiment entirely.

## 17. Statement
This post-mortem made **no Jev, API or network call**. It performed **no refit, re-selection
or stage re-run**. It made **no change to the protocol, configuration, templates, draws, labels,
features, cache, ledger or any existing stage artifact**. It ran **no new confirmatory test**.
All added calculations are POST-MORTEM / NON-CONFIRMATORY.
