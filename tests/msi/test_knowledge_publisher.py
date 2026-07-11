"""KnowledgePublisher tests (MSI-005 §6)."""

from datetime import date, datetime

import pytest

from core.msi.contracts.estimate import Estimate
from core.msi.contracts.knowledge import KnowledgeObject
from core.msi.contracts.market_state import MarketState
from core.msi.dra.default_knowledge_publisher import DefaultKnowledgePublisher
from core.msi.dra.knowledge_repository import KnowledgeRepository
from core.msi.dra.errors import KnowledgePublishError

_TS = datetime(2026, 7, 4, 12, 0, 0)
_TS2 = datetime(2026, 7, 5, 12, 0, 0)


def _make_ko(
    kid: str = "ko_abc",
    ts: datetime = _TS,
) -> KnowledgeObject:
    return KnowledgeObject(
        knowledge_id=kid,
        evaluation_timestamp=ts,
        artifact_version="v1.0.0",
        runtime_version="msi-v1.0",
        market_state=MarketState(
            ts,
            (Estimate("market_regime", 1.0, 0.15, "regime_class"),),
        ),
        provenance_reference=kid,
    )


class TestDefaultKnowledgePublisher:
    """DefaultKnowledgePublisher tests (MSI-005 §6)."""

    def test_publish_success(self):
        """Publishing a KnowledgeObject succeeds."""
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        ko = _make_ko()
        pub.publish(ko)
        assert repo.exists(ko.knowledge_id) is True

    def test_publish_deterministic(self):
        """Publishing preserves all fields."""
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        ko = _make_ko()
        pub.publish(ko)
        loaded = repo.load(ko.knowledge_id)
        assert loaded.knowledge_id == ko.knowledge_id
        assert loaded.artifact_version == ko.artifact_version
        assert loaded.runtime_version == ko.runtime_version
        assert loaded.provenance_reference == ko.provenance_reference

    def test_publish_preserves_ids(self):
        """knowledge_id is unchanged after publication."""
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        ko = _make_ko(kid="ko_preserve_test")
        pub.publish(ko)
        loaded = repo.load("ko_preserve_test")
        assert loaded.knowledge_id == "ko_preserve_test"

    def test_publish_preserves_market_state(self):
        """MarketState is unchanged after publication."""
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        ko = _make_ko()
        pub.publish(ko)
        loaded = repo.load(ko.knowledge_id)
        assert loaded.market_state == ko.market_state
        assert loaded.market_state.estimates == ko.market_state.estimates

    def test_publish_preserves_provenance(self):
        """Provenance reference is unchanged after publication."""
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        ko = _make_ko(kid="ko_prov")
        pub.publish(ko)
        loaded = repo.load("ko_prov")
        assert loaded.provenance_reference == "ko_prov"

    def test_get_knowledge_by_date(self):
        """get_knowledge returns KnowledgeObject for the evaluation date."""
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        ko = _make_ko(ts=_TS)
        pub.publish(ko)
        result = pub.get_knowledge(date(2026, 7, 4))
        assert result == ko

    def test_get_knowledge_missing_date(self):
        """get_knowledge returns None for date with no knowledge."""
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        ko = _make_ko(ts=_TS)
        pub.publish(ko)
        assert pub.get_knowledge(date(2026, 7, 5)) is None

    def test_get_latest(self):
        """get_latest returns most recent KnowledgeObject."""
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        ko_early = _make_ko(kid="ko_early", ts=_TS)
        ko_late = _make_ko(kid="ko_late", ts=_TS2)
        pub.publish(ko_early)
        pub.publish(ko_late)
        assert pub.get_latest() == ko_late

    def test_get_latest_empty(self):
        """get_latest returns None when no knowledge published."""
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        assert pub.get_latest() is None

    def test_publish_duplicate_raises(self):
        """Publishing duplicate knowledge_id raises KnowledgePublishError."""
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        ko = _make_ko()
        pub.publish(ko)
        with pytest.raises(KnowledgePublishError):
            pub.publish(ko)

    def test_publish_immutable(self):
        """Published KnowledgeObject remains unchanged in repository."""
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        ko = _make_ko()
        pub.publish(ko)
        loaded = repo.load(ko.knowledge_id)
        assert loaded == ko

    def test_publisher_is_subclass_of_abc(self):
        """DefaultKnowledgePublisher satisfies the KnowledgePublisher ABC."""
        from core.msi.interfaces.knowledge_publisher import KnowledgePublisher
        repo = KnowledgeRepository()
        pub = DefaultKnowledgePublisher(repo)
        assert isinstance(pub, KnowledgePublisher)
