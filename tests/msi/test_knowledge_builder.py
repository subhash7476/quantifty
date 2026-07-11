"""Knowledge Builder tests (MSI-005 §11)."""

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from core.msi.contracts.estimate import Estimate
from core.msi.contracts.knowledge import KnowledgeObject
from core.msi.contracts.market_state import MarketState
from core.msi.dra.default_knowledge_builder import DefaultKnowledgeBuilder
from core.msi.dra.provenance import ProvenanceChain
from core.msi.dra.errors import KnowledgeBuildError

_TS = datetime(2026, 7, 4, 12, 0, 0)


def _make_market_state() -> MarketState:
    return MarketState(
        evaluation_timestamp=_TS,
        estimates=(
            Estimate("market_regime", 1.0, 0.15, "regime_class"),
            Estimate("trend_strength", 0.5, 0.30, "trend_magnitude"),
        ),
    )


def _make_provenance_chain() -> ProvenanceChain:
    return ProvenanceChain(
        observation_ids=("obs_n50", "obs_vix"),
        evidence_ids=("ev_n50_close", "ev_vix_close"),
        artifact_id="ref-test-001",
        artifact_version="v1.0.0",
        validation_id="val-ref-test-001-v1",
        knowledge_id="",
    )


class TestDefaultKnowledgeBuilder:
    """DefaultKnowledgeBuilder tests (MSI-005 §11)."""

    def test_knowledge_object_schema(self, reference_test_artifact):
        """KnowledgeObject has all 6 fields from MSI-005 §11."""
        builder = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        chain = _make_provenance_chain()
        ko = builder.build(ms, reference_test_artifact, chain)
        assert isinstance(ko, KnowledgeObject)
        assert isinstance(ko.knowledge_id, str)
        assert isinstance(ko.evaluation_timestamp, datetime)
        assert isinstance(ko.artifact_version, str)
        assert isinstance(ko.runtime_version, str)
        assert isinstance(ko.market_state, MarketState)
        assert isinstance(ko.provenance_reference, str)

    def test_knowledge_id_deterministic(self, reference_test_artifact):
        """Identical inputs → identical knowledge_id."""
        builder = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        chain = _make_provenance_chain()
        ko1 = builder.build(ms, reference_test_artifact, chain)
        ko2 = builder.build(ms, reference_test_artifact, chain)
        assert ko1.knowledge_id == ko2.knowledge_id

    def test_knowledge_id_hash_content_across_builders(
        self, reference_test_artifact
    ):
        """Identical inputs → identical IDs across builder instances."""
        b1 = DefaultKnowledgeBuilder()
        b2 = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        chain = _make_provenance_chain()
        ko1 = b1.build(ms, reference_test_artifact, chain)
        ko2 = b2.build(ms, reference_test_artifact, chain)
        assert ko1.knowledge_id == ko2.knowledge_id

    def test_knowledge_id_is_64_char_hex(self, reference_test_artifact):
        """knowledge_id is a 64-character hex string (SHA-256)."""
        builder = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        chain = _make_provenance_chain()
        ko = builder.build(ms, reference_test_artifact, chain)
        assert len(ko.knowledge_id) == 64
        int(ko.knowledge_id, 16)

    def test_no_scalar_confidence(self, reference_test_artifact):
        """KnowledgeObject has no standalone confidence/uncertainty (MSI-5D-03)."""
        builder = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        chain = _make_provenance_chain()
        ko = builder.build(ms, reference_test_artifact, chain)
        assert not hasattr(ko, "confidence")
        assert not hasattr(ko, "uncertainty")

    def test_knowledge_object_immutable(self, reference_test_artifact):
        """KnowledgeObject is frozen."""
        builder = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        chain = _make_provenance_chain()
        ko = builder.build(ms, reference_test_artifact, chain)
        with pytest.raises(FrozenInstanceError):
            ko.artifact_version = "changed"

    def test_artifact_version_propagated(self, reference_test_artifact):
        """artifact_version comes from the artifact's metadata."""
        builder = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        chain = _make_provenance_chain()
        ko = builder.build(ms, reference_test_artifact, chain)
        assert ko.artifact_version == "v1.0.0"

    def test_runtime_version_default(self, reference_test_artifact):
        """runtime_version is the default MSI runtime version."""
        builder = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        chain = _make_provenance_chain()
        ko = builder.build(ms, reference_test_artifact, chain)
        assert ko.runtime_version == "msi-v1.0"

    def test_evaluation_timestamp_preserved(self, reference_test_artifact):
        """evaluation_timestamp matches the MarketState."""
        builder = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        chain = _make_provenance_chain()
        ko = builder.build(ms, reference_test_artifact, chain)
        assert ko.evaluation_timestamp == _TS

    def test_market_state_preserved(self, reference_test_artifact):
        """MarketState is preserved in the KnowledgeObject."""
        builder = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        chain = _make_provenance_chain()
        ko = builder.build(ms, reference_test_artifact, chain)
        assert ko.market_state == ms

    def test_invalid_market_state_raises(self, reference_test_artifact):
        """Non-MarketState input raises KnowledgeBuildError."""
        builder = DefaultKnowledgeBuilder()
        chain = _make_provenance_chain()
        with pytest.raises(KnowledgeBuildError):
            builder.build("not_a_market_state", reference_test_artifact, chain)

    def test_invalid_provenance_raises(self, reference_test_artifact):
        """Non-ProvenanceChain provenance raises KnowledgeBuildError."""
        builder = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        with pytest.raises(KnowledgeBuildError):
            builder.build(ms, reference_test_artifact, "not_a_chain")

    def test_provenance_chain_reference_matches_knowledge_id(
        self, reference_test_artifact
    ):
        """provenance_reference equals knowledge_id."""
        builder = DefaultKnowledgeBuilder()
        ms = _make_market_state()
        chain = _make_provenance_chain()
        ko = builder.build(ms, reference_test_artifact, chain)
        assert ko.provenance_reference == ko.knowledge_id

    def test_knowledge_id_different_for_different_market_state(
        self, reference_test_artifact
    ):
        """Different estimates produce different knowledge_id."""
        builder = DefaultKnowledgeBuilder()
        chain = _make_provenance_chain()
        ms1 = _make_market_state()
        ms2 = MarketState(
            _TS,
            (Estimate("different_regime", 2.0, 0.2, "regime_class"),),
        )
        ko1 = builder.build(ms1, reference_test_artifact, chain)
        ko2 = builder.build(ms2, reference_test_artifact, chain)
        assert ko1.knowledge_id != ko2.knowledge_id

    def test_builder_is_subclass_of_abc(self):
        """DefaultKnowledgeBuilder satisfies the KnowledgeBuilder ABC."""
        from core.msi.interfaces.knowledge_builder import KnowledgeBuilder
        assert issubclass(DefaultKnowledgeBuilder, KnowledgeBuilder)
