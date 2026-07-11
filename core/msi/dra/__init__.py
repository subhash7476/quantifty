"""DRA — Daily Regime Analyzer (MSI-009).

Reference implementation of the MSI Runtime Pipeline.

Components:
  DuckDBObservationReader      — MSI-003 §4 read-contract over DuckDB
  FilesystemArtifactLoader     — MSI-007 §7–8 filesystem-based artifact loading
  DefaultEvidenceBuilder       — MSI-004 §2/§5 evidence construction
  DefaultArtifactEvaluator     — MSI-005 §7 runtime evaluation engine
  DefaultKnowledgeBuilder      — MSI-005 §11 KnowledgeObject construction
  DefaultKnowledgePublisher    — MSI-005 §6 Knowledge publication
  KnowledgeRepository          — MSI-005 §6 in-memory KnowledgeObject store
  ProvenanceChain              — MSI-005 §14 immutable provenance chain
  DRAOrchestrator              — MSI-009 §5–6 stateless pipeline coordinator

Error Hierarchy (MSI-009 §16):
  DRAError, ObservationReadError, ArtifactLoadError,
  ArtifactNotFoundError, ArtifactIncompatibleError, ArtifactNotActiveError,
  ArtifactNotValidatedError, ArtifactIntegrityError,
  EvidenceConstructionError, EvaluationError,
  KnowledgeBuildError, KnowledgePublishError, KnowledgeRepositoryError

Tag: msi-v1.0
"""

from .default_artifact_evaluator import DefaultArtifactEvaluator
from .default_evidence_builder import DefaultEvidenceBuilder
from .default_knowledge_builder import DefaultKnowledgeBuilder
from .default_knowledge_publisher import DefaultKnowledgePublisher
from .duckdb_observation_reader import DuckDBObservationReader
from .filesystem_artifact_loader import FilesystemArtifactLoader
from .knowledge_repository import KnowledgeRepository
from .orchestrator import DRAOrchestrator
from .provenance import ProvenanceChain

__all__ = [
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
