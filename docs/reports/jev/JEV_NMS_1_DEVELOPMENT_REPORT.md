# JEV-NMS-1 — Development Report

**Development result: NULL under §24 rule 4.**
- The out-of-fold development ΔLL at h = 15 is **−0.000499 nats** (100 sessions, 1,000 valid
  observations), and the rule is "out-of-fold development ΔLL ≤ 0 → NULL".
- Consequences under §24/§27:
  - F₂ is **not** established;
  - n_req and N_P are not computed, because δ = 0.5 × ΔLL is not positive;
  - P is not run.
- **This is development evidence only.** It is neither confirmatory nor a prospective result
  (§13).
- **No P, L5 or other unauthorized call was made.**

| §24 development rule | Value | Fires? |
|---|---|---|
| Rule 4: out-of-fold dev ΔLL ≤ 0 | **−0.000499** | **Yes → NULL** |
| Rule 5: b̂ ≤ 0 (full permitted sample) | b̂ = **+0.0101** | No |
| Rule 6: n_req > 250 | not computable (δ ≤ 0) | n/a |
| §26: invalid responses > 2% | 0 / 1,600 | No |

## 1. Sample and draw provenance
- **Draw:** D1 from `draws_step2.json` (`e4c1f3c9…733de8`, verified). `random.Random(42).sample`
  of the 243 otherwise-eligible D-eval sessions gives 100 sessions (population SHA-256
  `population_hash` matches the manifest).
- **R-1 discharged:** otherwise-eligible = eligible = 243 in D-eval. Item 7 excludes nothing,
  and no drawn session is affected.
- **D2:** the first 30 of D1 in seed order.
- **States:**
  - primary: 100 sessions × 10 §5 slots = 1,000 (h15 template);
  - secondary: 30 × 10 × {h5, h30} = 600.
- **Checks before any call:**
  - The F₁/A2 seal chain passed (`load_seal()`), and so did A3 (`load_a3()`, addendum
    `d4dfe861…`).
  - Step-1/2, L1, L2 and L3 artifacts were verified by SHA-256. L1 had passed, L2 was PASS,
    and L3 was complete.
  - All 1,600 states passed the L1 fence for the development stage (eligible D-eval only).
  - All 1,600 passed the request audit: features rebuilt from the SHA-256-checked store equal
    `features_step2.json`, and the templates match their sealed hashes.
  - The 1,600 keys are distinct and none collided with the 200 cached S0/L2/L3 keys.
- **Cross-fitting blocks (h15)**, the 100 sessions date-sorted into 5 × 20:

  | Block | First session | Last session |
  |---|---|---|
  | 1 | 2025-01-02 | 2025-02-28 |
  | 2 | 2025-03-04 | 2025-05-16 |
  | 3 | 2025-05-19 | 2025-08-01 |
  | 4 | 2025-08-04 | 2025-10-08 |
  | 5 | 2025-10-09 | 2025-12-29 |

- **Secondary horizons (declared P3):** the 30 D2 sessions date-sorted into 5 blocks of 6.
- The full lists are in `development_step6.json`.

## 2. Jev requests and responses

| Item | Value |
|---|---|
| Run ID | `DEV-20260918T134137Z` |
| Scheduled / sent / valid | 1,600 / 1,600 / **1,600** (h15 1,000; h5 300; h30 300) |
| Invalid / paired-excluded | **0** |
| Retries | **0** (all HTTP 200 on the first attempt) |
| Cache hits | 0. Every key was new and sent once. `development_started` listed all 1,600 keys before the first send. |
| Model echoed | `jev-1.13.0` in all 1,600 |
| Request IDs | 1,600 captured, all distinct |
| Usage | 786–801 input and 55–57 output tokens per request |
| Sent / received (UTC) | 2026-09-18T13:41:37.893Z → 13:51:48.473Z |
| Latency | min 316.0, median 367.7, max 1,319.4 ms |
| Upstream time | min 43, median 93, max 542 ms |
| Keep-alive | One connection, reused for 1,599 requests |
| Timing validity | Not applicable (§11: historical calls). Every record carries `state_as_of`, sent and received times. |

