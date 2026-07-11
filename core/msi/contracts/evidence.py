from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple


@dataclass(frozen=True)
class Evidence:
    """Evidence DTO (MSI-004 §7).

    Information derived from one or more Observations that supports inference.
    Immutable; preserves provenance through source_observation_ids.
    """

    evidence_id: str
    source_observation_ids: Tuple[str, ...]
    construction_timestamp: datetime
    evidence_type: str
    evidence_value: float
    artifact_version: str
    provenance_metadata: Dict[str, object]
    quality_metadata: Dict[str, object]
    version: str