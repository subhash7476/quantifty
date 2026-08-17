"""Iron-fly construction, marking, fees, and defined-risk margin for the paper pilot.

An iron fly is centered at the ATM strike (short CE + short PE) with protective
wings bought at ±wing_pct of spot, snapped to the nearest listed strike. P&L is
computed directly from leg mids; fees come from the shared options fee model. No
group/broker primitives are reused — a 4-leg fly's math is arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

from core.execution.options.fees import option_order_fees


@dataclass
class FlyLeg:
    side: str          # "SELL" (shorts) or "BUY" (wings)
    option_type: str   # "CE" / "PE"
    strike: float
    entry_mid: float


@dataclass
class IronFly:
    short_strike: float
    call_wing: float
    put_wing: float
    legs: List[FlyLeg]
    net_credit_per_unit: float
    qty: int
    net_credit: float
    entry_fees: float
    max_loss: float


def _bid_ask(row) -> Tuple[Optional[float], Optional[float]]:
    return getattr(row, "best_bid", None), getattr(row, "best_ask", None)


def _spread_ok(row, max_spread_pct: float) -> bool:
    bid, ask = _bid_ask(row)
    if not (bid and ask and bid > 0 and ask > 0):
        return True  # no book -> fall back to ltp; nothing to reject on
    mid = (bid + ask) / 2.0
    return (ask - bid) / mid <= max_spread_pct


def _nearest_strike(strikes: List[float], target: float) -> float:
    return min(strikes, key=lambda s: abs(s - target))


def _row(chain, strike, ot):
    return next((r for r in chain if r.strike == strike and r.option_type == ot), None)


def build_iron_fly(chain, spot, wing_pct, qty, trade_date: date,
                   max_spread_pct: float = 0.05) -> Optional[IronFly]:
    strikes = sorted({r.strike for r in chain})
    if not strikes:
        return None
    atm = _nearest_strike(strikes, spot)
    call_wing = _nearest_strike(strikes, spot * (1 + wing_pct))
    put_wing = _nearest_strike(strikes, spot * (1 - wing_pct))
    if call_wing <= atm or put_wing >= atm:
        return None

    specs = [("SELL", "CE", atm), ("SELL", "PE", atm),
             ("BUY", "CE", call_wing), ("BUY", "PE", put_wing)]
    legs: List[FlyLeg] = []
    for side, ot, k in specs:
        r = _row(chain, k, ot)
        if r is None:
            return None
        bid, ask = _bid_ask(r)
        if not (bid and ask and bid > 0 and ask > 0):
            return None  # entry requires a live quote per leg (spec §3)
        if not _spread_ok(r, max_spread_pct):
            return None
        legs.append(FlyLeg(side=side, option_type=ot, strike=k, entry_mid=(bid + ask) / 2.0))

    credit_unit = sum((l.entry_mid if l.side == "SELL" else -l.entry_mid) for l in legs)
    if credit_unit <= 0:
        return None
    net_credit = credit_unit * qty
    entry_fees = sum(option_order_fees(premium=l.entry_mid, quantity=qty,
                                       side=l.side, trade_date=trade_date).total
                     for l in legs)
    width = max(call_wing - atm, atm - put_wing)
    max_loss = width * qty - net_credit
    return IronFly(short_strike=atm, call_wing=call_wing, put_wing=put_wing, legs=legs,
                   net_credit_per_unit=credit_unit, qty=qty, net_credit=net_credit,
                   entry_fees=entry_fees, max_loss=max_loss)


def mark_to_close(fly: IronFly, mids: Dict[Tuple[float, str], float]) -> Optional[float]:
    total = 0.0
    for l in fly.legs:
        m = mids.get((l.strike, l.option_type))
        if m is None:
            return None
        total += (m if l.side == "SELL" else -m)
    return total * fly.qty


def unrealized_pnl(fly: IronFly, mids) -> Optional[float]:
    cost = mark_to_close(fly, mids)
    return None if cost is None else fly.net_credit - cost


def exit_fees(fly: IronFly, mids, trade_date: date) -> Optional[float]:
    total = 0.0
    for l in fly.legs:
        m = mids.get((l.strike, l.option_type))
        if m is None:
            return None
        close_side = "BUY" if l.side == "SELL" else "SELL"
        total += option_order_fees(premium=m, quantity=fly.qty,
                                   side=close_side, trade_date=trade_date).total
    return total
