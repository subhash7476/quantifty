"""Order-placement rules imposed by the Closing Auction Session.

Stop-loss, IOC, iceberg, and disclosed-quantity orders are rejected during CAS;
market orders are barred once Order Entry II opens at 15:25. Separately, broker
MIS auto-square-off for Category I cash moved to ~15:12, which is EARLIER than
the 15:29 close a naive intraday backtest would exit at — an execution
feasibility limit, not a cost adjustment.
"""
from __future__ import annotations

from datetime import date, datetime, time

from core.market.session_schedule import CAS_EFFECTIVE, session_window

MIS_SQUAREOFF = time(15, 12)
MARKET_ORDER_CUTOFF = time(15, 25)

_AUCTION_BANNED = frozenset({"SL", "SL-M", "IOC", "ICEBERG", "DISCLOSED"})


def is_order_type_permitted(order_type: str, dt: datetime) -> bool:
    """Whether `order_type` may be sent to the cash segment at `dt`."""
    if dt.date() < CAS_EFFECTIVE:
        return True
    auction = session_window("cash_auction", dt.date())
    if auction is None or not (auction[0] <= dt.time() < auction[1]):
        return True
    normalized = order_type.upper()
    if normalized in _AUCTION_BANNED:
        return False
    if normalized == "MARKET":
        return dt.time() < MARKET_ORDER_CUTOFF
    return True


def latest_intraday_exit(on: date) -> time:
    """The last moment an MIS intraday cash position can be exited by choice."""
    if on < CAS_EFFECTIVE:
        return session_window("cash_cat1", on)[1]
    return MIS_SQUAREOFF
