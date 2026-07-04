from abc import ABC, abstractmethod
from typing import Tuple

from ..contracts.evidence import Evidence
from ..contracts.observation import Observation
from ..contracts.artifact import PublishedArtifact


class EvidenceBuilder(ABC):
    """EvidenceBuilder interface (MSI-004 §2/§5).

    Construct Evidence from Observations + artifact-carried rules.
    Applies only validated rules; authors no rules at runtime.
    """

    @abstractmethod
    def build(
        self, observations: Tuple[Observation, ...], artifact: PublishedArtifact
    ) -> Tuple[Evidence, ...]:
        """Apply artifact-carried construction rules to Observations. Deterministic.

        Args:
            observations: Observation objects from Platform stores.
            artifact: PublishedArtifact containing evidence-construction rules.

        Returns:
            Tuple of immutable Evidence objects with deterministic IDs.

        Raises:
            EvidenceConstructionError: Rules cannot be applied.
        """
        ...