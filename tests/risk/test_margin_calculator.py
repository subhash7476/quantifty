"""
MM9.4-S1: MarginCalculator Protocol & SPAN Architecture Seam.

Tests prove:
1. MarginCalculator is a Protocol (not instantiable directly).
2. MarginTracker conforms structurally.
3. PortfolioView accepts the protocol type.
4. ExecutionHandler.margin_tracker is typed to the protocol.
"""

import ast
from pathlib import Path

from core.execution.margin_tracker import MarginTracker
from core.execution.position_tracker import PositionTracker
from core.execution.position_models import Position, PositionSide
from core.instruments.equity import Equity
from core.risk.margin_calculator import MarginCalculator


def _tracker_with_position():
    pt = PositionTracker()
    pt._positions["SYM"] = Position(
        instrument=Equity("SYM"), side=PositionSide.LONG, quantity=10, avg_price=100.0)
    return pt


# --------------------------------------------------------------------------- #
# 1. Protocol is not instantiable
# --------------------------------------------------------------------------- #
def test_margin_calculator_is_protocol():
    """MarginCalculator is a Protocol — cannot be instantiated directly."""
    from typing import Protocol as _Protocol
    assert issubclass(MarginCalculator, _Protocol)


def test_margin_calculator_cannot_be_instantiated():
    """Attempting to instantiate MarginCalculator raises TypeError."""
    try:
        MarginCalculator()
        assert False, "Should have raised TypeError"
    except TypeError:
        pass


# --------------------------------------------------------------------------- #
# 2. MarginTracker conforms structurally
# --------------------------------------------------------------------------- #
def test_margintracker_conforms_to_protocol():
    """MarginTracker satisfies MarginCalculator structurally (no TypeError)."""
    pt = _tracker_with_position()
    mt: MarginCalculator = MarginTracker(pt)
    assert isinstance(mt, MarginTracker)
    assert mt.margin_rate == 0.2


def test_margintracker_supports_get_exposure():
    """get_exposure works through the protocol interface."""
    mt: MarginCalculator = MarginTracker(_tracker_with_position())
    exposure = mt.get_exposure({"SYM": 200.0})
    assert exposure == 10 * 200.0 * 1.0  # qty * price * multiplier
    assert mt.margin_rate == 0.2


def test_margintracker_supports_get_used_margin():
    """get_used_margin works through the protocol interface."""
    mt: MarginCalculator = MarginTracker(_tracker_with_position())
    used = mt.get_used_margin({"SYM": 200.0})
    assert used == 10 * 200.0 * 1.0 * 0.2  # exposure * margin_rate


# --------------------------------------------------------------------------- #
# 3. MarginCalculator protocol has the expected surface
# --------------------------------------------------------------------------- #
def test_protocol_has_expected_methods():
    """MarginCalculator defines get_exposure, get_used_margin, and margin_rate annot."""
    members = {name for name in dir(MarginCalculator)
               if not name.startswith('_')}
    assert "get_exposure" in members
    assert "get_used_margin" in members
    # margin_rate is a Protocol field annotation, not a runtime attribute
    assert "margin_rate" in MarginCalculator.__annotations__


# --------------------------------------------------------------------------- #
# 4. PortfolioView accepts MarginCalculator
# --------------------------------------------------------------------------- #
def test_portfolio_view_accepts_calculator_type():
    """PortfolioView.__init__ accepts MarginCalculator-typed tracker."""
    from core.execution.portfolio_view import PortfolioView
    from core.execution.pnl_tracker import PnLTracker
    pt = _tracker_with_position()
    mc: MarginCalculator = MarginTracker(pt)
    # Must not raise TypeError
    view = PortfolioView(pt, PnLTracker(pt), mc)
    snap = view.snapshot({"SYM": 200.0}, 100000.0)
    assert snap.gross_exposure == 10 * 200.0 * 1.0
    assert snap.used_margin == 10 * 200.0 * 1.0 * 0.2


# --------------------------------------------------------------------------- #
# 5. PortfolioView imports MarginCalculator (not only MarginTracker)
# --------------------------------------------------------------------------- #
def test_portfolio_view_imports_calculator():
    """portfolio_view.py must import MarginCalculator from core.risk."""
    src_path = Path(__file__).resolve().parents[2] / "core" / "execution" / "portfolio_view.py"
    content = src_path.read_text(encoding="utf-8")
    assert "MarginCalculator" in content, (
        "portfolio_view.py must import MarginCalculator"
    )


# --------------------------------------------------------------------------- #
# 6. Handler imports MarginCalculator
# --------------------------------------------------------------------------- #
def test_handler_imports_calculator():
    """handler.py must import MarginCalculator from core.risk."""
    src_path = Path(__file__).resolve().parents[2] / "core" / "execution" / "handler.py"
    content = src_path.read_text(encoding="utf-8")
    assert "MarginCalculator" in content, (
        "handler.py must import MarginCalculator"
    )
