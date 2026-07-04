from dataclasses import dataclass
from datetime import datetime

from .market_state import MarketState


@dataclass(frozen=True)
class KnowledgeObject:
    """KnowledgeObject DTO (MSI-005 §11).

    Runtime-exposed representation of Market State consumed by strategies.
    Carries no standalone scalar Confidence or Uncertainty per MSI-5D-03.
    """

    knowledge_id: str
    evaluation_timestamp: datetime
    artifact_version: str
    runtime_version: str
    market_state: MarketState
    provenance_reference: str