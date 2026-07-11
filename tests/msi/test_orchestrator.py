"""DRAOrchestrator tests (MSI-009 §5–6)."""

from datetime import date, datetime
from typing import Tuple

import pytest

from core.msi.contracts.observation import Observation
from core.msi.contracts.knowledge import KnowledgeObject
from core.msi.dra.orchestrator import DRAOrchestrator
from core.msi.dra.default_evidence_builder import DefaultEvidenceBuilder
from core.msi.dra.default_artifact_evaluator import DefaultArtifactEvaluator
from core.msi.dra.default_knowledge_builder import DefaultKnowledgeBuilder
from core.msi.dra.default_knowledge_publisher import DefaultKnowledgePublisher
from core.msi.dra.knowledge_repository import KnowledgeRepository
from core.msi.dra.errors import (
    ArtifactIncompatibleError,
    ObservationReadError,
)
from core.msi.interfaces.observation_reader import ObservationReader

_TS = datetime(2026, 7, 3, 15, 30)

_FAKE_OBSERVATIONS = (
    Observation(
        observation_id="obs_n50_close",
        timestamp=_TS,
        instrument_id="NSE_INDEX|Nifty 50",
        source_reference="test",
        observable_type="close_price",
        measured_value=24850.75,
        measurement_units="index_points",
        provenance_ref="prov_test",
        quality_metadata={},
    ),
    Observation(
        observation_id="obs_vix_close",
        timestamp=_TS,
        instrument_id="NSE_INDEX|India VIX",
        source_reference="test",
        observable_type="close_price",
        measured_value=18.5,
        measurement_units="percentage",
        provenance_ref="prov_test",
        quality_metadata={},
    ),
)


class FakeObservationReader(ObservationReader):
    """Returns fixed observations for testing."""

    def __init__(self, fail_on_symbol: str = ""):
        self._fail_on_symbol = fail_on_symbol

    def read(
        self, evaluation_date: date, symbols: Tuple[str, ...]
    ) -> Tuple[Observation, ...]:
        for sym in symbols:
            if self._fail_on_symbol and sym == self._fail_on_symbol:
                raise ObservationReadError(
                    f"No data for symbol: {sym}"
                )
        return _FAKE_OBSERVATIONS


