"""nifty_shield_v1 — config (datasheet §3 certified dict + runtime seams).

The strategy-parameter dict mirrors the datasheet §3 proposed certified dict
(the `config_hash` is computed over this frozen form, excluding the runtime
seam `facts_db_path`). `build_signal_source` merges a caller config over
DEFAULT_CONFIG.

**Scale-invariance (2026-09-08).** The 2026-09-08 audit found every trading
decision in this strategy was made by an absolute constant chosen once and never
re-validated: VIX gates that stopped firing when India VIX compressed, wings
fixed in index points while 1 sigma to expiry ranged 189-448 points, and a
profit target set as a fraction of credit that was an order of magnitude outside
what a 2.5-hour hold can decay. Those constants are replaced here by
scale-invariant equivalents — percentiles, sigma fractions, and a fraction of
modelled available decay. Each replacement is the legacy constant mapped onto
its own historical equivalent in the new unit, so design intent is preserved and
nothing is fitted to observed P&L; the derivation is
`scripts/nifty_shield/derive_anchoring_params.py` and
`docs/reports/index_research/NIFTY_SHIELD_ANCHORING_DERIVATION.md`.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

STRATEGY_ID = "nifty_shield_v1"

# Provenance of the derived anchoring parameters below. Refreshing them means
# re-running the derivation script and moving this date with the values.
ANCHORING_DERIVED_ON = "2026-09-08"
ANCHORING_SUBSTRATE = "Nifty 50 + India VIX daily closes, 2014-05-14..2026-09-07 (3,040 sessions)"

DEFAULT_CONFIG: Dict[str, Any] = {
    "underlying": "NSE_INDEX|Nifty 50",
    "entry_checkpoint": "13pm",
    # Live fact-publication tolerance: the entry may fire on any bar from the
    # 13:00 checkpoint through 13:00 + this many minutes (the DS2-2 publisher is
    # given the same window to compute and publish the 13pm fact). Offline the
    # fact is already present at 13:00, so this is a provable no-op there.
    "entry_window_minutes": 30,
    # Hard flatten. 15:35, not 15:15: the structure is managed by its own TP/SL
    # for the whole session and the clock only ends it. 15:15 cut every trade at
    # the cash Category-I close, but this book is F&O — the derivatives segment
    # trades to 15:40 (post-CAS, core/market/session_schedule.py) and option
    # premia keep decaying the entire time. The underlying's 1m bars stop at the
    # 15:29 auction print, so the exit driver is also driven on idle ticks
    # (RuntimeConfig.rebalance_on_idle) to make this time reachable.
    "exit_time": {"hour": 15, "minute": 35},

    # --- Exit bracket ----------------------------------------------------
    # Take-profit and stop are the structure's P&L at spot +/- bracket_sigma x
    # 1 sigma over the hold, sized by execution from the legs' fill-implied
    # vols. A 13:00-15:35 hold decays only a few percent of a 2-8 DTE premium,
    # so its P&L is the index move. The decay-fraction take-profit and max-loss
    # stop this replaces were sized in units unrelated to it: on 2026-09-15 a
    # Rs 121 target (8 index points, below the Rs 133 round trip) against a
    # Rs 3,534 stop (245 points). Both values are design choices, not fits
    # (docs/superpowers/specs/2026-09-15-nifty-shield-sigma-bracket-design.md).
    "bracket_sigma": 1.0,
    # The take-profit is disabled when its gain side is below this multiple of
    # the round-trip fees — a target at the fee line nets nothing.
    "tp_min_fee_multiple": 3.0,
    # Market hours in a session, and the modelled hold from the 13:00 entry to
    # the close. Scale 1 sigma of the index over the hold.
    "session_hours": 6.25,
    "hold_hours": 2.5,
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

    # --- Volatility gates ------------------------------------------------
    # `vix_skip_above` stays an ABSOLUTE level on purpose. It is a hard risk
    # limit ("do not trade this book when vol is outright high"), not a read on
    # how unusual today's vol is, and a percentile form would happily authorise
    # trading at VIX 40 in a period whose trailing window was also high.
    "vix_skip_above": 20.0,
    # The structure-selection gates ARE regime-relative reads, and are keyed to
    # the trailing India VIX distribution. Legacy 16.0 -> 59.0th percentile and
    # 14.0 -> 36.8th percentile (median trailing percentile those levels have
    # historically occupied). Evaluated against the trailing window at entry,
    # so they cannot silently expire the way the absolute levels did: VIX 14 sat
    # at the 19.6th percentile in some eras and the 44.0th in others.
    "vix_strangle_pctile": 59.0,
    "vix_iron_fly_pctile": 36.8,
    "vix_pctile_lookback_sessions": 756,

    # --- Strike geometry -------------------------------------------------
    # Offsets are fractions of 1 sigma to expiry (spot x IV x sqrt(T)), not
    # fixed index points. The audit measured 1 sigma ranging 189-448 points
    # across eight trades while the wing stayed at 150 — the same nominal
    # structure was 0.79 sigma wide one day and 0.34 sigma the next. Fractions
    # are the legacy point offsets mapped to the sigma they have historically
    # represented: 150 -> 0.541, 100 -> 0.361, 50 -> 0.180.
    "directional_wing_sigma_frac": 0.541,
    "wing_sigma_frac": 0.361,
    "strangle_otm_sigma_frac": 0.180,
    "expiry_days_min": 2,
    "strike_step": 50,
    "risk_free_rate": 0.065,
    "iv_default": 0.14,

    # --- Entry pricing quality ------------------------------------------
    # Structure selection chooses a shape; it never asked whether the credit on
    # offer was worth taking. An entry is skipped when the real credit from
    # marks falls below this fraction of the Black-Scholes credit for the same
    # legs at the session's own implied vol. A pure no-trade filter: it can only
    # reduce activity, and it fires on stale or badly-spread quotes rather than
    # on a view. Set from what a fairly-priced structure should collect, not
    # from any observed outcome.
    "credit_fair_frac": 0.90,

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
