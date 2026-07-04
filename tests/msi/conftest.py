import json
from datetime import datetime
from pathlib import Path

import pytest

from core.msi.contracts.artifact import ArtifactMetadata, PublishedArtifact
from core.msi.contracts.evidence import Evidence
from core.msi.contracts.observation import Observation

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
TEST_ARTIFACT_DIR = FIXTURES_DIR / "test_artifact"

_TS = datetime(2026, 7, 4, 12, 0, 0)


def _read_json(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def test_artifact_path() -> Path:
    """Absolute path to the reference test artifact directory."""
    return TEST_ARTIFACT_DIR


@pytest.fixture(scope="session")
def test_artifact_metadata_json() -> dict:
    """Parsed metadata.json from the reference test artifact."""
    return _read_json(TEST_ARTIFACT_DIR / "metadata.json")


@pytest.fixture(scope="session")
def test_artifact_evidence_rules_json() -> dict:
    """Parsed evidence_rules.json from the reference test artifact."""
    return _read_json(TEST_ARTIFACT_DIR / "evidence_rules.json")


@pytest.fixture(scope="session")
def test_artifact_provenance_json() -> dict:
    """Parsed provenance.json from the reference test artifact."""
    return _read_json(TEST_ARTIFACT_DIR / "provenance.json")


@pytest.fixture(scope="session")
def test_artifact_checksum_json() -> dict:
    """Parsed checksum.sha256 from the reference test artifact."""
    return _read_json(TEST_ARTIFACT_DIR / "checksum.sha256")


@pytest.fixture(scope="session")
def reference_test_artifact() -> PublishedArtifact:
    """Instantiated ReferenceTestArtifact from model.py."""
    import sys

    sys.path.insert(0, str(TEST_ARTIFACT_DIR))
    from model import ReferenceTestArtifact

    return ReferenceTestArtifact()


@pytest.fixture
def sample_artefact_metadata() -> ArtifactMetadata:
    """Valid ArtifactMetadata matching the reference test artifact."""
    return ArtifactMetadata(
        artifact_id="ref-test-001",
        artifact_version="v1.0.0",
        schema_version="1.0",
        validation_id="val-ref-test-001-v1",
        publication_timestamp=_TS,
        compatibility_version="1.0",
        runtime_compatibility="msi-v1.0",
        provenance_reference="prov-ref-test-001",
    )


@pytest.fixture
def sample_observations() -> tuple[Observation, ...]:
    """Tuple of sample Observations for testing."""
    return (
        Observation(
            observation_id="obs_n50_close_20260703",
            timestamp=datetime(2026, 7, 3, 15, 30),
            instrument_id="NSE_INDEX|Nifty 50",
            source_reference="upstox_v2",
            observable_type="close_price",
            measured_value=24850.75,
            measurement_units="index_points",
            provenance_ref="prov_data_20260703",
            quality_metadata={"completeness": 1.0},
        ),
        Observation(
            observation_id="obs_vix_close_20260703",
            timestamp=datetime(2026, 7, 3, 15, 30),
            instrument_id="NSE_INDEX|India VIX",
            source_reference="upstox_v2",
            observable_type="close_price",
            measured_value=18.5,
            measurement_units="percentage",
            provenance_ref="prov_data_20260703",
            quality_metadata={"completeness": 1.0},
        ),
    )


@pytest.fixture
def sample_evidence() -> tuple[Evidence, ...]:
    """Tuple of sample Evidence for testing regime evaluation."""
    ts = datetime(2026, 7, 3, 16, 0)
    return (
        Evidence(
            evidence_id="ev_vix_close_20260703",
            source_observation_ids=("obs_vix_close_20260703",),
            construction_timestamp=ts,
            evidence_type="vix_close",
            evidence_value=18.5,
            artifact_version="v1.0.0",
            provenance_metadata={"source": "test"},
            quality_metadata={"stability": 0.9},
            version="1.0",
        ),
        Evidence(
            evidence_id="ev_n50_close_20260703",
            source_observation_ids=("obs_n50_close_20260703",),
            construction_timestamp=ts,
            evidence_type="nifty_close",
            evidence_value=24850.75,
            artifact_version="v1.0.0",
            provenance_metadata={"source": "test"},
            quality_metadata={"stability": 0.9},
            version="1.0",
        ),
    )


@pytest.fixture
def sample_evidence_high_vix() -> tuple[Evidence, ...]:
    """Evidence tuple with VIX at high-volatility level (≥25)."""
    ts = datetime(2026, 7, 3, 16, 0)
    return (
        Evidence(
            evidence_id="ev_vix_close_high",
            source_observation_ids=("obs_vix_close",),
            construction_timestamp=ts,
            evidence_type="vix_close",
            evidence_value=28.0,
            artifact_version="v1.0.0",
            provenance_metadata={"source": "test"},
            quality_metadata={"stability": 0.9},
            version="1.0",
        ),
    )


@pytest.fixture
def sample_evidence_low_vix() -> tuple[Evidence, ...]:
    """Evidence tuple with VIX at low-volatility level (<15)."""
    ts = datetime(2026, 7, 3, 16, 0)
    return (
        Evidence(
            evidence_id="ev_vix_close_low",
            source_observation_ids=("obs_vix_close",),
            construction_timestamp=ts,
            evidence_type="vix_close",
            evidence_value=11.5,
            artifact_version="v1.0.0",
            provenance_metadata={"source": "test"},
            quality_metadata={"stability": 0.9},
            version="1.0",
        ),
    )


@pytest.fixture
def sample_evidence_empty() -> tuple[Evidence, ...]:
    """Empty evidence tuple."""
    return ()
