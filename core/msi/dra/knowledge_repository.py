"""KnowledgeRepository — deterministic in-memory KnowledgeObject store."""

from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from ..contracts.estimate import Estimate
from ..contracts.knowledge import KnowledgeObject
from ..contracts.market_state import MarketState
from .errors import KnowledgeRepositoryError


class KnowledgeRepository:
    """Deterministic in-memory KnowledgeObject repository.

    Supports store, load, exists, date-based retrieval, and latest retrieval.
    All KnowledgeObjects remain immutable before and after storage.
    """

    def __init__(self):
        self._by_id: Dict[str, KnowledgeObject] = {}
        self._by_date: Dict[date, str] = {}
        self._ordered_dates: List[date] = []

    def store(self, knowledge: KnowledgeObject) -> None:
        """Persist a KnowledgeObject.

        Args:
            knowledge: KnowledgeObject to store.

        Raises:
            KnowledgeRepositoryError: Duplicate knowledge_id or storage failure.
        """
        if knowledge.knowledge_id in self._by_id:
            raise KnowledgeRepositoryError(
                f"KnowledgeObject with id '{knowledge.knowledge_id}' "
                f"already exists"
            )

        eval_date = knowledge.evaluation_timestamp.date()

        self._by_id[knowledge.knowledge_id] = knowledge
        self._by_date[eval_date] = knowledge.knowledge_id

        if eval_date not in self._ordered_dates:
            self._ordered_dates.append(eval_date)
            self._ordered_dates.sort()

    def load(self, knowledge_id: str) -> KnowledgeObject:
        """Retrieve a KnowledgeObject by ID.

        Args:
            knowledge_id: The knowledge_id to look up.

        Returns:
            The stored KnowledgeObject (immutable).

        Raises:
            KnowledgeRepositoryError: knowledge_id not found.
        """
        obj = self._by_id.get(knowledge_id)
        if obj is None:
            raise KnowledgeRepositoryError(
                f"KnowledgeObject not found: '{knowledge_id}'"
            )
        return obj

    def exists(self, knowledge_id: str) -> bool:
        """Check if a KnowledgeObject exists by ID.

        Args:
            knowledge_id: The knowledge_id to check.

        Returns:
            True if the knowledge_id is stored, False otherwise.
        """
        return knowledge_id in self._by_id

    def get_by_date(self, eval_date: date) -> Optional[KnowledgeObject]:
        """Retrieve KnowledgeObject for a specific evaluation date.

        Args:
            eval_date: Evaluation date to query.

        Returns:
            KnowledgeObject if found, else None.
        """
        knowledge_id = self._by_date.get(eval_date)
        if knowledge_id is None:
            return None
        return self._by_id[knowledge_id]

    def get_latest(self) -> Optional[KnowledgeObject]:
        """Retrieve the most recent KnowledgeObject by evaluation date.

        Returns:
            The most recent KnowledgeObject, or None if empty.
        """
        if not self._ordered_dates:
            return None
        latest_date = self._ordered_dates[-1]
        knowledge_id = self._by_date[latest_date]
        return self._by_id[knowledge_id]
