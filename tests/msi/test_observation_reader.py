from datetime import date, datetime

import pytest

from core.msi.dra.duckdb_observation_reader import DuckDBObservationReader
from core.msi.dra.errors import ObservationReadError
from core.msi.contracts.observation import Observation
from dataclasses import FrozenInstanceError

_TEST_DB_PATH = "tests/msi/fixtures/test_data.duckdb"


class TestDuckDBObservationReader:
    """DuckDBObservationReader tests (MSI-003 §4)."""

    def test_read_observations_for_date(self):
        """Read observations for a date returns correct count and values."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))

        assert len(observations) == 10  # 5 observables × 2 candles

        for obs in observations:
            assert isinstance(obs, Observation)
            assert obs.instrument_id == "NSE_INDEX|Nifty 50"
            assert obs.timestamp.date() == evaluation_date

        close_obs = [o for o in observations if o.observable_type == "close_price"]
        assert len(close_obs) == 2
        close_values = sorted([o.measured_value for o in close_obs])
        assert close_values[0] == 24680.0
        assert close_values[1] == 24700.0

    def test_observation_ids_are_deterministic(self):
        """Same input produces same observation IDs."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        obs1 = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))
        obs2 = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))

        assert len(obs1) == len(obs2)
        for o1, o2 in zip(sorted(obs1, key=lambda o: o.observation_id),
                          sorted(obs2, key=lambda o: o.observation_id)):
            assert o1.observation_id == o2.observation_id

    def test_observation_ids_are_deterministic_across_reader_instances(self):
        """Different reader instances produce same observation IDs."""
        reader1 = DuckDBObservationReader(_TEST_DB_PATH)
        reader2 = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        obs1 = reader1.read(evaluation_date, ("NSE_INDEX|Nifty 50",))
        obs2 = reader2.read(evaluation_date, ("NSE_INDEX|Nifty 50",))

        assert len(obs1) == len(obs2)
        id1_set = {o.observation_id for o in obs1}
        id2_set = {o.observation_id for o in obs2}
        assert id1_set == id2_set

    def test_missing_symbol_raises(self):
        """Reading a symbol not in database raises ObservationReadError."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        with pytest.raises(ObservationReadError) as exc_info:
            reader.read(evaluation_date, ("NONEXISTENT|Symbol",))

        assert "not found" in str(exc_info.value)

    def test_empty_result_for_future_date(self):
        """Reading a date with no data returns empty tuple."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        future_date = date(2099, 1, 1)

        observations = reader.read(future_date, ("NSE_INDEX|Nifty 50",))

        assert observations == ()

    def test_empty_result_for_symbol_with_no_data_on_date(self):
        """Symbol exists but has no data on requested date returns empty tuple."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        date_with_no_nifty = date(2024, 7, 4)

        observations = reader.read(date_with_no_nifty, ("NSE_INDEX|Nifty 50",))

        assert observations == ()

    def test_multiple_symbols(self):
        """Read observations for multiple symbols."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(
            evaluation_date,
            ("NSE_INDEX|Nifty 50", "NSE_INDEX|India VIX")
        )

        assert len(observations) == 20  # 10 per symbol

        nifty_obs = [o for o in observations if o.instrument_id == "NSE_INDEX|Nifty 50"]
        vix_obs = [o for o in observations if o.instrument_id == "NSE_INDEX|India VIX"]

        assert len(nifty_obs) == 10
        assert len(vix_obs) == 10

    def test_chronological_ordering(self):
        """Observations are returned in timestamp order."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))

        timestamps = [o.timestamp for o in observations]
        assert timestamps == sorted(timestamps)

    def test_symbol_ordering_preserved_in_output(self):
        """When same timestamps, symbols follow request order."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(
            evaluation_date,
            ("NSE_INDEX|Nifty 50", "NSE_INDEX|India VIX")
        )

        nifty_obs = [o for o in observations if o.instrument_id == "NSE_INDEX|Nifty 50"]
        vix_obs = [o for o in observations if o.instrument_id == "NSE_INDEX|India VIX"]

        first_nifty_timestamp = min(nifty_obs, key=lambda o: o.timestamp).timestamp
        first_vix_timestamp = min(vix_obs, key=lambda o: o.timestamp).timestamp

        nifty_indices = [i for i, o in enumerate(observations) if o.instrument_id == "NSE_INDEX|Nifty 50"]
        vix_indices = [i for i, o in enumerate(observations) if o.instrument_id == "NSE_INDEX|India VIX"]

        assert min(nifty_indices) < min(vix_indices), "Nifty observations should appear before VIX in output"

    def test_observations_are_immutable(self):
        """Returned Observation DTOs are frozen."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))

        with pytest.raises(FrozenInstanceError):
            observations[0].measured_value = 999.0

    def test_empty_symbols_returns_empty_tuple(self):
        """Empty symbols tuple returns empty result."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(evaluation_date, ())

        assert observations == ()

    def test_observable_types_correct(self):
        """Each candle produces observations for all observable types."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))

        observable_types = {o.observable_type for o in observations}
        expected_types = {"open_price", "high_price", "low_price", "close_price", "volume"}

        assert observable_types == expected_types

    def test_measurement_units_correct(self):
        """Observable types have correct measurement units."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))

        for obs in observations:
            if obs.observable_type == "volume":
                assert obs.measurement_units == "shares"
            else:
                assert obs.measurement_units == "index_points"

    def test_point_in_time_correctness(self):
        """Each observation represents a single point-in-time measurement."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))

        for obs in observations:
            assert isinstance(obs.timestamp, datetime)
            assert obs.instrument_id
            assert obs.observable_type
            assert isinstance(obs.measured_value, (int, float))
            assert isinstance(obs.observation_id, str)
            assert len(obs.observation_id) == 32  # SHA-256 prefix

    def test_quality_metadata_present(self):
        """All observations have quality metadata."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))

        for obs in observations:
            assert "completeness" in obs.quality_metadata
            assert "validity" in obs.quality_metadata

    def test_source_reference_settable(self):
        """Custom source reference is preserved in observations."""
        reader = DuckDBObservationReader(
            _TEST_DB_PATH,
            source_reference="custom_source"
        )
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))

        for obs in observations:
            assert obs.source_reference == "custom_source"

    def test_provenance_ref_settable(self):
        """Custom provenance reference is preserved in observations."""
        reader = DuckDBObservationReader(
            _TEST_DB_PATH,
            provenance_ref="custom_provenance"
        )
        evaluation_date = date(2024, 7, 1)

        observations = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))

        for obs in observations:
            assert obs.provenance_ref == "custom_provenance"

    def test_multiple_reads_are_deterministic(self):
        """Multiple sequential reads produce identical results."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        evaluation_date = date(2024, 7, 2)

        results = []
        for _ in range(3):
            obs = reader.read(evaluation_date, ("NSE_INDEX|Nifty 50",))
            results.append([o.observation_id for o in sorted(obs, key=lambda o: o.observation_id)])

        assert results[0] == results[1] == results[2]

    def test_reader_is_subclass_of_abc(self):
        """DuckDBObservationReader satisfies the ObservationReader ABC."""
        from core.msi.interfaces.observation_reader import ObservationReader
        assert issubclass(DuckDBObservationReader, ObservationReader)

    def test_reader_implements_read_method(self):
        """DuckDBObservationReader has a callable read method."""
        reader = DuckDBObservationReader(_TEST_DB_PATH)
        assert callable(reader.read)

    def test_invalid_db_path_raises(self):
        """Non-existent DuckDB path raises ObservationReadError."""
        with pytest.raises(ObservationReadError) as exc_info:
            DuckDBObservationReader("nonexistent/path.db")

        assert "not found" in str(exc_info.value)