**Two response-level facts:**
- **Probability sums.** Jev's returned vectors do not always sum to exactly 1. The maximum
  |sum − 1| is 0.010, consistent with two-decimal rounding. `validate_response` checks keys,
  range and choice, not the sum, so all 1,600 are valid. Every vector is clipped at 1e-4 and
  renormalized before use (§15, Q5).
- **`choice` versus arg-max.** In 13 of 1,600 responses the `choice` field is not the arg-max
  of the probabilities. The analysis uses the probability vectors only, and accuracy uses the
  A3-1 arg-max; `choice` is not used.

## 3. B2/B3 — frozen selection and model hashes
- **No selection or fit was re-run.** B2's C and B3's hyperparameters were selected per
  horizon by the frozen out-of-fold rule on D-fit at §28 step 2 (commit `0ebcea4`). §26 and
  §28 item 3 forbid any D-fit fitting or hyperparameter selection after the first Jev call.
  Development **applies** the frozen models.

| h | B2 C | B3 grid index / parameters |
|---|---|---|
| 5 | 0.01 | 0: lr 0.03, max_iter 100, leaves 7, min_leaf 50, l2 0.0 |
| 15 | 0.1 | 0: same as h5 |
| 30 | 0.1 | 3: lr 0.03, max_iter 100, leaves 7, min_leaf 200, l2 1.0 |

| Frozen input | SHA-256 |
|---|---|
| `b2_b3_step2.json` (B2 coefficients, standardization, selection record) | `23e32d105f9953e162d0588198829e02448213cc95145a35020aed571f504959` |
| `b3_h5_step2.pkl` | `1f0e9675725c30e4323d8bf9779c43a51fceb0c3d38eece7a079d852c694908e` |
| `b3_h15_step2.pkl` | `b50a42de6862fda0afabe6f83a5a436b4cfa4f5e2bdaaa14c9c91a1a40fccd46` |
| `b3_h30_step2.pkl` | `434ecbb0a670fb8f0f4d3b238de24c1862bb103272372ba0f395d1a39022a675` |
| `dfit_constants_step2.json` (§8 thresholds, §9 scales, B0/B1) | `656ed4ddf3ee19d264c2dc8183844f329881bf14ca2e77c7dfb87e6d8bafe88d` |

**Fidelity checks, run before any call:**
- The frozen B2 (reconstructed from its coefficients) and B3 (unpickled) reproduce their
  recorded D-fit in-sample log-loss exactly, with difference 0.0 at every horizon.
- The label path reproduces the stored D-fit labels, with 0 mismatches.
- D-eval labels apply the frozen constants through the same `dfit.window_stats` /
  `dfit.classify` code. Nothing was re-estimated (§9).

## 4. B3, B3* and B3+J (h = 15, development, out of fold)

**Pool (§16):**
- **Form:** logit_k = a·ln p_B3,k + b·ln p_J,k + c_k, with Σc_k = 0. B3* is the same with
  b = 0.
- **Estimation:** maximum likelihood with BFGS (declared P1).
- **Convergence:** all h15 fold fits and both full-sample fits converged, with max
  |gradient| ≤ 7e-10.

| Fit | a | b | c (trending_up, trending_down, range_bound, disorderly) |
|---|---|---|---|
| B3+J, full permitted sample (1,000) | 0.8158 | **+0.0101** | 0.0191, −0.0216, 0.1496, −0.1471 |
| B3*, full permitted sample | 0.8196 | 0 | 0.0112, −0.0196, 0.1535, −0.1451 |

| Fold | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| B3+J b | 0.0111 | 0.0283 | −0.0040 | −0.0048 | 0.0190 |
| B3+J a | 0.7874 | 0.7518 | 0.9066 | 0.8137 | 0.8163 |
| B3* a | 0.7911 | 0.7619 | 0.9049 | 0.8119 | 0.8235 |

The full-sample B3+J fit is the §16 "full permitted D-eval" pool. It is reported here only for
the rule-5 sign. It is **not frozen**, because F₂ is not established.

**Out-of-fold scores**, 1,000 observations. B0–B3 are the frozen D-fit models; J is Jev
clipped and renormalized.

