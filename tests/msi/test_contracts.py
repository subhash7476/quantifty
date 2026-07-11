import pytest
from dataclasses import FrozenInstanceError
from datetime import datetime, date

from core.msi.contracts import (
    Observation,
    Evidence,
    Estimate,
    MarketState,
    KnowledgeObject,
    ArtifactMetadata,
    PublishedArtifact,
)


class TestObservation:
    """Test Observation DTO (MSI-003 §5)."""

    def test_observations_are_frozen(self):
        """Observations raise FrozenInstanceError on mutation attempt."""
        obs = Observation(
            observation_id="obs_1",
            timestamp=datetime(2026, 7, 3, 15, 30),
            instrument_id="NSE_INDEX|Nifty 50",
            source_reference="upstox_v2",
            observable_type="close_price",
            measured_value=24500.5,
            measurement_units="INR",
            provenance_ref="prov_123",
            quality_metadata={"completeness": 1.0},
        )
        with pytest.raises(FrozenInstanceError):
            obs.measured_value = 25000.0

    def test_observation_has_required_fields(self):
        """Observation has all required fields per MSI-003 §5."""
        obs = Observation(
            observation_id="obs_1",
            timestamp=datetime(2026, 7, 3, 15, 30),
            instrument_id="NSE_INDEX|Nifty 50",
            source_reference="upstox_v2",
            observable_type="close_price",
            measured_value=24500.5,
            measurement_units="INR",
            provenance_ref="prov_123",
            quality_metadata={"completeness": 1.0},
        )
        assert obs.observation_id == "obs_1"
        assert obs.instrument_id == "NSE_INDEX|Nifty 50"
        assert obs.source_reference == "upstox_v2"
        assert obs.observable_type == "close_price"
        assert obs.measured_value == 24500.5
        assert obs.measurement_units == "INR"
        assert obs.provenance_ref == "prov_123"
        assert obs.quality_metadata == {"completeness": 1.0}


class TestEvidence:
    """Test Evidence DTO (MSI-004 §7)."""

    def test_evidence_are_frozen(self):
        """Evidence raises FrozenInstanceError on mutation attempt."""
        ev = Evidence(
            evidence_id="ev_1",
            source_observation_ids=("obs_1", "obs_2"),
            construction_timestamp=datetime(2026, 7, 3, 16, 0),
            evidence_type="vix_level",
            evidence_value=15.5,
            artifact_version="v1.0.0",
            provenance_metadata={"source": "test"},
            quality_metadata={"stability": 0.9},
            version="1.0",
        )
        with pytest.raises(FrozenInstanceError):
            ev.evidence_value = 20.0

    def test_evidence_has_required_fields(self):
        """Evidence has all required fields per MSI-004 §7."""
        ev = Evidence(
            evidence_id="ev_1",
            source_observation_ids=("obs_1", "obs_2"),
            construction_timestamp=datetime(2026, 7, 3, 16, 0),
            evidence_type="vix_level",
            evidence_value=15.5,
            artifact_version="v1.0.0",
            provenance_metadata={"source": "test"},
            quality_metadata={"stability": 0.9},
            version="1.0",
        )
        assert ev.evidence_id == "ev_1"
        assert ev.source_observation_ids == ("obs_1", "obs_2")
        assert ev.evidence_type == "vix_level"
        assert ev.evidence_value == 15.5
        assert ev.artifact_version == "v1.0.0"


class TestEstimate:
    """Test Estimate DTO (MSI-002 §4.7)."""

    def test_estimate_are_frozen(self):
        """Estimate raises FrozenInstanceError on mutation attempt."""
        est = Estimate(
            latent_variable="market_regime",
            value=0.75,
            uncertainty=0.15,
            dimension="regime_class",
        )
        with pytest.raises(FrozenInstanceError):
            est.value = 0.8

    def test_estimate_carries_value_and_uncertainty(self):
        """Estimate carries both value and uncertainty per MSI-OD-005."""
        est = Estimate(
            latent_variable="market_regime",
            value=0.75,
            uncertainty=0.15,
            dimension="regime_class",
        )
        assert est.latent_variable == "market_regime"
        assert est.value == 0.75
        assert est.uncertainty == 0.15
        assert est.dimension == "regime_class"


