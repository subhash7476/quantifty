"""DefaultKnowledgePublisher — MSI-005 §6 Knowledge publication."""

from datetime import date
from typing import Optional

from ..contracts.knowledge import KnowledgeObject
from ..interfaces.knowledge_publisher import KnowledgePublisher
from .errors import KnowledgePublishError
from .knowledge_repository import KnowledgeRepository


class DefaultKnowledgePublisher(KnowledgePublisher):
    """Default KnowledgePublisher (MSI-005 §6).

    Persists immutable KnowledgeObjects via a KnowledgeRepository.
    Exposes read-only access: get_knowledge (by date) and get_latest.
    """

    def __init__(self, repository: KnowledgeRepository):
        self._repository = repository

    def publish(self, knowledge: KnowledgeObject) -> None:
        """Persist a KnowledgeObject.

        Args:
            knowledge: Immutable KnowledgeObject to publish.

        Raises:
            KnowledgePublishError: Publication failed (e.g., duplicate ID).
        """
        try:
            self._repository.store(knowledge)
        except Exception as e:
            raise KnowledgePublishError(
                f"Failed to publish KnowledgeObject "
                f"'{knowledge.knowledge_id}': {e}"
            ) from e

    def get_knowledge(self, eval_date: date) -> Optional[KnowledgeObject]:
        """Read Knowledge for a given evaluation date.

        Args:
            eval_date: Evaluation date to query.

        Returns:
            KnowledgeObject if found, else None.
        """
        return self._repository.get_by_date(eval_date)

    def get_latest(self) -> Optional[KnowledgeObject]:
        """Read most recent Knowledge.

        Returns:
            KnowledgeObject if any exists, else None.
        """
        return self._repository.get_latest()
