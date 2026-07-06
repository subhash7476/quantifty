# MSRP Phase 5A — PublishedArtifact v2 Implementation Report

**Document type:** Implementation report (Phase 5A of the Market State Research Program).

**Subject:** `PublishedArtifact v2` for the Forward Volatility Regime hypothesis
(`expected_next_day_realized_vol`).

**Status:** Implementation complete; ready for independent technical review.

**Date:** 2026-07-06

**Governing baseline:** MSRP Phase-1 Research Dossier, commit `d9233b1` (FROZEN).

---

## Implementation Conformance Statement

> This implementation conforms exactly to the frozen MSRP Phase-1 Research Dossier
> (commit `d9233b1`) and incorporates all mandatory revisions identified in the Phase-2
> Independent Review. No research decisions, feature additions, parameter changes,
> validation changes, or methodological alterations were introduced during
> implementation.

---

## 1. Implementation Summary

A single `PublishedArtifact v2` (`ForwardVolatilityArtifact`) was implemented, fitting
the frozen HAR-RV+VIX log specification by ordinary least squares **on the development
window only** (2023-01-02 → 2025-12-31) and freezing the coefficients into an immutable,
MSI-007-shaped artifact. The held-out window (2026-01-01 → 2026-07-03) was never read
during fitting.

The artifact's deterministic `evaluate()` applies the frozen linear predictor to
pre-built Evidence (the four dossier features) and emits one named Estimate
(`expected_next_day_realized_vol`) with a **state-dependent** uncertainty (Phase-2
finding Mo2). The artifact loads through the certified `FilesystemArtifactLoader` and
produces MSI-v1.0-compatible `KnowledgeObject`s via the certified
`DefaultKnowledgeBuilder`. No MSI runtime, contract, or interface code was modified.

### Frozen coefficients (dev window, OLS, n_obs = 700)

| Coefficient | Value | Dossier role |
|---|---|---|
| `b0` (intercept) | -3.762284 | §7 intercept |
| `b1` (`log RV^{(d)}`) | 0.312252 | §7 daily HAR term |
| `b2` (`log RV^{(w)}`) | 0.129720 | §7 weekly HAR term |
| `b3` (`log RV^{(m)}`) | 0.082761 | §7 monthly HAR term |
| `b4` (`log VIX`) | 0.475815 | §7 exogenous implied-vol term |
| `sigma` (residual std, log space) | 0.272552 | §7 log-normal residual assumption |

All five coefficients are positive (economically consistent with volatility clustering,
Corsi 2009); the VIX term carries the largest weight, as the dossier's "VIX is the bar
to beat" framing (§4) predicts. These were fitted, not tuned.

---

## 2. Files Created

| Path | Purpose |
|---|---|
| `core/msi/artifacts/forward_vol_v2/metadata.json` | MSI-007 §7 artifact identity + compatibility |
| `core/msi/artifacts/forward_vol_v2/evidence_rules.json` | MSI-004 §2 evidence rules (4 features) |
| `core/msi/artifacts/forward_vol_v2/model.py` | Frozen `ForwardVolatilityArtifact` (PublishedArtifact subclass) |
| `core/msi/artifacts/forward_vol_v2/provenance.json` | MSI-007 §9 provenance + research record |
| `core/msi/artifacts/forward_vol_v2/checksum.sha256` | MSI-007 integrity (per-file + combined SHA-256) |
| `core/msi/msrp/__init__.py` | Authoring module package |
| `core/msi/msrp/forward_vol.py` | RV construction + HAR features + OLS fit (importable, tested) |
| `scripts/msrp/build_forward_vol_artifact.py` | A1 authoring script: data → fit → frozen artifact |
| `tests/msi/msrp/__init__.py` | Test package |
| `tests/msi/msrp/test_forward_vol_artifact.py` | 42 unit/integration tests |
| `docs/implementation/msrp/reports/MSRP_PHASE5A_IMPLEMENTATION_REPORT.md` | This report |

## 3. Files Modified

