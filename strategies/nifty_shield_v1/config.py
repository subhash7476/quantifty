"""nifty_shield_v1 — config (datasheet §3 certified dict + runtime seams).

The strategy-parameter dict mirrors the datasheet §3 proposed certified dict
(the `config_hash` is computed over this frozen form, excluding the runtime
seam `facts_db_path`). `build_signal_source` merges a caller config over
DEFAULT_CONFIG.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

STRATEGY_ID = "nifty_shield_v1"

DEFAULT_CONFIG: Dict[str, Any] = {
    "underlying": "NSE_INDEX|Nifty 50",
    "entry_checkpoint": "13pm",
    "exit_time": {"hour": 15, "minute": 15},
    "profit_target_pct": 0.50,
    "stop_loss_multiplier": 2.0,
    # D1: delta adjustment dropped in v1 — delta is a flatten-gate (close-only).
    "delta_adjustment_threshold": 0.55,
    "max_portfolio_delta": 500,
    "max_lots": 2,
    "lot_size": 75,
    "regime_sizing": {"Choppy": 1.0, "BullTrend": 0.5, "BearTrend": 0.5},
    "vix_skip_above": 20.0,
    "vix_reduce_above": 16.0,
    "iron_fly_vix_above": 14.0,
    "wing_offset_pts": 100,
    "directional_wing_pts": 150,
    "strangle_otm_pts": 50,
    "expiry_days_min": 2,
    "strike_step": 50,
    "risk_free_rate": 0.065,
    "iv_default": 0.14,
    # Undefined-risk (straddle/strangle) per-signal risk declaration: a stated
    # stress distance in index points (datasheet §7a philosophy; proposed value,
    # a freeze input for the datasheet §3/§7 grant).
    "undefined_risk_stress_pts": 200,
    # Runtime seam (not part of the certified strategy dict / config_hash).
    "facts_db_path": "data/features/day_type/day_type_facts.duckdb",
}

# Keys that are runtime wiring, not strategy parameters — excluded from config_hash.
_RUNTIME_SEAMS = ("facts_db_path",)


def _canonical_strategy_dict(config: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in config.items() if k not in _RUNTIME_SEAMS}


def config_hash(config: Dict[str, Any]) -> str:
    """SHA-256 over the frozen strategy-parameter dict (datasheet §1 config_hash).

    Excludes runtime seams so the certified identity does not move when the
    facts store path changes between environments.
    """
    canonical = _canonical_strategy_dict(config)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
