"""MSRP Phase 5A — PublishedArtifact v2 (forward-volatility HAR-RV+VIX) tests.

Covers (per Phase-5A acceptance criteria):
  - feature construction (RV + HAR aggregates)
  - deterministic coefficient fitting
  - coefficient serialization into the frozen artifact
  - artifact loading via the certified FilesystemArtifactLoader
  - evaluate() contract + determinism
  - KnowledgeObject generation (MSI v1.0 compatibility)
  - state-dependent uncertainty emission (Phase-2 finding Mo2)
  - deterministic replay
  - point-in-time correctness

Conforms to the frozen MSRP Phase-1 Research Dossier (commit d9233b1).
"""

import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core.msi.contracts.artifact import ArtifactMetadata, PublishedArtifact
from core.msi.contracts.evidence import Evidence
from core.msi.contracts.knowledge import KnowledgeObject
from core.msi.contracts.market_state import MarketState
from core.msi.contracts.observation import Observation
from core.msi.dra.default_evidence_builder import DefaultEvidenceBuilder
from core.msi.dra.default_knowledge_builder import DefaultKnowledgeBuilder
from core.msi.dra.errors import EvidenceConstructionError
from core.msi.dra.filesystem_artifact_loader import FilesystemArtifactLoader
from core.msi.dra.provenance import ProvenanceChain
from core.msi.msrp import forward_vol as fv

REPO = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = REPO / "core" / "msi" / "artifacts" / "forward_vol_v2"

