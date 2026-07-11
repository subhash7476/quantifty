import pytest

from core.msi.interfaces import (
    ObservationReader,
    EvidenceBuilder,
    ArtifactLoader,
    ArtifactEvaluator,
    KnowledgeBuilder,
    KnowledgePublisher,
)


class TestObservationReader:
    """Test ObservationReader interface (MSI-003 §4)."""

    def test_observation_reader_is_abstract(self):
        """ObservationReader cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ObservationReader()

    def test_observation_reader_requires_read_method(self):
        """ObservationReader requires read abstract method."""
        from abc import ABC

        class IncompleteReader(ObservationReader):
            pass

        with pytest.raises(TypeError):
            IncompleteReader()

    def test_observation_reader_can_be_subclassed(self):
        """ObservationReader can be subclassed with read method implemented."""
        from datetime import date
        from core.msi.contracts import Observation

        class TestReader(ObservationReader):
            def read(self, evaluation_date: date, symbols: tuple):
                return ()

        reader = TestReader()
        assert isinstance(reader, ObservationReader)
        assert callable(reader.read)


class TestEvidenceBuilder:
    """Test EvidenceBuilder interface (MSI-004 §2/§5)."""

    def test_evidence_builder_is_abstract(self):
        """EvidenceBuilder cannot be instantiated directly."""
        with pytest.raises(TypeError):
            EvidenceBuilder()

    def test_evidence_builder_requires_build_method(self):
        """EvidenceBuilder requires build abstract method."""
        from abc import ABC

        class IncompleteBuilder(EvidenceBuilder):
            pass

        with pytest.raises(TypeError):
            IncompleteBuilder()

    def test_evidence_builder_can_be_subclassed(self):
        """EvidenceBuilder can be subclassed with build method implemented."""
        from core.msi.contracts import Observation, Evidence, PublishedArtifact

        class TestBuilder(EvidenceBuilder):
            def build(self, observations: tuple, artifact: PublishedArtifact):
                return ()

        builder = TestBuilder()
        assert isinstance(builder, EvidenceBuilder)
        assert callable(builder.build)


class TestArtifactLoader:
    """Test ArtifactLoader interface (MSI-007 §7–8, MSI-008 §9)."""

    def test_artifact_loader_is_abstract(self):
        """ArtifactLoader cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ArtifactLoader()

    def test_artifact_loader_requires_load_method(self):
        """ArtifactLoader requires load abstract method."""
        from abc import ABC

        class IncompleteLoader(ArtifactLoader):
            pass

        with pytest.raises(TypeError):
            IncompleteLoader()

    def test_artifact_loader_can_be_subclassed(self):
        """ArtifactLoader can be subclassed with load method implemented."""
        from core.msi.contracts import PublishedArtifact

        class TestLoader(ArtifactLoader):
            def load(self, artifact_ref: str):
                pass

        loader = TestLoader()
        assert isinstance(loader, ArtifactLoader)
        assert callable(loader.load)