**None.** No existing production code, contract, interface, MSI runtime component, test,
or governing document was modified. The change set is purely additive (new artifact +
new authoring module + new build script + new tests + this report).

## 4. Tests Added

`tests/msi/msrp/test_forward_vol_artifact.py` — **42 tests** across 11 classes:

| Class | Coverage | Count |
|---|---|---|
| `TestFeatureConstruction` | RV from intraday 1m log-returns; overnight exclusion; scale invariance; HAR windows + warmup | 5 |
| `TestCoefficientFitting` | deterministic fit; matches manual `lstsq`; held-out never leaks into dev fit | 3 |
| `TestArtifactStructure` | 5 required files; no unexpected files | 3 |
| `TestArtifactMetadata` | required fields; runtime compatibility; MSI-v1.0 declaration | 3 |
| `TestArtifactChecksum` | sha256; covers all content files; per-file + combined integrity | 4 |
| `TestEvidenceRules` | four features; required symbols; rule format | 3 |
| `TestCoefficientSerialization` | model.py carries frozen literals; literals match module object | 2 |
| `TestArtifactLoading` | loads via certified `FilesystemArtifactLoader`; metadata identity | 3 |
| `TestEvaluate` | returns MarketState; named estimate; matches log-normal formula; determinism (×2); rejects missing/non-positive evidence; immutability | 8 |
| `TestStateDependentUncertainty` | matches formula; widens in high-vol; positive (Phase-2 Mo2) | 3 |
| `TestKnowledgeObjectGeneration` | builds KO; MSI-v1.0 runtime; deterministic knowledge_id | 2 |
| `TestDeterministicReplay` | three consecutive load→evaluate→build cycles → identical knowledge_id | 1 |
| `TestPointInTime` | evaluate uses only provided evidence; different evidence → different output | 2 |

---

## 5. Test Execution Results

```
$ python -m pytest tests/msi/msrp/test_forward_vol_artifact.py -v
============================= 42 passed in 1.42s ==============================
```

## 6. Regression Summary

Full MSI suite, unchanged baseline plus the new tests:

```
$ python -m pytest tests/msi/
============================= 326 passed in 3.61s =============================
```

- **Existing MSI tests:** 284 — all pass, no regressions.
- **New Phase-5A tests:** 42 — all pass.
- **Total:** 326 passed, 0 failed, 0 errors, 0 skipped.

The frozen reference fixture (`tests/msi/fixtures/test_artifact/`) and the certified DRA
pipeline (`DRAOrchestrator`, `FilesystemArtifactLoader`, `DefaultEvidenceBuilder`,
`DefaultArtifactEvaluator`, `DefaultKnowledgeBuilder`) are untouched and remain green.

---

## 7. Mapping: Dossier Sections → Implementation

| Dossier section | Implementation realization |
|---|---|
| §3.1 label `Y_t` | Label is the Phase-6 evaluation's concern (out of scope for 5A); the artifact emits the continuous `E[RV_{t+1}]` score that the dossier specifies as the candidate discriminant (§3.2). |
| §5 RV definition | `compute_daily_rv()` — `sqrt(Σ r²)`, intraday-only log-returns, no annualization, drops <2-print days. |
| §5 overnight exclusion | Explicit: per-day 1m closes only; no prev-close→open term (verified by `test_rv_excludes_overnight_return`). |
| §6 feature library | `compute_har_features()` — `rv_daily` (1d), `rv_weekly` (5d mean), `rv_monthly` (22d mean), `vix_close`; the four rejected features are absent. |
| §6 22-day warmup | `compute_har_features().dropna()` — first usable row after the monthly aggregate exists. |
| §7 model form | `fit_har_rv_vix()` — OLS of `log RV_{t+1}` on `[1, log RV_d, log RV_w, log RV_m, log VIX]`; five coefficients `b0…b4`. |
| §7 estimator = OLS, dev-only | Fit restricted to `[dev_start, dev_end]`; numpy closed-form `lstsq` (uniquely determined; statsmodels not installed, not required). |
| §7 freezing | Fitted `b0…b4`, `sigma` baked into `model.py` as module-level literals; checksum-frozen. |
| §7 point estimate `E[RV]=exp(x·b+σ²/2)` | `point_estimate()` / inline in `evaluate()`. |
| §7 uncertainty (Mo2, state-dependent) | `predictive_uncertainty()` = log-normal predictive SD `value·sqrt(exp(σ²)−1)` — see §8 below. |
| §8 held-out sealed | Target `RV_{t+1}` clamped so `t+1 ≤ dev_end` before shift; held-out never used as a target. Verified by `test_fit_only_uses_dev_window`. |
| §8 VIX inner-join, no forward-fill | `vix.reindex(features.index)` then `dropna` (holiday mismatches dropped). |
| §9 Architectural domain | MSI-007 shape (metadata + evidence_rules + model + provenance + checksum); named estimate + uncertainty per MM13 §4. |
| §9 Operational domain | `evaluate()` deterministic, side-effect-free; verified by replay tests. |
| §12.6 Mo3 simplification | `uncertainty` reflects residual spread only, not `b0…b4` estimation uncertainty — recorded in `provenance.json` notes. |

