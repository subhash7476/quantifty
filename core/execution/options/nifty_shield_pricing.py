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
from typing import Dict, Iterable, Optional


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
