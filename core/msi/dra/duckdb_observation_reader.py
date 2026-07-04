import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import duckdb

from ..contracts.observation import Observation
from ..interfaces.observation_reader import ObservationReader
from .errors import ObservationReadError


def _make_observation_id(
    instrument_id: str,
    observable_type: str,
    timestamp: datetime,
) -> str:
    """Generate deterministic observation ID from input fields."""
    key = f"{instrument_id}|{observable_type}|{timestamp.isoformat()}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


class DuckDBObservationReader(ObservationReader):
    """DuckDB-based ObservationReader (MSI-003 §4).

    Reads immutable market observations from DuckDB candles table.
    Produces point-in-time correct, immutable Observation DTOs.
    """

    _DEFAULT_SOURCE_REFERENCE = "platform_duckdb_v1"
    _DEFAULT_PROVENANCE_REF = "prov_platform_data"

    _COLUMN_TO_OBSERVABLE: Dict[str, str] = {
        "open": "open_price",
        "high": "high_price",
        "low": "low_price",
        "close": "close_price",
        "volume": "volume",
    }

    def __init__(
        self,
        db_path: str,
        table_name: str = "candles",
        source_reference: Optional[str] = None,
        provenance_ref: Optional[str] = None,
    ):
        """Initialize DuckDBObservationReader.

        Args:
            db_path: Path to DuckDB database file.
            table_name: Name of table containing candle data (default: "candles").
            source_reference: Source identifier for provenance (default: "platform_duckdb_v1").
            provenance_ref: Provenance reference (default: "prov_platform_data").
        """
        self._db_path = Path(db_path)
        self._table_name = table_name
        self._source_reference = source_reference or self._DEFAULT_SOURCE_REFERENCE
        self._provenance_ref = provenance_ref or self._DEFAULT_PROVENANCE_REF

        if not self._db_path.exists():
            raise ObservationReadError(
                f"DuckDB file not found: {db_path}"
            )

    def read(
        self,
        evaluation_date: date,
        symbols: Tuple[str, ...],
    ) -> Tuple[Observation, ...]:
        """Read Observations for the given date and symbols.

        Args:
            evaluation_date: Date to read Observations for.
            symbols: Canonical instrument identifiers.

        Returns:
            Tuple of immutable Observation objects, point-in-time ordered.
            Order: symbols in request order, then timestamps ascending within each symbol.

        Raises:
            ObservationReadError: DuckDB file does not exist, query fails,
                or required symbols do not exist in the database.
        """
        if not symbols:
            return ()

        observations: List[Observation] = []

        try:
            with duckdb.connect(str(self._db_path)) as conn:
                for symbol in symbols:
                    symbol_observations = self._read_symbol(
                        conn,
                        evaluation_date,
                        symbol,
                    )
                    observations.extend(symbol_observations)

        except duckdb.Error as e:
            raise ObservationReadError(
                f"Failed to read observations from DuckDB: {e}"
            ) from e

        return tuple(observations)

    def _read_symbol(
        self,
        conn: duckdb.DuckDBPyConnection,
        evaluation_date: date,
        symbol: str,
    ) -> List[Observation]:
        """Read all Observations for a single symbol on a date.

        Returns:
            List of Observations for the symbol, chronologically ordered.

        Raises:
            ObservationReadError: Symbol does not exist in the database.
        """
        exists_query = f"""
            SELECT COUNT(*) FROM {self._table_name}
            WHERE symbol = ?
        """
        exists = conn.execute(exists_query, (symbol,)).fetchone()[0]
        if exists == 0:
            raise ObservationReadError(
                f"Symbol not found in database: {symbol}"
            )

        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM {self._table_name}
            WHERE symbol = ? AND DATE(timestamp) = ?
            ORDER BY timestamp ASC
        """

        result = conn.execute(query, (symbol, evaluation_date)).fetchall()

        if not result:
            return []

        observations: List[Observation] = []

        for row in result:
            timestamp_dt, open_val, high_val, low_val, close_val, volume_val = row

            timestamp: datetime = timestamp_dt
            measurement_units: str = ""

            for column, observable_type in self._COLUMN_TO_OBSERVABLE.items():
                value: float

                if column == "open":
                    value = open_val
                    measurement_units = "index_points"
                elif column == "high":
                    value = high_val
                    measurement_units = "index_points"
                elif column == "low":
                    value = low_val
                    measurement_units = "index_points"
                elif column == "close":
                    value = close_val
                    measurement_units = "index_points"
                elif column == "volume":
                    value = float(volume_val)
                    measurement_units = "shares"
                else:
                    continue

                obs = Observation(
                    observation_id=_make_observation_id(symbol, observable_type, timestamp),
                    timestamp=timestamp,
                    instrument_id=symbol,
                    source_reference=self._source_reference,
                    observable_type=observable_type,
                    measured_value=value,
                    measurement_units=measurement_units,
                    provenance_ref=self._provenance_ref,
                    quality_metadata={"completeness": 1.0, "validity": 1.0},
                )
                observations.append(obs)

        return observations