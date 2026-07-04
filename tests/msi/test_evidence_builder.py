from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from core.msi.contracts.artifact import PublishedArtifact
from core.msi.contracts.evidence import Evidence
from core.msi.contracts.observation import Observation
from core.msi.dra.default_evidence_builder import DefaultEvidenceBuilder
from core.msi.dra.errors import EvidenceConstructionError

_TS = datetime(2026, 7, 4, 12, 0, 0)


class TestDefaultEvidenceBuilder:
    """DefaultEvidenceBuilder tests (MSI-004 §2/§5/§8)."""

    def test_build_evidence_from_test_rules(
        self, reference_test_artifact, sample_observations
    ):
        """Build evidence from M1 test artifact rules."""
        builder = DefaultEvidenceBuilder()
        result = builder.build(sample_observations, reference_test_artifact)
        assert len(result) == 2
        types = {e.evidence_type for e in result}
        assert types == {"vix_close", "nifty_close"}

    def test_build_evidence_values_correct(
        self, reference_test_artifact, sample_observations
    ):
        """Evidence values match the most recent observations."""
        builder = DefaultEvidenceBuilder()
        result = builder.build(sample_observations, reference_test_artifact)
        ev_dict = {e.evidence_type: e for e in result}
        assert ev_dict["vix_close"].evidence_value == 18.5
        assert ev_dict["nifty_close"].evidence_value == 24850.75

    def test_build_evidence_artifact_version_propagated(
        self, reference_test_artifact, sample_observations
    ):
        """Evidence carries the correct artifact version."""
        builder = DefaultEvidenceBuilder()
        result = builder.build(sample_observations, reference_test_artifact)
        for ev in result:
            assert ev.artifact_version == "v1.0.0"

    def test_build_evidence_construction_timestamp(
        self, reference_test_artifact, sample_observations
    ):
        """Evidence construction_timestamp matches eval boundary."""
        builder = DefaultEvidenceBuilder()
        result = builder.build(sample_observations, reference_test_artifact)
        expected_ts = datetime(2026, 7, 3, 15, 30)
        for ev in result:
            assert ev.construction_timestamp == expected_ts

    def test_evidence_determinism(
        self, reference_test_artifact, sample_observations
    ):
        """Identical inputs produce identical evidence output."""
        builder = DefaultEvidenceBuilder()
        r1 = builder.build(sample_observations, reference_test_artifact)
        r2 = builder.build(sample_observations, reference_test_artifact)
        assert r1 == r2
        assert len(r1) == len(r2)
        for e1, e2 in zip(r1, r2):
            assert e1.evidence_id == e2.evidence_id
            assert e1.evidence_value == e2.evidence_value
            assert e1.source_observation_ids == e2.source_observation_ids

    def test_evidence_ids_deterministic(
        self, reference_test_artifact, sample_observations
    ):
        """Evidence IDs are deterministic (hash-based, not random)."""
        builder = DefaultEvidenceBuilder()
        r1 = builder.build(sample_observations, reference_test_artifact)
        r2 = builder.build(sample_observations, reference_test_artifact)
        for e1, e2 in zip(r1, r2):
            assert e1.evidence_id == e2.evidence_id
            assert len(e1.evidence_id) == 64  # SHA-256 hex digest

    def test_evidence_ids_hash_content(
        self, reference_test_artifact, sample_observations
    ):
        """Same inputs produce same IDs across builder instances."""
        b1 = DefaultEvidenceBuilder()
        b2 = DefaultEvidenceBuilder()
        r1 = b1.build(sample_observations, reference_test_artifact)
        r2 = b2.build(sample_observations, reference_test_artifact)
        for e1, e2 in zip(r1, r2):
            assert e1.evidence_id == e2.evidence_id

    def test_reject_missing_symbol_in_rules(
        self, reference_test_artifact
    ):
        """Missing required symbol raises EvidenceConstructionError."""
        builder = DefaultEvidenceBuilder()
        obs = (
            Observation(
                observation_id="obs_n50",
                timestamp=_TS,
                instrument_id="NSE_INDEX|Nifty 50",
                source_reference="test",
                observable_type="close_price",
                measured_value=24000.0,
                measurement_units="index_points",
                provenance_ref="prov_test",
                quality_metadata={},
            ),
        )
        with pytest.raises(EvidenceConstructionError) as exc:
            builder.build(obs, reference_test_artifact)
        assert "India VIX" in str(exc.value)

    def test_source_observation_ids_correct(
        self, reference_test_artifact, sample_observations
    ):
        """Evidence source_observation_ids reference the source observations."""
        builder = DefaultEvidenceBuilder()
        result = builder.build(sample_observations, reference_test_artifact)
        obs_dict = {o.observation_id: o for o in sample_observations}
        for ev in result:
            for src_id in ev.source_observation_ids:
                assert src_id in obs_dict
                src_obs = obs_dict[src_id]
                assert src_obs.observable_type == "close_price"

    def test_no_look_ahead(self, reference_test_artifact):
        """Observations after the evaluation boundary are not used."""
        builder = DefaultEvidenceBuilder()
        boundary = datetime(2026, 7, 3, 15, 30)
        obs = (
            Observation(
                observation_id="obs_n50_close",
                timestamp=boundary,
                instrument_id="NSE_INDEX|Nifty 50",
                source_reference="test",
                observable_type="close_price",
                measured_value=24500.0,
                measurement_units="index_points",
                provenance_ref="prov_test",
                quality_metadata={},
            ),
            Observation(
                observation_id="obs_vix_close",
                timestamp=boundary,
                instrument_id="NSE_INDEX|India VIX",
                source_reference="test",
                observable_type="close_price",
                measured_value=15.0,
                measurement_units="percentage",
                provenance_ref="prov_test",
                quality_metadata={},
            ),
            Observation(
                observation_id="obs_n50_look_ahead",
                timestamp=datetime(2026, 7, 4, 10, 0),
                instrument_id="NSE_INDEX|Nifty 50",
                source_reference="test",
                observable_type="close_price",
                measured_value=99999.0,
                measurement_units="index_points",
                provenance_ref="prov_test",
                quality_metadata={},
            ),
        )
        result = builder.build(obs, reference_test_artifact)
        ev_dict = {e.evidence_type: e for e in result}
        assert ev_dict["nifty_close"].evidence_value == 24500.0
        assert ev_dict["nifty_close"].evidence_value != 99999.0

    def test_no_look_ahead_isolation(
        self, reference_test_artifact
    ):
        """Multiple observations for same symbol use the most recent in-boundary."""
        builder = DefaultEvidenceBuilder()
        boundary = datetime(2026, 7, 3, 15, 30)
        obs = (
            Observation(
                observation_id="obs_n50_early",
                timestamp=datetime(2026, 7, 3, 10, 0),
                instrument_id="NSE_INDEX|Nifty 50",
                source_reference="test",
                observable_type="close_price",
                measured_value=24000.0,
                measurement_units="index_points",
                provenance_ref="prov_test",
                quality_metadata={},
            ),
            Observation(
                observation_id="obs_n50_late",
                timestamp=boundary,
                instrument_id="NSE_INDEX|Nifty 50",
                source_reference="test",
                observable_type="close_price",
                measured_value=24500.0,
                measurement_units="index_points",
                provenance_ref="prov_test",
                quality_metadata={},
            ),
            Observation(
                observation_id="obs_vix_close",
                timestamp=boundary,
                instrument_id="NSE_INDEX|India VIX",
                source_reference="test",
                observable_type="close_price",
                measured_value=15.0,
                measurement_units="percentage",
                provenance_ref="prov_test",
                quality_metadata={},
            ),
        )
        result = builder.build(obs, reference_test_artifact)
        ev_dict = {e.evidence_type: e for e in result}
        assert ev_dict["nifty_close"].evidence_value == 24500.0

    def test_empty_observations_returns_empty_evidence(
        self, reference_test_artifact
    ):
        """Empty observations produce an empty tuple."""
        builder = DefaultEvidenceBuilder()
        result = builder.build((), reference_test_artifact)
        assert result == ()

    def test_builder_is_evidence_builder_subclass(self):
        """DefaultEvidenceBuilder satisfies the EvidenceBuilder ABC."""
        from core.msi.interfaces.evidence_builder import EvidenceBuilder
        assert issubclass(DefaultEvidenceBuilder, EvidenceBuilder)

    def test_builder_has_build_method(self):
        """DefaultEvidenceBuilder exposes callable build method."""
        builder = DefaultEvidenceBuilder()
        assert callable(builder.build)

    def test_unsupported_transform_raises(
        self, reference_test_artifact, sample_observations
    ):
        """Unsupported transform raises EvidenceConstructionError."""
        from core.msi.contracts.artifact import PublishedArtifact

        class BadTransformArtifact(PublishedArtifact):
            metadata = reference_test_artifact.metadata
            def get_evidence_rules(self):
                return {
                    "features": [
                        {
                            "name": "bad_feat",
                            "source": "NSE_INDEX|Nifty 50",
                            "field": "close",
                            "transform": "pct_change",
                        }
                    ],
                    "lookback_days": 90,
                    "required_symbols": ["NSE_INDEX|Nifty 50"],
                    "rule_format_version": "1.0",
                }
            def evaluate(self, evidence):
                from core.msi.contracts.market_state import MarketState
                from core.msi.contracts.estimate import Estimate
                return MarketState(_TS, (Estimate("x", 0.0, 0.1, "d"),))

        builder = DefaultEvidenceBuilder()
        with pytest.raises(EvidenceConstructionError) as exc:
            builder.build((sample_observations[0],), BadTransformArtifact())
        assert "pct_change" in str(exc.value)

    def test_malformed_rules_no_features_raises(
        self, reference_test_artifact, sample_observations
    ):
        """Rules without features list raise EvidenceConstructionError."""
        from core.msi.contracts.artifact import PublishedArtifact

        class NoFeatureArtifact(PublishedArtifact):
            metadata = reference_test_artifact.metadata
            def get_evidence_rules(self):
                return {"rule_format_version": "1.0"}
            def evaluate(self, evidence):
                from core.msi.contracts.market_state import MarketState
                from core.msi.contracts.estimate import Estimate
                return MarketState(_TS, (Estimate("x", 0.0, 0.1, "d"),))

        builder = DefaultEvidenceBuilder()
        with pytest.raises(EvidenceConstructionError):
            builder.build(sample_observations, NoFeatureArtifact())

    def test_malformed_rules_empty_features_raises(
        self, reference_test_artifact, sample_observations
    ):
        """Empty features list raises EvidenceConstructionError."""
        from core.msi.contracts.artifact import PublishedArtifact

        class EmptyFeatureArtifact(PublishedArtifact):
            metadata = reference_test_artifact.metadata
            def get_evidence_rules(self):
                return {
                    "features": [],
                    "lookback_days": 90,
                    "required_symbols": ["NSE_INDEX|Nifty 50"],
                    "rule_format_version": "1.0",
                }
            def evaluate(self, evidence):
                from core.msi.contracts.market_state import MarketState
                from core.msi.contracts.estimate import Estimate
                return MarketState(_TS, (Estimate("x", 0.0, 0.1, "d"),))

        builder = DefaultEvidenceBuilder()
        with pytest.raises(EvidenceConstructionError):
            builder.build(sample_observations, EmptyFeatureArtifact())

    def test_evidence_is_immutable(
        self, reference_test_artifact, sample_observations
    ):
        """Returned Evidence DTOs are frozen."""
        builder = DefaultEvidenceBuilder()
        result = builder.build(sample_observations, reference_test_artifact)
        for ev in result:
            with pytest.raises(FrozenInstanceError):
                ev.evidence_value = 0.0

    def test_evidence_version_string(
        self, reference_test_artifact, sample_observations
    ):
        """Evidence version is correctly set."""
        builder = DefaultEvidenceBuilder()
        result = builder.build(sample_observations, reference_test_artifact)
        for ev in result:
            assert ev.version == "1.0"

    def test_evidence_provenance_metadata(
        self, reference_test_artifact, sample_observations
    ):
        """Evidence provenance_metadata contains rule info."""
        builder = DefaultEvidenceBuilder()
        result = builder.build(sample_observations, reference_test_artifact)
        for ev in result:
            assert "rule_name" in ev.provenance_metadata
            assert "source" in ev.provenance_metadata
            assert "transform" in ev.provenance_metadata
            assert ev.provenance_metadata["transform"] == "identity"

    def test_evidence_source_observations_traceable(
        self, reference_test_artifact, sample_observations
    ):
        """source_observation_ids length matches documented provenance."""
        builder = DefaultEvidenceBuilder()
        result = builder.build(sample_observations, reference_test_artifact)
        for ev in result:
            assert len(ev.source_observation_ids) == 1

    def test_multiple_calls_same_artifact(
        self, reference_test_artifact, sample_observations
    ):
        """Builder can be reused across multiple calls."""
        builder = DefaultEvidenceBuilder()
        r1 = builder.build(sample_observations, reference_test_artifact)
        r2 = builder.build(sample_observations, reference_test_artifact)
        assert r1 == r2
