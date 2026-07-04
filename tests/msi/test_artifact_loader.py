import json
import shutil
from pathlib import Path

import pytest

from core.msi.dra.errors import (
    ArtifactIncompatibleError,
    ArtifactIntegrityError,
    ArtifactLoadError,
    ArtifactNotFoundError,
    ArtifactNotActiveError,
    ArtifactNotValidatedError,
)
from core.msi.dra.filesystem_artifact_loader import FilesystemArtifactLoader
from core.msi.contracts.artifact import ArtifactMetadata, PublishedArtifact

_TEST_ARTIFACT = (
    Path(__file__).resolve().parent
    / "fixtures" / "test_artifact"
)

_MODEL_PY_HEADER = """
from datetime import datetime
from typing import Dict, Tuple
from core.msi.contracts.artifact import ArtifactMetadata, PublishedArtifact
from core.msi.contracts.estimate import Estimate
from core.msi.contracts.evidence import Evidence
from core.msi.contracts.market_state import MarketState

_METADATA = ArtifactMetadata(
    artifact_id="test-artifact",
    artifact_version="v1.0.0",
    schema_version="1.0",
    validation_id="val-test",
    publication_timestamp=datetime(2026, 7, 4, 12, 0, 0),
    compatibility_version="1.0",
    runtime_compatibility="msi-v1.0",
    provenance_reference="prov-test",
)
"""


def _copy_artifact(dst: Path) -> Path:
    dst = dst / "test_artifact"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(_TEST_ARTIFACT, dst)
    return dst


def _write_metadata(dst: Path, overrides: dict) -> None:
    meta_path = dst / "metadata.json"
    with open(meta_path, "r") as f:
        data = json.load(f)
    data.update(overrides)
    with open(meta_path, "w") as f:
        json.dump(data, f, indent=2)


def _write_model(dst: Path, source: str) -> None:
    model_path = dst / "model.py"
    with open(model_path, "w") as f:
        f.write(source)


