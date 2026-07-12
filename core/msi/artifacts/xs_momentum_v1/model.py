"""Frozen PublishedArtifact v1 for the CSMP cross-sectional-momentum hypothesis.

Specification: `docs/reports/CSMP_PHASE1_RESEARCH_DOSSIER.md` Rev 7 (FROZEN). This
artifact is PARAMETER-FREE — the construct is a deterministic transform of adjusted
prices; there are no fitted coefficients (dossier §7). Any change to the construct
(universe, score, K, §5.2, etc.) requires a NEW pre-registration, not an edit.

Construct (dossier §3.2 / §5.1 / §7): classic 12-1 cross-sectional momentum.
`evaluate()` emits ONE Estimate per point-in-time universe member:
  - latent_variable = "xs_momentum_score"
  - value           = adj_close(t-1m) / adj_close(t-12m) - 1   (12-1, most-recent month skipped)
  - dimension       = <symbol> (the member's ticker at the rebalance date)
  - uncertainty     = SD of the monthly formation sub-returns (reported-not-acted-on, §7)

Evidence contract (built by the A2 harness / DRA, not here): one Evidence per
(symbol, month-offset k) with evidence_type = f"{symbol}|{k}", k = 0..11, where k=0 is
the t-12m grid session and k=11 is the t-1m grid session, and evidence_value is the
gate-(b) CA-adjusted close for that member's ENTITY at that grid session (entity
continuity / PIT membership are the harness's responsibility). The artifact is
entity-agnostic: it transforms whatever prices it is handed.

Scoring rule (matches the frozen dossier / `phase1_prereg_analysis.py`):
  - A name is SCORED iff both formation endpoints are present and positive
    (k=0 and k=11) — "complete formation window" per §3.2/§5.1. Names failing this
    are not scored and cannot enter the top-40.
  - `uncertainty` = sample SD of the available consecutive monthly sub-returns among
    the 12 grid prices; NaN if fewer than two are computable. It is REPORTED, never
    acted on (no role in ranking, K-selection, or weighting — §4/§7).
  - Formation-window completeness (all 12 monthly prices present) is SEPARATE metadata
    on the Estimate's… — carried by the harness, NOT folded into `uncertainty` (§7).

Deterministic and side-effect-free: identical Evidence -> identical MarketState
(estimates sorted by dimension for a stable order).
"""

import statistics
from datetime import datetime
from typing import Dict, Tuple

from core.msi.contracts.artifact import ArtifactMetadata, PublishedArtifact
from core.msi.contracts.estimate import Estimate
from core.msi.contracts.evidence import Evidence
from core.msi.contracts.market_state import MarketState

_LATENT_VARIABLE = "xs_momentum_score"
FORMATION_MONTHS = 12          # 12-1: grid offsets k=0 (t-12m) .. k=11 (t-1m)
_N_GRID = FORMATION_MONTHS      # 12 monthly grid prices define the formation window

_METADATA = ArtifactMetadata(
    artifact_id="csmp-xs-momentum-v1",
    artifact_version="v1.0.0",
    schema_version="1.0",
    validation_id="val-csmp-xs-momentum-v1-pending",
    publication_timestamp=datetime(2026, 7, 12, 0, 0, 0),
    compatibility_version="1.0",
    runtime_compatibility="msi-v1.0",
    provenance_reference="prov-csmp-xs-momentum-v1",
)

_EVIDENCE_RULES: Dict[str, object] = {
    "construct": "classic 12-1 cross-sectional momentum (monthly, equal-weight, long-only)",
    "score": "adj_close(t-1m)/adj_close(t-12m) - 1 (skip most-recent month)",
    "formation_months": FORMATION_MONTHS,
    "skip_months": 1,
    "price_source": "equity_bhavcopy_adjusted (gate (b) CA-adjusted close)",
    "universe": "universe_membership (gate (c) point-in-time NIFTY-200)",
    "entity_continuity": "universe_eligibility / symbol_changes (gate (a))",
    "evidence_type_format": "'{symbol}|{k}' with k in 0..11; k=0 is t-12m, k=11 is t-1m",
    "uncertainty": "sample SD of monthly formation sub-returns (reported-not-acted-on)",
    "rule_format_version": "1.0",
}


def _parse(evidence_type: str) -> Tuple[str, int]:
    sym, _, k = evidence_type.rpartition("|")
    return sym, int(k)


class XSMomentumArtifact(PublishedArtifact):
    """Frozen parameter-free 12-1 cross-sectional-momentum PublishedArtifact (MSI-007).

    Deterministic: identical Evidence -> identical MarketState. Emits one Estimate per
    scored universe member; `uncertainty` is emitted but never acted on.
    """

    metadata = _METADATA

    def get_evidence_rules(self) -> Dict[str, object]:
        return _EVIDENCE_RULES

    def evaluate(self, evidence: Tuple[Evidence, ...]) -> MarketState:
        by_symbol: Dict[str, Dict[int, float]] = {}
        for e in evidence:
            sym, k = _parse(e.evidence_type)
            by_symbol.setdefault(sym, {})[k] = float(e.evidence_value)

        estimates = []
        for sym in sorted(by_symbol):
            prices = by_symbol[sym]
            p0 = prices.get(0)
            p_last = prices.get(_N_GRID - 1)
            # "complete formation window" = both endpoints present & positive (§3.2).
            if not (p0 and p_last and p0 > 0.0 and p_last > 0.0):
                continue
            score = p_last / p0 - 1.0
            subrets = [
                prices[k + 1] / prices[k] - 1.0
                for k in range(_N_GRID - 1)
                if prices.get(k) and prices.get(k + 1) and prices[k] > 0.0
            ]
            uncertainty = statistics.stdev(subrets) if len(subrets) >= 2 else float("nan")
            estimates.append(Estimate(
                latent_variable=_LATENT_VARIABLE,
                value=score,
                uncertainty=uncertainty,
                dimension=sym,
            ))

        latest_ts = max(e.construction_timestamp for e in evidence)
        return MarketState(evaluation_timestamp=latest_ts, estimates=tuple(estimates))
