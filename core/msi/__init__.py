"""Market State Intelligence (MSI) Package.

Runtime implementation of the MSI Architecture (MSI-001 through MSI-009).
Provides contracts, interfaces, and the Daily Regime Analyzer (DRA).

Contracts (core/msi/contracts/):
    Frozen DTOs implementing MSI ontology entities.

Interfaces (core/msi/interfaces/):
    Abstract base classes defining component contracts.

DRA (core/msi/dra/):
    Concrete implementations of MSI-009 Runtime Pipeline.

Tag: msi-v1.0
"""

from .contracts import (
    Observation,
    Evidence,
    Estimate,
    MarketState,
    KnowledgeObject,
    ArtifactMetadata,
    PublishedArtifact,
)

from .interfaces import (
    ObservationReader,
    EvidenceBuilder,
    ArtifactLoader,
    ArtifactEvaluator,
    KnowledgeBuilder,
    KnowledgePublisher,
)

__all__ = [
    "Observation",
    "Evidence",
    "Estimate",
    "MarketState",
    "KnowledgeObject",
    "ArtifactMetadata",
    "PublishedArtifact",
    "ObservationReader",
    "EvidenceBuilder",
    "ArtifactLoader",
    "ArtifactEvaluator",
    "KnowledgeBuilder",
    "KnowledgePublisher",
]