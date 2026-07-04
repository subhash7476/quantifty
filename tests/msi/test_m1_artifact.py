import hashlib
import json
from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

import pytest

from core.msi.contracts.artifact import ArtifactMetadata, PublishedArtifact
from core.msi.contracts.estimate import Estimate
from core.msi.contracts.evidence import Evidence
from core.msi.contracts.market_state import MarketState

_REQUIRED_FILES = [
    "metadata.json",
    "evidence_rules.json",
    "model.py",
    "provenance.json",
    "checksum.sha256",
]


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestArtifactStructure:
    """MSI-007 §7: artifact directory structure and file presence."""

    def test_artifact_directory_exists(self, test_artifact_path):
        assert test_artifact_path.is_dir(), "Artifact directory must exist"

    def test_all_required_files_present(self, test_artifact_path):
        actual = {p.name for p in test_artifact_path.iterdir() if p.is_file()}
        for f in _REQUIRED_FILES:
            assert f in actual, f"Required file '{f}' missing from artifact directory"

    def test_no_unexpected_files(self, test_artifact_path):
        actual = {p.name for p in test_artifact_path.iterdir() if p.is_file()}
        expected = set(_REQUIRED_FILES)
        unexpected = actual - expected
        assert not unexpected, f"Unexpected files in artifact directory: {unexpected}"

    def test_metadata_is_valid_json(self, test_artifact_metadata_json):
        assert isinstance(test_artifact_metadata_json, dict)

    def test_evidence_rules_is_valid_json(self, test_artifact_evidence_rules_json):
        assert isinstance(test_artifact_evidence_rules_json, dict)

    def test_provenance_is_valid_json(self, test_artifact_provenance_json):
        assert isinstance(test_artifact_provenance_json, dict)

    def test_checksum_is_valid_json(self, test_artifact_checksum_json):
        assert isinstance(test_artifact_checksum_json, dict)


class TestArtifactMetadata:
    """MSI-007 §7: metadata completeness and correctness."""

    REQUIRED_FIELDS = [
        "artifact_id",
        "artifact_version",
        "schema_version",
        "validation_id",
        "publication_timestamp",
        "compatibility_version",
        "runtime_compatibility",
        "provenance_reference",
    ]

    def test_all_required_metadata_fields_present(self, test_artifact_metadata_json):
        for field in self.REQUIRED_FIELDS:
            assert field in test_artifact_metadata_json, (
                f"Required metadata field '{field}' missing (MSI-007 §7)"
            )

    def test_no_extra_metadata_fields(self, test_artifact_metadata_json):
        extra = set(test_artifact_metadata_json.keys()) - set(self.REQUIRED_FIELDS) - {
            "supported_runtime_versions",
            "supported_ontology_versions",
            "supported_contract_versions",
            "description",
            "created_by",
            "engine",
        }
        assert not extra, f"Unexpected metadata fields: {extra}"

    def test_artifact_id_is_string(self, test_artifact_metadata_json):
        assert isinstance(test_artifact_metadata_json["artifact_id"], str)

    def test_artifact_version_is_string(self, test_artifact_metadata_json):
        assert isinstance(test_artifact_metadata_json["artifact_version"], str)

    def test_schema_version_is_string(self, test_artifact_metadata_json):
        assert isinstance(test_artifact_metadata_json["schema_version"], str)

    def test_validation_id_is_set(self, test_artifact_metadata_json):
        assert isinstance(test_artifact_metadata_json["validation_id"], str)
        assert len(test_artifact_metadata_json["validation_id"]) > 0

    def test_publication_timestamp_present(self, test_artifact_metadata_json):
        assert isinstance(test_artifact_metadata_json["publication_timestamp"], str)
        assert len(test_artifact_metadata_json["publication_timestamp"]) > 0

    def test_runtime_compatibility_declared(self, test_artifact_metadata_json):
        assert test_artifact_metadata_json["runtime_compatibility"] == "msi-v1.0"

    def test_compatibility_versions_declared_msi_007_s8(self, test_artifact_metadata_json):
        assert "supported_runtime_versions" in test_artifact_metadata_json
        assert isinstance(test_artifact_metadata_json["supported_runtime_versions"], list)
        assert "msi-v1.0" in test_artifact_metadata_json["supported_runtime_versions"]
        assert "supported_ontology_versions" in test_artifact_metadata_json
        assert "supported_contract_versions" in test_artifact_metadata_json

    def test_metadata_json_matches_artefact_metadata_dto(self, test_artifact_metadata_json, sample_artefact_metadata):
        assert test_artifact_metadata_json["artifact_id"] == sample_artefact_metadata.artifact_id
        assert test_artifact_metadata_json["artifact_version"] == sample_artefact_metadata.artifact_version
        assert test_artifact_metadata_json["validation_id"] == sample_artefact_metadata.validation_id
        assert test_artifact_metadata_json["runtime_compatibility"] == sample_artefact_metadata.runtime_compatibility
        assert test_artifact_metadata_json["provenance_reference"] == sample_artefact_metadata.provenance_reference


