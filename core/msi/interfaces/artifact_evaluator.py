from abc import ABC, abstractmethod
from typing import Tuple

from ..contracts.evidence import Evidence
from ..contracts.market_state import MarketState
from ..contracts.artifact import PublishedArtifact


class ArtifactEvaluator(ABC):
    """ArtifactEvaluator interface (MSI-005 §7/§13).

    Runtime artifact evaluation engine.
    Calls artifact.evaluate() and validates output contract.
    """

    @abstractmethod
    def evaluate(self, evidence: Tuple[Evidence, ...], artifact: PublishedArtifact) -> MarketState:
        """Evaluate artifact against Evidence. Deterministic.

        Validates that every Estimate carries value + uncertainty (MSI-OD-005).

        Args:
            evidence: Evidence objects constructed from Observations.
            artifact: PublishedArtifact to evaluate.

        Returns:
            MarketState containing Estimates of Latent Variables.

        Raises:
            EvaluationError: Artifact evaluation failed or contract violation.
                (Exception type defined in M2 — DRA Implementation Plan §16.)
        """
        ...