"""NiftyShield — execution exit-manager (Decomposition Spec D5).

Owns each OrderGroup from fill to close, evaluated per bar against real marks
via GroupPnLTracker.get_group_unrealized_pnl. Triggers, in priority order:

  1. Take-profit:  group P&L >= tp_pct × credit_received        -> close
  2. Stop:         group P&L <= -sl_mult × credit_received      -> close
  3. Hard time:    bar time >= exit_time (15:15)                -> close
  4. Delta gate:   portfolio |delta| > max_portfolio_delta      -> close (flatten)

No dynamic hedge (D1) — the delta gate closes the structure; it never opens a
hedge leg. Exit decisions live here, never in the strategy (Principle #3).
"""
from __future__ import annotations

from datetime import datetime, time
from typing import Any, Dict, List, Optional
from uuid import UUID

from core.execution.groups.group_pnl import GroupPnLTracker


class NiftyShieldExitManager:
    """Per-bar exit-trigger evaluation for NiftyShield OrderGroups."""

    def __init__(self, group_pnl: GroupPnLTracker, cfg: Dict[str, Any]):
        self._group_pnl = group_pnl
        self._tp_pct = float(cfg.get("profit_target_pct", 0.50))
        self._sl_mult = float(cfg.get("stop_loss_multiplier", 2.0))
        self._exit_h = int(cfg.get("exit_time", {}).get("hour", 15))
        self._exit_m = int(cfg.get("exit_time", {}).get("minute", 15))
        self._max_delta = float(cfg.get("max_portfolio_delta", 500))

    def evaluate(self, group_id: UUID, credit_received: float,
                 current_prices: Dict[str, float],
                 bar_time: Optional[datetime],
                 portfolio_delta: float = 0.0) -> Optional[str]:
        """Return the exit reason to close the group, or None to hold.

        credit_received: the group's realized entry premium (execution knows it
        from fills). bar_time None is treated as "pre-time" (never triggers the
        hard exit); portfolio_delta is the Black-76 net portfolio delta.
        """
        pnl = self._group_pnl.get_group_unrealized_pnl(group_id, current_prices)

        if pnl >= self._tp_pct * max(credit_received, 0.0):
            return "take_profit"
        if pnl <= -self._sl_mult * max(credit_received, 0.0):
            return "stop_loss"
        if bar_time is not None and bar_time.time() >= time(self._exit_h, self._exit_m):
            return "time_exit"
        if abs(portfolio_delta) > self._max_delta:
            return "delta_flatten"
        return None
