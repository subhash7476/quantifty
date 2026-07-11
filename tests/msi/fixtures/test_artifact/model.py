from datetime import datetime
from typing import Dict, Tuple

from core.msi.contracts.artifact import ArtifactMetadata, PublishedArtifact
from core.msi.contracts.estimate import Estimate
from core.msi.contracts.evidence import Evidence
from core.msi.contracts.market_state import MarketState

_ARTIFACT_ID = "ref-test-001"
_ARTIFACT_VERSION = "v1.0.0"

_METADATA = ArtifactMetadata(
    artifact_id=_ARTIFACT_ID,
    artifact_version=_ARTIFACT_VERSION,
    schema_version="1.0",
    validation_id="val-ref-test-001-v1",
    publication_timestamp=datetime(2026, 7, 4, 12, 0, 0),
    compatibility_version="1.0",
    runtime_compatibility="msi-v1.0",
    provenance_reference="prov-ref-test-001",
)

_EVIDENCE_RULES: Dict[str, object] = {
    "features": [
        {
            "name": "vix_close",
            "source": "NSE_INDEX|India VIX",
            "field": "close",
            "transform": "identity",
            "description": "India VIX closing level — measures expected volatility",
        },
        {
            "name": "nifty_close",
            "source": "NSE_INDEX|Nifty 50",
            "field": "close",
            "transform": "identity",
            "description": "Nifty 50 closing price",
        },
    ],
    "lookback_days": 90,
    "required_symbols": [
        "NSE_INDEX|Nifty 50",
        "NSE_INDEX|India VIX",
    ],
    "rule_format_version": "1.0",
}

_MARKET_REGIME = "market_regime"
_REGIME_DIMENSION = "regime_class"
_TREND_STRENGTH = "trend_strength"
_TREND_DIMENSION = "trend_magnitude"

_HIGH_VOL_THRESHOLD = 25.0
_LOW_VOL_THRESHOLD = 15.0

_SENTINEL_TS = datetime(2026, 7, 4, 12, 0, 0)


class ReferenceTestArtifact(PublishedArtifact):
    """Minimal deterministic PublishedArtifact for pipeline contract validation (MSI-007 §11).

    Implements a simple threshold classifier:
      - VIX >= 25.0  → high_volatility regime (value=2.0)
      - VIX >= 15.0  → normal regime (value=1.0)
      - VIX <  15.0  → low_volatility regime (value=0.0)

    Always produces a fixed trend_strength estimate for contract verification.
    Entirely deterministic; identical Evidence input produces identical MarketState output.
    """

    metadata = _METADATA

    def get_evidence_rules(self) -> Dict[str, object]:
        """Return validated evidence-construction rules (MSI-004 §2)."""
        return _EVIDENCE_RULES

    def evaluate(self, evidence: Tuple[Evidence, ...]) -> MarketState:
        """Deterministic threshold evaluation (MSI-005 §7).

        Args:
            evidence: Tuple of Evidence objects keyed by evidence_type.
                      Expected: evidence_type="vix_close" for VIX level.

        Returns:
            MarketState with two Estimates: market_regime and trend_strength.
        """
        ev_dict: Dict[str, float] = {}
        for e in evidence:
            ev_dict[e.evidence_type] = e.evidence_value

        vix = ev_dict.get("vix_close", _LOW_VOL_THRESHOLD)

        if vix >= _HIGH_VOL_THRESHOLD:
            regime_value = 2.0
            regime_uncertainty = 0.20
        elif vix >= _LOW_VOL_THRESHOLD:
            regime_value = 1.0
            regime_uncertainty = 0.15
        else:
            regime_value = 0.0
            regime_uncertainty = 0.15

        regime_estimate = Estimate(
            latent_variable=_MARKET_REGIME,
            value=regime_value,
            uncertainty=regime_uncertainty,
            dimension=_REGIME_DIMENSION,
        )

        trend_estimate = Estimate(
            latent_variable=_TREND_STRENGTH,
            value=0.5,
            uncertainty=0.30,
            dimension=_TREND_DIMENSION,
        )

        if evidence:
            eval_ts = max(e.construction_timestamp for e in evidence)
        else:
            eval_ts = _SENTINEL_TS

        return MarketState(
            evaluation_timestamp=eval_ts,
            estimates=(regime_estimate, trend_estimate),
        )
