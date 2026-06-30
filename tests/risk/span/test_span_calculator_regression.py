"""MM9.5-S3 — Group R: Calculator regression tests against v400 snapshots.

NIFTY lot size = 65 (verified from instrument database, post-Oct-2025 NSE revision)
BANKNIFTY lot size = 30 (verified from instrument database)

Tests are skipped when the reference SPAN file is absent.

MM10.2: R8 (futures far-month), R9 (option contract), R10 (backward equivalence).
"""

import pathlib

import pytest

from datetime import date
from core.execution.position_tracker import PositionTracker
from core.execution.position_models import Position, PositionSide
from core.instruments.equity import Equity
from core.instruments.future import Future
from core.instruments.option import Option, OptionType
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


def test_r8_futures_far_month_per_contract_routing(real_snapshot):
    """Future with Jul-2026 expiry uses its own RA (2255.78), not nearest (2244.36)."""
    pt = PositionTracker()
    inst = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(
        instrument=inst, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    calc = SpanMarginCalculator(pt, real_snapshot)
    margin = calc.get_used_margin({"NIFTY25JUL": 24000.0})
    assert margin == pytest.approx(1_466_257.0, abs=1.0)
    assert margin != pytest.approx(1_458_834.0, abs=1.0)


def test_r9_option_contract_per_strike_routing(real_snapshot):
    """Option contracts use per-strike RA, not nearest-futures scan risk."""
    pt_a = PositionTracker()
    inst_a = Option(
        "NIFTY25JUL23750CE", underlying="NIFTY", expiry=date(2026, 7, 28),
        strike=23750.0, option_type=OptionType.CALL, lot_size=65,
    )
    pt_a._positions["NIFTY25JUL23750CE"] = Position(
        instrument=inst_a, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    calc_a = SpanMarginCalculator(pt_a, real_snapshot)

    pt_b = PositionTracker()
    inst_b = Option(
        "NIFTY25JUL23750PE", underlying="NIFTY", expiry=date(2026, 7, 28),
        strike=23750.0, option_type=OptionType.PUT, lot_size=65,
    )
    pt_b._positions["NIFTY25JUL23750PE"] = Position(
        instrument=inst_b, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    calc_b = SpanMarginCalculator(pt_b, real_snapshot)

    margin_a = calc_a.get_used_margin({"NIFTY25JUL23750CE": 24000.0})
    margin_b = calc_b.get_used_margin({"NIFTY25JUL23750PE": 24000.0})
    assert margin_a == pytest.approx(395_330.0, abs=1.0)
    assert margin_b == pytest.approx(143_390.0, abs=1.0)
    assert margin_a != margin_b


def test_r10_backward_equivalence_nearest_expiry(real_snapshot):
    """Nearest-expiry Future contract matches symbol-level R2 value."""
    pt = PositionTracker()
    inst = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(
        instrument=inst, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    calc = SpanMarginCalculator(pt, real_snapshot)
    margin = calc.get_used_margin({"NIFTY25JUN": 24000.0})
    assert margin == pytest.approx(1_458_834.0, abs=1.0)
