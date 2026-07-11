"""Market State Intelligence (MSI) Package.

Runtime implementation of the MSI Architecture (MSI-001 through MSI-009).
Provides contracts, interfaces, and the Daily Regime Analyzer (DRA).

Contracts (core/msi/contracts/):
    Frozen DTOs implementing MSI ontology entities.
    MSI-002 §4.7: Estimate
    MSI-002 §4.8: MarketState
    MSI-003 §5:    Observation
    MSI-004 §7:    Evidence
    MSI-005 §11:   KnowledgeObject
    MSI-007 §7:    ArtifactMetadata
    MSI-007 §11:   PublishedArtifact

Interfaces (core/msi/interfaces/):
    Abstract base classes defining component contracts.
    MSI-003 §4:    ObservationReader
    MSI-004 §2/§5: EvidenceBuilder
    MSI-007 §7–8:  ArtifactLoader
    MSI-005 §7:    ArtifactEvaluator
    MSI-005 §11:   KnowledgeBuilder
    MSI-005 §6:    KnowledgePublisher

DRA (core/msi/dra/):
    Concrete implementations of MSI-009 Runtime Pipeline.
    See ``core.msi.dra.__init__`` for the full public API.

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

from .dra import (
    DefaultArtifactEvaluator,
    DefaultEvidenceBuilder,
    DefaultKnowledgeBuilder,
    DefaultKnowledgePublisher,
    DuckDBObservationReader,
    FilesystemArtifactLoader,
    KnowledgeRepository,
    DRAOrchestrator,
    ProvenanceChain,
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
    "DefaultArtifactEvaluator",
    "DefaultEvidenceBuilder",
    "DefaultKnowledgeBuilder",
    "DefaultKnowledgePublisher",
    "DuckDBObservationReader",
    "FilesystemArtifactLoader",
    "KnowledgeRepository",
    "DRAOrchestrator",
    "ProvenanceChain",
]