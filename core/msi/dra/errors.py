"""DRA exception hierarchy (MSI-009 §16)."""


class DRAError(Exception):
    """Base exception for all DRA errors."""


class ObservationReadError(DRAError):
    """Data unavailable or insufficient lookback."""


class ArtifactLoadError(DRAError):
    """Base exception for artifact loading failures."""


class ArtifactNotFoundError(ArtifactLoadError):
    """Artifact directory or required file not found."""


class ArtifactIncompatibleError(ArtifactLoadError):
    """Artifact version incompatible with runtime."""


class ArtifactNotActiveError(ArtifactLoadError):
    """Artifact lifecycle state is not Active."""


class ArtifactNotValidatedError(ArtifactLoadError):
    """Artifact validation has not been approved."""


class ArtifactIntegrityError(ArtifactLoadError):
    """Artifact checksum or content integrity check failed."""


class EvidenceConstructionError(DRAError):
    """Evidence construction rules cannot be applied."""


class EvaluationError(DRAError):
    """Artifact evaluation failed."""


class KnowledgeBuildError(DRAError):
    """KnowledgeObject construction or schema failure."""


class KnowledgePublishError(DRAError):
    """DuckDB write failed during knowledge publication."""


class KnowledgeRepositoryError(DRAError):
    """Knowledge repository operation failed."""
