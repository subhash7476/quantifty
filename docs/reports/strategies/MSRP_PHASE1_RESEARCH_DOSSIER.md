# MSRP Phase 1 — Research Dossier (Pre-Registration)

**Hypothesis:** Forward Volatility Regime — `expected_next_day_realized_vol`

**Document type:** Research baseline / pre-registration (Phase 1 of the Market
State Research Program). This document *pre-registers*; it does not report results.

**Status:** **FROZEN — immutable Phase-1 baseline (2026-07-06).** Passed Phase 2
independent review with all required revisions applied
(`docs/reports/MSRP_PHASE2_INDEPENDENT_REVIEW.md`). **Do not modify.** Any change to
the model, label, features, metric, or decision rule requires a **new
pre-registration for a new research increment**, not an edit to this document.

**Date:** 2026-07-06

**Revision provenance:** revised once, before freeze, to resolve Phase-2 findings
M1 (secondary raw-VIX arm), M2 (moving-block bootstrap), M3 (base-rate + power),
Mo1 ("causal" softened), Mo2 (calibrated uncertainty in-scope), Mo3 / Mi1 / Mi2
(notes). Frozen thereafter.

**Predecessor:** `docs/reports/MSRP_PHASE0_CHARTER.md` — Phase 0 CLOSED; all three §8
decisions locked (D1 minimal-but-conformant validation; D2 this hypothesis; D3 the
pre-registered metric restated formally in §3 below).

