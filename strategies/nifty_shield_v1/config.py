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
    # Live fact-publication tolerance: the entry may fire on any bar from the
    # 13:00 checkpoint through 13:00 + this many minutes (the DS2-2 publisher is
    # given the same window to compute and publish the 13pm fact). Offline the
    # fact is already present at 13:00, so this is a provable no-op there.
    "entry_window_minutes": 10,
    # Hard flatten. 15:35, not 15:15: the structure is managed by its own TP/SL
    # for the whole session and the clock only ends it. 15:15 cut every trade at
    # the cash Category-I close, but this book is F&O — the derivatives segment
    # trades to 15:40 (post-CAS, core/market/session_schedule.py) and option
    # premia keep decaying the entire time. The underlying's 1m bars stop at the
    # 15:29 auction print, so the exit driver is also driven on idle ticks
    # (RuntimeConfig.rebalance_on_idle) to make this time reachable.
    "exit_time": {"hour": 15, "minute": 35},
    "profit_target_pct": 0.50,
    # Defined-risk structures (iron_fly / the two verticals) stop on a fraction
    # of max loss. A credit multiple cannot bound them: loss is capped at
    # wing_width x qty - credit, so -stop_loss_multiplier x credit is reachable
    # only when max_loss / credit >= the multiple -- true for 10.5% of
    # defined-risk entries over the certified facts, and 0 of 56 iron flies.
    "stop_loss_max_loss_frac": 0.50,
    # Retained for short_straddle / short_strangle, which have no structural
    # bound and for which a credit multiple is the only rule available.
    "stop_loss_multiplier": 2.0,
    # D1: delta adjustment dropped in v1 — delta is a flatten-gate (close-only).
    "delta_adjustment_threshold": 0.55,
    "max_portfolio_delta": 500,
    "max_lots": 2,
    # NSE NIFTY F&O lot size. 65 since the 2026-09 revision -- the instrument
    # master carries 65 on every option expiry from 2026-09-08. The handler
    # sizes from this value directly, so a stale number routes an un-tradeable
    # quantity. Better still would be resolving it per-contract from the
    # instrument layer at the execution boundary (ADR-016) -- see the report.
    "lot_size": 65,
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
# `entry_window_minutes` is a live data-readiness tolerance (how long the source
# waits for the 13pm fact), not a certified trading decision, so it sits here too.
_RUNTIME_SEAMS = ("facts_db_path", "entry_window_minutes")


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
