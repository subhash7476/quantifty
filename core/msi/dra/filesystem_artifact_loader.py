import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..contracts.artifact import ArtifactMetadata, PublishedArtifact
from ..interfaces.artifact_loader import ArtifactLoader
from .errors import (
    ArtifactIncompatibleError,
    ArtifactIntegrityError,
    ArtifactLoadError,
    ArtifactNotActiveError,
    ArtifactNotFoundError,
    ArtifactNotValidatedError,
)

_REQUIRED_FILES: Tuple[str, ...] = (
    "metadata.json",
    "evidence_rules.json",
    "model.py",
    "provenance.json",
    "checksum.sha256",
)

_REQUIRED_METADATA_FIELDS: Tuple[str, ...] = (
    "artifact_id",
    "artifact_version",
    "schema_version",
    "validation_id",
    "publication_timestamp",
    "compatibility_version",
    "runtime_compatibility",
    "provenance_reference",
)

_LIFECYCLE_ACTIVE = "Active"
_VALIDATION_APPROVED = "Approved"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FilesystemArtifactLoader(ArtifactLoader):
    """Filesystem-based PublishedArtifact loader (MSI-007 §7–8, MSI-009 §13).

    Resolves artifact_ref to a directory, validates structure, metadata,
    compatibility, checksum integrity, and returns a PublishedArtifact handle.
    """

    def __init__(
        self,
        runtime_version: str = "msi-v1.0",
        ontology_version: str = "1.0",
        contract_version: str = "1.0",
    ):
        self._runtime_version = runtime_version
        self._ontology_version = ontology_version
        self._contract_version = contract_version

    def load(self, artifact_ref: str) -> PublishedArtifact:
        """Load, validate, and return a PublishedArtifact (MSI-007 §11).

        Args:
            artifact_ref: Filesystem path to the artifact directory.

        Returns:
            Opaque PublishedArtifact handle.

        Raises:
            ArtifactNotFoundError: Artifact directory or required files missing.
            ArtifactIncompatibleError: Version mismatch with runtime.
            ArtifactNotActiveError: Artifact lifecycle state is not Active.
            ArtifactNotValidatedError: Artifact validation not approved.
            ArtifactIntegrityError: Checksum verification failed.
            ArtifactLoadError: Other loading or instantiation failures.
        """
        artifact_path = self._resolve_artifact_path(artifact_ref)
        self._verify_required_files(artifact_path)
        metadata = self._load_metadata(artifact_path)
        self._validate_metadata(metadata)
        self._validate_compatibility(metadata)
        self._validate_active_status(metadata)
        self._validate_validation_status(metadata)
        self._verify_checksum(artifact_path)
        module = self._import_model_module(artifact_path)
        artifact = self._instantiate_artifact(module, metadata)
        return artifact

    def _resolve_artifact_path(self, artifact_ref: str) -> Path:
        path = Path(artifact_ref).resolve()
        if not path.is_dir():
            raise ArtifactNotFoundError(
                f"Artifact directory not found: {artifact_ref}"
            )
        return path

    def _verify_required_files(self, path: Path) -> None:
        missing: List[str] = []
        for fname in _REQUIRED_FILES:
            if not (path / fname).is_file():
                missing.append(fname)
        if missing:
            raise ArtifactNotFoundError(
                f"Required artifact files missing: {', '.join(missing)}"
            )

    def _load_metadata(self, path: Path) -> dict:
        metadata_path = path / "metadata.json"
        try:
            with open(metadata_path, "r") as f:
                data: dict = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise ArtifactLoadError(
                f"Failed to parse metadata.json: {e}"
            ) from e
        if not isinstance(data, dict):
            raise ArtifactLoadError("metadata.json must contain a JSON object")
        return data

    def _validate_metadata(self, metadata: dict) -> None:
        missing = [f for f in _REQUIRED_METADATA_FIELDS if f not in metadata]
        if missing:
            raise ArtifactLoadError(
                f"metadata.json missing required fields (MSI-007 §7): "
                f"{', '.join(missing)}"
            )
        for field in ("artifact_id", "artifact_version"):
            if not isinstance(metadata.get(field), str) or not metadata[field]:
                raise ArtifactLoadError(
                    f"metadata.json '{field}' must be a non-empty string"
                )

    def _validate_compatibility(self, metadata: dict) -> None:
        """Validate MSI-007 §8 compatibility.

        Fail-closed: every supported_*_versions field must be present
        and include the runtime's expected version. Absent fields are
        rejected — the artifact must explicitly declare compatibility.
        """
        supported_runtime = metadata.get("supported_runtime_versions")
        if supported_runtime is None:
            raise ArtifactIncompatibleError(
                "metadata.json missing required field: "
                "supported_runtime_versions"
            )
        if self._runtime_version not in supported_runtime:
            raise ArtifactIncompatibleError(
                f"Runtime version '{self._runtime_version}' not in "
                f"supported_runtime_versions: {supported_runtime}"
            )

        supported_ontology = metadata.get("supported_ontology_versions")
        if supported_ontology is None:
            raise ArtifactIncompatibleError(
                "metadata.json missing required field: "
                "supported_ontology_versions"
            )
        if self._ontology_version not in supported_ontology:
            raise ArtifactIncompatibleError(
                f"Ontology version '{self._ontology_version}' not in "
                f"supported_ontology_versions: {supported_ontology}"
            )

        supported_contract = metadata.get("supported_contract_versions")
        if supported_contract is None:
            raise ArtifactIncompatibleError(
                "metadata.json missing required field: "
                "supported_contract_versions"
            )
        if self._contract_version not in supported_contract:
            raise ArtifactIncompatibleError(
                f"Inference contract version '{self._contract_version}' not in "
                f"supported_contract_versions: {supported_contract}"
            )

    def _validate_active_status(self, metadata: dict) -> None:
        status = metadata.get("lifecycle_state")
        if status is not None and status != _LIFECYCLE_ACTIVE:
            raise ArtifactNotActiveError(
                f"Artifact lifecycle_state is '{status}', expected 'Active'"
            )

    def _validate_validation_status(self, metadata: dict) -> None:
        status = metadata.get("validation_status")
        if status is not None and status != _VALIDATION_APPROVED:
            raise ArtifactNotValidatedError(
                f"Artifact validation_status is '{status}', expected 'Approved'"
            )

    def _verify_checksum(self, path: Path) -> None:
        checksum_path = path / "checksum.sha256"
        try:
            with open(checksum_path, "r") as f:
                checksum_data: dict = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise ArtifactIntegrityError(
                f"Failed to parse checksum.sha256: {e}"
            ) from e

        if not isinstance(checksum_data, dict):
            raise ArtifactIntegrityError("checksum.sha256 must contain a JSON object")
        if checksum_data.get("algorithm") != "sha256":
            raise ArtifactIntegrityError(
                f"Unsupported checksum algorithm: {checksum_data.get('algorithm')}"
            )

        file_hashes: dict = checksum_data.get("files", {})
        content_files = [f for f in _REQUIRED_FILES if f != "checksum.sha256"]

        for fname in content_files:
            expected = file_hashes.get(fname)
            if expected is None:
                raise ArtifactIntegrityError(
                    f"checksum.sha256 missing hash for '{fname}'"
                )
            file_path = path / fname
            try:
                actual = _sha256(file_path.read_bytes())
            except OSError as e:
                raise ArtifactIntegrityError(
                    f"Failed to read '{fname}' for checksum: {e}"
                ) from e
            if actual != expected:
                raise ArtifactIntegrityError(
                    f"Checksum mismatch for '{fname}': "
                    f"expected {expected}, got {actual}"
                )

        # Verify combined hash if present
        combined_expected = checksum_data.get("combined_hash")
        if combined_expected is not None:
            concatenated = "".join(file_hashes[f] for f in content_files)
            combined_actual = _sha256(concatenated.encode())
            if combined_actual != combined_expected:
                raise ArtifactIntegrityError(
                    f"Combined hash mismatch: "
                    f"expected {combined_expected}, got {combined_actual}"
                )

    def _import_model_module(self, path: Path) -> object:
        model_path = path / "model.py"
        module_name = f"_artifact_model_{path.name}"
        try:
            spec = importlib.util.spec_from_file_location(
                module_name, model_path
            )
            if spec is None or spec.loader is None:
                raise ArtifactLoadError(
                    f"Could not create import spec for model.py"
                )
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except ArtifactLoadError:
            raise
        except Exception as e:
            raise ArtifactLoadError(
                f"Failed to import model.py: {e}"
            ) from e
        return module

    def _instantiate_artifact(
        self, module: object, metadata: dict
    ) -> PublishedArtifact:
        candidates: List[PublishedArtifact] = []
        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, PublishedArtifact)
                and obj is not PublishedArtifact
            ):
                try:
                    instance = obj()
                    candidates.append(instance)
                except Exception as e:
                    raise ArtifactLoadError(
                        f"Failed to instantiate PublishedArtifact subclass "
                        f"'{name}': {e}"
                    ) from e

        if not candidates:
            raise ArtifactLoadError(
                "No instantiable PublishedArtifact subclass found in model.py"
            )
        if len(candidates) > 1:
            raise ArtifactLoadError(
                f"Multiple instantiable PublishedArtifact subclasses found "
                f"in model.py: {len(candidates)}"
            )

        artifact = candidates[0]

        try:
            _ = artifact.get_evidence_rules()
        except Exception as e:
            raise ArtifactLoadError(
                f"Artifact.get_evidence_rules() raised: {e}"
            ) from e

        if not isinstance(artifact.metadata, ArtifactMetadata):
            raise ArtifactLoadError(
                "Artifact.metadata is not an ArtifactMetadata instance"
            )

        return artifact