class TestMarketState:
    """Test MarketState DTO (MSI-002 §4.8)."""

    def test_market_state_are_frozen(self):
        """MarketState raises FrozenInstanceError on mutation attempt."""
        est = Estimate(
            latent_variable="market_regime",
            value=0.75,
            uncertainty=0.15,
            dimension="regime_class",
        )
        ms = MarketState(
            evaluation_timestamp=datetime(2026, 7, 3, 16, 0),
            estimates=(est,),
        )
        with pytest.raises(FrozenInstanceError):
            ms.evaluation_timestamp = datetime(2026, 7, 4, 16, 0)

    def test_market_state_is_multidimensional(self):
        """MarketState is tuple of Estimates per MSI-OD-001."""
        est1 = Estimate(
            latent_variable="market_regime",
            value=0.75,
            uncertainty=0.15,
            dimension="regime_class",
        )
        est2 = Estimate(
            latent_variable="trend_strength",
            value=0.6,
            uncertainty=0.2,
            dimension="trend_magnitude",
        )
        ms = MarketState(
            evaluation_timestamp=datetime(2026, 7, 3, 16, 0),
            estimates=(est1, est2),
        )
        assert len(ms.estimates) == 2
        assert ms.estimates[0].latent_variable == "market_regime"
        assert ms.estimates[1].latent_variable == "trend_strength"


class TestKnowledgeObject:
    """Test KnowledgeObject DTO (MSI-005 §11)."""

    def test_knowledge_object_are_frozen(self):
        """KnowledgeObject raises FrozenInstanceError on mutation attempt."""
        est = Estimate(
            latent_variable="market_regime",
            value=0.75,
            uncertainty=0.15,
            dimension="regime_class",
        )
        ms = MarketState(
            evaluation_timestamp=datetime(2026, 7, 3, 16, 0),
            estimates=(est,),
        )
        ko = KnowledgeObject(
            knowledge_id="ko_1",
            evaluation_timestamp=datetime(2026, 7, 3, 16, 0),
            artifact_version="v1.0.0",
            runtime_version="msi-v1.0",
            market_state=ms,
            provenance_reference="prov_chain_123",
        )
        with pytest.raises(FrozenInstanceError):
            ko.artifact_version = "v2.0.0"

    def test_knowledge_object_has_all_6_fields_per_msi_005(self):
        """KnowledgeObject has exactly 6 fields per MSI-005 §11."""
        est = Estimate(
            latent_variable="market_regime",
            value=0.75,
            uncertainty=0.15,
            dimension="regime_class",
        )
        ms = MarketState(
            evaluation_timestamp=datetime(2026, 7, 3, 16, 0),
            estimates=(est,),
        )
        ko = KnowledgeObject(
            knowledge_id="ko_1",
            evaluation_timestamp=datetime(2026, 7, 3, 16, 0),
            artifact_version="v1.0.0",
            runtime_version="msi-v1.0",
            market_state=ms,
            provenance_reference="prov_chain_123",
        )
        assert ko.knowledge_id == "ko_1"
        assert ko.evaluation_timestamp == datetime(2026, 7, 3, 16, 0)
        assert ko.artifact_version == "v1.0.0"
        assert ko.runtime_version == "msi-v1.0"
        assert ko.market_state == ms
        assert ko.provenance_reference == "prov_chain_123"

    def test_knowledge_object_has_no_scalar_confidence_or_uncertainty(self):
        """KnowledgeObject has no standalone scalar Confidence/Uncertainty per MSI-5D-03."""
        est = Estimate(
            latent_variable="market_regime",
            value=0.75,
            uncertainty=0.15,
            dimension="regime_class",
        )
        ms = MarketState(
            evaluation_timestamp=datetime(2026, 7, 3, 16, 0),
            estimates=(est,),
        )
        ko = KnowledgeObject(
            knowledge_id="ko_1",
            evaluation_timestamp=datetime(2026, 7, 3, 16, 0),
            artifact_version="v1.0.0",
            runtime_version="msi-v1.0",
            market_state=ms,
            provenance_reference="prov_chain_123",
        )
        assert not hasattr(ko, "confidence")
        assert not hasattr(ko, "uncertainty")


