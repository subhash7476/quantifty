"""DRAOrchestrator — MSI-009 §5–6 stateless pipeline coordinator."""

from datetime import date
from typing import Tuple

from ..contracts.artifact import PublishedArtifact
from ..contracts.evidence import Evidence
from ..contracts.knowledge import KnowledgeObject
from ..contracts.observation import Observation
from ..interfaces.artifact_evaluator import ArtifactEvaluator
from ..interfaces.artifact_loader import ArtifactLoader
from ..interfaces.evidence_builder import EvidenceBuilder
from ..interfaces.knowledge_builder import KnowledgeBuilder
from ..interfaces.knowledge_publisher import KnowledgePublisher
from ..interfaces.observation_reader import ObservationReader
from .provenance import ProvenanceChain


class DRAOrchestrator:
    """DRAOrchestrator (MSI-009 §5–6).

    Stateless pipeline coordinator. Wires the complete DRA pipeline:
    Observation → Evidence → Evaluation → Knowledge → Publication.
    """

    def __init__(
        self,
        observation_reader: ObservationReader,
        evidence_builder: EvidenceBuilder,
        artifact_loader: ArtifactLoader,
        artifact_evaluator: ArtifactEvaluator,
        knowledge_builder: KnowledgeBuilder,
        knowledge_publisher: KnowledgePublisher,
    ):
        self._observation_reader = observation_reader
        self._evidence_builder = evidence_builder
        self._artifact_loader = artifact_loader
        self._artifact_evaluator = artifact_evaluator
        self._knowledge_builder = knowledge_builder
        self._knowledge_publisher = knowledge_publisher

    def run(self, evaluation_date: date, artifact_ref: str) -> KnowledgeObject:
        """Execute the complete DRA pipeline for one evaluation date.

        Pipeline:
            1. Load + validate artifact (MSI-007/008)
            2. Read observations for required symbols (MSI-003)
            3. Construct evidence from artifact rules (MSI-004)
            4. Evaluate artifact → MarketState (MSI-005)
            5. Build provenance chain
            6. Build KnowledgeObject (MSI-005 §11)
            7. Publish Knowledge (MSI-005 §6)

        Args:
            evaluation_date: Date to evaluate.
            artifact_ref: Artifact identifier or path.

        Returns:
            KnowledgeObject with complete provenance chain.

        Raises:
            ArtifactLoadError: Artifact not found, incompatible, or not Active.
            ObservationReadError: Required data unavailable.
            EvidenceConstructionError: Artifact rules cannot be applied.
            EvaluationError: Artifact evaluation failed.
        """
        artifact = self._artifact_loader.load(artifact_ref)

        rules = artifact.get_evidence_rules()
        required_symbols = self._extract_required_symbols(rules)

        observations = self._observation_reader.read(
            evaluation_date, required_symbols
        )

        evidence = self._evidence_builder.build(observations, artifact)

        market_state = self._artifact_evaluator.evaluate(evidence, artifact)

        provenance_chain = self._build_provenance_chain(
            observations, evidence, artifact
        )

        knowledge = self._knowledge_builder.build(
            market_state, artifact, provenance_chain
        )

        self._knowledge_publisher.publish(knowledge)

        return knowledge

    def _extract_required_symbols(self, rules: dict) -> Tuple[str, ...]:
        symbols = rules.get("required_symbols", [])
        if not symbols:
            return ("NSE_INDEX|Nifty 50",)
        return tuple(symbols)

    def _build_provenance_chain(
        self,
        observations: Tuple[Observation, ...],
        evidence: Tuple[Evidence, ...],
        artifact: PublishedArtifact,
    ) -> ProvenanceChain:
        return ProvenanceChain(
            observation_ids=tuple(o.observation_id for o in observations),
            evidence_ids=tuple(e.evidence_id for e in evidence),
            artifact_id=artifact.metadata.artifact_id,
            artifact_version=artifact.metadata.artifact_version,
            validation_id=artifact.metadata.validation_id,
            knowledge_id="",
        )
