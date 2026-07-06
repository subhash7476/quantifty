# MSRP Phase 5B — A2 Validation Harness — Implementation Addendum

**Date:** 2026-07-06

**Status:** Addendum to the Phase-5B implementation — four findings raised during post-implementation review, three fixed, one acknowledged.

---

## Finding 1 — `methodology.json` missing calibration params

**Status:** FIXED

`validation.py:332-345` — the `methodology` dict in `run()` omitted `calibration_nominal` and `calibration_tolerance`, even though both are hashed into `methodology_fingerprint`. The recorded methodology was not self-contained.

**Fix:** Added both fields to the methodology dict at `validation.py:345-346`:
```python
"calibration_nominal": self._methodology.calibration_nominal,
"calibration_tolerance": self._methodology.calibration_tolerance,
```

---

## Finding 2 — `warmup_days` parameter in `score_window` is dead code

**Status:** FIXED

`validation_scoring.py:68-75` — `score_window` accepted `warmup_days: int = 22` but never used it. The warmup is handled implicitly by `compute_har_features(rv)` (hardcoded 22-day trim in `forward_vol.py`).

**Fix:** Removed the `warmup_days` parameter from the signature and the single test call site (`test_validation_scoring.py:46`).

---

## Finding 3 — `_evaluate_calibration` returns `REPORTED` for zero valid days

**Status:** FIXED

`validation.py:279-281` — the zero-valid-days guard returned `DomainResult("calibration", "REPORTED", ...)`. Calibration is a mandatory PASS/FAIL domain per design spec §4.7; `REPORTED` silently skips the gate.

**Fix:** Changed `"REPORTED"` to `"FAIL"` — if calibration cannot be verified, the record is rejected.

---

## Finding 4 — `_evaluate_architectural` with `artifact=None` returns `PASS`

**Status:** ACKNOWLEDGED — not a bug

`validation.py:222-223` — the unit-test-only path (no real artifact) returns `PASS` with `{"skipped": "no artifact"}`. When the real certified artifact passes through, the domain correctly checks feature names and returns `FAIL` on mismatch. There is no test exercising the real-artifact path for the architectural domain — a coverage gap, not a correctness issue. Acceptable for Phase 5B; the real-artifact path is exercised implicitly by `test_validation_scoring.py::test_score_window_shapes_and_boundary_drop` (loads the artifact and runs `score_window`).
