from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple

from .evidence import Evidence
from .market_state import MarketState


@dataclass(frozen=True)
class ArtifactMetadata:
    """ArtifactMetadata DTO (MSI-007 §7).

    Runtime binding metadata for a Published MSI Artifact.
    Immutable; complete provenance and compatibility information.
    """

    artifact_id: str
    artifact_version: str
    schema_version: str
    validation_id: str
    publication_timestamp: datetime
    compatibility_version: str
    runtime_compatibility: str
    provenance_reference: str


class PublishedArtifact(ABC):
    """PublishedArtifact protocol (MSI-007 §11).

    Opaque executable object; runtime never inspects internals.
    Defines the contract between Research (artifact) and Platform (runtime).
    """

    metadata: ArtifactMetadata

    @abstractmethod
    def get_evidence_rules(self) -> Dict[str, object]:
        """Return validated evidence-construction rules (MSI-004 §2).

        Returns:
            Artifact-carried rules for constructing Evidence from Observations.
        """
        ...

    @abstractmethod
    def evaluate(self, evidence: Tuple[Evidence, ...]) -> MarketState:
        """Evaluate artifact against Evidence to produce MarketState (MSI-005 §7).

        Deterministic evaluation; identical inputs produce identical outputs.

        Args:
            evidence: Evidence objects constructed from Observations.

        Returns:
            MarketState containing Estimates of Latent Variables.
        """
        ...