"""KnowledgeRepository tests (MSI-005 §6)."""

from datetime import date, datetime

import pytest

from core.msi.contracts.estimate import Estimate
from core.msi.contracts.knowledge import KnowledgeObject
from core.msi.contracts.market_state import MarketState
from core.msi.dra.knowledge_repository import KnowledgeRepository
from core.msi.dra.errors import KnowledgeRepositoryError

_TS = datetime(2026, 7, 4, 12, 0, 0)
_TS2 = datetime(2026, 7, 5, 12, 0, 0)


def _make_ko(
    kid: str = "ko_abc",
    ts: datetime = _TS,
    av: str = "v1.0.0",
    rv: str = "msi-v1.0",
    ref: str = "ko_abc",
) -> KnowledgeObject:
    return KnowledgeObject(
        knowledge_id=kid,
        evaluation_timestamp=ts,
        artifact_version=av,
        runtime_version=rv,
        market_state=MarketState(
            ts,
            (Estimate("market_regime", 1.0, 0.15, "regime_class"),),
        ),
        provenance_reference=ref,
    )


class TestKnowledgeRepository:
    """KnowledgeRepository store/load/exists tests."""

    def test_store_load_roundtrip(self):
        """Stored KnowledgeObject can be loaded by ID."""
        repo = KnowledgeRepository()
        ko = _make_ko()
        repo.store(ko)
        loaded = repo.load(ko.knowledge_id)
        assert loaded == ko
        assert loaded.knowledge_id == ko.knowledge_id

    def test_store_duplicate_raises(self):
        """Duplicate knowledge_id raises KnowledgeRepositoryError."""
        repo = KnowledgeRepository()
        ko = _make_ko()
        repo.store(ko)
        with pytest.raises(KnowledgeRepositoryError) as exc:
            repo.store(ko)
        assert "already exists" in str(exc.value)

    def test_load_missing_raises(self):
        """Loading a non-existent knowledge_id raises."""
        repo = KnowledgeRepository()
        with pytest.raises(KnowledgeRepositoryError) as exc:
            repo.load("nonexistent")
        assert "not found" in str(exc.value)

    def test_exists_returns_true(self):
        """exists() returns True for stored knowledge."""
        repo = KnowledgeRepository()
        ko = _make_ko()
        repo.store(ko)
        assert repo.exists(ko.knowledge_id) is True

    def test_exists_returns_false(self):
        """exists() returns False for unknown knowledge."""
        repo = KnowledgeRepository()
        assert repo.exists("unknown") is False

    def test_roundtrip_deterministic(self):
        """Multiple store/load cycles produce identical objects."""
        repo = KnowledgeRepository()
        ko = _make_ko()
        repo.store(ko)
        r1 = repo.load(ko.knowledge_id)
        r2 = repo.load(ko.knowledge_id)
        assert r1 == r2
        assert r1 == ko

    def test_repository_does_not_mutate(self):
        """Repository does not mutate stored KnowledgeObjects."""
        repo = KnowledgeRepository()
        ko = _make_ko()
        repo.store(ko)
        loaded = repo.load(ko.knowledge_id)
        assert loaded == ko
        assert loaded.knowledge_id == ko.knowledge_id

    def test_repository_returns_identical_object(self):
        """Loaded object is equal to stored object by value."""
        repo = KnowledgeRepository()
        ko = _make_ko()
        repo.store(ko)
        loaded = repo.load(ko.knowledge_id)
        assert loaded == ko

    def test_get_by_date(self):
        """KnowledgeObject retrievable by evaluation date."""
        repo = KnowledgeRepository()
        ko = _make_ko()
        repo.store(ko)
        result = repo.get_by_date(date(2026, 7, 4))
        assert result == ko

    def test_get_by_date_missing(self):
        """get_by_date returns None for date with no knowledge."""
        repo = KnowledgeRepository()
        result = repo.get_by_date(date(2026, 7, 1))
        assert result is None

    def test_get_latest(self):
        """get_latest returns most recent by evaluation_timestamp."""
        repo = KnowledgeRepository()
        ko_early = _make_ko(kid="ko_early", ts=_TS)
        ko_late = _make_ko(kid="ko_late", ts=_TS2)
        repo.store(ko_early)
        repo.store(ko_late)
        assert repo.get_latest() == ko_late

    def test_get_latest_empty(self):
        """get_latest returns None for empty repository."""
        repo = KnowledgeRepository()
        assert repo.get_latest() is None

    def test_get_latest_single(self):
        """get_latest returns the only stored knowledge."""
        repo = KnowledgeRepository()
        ko = _make_ko()
        repo.store(ko)
        assert repo.get_latest() == ko

    def test_multiple_dates_get_by_date(self):
        """Multiple knowledge on different dates retrievable individually."""
        repo = KnowledgeRepository()
        ko1 = _make_ko(kid="ko_day1", ts=datetime(2026, 7, 4, 12, 0, 0))
        ko2 = _make_ko(kid="ko_day2", ts=datetime(2026, 7, 5, 12, 0, 0))
        repo.store(ko1)
        repo.store(ko2)
        assert repo.get_by_date(date(2026, 7, 4)) == ko1
        assert repo.get_by_date(date(2026, 7, 5)) == ko2
