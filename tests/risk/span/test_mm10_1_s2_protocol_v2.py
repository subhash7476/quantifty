"""MM10.1-S2 — MarginCalculator Protocol v2 tests."""

import inspect
import pytest

from core.execution.margin_tracker import MarginTracker
from core.execution.position_tracker import PositionTracker
from core.execution.handler import ExecutionHandler
from core.risk.margin_calculator import MarginCalculator


# --------------------------------------------------------------------------- #
# Structural protocol conformance
# --------------------------------------------------------------------------- #

def test_margin_tracker_satisfies_protocol_v2():
    """MarginTracker has get_incremental_margin after S2."""
    mt = MarginTracker(PositionTracker(), margin_rate=0.2)
    assert hasattr(mt, "get_incremental_margin")


def test_span_calculator_satisfies_protocol_v2():
    """SpanMarginCalculator has get_incremental_margin (regression guard)."""
    from core.risk.span.span_calculator import SpanMarginCalculator
    smc = SpanMarginCalculator(PositionTracker(), None)
    assert hasattr(smc, "get_incremental_margin")


# --------------------------------------------------------------------------- #
# Numeric correctness — MarginTracker flat rate
# --------------------------------------------------------------------------- #

def test_margin_tracker_incremental_qty2_lot75_price100():
    """margin_rate=0.2, qty=2, lot=75, price=100 → 3000.0."""
    mt = MarginTracker(PositionTracker(), margin_rate=0.2)
    result = mt.get_incremental_margin("NIFTY", 2, 100.0, lot_size=75.0)
    assert result == 3000.0


def test_margin_tracker_incremental_default_lot_size():
    """margin_rate=0.2, qty=1, price=200, no lot_size → 40.0."""
    mt = MarginTracker(PositionTracker(), margin_rate=0.2)
    result = mt.get_incremental_margin("NIFTY", 1, 200.0)
    assert result == 40.0


def test_margin_tracker_incremental_matches_prior_else_branch():
    """Numeric equivalence with old formula: abs(qty) * lot * price * rate."""
    mt = MarginTracker(PositionTracker(), margin_rate=0.2)
    qty, lot, price = 5, 65, 150.0
    protocol_result = mt.get_incremental_margin("NIFTY", qty, price, lot_size=lot)
    else_branch = abs(qty) * lot * price * mt.margin_rate
    assert protocol_result == else_branch


# --------------------------------------------------------------------------- #
# Handler uses protocol, not hasattr
# --------------------------------------------------------------------------- #

def test_handler_uses_protocol_not_hasattr():
    """_check_margin_budget no longer uses hasattr duck-typing."""
    source = inspect.getsource(ExecutionHandler._check_margin_budget)
    assert "hasattr(self.margin_tracker, 'get_incremental_margin')" not in source
