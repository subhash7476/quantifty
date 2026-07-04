"""ProvenanceChain tests (MSI-005 §14, MSI-004 §9, MSI-003 §7)."""

from dataclasses import FrozenInstanceError

import pytest

from core.msi.dra.provenance import ProvenanceChain


class TestProvenanceChain:
    """ProvenanceChain immutability, reconstruction, and verification."""

    def _make_chain(self, knowledge_id: str = "ko_abc123") -> ProvenanceChain:
        return ProvenanceChain(
            observation_ids=("obs_1", "obs_2"),
            evidence_ids=("ev_1", "ev_2"),
            artifact_id="ref-test-001",
            artifact_version="v1.0.0",
            validation_id="val-ref-test-001-v1",
            knowledge_id=knowledge_id,
        )

    def test_provenance_is_immutable(self):
        """ProvenanceChain raises FrozenInstanceError on mutation."""
        chain = self._make_chain()
        with pytest.raises(FrozenInstanceError):
            chain.artifact_id = "changed"

    def test_provenance_all_fields_populated(self):
        """All six fields present after construction."""
        chain = self._make_chain()
        assert chain.observation_ids == ("obs_1", "obs_2")
        assert chain.evidence_ids == ("ev_1", "ev_2")
        assert chain.artifact_id == "ref-test-001"
        assert chain.artifact_version == "v1.0.0"
        assert chain.validation_id == "val-ref-test-001-v1"
        assert chain.knowledge_id == "ko_abc123"

    def test_provenance_reconstruct(self):
        """reconstruct() returns a complete provenance dict."""
        chain = self._make_chain()
        record = chain.reconstruct()
        assert isinstance(record, dict)
        assert record["observation_ids"] == ["obs_1", "obs_2"]
        assert record["evidence_ids"] == ["ev_1", "ev_2"]
        assert record["artifact_id"] == "ref-test-001"
        assert record["artifact_version"] == "v1.0.0"
        assert record["validation_id"] == "val-ref-test-001-v1"
        assert record["knowledge_id"] == "ko_abc123"
        assert record["chain"] == "Observation → Evidence → Artifact → Knowledge"

    def test_provenance_verify_valid(self):
        """verify() returns True for a valid complete chain."""
        chain = self._make_chain()
        assert chain.verify() is True

    def test_provenance_verify_empty_observation_ids(self):
        """verify() returns False when observation_ids is empty."""
        chain = ProvenanceChain(
            observation_ids=(),
            evidence_ids=("ev_1",),
            artifact_id="a",
            artifact_version="v1",
            validation_id="v",
            knowledge_id="k",
        )
        assert chain.verify() is False

    def test_provenance_verify_empty_evidence_ids(self):
        """verify() returns False when evidence_ids is empty."""
        chain = ProvenanceChain(
            observation_ids=("obs_1",),
            evidence_ids=(),
            artifact_id="a",
            artifact_version="v1",
            validation_id="v",
            knowledge_id="k",
        )
        assert chain.verify() is False

    def test_provenance_verify_empty_artifact_id(self):
        """verify() returns False when artifact_id is empty."""
        chain = ProvenanceChain(
            observation_ids=("obs_1",),
            evidence_ids=("ev_1",),
            artifact_id="",
            artifact_version="v1",
            validation_id="v",
            knowledge_id="k",
        )
        assert chain.verify() is False

    def test_provenance_deterministic(self):
        """Same inputs produce identical ProvenanceChain objects."""
        c1 = self._make_chain(knowledge_id="ko_abc")
        c2 = self._make_chain(knowledge_id="ko_abc")
        assert c1 == c2
        assert c1.reconstruct() == c2.reconstruct()

    def test_provenance_different_knowledge_id(self):
        """Different knowledge_id produces different provenance."""
        c1 = self._make_chain(knowledge_id="ko_a")
        c2 = self._make_chain(knowledge_id="ko_b")
        assert c1 != c2
        assert c1.knowledge_id != c2.knowledge_id

    def test_provenance_reconstruct_returns_new_dict(self):
        """reconstruct() returns a new dict each call."""
        chain = self._make_chain()
        r1 = chain.reconstruct()
        r2 = chain.reconstruct()
        assert r1 == r2
        assert r1 is not r2

    def test_provenance_verify_accepts_optional_stores(self):
        """verify() accepts optional store arguments without error."""
        chain = self._make_chain()
        assert chain.verify(
            knowledge_store=None,
            evidence_store=None,
            observation_store=None,
        ) is True
