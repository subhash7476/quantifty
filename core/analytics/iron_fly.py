"""N-gated NIFTY iron fly — construct pieces.

Implements §3–§6 of docs/superpowers/specs/2026-09-23-gex-fly-stage-b-design.md.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from core.analytics.gex_history import RATE, implied_vol
from core.execution.options.fees import option_order_fees

ZONE_WINDOW = 250
ZONE_MIN_PERIODS = 200
ENTRY_Q, EXIT_Q = 0.67, 0.50
STOP_MULT, PROFIT_MULT = 1.0, 0.5
SPREAD = 0.02
MIN_SESSIONS_LEFT = 3


def zone_thresholds(n: pd.Series) -> pd.DataFrame:
    roll = n.rolling(ZONE_WINDOW, min_periods=ZONE_MIN_PERIODS)
    return pd.DataFrame({"p67": roll.quantile(ENTRY_Q), "p50": roll.quantile(EXIT_Q)})


@dataclass(frozen=True)
class Leg:
    strike: float
    option_type: str
    side: int  # +1 long, -1 short


def _nearest(strikes: np.ndarray, target: float) -> float:
    return float(strikes[np.argmin(np.abs(strikes - target))])


def select_legs(chain: pd.DataFrame, forward: float, t_years: float, structure: str):
    strikes = np.sort(chain["strike"].unique())
    body = _nearest(strikes, forward)
    otm = "CE" if body >= forward else "PE"
    row = chain[(chain["strike"] == body) & (chain["option_type"] == otm)]
    if row.empty:
        return "no_body"
    iv = implied_vol(float(row["close"].iloc[0]), forward * math.exp(-RATE * t_years), body, t_years, RATE, otm)
    if iv is None:
        return "no_iv"
    w = iv * math.sqrt(t_years) * forward
    up, dn = strikes[strikes >= body + w], strikes[strikes <= body - w]
    if up.size == 0 or dn.size == 0:
        return "no_wing"
    fly_width = max(up.min() - body, body - dn.max())
    if structure == "fly":
        return (Leg(body, "CE", -1), Leg(body, "PE", -1),
                Leg(float(up.min()), "CE", 1), Leg(float(dn.max()), "PE", 1)), float(fly_width)
    if structure == "straddle":
        return (Leg(body, "CE", -1), Leg(body, "PE", -1)), float(fly_width)
    if structure == "condor":
        sc, sp = _nearest(strikes, forward + 0.5 * w), _nearest(strikes, forward - 0.5 * w)
        lc, lp = _nearest(strikes, forward + 1.5 * w), _nearest(strikes, forward - 1.5 * w)
        return (Leg(sc, "CE", -1), Leg(sp, "PE", -1), Leg(lc, "CE", 1), Leg(lp, "PE", 1)), float(max(lc - sc, sp - lp))
    raise ValueError(f"unknown structure {structure!r}")


def conservative_mark(close: float, settle: float, contracts: int, side: int) -> float:
    if contracts > 0:
        return close
    vals = [v for v in (close, settle) if v is not None and not math.isnan(v)]
    return max(vals) if side < 0 else min(vals)


def position_value(legs, prices) -> float:
    return float(sum(leg.side * p for leg, p in zip(legs, prices)))


def exit_reason(pnl: float, credit: float, regime_low: bool, is_last: bool):
    if pnl <= -STOP_MULT * credit:
        return "stop"
    if pnl >= PROFIT_MULT * credit:
        return "profit"
    if regime_low:
        return "regime"
    if is_last:
        return "time"
    return None


def leg_costs(legs, prices, trade_date: date, lot: int, opening: bool) -> tuple[float, float]:
    fees = 0.0
    for leg, p in zip(legs, prices):
        side = "BUY" if (leg.side > 0) == opening else "SELL"
        fees += option_order_fees(premium=p, quantity=lot, side=side, trade_date=trade_date).total
    return fees / lot, float(sum(prices))


def trade_return(gross: float, fees: float, premium_sum: float, risk: float, spread: float) -> float:
    return (gross - fees - 0.5 * spread * premium_sum) / risk
