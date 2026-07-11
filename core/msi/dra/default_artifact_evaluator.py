"""DefaultArtifactEvaluator — MSI-005 runtime evaluation engine."""

from typing import Tuple

from ..contracts.artifact import PublishedArtifact
from ..contracts.evidence import Evidence
from ..contracts.market_state import MarketState
from ..interfaces.artifact_evaluator import ArtifactEvaluator
from .errors import EvaluationError


class DefaultArtifactEvaluator(ArtifactEvaluator):
    """Default ArtifactEvaluator (MSI-005 §7/§13).

    Invokes artifact.evaluate(evidence) and validates the returned
    MarketState conforms to MSI-005 runtime contract:
    - Every Estimate has latent_variable, value, uncertainty, dimension
    - uncertainty >= 0
    """

    def evaluate(
        self, evidence: Tuple[Evidence, ...], artifact: PublishedArtifact
    ) -> MarketState:
        """Evaluate artifact against Evidence. Deterministic.

        Calls artifact.evaluate(evidence) and validates the output.

        Args:
            evidence: Immutable Evidence DTOs from EvidenceBuilder.
            artifact: Validated PublishedArtifact.

        Returns:
            MarketState with validated Estimates.

        Raises:
            EvaluationError: artifact.evaluate() raised or output invalid.
        """
        try:
            market_state = artifact.evaluate(evidence)
        except Exception as e:
            raise EvaluationError(
                f"artifact.evaluate() raised: {e}"
            ) from e

        self._validate_market_state(market_state)

        return market_state

    def _validate_market_state(self, market_state: MarketState) -> None:
        """Validate MarketState conforms to MSI-005 runtime contract."""
        if not isinstance(market_state, MarketState):
            raise EvaluationError(
                f"artifact.evaluate() returned {type(market_state).__name__}, "
                f"expected MarketState"
            )

        if not market_state.estimates:
            raise EvaluationError(
                "MarketState contains no estimates "
                "(MSI-OD-001 requires multidimensional output)"
            )

        for i, est in enumerate(market_state.estimates):
            if not isinstance(est.latent_variable, str) or not est.latent_variable:
                raise EvaluationError(
                    f"Estimate[{i}] missing or empty latent_variable"
                )
            if not isinstance(est.value, (int, float)):
                raise EvaluationError(
                    f"Estimate[{i}] value must be numeric, "
                    f"got {type(est.value).__name__}"
                )
            if not isinstance(est.uncertainty, (int, float)):
                raise EvaluationError(
                    f"Estimate[{i}] uncertainty must be numeric, "
                    f"got {type(est.uncertainty).__name__}"
                )
            if isinstance(est.uncertainty, bool) or est.uncertainty < 0.0:
                raise EvaluationError(
                    f"Estimate[{i}] uncertainty must be >= 0, "
                    f"got {est.uncertainty}"
                )
            if not isinstance(est.dimension, str) or not est.dimension:
                raise EvaluationError(
                    f"Estimate[{i}] missing or empty dimension"
                )
