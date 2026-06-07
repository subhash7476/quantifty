"""
Portfolio View
--------------
A read-only projection of the portfolio built from the existing execution
trackers. PortfolioView is NOT a source of truth (ADR-001 — Ledger Is Truth):
it never mutates the trackers and holds no state of its own. Given a price
snapshot and the current cash balance it returns an immutable PortfolioSnapshot.

It is the generalization of ExecutionHandler.get_stats() into a reusable,
deterministic surface (PORTFOLIO_STATE_DISCOVERY.md section 5.2). Every field is
a pass-through of an existing tracker calculation — no new financial logic.
"""

from dataclasses import dataclass
from typing import Dict

from core.execution.position_tracker import PositionTracker
from core.execution.pnl_tracker import PnLTracker
from core.execution.margin_tracker import MarginTracker
from core.execution.position_models import Position


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Immutable point-in-time projection of the portfolio."""
    positions: Dict[str, Position]
    cash_balance: float
    realized_pnl: float
    unrealized_pnl: float
    mtm_equity: float
    gross_exposure: float
    used_margin: float


class PortfolioView:
    """
    Read-only aggregation surface over the execution trackers.

    Bound to its data sources at construction; each call to snapshot() reads
    them and returns an immutable PortfolioSnapshot for the supplied prices and
    cash balance. The view mutates nothing.
    """

    def __init__(
        self,
        position_tracker: PositionTracker,
        pnl_tracker: PnLTracker,
        margin_tracker: MarginTracker,
    ):
        self.position_tracker = position_tracker
        self.pnl_tracker = pnl_tracker
        self.margin_tracker = margin_tracker

    def snapshot(self, current_prices: Dict[str, float], cash_balance: float) -> PortfolioSnapshot:
        realized_pnl = self.pnl_tracker.get_realized_pnl()
        unrealized_pnl = self.pnl_tracker.get_unrealized_pnl(current_prices)
        return PortfolioSnapshot(
            positions=self.position_tracker.get_all_positions(),
            cash_balance=cash_balance,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            mtm_equity=cash_balance + unrealized_pnl,
            gross_exposure=self.margin_tracker.get_exposure(current_prices),
            used_margin=self.margin_tracker.get_used_margin(current_prices),
        )