class TestDRAOrchestrator:
    """DRAOrchestrator pipeline integration tests (MSI-009 §5–6)."""

    def _make_orchestrator(
        self,
        artifact_loader,
        observation_reader=None,
    ) -> DRAOrchestrator:
        if observation_reader is None:
            observation_reader = FakeObservationReader()
        repo = KnowledgeRepository()
        publisher = DefaultKnowledgePublisher(repo)
        return DRAOrchestrator(
            observation_reader=observation_reader,
            evidence_builder=DefaultEvidenceBuilder(),
            artifact_loader=artifact_loader,
            artifact_evaluator=DefaultArtifactEvaluator(),
            knowledge_builder=DefaultKnowledgeBuilder(),
            knowledge_publisher=publisher,
        )

    def test_full_pipeline_success(self, test_artifact_path):
        """Full pipeline executes end-to-end with the M1 test artifact."""
        from core.msi.dra.filesystem_artifact_loader import (
            FilesystemArtifactLoader,
        )

        loader = FilesystemArtifactLoader()
        orchestrator = self._make_orchestrator(loader)
        result = orchestrator.run(
            evaluation_date=date(2026, 7, 3),
            artifact_ref=str(test_artifact_path),
        )
        assert isinstance(result, KnowledgeObject)
        assert result.knowledge_id
        assert len(result.knowledge_id) == 64
        assert result.artifact_version == "v1.0.0"
        assert result.runtime_version == "msi-v1.0"

    def test_full_pipeline_returns_market_state(self, test_artifact_path):
        """Resulting KnowledgeObject contains a MarketState with estimates."""
        from core.msi.dra.filesystem_artifact_loader import (
            FilesystemArtifactLoader,
        )

        loader = FilesystemArtifactLoader()
        orchestrator = self._make_orchestrator(loader)
        result = orchestrator.run(
            evaluation_date=date(2026, 7, 3),
            artifact_ref=str(test_artifact_path),
        )
        assert len(result.market_state.estimates) >= 1
        names = {e.latent_variable for e in result.market_state.estimates}
        assert "market_regime" in names

    def test_full_pipeline_deterministic(self, test_artifact_path):
        """Running the same pipeline twice produces identical knowledge_id."""
        from core.msi.dra.filesystem_artifact_loader import (
            FilesystemArtifactLoader,
        )

        loader = FilesystemArtifactLoader()
        r1 = self._make_orchestrator(loader).run(
            evaluation_date=date(2026, 7, 3),
            artifact_ref=str(test_artifact_path),
        )
        r2 = self._make_orchestrator(loader).run(
            evaluation_date=date(2026, 7, 3),
            artifact_ref=str(test_artifact_path),
        )
        assert r1.knowledge_id == r2.knowledge_id

    def test_pipeline_provenance_chain(self, test_artifact_path):
        """Provenance chain is populated from pipeline outputs."""
        from core.msi.dra.filesystem_artifact_loader import (
            FilesystemArtifactLoader,
        )

        loader = FilesystemArtifactLoader()
        orchestrator = self._make_orchestrator(loader)
        result = orchestrator.run(
            evaluation_date=date(2026, 7, 3),
            artifact_ref=str(test_artifact_path),
        )
        assert result.provenance_reference == result.knowledge_id

    def test_pipeline_fails_on_missing_data(self, test_artifact_path):
        """Missing observation data raises ObservationReadError."""
        from core.msi.dra.filesystem_artifact_loader import (
            FilesystemArtifactLoader,
        )

        loader = FilesystemArtifactLoader()
        failing_reader = FakeObservationReader(
            fail_on_symbol="NSE_INDEX|India VIX"
        )
        orchestrator = self._make_orchestrator(
            loader, observation_reader=failing_reader
        )
        with pytest.raises(ObservationReadError):
            orchestrator.run(
                evaluation_date=date(2026, 7, 3),
                artifact_ref=str(test_artifact_path),
            )

    def test_pipeline_fails_on_incompatible_artifact(
        self, test_artifact_path
    ):
        """Incompatible artifact version raises ArtifactIncompatibleError."""
        from core.msi.dra.filesystem_artifact_loader import (
            FilesystemArtifactLoader,
        )

        loader = FilesystemArtifactLoader(
            runtime_version="msi-v99.0"
        )
        orchestrator = self._make_orchestrator(loader)
        with pytest.raises(ArtifactIncompatibleError):
            orchestrator.run(
                evaluation_date=date(2026, 7, 3),
                artifact_ref=str(test_artifact_path),
            )

    def test_pipeline_no_partial_state_on_failure(
        self, test_artifact_path
    ):
        """When pipeline fails mid-way, no Knowledge is published."""
        from core.msi.dra.filesystem_artifact_loader import (
            FilesystemArtifactLoader,
        )

        loader = FilesystemArtifactLoader()
        failing_reader = FakeObservationReader(
            fail_on_symbol="NSE_INDEX|India VIX"
        )
        repo = KnowledgeRepository()
        publisher = DefaultKnowledgePublisher(repo)
        orchestrator = DRAOrchestrator(
            observation_reader=failing_reader,
            evidence_builder=DefaultEvidenceBuilder(),
            artifact_loader=loader,
            artifact_evaluator=DefaultArtifactEvaluator(),
            knowledge_builder=DefaultKnowledgeBuilder(),
            knowledge_publisher=publisher,
        )
        with pytest.raises(ObservationReadError):
            orchestrator.run(
                evaluation_date=date(2026, 7, 3),
                artifact_ref=str(test_artifact_path),
            )
        assert repo.get_latest() is None

    def test_pipeline_publishes_knowledge(self, test_artifact_path):
        """Successful pipeline run makes Knowledge available via publisher."""
        from core.msi.dra.filesystem_artifact_loader import (
            FilesystemArtifactLoader,
        )

        loader = FilesystemArtifactLoader()
        repo = KnowledgeRepository()
        publisher = DefaultKnowledgePublisher(repo)
        orchestrator = DRAOrchestrator(
            observation_reader=FakeObservationReader(),
            evidence_builder=DefaultEvidenceBuilder(),
            artifact_loader=loader,
            artifact_evaluator=DefaultArtifactEvaluator(),
            knowledge_builder=DefaultKnowledgeBuilder(),
            knowledge_publisher=publisher,
        )
        result = orchestrator.run(
            evaluation_date=date(2026, 7, 3),
            artifact_ref=str(test_artifact_path),
        )
        loaded = repo.load(result.knowledge_id)
        assert loaded == result

    def test_pipeline_knowledge_id_64_char_hex(self, test_artifact_path):
        """knowledge_id is a 64-character hex string."""
        from core.msi.dra.filesystem_artifact_loader import (
            FilesystemArtifactLoader,
        )

        loader = FilesystemArtifactLoader()
        orchestrator = self._make_orchestrator(loader)
        result = orchestrator.run(
            evaluation_date=date(2026, 7, 3),
            artifact_ref=str(test_artifact_path),
        )
        assert len(result.knowledge_id) == 64
        int(result.knowledge_id, 16)

    def test_orchestrator_sequence(self, test_artifact_path):
        """Orchestrator stores all pipeline stages."""
        from core.msi.dra.filesystem_artifact_loader import (
            FilesystemArtifactLoader,
        )

        loader = FilesystemArtifactLoader()
        call_order = []

        class TrackingReader(FakeObservationReader):
            def read(self, eval_date, symbols):
                call_order.append("read")
                return super().read(eval_date, symbols)

        from core.msi.dra.default_evidence_builder import (
            DefaultEvidenceBuilder,
        )

        original_build = DefaultEvidenceBuilder.build

        def tracking_build(self, obs, art):
            call_order.append("build")
            return original_build(self, obs, art)

        from core.msi.dra.default_artifact_evaluator import (
            DefaultArtifactEvaluator,
        )

        original_eval = DefaultArtifactEvaluator.evaluate

        def tracking_evaluate(self, ev, art):
            call_order.append("evaluate")
            return original_eval(self, ev, art)

        from core.msi.dra.default_knowledge_builder import (
            DefaultKnowledgeBuilder,
        )

        original_kb = DefaultKnowledgeBuilder.build

        def tracking_kb(self, ms, art, chain):
            call_order.append("knowledge")
            return original_kb(self, ms, art, chain)

        DefaultEvidenceBuilder.build = tracking_build
        DefaultArtifactEvaluator.evaluate = tracking_evaluate
        DefaultKnowledgeBuilder.build = tracking_kb

        try:
            repo = KnowledgeRepository()
            publisher = DefaultKnowledgePublisher(repo)
            orchestrator = DRAOrchestrator(
                observation_reader=TrackingReader(),
                evidence_builder=DefaultEvidenceBuilder(),
                artifact_loader=loader,
                artifact_evaluator=DefaultArtifactEvaluator(),
                knowledge_builder=DefaultKnowledgeBuilder(),
                knowledge_publisher=publisher,
            )
            orchestrator.run(
                evaluation_date=date(2026, 7, 3),
                artifact_ref=str(test_artifact_path),
            )
            assert call_order == ["read", "build", "evaluate", "knowledge"]
        finally:
            DefaultEvidenceBuilder.build = original_build
            DefaultArtifactEvaluator.evaluate = original_eval
            DefaultKnowledgeBuilder.build = original_kb
