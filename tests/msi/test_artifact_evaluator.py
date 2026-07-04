"""Artifact Evaluator tests (MSI-005 §7/§13)."""

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from core.msi.contracts.estimate import Estimate
from core.msi.contracts.evidence import Evidence
from core.msi.contracts.market_state import MarketState
from core.msi.contracts.artifact import PublishedArtifact
from core.msi.dra.default_artifact_evaluator import DefaultArtifactEvaluator
from core.msi.dra.errors import EvaluationError

_TS = datetime(2026, 7, 4, 12, 0, 0)


def _make_evidence() -> Evidence:
    return Evidence(
        evidence_id="ev_test",
        source_observation_ids=(),
        construction_timestamp=_TS,
        evidence_type="vix_close",
        evidence_value=18.5,
        artifact_version="v1.0.0",
        provenance_metadata={},
        quality_metadata={},
        version="1.0",
    )


class TestDefaultArtifactEvaluator:
    """DefaultArtifactEvaluator tests (MSI-005 §7/§13)."""

    def test_evaluate_returns_market_state(self, reference_test_artifact):
        """evaluate() returns a MarketState."""
        evaluator = DefaultArtifactEvaluator()
        evidence = (_make_evidence(),)
        result = evaluator.evaluate(evidence, reference_test_artifact)
        assert isinstance(result, MarketState)

    def test_evaluate_has_estimates(self, reference_test_artifact):
        """MarketState contains Estimate objects."""
        evaluator = DefaultArtifactEvaluator()
        evidence = (_make_evidence(),)
        result = evaluator.evaluate(evidence, reference_test_artifact)
        assert len(result.estimates) >= 1
        for est in result.estimates:
            assert isinstance(est, Estimate)

    def test_evaluate_estimates_have_required_fields(
        self, reference_test_artifact
    ):
        """Each Estimate has latent_variable, value, uncertainty, dimension."""
        evaluator = DefaultArtifactEvaluator()
        evidence = (_make_evidence(),)
        result = evaluator.evaluate(evidence, reference_test_artifact)
        for est in result.estimates:
            assert isinstance(est.latent_variable, str)
            assert isinstance(est.value, float)
            assert isinstance(est.uncertainty, float)
            assert isinstance(est.dimension, str)

    def test_evaluate_determinism(self, reference_test_artifact):
        """Same evidence + artifact → identical MarketState."""
        evaluator = DefaultArtifactEvaluator()
        evidence = (_make_evidence(),)
        r1 = evaluator.evaluate(evidence, reference_test_artifact)
        r2 = evaluator.evaluate(evidence, reference_test_artifact)
        assert r1 == r2
        assert r1.estimates == r2.estimates

    def test_evaluate_market_state_immutable(self, reference_test_artifact):
        """Returned MarketState is frozen."""
        evaluator = DefaultArtifactEvaluator()
        evidence = (_make_evidence(),)
        result = evaluator.evaluate(evidence, reference_test_artifact)
        with pytest.raises(FrozenInstanceError):
            result.evaluation_timestamp = datetime.now()

    def test_evaluate_artifact_raises_evaluation_error(
        self, reference_test_artifact
    ):
        """If artifact.evaluate() raises, EvaluationError is raised."""
        class BadArtifact(PublishedArtifact):
            metadata = reference_test_artifact.metadata
            def get_evidence_rules(self):
                return {}
            def evaluate(self, evidence):
                raise RuntimeError("evaluation crashed")

        evaluator = DefaultArtifactEvaluator()
        evidence = (_make_evidence(),)
        with pytest.raises(EvaluationError) as exc:
            evaluator.evaluate(evidence, BadArtifact())
        assert "evaluation crashed" in str(exc.value)

    def test_evaluate_no_estimates_raises(self):
        """MarketState with no estimates is rejected."""
        class EmptyArtifact(PublishedArtifact):
            metadata = type("m", (), {
                "artifact_id": "test",
                "artifact_version": "v1",
                "schema_version": "1",
                "validation_id": "v",
                "publication_timestamp": _TS,
                "compatibility_version": "1",
                "runtime_compatibility": "msi-v1.0",
                "provenance_reference": "p",
            })
            def get_evidence_rules(self):
                return {}
            def evaluate(self, evidence):
                return MarketState(_TS, ())

        evaluator = DefaultArtifactEvaluator()
        evidence = (_make_evidence(),)
        with pytest.raises(EvaluationError) as exc:
            evaluator.evaluate(evidence, EmptyArtifact())
        assert "no estimates" in str(exc.value).lower()

    def test_evaluate_negative_uncertainty_rejected(self):
        """Estimate with negative uncertainty raises EvaluationError."""
        _META = type("m", (), {
            "artifact_id": "test",
            "artifact_version": "v1",
            "schema_version": "1",
            "validation_id": "v",
            "publication_timestamp": _TS,
            "compatibility_version": "1",
            "runtime_compatibility": "msi-v1.0",
            "provenance_reference": "p",
        })

        class BadUncertaintyArtifact(PublishedArtifact):
            metadata = _META
            def get_evidence_rules(self):
                return {}
            def evaluate(self, evidence):
                return MarketState(
                    _TS,
                    (Estimate("x", 1.0, -0.5, "dim"),),
                )

        evaluator = DefaultArtifactEvaluator()
        evidence = (_make_evidence(),)
        with pytest.raises(EvaluationError) as exc:
            evaluator.evaluate(evidence, BadUncertaintyArtifact())
        assert "uncertainty" in str(exc.value).lower()
        assert "-0.5" in str(exc.value)

    def test_evaluate_wrong_return_type_raises(self):
        """Returning non-MarketState from evaluate() raises EvaluationError."""
        _META = type("m", (), {
            "artifact_id": "test",
            "artifact_version": "v1",
            "schema_version": "1",
            "validation_id": "v",
            "publication_timestamp": _TS,
            "compatibility_version": "1",
            "runtime_compatibility": "msi-v1.0",
            "provenance_reference": "p",
        })

        class WrongReturnArtifact(PublishedArtifact):
            metadata = _META
            def get_evidence_rules(self):
                return {}
            def evaluate(self, evidence):
                return "not_a_market_state"

        evaluator = DefaultArtifactEvaluator()
        evidence = (_make_evidence(),)
        with pytest.raises(EvaluationError):
            evaluator.evaluate(evidence, WrongReturnArtifact())

    def test_evaluate_empty_evidence(self, reference_test_artifact):
        """Empty evidence tuple does not crash."""
        evaluator = DefaultArtifactEvaluator()
        result = evaluator.evaluate((), reference_test_artifact)
        assert isinstance(result, MarketState)

    def test_evaluator_is_subclass_of_abc(self):
        """DefaultArtifactEvaluator satisfies the ArtifactEvaluator ABC."""
        from core.msi.interfaces.artifact_evaluator import ArtifactEvaluator
        assert issubclass(DefaultArtifactEvaluator, ArtifactEvaluator)
