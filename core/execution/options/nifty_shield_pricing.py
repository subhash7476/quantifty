"""NiftyShield — Black-Scholes reference pricing for the entry credit gate.

Structure selection chooses a *shape*; until now nothing asked whether the
credit on offer for that shape was worth taking. This module supplies the
reference the gate compares against: what the structure's legs are worth at the
session's own implied vol, so an entry can be refused when the real credit from
marks falls materially short of it.

Deliberately a reference price, not a valuation engine: European Black-Scholes
on the index level, no dividend term, no term-structure model.

Each leg is priced at ITS OWN implied vol. It was originally priced at India VIX
flat across every leg, on the reasoning that "a shared bias cancels" in a ratio
against the same legs' marks. That reasoning was wrong: the marks carry the
market's vol and the reference carried VIX, so the error entered one side of the
ratio only and scaled the reference directly. Measured, it overstated a 6-DTE
bull put spread by ~30% — VIX is a 30-day variance-swap strip (above ATM IV by
construction, on a weekly option), and a single flat vol cannot sit on both legs
of a vertical, where it overprices the near leg and underprices the far one so
the two errors compound in the credit. Full measurement:
`docs/reports/index_research/NIFTY_SHIELD_CREDIT_FLOOR_CALIBRATION_2026-09-09.md`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

# Bisection bounds for implied vol. The upper bound is far above any index
# option vol; a price outside [bs(lo), bs(hi)] has no Black-Scholes vol at all.
_IV_LO, _IV_HI = 1e-4, 5.0
_LEG_KEYS = ("side", "strike", "option_type", "price", "qty")


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(spot: float, strike: float, t_years: float, rate: float,
             iv: float, option_type: str) -> float:
    """European Black-Scholes premium for a CE or PE."""
    if spot <= 0 or strike <= 0:
        return 0.0
    if t_years <= 0 or iv <= 0:
        intrinsic = (spot - strike) if option_type == "CE" else (strike - spot)
        return max(0.0, intrinsic)
    vol_t = iv * math.sqrt(t_years)
    d1 = (math.log(spot / strike) + (rate + 0.5 * iv * iv) * t_years) / vol_t
    d2 = d1 - vol_t
    disc = math.exp(-rate * t_years)
    if option_type == "CE":
        return spot * _norm_cdf(d1) - strike * disc * _norm_cdf(d2)
    return strike * disc * _norm_cdf(-d2) - spot * _norm_cdf(-d1)


def fair_structure_credit(legs: Iterable[Dict], spot: float, dte_days: float,
                          rate: float) -> Optional[float]:
    """Net premium per unit the structure should collect at the legs' own vols.

    `legs` are dicts carrying `side` ("SELL"/"BUY"), `strike`, `option_type` and
    `iv` — the leg's own implied vol as a decimal. SELL legs contribute
    positively, BUY legs negatively — the same sign convention the fill-derived
    credit uses, so the two are comparable.

    Returns None when the inputs cannot support a price, INCLUDING a leg with no
    usable `iv`. The caller must treat None as "gate unavailable" rather than as
    a pass or a fail. There is deliberately no flat-vol parameter to fall back
    on: substituting one vol for every leg is the defect this signature exists to
    make unrepresentable, and a fallback would reintroduce it silently.
    """
    if spot <= 0 or dte_days <= 0:
        return None
    t_years = float(dte_days) / 365.0
    total = 0.0
    for leg in legs:
        strike = leg.get("strike")
        opt = leg.get("option_type")
        iv = leg.get("iv")
        if strike is None or opt not in ("CE", "PE"):
            return None
        if iv is None or float(iv) <= 0:
            return None
        sign = 1.0 if str(leg.get("side")).upper() == "SELL" else -1.0
        total += sign * bs_price(spot, float(strike), t_years, rate,
                                 float(iv), opt)
    return total


def marked_structure_credit(legs: Iterable[Dict],
                            marks: Dict[str, float]) -> Optional[float]:
    """Net premium per unit the structure actually collects at current marks."""
    total = 0.0
    for leg in legs:
        symbol = leg.get("symbol")
        if symbol not in marks:
            return None
        sign = 1.0 if str(leg.get("side")).upper() == "SELL" else -1.0
        total += sign * float(marks[symbol])
    return total


def implied_vol(price: float, spot: float, strike: float, t_years: float,
                rate: float, option_type: str) -> Optional[float]:
    """Black-Scholes implied vol by bisection, or None when no vol reproduces
    the price (e.g. a premium below discounted intrinsic value)."""
    if price <= 0 or spot <= 0 or strike <= 0 or t_years <= 0:
        return None
    lo, hi = _IV_LO, _IV_HI
    if not (bs_price(spot, strike, t_years, rate, lo, option_type) <= price
            <= bs_price(spot, strike, t_years, rate, hi, option_type)):
        return None
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if bs_price(spot, strike, t_years, rate, mid, option_type) < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


@dataclass(frozen=True)
class Bracket:
    """A structure's take-profit and stop in Rs, sized at entry.

    `tp_rs` is the book's gain and `sl_rs` its loss at spot -/+ sigma_mult x
    sigma over the hold. `tp_enabled` is False when the gain side does not
    clear the fee floor (or does not exist, as for a straddle)."""
    tp_rs: float
    sl_rs: float
    sigma_pts: float
    leg_ivs: Tuple[float, ...]
    fee_floor_rs: float
    tp_enabled: bool


def sigma_bracket(legs: Iterable[Dict], spot: float, dte_days: float, rate: float,
                  sigma_mult: float, hold_hours: float, session_hours: float,
                  fee_floor_rs: float) -> Optional[Bracket]:
    """Size the exit bracket as the structure's P&L at spot +/-1 sigma.

    A 13:00-15:35 hold on a 2-8 DTE structure decays only a few percent of its
    premium, so its P&L is the index move, and the exits are sized in that unit
    (docs/superpowers/specs/2026-09-15-nifty-shield-sigma-bracket-design.md).
    Each leg's vol is solved from its own fill `price`, so the bracket depends
    only on what was paid and recomputes identically after a restart. Sigma is
    taken from the SELL legs' vols; the structure is repriced with vols and time
    held fixed.

    `legs` carry `side`, `strike`, `option_type`, `price` (the fill) and `qty`.
    Returns None when any input cannot support a price, or when the structure
    has no loss side — the caller must treat that as "no bracket", never
    substitute one.
    """
    legs = list(legs)
    if (spot <= 0 or dte_days <= 0 or hold_hours <= 0 or session_hours <= 0
            or not legs or any(leg.get(k) is None for leg in legs for k in _LEG_KEYS)):
        return None
    t_years = float(dte_days) / 365.0
    priced = []
    for leg in legs:
        iv = implied_vol(float(leg["price"]), spot, float(leg["strike"]), t_years,
                         rate, leg["option_type"])
        if iv is None:
            return None
        sign = 1.0 if str(leg["side"]).upper() == "SELL" else -1.0
        priced.append((sign, float(leg["strike"]), leg["option_type"], iv,
                       float(leg["qty"])))
    short_ivs = [iv for sign, _, _, iv, _ in priced if sign > 0]
    if not short_ivs:
        return None

    sigma_pts = (spot * (sum(short_ivs) / len(short_ivs))
                 * math.sqrt(hold_hours / (252.0 * session_hours)))

    def value(s: float) -> float:
        return sum(sign * bs_price(s, strike, t_years, rate, iv, opt) * qty
                   for sign, strike, opt, iv, qty in priced)

    shift = sigma_mult * sigma_pts
    base = value(spot)
    gain_down = base - value(spot - shift)
    gain_up = base - value(spot + shift)
    tp_rs = max(gain_down, gain_up, 0.0)
    sl_rs = max(-min(gain_down, gain_up), 0.0)
    if sl_rs <= 0.0:
        return None    # gains both ways (an arbitrage-priced fill): a Rs 0 stop fires at flat marks
    return Bracket(tp_rs=tp_rs, sl_rs=sl_rs, sigma_pts=sigma_pts,
                   leg_ivs=tuple(iv for _, _, _, iv, _ in priced),
                   fee_floor_rs=float(fee_floor_rs),
                   tp_enabled=tp_rs > 0.0 and tp_rs >= fee_floor_rs)