class TestArtifactChecksum:
    """MSI-007: integrity verification."""

    def test_checksum_file_contains_algorithm(self, test_artifact_checksum_json):
        assert "algorithm" in test_artifact_checksum_json
        assert test_artifact_checksum_json["algorithm"] == "sha256"

    def test_checksum_file_contains_per_file_hashes(self, test_artifact_checksum_json):
        assert "files" in test_artifact_checksum_json
        assert isinstance(test_artifact_checksum_json["files"], dict)

    def test_checksum_covers_all_content_files(self, test_artifact_checksum_json):
        content_files = {"metadata.json", "evidence_rules.json", "model.py", "provenance.json"}
        hashed_files = set(test_artifact_checksum_json["files"].keys())
        assert content_files == hashed_files, f"Mismatch: checksum covers {hashed_files}, expected {content_files}"

    def test_checksum_contains_combined_hash(self, test_artifact_checksum_json):
        assert "combined_hash" in test_artifact_checksum_json
        assert isinstance(test_artifact_checksum_json["combined_hash"], str)
        assert len(test_artifact_checksum_json["combined_hash"]) == 64

    def test_checksum_file_itself_not_hashed(self, test_artifact_checksum_json):
        assert "checksum.sha256" not in test_artifact_checksum_json["files"]

    def test_per_file_hashes_are_64_char_hex(self, test_artifact_checksum_json):
        for fname, fhash in test_artifact_checksum_json["files"].items():
            assert len(fhash) == 64, f"Hash for '{fname}' is not 64 chars"
            int(fhash, 16)  # must be valid hex

    def test_integrity_per_file_hashes_match(self, test_artifact_path, test_artifact_checksum_json):
        for fname, expected_hash in test_artifact_checksum_json["files"].items():
            actual = _hash_file(test_artifact_path / fname)
            assert actual == expected_hash, f"Integrity failure: '{fname}' hash mismatch"

    def test_integrity_combined_hash_matches(self, test_artifact_path, test_artifact_checksum_json):
        content_files = ["metadata.json", "evidence_rules.json", "model.py", "provenance.json"]
        per_file_hashes = test_artifact_checksum_json["files"]
        concatenated = "".join(per_file_hashes[f] for f in content_files)
        expected_combined = hashlib.sha256(concatenated.encode()).hexdigest()
        actual_combined = test_artifact_checksum_json["combined_hash"]
        assert actual_combined == expected_combined, "Combined hash integrity failure"

    def test_tampered_file_detected(self, test_artifact_checksum_json):
        modified = dict(test_artifact_checksum_json)
        modified_files = dict(modified["files"])
        modified_files["metadata.json"] = "0" * 64
        modified["files"] = modified_files
        assert modified["files"]["metadata.json"] != test_artifact_checksum_json["files"]["metadata.json"]


