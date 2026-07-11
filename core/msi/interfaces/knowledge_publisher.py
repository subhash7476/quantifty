from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from ..contracts.knowledge import KnowledgeObject


class KnowledgePublisher(ABC):
    """KnowledgePublisher interface (MSI-005 §6).

    Persist Knowledge and expose read-only access to strategies.
    Strategies pull; publisher never pushes.
    """

    @abstractmethod
    def publish(self, knowledge: KnowledgeObject) -> None:
        """Persist KnowledgeObject with transactional guarantee.

        Args:
            knowledge: KnowledgeObject to persist.

        Raises:
            KnowledgePublishError: DuckDB write failed.
                (Exception type defined in M2 — DRA Implementation Plan §16.)
        """
        ...

    @abstractmethod
    def get_knowledge(self, date: date) -> Optional[KnowledgeObject]:
        """Read Knowledge for a given date. Returns None if not found.

        Args:
            date: Evaluation date to query.

        Returns:
            KnowledgeObject if found, else None.
        """
        ...

    @abstractmethod
    def get_latest(self) -> Optional[KnowledgeObject]:
        """Read most recent Knowledge.

        Returns:
            KnowledgeObject if any exists, else None.
        """
        ...