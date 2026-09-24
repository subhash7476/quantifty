"""NiftyShield — execution exit-manager (Decomposition Spec D5).

Owns each OrderGroup from fill to close, evaluated per bar against real marks
via GroupPnLTracker.get_group_unrealized_pnl. Triggers, in priority order:

  1. Take-profit:  bracket available, TP enabled, P&L >= bracket.tp_rs  -> close
  2. Stop:         bracket available,             P&L <= -bracket.sl_rs -> close
  3. Hard time:    bar time >= exit_time (15:35)                         -> close
  4. Delta gate:   portfolio |delta| > max_portfolio_delta               -> close (flatten)

The bracket is the structure's P&L at spot +/-1 sigma over the 13:00-15:35
hold (`nifty_shield_pricing.sigma_bracket`). A hold that short decays only a
few percent of a 2-8 DTE premium, so its P&L is the index move and both exits
are sized in that unit. The rules it replaces were sized in units unrelated to
the move: on 2026-09-15 the decay-based take-profit was Rs 121 (8 index points,
below the Rs 133 round trip) and the max-loss stop Rs 3,534 (245 points), and
the structure closed after two minutes for Rs 6
(docs/superpowers/specs/2026-09-15-nifty-shield-sigma-bracket-design.md).

No bracket means no take-profit and no stop — never substituted thresholds;
the clock and the delta gate still bound the structure.

No dynamic hedge (D1) — the delta gate closes the structure; it never opens a
hedge leg. Exit decisions live here, never in the strategy (Principle #3).
"""
from __future__ import annotations

from datetime import datetime, time
from typing import Any, Dict, Optional
from uuid import UUID

from core.execution.groups.group_pnl import GroupPnLTracker
from core.execution.options.nifty_shield_pricing import Bracket


class NiftyShieldExitManager:
    """Per-bar exit-trigger evaluation for NiftyShield OrderGroups."""

    def __init__(self, group_pnl: GroupPnLTracker, cfg: Dict[str, Any]):
        self._group_pnl = group_pnl
        self._exit_h = int(cfg.get("exit_time", {}).get("hour", 15))
        self._exit_m = int(cfg.get("exit_time", {}).get("minute", 35))
        self._max_delta = float(cfg.get("max_portfolio_delta", 500))

    def evaluate(self, group_id: UUID, current_prices: Dict[str, float],
                 bar_time: Optional[datetime],
                 portfolio_delta: float = 0.0,
                 bracket: Optional[Bracket] = None) -> Optional[str]:
        """Return the exit reason to close the group, or None to hold.

        bar_time None is treated as "pre-time" (never triggers the hard exit);
        portfolio_delta is the Black-76 net portfolio delta. bracket None means
        the structure has no take-profit or stop.
        """
        pnl = self._group_pnl.get_group_unrealized_pnl(group_id, current_prices)

        if bracket is not None:
            if bracket.tp_enabled and pnl >= bracket.tp_rs:
                return "take_profit"
            if pnl <= -bracket.sl_rs:
                return "stop_loss"
        if bar_time is not None and bar_time.time() >= time(self._exit_h, self._exit_m):
            return "time_exit"
        if abs(portfolio_delta) > self._max_delta:
            return "delta_flatten"
        return None