**Prior art (cited, not re-derived):** `docs/reports/DRA_TECHNICAL_DOSSIER.md` — the
pre-SALVAGE daily regime system. Its documented causal daily feature set
(`realized_vol_10d`, `vix_level`, `vix_pctl_90d`, `vix_roc_5d`,
`banknifty_nifty_ratio`, `nifty_20dma_slope`) and its central lesson ("the
classifier worked; the strategy did not") inform this design.

---

## 1. Pre-Registration Statement

This dossier is written and committed **before** the model is fitted and **before**
the held-out window is scored. It exists to make the research falsifiable and
resistant to hindsight bias: the model form, the label, the features, the metric,
and the decision rule are all fixed here, in advance.

- **Development window (fitting + all model/feature/threshold selection):**
  `2023-01-02 → 2025-12-31`.
- **Held-out window (evaluation only — SEALED):** `2026-01-01 → 2026-07-03`. No
  feature, coefficient, lag structure, threshold, block length, or hyperparameter
  may be chosen, tuned, or inspected against this window. It is touched exactly
  once, at Phase 6, by the A2 harness, to produce the single pre-registered
  comparison.
- **Data snapshot:** the candle store as of `2026-07-03` (1m Nifty 50 from
  2023-01-02; 1d India VIX / Nifty 50 / Bank Nifty from 2023-01-02).

### 1.1 Reproducibility substrate (MSI-006 Reproducibility domain — §5.3 precondition)

To be **pinned at A2 build** and cited in the immutable validation record. Recorded
here as the binding fields, not yet filled:

| Field | Value |
|---|---|
| Python version | *(pin at build)* |
| numpy / pandas / statsmodels / scikit-learn versions | *(pin at build)* |
| Moving-block-bootstrap block length `L` | *(pin at build — chosen from **dev**-window RV autocorrelation, e.g. 10 trading days; never from held-out)* |
| Bootstrap replicate count `B` | *(pin at build — e.g. 10,000)* |
| Bootstrap RNG seed | *(pin at build — single integer, fixed)* |
| Data-snapshot hash | *(pin at build — SHA-256 over the exact candle files used)* |
| Code commit hash | *(pin at build)* |

---

## 2. Objectives

### 2.1 Scientific Claim (a proposition about the world)

> **Next-day realized-volatility regime for the Nifty 50 is predictable from the
> heterogeneous autoregressive dynamics of realized volatility together with the
> India VIX level — to a degree that exceeds what the VIX level alone provides.**

This claim is true or false independently of any code. It is adjudicated by the
pre-registered metric of §3 on the sealed held-out window. **The phrase "VIX alone"
is made testable by the secondary raw-VIX reference arm (§3.2):** an Approved verdict
against the fixture gate substantiates this claim only insofar as the candidate also
out-discriminates raw continuous `VIX_t`. The claim can fail even if the engineering
deliverable (§2.2) is built perfectly.

### 2.2 Engineering Deliverable (an artifact + a validation record)

1. A `PublishedArtifact v2` (MSI-007 shape) whose frozen HAR-RV+VIX coefficients
   emit the named estimate `expected_next_day_realized_vol` with quantified
   `uncertainty`, conforming to the MM13 §4 consumer contract.
2. The minimal MSI-006 **A2 harness** (path (ii), D1) that produces one immutable
   validation record covering all seven mandatory domains, and a resolvable
   `validation_id`.

The deliverable is "built" regardless of the scientific outcome. The artifact only
reaches an **Approved** lifecycle verdict if the Scientific Claim holds under §3.
**Building the artifact is not evidence the claim is true.** Keeping these two
separate is the discipline this section exists to enforce.

---

## 3. Hypotheses and Decision Rule (pre-registered)

### 3.1 Common target

For each trading day `t`, define the binary next-day high-volatility label:

```
Y_t = 1  if  RV_{t+1} > M_t
Y_t = 0  otherwise
```

where `RV_{t+1}` is the day-(t+1) realized volatility of the Nifty 50 (§5), and
`M_t = median(RV_{t-19}, …, RV_t)` is the trailing 20-trading-day median of daily
RV, known as of the close of day `t`. The label is point-in-time and leak-free:
everything on the right of the prediction (features, threshold `M_t`) is known at
the close of day `t`; only the outcome `RV_{t+1}` is realized on day `t+1`.

### 3.2 One candidate, two references, one target

All three scores are evaluated against the **same** `Y` over the held-out window:

- **Candidate score** `s^{cand}_t` = the HAR-RV+VIX model's predicted
  `E[RV_{t+1}]` (continuous; §7). Because AUC is rank-based, any monotonic
  transform is equivalent — the linear predictor is used directly.
- **Gate reference** `s^{fix}_t` = the reference fixture's discrete `market_regime`
  value ∈ {0, 1, 2} (VIX thresholds 15 / 25), used directly as its discriminant
  score (per charter D3). This is the pre-registered **Approved gate**.
- **Secondary reference** `s^{vix}_t` = raw continuous `VIX_t`. Not a gate — reported
  to substantiate the §2.1 "beats VIX alone" claim (Phase-2 finding M1). Beating the
  3-level fixture bucket is necessary but not sufficient to claim the candidate beats
  VIX itself; the raw-VIX arm exposes that distinction.

### 3.3 H₀ / H₁

Let `ΔAUC_gate = AUC(s^{cand}, Y) − AUC(s^{fix}, Y)` and, for reporting,
`ΔAUC_vix = AUC(s^{cand}, Y) − AUC(s^{vix}, Y)`, both on the held-out window.

- **H₀ (null):** the candidate does not out-discriminate the fixture gate:
  `ΔAUC_gate ≤ 0`.
- **H₁ (alternative):** the candidate out-discriminates the fixture gate:
  `ΔAUC_gate > 0`, with the pre-registered practical-and-statistical bar
  `ΔAUC_gate ≥ 0.03` **and** the 95% moving-block-bootstrap CI of `ΔAUC_gate`
  excluding 0.

### 3.4 Decision rule

The artifact is **Approved** iff **both** hold on the held-out window:

```
ΔAUC_gate ≥ 0.03                                     (practical significance)
AND  95% moving-block-bootstrap CI of ΔAUC_gate excludes 0   (statistical significance)
```

`ΔAUC_vix` (with its own moving-block-bootstrap CI) is **reported alongside** and
qualifies the verdict: an Approved verdict with `ΔAUC_vix ≤ 0` substantiates only
"beats the fixture bucket," **not** the §2.1 "beats VIX alone" claim, and must be
recorded as such.

Primary metric: **ROC-AUC** (rank-based; compares the discrete fixture score and the
continuous candidate score without requiring probability calibration). Brier score is
**secondary** and reported for information only; it does not gate the verdict (the
discrete fixture cannot emit honest probabilities).

---

## 4. Latent Variable and Economic Rationale

**Latent variable:** `expected_next_day_realized_vol` — a single named `Estimate`
carrying `value` (predicted RV level) and `uncertainty`, in the multidimensional
`MarketState` (MSI-OD-001). One estimate; not a regime label, not a scalar
confidence (MM13 §4 established that named-estimate-with-uncertainty is the whole
consumer contract).

**A structurally-motivated forecasting variable (not a causal claim).** Volatility
clusters (large moves follow large moves) and mean-reverts — a well-established
property of financial returns (ARCH/GARCH literature; the HAR model of Corsi 2009
was built to capture the long-memory, multi-horizon structure of realized
volatility). This economic mechanism *motivates* the predictor and is the reason to
expect it to **generalize** out-of-sample; it does not make the reduced-form HAR
regression causal in the manipulationist sense. The variables here are
structurally-motivated **predictors**, not manipulable causes — an honest framing the
forecasting task does not require to be stronger.

**Why VIX is the bar to beat, not merely a feature.** India VIX is a forward-looking
option-implied volatility measure; it already prices expected near-term volatility.
The scientific question is therefore sharp: does the *realized*-vol time-series
structure (HAR) add forecasting power **over and above** the market's own implied
forecast? If HAR-RV+VIX cannot beat the VIX level alone (§3.2 secondary arm), the
realized-vol structure carries no incremental decision value here, and the §2.1 claim
is falsified.

---

## 5. Labels / Target Definition

**Daily realized volatility (Nifty 50):**

```
RV_t = sqrt( Σ_k r_{t,k}^2 ),   r_{t,k} = ln( P_{t,k} / P_{t,k-1} )
```

where `P_{t,k}` are the 1-minute closing prices of `NSE_INDEX|Nifty 50` within
trading day `t`, and `r_{t,k}` are the intraday 1-minute log returns.

- **Intraday only** — the overnight return (previous close → today's open) is
  **excluded**. RV here measures intraday realized volatility; the overnight gap is
  a distinct jump component and is not part of this construct. (Pre-registered
  choice, not optimized. Construct-mismatch note vs. VIX: §12.)
- **volume = 0 is a non-issue.** NSE index instruments report volume = 0, which
  breaks VWAP/vol_z filters — but RV is built from *returns*, not volume, so the
  known index-volume pitfall does not apply.
- **Half / special sessions** (e.g. Muhurat): `RV_t` uses whatever 1m bars exist
  for the day; no special handling. These are rare and flagged, not dropped, so the
  series has no gaps.
- **Scale invariance:** annualization is intentionally omitted. `RV_t` and the
  trailing median `M_t` share the same scale, and both AUC (rank-based) and the
  `> M_t` label are invariant to any positive constant scaling. Annualizing would
  change no result.

**Target `Y_t`** as defined in §3.1. One label per day, aligned so that the
prediction issued at the close of day `t` (using features through `t`) is scored
against `Y_t = 1[RV_{t+1} > M_t]`.

---

## 6. Feature Library

Every feature is admitted only by answering: **"which latent variable does this
estimate?"** For the forward-vol latent variable, the admitted features are the HAR
realized-vol aggregates plus the implied-vol level. All are daily, point-in-time,
and leak-free (computed from data through the close of day `t`).

| Feature | Definition (as of close of day `t`) | Source | Estimates | Leak check |
|---|---|---|---|---|
| `RV^{(d)}_t` | `RV_t` (1-day realized vol) | Nifty 50 1m | short-horizon vol persistence | uses only day `t` |
| `RV^{(w)}_t` | mean of `RV` over the last 5 trading days | Nifty 50 1m | weekly vol level | trailing 5d |
| `RV^{(m)}_t` | mean of `RV` over the last 22 trading days | Nifty 50 1m | monthly vol level / long memory | trailing 22d |
| `VIX_t` | India VIX close on day `t` | India VIX 1d | market-implied forward vol | close of day `t` |

Regressors enter the model in logs (§7). First usable prediction begins once the
22-day monthly aggregate is defined (≈22 trading days into the series).

**Explicitly rejected features (YAGNI / construct discipline):**

| Rejected | Why rejected |
|---|---|
| `banknifty_nifty_ratio` | estimates intermarket *direction/leadership*, not forward vol *level* |
| `nifty_20dma_slope` | estimates *trend direction*, not volatility |
| `gap_pct` | an execution-level / overnight-jump signal, not a realized-vol-regime indicator (prior art excluded it "per expert review" for the analogous reason) |
| `vix_pctl_90d`, `vix_roc_5d` | shock-onset transforms of VIX; the level `VIX_t` is the parsimonious implied-vol regressor. Deferred to increment 2 if the level proves insufficient — not added pre-emptively |

Rejecting these is a pre-registered commitment: they will **not** be silently added
after seeing dev-window results to lift performance.

---

## 7. Model

**Form — HAR-RV with an exogenous VIX regressor (log specification):**

```
log RV_{t+1} = b0
             + b1 · log RV^{(d)}_t
             + b2 · log RV^{(w)}_t
             + b3 · log RV^{(m)}_t
             + b4 · log VIX_t
             + ε_t
```

- **Estimator:** ordinary least squares on the **development window only**
  (2023-01-02 → 2025-12-31). Five coefficients (`b0…b4`) — deliberately few, to
  resist overfitting on a daily sample (~750 dev observations). The log form handles
  the right-skew and heteroskedasticity of realized volatility.
- **Freezing:** the fitted `b0…b4` (and the residual statistics below) are **frozen
  into the PublishedArtifact**. At runtime `evaluate()` applies the fixed linear
  combination to the evidence — fully deterministic; identical evidence ⇒ identical
  `MarketState` (MSI runtime contract).
- **Point estimate emitted:** `value = E[RV_{t+1}]`. Under the log-normal residual
  assumption, `E[RV_{t+1}] = exp( x_t·b + σ²/2 )`; because AUC is rank-based, the
  discriminant score in §3.2 may equivalently use the linear predictor `x_t·b`.
- **Uncertainty emitted (calibrated, in-scope — Phase-2 finding Mo2):** because RV is
  heteroskedastic even in logs and the MM13 consumer *uses* `uncertainty` to gate
  signals, a **state-dependent** uncertainty is a **required** Phase-5 deliverable,
  not an optional refinement. The emitted `uncertainty` is a prediction spread scaled
  by predicted level so it widens in high-vol states. It is validated by the §9
  Calibration domain's acceptance check; it does **not** enter the AUC gate.

**Comparison arms:**
- **Gate — the reference fixture** (`tests/msi/fixtures/test_artifact/`): the
  certified VIX-threshold classifier emitting `market_regime` ∈ {0,1,2} (thresholds
  15 / 25). Unchanged; the pre-registered Approved gate (§3.2).
- **Secondary — raw continuous `VIX_t`** (§3.2, finding M1): reported, not a gate;
  substantiates the §2.1 "beats VIX alone" claim.

---

## 8. Methodology

**Data.** 1m `NSE_INDEX|Nifty 50` closes → `RV_t` (§5); 1d `NSE_INDEX|India VIX`
close → `VIX_t`; both from the 2026-07-03 snapshot, spanning dev + held-out.

**Split.** Dev = 2023-01-02 → 2025-12-31 (fit + every selection decision, including
the block length `L`). Held-out = 2026-01-01 → 2026-07-03 (scored once, at Phase 6).

**Fit protocol.** Compute `RV_t` and aggregates over the dev window; fit the OLS of
§7; record `b0…b4`, `σ`, and residual diagnostics. Freeze into the artifact. No refit
on the held-out window.

**Head-to-head protocol.** Over the held-out window, for each day `t`: form
`s^{cand}_t`, `s^{fix}_t`, `s^{vix}_t`, and `Y_t`. Compute the three AUCs, then
`ΔAUC_gate` and `ΔAUC_vix`. Report the **held-out base rate** `mean(Y)` and its
run-structure (finding M3) — an AUC read without the base rate is uninterpretable
under a drifting-base-rate label.

**Uncertainty on ΔAUC — moving-block bootstrap (finding M2).** Both scores and the
label are strongly autocorrelated (RV is persistent; `Y` depends on a trailing
median), so an i.i.d. day-level bootstrap would understate the CI. Use a **moving-
block bootstrap**: resample contiguous blocks of length `L` (pinned from dev-window
RV autocorrelation, §1.1) with replacement, `B` replicates (pinned), recompute
`ΔAUC_gate` (and `ΔAUC_vix`) per replicate, take the 95% percentile interval. Apply
the §3.4 decision rule.

**Point-in-time discipline.** Every feature and the threshold `M_t` use only data
through the close of day `t`; the single-date `DuckDBObservationReader` reads suffice
because the hypothesis is daily and as-of-clean (charter §5.2 — satisfied by
construction, no spanning-read engineering).

---

## 9. Validation Plan → Minimal MSI-006 (path (ii), all seven domains)

The A2 harness will satisfy each mandatory domain with the lightest defensible
method (D1). Pre-committed here:

| Domain | Minimal method pre-committed |
|---|---|
| **Architectural** | Artifact conforms to MSI-007 shape (metadata + evidence_rules + model + provenance + checksum); emits the named estimate + uncertainty per the MM13 §4 contract. |
| **Scientific** | The §3 pre-registered head-to-head vs. the fixture gate **and** the secondary raw-VIX arm on the sealed held-out window; the §3.4 decision rule. |
| **Temporal** | Point-in-time / no-leak audit: features and `M_t` use only data ≤ day `t`; held-out never touched during fitting or selection. |
| **Robustness** | The 95% moving-block-bootstrap CI on `ΔAUC_gate` (§8); the held-out base rate + run-structure; one pre-registered sub-period split of the held-out window reported for information. |
| **Reproducibility** | The §1.1 substrate: pinned block length `L`, replicate count `B`, seed, library versions, data-snapshot hash, commit hash → deterministic re-run to identical `ΔAUC`. |
| **Operational** | `evaluate()` is deterministic and side-effect-free; identical evidence ⇒ identical `MarketState`. |
| **Calibration** | **Acceptance check (finding Mo2):** empirical coverage of the state-dependent prediction interval within a pre-stated tolerance (e.g. 90% interval covers 90% ± tolerance) — measured on dev, reported once on held-out, never tuned. |

---

## 10. Post-Experiment Decision Table (fixed before results exist)

The verdict for **every** possible held-out outcome is defined now, so no outcome
can be re-interpreted favorably after the fact. The gate is `ΔAUC_gate` (§3.4);
`ΔAUC_vix` is reported alongside and qualifies an Approved verdict per §3.4.

| Held-out outcome (`ΔAUC_gate`) | Verdict | Next action |
|---|---|---|
| `≥ 0.03` **and** CI excludes 0 | **H₁ supported → Approved** | Proceed to Phase 7 (first alpha strategy consuming this Knowledge). Record whether `ΔAUC_vix > 0` (claim §2.1 substantiated) or `≤ 0` (beats fixture bucket only). |
| `≥ 0.03` **but** CI includes 0 | **Inconclusive (underpowered)** | **Not Approved.** Do **not** tune. Re-evaluate under the *same* pre-registered rule only when the held-out window has extended with more 2026 data. |
| `0 < ΔAUC_gate < 0.03` | **Weak positive, below bar** | **Not Approved.** Record as a weak edge. A model enrichment (e.g. the deferred VIX transforms) is a *new* hypothesis with its *own* pre-registration in increment 2. |
| `≤ 0` | **H₀ not rejected** | Hypothesis **falsified** for this model form. HAR-over-fixture rejected. Return to Phase 2/3 with a different latent variable or model. The engineering deliverable (§2.2) still stands as a proven pipeline. |

---

## 11. Threats to Validity

**Statistical-conclusion validity.** The held-out window is short (~120 trading
days) and the label is autocorrelated with a **drifting base rate**, so the
*effective* sample size is far below 120. Power is limited: a real edge may leave the
moving-block-bootstrap CI straddling 0, giving an "inconclusive" verdict (§10 row 2)
rather than approval — an **expected, non-failing** outcome, not a disappointment to
explain away. AUC can also be partly inflated by a model tracking vol *persistence*
rather than forecasting regime *change*; the reported base rate and run-structure
(§8) expose this. The 3-level fixture score produces many ties, coarsening its AUC —
the raw-VIX secondary arm (§3.2) is the sharper comparison.

**Internal validity (leakage).** The dominant risk is contaminating the held-out
window: choosing the HAR lag structure, the 20-day median window, the block length
`L`, the intraday-only RV convention, or any threshold with knowledge of held-out
performance. Pre-registration forbids this — all such choices are fixed in this
document, on the dev window only. The label and features are constructed strictly
as-of day `t`.

**External validity (generalization).** HAR coefficients fitted on 2023–2025 may not
transfer to a structurally different 2026 regime; the prior daily-regime system's
central failure was **parameter non-stationarity** (`DRA_TECHNICAL_DOSSIER.md` §12).
A single held-out window cannot rule this out; the sub-period split (§9, Robustness)
is a partial, pre-registered probe.

**Construct validity.** Is "next-day Nifty 50 intraday RV (from 1m log-returns)
exceeding its trailing-20-day median" a faithful operationalization of "high
volatility regime"? Alternatives exist (Parkinson/Garman-Klass range estimators,
Yang-Zhang, different thresholds or horizons). The chosen construct is
pre-registered, not selected for performance; alternatives are out of scope for
increment 1 and would each require their own pre-registration.

---

## 12. Assumptions and Known Simplifications

1. HAR coefficients estimated on the dev window are approximately stationary into
   the held-out window (the assumption most directly threatened — §11 external).
2. India VIX and Nifty 50 daily series are date-alignable over dev + held-out; any
   holiday mismatch drops the day (no forward-fill of prices).
3. Intraday 1m realized volatility is a faithful proxy for the day's realized
   volatility; microstructure noise at the 1-minute frequency is tolerated and not
   separately modeled in increment 1.
4. The trailing-20-trading-day median is a reasonable, economically neutral
   threshold for "elevated vs. normal" next-day volatility. It is a definitional
   choice, pre-registered, not optimized.
5. The reference fixture is a fair, certified **gate** baseline; raw `VIX_t` is the
   secondary reference (§3.2).
6. **Parameter-estimation uncertainty is not modelled (finding Mo3):** the emitted
   `uncertainty` reflects residual/predictive spread only, not uncertainty in the
   fitted `b0…b4`. Acceptable for a frozen artifact; recorded as a known
   simplification.
7. **Construct mismatch (finding Mi2):** `RV_t` excludes the overnight return while
   VIX prices overnight-inclusive expectations. Defensible (intraday RV is the target
   construct) but recorded so it is not mistaken for an oversight.

---

## 13. Sources

| Source | Role |
|---|---|
| `docs/reports/MSRP_PHASE0_CHARTER.md` | Program charter; the three §8 decisions this dossier operationalizes |
| `docs/reports/MSRP_PHASE2_INDEPENDENT_REVIEW.md` | The independent review whose findings were resolved before this freeze |
| `docs/reports/DRA_TECHNICAL_DOSSIER.md` | Prior art: pre-SALVAGE daily regime features + the "classifier worked, strategy didn't" / non-stationarity lessons |
| `tests/msi/fixtures/test_artifact/` (`ReferenceTestArtifact`) | The reference fixture — the VIX-threshold baseline gate |
| `docs/architecture/market_state_intelligence/MSI_006_VALIDATION_FRAMEWORK.md` | The seven mandatory validation domains (§9) |
| MSI-007 (Published Artifact Specification) | The artifact shape the Phase-5 deliverable must conform to |
| Corsi, F. (2009), "A Simple Approximate Long-Memory Model of Realized Volatility", *J. Financial Econometrics* | The HAR-RV model form (§7) |
| MM13 `KnowledgeSignalSource` (`core/strategies/knowledge_signal_source.py`) | The empirical consumer contract (named estimate + uncertainty) the latent variable must satisfy |

---

*End of pre-registration. FROZEN. Nothing in this document reports a result computed
on the held-out window. Subsequent work either conforms to this pre-registration or
requires a new pre-registration for a new research increment.*
