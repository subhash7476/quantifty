# MSRP Phase 5B — A2 Validation Harness — Implementation Review

**Document type:** Implementation review

**Subject:** Review of the A2 Validation Harness implementation against the Phase 5B design spec

**Date:** 2026-07-06

**Status:** Approved — 4 findings (0 blocking)

**Reviewing:** 8 files, 353 tests (25 new + 328 existing), zero frozen-file changes

---

## Verdict

Implementation is faithful to the design spec. All three notes from the pre-implementation review were applied correctly. Four non-blocking findings below.

---

## Files Reviewed

| File | Lines | Verdict |
|------|-------|---------|
| `core/msi/msrp/validation_stats.py` | 83 | PASS — ROC-AUC, MBB CI, canonical JSON, 6dp, sha256 all correct |
| `core/msi/msrp/validation_scoring.py` | 123 | PASS — `ScoredWindow`, VIX gate, direct `evaluate()`, label construction |
| `core/msi/msrp/validation.py` | 358 | PASS — DTOs, 7 domains, aggregator, sealed-record I/O |
| `scripts/msrp/run_forward_vol_validation.py` | 192 | PASS — composition root, data loading, phase-6 guard |
| `core/msi/validations/.gitkeep` | 0 | PASS |
| `tests/msi/msrp/test_validation_stats.py` | 48 | PASS — 7 tests |
| `tests/msi/msrp/test_validation_scoring.py` | 54 | PASS — 3 tests |
| `tests/msi/msrp/test_forward_vol_validation.py` | 182 | PASS — 15 tests |

---

## Findings

### F1 — `methodology.json` omits calibration params (non-blocking)

`validation.py:332-345` — the `methodology` dict written to `methodology.json` by `run()` excludes `calibration_nominal` and `calibration_tolerance`, even though both are hashed into `methodology_fingerprint`. The recorded methodology JSON should be self-contained.

**Recommendation:** Add `calibration_nominal` and `calibration_tolerance` to the methodology dict.

---

### F2 — `warmup_days` parameter in `score_window` is dead code (non-blocking)

`validation_scoring.py:74` — `score_window` accepts `warmup_days: int = 22` but never uses it. The warmup trim is handled implicitly by `compute_har_features(rv)` which has a hardcoded 22-day minimum. The parameter is dead weight in the signature.

**Recommendation:** Remove the unused parameter, or pass it through to `compute_har_features` if that module supports a configurable warmup.

---

### F3 — `_evaluate_calibration` returns `REPORTED` for empty valid-day set (non-blocking)

`validation.py:279-281` — when `n_valid == 0`, the method returns `REPORTED` instead of the expected `PASS`/`FAIL` per the design spec §4.7. This is a defensive guard that will never fire on real positive-RV data, but the spec lists Calibration as a mandatory PASS/FAIL domain. The `REPORTED` fallback silently bypasses a mandatory check.

**Recommendation:** Either (a) return `FAIL` when calibration can't be computed (principle: mandatory domain with no evidence = cannot pass), or (b) document in the spec that `REPORTED` is a valid Calibration outcome for the empty-data edge case.

---

### F4 — No test coverage for `_evaluate_architectural` with a real artifact (non-blocking)

`validation.py:222-223` — the unit-test path returns `PASS` when `artifact=None`. All 15 harness tests use this skip path. The real-artifact path (feature-name assertion, uncertainty check) is exercised only by the integration test in `test_validation_scoring.py` and the CLI smoke run — not by a dedicated architectural-domain unit test.

**Recommendation:** Acknowledge the coverage gap. It's acceptable for D1 minimal-but-conformant; the integration test validates the real artifact path indirectly.

---

## Verified Correct

| Mechanism | Location | Status |
|-----------|----------|--------|
| `validation_id` preimage (5 fields, excludes results) | `validation.py:307-317` | Correct |
| `methodology_fingerprint` excludes `harness_version` | `validation.py:71-87` | Correct |
| `results_digest` via `_round_results` + `canonical_json` | `validation.py:90-105` | Correct |
| MBB CI determinism with fixed seed | `validation_stats.py:43-71` | Correct |
| Sub-period split `(n + 1) // 2` (ceil) | `validation.py:196` | Correct |
| Calibration PI reconstruction from (value, uncertainty) | `validation.py:269-293` | Correct |
| Calibration params in `Methodology` DTO + fingerprint | `validation.py:40-47, 71-87` | Correct |
| Phase-6 duplicate guard | `run_forward_vol_validation.py:97-122` | Correct |
| `files = sorted(set(files))` dedup | `run_forward_vol_validation.py:93` | Correct |
| `statsmodels`/`sklearn`/`scipy` in lib versions | `run_forward_vol_validation.py:125-134` | Correct |
| Conjunctive verdict — any FAIL → Rejected | `validation.py:329` | Correct |
| `checksum.sha256` per-file + combined hash | `validation.py:154-156` | Correct |
| `format_6dp` float determinism | `validation_stats.py:74-75` | Correct |
| `record.json` excludes reviewer/approval_status in 5B | `validation.py:137-138` | Correct |
| `dataset_snapshot_hash` sorted manifest | `validation.py:108-113` | Correct |
| Binary-stability caveat honored (frozen binary files) | `run_forward_vol_validation.py:161` | Correct |

---

## Test Summary

```
353 passed (25 new + 328 existing), 0 failures
Zero frozen-file changes confirmed (git diff on contracts/interfaces/dra/artifacts/forward_vol.py)
```

**New tests:**
- `test_validation_stats.py`: 7 tests (AUC edge cases, bootstrap determinism, 6dp formatting, sha256)
- `test_validation_scoring.py`: 3 tests (VIX gate thresholds, evidence features, scoring pipeline shapes)
- `test_forward_vol_validation.py`: 15 tests (domain methods, aggregator, id/digest determinism, sealed record I/O, phase-6 guard, two-instance reproducibility)

---

*End of implementation review. 0 blocking findings. Approved for Phase 6 held-out scoring after the Phase-6 independent technical review.*