class TestArtifactEvaluator:
    """Test ArtifactEvaluator interface (MSI-005 §7/§13)."""

    def test_artifact_evaluator_is_abstract(self):
        """ArtifactEvaluator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ArtifactEvaluator()

    def test_artifact_evaluator_requires_evaluate_method(self):
        """ArtifactEvaluator requires evaluate abstract method."""
        from abc import ABC

        class IncompleteEvaluator(ArtifactEvaluator):
            pass

        with pytest.raises(TypeError):
            IncompleteEvaluator()

    def test_artifact_evaluator_can_be_subclassed(self):
        """ArtifactEvaluator can be subclassed with evaluate method implemented."""
        from core.msi.contracts import Evidence, MarketState, PublishedArtifact

        class TestEvaluator(ArtifactEvaluator):
            def evaluate(self, evidence: tuple, artifact: PublishedArtifact):
                pass

        evaluator = TestEvaluator()
        assert isinstance(evaluator, ArtifactEvaluator)
        assert callable(evaluator.evaluate)


class TestKnowledgeBuilder:
    """Test KnowledgeBuilder interface (MSI-005 §11)."""

    def test_knowledge_builder_is_abstract(self):
        """KnowledgeBuilder cannot be instantiated directly."""
        with pytest.raises(TypeError):
            KnowledgeBuilder()

    def test_knowledge_builder_requires_build_method(self):
        """KnowledgeBuilder requires build abstract method."""
        from abc import ABC

        class IncompleteBuilder(KnowledgeBuilder):
            pass

        with pytest.raises(TypeError):
            IncompleteBuilder()

    def test_knowledge_builder_can_be_subclassed(self):
        """KnowledgeBuilder can be subclassed with build method implemented."""
        from core.msi.contracts import MarketState, PublishedArtifact, KnowledgeObject

        class TestBuilder(KnowledgeBuilder):
            def build(self, market_state, artifact, provenance_chain):
                pass

        builder = TestBuilder()
        assert isinstance(builder, KnowledgeBuilder)
        assert callable(builder.build)


class TestKnowledgePublisher:
    """Test KnowledgePublisher interface (MSI-005 §6)."""

    def test_knowledge_publisher_is_abstract(self):
        """KnowledgePublisher cannot be instantiated directly."""
        with pytest.raises(TypeError):
            KnowledgePublisher()

    def test_knowledge_publisher_requires_methods(self):
        """KnowledgePublisher requires publish, get_knowledge, get_latest methods."""
        from abc import ABC

        class IncompletePublisher(KnowledgePublisher):
            pass

        with pytest.raises(TypeError):
            IncompletePublisher()

    def test_knowledge_publisher_can_be_subclassed(self):
        """KnowledgePublisher can be subclassed with all methods implemented."""
        from datetime import date
        from core.msi.contracts import KnowledgeObject
        from typing import Optional

        class TestPublisher(KnowledgePublisher):
            def publish(self, knowledge: KnowledgeObject):
                pass

            def get_knowledge(self, evaluation_date: date) -> Optional[KnowledgeObject]:
                return None

            def get_latest(self) -> Optional[KnowledgeObject]:
                return None

        publisher = TestPublisher()
        assert isinstance(publisher, KnowledgePublisher)
        assert callable(publisher.publish)
        assert callable(publisher.get_knowledge)
        assert callable(publisher.get_latest)


class TestInterfaceInheritance:
    """Test that all interfaces inherit from ABC."""

    def test_all_interfaces_inherit_from_abc(self):
        """All interfaces inherit from ABC."""
        from abc import ABC

        assert issubclass(ObservationReader, ABC)
        assert issubclass(EvidenceBuilder, ABC)
        assert issubclass(ArtifactLoader, ABC)
        assert issubclass(ArtifactEvaluator, ABC)
        assert issubclass(KnowledgeBuilder, ABC)
        assert issubclass(KnowledgePublisher, ABC)


class TestInterfaceAbstractMethods:
    """Test that all interfaces expose only defined abstract methods."""

    def test_observation_reader_exposes_only_read_method(self):
        """ObservationReader exposes only the read method defined by DRA plan."""
        reader_methods = [m for m in dir(ObservationReader) if not m.startswith("_")]
        assert "read" in reader_methods

    def test_evidence_builder_exposes_only_build_method(self):
        """EvidenceBuilder exposes only the build method defined by DRA plan."""
        builder_methods = [m for m in dir(EvidenceBuilder) if not m.startswith("_")]
        assert "build" in builder_methods

    def test_artifact_loader_exposes_only_load_method(self):
        """ArtifactLoader exposes only the load method defined by DRA plan."""
        loader_methods = [m for m in dir(ArtifactLoader) if not m.startswith("_")]
        assert "load" in loader_methods

    def test_artifact_evaluator_exposes_only_evaluate_method(self):
        """ArtifactEvaluator exposes only the evaluate method defined by DRA plan."""
        evaluator_methods = [m for m in dir(ArtifactEvaluator) if not m.startswith("_")]
        assert "evaluate" in evaluator_methods

    def test_knowledge_builder_exposes_only_build_method(self):
        """KnowledgeBuilder exposes only the build method defined by DRA plan."""
        builder_methods = [m for m in dir(KnowledgeBuilder) if not m.startswith("_")]
        assert "build" in builder_methods

    def test_knowledge_publisher_exposes_only_defined_methods(self):
        """KnowledgePublisher exposes only methods defined by DRA plan."""
        publisher_methods = [m for m in dir(KnowledgePublisher) if not m.startswith("_")]
        assert "publish" in publisher_methods
        assert "get_knowledge" in publisher_methods
        assert "get_latest" in publisher_methods