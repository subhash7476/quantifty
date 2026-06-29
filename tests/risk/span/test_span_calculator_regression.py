"""MM9.5-S3 — Group R: Calculator regression tests against v400 snapshots.

NIFTY lot size = 65 (verified from instrument database, post-Oct-2025 NSE revision)
BANKNIFTY lot size = 30 (verified from instrument database)

Tests are skipped when the reference SPAN file is absent.
"""

import pathlib

import pytest

from datetime import date
from core.execution.position_tracker import PositionTracker
from core.execution.position_models import Position, PositionSide
from core.instruments.equity import Equity
from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray
from core.risk.span.span_calculator import (
    SpanMarginCalculator,
    SPAN_METRIC_SCAN_RISK,
    SPAN_METRIC_SHORT_OPTION_MIN,
    SPAN_METRIC_PRICE_SCAN_RANGE,
)

SPAN_FILE = (
    pathlib.Path(__file__).resolve().parents[3]
    / "reference" / "span" / "nsccl.20260625.i1" / "nsccl.20260625.i01.spn"
)

pytestmark = pytest.mark.skipif(
    not SPAN_FILE.exists(),
    reason="Reference SPAN file absent — run without real-file regression",
)


def _tracker_with(sym: str, qty: int, lot_size: int = 1):
    pt = PositionTracker()
    inst = Equity(sym)
    object.__setattr__(inst, "lot_size", lot_size)
    pt._positions[sym] = Position(
        instrument=inst, side=PositionSide.LONG, quantity=qty, avg_price=100.0)
    return pt


@pytest.fixture(scope="module")
def real_snapshot():
    from core.risk.span.parser_v400 import parse_span_xml
    return parse_span_xml(SPAN_FILE.read_bytes())


def test_r1_v400_scan_risk_is_absolute_not_fraction(real_snapshot):
    """scan_risk from v400 parser is ~2244 (Rs/unit), not 0.xx fraction."""
    sr = real_snapshot.risk_arrays["NIFTY"].risk_metrics[SPAN_METRIC_SCAN_RISK]
    assert sr > 100.0, f"scan_risk {sr} looks like a fraction, not Rs/unit"


def test_r2_nifty_margin_from_reference_snapshot(real_snapshot):
    """10 NIFTY lots at current lot size 65.
    margin = 10 x 65 x 2244.36 = 1,458,834 Rs (independently of price)."""
    pt = _tracker_with("NIFTY", qty=10, lot_size=65)
    calc = SpanMarginCalculator(pt, real_snapshot)
    margin_24k = calc.get_used_margin({"NIFTY": 24000.0})
    margin_25k = calc.get_used_margin({"NIFTY": 25000.0})
    assert margin_24k == margin_25k, "Absolute-Rs margin must be price-independent"
    assert margin_24k == pytest.approx(1_458_834.0, abs=1.0)


def test_r3_banknifty_margin_from_reference_snapshot(real_snapshot):
    """5 BANKNIFTY lots at lot size 30.
    margin = 5 x 30 x 5513.40 = 827,010 Rs.
    BANKNIFTY lot size = 30 (verified from instrument database)."""
    pt = _tracker_with("BANKNIFTY", qty=5, lot_size=30)
    calc = SpanMarginCalculator(pt, real_snapshot)
    margin = calc.get_used_margin({"BANKNIFTY": 52000.0})
    assert margin == pytest.approx(827_010.0, abs=1.0)


def test_r4_get_snapshot_param_price_scan_range_from_v400(real_snapshot):
    calc = SpanMarginCalculator(PositionTracker(), real_snapshot)
    psr = calc.get_snapshot_param("NIFTY", SPAN_METRIC_PRICE_SCAN_RANGE)
    assert psr == pytest.approx(2234.01, abs=0.01)


def test_r5_get_snapshot_param_risk_free_rate_from_v400(real_snapshot):
    calc = SpanMarginCalculator(PositionTracker(), real_snapshot)
    rfr = calc.get_snapshot_param("NIFTY", "risk_free_rate")
    assert rfr == pytest.approx(0.07, abs=0.001)


def test_r6_determinism_with_v400_snapshot(real_snapshot):
    pt = _tracker_with("NIFTY", qty=10, lot_size=65)
    calc = SpanMarginCalculator(pt, real_snapshot)
    prices = {"NIFTY": 24000.0}
    assert calc.get_used_margin(prices) == calc.get_used_margin(prices)


def test_r7_margin_independent_of_price(real_snapshot):
    pt = _tracker_with("NIFTY", qty=10, lot_size=65)
    calc = SpanMarginCalculator(pt, real_snapshot)
    assert calc.get_used_margin({"NIFTY": 20000.0}) == calc.get_used_margin({"NIFTY": 30000.0})