| Model | Log-loss (nats) | Brier | Accuracy | ECE (10 bins) |
|---|---|---|---|---|
| B0 | 1.1544 | 0.6120 | 0.5720 | 0.0231 |
| B1 | 1.1071 | 0.5858 | 0.5710 | 0.0268 |
| B2 | 1.0737 | 0.5695 | 0.5730 | 0.0414 |
| B3 | 1.0665 | 0.5664 | 0.5690 | 0.0452 |
| **B3\*** | **1.0679** | 0.5667 | 0.5710 | 0.0246 |
| **B3+J** | **1.0684** | 0.5667 | 0.5690 | 0.0264 |
| J (Jev alone) | 1.5349 | 0.7882 | 0.3800 | 0.1912 |

**Label base rates (h15, dev):**

| Class | Share |
|---|---|
| range_bound | 0.572 |
| trending_up | 0.164 |
| trending_down | 0.155 |
| disorderly | 0.109 |

**Confusion matrices** (true class → predicted class, A3-1 arg-max):

| Model | True class | → trending_up | → trending_down | → range_bound | → disorderly |
|---|---|---|---|---|---|
| J | trending_up | 37 | 50 | 65 | 12 |
| J | trending_down | 36 | 50 | 61 | 8 |
| J | range_bound | 118 | 159 | 280 | 15 |
| J | disorderly | 25 | 45 | 26 | 13 |
| B3* | trending_up | 0 | 5 | 144 | 15 |
| B3* | trending_down | 1 | 3 | 140 | 11 |
| B3* | range_bound | 5 | 6 | 546 | 15 |
| B3* | disorderly | 4 | 7 | 76 | 22 |

The B3 and B3+J matrices, and every model's reliability bins, are in `development_step6.json`.

## 5. Primary ΔLL and preregistered diagnostics (h = 15)
- **ΔLL (out of fold)** = session-weighted mean of session means of (ℓ_B3* − ℓ_B3+J) =
  **−0.000499 nats**. Positive would favour J.
- **Session-level spread:** SD of the 100 per-session means is 0.00498 (ddof 1); 42 of 100
  sessions are positive.

**Per-slot ΔLL:**

| 10:00 | 10:30 | 11:00 | 11:30 | 12:00 | 12:30 | 13:00 | 13:30 | 14:00 | 14:30 |
|---|---|---|---|---|---|---|---|---|---|
| −0.0023 | +0.0012 | −0.0048 | −0.0007 | +0.0008 | −0.0001 | +0.0005 | +0.0016 | −0.0011 | −0.0002 |

**J against each deterministic model:** mean ℓ_model − ℓ_J (positive would favour J):

| B0 | B1 | B2 | B3 |
|---|---|---|---|
| −0.3805 | −0.4278 | −0.4612 | −0.4684 |

Jev alone is worse than every deterministic baseline, including climatology.

**Not applicable in development:**
- "primary without seam-flagged observations" (seam flags exist only on P);
- timing compliance (P only).

The L3/canary statistics are in the L3 report and A3: baseline 46/50, L5 threshold 41/50.

**Deterministic models on H-exposed** (§18). This set is **EXPOSED / NON-CONFIRMATORY**:
172 eligible sessions × 10 = 1,720 states, 2026-01-01 → 2026-09-17, B0–B3 only.

| h | Model | Log-loss | Brier | Accuracy |
|---|---|---|---|---|
| 15 | B0 | 1.2736 | 0.6855 | 0.4930 |
| 15 | B1 | 1.1848 | 0.6302 | 0.5105 |
| 15 | B2 | 1.1201 | 0.5960 | 0.5285 |
| 15 | B3 | 1.1025 | 0.5851 | 0.5500 |
| 5 | B3 | 1.1209 | 0.5931 | 0.5477 |
| 30 | B3 | 1.0782 | 0.5731 | 0.5610 |

(All horizons and models are in the artifact.)

## 6. Secondary horizons (30 D2 sessions, 300 observations each; cannot rescue the primary)

| h | Out-of-fold ΔLL (blocks of 6, declared) | Alternative (h15 blocks) | Full-sample b̂ | B3* log-loss | B3+J log-loss | J log-loss | B3 log-loss |
|---|---|---|---|---|---|---|---|
| 5 | **−0.00617** | −0.00535 | +0.0409 | 1.0355 | 1.0416 | 1.4947 | 0.9946 |
| 30 | **−0.00056** | −0.00026 | −0.0106 | 1.0882 | 1.0887 | 1.6973 | 1.0721 |

