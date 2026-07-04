import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..contracts.artifact import PublishedArtifact
from ..contracts.evidence import Evidence
from ..contracts.observation import Observation
from ..interfaces.evidence_builder import EvidenceBuilder
from .errors import EvidenceConstructionError

_DEFAULT_FIELD_MAPPING: Dict[str, str] = {
    "close": "close_price",
    "open": "open_price",
    "high": "high_price",
    "low": "low_price",
    "volume": "volume",
}


class DefaultEvidenceBuilder(EvidenceBuilder):
    """Default EvidenceBuilder (MSI-004 §2/§5).

    Converts immutable Observations into immutable Evidence using
    construction rules carried by a PublishedArtifact. The builder
    authors no rules — it only executes them.

    Deterministic: identical Observations + identical Artifact produce
    bit-identical Evidence (including evidence_ids).
    """

    def __init__(self, field_mapping: Optional[Dict[str, str]] = None):
        self._field_mapping = _DEFAULT_FIELD_MAPPING.copy()
        if field_mapping is not None:
            self._field_mapping.update(field_mapping)

    def build(
        self,
        observations: Tuple[Observation, ...],
        artifact: PublishedArtifact,
    ) -> Tuple[Evidence, ...]:
        """Apply artifact-carried rules to Observations (MSI-004 §8).

        Args:
            observations: Immutable Observations from Platform stores.
            artifact: PublishedArtifact carrying evidence rules.

        Returns:
            Tuple of immutable Evidence DTOs with deterministic IDs.

        Raises:
            EvidenceConstructionError: Rules cannot be applied.
        """
        if not observations:
            return ()

        rules = artifact.get_evidence_rules()
        features = self._extract_features(rules)
        self._validate_features(features)
        required_symbols = self._get_required_symbols(rules)

        self._validate_required_symbols_present(
            observations, required_symbols
        )

        by_symbol = self._group_by_symbol(observations)
        eval_boundary = self._determine_eval_boundary(
            by_symbol, required_symbols
        )

        evidence_list: List[Evidence] = []
        for feature in features:
            ev = self._apply_feature(
                feature, by_symbol, artifact, eval_boundary
            )
            evidence_list.append(ev)

        return tuple(evidence_list)

    def _extract_features(self, rules: dict) -> List[dict]:
        features = rules.get("features")
        if features is None:
            raise EvidenceConstructionError(
                "Evidence rules missing required 'features' list"
            )
        if not isinstance(features, list) or len(features) == 0:
            raise EvidenceConstructionError(
                "'features' must be a non-empty list"
            )
        return features

    def _validate_features(self, features: List[dict]) -> None:
        for feat in features:
            if not isinstance(feat, dict):
                raise EvidenceConstructionError(
                    "Each feature must be a dict"
                )
            for key in ("name", "source", "field"):
                if key not in feat:
                    raise EvidenceConstructionError(
                        f"Feature missing required field '{key}': {feat}"
                    )

    def _get_required_symbols(self, rules: dict) -> List[str]:
        symbols = rules.get("required_symbols")
        if symbols is None:
            raise EvidenceConstructionError(
                "Evidence rules missing 'required_symbols'"
            )
        if not isinstance(symbols, list) or len(symbols) == 0:
            raise EvidenceConstructionError(
                "'required_symbols' must be a non-empty list"
            )
        return symbols

    def _validate_required_symbols_present(
        self,
        observations: Tuple[Observation, ...],
        required_symbols: List[str],
    ) -> None:
        present = {o.instrument_id for o in observations}
        missing = [s for s in required_symbols if s not in present]
        if missing:
            raise EvidenceConstructionError(
                f"Required symbols missing from observations: "
                f"{', '.join(missing)}"
            )

    def _group_by_symbol(
        self, observations: Tuple[Observation, ...]
    ) -> Dict[str, List[Observation]]:
        result: Dict[str, List[Observation]] = {}
        for o in observations:
            result.setdefault(o.instrument_id, []).append(o)
        for symbol in result:
            result[symbol].sort(key=lambda x: x.timestamp)
        return result

    def _determine_eval_boundary(
        self,
        by_symbol: Dict[str, List[Observation]],
        required_symbols: List[str],
    ) -> datetime:
        """Derive the evaluation boundary — the latest timestamp at which
        ALL required symbols have data. Observations after this boundary
        are excluded (point-in-time correctness, no look-ahead)."""
        per_symbol_max: List[datetime] = []
        for symbol in required_symbols:
            obs_list = by_symbol.get(symbol, [])
            if obs_list:
                per_symbol_max.append(obs_list[-1].timestamp)
        if not per_symbol_max:
            raise EvidenceConstructionError(
                "No observations available for required symbols"
            )
        return min(per_symbol_max)

    def _apply_feature(
        self,
        feature: dict,
        by_symbol: Dict[str, List[Observation]],
        artifact: PublishedArtifact,
        eval_boundary: datetime,
    ) -> Evidence:
        name: str = feature["name"]
        source: str = feature["source"]
        field: str = feature["field"]
        transform: str = feature.get("transform", "identity")

        if transform != "identity":
            raise EvidenceConstructionError(
                f"Unsupported transform '{transform}' "
                f"for feature '{name}'"
            )

        source_obs = by_symbol.get(source, [])
        if not source_obs:
            raise EvidenceConstructionError(
                f"No observations for source '{source}' "
                f"in feature '{name}'"
            )

        obs_type = self._field_mapping.get(field, field)

        matching = [
            o
            for o in source_obs
            if o.observable_type == obs_type
            and o.timestamp <= eval_boundary
        ]
        if not matching:
            raise EvidenceConstructionError(
                f"No observations matching field '{field}' "
                f"(observable_type='{obs_type}') "
                f"for feature '{name}'"
            )

        latest = matching[-1]

        evidence_id = self._make_evidence_id(
            artifact_version=artifact.metadata.artifact_version,
            evidence_type=name,
            source_observation_ids=(latest.observation_id,),
            evidence_value=latest.measured_value,
        )

        return Evidence(
            evidence_id=evidence_id,
            source_observation_ids=(latest.observation_id,),
            construction_timestamp=eval_boundary,
            evidence_type=name,
            evidence_value=latest.measured_value,
            artifact_version=artifact.metadata.artifact_version,
            provenance_metadata={
                "rule_name": name,
                "source": source,
                "transform": transform,
            },
            quality_metadata=latest.quality_metadata,
            version="1.0",
        )

    def _make_evidence_id(
        self,
        artifact_version: str,
        evidence_type: str,
        source_observation_ids: Tuple[str, ...],
        evidence_value: float,
    ) -> str:
        content = (
            f"{artifact_version}|{evidence_type}|"
            f"{'|'.join(sorted(source_observation_ids))}|"
            f"{evidence_value}"
        )
        return hashlib.sha256(content.encode()).hexdigest()
