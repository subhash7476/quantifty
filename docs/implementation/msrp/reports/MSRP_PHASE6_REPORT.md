# MSRP Phase 6 — Held-Out Scoring Report & Certification

**Document type:** Phase-6 report + certification (Market State Research Program)

**Subject:** The single held-out scoring run — applied the certified A2 Validation Harness to the sealed window 2026-01-01 → 2026-07-03 per the frozen Phase-1 dossier.

**Date:** 2026-07-07

**Predecessors:** Phase-1 dossier (d9233b1), Phase-5A artifact (certified), Phase-5B harness (certified), Phase-6 pre-flight (L=28, B=10000, seed=42)

**validation_id:** `47fe32723aa9da163aee5b32e72934609187fec79f254c7b95d64629e75a6c42`

---

## 1. Pinned Reproducibility Substrate

| Field | Value | Source |
|-------|-------|--------|
| Block length `L` | 28 | Dev-window RV ACF (first lag below 1.96/√722 ≈ 0.073 at k=28, |ACF|=0.0624, no override) |
| Replicate count `B` | 10000 | Administratively pinned |
| RNG seed | 42 | Administratively pinned |
| Python | 3.13.5 | Build environment |
| numpy | 2.4.4 | Build environment |
| pandas | 2.3.3 | Build environment |
| statsmodels | 0.14.6 | Build environment |
| scikit-learn | 1.8.0 | Build environment |
| harness_version | 1.0.0 | Certified |
| Code commit | `ce7d4eb` | Runner byte-identical to Phase-5B-certified `6e10142` |
| Artifact checksum | `e6185683...` | Verified OK |
| dataset_snapshot_hash | `e2a9a603...` | 2026-07-03 candle store |

---

## 2. Held-Out Scoring Results

| Metric | Value |
|--------|-------|
| **delta_auc_gate** | **0.090767** |
| 95% MBB CI (lower) | 0.019941 |
| 95% MBB CI (upper) | 0.212755 |
| AUC candidate | 0.584943 |
| AUC fixture (VIX 0/1/2) | 0.494176 |
| AUC raw VIX | 0.518750 |
| **delta_auc_vix** | **0.066193** |
| Held-out base rate | 0.537815 |
| n_scored | 119 |
| n_dropped_boundary | 1 |

---

## 3. Seven-Domain Validation

| Domain | Status | Key Evidence |
|--------|--------|--------------|
| Architectural | PASS | Artifact v1.0.0, feature names match MSI-007 shape |
| Scientific | PASS | ΔAUC_gate=0.090767 ≥ 0.03 ∧ CI excludes 0 |
| Temporal | PASS | Evaluation window [2026-01-01, 2026-07-03]; 1 boundary day dropped |
| Robustness | REPORTED | CI re-reported; first-half Δ=0.065185, second-half Δ=0.0125 |
| Operational | PASS | evaluate() deterministic (score_repeatable=true) |
| Calibration | PASS | Empirical coverage 94.12% of nominal 90% (tolerance ±5%) |
| Reproducibility | PASS | results_digest byte-identical on double-invocation |

**Conjunctive verdict:** All mandatory domains PASS → `Approved (candidate)`.

---

## 4. §10 Decision Table — Verdict

| Criterion | Value | Met? |
|-----------|-------|------|
| ΔAUC_gate ≥ 0.03 | 0.090767 | ✓ |
| 95% CI excludes 0 | ci_lower = 0.019941 > 0 | ✓ |

**Verdict: Approved (§10 row 1).**

**§3.4 qualifier:** ΔAUC_vix = 0.066193 > 0 → the candidate out-discriminates raw continuous VIX. Per the dossier, this Approved verdict substantiates the §2.1 claim: "HAR-RV structure adds forecasting power over and above the market's own implied forecast." This is the strong outcome — not merely "beats the fixture bucket."

---

## 5. Caveats (dossier §11)

**Modest edge on a single window.** AUC_candidate ≈ 0.585 represents a statistically-significant but economically-modest edge over a ~120-trading-day held-out period. This does not rule out parameter non-stationarity — HAR coefficients fitted on 2023–2025 may not transfer to a structurally different regime (the prior daily-regime system's central failure mode).

**Sub-period drift.** The first half of the held-out window (H1-2026) carries ΔAUC_gate = 0.065185; the second half (through early July) carries ΔAUC_gate = 0.0125 — consistent directional edge but fading. This sub-period split is a pre-registered partial probe, not a decision input, but it is consistent with the §11 external-validity concern.

**Effective sample size.** The held-out window is short (119 scored trading days) and the label is autocorrelated with a drifting base rate (0.538). The MBB CI properly accounts for the autocorrelation, but statistical power remains limited — a real edge at this magnitude could easily have returned an "inconclusive" verdict on a different 6-month draw of 2026. This was an expected, non-failing possibility per §11.

**Calibration strong.** Empirical coverage of 94.12% vs nominal 90% (±5% tolerance) indicates the state-dependent predictive interval is well-calibrated on this window — not overconfident.

---

## 6. Execution Attestation

An independent execution attestation was performed (see `MSRP_PHASE6_REVIEW.md`). All six attestation checks passed: evaluation window correct, single-touch upheld, substrate pinned correctly, all seven domains resolved, §10 mapping faithful, determinism spot-check verified. The sealed record is attested with `reviewer = "Phase-6 attestation"` and `approval_status = "approved"` via `checksum.sha256` re-seal.

---

## 7. Next Action

**Phase 7 — First Alpha Strategy Consuming this Knowledge.** Per the charter: build the first strategy that consumes the `expected_next_day_realized_vol` Knowledge from the certified `ForwardVolatilityArtifact` and evaluates against the reference fixture. Phase 7 is authorized by this Approved verdict but is not started here. The strategy must be a new design, pre-registered, and evaluated on its own held-out window.

---

## 8. Certification

**MSRP Phase 6 — Held-Out Scoring Run — CERTIFIED — PASS.**

The single held-out scoring run executed faithfully against the certified A2 harness. The frozen pre-registered decision rule (dossier §3.4) returns an Approved verdict. The sealed record is immutable, attested, and checksum-verified. No frozen components were modified. The §2.1 scientific claim is substantiated (HAR-RV+VIX out-discriminates both the fixture gate and raw VIX alone on the held-out window). All caveats are recorded faithfully; none are qualified away.

---

*End of report. MSRP Phase 6 is officially certified.*