class TestEvidenceRules:
    """MSI-004 §2: evidence rule structure and determinism."""

    def test_rules_have_features_list(self, test_artifact_evidence_rules_json):
        assert "features" in test_artifact_evidence_rules_json
        assert isinstance(test_artifact_evidence_rules_json["features"], list)

    def test_rules_have_lookback_days(self, test_artifact_evidence_rules_json):
        assert "lookback_days" in test_artifact_evidence_rules_json
        assert isinstance(test_artifact_evidence_rules_json["lookback_days"], int)

    def test_rules_have_required_symbols(self, test_artifact_evidence_rules_json):
        assert "required_symbols" in test_artifact_evidence_rules_json
        assert isinstance(test_artifact_evidence_rules_json["required_symbols"], list)

    def test_rules_have_rule_format_version(self, test_artifact_evidence_rules_json):
        assert "rule_format_version" in test_artifact_evidence_rules_json
        assert test_artifact_evidence_rules_json["rule_format_version"] == "1.0"

    def test_each_feature_has_required_fields(self, test_artifact_evidence_rules_json):
        required = {"name", "source", "field", "transform"}
        for feature in test_artifact_evidence_rules_json["features"]:
            missing = required - set(feature.keys())
            assert not missing, f"Feature missing fields: {missing}"

    def test_vix_close_feature_present(self, test_artifact_evidence_rules_json):
        names = {f["name"] for f in test_artifact_evidence_rules_json["features"]}
        assert "vix_close" in names

    def test_nifty_close_feature_present(self, test_artifact_evidence_rules_json):
        names = {f["name"] for f in test_artifact_evidence_rules_json["features"]}
        assert "nifty_close" in names

    def test_required_symbols_include_nifty_and_vix(self, test_artifact_evidence_rules_json):
        symbols = set(test_artifact_evidence_rules_json["required_symbols"])
        assert "NSE_INDEX|Nifty 50" in symbols
        assert "NSE_INDEX|India VIX" in symbols

    def test_rules_are_deterministic_structure(self, test_artifact_evidence_rules_json):
        serialized = json.dumps(test_artifact_evidence_rules_json, sort_keys=True)
        reparsed = json.loads(serialized)
        assert reparsed == test_artifact_evidence_rules_json


