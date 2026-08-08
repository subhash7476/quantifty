"""nifty_shield_v1 — structure selection and leg arithmetic (pure).

Re-expresses the bundle's `_select_structure` / `_enter` strike math as pure
functions (no core imports — the source may only import core.events +
core.runtime.signal_source). Everything here is arithmetic on config + inputs;
no marks, no instruments, no sizing beyond declarations.

Structure selection (datasheet §5a):
  BullTrend            -> bull_put_spread  (short ATM PE + long OTM PE -dir)
  BearTrend            -> bear_call_spread (short ATM CE + long OTM CE +dir)
  Choppy, VIX > 16     -> short_strangle   (short OTM CE +otm, short OTM PE -otm)
  Choppy, 14 < VIX<=16 -> iron_fly         (short ATM CE/PE + long wings +/-wing)
  Choppy, VIX <= 14    -> short_straddle   (short ATM CE + short ATM PE)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

# Expiry weekday per index (selector: Nifty = Tuesday). Python weekday: Mon=0.
INDEX_EXPIRY_WEEKDAY = {"NSE_INDEX|Nifty 50": 1}


@dataclass(frozen=True)
class LegSpec:
    role: str            # short_ce | short_pe | wing_ce | wing_pe
    option_type: str     # CE | PE
    strike_offset: int   # signed points from ATM
    signal_type: str     # SELL for shorts, BUY for wings


STRUCTURES: Dict[str, List[LegSpec]] = {
    "bull_put_spread": [
        LegSpec("short_pe", "PE", 0, "SELL"),
        LegSpec("wing_pe", "PE", -1, "BUY"),      # offset filled from config
    ],
    "bear_call_spread": [
        LegSpec("short_ce", "CE", 0, "SELL"),
        LegSpec("wing_ce", "CE", 1, "BUY"),
    ],
    "short_strangle": [
        LegSpec("short_ce", "CE", 1, "SELL"),
        LegSpec("short_pe", "PE", -1, "SELL"),
    ],
    "iron_fly": [
        LegSpec("short_ce", "CE", 0, "SELL"),
        LegSpec("short_pe", "PE", 0, "SELL"),
        LegSpec("wing_ce", "CE", 1, "BUY"),
        LegSpec("wing_pe", "PE", -1, "BUY"),
    ],
    "short_straddle": [
        LegSpec("short_ce", "CE", 0, "SELL"),
        LegSpec("short_pe", "PE", 0, "SELL"),
    ],
}


def select_structure(regime: str, vix: Optional[float], cfg: Dict[str, Any]) -> str:
    """Structure selection per datasheet §5a (bundle `_select_structure`)."""
    v = vix or 0.0
    if regime == "BullTrend":
        return "bull_put_spread"
    if regime == "BearTrend":
        return "bear_call_spread"
    # Choppy
    if v > float(cfg.get("vix_reduce_above", 16.0)):
        return "short_strangle"
    if v > float(cfg.get("iron_fly_vix_above", 14.0)):
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


def _leg_offsets(structure: str, cfg: Dict[str, Any]) -> List[LegSpec]:
    """Resolve the signed offsets for each structure's legs."""
    specs = STRUCTURES[structure]
    wing_pts = int(cfg.get("wing_offset_pts", 100))
    dir_pts = int(cfg.get("directional_wing_pts", 150))
    otm_pts = int(cfg.get("strangle_otm_pts", 50))

    out = []
    for spec in specs:
        offset = spec.strike_offset
        if spec.strike_offset == -1:
            offset = -dir_pts if structure in ("bull_put_spread", "bear_call_spread") else -wing_pts
        elif spec.strike_offset == 1:
            offset = dir_pts if structure in ("bull_put_spread", "bear_call_spread") else wing_pts
        out.append(LegSpec(spec.role, spec.option_type, offset, spec.signal_type))
    # Strangle uses OTM offsets for the shorts.
    if structure == "short_strangle":
        out = [
            LegSpec(s.role, s.option_type,
                    otm_pts if s.option_type == "CE" else -otm_pts, s.signal_type)
            for s in out
        ]
    return out


def compute_legs(structure: str, price: float, cfg: Dict[str, Any],
                 session_date: date) -> List[Dict[str, Any]]:
    """Compute the leg descriptors (symbol, strike, expiry, option_type, role).

    Returns one dict per leg, ready for SignalEvent metadata:
      symbol, structure, leg_role, strike, expiry, option_type, signal_type.
    The short-name symbol mirrors the selector's `_build_symbol` output
    (NIFTY{DD}{MON}{YY}{STRIKE}{CE|PE}) so the execution boundary can resolve it.
    """
    step = int(cfg.get("strike_step", 50))
    atm = atm_strike(price, step)
    min_days = int(cfg.get("expiry_days_min", 2))
    underlying = cfg.get("underlying", "NSE_INDEX|Nifty 50")
    expiry = nearest_expiry(session_date, min_days, underlying)
    short_name = "NIFTY" if "Nifty 50" in underlying else "NIFTY"

    legs = []
    for spec in _leg_offsets(structure, cfg):
        strike = atm + spec.strike_offset
        symbol = _build_symbol(short_name, expiry, strike, spec.option_type)
        legs.append({
            "symbol": symbol,
            "structure": structure,
            "leg_role": spec.role,
            "strike": strike,
            "expiry": expiry.isoformat(),
            "option_type": spec.option_type,
            "signal_type": spec.signal_type,
        })
    return legs


def _build_symbol(short_name: str, expiry: date, strike: int, option_type: str) -> str:
    day = expiry.strftime("%d")
    month = expiry.strftime("%b").upper()
    year = expiry.strftime("%y")
    return f"{short_name}{day}{month}{year}{strike}{option_type}"