- **Block readings:** both give negative ΔLL at both horizons, so no sign disagreement arises.
  The alternative's fold sizes are 80/60/30/80/50.
- **J against the deterministic models:** J is worse than every one at both horizons:

  | h | B0 | B1 | B2 | B3 |
  |---|---|---|---|---|
  | 5 | −0.42 | −0.43 | −0.50 | −0.50 |
  | 30 | −0.55 | −0.58 | −0.64 | −0.63 |

- **Disclosure:** one h5 B3+J fold fit (fold 5) ended with "precision loss" at max
  |gradient| 2.0e-9. That is optimal to numerical precision on the mean scale. All other
  secondary fits converged.

## 7. Abstention and coverage (§21, h = 15, out of fold)
Confidence is the maximum clipped probability. Cuts use `numpy.quantile(method="linear")`.
Ties at the cut are retained (declared P5), and the realized counts are shown.

**Retained by J's confidence:**

| Coverage | Cut | n | J log-loss | J accuracy | B3* log-loss | B3* accuracy |
|---|---|---|---|---|---|---|
| 100% | 0.31 | 1,000 | 1.5349 | 0.380 | 1.0679 | 0.571 |
| 80% | 0.46 | 813 | 1.5442 | 0.386 | 1.0420 | 0.589 |
| 60% | 0.52 | 616 | 1.5670 | 0.386 | 1.0437 | 0.589 |
| 40% | 0.59 | 402 | 1.6827 | 0.381 | 1.0684 | 0.572 |
| 20% | 0.690 | 200 | 1.9807 | 0.290 | 1.1185 | 0.530 |

**Retained by B3\*'s own confidence:**

| Coverage | n | B3* log-loss | B3* accuracy | J log-loss | J accuracy |
|---|---|---|---|---|---|
| 80% | 800 | 0.9909 | 0.644 | 1.4597 | 0.408 |
| 60% | 600 | 0.8866 | 0.703 | 1.3672 | 0.443 |
| 40% | 400 | 0.8252 | 0.730 | 1.3027 | 0.473 |
| 20% | 200 | 0.6592 | 0.800 | 1.1400 | 0.535 |

**AURC** (tie-group invariant):

| Model | 0-1 loss | Log-loss |
|---|---|---|
| J | 0.6590 | 1.7611 |
| B3* | 0.2733 | 0.8151 |

**Is B3\* loss higher where J is least confident?** The Spearman correlation between J's
confidence and B3*'s log-loss is ρ = −0.026, one-sided p = 0.205.

Descriptively, J's confidence does not rank its own accuracy: J is least accurate in its most
confident 20%.

## 8. Descriptive inference on development
The §19 and §20 machinery is defined for P. It is shown here on development only as
declared (P6): descriptive, non-confirmatory, never a gate.

| Statistic | Value |
|---|---|
| Moving-block bootstrap (block 5, 10,000 iterations, seed 42): one-sided 95% lower bound of ΔLL | −0.00172 |
| Newey–West t (lag 5) | −0.736 |
| AC₁ of session ΔLL | 0.256 |
| Conditional randomization (1,000 iterations; strata slot × B3* top class × B3* tercile; 53 strata) | p = 0.842 |
| N1, within-slot session permutation (1,000 iterations) | p = 0.732 |
| N2, 5k-session cyclic shifts (k = 1..19) | 14 of 19 shifts ≥ observed |

- **Conditional randomization:** the tercile cuts (0.5422, 0.6715) are reported and **not
  frozen**.
- **N2 shifts:** ΔLL ranges from −0.00108 to +0.00062 across the 19 shifts.

## 9. Hashes
All data paths are relative to `data/jev_market_state/`.

| Artifact | SHA-256 |
|---|---|
| `development_step6.json` (full analysis record) | `3fc16a452da9630dfeac95dd9616df21e56a32a5cd6b0963db01b17b3bdd669d` |
| `cache.jsonl` before development (200 records) | `23b0bcdf1c7ffddd6350baab0770d3537948927b56045facaaaf0c23ee82e143` |
| `cache.jsonl` after development (1,800 records) | `fd27d793be510a1998d80b4d9a556e67fd0256d134a1e7d84cec3fd6f6a839c9` |
| `ledger.jsonl` before development (through `a3_ruling`) | `3c7d73f7ceb9aaec2dbe49a19629f33d77a77149f860c40efad0162975b411a0` |
| `ledger.jsonl` through `development_completed` | `cad2f30fbc11142284d0f0760ac829702637d74c2e9ebcdb2a4efc4783d17a16` |