def _make_checksum(path: Path) -> dict:
    import hashlib

    files = ["metadata.json", "evidence_rules.json", "model.py", "provenance.json"]
    hashes = {}
    for f in files:
        hashes[f] = hashlib.sha256((path / f).read_bytes()).hexdigest()
    combined = hashlib.sha256("".join(hashes[f] for f in files).encode()).hexdigest()
    result = {"algorithm": "sha256", "files": hashes, "combined_hash": combined}
    with open(path / "checksum.sha256", "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    return result


class TestFilesystemArtifactLoader:
    """FilesystemArtifactLoader tests (MSI-007, MSI-009 §13)."""

    def test_load_valid_artifact(self):
        """Load the M1 reference test artifact successfully."""
        loader = FilesystemArtifactLoader()
        artifact = loader.load(str(_TEST_ARTIFACT))
        assert isinstance(artifact, PublishedArtifact)
        assert isinstance(artifact.metadata, ArtifactMetadata)
        assert artifact.metadata.artifact_id == "ref-test-001"
        assert artifact.metadata.artifact_version == "v1.0.0"
        assert callable(artifact.get_evidence_rules)
        assert callable(artifact.evaluate)

    def test_load_returns_opaque_handle(self):
        """Returned artifact is an opaque PublishedArtifact handle."""
        loader = FilesystemArtifactLoader()
        artifact = loader.load(str(_TEST_ARTIFACT))
        assert type(artifact).__name__ == "ReferenceTestArtifact"
        assert isinstance(artifact.get_evidence_rules(), dict)
        assert hasattr(artifact, "metadata")

    def test_load_artifact_not_found(self):
        """Non-existent directory raises ArtifactNotFoundError."""
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactNotFoundError):
            loader.load("/nonexistent/artifact/path")

    def test_load_missing_metadata(self, tmp_path):
        """Missing metadata.json raises ArtifactNotFoundError."""
        dst = _copy_artifact(tmp_path)
        (dst / "metadata.json").unlink()
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactNotFoundError):
            loader.load(str(dst))

    def test_load_missing_checksum(self, tmp_path):
        """Missing checksum.sha256 raises ArtifactNotFoundError."""
        dst = _copy_artifact(tmp_path)
        (dst / "checksum.sha256").unlink()
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactNotFoundError):
            loader.load(str(dst))

    def test_load_missing_provenance(self, tmp_path):
        """Missing provenance.json raises ArtifactNotFoundError."""
        dst = _copy_artifact(tmp_path)
        (dst / "provenance.json").unlink()
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactNotFoundError):
            loader.load(str(dst))

    def test_load_missing_evidence_rules(self, tmp_path):
        """Missing evidence_rules.json raises ArtifactNotFoundError."""
        dst = _copy_artifact(tmp_path)
        (dst / "evidence_rules.json").unlink()
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactNotFoundError):
            loader.load(str(dst))

    def test_load_missing_model(self, tmp_path):
        """Missing model.py raises ArtifactNotFoundError."""
        dst = _copy_artifact(tmp_path)
        (dst / "model.py").unlink()
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactNotFoundError):
            loader.load(str(dst))

    def test_load_invalid_metadata_json(self, tmp_path):
        """Malformed metadata.json raises ArtifactLoadError."""
        dst = _copy_artifact(tmp_path)
        with open(dst / "metadata.json", "w") as f:
            f.write("not valid json")
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactLoadError):
            loader.load(str(dst))

    def test_load_metadata_missing_field(self, tmp_path):
        """metadata.json missing artifact_id raises ArtifactLoadError."""
        dst = _copy_artifact(tmp_path)
        _write_metadata(dst, {"artifact_id": None, "artifact_version": None})
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactLoadError):
            loader.load(str(dst))

    def test_load_incompatible_runtime_version(self, tmp_path):
        """Incompatible runtime version raises ArtifactIncompatibleError."""
        dst = _copy_artifact(tmp_path)
        _write_metadata(dst, {
            "supported_runtime_versions": ["msi-v2.0"],
        })
        loader = FilesystemArtifactLoader(runtime_version="msi-v1.0")
        with pytest.raises(ArtifactIncompatibleError):
            loader.load(str(dst))

    def test_load_incompatible_ontology_version(self, tmp_path):
        """Incompatible ontology version raises ArtifactIncompatibleError."""
        dst = _copy_artifact(tmp_path)
        _write_metadata(dst, {
            "supported_ontology_versions": ["2.0"],
        })
        loader = FilesystemArtifactLoader(ontology_version="1.0")
        with pytest.raises(ArtifactIncompatibleError):
            loader.load(str(dst))

    def test_load_incompatible_contract_version(self, tmp_path):
        """Incompatible contract version raises ArtifactIncompatibleError."""
        dst = _copy_artifact(tmp_path)
        _write_metadata(dst, {
            "supported_contract_versions": ["2.0"],
        })
        loader = FilesystemArtifactLoader(contract_version="1.0")
        with pytest.raises(ArtifactIncompatibleError):
            loader.load(str(dst))

    def test_load_not_active(self, tmp_path):
        """Non-Active lifecycle_state raises ArtifactNotActiveError."""
        dst = _copy_artifact(tmp_path)
        _write_metadata(dst, {"lifecycle_state": "Retired"})
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactNotActiveError):
            loader.load(str(dst))

    def test_load_not_validated(self, tmp_path):
        """Non-Approved validation_status raises ArtifactNotValidatedError."""
        dst = _copy_artifact(tmp_path)
        _write_metadata(dst, {"validation_status": "Failed"})
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactNotValidatedError):
            loader.load(str(dst))

    def test_load_active_absent_allows(self, tmp_path):
        """Absent lifecycle_state (as in M1 artifact) passes Active check."""
        dst = _copy_artifact(tmp_path)
        meta = json.loads((dst / "metadata.json").read_text())
        assert "lifecycle_state" not in meta
        loader = FilesystemArtifactLoader()
        artifact = loader.load(str(dst))
        assert isinstance(artifact, PublishedArtifact)

    def test_load_validated_absent_allows(self, tmp_path):
        """Absent validation_status (as in M1 artifact) passes validation check."""
        dst = _copy_artifact(tmp_path)
        meta = json.loads((dst / "metadata.json").read_text())
        assert "validation_status" not in meta
        loader = FilesystemArtifactLoader()
        artifact = loader.load(str(dst))
        assert isinstance(artifact, PublishedArtifact)

    def test_load_checksum_mismatch(self, tmp_path):
        """Tampered artifact raises ArtifactIntegrityError."""
        dst = _copy_artifact(tmp_path)
        (dst / "provenance.json").write_text('{"tampered": true}')
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactIntegrityError):
            loader.load(str(dst))

    def test_load_invalid_checksum_json(self, tmp_path):
        """Malformed checksum.sha256 raises ArtifactIntegrityError."""
        dst = _copy_artifact(tmp_path)
        with open(dst / "checksum.sha256", "w") as f:
            f.write("not valid json")
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactIntegrityError):
            loader.load(str(dst))

    def test_load_checksum_wrong_algorithm(self, tmp_path):
        """Non-sha256 algorithm raises ArtifactIntegrityError."""
        dst = _copy_artifact(tmp_path)
        with open(dst / "checksum.sha256", "w") as f:
            json.dump({"algorithm": "md5", "files": {}}, f)
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactIntegrityError):
            loader.load(str(dst))

    def test_load_no_artifact_class(self, tmp_path):
        """model.py without PublishedArtifact subclass raises ArtifactLoadError."""
        dst = _copy_artifact(tmp_path)
        _write_model(dst, _MODEL_PY_HEADER + """
class NotAnArtifact:
    pass
""")
        _make_checksum(dst)
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactLoadError):
            loader.load(str(dst))

    def test_load_artifact_missing_abstract_methods(self, tmp_path):
        """PublishedArtifact subclass missing get_evidence_rules raises."""
        dst = _copy_artifact(tmp_path)
        _write_model(dst, _MODEL_PY_HEADER + f"""

class IncompleteArtifact(PublishedArtifact):
    metadata = _METADATA
""")
        _make_checksum(dst)
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactLoadError):
            loader.load(str(dst))

    def test_load_artifact_instantiation_raises(self, tmp_path):
        """PublishedArtifact where __init__ raises, load fails."""
        dst = _copy_artifact(tmp_path)
        _write_model(dst, _MODEL_PY_HEADER + """

class BadArtifact(PublishedArtifact):
    metadata = _METADATA

    def get_evidence_rules(self):
        return {}

    def evaluate(self, evidence):
        raise RuntimeError("evaluate failed")

    def __init__(self):
        raise RuntimeError("instantiation failed")
""")
        _make_checksum(dst)
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactLoadError):
            loader.load(str(dst))

    def test_load_absent_runtime_versions(self, tmp_path):
        """Absent supported_runtime_versions raises ArtifactIncompatibleError (fail-closed)."""
        dst = _copy_artifact(tmp_path)
        _write_metadata(dst, {"supported_runtime_versions": None})
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactIncompatibleError):
            loader.load(str(dst))

    def test_load_absent_ontology_versions(self, tmp_path):
        """Absent supported_ontology_versions raises ArtifactIncompatibleError (fail-closed)."""
        dst = _copy_artifact(tmp_path)
        _write_metadata(dst, {"supported_ontology_versions": None})
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactIncompatibleError):
            loader.load(str(dst))

    def test_load_absent_contract_versions(self, tmp_path):
        """Absent supported_contract_versions raises ArtifactIncompatibleError (fail-closed)."""
        dst = _copy_artifact(tmp_path)
        _write_metadata(dst, {"supported_contract_versions": None})
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactIncompatibleError):
            loader.load(str(dst))

    def test_load_multiple_artifact_classes(self, tmp_path):
        """model.py with multiple PublishedArtifact subclasses raises."""
        dst = _copy_artifact(tmp_path)
        _write_model(dst, _MODEL_PY_HEADER + """

class FirstArtifact(PublishedArtifact):
    metadata = _METADATA
    def get_evidence_rules(self): return {}
    def evaluate(self, evidence): return None

class SecondArtifact(PublishedArtifact):
    metadata = _METADATA
    def get_evidence_rules(self): return {}
    def evaluate(self, evidence): return None
""")
        _make_checksum(dst)
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactLoadError):
            loader.load(str(dst))

    def test_load_artifact_wrong_metadata_type(self, tmp_path):
        """PublishedArtifact where metadata is not ArtifactMetadata raises."""
        dst = _copy_artifact(tmp_path)
        _write_model(dst, _MODEL_PY_HEADER + """

class WrongMetadataArtifact(PublishedArtifact):
    metadata = "not_an_artifact_metadata"

    def get_evidence_rules(self):
        return {}

    def evaluate(self, evidence):
        from core.msi.contracts.estimate import Estimate
        from core.msi.contracts.market_state import MarketState
        from datetime import datetime
        return MarketState(
            evaluation_timestamp=datetime(2026, 7, 4, 12, 0, 0),
            estimates=(Estimate("x", 1.0, 0.1, "dim"),),
        )
""")
        _make_checksum(dst)
        loader = FilesystemArtifactLoader()
        with pytest.raises(ArtifactLoadError):
            loader.load(str(dst))

    def test_deterministic_loading(self):
        """Loading the same artifact twice returns equivalent instances."""
        loader = FilesystemArtifactLoader()
        a1 = loader.load(str(_TEST_ARTIFACT))
        a2 = loader.load(str(_TEST_ARTIFACT))
        assert a1.metadata == a2.metadata
        assert a1.get_evidence_rules() == a2.get_evidence_rules()

    def test_deterministic_different_loader_instance(self):
        """Different loader instances loading same artifact produce identical results."""
        l1 = FilesystemArtifactLoader()
        l2 = FilesystemArtifactLoader()
        a1 = l1.load(str(_TEST_ARTIFACT))
        a2 = l2.load(str(_TEST_ARTIFACT))
        assert a1.metadata == a2.metadata
        assert a1.get_evidence_rules() == a2.get_evidence_rules()

    def test_metadata_immutability(self):
        """Returned artifact metadata is frozen."""
        loader = FilesystemArtifactLoader()
        artifact = loader.load(str(_TEST_ARTIFACT))
        from dataclasses import FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            artifact.metadata.artifact_id = "changed"

    def test_loader_is_subclass_of_abc(self):
        """FilesystemArtifactLoader satisfies the ArtifactLoader ABC."""
        from core.msi.interfaces.artifact_loader import ArtifactLoader
        assert issubclass(FilesystemArtifactLoader, ArtifactLoader)

    def test_loader_implements_load_method(self):
        """FilesystemArtifactLoader has a callable load method."""
        loader = FilesystemArtifactLoader()
        assert callable(loader.load)

    def test_load_multiple_times_same_instance(self):
        """Same loader instance can load an artifact multiple times."""
        loader = FilesystemArtifactLoader()
        a1 = loader.load(str(_TEST_ARTIFACT))
        a2 = loader.load(str(_TEST_ARTIFACT))
        assert a1.metadata == a2.metadata
        assert a1.get_evidence_rules() == a2.get_evidence_rules()

    def test_load_artifact_id_consistency(self):
        """The artifact's metadata matches the known reference values."""
        loader = FilesystemArtifactLoader()
        artifact = loader.load(str(_TEST_ARTIFACT))
        m = artifact.metadata
        assert m.artifact_id == "ref-test-001"
        assert m.artifact_version == "v1.0.0"
        assert m.schema_version == "1.0"
        assert m.runtime_compatibility == "msi-v1.0"
        assert m.provenance_reference == "prov-ref-test-001"

    def test_evidence_rules_loaded(self):
        """get_evidence_rules returns the expected rules from the loaded artifact."""
        loader = FilesystemArtifactLoader()
        artifact = loader.load(str(_TEST_ARTIFACT))
        rules = artifact.get_evidence_rules()
        assert "features" in rules
        assert "required_symbols" in rules
        assert rules["rule_format_version"] == "1.0"

    def test_loaded_artifact_can_evaluate(self):
        """Loaded artifact's evaluate method works correctly."""
        loader = FilesystemArtifactLoader()
        artifact = loader.load(str(_TEST_ARTIFACT))
        from core.msi.contracts.evidence import Evidence
        from datetime import datetime
        ev = Evidence(
            evidence_id="ev_test",
            source_observation_ids=(),
            construction_timestamp=datetime(2026, 7, 4, 12, 0, 0),
            evidence_type="vix_close",
            evidence_value=18.5,
            artifact_version="v1.0.0",
            provenance_metadata={},
            quality_metadata={},
            version="1.0",
        )
        ms = artifact.evaluate((ev,))
        assert ms.evaluation_timestamp == datetime(2026, 7, 4, 12, 0, 0)
        regime = next(e for e in ms.estimates if e.latent_variable == "market_regime")
        assert regime.value == 1.0  # normal regime for VIX=18.5
