from abc import ABC, abstractmethod

from ..contracts.artifact import PublishedArtifact
from ..contracts.knowledge import KnowledgeObject
from ..contracts.market_state import MarketState


class KnowledgeBuilder(ABC):
    """KnowledgeBuilder interface (MSI-005 §11).

    Construct KnowledgeObject from MarketState + provenance metadata.
    Conforms to MSI-005 §11 schema; no standalone scalar Confidence/Uncertainty.
    """

    @abstractmethod
    def build(
        self, market_state: MarketState, artifact: PublishedArtifact, provenance_chain: object
    ) -> KnowledgeObject:
        """Construct a KnowledgeObject conforming to MSI-005 §11. Deterministic ID.

        Args:
            market_state: Collection of Estimates from artifact evaluation.
            artifact: PublishedArtifact evaluated to produce MarketState.
            provenance_chain: Complete provenance chain from Observations to Knowledge.

        Returns:
            KnowledgeObject with deterministic ID, no scalar confidence.

        Raises:
            KnowledgeBuildError: Construction failed or schema violation.
        """
        ...