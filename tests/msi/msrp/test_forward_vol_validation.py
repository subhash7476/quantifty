import hashlib
import json

import numpy as np
import pytest

from core.msi.msrp.validation import (
    HARNESS_VERSION,
    Substrate,
    Methodology,
    ValidationHarness,
    DomainResult,
    ValidationRecord,
    methodology_fingerprint,
    results_digest,
    dataset_snapshot_hash,
    write_sealed_record,
)
from core.msi.msrp.validation_scoring import ScoredWindow


def _methodology():
    return Methodology(
        substrate=Substrate(
            block_length=10, n_replicates=500, seed=42,
            lib_versions={"numpy": "x", "pandas": "y"}, commit="deadbeef",
        ),
        median_window=20, delta_auc_bar=0.03, dossier_commit="d9233b1",
        calibration_nominal=0.90, calibration_tolerance=0.05,
    )


def _scored(sep=True, n=120, seed=0):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) > 0.5).astype(int)
    base = 0.3 * y if sep else np.zeros(n)
    s_cand = np.exp(base + rng.normal(0, 0.2, n))
    s_unc = s_cand * 0.3
    rv_next = np.exp(rng.normal(-3.0, 0.3, n))
    return ScoredWindow(
        dates=tuple(f"2024-01-{i % 28 + 1:02d}" for i in range(n)),
        s_cand=s_cand, s_fix=rng.normal(0, 1, n), s_vix=rng.normal(15, 3, n), y=y,
        s_unc=s_unc, rv_next=rv_next,
        n_dropped_boundary=1, requested_window=("2024-01-01", "2024-06-30"),
    )


def _harness(scored):
    return ValidationHarness(
        artifact=None, methodology=_methodology(), scored=scored,
        evaluation_window=("2024-01-01", "2024-06-30"), phase="5B",
        artifact_checksum="artifactsum", dataset_snapshot_hash="datasetsum",
    )


# --- Task 3 tests ---

def test_methodology_fingerprint_excludes_harness_version():
    fp = methodology_fingerprint(_methodology())
    assert isinstance(fp, str) and len(fp) == 64
    assert HARNESS_VERSION not in fp


def test_delta_auc_ci_is_shared_and_deterministic():
    h = _harness(_scored())
    ci_a = h._delta_auc_ci()
    ci_b = h._delta_auc_ci()
    assert ci_a == ci_b
    assert ci_a[0] <= ci_a[1]


def test_results_digest_is_stable_and_6dp():
    r = {"delta_auc_gate": 1 / 3, "domain_verdicts": {"scientific": "PASS"}}
    assert results_digest(r) == results_digest(r)
    assert len(results_digest(r)) == 64


# --- Task 4 tests ---

def test_scientific_pass_on_separated_scores():
    dr = _harness(_scored(sep=True))._evaluate_scientific()
    assert dr.name == "scientific" and dr.status == "PASS"
    assert dr.evidence["delta_auc_gate"] >= 0.03


def test_scientific_fail_on_noise():
    assert _harness(_scored(sep=False))._evaluate_scientific().status == "FAIL"


def test_robustness_is_reported_only():
    dr = _harness(_scored())._evaluate_robustness()
    assert dr.status == "REPORTED"
    assert "subperiod_first_half_delta_auc_gate" in dr.evidence


def test_temporal_records_window_and_boundary_drop():
    dr = _harness(_scored())._evaluate_temporal()
    assert dr.evidence["evaluation_window"] == ["2024-01-01", "2024-06-30"]
    assert dr.evidence["n_dropped_boundary"] == 1


def test_calibration_reports_coverage_and_gates():
    rng = np.random.default_rng(3)
    n = 300
    mu = rng.normal(-3.0, 0.2, n)
    sig = 0.27
    value = np.exp(mu + sig ** 2 / 2)
    unc = value * np.sqrt(np.exp(sig ** 2) - 1)
    rv_next = np.exp(mu + rng.normal(0, sig, n))
    sw = ScoredWindow(
        dates=tuple(str(i) for i in range(n)),
        s_cand=value, s_fix=rng.normal(0, 1, n), s_vix=rng.normal(15, 3, n),
        y=(rng.random(n) > 0.5).astype(int), s_unc=unc, rv_next=rv_next,
        n_dropped_boundary=0, requested_window=("2024-01-01", "2024-12-31"),
    )
    dr = _harness(sw)._evaluate_calibration()
    assert dr.name == "calibration" and dr.status == "PASS"
    assert dr.evidence["nominal"] == 0.90
    assert 0.85 <= dr.evidence["empirical_coverage"] <= 0.95


def test_run_produces_record_with_conjunctive_verdict():
    rec = _harness(_scored(sep=False)).run()
    assert rec.candidate_verdict == "Rejected"
    assert rec.phase == "5B"
    assert len(rec.validation_id) == 64
    assert rec.results_digest == results_digest(rec.results)


def test_validation_id_excludes_results():
    h1 = _harness(_scored(sep=True, seed=1))
    h2 = _harness(_scored(sep=False, seed=2))
    assert h1.validation_id() == h2.validation_id()


# --- Task 5 tests ---

def test_dataset_snapshot_hash_is_sorted_and_scoped(tmp_path):
    a = tmp_path / "b.duckdb"; a.write_bytes(b"BB")
    b = tmp_path / "a.duckdb"; b.write_bytes(b"AA")
    assert dataset_snapshot_hash([a, b]) == dataset_snapshot_hash([b, a])
    assert len(dataset_snapshot_hash([a, b])) == 64


def test_write_sealed_record_roundtrip_and_checksum(tmp_path):
    rec = _harness(_scored(sep=True)).run()
    out = write_sealed_record(rec, tmp_path, reviewer=None, approval_status=None,
                              timestamp_iso="2026-07-06T00:00:00")
    assert out.name == rec.validation_id
    for fname in ("record.json", "methodology.json", "results.json", "checksum.sha256"):
        assert (out / fname).exists()
    checks = json.loads((out / "checksum.sha256").read_text())
    for fname, digest in checks["files"].items():
        assert hashlib.sha256((out / fname).read_bytes()).hexdigest() == digest
    rec_json = json.loads((out / "record.json").read_text())
    assert rec_json["phase"] == "5B"
    assert rec_json["results_digest"] == rec.results_digest


# --- Task 6 tests ---

def test_phase6_guard_blocks_duplicate(tmp_path):
    from scripts.msrp.run_forward_vol_validation import phase6_guard
    d = tmp_path / "someid"; d.mkdir()
    (d / "record.json").write_text(json.dumps({"phase": "6"}), encoding="utf-8")
    (d / "results.json").write_text(
        json.dumps({"results": {"evaluation_window": ["2026-01-01", "2026-07-03"]}}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError):
        phase6_guard(tmp_path, ("2026-01-01", "2026-07-03"))


def test_phase6_guard_allows_new_window(tmp_path):
    from scripts.msrp.run_forward_vol_validation import phase6_guard
    phase6_guard(tmp_path, ("2026-01-01", "2026-07-03"))


def test_two_independent_instances_reproduce_digest():
    h1 = _harness(_scored(sep=True, seed=5))
    h2 = _harness(_scored(sep=True, seed=5))
    assert h1.run().results_digest == h2.run().results_digest
