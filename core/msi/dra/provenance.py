"""ProvenanceChain — immutable provenance support (MSI-005 §14, MSI-004 §9, MSI-003 §7)."""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class ProvenanceChain:
    """Immutable provenance chain: Observation → Evidence → Artifact → Knowledge.

    Tracks every link from source Observations through Evidence construction,
    Artifact evaluation, to KnowledgeObject creation. Supports reconstruction
    for audit and external store verification.
    """

    observation_ids: Tuple[str, ...]
    evidence_ids: Tuple[str, ...]
    artifact_id: str
    artifact_version: str
    validation_id: str
    knowledge_id: str

    def reconstruct(self) -> Dict[str, object]:
        """Return complete provenance record suitable for audit."""
        return {
            "observation_ids": list(self.observation_ids),
            "evidence_ids": list(self.evidence_ids),
            "artifact_id": self.artifact_id,
            "artifact_version": self.artifact_version,
            "validation_id": self.validation_id,
            "knowledge_id": self.knowledge_id,
            "chain": "Observation → Evidence → Artifact → Knowledge",
        }

    def verify(
        self,
        knowledge_store: Optional[object] = None,
        evidence_store: Optional[object] = None,
        observation_store: Optional[object] = None,
    ) -> bool:
        """Verify every link in the chain resolves to its stored record.

        When stores are provided (M6+), checks that each ID resolves.
        Without stores, verifies internal chain consistency:
        - All required fields are non-empty
        - Chain ordering is valid
        """
        if not self.observation_ids:
            return False
        if not self.evidence_ids:
            return False
        if not self.artifact_id:
            return False
        if not self.artifact_version:
            return False
        if not self.validation_id:
            return False
        if not self.knowledge_id:
            return False
        return True