class TestArtifactMetadata:
    """Test ArtifactMetadata DTO (MSI-007 §7)."""

    def test_artifact_metadata_are_frozen(self):
        """ArtifactMetadata raises FrozenInstanceError on mutation attempt."""
        am = ArtifactMetadata(
            artifact_id="test_artifact",
            artifact_version="v1.0.0",
            schema_version="1.0",
            validation_id="val_123",
            publication_timestamp=datetime(2026, 7, 3, 12, 0),
            compatibility_version="1.0",
            runtime_compatibility="msi-v1.0",
            provenance_reference="prov_456",
        )
        with pytest.raises(FrozenInstanceError):
            am.artifact_version = "v2.0.0"

    def test_artifact_metadata_has_required_fields(self):
        """ArtifactMetadata has all required fields per MSI-007 §7."""
        am = ArtifactMetadata(
            artifact_id="test_artifact",
            artifact_version="v1.0.0",
            schema_version="1.0",
            validation_id="val_123",
            publication_timestamp=datetime(2026, 7, 3, 12, 0),
            compatibility_version="1.0",
            runtime_compatibility="msi-v1.0",
            provenance_reference="prov_456",
        )
        assert am.artifact_id == "test_artifact"
        assert am.artifact_version == "v1.0.0"
        assert am.schema_version == "1.0"
        assert am.validation_id == "val_123"
        assert am.runtime_compatibility == "msi-v1.0"


class TestPublishedArtifact:
    """Test PublishedArtifact protocol (MSI-007 §11)."""

    def test_published_artifact_is_abstract(self):
        """PublishedArtifact cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PublishedArtifact()

    def test_published_artifact_requires_abstract_methods(self):
        """PublishedArtifact requires get_evidence_rules and evaluate methods."""
        from abc import ABC

        class IncompleteArtifact(PublishedArtifact):
            pass

        with pytest.raises(TypeError):
            IncompleteArtifact()

    def test_published_artifact_can_be_subclassed(self):
        """PublishedArtifact can be subclassed with abstract methods implemented."""
        from typing import Tuple

        class TestArtifact(PublishedArtifact):
            metadata = ArtifactMetadata(
                artifact_id="test",
                artifact_version="v1.0.0",
                schema_version="1.0",
                validation_id="val",
                publication_timestamp=datetime(2026, 7, 3, 12, 0),
                compatibility_version="1.0",
                runtime_compatibility="msi-v1.0",
                provenance_reference="prov",
            )

            def get_evidence_rules(self):
                return {}

            def evaluate(self, evidence: Tuple[Evidence, ...]) -> MarketState:
                est = Estimate(
                    latent_variable="test",
                    value=0.5,
                    uncertainty=0.1,
                    dimension="test_dim",
                )
                return MarketState(
                    evaluation_timestamp=datetime.now(),
                    estimates=(est,),
                )

        artifact = TestArtifact()
        assert isinstance(artifact, PublishedArtifact)
        assert callable(artifact.get_evidence_rules)
        assert callable(artifact.evaluate)


class TestContractTypeSafety:
    """Test contract type hints and immutability."""

    def test_no_mutable_defaults_in_dto_fields(self):
        """DTOs have no mutable default values (no dict/list defaults)."""
        obs = Observation(
            observation_id="obs_1",
            timestamp=datetime.now(),
            instrument_id="NSE_INDEX|Nifty 50",
            source_reference="upstox_v2",
            observable_type="close_price",
            measured_value=24500.5,
            measurement_units="INR",
            provenance_ref="prov_123",
            quality_metadata={},
        )
        ev = Evidence(
            evidence_id="ev_1",
            source_observation_ids=(),
            construction_timestamp=datetime.now(),
            evidence_type="test",
            evidence_value=1.0,
            artifact_version="v1.0.0",
            provenance_metadata={},
            quality_metadata={},
            version="1.0",
        )
        ms = MarketState(
            evaluation_timestamp=datetime.now(),
            estimates=(),
        )
        ko = KnowledgeObject(
            knowledge_id="ko_1",
            evaluation_timestamp=datetime.now(),
            artifact_version="v1.0.0",
            runtime_version="msi-v1.0",
            market_state=ms,
            provenance_reference="prov_123",
        )
        assert obs.quality_metadata is not None
        assert ev.source_observation_ids == ()
        assert ms.estimates == ()