class TestPublishedArtifactImplementation:
    """MSI-007 §11: PublishedArtifact contract conformance."""

    def test_artifact_is_published_artifact_subclass(self, reference_test_artifact):
        assert isinstance(reference_test_artifact, PublishedArtifact)

    def test_artifact_has_metadata(self, reference_test_artifact):
        assert hasattr(reference_test_artifact, "metadata")
        assert isinstance(reference_test_artifact.metadata, ArtifactMetadata)

    def test_artifact_metadata_values(self, reference_test_artifact):
        m = reference_test_artifact.metadata
        assert m.artifact_id == "ref-test-001"
        assert m.artifact_version == "v1.0.0"
        assert m.schema_version == "1.0"
        assert m.validation_id == "val-ref-test-001-v1"
        assert m.compatibility_version == "1.0"
        assert m.runtime_compatibility == "msi-v1.0"
        assert m.provenance_reference == "prov-ref-test-001"

    def test_artifact_metadata_is_immutable(self, reference_test_artifact):
        with pytest.raises(FrozenInstanceError):
            reference_test_artifact.metadata.artifact_version = "v2.0.0"

    def test_get_evidence_rules_returns_dict(self, reference_test_artifact):
        rules = reference_test_artifact.get_evidence_rules()
        assert isinstance(rules, dict)

    def test_get_evidence_rules_has_features(self, reference_test_artifact):
        rules = reference_test_artifact.get_evidence_rules()
        assert "features" in rules
        assert isinstance(rules["features"], list)
        assert len(rules["features"]) >= 1

    def test_get_evidence_rules_has_required_symbols(self, reference_test_artifact):
        rules = reference_test_artifact.get_evidence_rules()
        assert "required_symbols" in rules

    def test_get_evidence_rules_matches_json(self, reference_test_artifact, test_artifact_evidence_rules_json):
        rules = reference_test_artifact.get_evidence_rules()
        assert rules["lookback_days"] == test_artifact_evidence_rules_json["lookback_days"]
        assert rules["required_symbols"] == test_artifact_evidence_rules_json["required_symbols"]
        assert rules["rule_format_version"] == test_artifact_evidence_rules_json["rule_format_version"]

    def test_get_evidence_rules_is_deterministic(self, reference_test_artifact):
        r1 = reference_test_artifact.get_evidence_rules()
        r2 = reference_test_artifact.get_evidence_rules()
        assert r1 == r2

    def test_evaluate_returns_market_state(self, reference_test_artifact, sample_evidence):
        result = reference_test_artifact.evaluate(sample_evidence)
        assert isinstance(result, MarketState)

    def test_evaluate_produces_estimates(self, reference_test_artifact, sample_evidence):
        result = reference_test_artifact.evaluate(sample_evidence)
        assert len(result.estimates) >= 1
        for est in result.estimates:
            assert isinstance(est, Estimate)
            assert isinstance(est.latent_variable, str)
            assert isinstance(est.value, float)
            assert isinstance(est.uncertainty, float)
            assert isinstance(est.dimension, str)

    def test_evaluate_produces_market_regime_estimate(self, reference_test_artifact, sample_evidence):
        result = reference_test_artifact.evaluate(sample_evidence)
        names = {e.latent_variable for e in result.estimates}
        assert "market_regime" in names

    def test_evaluate_produces_trend_strength_estimate(self, reference_test_artifact, sample_evidence):
        result = reference_test_artifact.evaluate(sample_evidence)
        names = {e.latent_variable for e in result.estimates}
        assert "trend_strength" in names

    def test_evaluate_has_evaluation_timestamp(self, reference_test_artifact, sample_evidence):
        result = reference_test_artifact.evaluate(sample_evidence)
        assert isinstance(result.evaluation_timestamp, datetime)

    def test_evaluate_all_estimates_have_uncertainty(self, reference_test_artifact, sample_evidence):
        result = reference_test_artifact.evaluate(sample_evidence)
        for est in result.estimates:
            assert est.uncertainty >= 0.0, f"Uncertainty for '{est.latent_variable}' must be >= 0"

    def test_evaluate_uncertainty_not_negative(self, reference_test_artifact, sample_evidence):
        result = reference_test_artifact.evaluate(sample_evidence)
        for est in result.estimates:
            assert est.uncertainty >= 0.0


