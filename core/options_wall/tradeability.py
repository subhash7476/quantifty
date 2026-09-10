"""Why a screen row can or cannot become a trade right now.

A row on the farm list is a **screen pass**, not an entry signal. The dashboard
rendered the two identically, and on 2026-09-10 that cost a live decision: trade
31 was closed manually at 15:03 in the expectation of re-entering on a visible
`Premium farm` row, which `entry_end = 15:00` had already foreclosed. Held, its
TP would have fired at 15:20:50.

The order of tests mirrors `PaperExecutor.step` exactly — an open position
short-circuits before the entry window is consulted — so the badge cannot claim
a row is tradeable when the executor would decline it, or vice versa.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict

from core.options_wall.paper_executor import PaperConfig, _hhmm

TRADED_SCREEN = "premium_farm"


def tradeability(row: Dict, now: datetime, has_open_position: bool,
                 derivatives_open: bool,
                 config: PaperConfig | None = None) -> Dict[str, str]:
    """`{"state": ..., "reason": ...}` for one scan row, evaluated at `now`.

    States: `tradeable`, `window_closed`, `position_open`, `market_closed`,
    `not_actionable`.
    """
    cfg = config or PaperConfig()

    if row.get("screen") != TRADED_SCREEN:
        return {"state": "not_actionable",
                "reason": "Discovery screen — only premium farm rows are traded"}
    if has_open_position:
        return {"state": "position_open",
                "reason": "A position is already open on this underlying — one at a time"}
    if not derivatives_open:
        return {"state": "market_closed",
                "reason": "The derivatives segment is closed"}

    t = now.time()
    if t < _hhmm(cfg.entry_start):
        return {"state": "window_closed",
                "reason": f"The entry window opens at {cfg.entry_start}"}
    if t > _hhmm(cfg.entry_end):
        return {"state": "window_closed",
                "reason": f"The entry window closed at {cfg.entry_end}"}

    return {"state": "tradeable",
            "reason": f"Entry window open until {cfg.entry_end}, no position on this underlying"}
