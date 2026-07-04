from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass(frozen=True)
class Observation:
    """Observation DTO (MSI-003 §5).

    A point-in-time measurement of an Observable from Platform-persisted market data.
    Immutable; preserves point-in-time correctness and provenance.
    """

    observation_id: str
    timestamp: datetime
    instrument_id: str
    source_reference: str
    observable_type: str
    measured_value: float
    measurement_units: str
    provenance_ref: str
    quality_metadata: Dict[str, object]