---

## 8. Implementation Decisions (all non-research; documented per discipline rule)

The frozen dossier is law. The following are **implementation-level** choices that change
no model form, label, feature, metric, or decision rule. Each is recorded here for
reviewer traceability.

1. **OLS solver — numpy `np.linalg.lstsq`.** `statsmodels` is not installed in this
   environment and is not needed: the OLS closed form is uniquely determined, so the
   solver introduces no coefficient degrees of freedom. No research decision.

2. **Estimate `dimension` field — `"volatility_level"`.** The `Estimate` DTO requires a
   `dimension` string (MSI-002 §4.7); the dossier names the latent variable
   (`expected_next_day_realized_vol`) but not this descriptive label. `"volatility_level"`
   is a label, not a model decision.

3. **State-dependent uncertainty formula (Phase-2 Mo2) — log-normal predictive SD.** The
   dossier commits to the log-normal residual assumption for the point estimate
   (`E[RV_{t+1}] = exp(x_t·b + σ²/2)`). Under the **same** assumption, the predictive
   standard deviation of `RV_{t+1}` is mathematically
   `sqrt((exp(σ²)−1)·exp(2·μ+σ²)) = value·sqrt(exp(σ²)−1)`. This is therefore the
   **derived** state-dependent spread, not an invented calibration: it (a) scales with
   the predicted level, (b) widens in high-vol states (exactly Mo2's requirement), and
   (c) uses residual spread only (honouring Mo3). It does **not** enter the AUC gate
   (dossier §7). Calibration *acceptance* is a Phase-6/A2 concern (explicitly out of
   scope for 5A).

4. **Evidence feature names — `rv_daily`, `rv_weekly`, `rv_monthly`, `vix_close`.**
   Implementation labels for the dossier's `RV^{(d)}`, `RV^{(w)}`, `RV^{(m)}`, `VIX_t`.

5. **Artifact location — `core/msi/artifacts/forward_vol_v2/`.** No `artifacts/`
   directory previously existed; the Phase-5A prompt names `core/msi/artifacts/` as the
   expected location. Additive only.

6. **`lifecycle_state` / `validation_status` omitted from `metadata.json`.** Phase 5A is
   explicitly *pre-review, pre-certification*. Declaring `validation_status = "Approved"`
   would be premature certification (an MSI-008 governance act outside this phase). The
   artifact is loadable (the loader treats absent status fields as "not yet governed"),
   matching the established reference-fixture pattern.

7. **Point-in-time target clamp.** During implementation, the test
   `test_fit_only_uses_dev_window` surfaced that `RV_{t+1} = rv.shift(-1)` could, in
   principle, reach a held-out `t+1` if held-out data were present in the series. The
   function now clamps the target series to `≤ dev_end` before shifting, making the
   dossier §1 "held-out sealed" invariant **explicit and unconditional**. This changed
   **no fitted coefficient** (the production build loads only dev-window data, so the
   clamp is a no-op there — n_obs, sigma, and all five coefficients are bit-identical
   before and after).

---

## 9. Architectural Compliance

| MSI principle | Evidence |
|---|---|
| MSI-007 shape (metadata + evidence_rules + model + provenance + checksum) | Artifact directory contains exactly these 5 files; verified by `TestArtifactStructure`. |
| Immutability (MSI-AP-701) | Frozen dataclasses; coefficients are module literals; checksum-frozen; metadata immutable (`test_market_state_immutable`, `test_artifact_metadata_dto_is_immutable` analogue). |
| Determinism (MSI-AP-705 / MSI-005 §13) | `evaluate()` identical across instances and runs; 3× replay → identical `knowledge_id`. |
| Opacity (MSI-7D-02) | Runtime depends only on `metadata`, `get_evidence_rules()`, `evaluate()`; no internals inspected. |
| Compatibility (MSI-007 §8) | Declares `msi-v1.0` runtime, `1.0` ontology, `1.0` contract; loadable by the certified `FilesystemArtifactLoader`. |
| MSI-OD-001 (multidimensional, no scalar confidence) | Single named Estimate with `value` + `uncertainty`; no scalar `confidence` on MarketState (MM13 §4 contract). |
| Certified-runtime compatibility | Loads via `FilesystemArtifactLoader`; KO built via `DefaultKnowledgeBuilder`; runtime_version `msi-v1.0`. |
| No architectural changes | Zero existing files modified. |

---

## 10. Acceptance Criteria

| Criterion | Status |
|---|---|
| PublishedArtifact v2 implemented | ✅ `ForwardVolatilityArtifact` |
| Coefficients fitted only on the dev window | ✅ 2023-01-02 → 2025-12-31; held-out sealed (target clamp) |
| Coefficients frozen after fitting | ✅ Literals in `model.py`; checksum-frozen |
| Artifact deterministic | ✅ `TestEvaluate::test_deterministic_*` |
| Artifact replayable | ✅ `TestDeterministicReplay` |
| `evaluate()` deterministic | ✅ Identical evidence → identical MarketState |
| KnowledgeObjects emitted correctly | ✅ `TestKnowledgeObjectGeneration`; MSI-v1.0 runtime |
| MSI runtime compatibility preserved | ✅ Loads via certified loader; 284 existing tests green |
| Existing MSI tests remain green | ✅ 284/284 pass |
| New tests pass | ✅ 42/42 pass |
| No research decisions made during implementation | ✅ See §8; all choices are implementation-level |

---

## 11. Deviations

**None.** The implementation realizes the frozen dossier exactly. The seven items in §8
are implementation decisions recorded for traceability, not deviations from the frozen
specification.

---

## 12. Out-of-Scope Confirmation

Per the Phase-5A brief, the following were **not** performed and remain for their
separate governed phases:

- MSI-006 A2 validation harness — not built.
- Held-out evaluation — not run; held-out window untouched.
- Technical review, review fixes, certification, governance updates, commit, tag — not
  performed.

---

## 13. Confirmation

1. **Implementation conforms exactly to the frozen Phase-1 dossier (commit `d9233b1`)**,
   with all Phase-2 mandatory revisions incorporated (M1 secondary arm is a reporting
   concern for Phase 6; M2 moving-block bootstrap is an A2 concern; M3 base-rate
   reporting is Phase 6; Mo1 wording already in the dossier; **Mo2 calibrated
   state-dependent uncertainty is implemented** as a required Phase-5 deliverable; Mo3
   recorded in provenance).

2. **No research decisions were introduced.** Every choice in §8 is an
   implementation-level decision that leaves the model form, label, features, metric,
   and decision rule identical to the frozen pre-registration.

3. **Phase 5A is ready for independent technical review.**

---

*End of implementation report. Implementation only — review, certification, and
governance are separate governed phases.*
