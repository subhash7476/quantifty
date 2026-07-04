from abc import ABC, abstractmethod

from ..contracts.artifact import PublishedArtifact


class ArtifactLoader(ABC):
    """ArtifactLoader interface (MSI-007 §7–8, MSI-008 §9).

    Load, validate, and verify a Published MSI Artifact.
    Checks compatibility, Active status, validation, integrity.
    """

    @abstractmethod
    def load(self, artifact_ref: str) -> PublishedArtifact:
        """Load and validate an artifact. Returns opaque PublishedArtifact handle.

        Checks:
            - Compatibility (MSI-007 §8)
            - Active status (MSI-008 §9)
            - Validation (MSI-006)
            - Integrity (checksum)

        Args:
            artifact_ref: Artifact identifier or path.

        Returns:
            Validated PublishedArtifact handle.

        Raises:
            ArtifactLoadError: Artifact not found, incompatible, not Active, or invalid.
        """
        ...