from abc import ABC, abstractmethod
from datetime import date
from typing import Tuple

from ..contracts.observation import Observation


class ObservationReader(ABC):
    """ObservationReader interface (MSI-003 §4).

    Read-contract over Platform-persisted market data.
    Reads only from immutable stored facts; no acquisition.
    """

    @abstractmethod
    def read(self, evaluation_date: date, symbols: Tuple[str, ...]) -> Tuple[Observation, ...]:
        """Read Observations for the given date and symbols. Deterministic.

        Args:
            evaluation_date: Date to read Observations for.
            symbols: Canonical instrument identifiers.

        Returns:
            Tuple of immutable Observation objects, point-in-time ordered.

        Raises:
            ObservationReadError: Required data unavailable or insufficient lookback.
                (Exception type defined in M2 — DRA Implementation Plan §16.)
        """
        ...