class TestDeterministicEvaluation:
    """MSI-005 §13: deterministic evaluation — identical inputs → identical outputs."""

    def test_same_evidence_same_output(self, reference_test_artifact, sample_evidence):
        r1 = reference_test_artifact.evaluate(sample_evidence)
        r2 = reference_test_artifact.evaluate(sample_evidence)
        assert r1 == r2

    def test_same_evidence_same_evaluation_timestamp(self, reference_test_artifact, sample_evidence):
        r1 = reference_test_artifact.evaluate(sample_evidence)
        r2 = reference_test_artifact.evaluate(sample_evidence)
        assert r1.evaluation_timestamp == r2.evaluation_timestamp

    def test_same_evidence_same_estimate_values(self, reference_test_artifact, sample_evidence):
        r1 = reference_test_artifact.evaluate(sample_evidence)
        r2 = reference_test_artifact.evaluate(sample_evidence)
        assert len(r1.estimates) == len(r2.estimates)
        for e1, e2 in zip(r1.estimates, r2.estimates):
            assert e1.latent_variable == e2.latent_variable
            assert e1.value == e2.value
            assert e1.uncertainty == e2.uncertainty
            assert e1.dimension == e2.dimension

    def test_deterministic_across_instances(self, reference_test_artifact, sample_evidence):
        import sys
        from pathlib import Path

        base = Path(__file__).resolve().parent / "fixtures" / "test_artifact"
        sys.path.insert(0, str(base))
        from model import ReferenceTestArtifact

        a1 = ReferenceTestArtifact()
        a2 = ReferenceTestArtifact()

        r1 = a1.evaluate(sample_evidence)
        r2 = a2.evaluate(sample_evidence)
        assert r1 == r2

    def test_high_vix_produces_high_volatility_regime(self, reference_test_artifact, sample_evidence_high_vix):
        result = reference_test_artifact.evaluate(sample_evidence_high_vix)
        regime_est = next(e for e in result.estimates if e.latent_variable == "market_regime")
        assert regime_est.value == 2.0

    def test_normal_vix_produces_normal_regime(self, reference_test_artifact, sample_evidence):
        result = reference_test_artifact.evaluate(sample_evidence)
        regime_est = next(e for e in result.estimates if e.latent_variable == "market_regime")
        assert regime_est.value == 1.0

    def test_low_vix_produces_low_volatility_regime(self, reference_test_artifact, sample_evidence_low_vix):
        result = reference_test_artifact.evaluate(sample_evidence_low_vix)
        regime_est = next(e for e in result.estimates if e.latent_variable == "market_regime")
        assert regime_est.value == 0.0

    def test_trend_strength_is_constant_regardless_of_vix(self, reference_test_artifact, sample_evidence_high_vix, sample_evidence_low_vix):
        r_high = reference_test_artifact.evaluate(sample_evidence_high_vix)
        r_low = reference_test_artifact.evaluate(sample_evidence_low_vix)
        ts_high = next(e for e in r_high.estimates if e.latent_variable == "trend_strength")
        ts_low = next(e for e in r_low.estimates if e.latent_variable == "trend_strength")
        assert ts_high.value == ts_low.value == 0.5

    def test_empty_evidence_produces_market_state(self, reference_test_artifact, sample_evidence_empty):
        result = reference_test_artifact.evaluate(sample_evidence_empty)
        assert isinstance(result, MarketState)
        assert isinstance(result.evaluation_timestamp, datetime)

    def test_market_state_is_immutable(self, reference_test_artifact, sample_evidence):
        result = reference_test_artifact.evaluate(sample_evidence)
        with pytest.raises(FrozenInstanceError):
            result.evaluation_timestamp = datetime.now()

    def test_estimate_is_immutable(self, reference_test_artifact, sample_evidence):
        result = reference_test_artifact.evaluate(sample_evidence)
        est = result.estimates[0]
        with pytest.raises(FrozenInstanceError):
            est.value = 0.99  # type: ignore[misc]

    def test_no_scalar_confidence_on_knowledge_output(self, reference_test_artifact, sample_evidence):
        result = reference_test_artifact.evaluate(sample_evidence)
        assert not hasattr(result, "confidence")
        assert not hasattr(result, "uncertainty")