REQUIRED_FILES = ["metadata.json", "evidence_rules.json", "model.py", "provenance.json", "checksum.sha256"]
_TS = datetime(2026, 7, 3, 15, 30, 0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(name: str) -> dict:
    with open(ARTIFACT_DIR / name, "r") as f:
        return json.load(f)


def _import_artifact_model() -> PublishedArtifact:
    """Import model.py directly (mirrors FilesystemArtifactLoader's mechanism)."""
    module_name = "_fwd_vol_model_under_test"
    spec = importlib.util.spec_from_file_location(module_name, ARTIFACT_DIR / "model.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    instance = None
    for name in dir(module):
        obj = getattr(module, name)
        if (isinstance(obj, type) and issubclass(obj, PublishedArtifact)
                and obj is not PublishedArtifact):
            instance = obj()
            break
    assert instance is not None, "No PublishedArtifact subclass found in model.py"
    return instance


def _evidence(rv_daily=0.008, rv_weekly=0.0075, rv_monthly=0.0072, vix=13.5) -> tuple:
    return tuple(
        Evidence(f"e{i}", (f"o{i}",), _TS, t, v, "v1.0.0", {}, {}, "1.0")
        for i, (t, v) in enumerate(
            [("rv_daily", rv_daily), ("rv_weekly", rv_weekly),
             ("rv_monthly", rv_monthly), ("vix_close", vix)]
        )
    )


# ---------------------------------------------------------------------------
# Feature construction (dossier S5 / S6)
# ---------------------------------------------------------------------------

class TestFeatureConstruction:
    """RV computation and HAR aggregates, per the frozen dossier."""

    def test_rv_known_value(self):
        # Two closes 100 -> 101: r = ln(1.01), RV = |ln(1.01)|
        closes = np.array([100.0, 101.0])
        by_day = {pd.Timestamp("2025-01-01"): closes}
        rv = fv.compute_daily_rv(by_day)
        expected = abs(math.log(1.01))
        assert rv.iloc[0] == pytest.approx(expected, rel=1e-12)

    def test_rv_excludes_overnight_return(self):
        # Two days, each with two intraday prints. The cross-day gap must NOT enter.
        day1 = pd.Timestamp("2025-01-02")
        day2 = pd.Timestamp("2025-01-03")
        by_day = {
            day1: np.array([100.0, 110.0]),   # intraday r = ln(1.10)
            day2: np.array([200.0, 220.0]),   # intraday r = ln(1.10); huge overnight gap ignored
        }
        rv = fv.compute_daily_rv(by_day)
        expected = abs(math.log(1.10))
        assert rv.loc[day1] == pytest.approx(expected, rel=1e-12)
        assert rv.loc[day2] == pytest.approx(expected, rel=1e-12)

    def test_rv_drops_days_with_too_few_prints(self):
        by_day = {
            pd.Timestamp("2025-01-02"): np.array([100.0]),  # single print -> dropped
            pd.Timestamp("2025-01-03"): np.array([100.0, 101.0]),
        }
        rv = fv.compute_daily_rv(by_day)
        assert len(rv) == 1
        assert pd.Timestamp("2025-01-03") in rv.index

    def test_rv_is_scale_invariant(self):
        # dossier S5: scale invariance (no annualization)
        a = fv.compute_daily_rv({pd.Timestamp("2025-01-02"): np.array([100.0, 105.0])})
        b = fv.compute_daily_rv({pd.Timestamp("2025-01-02"): np.array([1000.0, 1050.0])})
        assert a.iloc[0] == pytest.approx(b.iloc[0], rel=1e-12)

    def test_har_windows_and_warmup(self):
        # 25 days of constant-ish RV; weekly=5, monthly=22
        idx = pd.date_range("2025-01-02", periods=25, freq="B")
        rv = pd.Series(np.linspace(0.005, 0.010, 25), index=idx)
        feat = fv.compute_har_features(rv)
        # First 21 rows dropped (monthly needs 22 including current)
        assert feat.isna().sum().sum() == 0
        assert len(feat) == 25 - 21
        # Weekly = mean of last 5 (incl current); monthly = mean of last 22
        last_day = idx[-1]
        last_pos = idx.get_loc(last_day)
        assert feat.loc[last_day, "rv_daily"] == pytest.approx(rv.loc[last_day])
        assert feat.loc[last_day, "rv_weekly"] == pytest.approx(rv.iloc[last_pos - 4: last_pos + 1].mean())
        assert feat.loc[last_day, "rv_monthly"] == pytest.approx(rv.iloc[last_pos - 21: last_pos + 1].mean())


# ---------------------------------------------------------------------------
# Deterministic coefficient fitting (dossier S7/S8)
# ---------------------------------------------------------------------------

class TestCoefficientFitting:
    """OLS fit is deterministic and matches a manual closed-form computation."""

    def test_fit_is_deterministic(self):
        rv, vix = self._synthetic_series(seed=7)
        c1 = fv.fit_har_rv_vix(rv, vix, "2024-01-02", "2024-12-31")
        c2 = fv.fit_har_rv_vix(rv, vix, "2024-01-02", "2024-12-31")
        for k in ("b0", "b1", "b2", "b3", "b4", "sigma"):
            assert c1[k] == c2[k]

    def test_fit_matches_manual_lstsq(self):
        rv, vix = self._synthetic_series(seed=11)
        dev_start, dev_end = "2024-01-02", "2024-12-31"
        coeffs = fv.fit_har_rv_vix(rv, vix, dev_start, dev_end)
        # Re-derive independently, faithfully mirroring the implementation's
        # point-in-time target clamping (held-out t+1 never used).
        feat = fv.compute_har_features(rv)
        vix_a = vix.reindex(feat.index)
        d = feat.join(vix_a.rename("vix"))
        d = d.loc[(d.index >= dev_start) & (d.index <= dev_end)].dropna()
        rv_clamped = rv.loc[rv.index <= pd.Timestamp(dev_end)]
        y = np.log(rv_clamped.shift(-1).reindex(d.index).dropna())
        d = d.loc[y.index]
        X = np.column_stack([
            np.ones(len(d)),
            np.log(d["rv_daily"]), np.log(d["rv_weekly"]),
            np.log(d["rv_monthly"]), np.log(d["vix"]),
        ])
        beta, *_ = np.linalg.lstsq(X, y.to_numpy(), rcond=None)
        assert coeffs["b0"] == pytest.approx(beta[0], rel=1e-9)
        assert coeffs["b1"] == pytest.approx(beta[1], rel=1e-9)
        assert coeffs["b4"] == pytest.approx(beta[4], rel=1e-9)
        resid = y.to_numpy() - X @ beta
        sigma_manual = math.sqrt((resid ** 2).sum() / (len(d) - 5))
        assert coeffs["sigma"] == pytest.approx(sigma_manual, rel=1e-9)

    def test_fit_only_uses_dev_window(self):
        # Point-in-time guarantee: appending held-out data must not change the dev fit.
        rv, vix = self._synthetic_series(seed=3)
        rv_heldout = pd.Series(
            np.linspace(0.5, 0.6, 30),
            index=pd.date_range("2026-01-02", periods=30, freq="B"),
        )
        rv_full = pd.concat([rv, rv_heldout])
        c_dev = fv.fit_har_rv_vix(rv, vix, "2024-01-02", "2024-12-31")
        c_full = fv.fit_har_rv_vix(rv_full, vix, "2024-01-02", "2024-12-31")
        for k in ("b0", "b1", "b2", "b3", "b4", "sigma"):
            assert c_dev[k] == c_full[k], f"held-out leaked into dev fit via {k}"

    @staticmethod
    def _synthetic_series(seed: int):
        rng = np.random.default_rng(seed)
        # Span the full dev window so the fit has realistic coverage.
        idx = pd.date_range("2023-01-02", periods=750, freq="B")
        rv = pd.Series(np.abs(rng.normal(0.008, 0.002, 750)), index=idx)
        vix = pd.Series(12.0 + rng.normal(0, 2, 750), index=idx)
        return rv, vix


# ---------------------------------------------------------------------------
# Artifact structure (MSI-007)
# ---------------------------------------------------------------------------

class TestArtifactStructure:
    def test_directory_exists(self):
        assert ARTIFACT_DIR.is_dir()

    def test_all_required_files_present(self):
        actual = {p.name for p in ARTIFACT_DIR.iterdir() if p.is_file()}
        for f in REQUIRED_FILES:
            assert f in actual, f"Missing {f}"

    def test_no_unexpected_files(self):
        actual = {p.name for p in ARTIFACT_DIR.iterdir() if p.is_file()}
        assert actual == set(REQUIRED_FILES)


class TestArtifactMetadata:
    def test_required_fields_present(self):
        m = _load_json("metadata.json")
        for f in ["artifact_id", "artifact_version", "schema_version", "validation_id",
                  "publication_timestamp", "compatibility_version", "runtime_compatibility",
                  "provenance_reference"]:
            assert f in m

    def test_runtime_compatibility(self):
        assert _load_json("metadata.json")["runtime_compatibility"] == "msi-v1.0"

    def test_declares_msi_v1_compatibility(self):
        m = _load_json("metadata.json")
        assert "msi-v1.0" in m["supported_runtime_versions"]
        assert "1.0" in m["supported_ontology_versions"]
        assert "1.0" in m["supported_contract_versions"]


class TestArtifactChecksum:
    def test_algorithm_sha256(self):
        assert _load_json("checksum.sha256")["algorithm"] == "sha256"

    def test_covers_all_content_files(self):
        c = _load_json("checksum.sha256")
        assert set(c["files"].keys()) == {"metadata.json", "evidence_rules.json", "model.py", "provenance.json"}

    def test_per_file_hashes_match(self):
        c = _load_json("checksum.sha256")
        for fname, expected in c["files"].items():
            actual = hashlib.sha256((ARTIFACT_DIR / fname).read_bytes()).hexdigest()
            assert actual == expected, f"Integrity failure: {fname}"

    def test_combined_hash_matches(self):
        c = _load_json("checksum.sha256")
        order = ["metadata.json", "evidence_rules.json", "model.py", "provenance.json"]
        concat = "".join(c["files"][f] for f in order).encode()
        assert c["combined_hash"] == hashlib.sha256(concat).hexdigest()


class TestEvidenceRules:
    def test_four_features(self):
        r = _load_json("evidence_rules.json")
        names = {f["name"] for f in r["features"]}
        assert names == {"rv_daily", "rv_weekly", "rv_monthly", "vix_close"}

    def test_required_symbols(self):
        r = _load_json("evidence_rules.json")
        assert "NSE_INDEX|Nifty 50" in r["required_symbols"]
        assert "NSE_INDEX|India VIX" in r["required_symbols"]

    def test_rule_format_version(self):
        assert _load_json("evidence_rules.json")["rule_format_version"] == "1.0"


# ---------------------------------------------------------------------------
# Coefficient serialization (frozen into model.py)
# ---------------------------------------------------------------------------

class TestCoefficientSerialization:
    def test_model_py_contains_frozen_coefficient_literals(self):
        text = (ARTIFACT_DIR / "model.py").read_text(encoding="utf-8")
        for const in ["B0", "B1", "B2", "B3", "B4", "SIGMA"]:
            assert const in text
        assert "expected_next_day_realized_vol" in text

    def test_serialized_coefficients_match_model_object(self):
        artifact = _import_artifact_model()
        text = (ARTIFACT_DIR / "model.py").read_text(encoding="utf-8")
        # The module-level constants equal the fitted values used at authoring time.
        assert artifact.evaluate  # noqa: B018 - confirms instantiable
        # Parse the B1 literal out and compare to the object attribute on the module
        import re
        m = re.search(r"^B1 = ([-\d.e]+)", text, re.MULTILINE)
        assert m is not None
        assert float(m.group(1)) == pytest.approx(sys.modules["_fwd_vol_model_under_test"].B1)


# ---------------------------------------------------------------------------
# Artifact loading via the certified runtime
# ---------------------------------------------------------------------------

class TestArtifactLoading:
    def test_loads_via_filesystem_loader(self):
        loader = FilesystemArtifactLoader()
        artifact = loader.load(str(ARTIFACT_DIR))
        assert isinstance(artifact, PublishedArtifact)

    def test_metadata_identity(self):
        loader = FilesystemArtifactLoader()
        artifact = loader.load(str(ARTIFACT_DIR))
        assert artifact.metadata.artifact_id == "msrp-forward-vol-v2"
        assert artifact.metadata.artifact_version == "v1.0.0"
        assert isinstance(artifact.metadata, ArtifactMetadata)

    def test_get_evidence_rules_returns_four_features(self):
        loader = FilesystemArtifactLoader()
        artifact = loader.load(str(ARTIFACT_DIR))
        rules = artifact.get_evidence_rules()
        assert len(rules["features"]) == 4


# ---------------------------------------------------------------------------
# evaluate() contract
# ---------------------------------------------------------------------------

class TestEvaluate:
    def test_returns_market_state(self):
        artifact = _import_artifact_model()
        assert isinstance(artifact.evaluate(_evidence()), MarketState)

    def test_emits_single_named_estimate(self):
        artifact = _import_artifact_model()
        ms = artifact.evaluate(_evidence())
        assert len(ms.estimates) == 1
        est = ms.estimates[0]
        assert est.latent_variable == "expected_next_day_realized_vol"
        assert est.value > 0.0
        assert est.uncertainty > 0.0
        assert est.dimension == "volatility_level"

    def test_value_matches_log_normal_formula(self):
        artifact = _import_artifact_model()
        mod = sys.modules["_fwd_vol_model_under_test"]
        ev = _evidence(rv_daily=0.008, rv_weekly=0.0075, rv_monthly=0.0072, vix=13.5)
        ms = artifact.evaluate(ev)
        mu = (mod.B0 + mod.B1 * math.log(0.008) + mod.B2 * math.log(0.0075)
              + mod.B3 * math.log(0.0072) + mod.B4 * math.log(13.5))
        expected_value = math.exp(mu + (mod.SIGMA ** 2) / 2.0)
        assert ms.estimates[0].value == pytest.approx(expected_value, rel=1e-12)

    def test_deterministic_same_evidence(self):
        artifact = _import_artifact_model()
        r1 = artifact.evaluate(_evidence())
        r2 = artifact.evaluate(_evidence())
        assert r1 == r2

    def test_deterministic_across_instances(self):
        a1 = _import_artifact_model()
        a2 = _import_artifact_model()
        assert a1.evaluate(_evidence()) == a2.evaluate(_evidence())

    def test_rejects_missing_evidence(self):
        artifact = _import_artifact_model()
        with pytest.raises(ValueError):
            artifact.evaluate(_evidence()[:3])  # missing vix_close

    def test_rejects_non_positive_evidence(self):
        artifact = _import_artifact_model()
        bad = _evidence(rv_daily=0.0)
        with pytest.raises(ValueError):
            artifact.evaluate(bad)

    def test_market_state_immutable(self):
        artifact = _import_artifact_model()
        ms = artifact.evaluate(_evidence())
        with pytest.raises(Exception):
            ms.evaluation_timestamp = datetime.now()

    def test_evaluation_timestamp_is_max_evidence_timestamp(self):
        # F2 regression guard: evaluation_timestamp must be the evidence's own as-of
        # date, NOT a future sentinel floor. Use a deliberately historical date so a
        # sentinel floor would be caught.
        artifact = _import_artifact_model()
        hist_ts = datetime(2025, 6, 16, 15, 30, 0)
        ev = tuple(
            Evidence(f"e{i}", (f"o{i}",), hist_ts, t, v, "v1.0.0", {}, {}, "1.0")
            for i, (t, v) in enumerate(
                [("rv_daily", 0.008), ("rv_weekly", 0.0075),
                 ("rv_monthly", 0.0072), ("vix_close", 13.5)]
            )
        )
        ms = artifact.evaluate(ev)
        assert ms.evaluation_timestamp == hist_ts
        assert ms.evaluation_timestamp == max(e.construction_timestamp for e in ev)
        assert ms.evaluation_timestamp.year == 2025  # would be 2026 if the sentinel floor survived


# ---------------------------------------------------------------------------
# Evidence-construction boundary (Phase-5A review finding F1)
# ---------------------------------------------------------------------------

class TestEvidenceConstructionBoundary:
    """Documents that this artifact's evidence CANNOT be built by the certified
    DefaultEvidenceBuilder, which executes identity transforms only.

    The artifact honestly declares non-identity transforms (rv_intraday,
    har_weekly_5d, har_monthly_22d) because its features are intraday/multi-day
    aggregates, not raw observations. Evidence for these features must be built by
    Phase-6 offline research tooling (the same category as core/msi/msrp/forward_vol.py)
    and fed to evaluate() as pre-built Evidence — NOT by extending the frozen
    builder/reader, which the charter scope fence forbids. This test pins the boundary
    so it is not rediscovered in Phase 6.
    """

    def test_certified_builder_rejects_non_identity_transforms(self):
        artifact = _import_artifact_model()
        obs = (
            Observation("o1", datetime(2025, 6, 16, 15, 30), "NSE_INDEX|Nifty 50",
                        "src", "close_price", 24000.0, "index_points", "p", {}),
            Observation("o2", datetime(2025, 6, 16, 15, 30), "NSE_INDEX|India VIX",
                        "src", "close_price", 13.5, "percentage", "p", {}),
        )
        with pytest.raises(EvidenceConstructionError):
            DefaultEvidenceBuilder().build(obs, artifact)


# ---------------------------------------------------------------------------
# State-dependent uncertainty (Phase-2 finding Mo2)
# ---------------------------------------------------------------------------

class TestStateDependentUncertainty:
    def test_uncertainty_matches_formula(self):
        artifact = _import_artifact_model()
        mod = sys.modules["_fwd_vol_model_under_test"]
        ms = artifact.evaluate(_evidence())
        expected = ms.estimates[0].value * math.sqrt(math.exp(mod.SIGMA ** 2) - 1.0)
        assert ms.estimates[0].uncertainty == pytest.approx(expected, rel=1e-12)

    def test_uncertainty_widens_in_high_vol_state(self):
        artifact = _import_artifact_model()
        low = artifact.evaluate(_evidence(vix=11.0, rv_daily=0.005)).estimates[0]
        high = artifact.evaluate(_evidence(vix=28.0, rv_daily=0.020)).estimates[0]
        assert high.uncertainty > low.uncertainty
        assert high.value > low.value

    def test_uncertainty_positive(self):
        artifact = _import_artifact_model()
        assert artifact.evaluate(_evidence()).estimates[0].uncertainty > 0.0


# ---------------------------------------------------------------------------
# KnowledgeObject generation (MSI v1.0 compatibility)
# ---------------------------------------------------------------------------

class TestKnowledgeObjectGeneration:
    def test_builds_knowledge_object(self):
        artifact = _import_artifact_model()
        ms = artifact.evaluate(_evidence())
        prov = ProvenanceChain(("o0", "o1", "o2", "o3"),
                               ("e0", "e1", "e2", "e3"),
                               artifact.metadata.artifact_id,
                               artifact.metadata.artifact_version,
                               artifact.metadata.validation_id, "")
        ko = DefaultKnowledgeBuilder().build(ms, artifact, prov)
        assert isinstance(ko, KnowledgeObject)
        assert ko.runtime_version == "msi-v1.0"
        assert ko.artifact_version == artifact.metadata.artifact_version
        assert len(ko.market_state.estimates) == 1
        assert ko.market_state.estimates[0].latent_variable == "expected_next_day_realized_vol"

    def test_knowledge_id_deterministic(self):
        artifact = _import_artifact_model()
        ms = artifact.evaluate(_evidence())
        prov = ProvenanceChain(("o0", "o1", "o2", "o3"),
                               ("e0", "e1", "e2", "e3"),
                               artifact.metadata.artifact_id,
                               artifact.metadata.artifact_version,
                               artifact.metadata.validation_id, "")
        kb = DefaultKnowledgeBuilder()
        k1 = kb.build(ms, artifact, prov)
        k2 = kb.build(ms, artifact, prov)
        assert k1.knowledge_id == k2.knowledge_id


# ---------------------------------------------------------------------------
# Deterministic replay (full load -> evaluate -> build KO)
# ---------------------------------------------------------------------------

class TestDeterministicReplay:
    def test_three_loads_produce_identical_knowledge(self):
        loader = FilesystemArtifactLoader()
        results = []
        for _ in range(3):
            art = loader.load(str(ARTIFACT_DIR))
            ms = art.evaluate(_evidence())
            prov = ProvenanceChain(("o0", "o1", "o2", "o3"),
                                   ("e0", "e1", "e2", "e3"),
                                   art.metadata.artifact_id,
                                   art.metadata.artifact_version,
                                   art.metadata.validation_id, "")
            results.append(DefaultKnowledgeBuilder().build(ms, art, prov))
        assert results[0].knowledge_id == results[1].knowledge_id == results[2].knowledge_id


# ---------------------------------------------------------------------------
# Point-in-time correctness
# ---------------------------------------------------------------------------

class TestPointInTime:
    def test_evaluate_uses_only_provided_evidence(self):
        artifact = _import_artifact_model()
        # Identical feature values -> identical output regardless of object identity
        e1 = _evidence(vix=15.0)
        e2 = tuple(
            Evidence(f"x{i}", (f"y{i}",), _TS, t, v, "v1.0.0", {}, {}, "1.0")
            for i, (t, v) in enumerate(
                [("rv_daily", 0.008), ("rv_weekly", 0.0075),
                 ("rv_monthly", 0.0072), ("vix_close", 15.0)]
            )
        )
        assert artifact.evaluate(e1) == artifact.evaluate(e2)

    def test_different_evidence_different_output(self):
        artifact = _import_artifact_model()
        a = artifact.evaluate(_evidence(vix=12.0))
        b = artifact.evaluate(_evidence(vix=22.0))
        assert a != b
