"""A farm row is a screen pass, not an entry signal — the panel must say which.

2026-09-10: trade 31 was closed manually at 15:03 because the panel showed an
active `Premium farm` row and the operator expected to re-enter. `entry_end` is
15:00, so no re-entry was possible. Held, TP would have fired at 15:20:50 for
+Rs1,876 against the -Rs2,495 taken. The panel rendered a tradeable row and an
untradeable one identically. Flagged 2026-09-08, unfixed for two days.
"""
from datetime import datetime

from core.options_wall.tradeability import tradeability

FARM = {"screen": "premium_farm"}
_OPEN = datetime(2026, 9, 11, 11, 0)        # Friday, mid-session


def test_tradeable_when_window_open_and_flat():
    t = tradeability(FARM, now=_OPEN, has_open_position=False, derivatives_open=True)
    assert t["state"] == "tradeable"


def test_entry_window_closed_after_the_cutoff():
    t = tradeability(FARM, now=datetime(2026, 9, 11, 15, 3),
                     has_open_position=False, derivatives_open=True)
    assert t["state"] == "window_closed"
    assert "15:00" in t["reason"]


def test_entry_window_closed_before_the_open():
    t = tradeability(FARM, now=datetime(2026, 9, 11, 9, 20),
                     has_open_position=False, derivatives_open=True)
    assert t["state"] == "window_closed"
    assert "09:30" in t["reason"]


def test_open_position_preempts_entry_even_inside_the_window():
    """Mirrors PaperExecutor.step: an open row short-circuits before the window test."""
    t = tradeability(FARM, now=_OPEN, has_open_position=True, derivatives_open=True)
    assert t["state"] == "position_open"


def test_market_closed_is_reported_over_the_window():
    t = tradeability(FARM, now=_OPEN, has_open_position=False, derivatives_open=False)
    assert t["state"] == "market_closed"


def test_discovery_screens_are_never_actionable():
    for screen in ("imperfection", "laggard"):
        t = tradeability({"screen": screen}, now=_OPEN,
                         has_open_position=False, derivatives_open=True)
        assert t["state"] == "not_actionable"


def test_every_state_carries_a_human_reason():
    cases = [
        (FARM, _OPEN, False, True),
        (FARM, datetime(2026, 9, 11, 15, 3), False, True),
        (FARM, _OPEN, True, True),
        (FARM, _OPEN, False, False),
        ({"screen": "laggard"}, _OPEN, False, True),
    ]
    for row, now, has_open, deriv in cases:
        t = tradeability(row, now=now, has_open_position=has_open, derivatives_open=deriv)
        assert t["reason"] and len(t["reason"]) > 10
        assert t["state"] in {"tradeable", "window_closed", "position_open",
                              "market_closed", "not_actionable"}
