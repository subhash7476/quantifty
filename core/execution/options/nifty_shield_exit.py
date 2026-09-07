"""NiftyShield — execution exit-manager (Decomposition Spec D5).

Owns each OrderGroup from fill to close, evaluated per bar against real marks
via GroupPnLTracker.get_group_unrealized_pnl. Triggers, in priority order:

  1. Take-profit:  group P&L >= tp_pct × credit_received        -> close
  2. Stop:         defined-risk  P&L <= -sl_frac × max_loss     -> close
                   undefined     P&L <= -sl_mult × credit       -> close
  3. Hard time:    bar time >= exit_time (15:15)                -> close
  4. Delta gate:   portfolio |delta| > max_portfolio_delta      -> close (flatten)

The stop has two forms because NiftyShield builds two kinds of structure. A
credit multiple cannot bound a defined-risk structure: its loss is capped at
`wing_width x qty - credit`, so `-sl_mult x credit` is reachable only when
`max_loss / credit >= sl_mult`. Over the certified 13pm facts that holds for
only 10.5% of defined-risk entries (iron_fly 0 of 56), so the stop was
arithmetic that could not fire. Straddle and strangle have no structural bound
and there the credit multiple is the only rule available, so
`stop_loss_multiplier` is kept for them -- it is not a back-compat shim.

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
        self._sl_frac = float(cfg.get("stop_loss_max_loss_frac", 0.50))
        self._exit_h = int(cfg.get("exit_time", {}).get("hour", 15))
        self._exit_m = int(cfg.get("exit_time", {}).get("minute", 15))
        self._max_delta = float(cfg.get("max_portfolio_delta", 500))

    def evaluate(self, group_id: UUID, credit_received: float,
                 current_prices: Dict[str, float],
                 bar_time: Optional[datetime],
                 portfolio_delta: float = 0.0,
                 max_loss: Optional[float] = None) -> Optional[str]:
        """Return the exit reason to close the group, or None to hold.

        credit_received: the group's realized entry premium (execution knows it
        from fills). bar_time None is treated as "pre-time" (never triggers the
        hard exit); portfolio_delta is the Black-76 net portfolio delta.

        max_loss: the structure's worst-case loss in Rs, or None when it has no
        structural bound -- an undefined structure, or a defined one whose
        wings did not all fill (a fly missing a wing is not defined-risk, and a
        stop set to a fraction of a fabricated bound is worse than one that
        never fires). None selects the credit-multiple stop.
        """
        pnl = self._group_pnl.get_group_unrealized_pnl(group_id, current_prices)

        if pnl >= self._tp_pct * max(credit_received, 0.0):
            return "take_profit"
        if self._stop_hit(pnl, credit_received, max_loss):
            return "stop_loss"
        if bar_time is not None and bar_time.time() >= time(self._exit_h, self._exit_m):
            return "time_exit"
        if abs(portfolio_delta) > self._max_delta:
            return "delta_flatten"
        return None

    def _stop_hit(self, pnl: float, credit_received: float,
                  max_loss: Optional[float]) -> bool:
        if max_loss is not None and max_loss > 0.0:
            return pnl <= -self._sl_frac * max_loss
        return pnl <= -self._sl_mult * max(credit_received, 0.0)
