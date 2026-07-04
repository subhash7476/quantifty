"""DefaultKnowledgeBuilder — MSI-005 §11 KnowledgeObject construction."""

import hashlib
from datetime import datetime
from typing import Dict, List, Tuple

from ..contracts.artifact import PublishedArtifact
from ..contracts.knowledge import KnowledgeObject
from ..contracts.market_state import MarketState
from ..interfaces.knowledge_builder import KnowledgeBuilder
from .errors import KnowledgeBuildError
from .provenance import ProvenanceChain

_RUNTIME_VERSION = "msi-v1.0"


def _make_knowledge_id(
    artifact_version: str,
    evaluation_timestamp: datetime,
    estimates: Tuple,
) -> str:
    """Deterministic SHA-256 knowledge ID."""
    parts: List[str] = [
        artifact_version,
        evaluation_timestamp.isoformat(),
    ]
    for est in estimates:
        parts.extend([
            str(est.latent_variable),
            str(est.value),
            str(est.uncertainty),
            str(est.dimension),
        ])
    content = "|".join(parts)
    return hashlib.sha256(content.encode()).hexdigest()


class DefaultKnowledgeBuilder(KnowledgeBuilder):
    """Default KnowledgeBuilder (MSI-005 §11).

    Constructs immutable KnowledgeObject from MarketState + Artifact +
    ProvenanceChain. Deterministic: identical inputs produce identical
    knowledge_id and KnowledgeObject.
    """

    def __init__(self, runtime_version: str = _RUNTIME_VERSION):
        self._runtime_version = runtime_version

    def build(
        self,
        market_state: MarketState,
        artifact: PublishedArtifact,
        provenance_chain: ProvenanceChain,
    ) -> KnowledgeObject:
        """Construct a KnowledgeObject (MSI-005 §11). Deterministic ID.

        Args:
            market_state: Evaluated MarketState from artifact evaluation.
            artifact: PublishedArtifact that produced the MarketState.
            provenance_chain: Complete provenance chain.

        Returns:
            Immutable KnowledgeObject with deterministic knowledge_id.

        Raises:
            KnowledgeBuildError: Construction failed.
        """
        if not isinstance(market_state, MarketState):
            raise KnowledgeBuildError(
                f"Expected MarketState, got {type(market_state).__name__}"
            )
        if not isinstance(provenance_chain, ProvenanceChain):
            raise KnowledgeBuildError(
                "provenance_chain must be a ProvenanceChain instance"
            )

        estimates = market_state.estimates

        knowledge_id = _make_knowledge_id(
            artifact_version=artifact.metadata.artifact_version,
            evaluation_timestamp=market_state.evaluation_timestamp,
            estimates=estimates,
        )

        provenance_chain = ProvenanceChain(
            observation_ids=provenance_chain.observation_ids,
            evidence_ids=provenance_chain.evidence_ids,
            artifact_id=provenance_chain.artifact_id,
            artifact_version=provenance_chain.artifact_version,
            validation_id=provenance_chain.validation_id,
            knowledge_id=knowledge_id,
        )

        return KnowledgeObject(
            knowledge_id=knowledge_id,
            evaluation_timestamp=market_state.evaluation_timestamp,
            artifact_version=artifact.metadata.artifact_version,
            runtime_version=self._runtime_version,
            market_state=market_state,
            provenance_reference=knowledge_id,
        )