**Request hashes:**
- Each cache record's `key` is the SHA-256 of its exact canonical request bytes, which are
  stored alongside it.
- All 1,600 keys, in send order, are in the `development_started` ledger event, written before
  the first send.
- The first key is `3ccd8a3ff0e34679027fd11d56dca2c24196d357e83df479ff431b4d4281a15b`, for
  2025-09-03 10:00, h15.

**Ledger events (append-only):**
- `development_started`;
- `development_calls_completed` (1,600 records, 1,600 valid, cache hash);
- `development_completed` (artifact hash, result NULL, gates, ΔLL, b̂);
- `development_report` (this report's hash; the final ledger hash is reported with the
  commit).

## 10. Model, environment and seal verification
- **Model:** `jev-1.13.0` in all 1,600 requests and responses.
- **Transport:** the frozen historical policy (stdlib `http.client`, 20 s, transport-only
  retries, none used).
- **Environment:** Python 3.13.5, numpy 2.4.4, pandas 2.3.3, scikit-learn 1.8.0, scipy
  1.17.0, duckdb 1.4.3, OpenSSL 3.0.16, with `OMP_NUM_THREADS=1`. All match the F₁ pins.
- **Seals:** F₁/A2 (`load_seal`) and A3 (`load_a3`) verified. The protocol, configuration,
  addenda, templates and draws are unchanged.
- **API key:** read at send time only. It is absent from worktree files and from the committed
  tree.

## 11. Tests and git
**Tests:** `tests/jev_nms_1/test_dev_analysis.py` has 16 tests. They cover:
- pool gradient against finite differences, and convergence;
- sign recovery of b with informative and uninformative J;
- B3* having no J term;
- contiguous date-sorted blocks;
- out-of-fold cross-fitting;
- session weighting;
- the A3-1 tie rule;
- clip and renormalize;
- AURC tie invariance;
- ties retained at coverage cuts;
- ECE and confusion;
- Newey–West and AC₁;
- bootstrap determinism;
- the n_req variants and rule 6;
- the declared order of the 1,600 planned states.

**Full relevant suite:** 256 passed, 1 skipped (the CSMP calendar store is absent from this
worktree), 0 failed, `-W error`.

**Commits on `research/jev-nifty-market-state`:**
- `4673e09`: development runner and analysis, with the implementation choices P1–P7 declared
  in the module docstring. Committed **before** any development call.
- The next commit contains the cache, ledger, `development_step6.json` and this report.

**Implementation choices declared before any call (P1–P7):**

| # | Choice |
|---|---|
| P1 | Optimizer |
| P2 | n_req variants and their flag |
| P3 | Secondary-horizon blocks |
| P4 | ECE |
| P5 | Coverage ties and AURC |
| P6 | Descriptive development inference |
| P7 | H-exposed scope |

None of them affects the rule-4 outcome. The ΔLL uses only the §16 form, the §16 blocks and
the Q5 clipping.

## 12. Stages not performed
**P and L5 were NOT performed.** No live or prospective call, no canary replay, no F₂, no
freezing of stratum cuts or N_P, and no pool freeze.

Jev calls under JEV-NMS-1:

| Stage | Calls |
|---|---|
| S0 | 10 |
| L2 | 90 |
| L3 | 100 |
| Development | 1,600 |
| **Total** | **1,800** |

The total equals the §23 initial budget exactly.

## 13. Development evidence versus prospective confirmation
- Everything in this report is **development evidence** on D-eval (2025). The same year is
  within Jev's possible pretraining exposure (§2, disclosure 3). §27 states that nothing from
  D-fit, D-eval, H-exposed or the buffer can produce POSITIVE; only a valid P run can.
- A development NULL is the protocol's §24 rule 4 outcome. It is **not** a confirmatory test
  of H0, and it does **not** by itself establish that Jev carries no information.
- Its preregistered consequence is that F₂ is not established and P is not run. Any
  different course would be an operator decision outside the sealed protocol.