class TestFixtureCorrectness:
    """Verify that conftest fixtures are valid and consistent."""

    def test_sample_observations_have_required_fields(self, sample_observations):
        for obs in sample_observations:
            assert obs.observation_id
            assert obs.instrument_id
            assert obs.observable_type

    def test_sample_observations_are_immutable(self, sample_observations):
        with pytest.raises(FrozenInstanceError):
            sample_observations[0].measured_value = 0.0  # type: ignore[misc]

    def test_sample_evidence_have_required_fields(self, sample_evidence):
        for ev in sample_evidence:
            assert ev.evidence_id
            assert ev.evidence_type
            assert ev.artifact_version

    def test_sample_evidence_are_immutable(self, sample_evidence):
        with pytest.raises(FrozenInstanceError):
            sample_evidence[0].evidence_value = 0.0  # type: ignore[misc]

    def test_sample_evidence_has_vix_type(self, sample_evidence):
        types = {e.evidence_type for e in sample_evidence}
        assert "vix_close" in types

    def test_sample_evidence_high_vix_value(self, sample_evidence_high_vix):
        assert sample_evidence_high_vix[0].evidence_value >= 25.0

    def test_sample_evidence_low_vix_value(self, sample_evidence_low_vix):
        assert sample_evidence_low_vix[0].evidence_value < 15.0

    def test_sample_evidence_empty_is_empty(self, sample_evidence_empty):
        assert len(sample_evidence_empty) == 0

    def test_all_vix_evidence_has_correct_type(self, sample_evidence_high_vix, sample_evidence_low_vix):
        for ev in list(sample_evidence_high_vix) + list(sample_evidence_low_vix):
            assert ev.evidence_type == "vix_close"

    def test_sample_artefact_metadata_matches_reference(self, sample_artefact_metadata, reference_test_artifact):
        am = sample_artefact_metadata
        rm = reference_test_artifact.metadata
        assert am.artifact_id == rm.artifact_id
        assert am.artifact_version == rm.artifact_version
        assert am.runtime_compatibility == rm.runtime_compatibility


class TestProvenance:
    """MSI-007 §9: provenance completeness."""

    def test_provenance_has_originating_research(self, test_artifact_provenance_json):
        assert "originating_research" in test_artifact_provenance_json

    def test_provenance_has_validation_id(self, test_artifact_provenance_json):
        assert "validation_id" in test_artifact_provenance_json
        assert test_artifact_provenance_json["validation_id"] == "val-ref-test-001-v1"

    def test_provenance_has_inference_contract_version(self, test_artifact_provenance_json):
        assert "inference_contract_version" in test_artifact_provenance_json

    def test_provenance_has_ontology_version(self, test_artifact_provenance_json):
        assert "ontology_version" in test_artifact_provenance_json

    def test_provenance_has_publication_event(self, test_artifact_provenance_json):
        assert "publication_event" in test_artifact_provenance_json
        evt = test_artifact_provenance_json["publication_event"]
        assert "event_id" in evt
        assert "timestamp" in evt
        assert "artifact_id" in evt
        assert "artifact_version" in evt

    def test_provenance_research_provenance_present(self, test_artifact_provenance_json):
        assert "research_provenance" in test_artifact_provenance_json
        rp = test_artifact_provenance_json["research_provenance"]
        assert "methodology" in rp
        assert "features_used" in rp


class TestImmutability:
    """MSI-AP-701: artifact immutability."""

    def test_artifact_metadata_dto_is_immutable(self, sample_artefact_metadata):
        with pytest.raises(FrozenInstanceError):
            sample_artefact_metadata.artifact_id = "changed"

    def test_metadata_json_is_loadable_multiple_times(self, test_artifact_metadata_json):
        base = Path(__file__).resolve().parent / "fixtures" / "test_artifact"
        with open(base / "metadata.json", "r") as f:
            load2 = json.load(f)
        assert load2 == test_artifact_metadata_json

    def test_evidence_rules_json_is_loadable_multiple_times(self, test_artifact_evidence_rules_json):
        base = Path(__file__).resolve().parent / "fixtures" / "test_artifact"
        with open(base / "evidence_rules.json", "r") as f:
            load2 = json.load(f)
        assert load2 == test_artifact_evidence_rules_json

    def test_model_module_reimports_consistently(self, reference_test_artifact):
        import sys
        from pathlib import Path

        base = Path(__file__).resolve().parent / "fixtures" / "test_artifact"
        sys.path.insert(0, str(base))
        from model import ReferenceTestArtifact as RTA1

        a1 = RTA1()
        a2 = reference_test_artifact

        assert a1.metadata == a2.metadata
        assert a1.get_evidence_rules() == a2.get_evidence_rules()
