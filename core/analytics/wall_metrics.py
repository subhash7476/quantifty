"""Options-Wall board metrics — pure functions over a chain snapshot's gamma ladder.

Everything here is arithmetic on data the wall store already carries (per-strike
gamma mass, OI, IV, spot). Bands and thresholds are display constants, not fits.

  hhi / hhi_band            concentration of |gamma| across strikes (Herfindahl)
  pin_candidates            pin, runner-up, conviction (0–100), margin (score pts)
  gamma_walls               ceiling / floor = argmax of call-side / put-side mass
  sigma_points              ATM-IV-implied one-sigma move to expiry, in index points
  time_to_expiry_years      weekday sessions to expiry incl. today's remaining fraction
  hedge_ladder              forced dealer futures flow (₹ Cr) at ±0.5/1.0/1.5 %
  oi_since_open             per-strike OI added / unwound vs the 09:15 baseline
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Dict, List, Optional, Tuple

HHI_COMPRESSED = 0.25
HHI_BALANCED = 0.10
CONVICTION_LOCKED = 70.0
CONVICTION_CONTESTED = 30.0
PIN_TOP_N = 10
LADDER_MOVES_PCT = (-1.5, -1.0, -0.5, 0.5, 1.0, 1.5)
SESSIONS_PER_YEAR = 252
SESSION_OPEN = time(9, 15)
SESSION_CLOSE = time(15, 30)
SESSION_MINUTES = 375.0
MIN_TTE_YEARS = 0.1 / SESSIONS_PER_YEAR
CRORE = 1e7


# ---------------------------------------------------------------- concentration

def hhi(values: Dict[float, float]) -> Optional[float]:
    """Sum of squared shares of total |value|; 1.0 = one strike, →0 = even."""
    total = sum(abs(v) for v in values.values())
    if total <= 0:
        return None
    return sum((abs(v) / total) ** 2 for v in values.values())


def hhi_band(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    if value >= HHI_COMPRESSED:
        return "COMPRESSED"
    if value >= HHI_BALANCED:
        return "BALANCED"
    return "DISPERSED"


# ----------------------------------------------------------------- pin candidates

def pin_candidates(ce_mass: Dict[float, float], pe_mass: Dict[float, float],
                   top_n: int = PIN_TOP_N) -> Dict:
    """Rank strikes by combined unsigned gamma mass (call + put).

    Scores are expressed as % of the leader. `margin` = 100 − runner-up score.
    `conviction` = leader's lead over the mean of the other top-N candidates,
    0–100; a lone strike is fully LOCKED.
    """
    strikes = set(ce_mass) | set(pe_mass)
    score = {k: abs(ce_mass.get(k, 0.0)) + abs(pe_mass.get(k, 0.0)) for k in strikes}
    score = {k: v for k, v in score.items() if v > 0}
    if not score:
        return {"pin": None, "runner_up": None, "conviction": None, "margin": None,
                "candidates": []}
    ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    top = ranked[0][1]
    candidates = [(k, v / top * 100.0) for k, v in ranked]
    rest = [pct for _, pct in candidates[1:]]
    runner_pct = rest[0] if rest else 0.0
    conviction = 100.0 - (sum(rest) / len(rest) if rest else 0.0)
    return {
        "pin": ranked[0][0],
        "runner_up": ranked[1][0] if len(ranked) > 1 else None,
        "conviction": conviction,
        "margin": 100.0 - runner_pct,
        "candidates": candidates,
    }


def conviction_band(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    if value >= CONVICTION_LOCKED:
        return "LOCKED"
    if value >= CONVICTION_CONTESTED:
        return "CONTESTED"
    return "DRIFTING"


# -------------------------------------------------------------------- gamma walls

def gamma_walls(ce_mass: Dict[float, float],
                pe_mass: Dict[float, float]) -> Tuple[Optional[float], Optional[float]]:
    """(ceiling, floor): strikes carrying the most call-side / put-side gamma."""
    ceiling = max(ce_mass, key=lambda k: abs(ce_mass[k])) if ce_mass else None
    floor = max(pe_mass, key=lambda k: abs(pe_mass[k])) if pe_mass else None
    return ceiling, floor


# -------------------------------------------------------------------------- sigma

def sigma_points(spot: Optional[float], atm_iv_pct: Optional[float],
                 tte_years: Optional[float]) -> Optional[float]:
    """One-sigma move implied by ATM IV over the time left, in index points."""
    if not spot or atm_iv_pct is None or tte_years is None or tte_years <= 0:
        return None
    return spot * atm_iv_pct / 100.0 * tte_years ** 0.5


def _session_fraction_remaining(now: datetime) -> float:
    if now.weekday() >= 5:
        return 0.0
    t = now.time()
    if t <= SESSION_OPEN:
        return 1.0
    if t >= SESSION_CLOSE:
        return 0.0
    elapsed = (now.hour * 60 + now.minute + now.second / 60.0) \
        - (SESSION_OPEN.hour * 60 + SESSION_OPEN.minute)
    return max(0.0, 1.0 - elapsed / SESSION_MINUTES)


def time_to_expiry_years(expiry: str, now: Optional[datetime] = None) -> Optional[float]:
    """Weekday sessions strictly after today up to expiry, plus today's remaining
    session fraction, over 252. Floored so an expiry-day read never divides by zero.
    Holidays are not subtracted."""
    try:
        exp = date.fromisoformat(expiry)
    except (TypeError, ValueError):
        return None
    now = now or datetime.now()
    full = 0
    d = now.date()
    while d < exp:
        d = date.fromordinal(d.toordinal() + 1)
        if d.weekday() < 5:
            full += 1
    frac = _session_fraction_remaining(now) if now.date() <= exp else 0.0
    return max((full + frac) / SESSIONS_PER_YEAR, MIN_TTE_YEARS)


# ------------------------------------------------------------------- hedge ladder

def hedge_ladder(gamma_by_strike: Dict[float, float], spot: float,
                 moves_pct: Tuple[float, ...] = LADDER_MOVES_PCT) -> List[Dict]:
    """Futures the dealer book must trade for each spot move, in ₹ Cr notional.

    `gamma_by_strike` is signed dealer gamma in (gamma × OI × lot) units, i.e. the
    change in dealer delta per index point. Long gamma → dealers sell rallies and
    buy dips; the sign of `flow_cr` is +BUY / −SELL.
    """
    if not gamma_by_strike or not spot:
        return []
    net_gamma = sum(gamma_by_strike.values())
    out = []
    for m in moves_pct:
        d_points = spot * m / 100.0
        delta_change = net_gamma * d_points
        flow_units = -delta_change
        flow_cr = flow_units * spot / CRORE
        out.append({"move_pct": m, "flow_cr": flow_cr,
                    "side": "BUY" if flow_cr >= 0 else "SELL"})
    return out


# ---------------------------------------------------------------- OI since open

def oi_since_open(chain, baseline: Dict[Tuple[float, str], int]) -> Optional[Dict]:
    """Per-strike OI change vs the 09:15 baseline (legs without a baseline read 0)."""
    if not baseline:
        return None
    by_strike: Dict[float, Dict[str, int]] = {}
    added = unwound = 0
    total_oi = total_vol = 0
    for r in chain:
        base = baseline.get((r.strike, r.option_type))
        delta = (r.oi or 0) - base if base is not None else 0
        cell = by_strike.setdefault(r.strike, {"ce": 0, "pe": 0})
        cell["ce" if r.option_type == "CE" else "pe"] += delta
        if delta > 0:
            added += delta
        else:
            unwound += -delta
        total_oi += r.oi or 0
        total_vol += r.volume or 0
    return {"added": added, "unwound": unwound, "by_strike": by_strike,
            "total_oi": total_oi,
            "vol_oi": (total_vol / total_oi) if total_oi else None}
