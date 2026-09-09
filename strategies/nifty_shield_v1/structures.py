"""nifty_shield_v1 — structure selection and leg arithmetic (pure).

Re-expresses the bundle's `_select_structure` / `_enter` strike math as pure
functions (no core imports — the source may only import core.events +
core.runtime.signal_source). Everything here is arithmetic on config + inputs;
no marks, no instruments, no sizing beyond declarations.

Structure selection (datasheet §5a, re-anchored 2026-09-08):
  BullTrend                        -> bull_put_spread
  BearTrend                        -> bear_call_spread
  Choppy, VIX pctile > strangle    -> short_strangle
  Choppy, VIX pctile > iron_fly    -> iron_fly
  Choppy, otherwise                -> short_straddle

The Choppy branch keys on the percentile of today's India VIX within its own
trailing distribution, not on an absolute level. The absolute gates (14 / 16)
never fired across the live window — India VIX sat at 10.6-11.7 — so `iron_fly`
and `short_strangle` were unreachable and Choppy always produced a straddle.

Strike geometry is anchored to 1 sigma to expiry rather than to fixed index
points, so a structure means the same thing regardless of days remaining or the
level of implied vol. `sigma_points()` is the single definition of that scale.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

# Expiry weekday per index (selector: Nifty = Tuesday). Python weekday: Mon=0.
INDEX_EXPIRY_WEEKDAY = {"NSE_INDEX|Nifty 50": 1}


@dataclass(frozen=True)
class LegSpec:
    role: str            # short_ce | short_pe | wing_ce | wing_pe
    option_type: str     # CE | PE
    sigma_mult: float    # signed multiple of the structure's sigma offset
    signal_type: str     # SELL for shorts, BUY for wings


STRUCTURES: Dict[str, List[LegSpec]] = {
    "bull_put_spread": [
        LegSpec("short_pe", "PE", 0.0, "SELL"),
        LegSpec("wing_pe", "PE", -1.0, "BUY"),
    ],
    "bear_call_spread": [
        LegSpec("short_ce", "CE", 0.0, "SELL"),
        LegSpec("wing_ce", "CE", 1.0, "BUY"),
    ],
    "short_strangle": [
        LegSpec("short_ce", "CE", 1.0, "SELL"),
        LegSpec("short_pe", "PE", -1.0, "SELL"),
    ],
    "iron_fly": [
        LegSpec("short_ce", "CE", 0.0, "SELL"),
        LegSpec("short_pe", "PE", 0.0, "SELL"),
        LegSpec("wing_ce", "CE", 1.0, "BUY"),
        LegSpec("wing_pe", "PE", -1.0, "BUY"),
    ],
    "short_straddle": [
        LegSpec("short_ce", "CE", 0.0, "SELL"),
        LegSpec("short_pe", "PE", 0.0, "SELL"),
    ],
}

# Which config sigma fraction sets each structure's offset scale.
_SIGMA_FRAC_KEY = {
    "bull_put_spread": "directional_wing_sigma_frac",
    "bear_call_spread": "directional_wing_sigma_frac",
    "iron_fly": "wing_sigma_frac",
    "short_strangle": "strangle_otm_sigma_frac",
    "short_straddle": "wing_sigma_frac",     # unused: straddle has no offset leg
}


def select_structure(regime: str, vix_pctile: Optional[float],
                     cfg: Dict[str, Any]) -> str:
    """Structure selection per datasheet §5a, on the trailing VIX percentile.

    `vix_pctile` is today's India VIX expressed as its percentile within the
    trailing `vix_pctile_lookback_sessions` window, published on the regime
    fact. None (a store predating the column) falls through to the calmest
    branch — a straddle — which is the behaviour the absolute gates produced in
    every live session anyway, so an un-migrated store cannot silently start
    trading a structure it never traded before.
    """
    if regime == "BullTrend":
        return "bull_put_spread"
    if regime == "BearTrend":
        return "bear_call_spread"
    p = -1.0 if vix_pctile is None else float(vix_pctile)
    if p > float(cfg.get("vix_strangle_pctile", 59.0)):
        return "short_strangle"
    if p > float(cfg.get("vix_iron_fly_pctile", 36.8)):
        return "iron_fly"
    return "short_straddle"


def nearest_expiry(from_date: date, min_days: int,
                   underlying: str = "NSE_INDEX|Nifty 50") -> date:
    """Nearest weekly expiry >= min_days away (selector `_nearest_expiry`)."""
    weekday = INDEX_EXPIRY_WEEKDAY.get(underlying, 1)
    target = from_date + timedelta(days=min_days)
    days_ahead = (weekday - target.weekday()) % 7
    return target + timedelta(days=days_ahead)


def atm_strike(price: float, step: int) -> int:
    return int(round(price / step) * step)


def sigma_points(price: float, iv: float, days_to_expiry: float) -> float:
    """1 sigma of index movement between now and expiry, in index points.

    `iv` is an annualised decimal (India VIX / 100). This is the scale every
    strike offset is expressed against, so that a structure describes the same
    probability of being breached whatever the days remaining or the vol level.
    """
    if price <= 0 or iv <= 0 or days_to_expiry <= 0:
        return 0.0
    return float(price) * float(iv) * math.sqrt(float(days_to_expiry) / 365.0)


def available_decay_frac(days_to_expiry: float, cfg: Dict[str, Any]) -> float:
    """Fraction of ATM premium a hold can decay with spot unchanged.

    ATM value scales ~sqrt(T), so holding `h` market-hours out of `T` leaves
    sqrt((T-h)/T). Trading-time convention: only market hours count, and
    calendar days are converted at 5 trading days per 7. This is what the
    profit target is a fraction OF — see config `profit_target_decay_frac`.
    """
    session_hours = float(cfg.get("session_hours", 6.25))
    hold = float(cfg.get("hold_hours", 2.5))
    total = (float(days_to_expiry) * 5.0 / 7.0) * session_hours
    if total <= hold:
        return 1.0
    return 1.0 - math.sqrt((total - hold) / total)


def _offset_points(structure: str, sigma_pts: float, step: int,
                   cfg: Dict[str, Any]) -> int:
    """The structure's offset in index points: frac x sigma, on the strike grid.

    Floored at one strike step — a zero offset would collapse a vertical into a
    naked short, and a fly into a straddle, silently converting a defined-risk
    structure into an unbounded one.
    """
    frac = float(cfg.get(_SIGMA_FRAC_KEY.get(structure, "wing_sigma_frac"), 0.361))
    raw = frac * float(sigma_pts)
    return max(step, int(round(raw / step) * step))


def compute_legs(structure: str, price: float, cfg: Dict[str, Any],
                 session_date: date, iv: float) -> List[Dict[str, Any]]:
    """Compute the leg descriptors (symbol, strike, expiry, option_type, role).

    Returns one dict per leg, ready for SignalEvent metadata:
      symbol, structure, leg_role, strike, expiry, option_type, signal_type.
    The short-name symbol mirrors the selector's `_build_symbol` output
    (NIFTY{DD}{MON}{YY}{STRIKE}{CE|PE}) so the execution boundary can resolve it.

    `iv` is the annualised decimal implied vol used to size the sigma offsets
    (India VIX / 100 at the checkpoint, falling back to config `iv_default`).
    """
    step = int(cfg.get("strike_step", 50))
    atm = atm_strike(price, step)
    min_days = int(cfg.get("expiry_days_min", 2))
    underlying = cfg.get("underlying", "NSE_INDEX|Nifty 50")
    expiry = nearest_expiry(session_date, min_days, underlying)
    dte = max((expiry - session_date).days, 1)
    sigma_pts = sigma_points(price, iv, dte)
    offset = _offset_points(structure, sigma_pts, step, cfg)
    short_name = "NIFTY"

    legs = []
    for spec in STRUCTURES[structure]:
        strike = atm + int(round(spec.sigma_mult * offset))
        symbol = _build_symbol(short_name, expiry, strike, spec.option_type)
        legs.append({
            "symbol": symbol,
            "structure": structure,
            "leg_role": spec.role,
            "strike": strike,
            "expiry": expiry.isoformat(),
            "option_type": spec.option_type,
            "signal_type": spec.signal_type,
            "offset_pts": offset,
            "sigma_pts": sigma_pts,
        })
    return legs


def _build_symbol(short_name: str, expiry: date, strike: int, option_type: str) -> str:
    day = expiry.strftime("%d")
    month = expiry.strftime("%b").upper()
    year = expiry.strftime("%y")
    return f"{short_name}{day}{month}{year}{strike}{option_type}"
