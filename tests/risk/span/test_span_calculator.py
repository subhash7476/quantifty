"""MM9.4-S3 — SpanMarginCalculator tests.

Groups:
  A — Protocol conformance
  B — Margin calculation (get_exposure, get_used_margin)
  C — Exception hierarchy
  D — Incremental margin
  E — Deterministic behaviour
  F — Import isolation
  G — Multi-position integration
"""

from datetime import date
from pathlib import Path

import pytest

from core.execution.position_tracker import PositionTracker
from core.execution.position_models import Position, PositionSide
from core.instruments.equity import Equity
from core.risk.margin_calculator import MarginCalculator
from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray
from core.risk.span.span_calculator import (
    SpanMarginCalculator,
    SpanMarginError,
    UnsupportedInstrument,
    MissingRiskArray,
    MissingRiskMetric,
    SPAN_METRIC_SCAN_RISK,
    SPAN_METRIC_SHORT_OPTION_MIN,
)


# --------------------------------------------------------------------------- #
# Test helpers
# --------------------------------------------------------------------------- #

def _tracker_with(*positions):
    pt = PositionTracker()
    for sym, qty, avg, side in positions:
        pt._positions[sym] = Position(
            instrument=Equity(sym), side=side, quantity=qty, avg_price=avg)
    return pt


def _snapshot(risk_data):
    """Build a SpanSnapshot with given risk arrays: {symbol: {metric: value}}."""
    return SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash="test",
        risk_arrays={
            sym: SpanRiskArray(symbol=sym, risk_metrics=metrics)
            for sym, metrics in risk_data.items()
        },
        metadata={},
    )


# --------------------------------------------------------------------------- #
# A — Protocol conformance
# --------------------------------------------------------------------------- #

def test_satisfies_margin_calculator_protocol():
    pt = _tracker_with()
    snap = _snapshot({})
    calc = SpanMarginCalculator(pt, snap)
    # Structural conformance: has all protocol members
    assert hasattr(calc, "margin_rate")
    assert callable(getattr(calc, "get_exposure", None))
    assert callable(getattr(calc, "get_used_margin", None))


def test_has_margin_rate_attribute():
    pt = _tracker_with()
    snap = _snapshot({})
    calc = SpanMarginCalculator(pt, snap, margin_rate=0.15)
    assert calc.margin_rate == 0.15


def test_default_margin_rate():
    pt = _tracker_with()
    snap = _snapshot({})
    calc = SpanMarginCalculator(pt, snap)
    assert calc.margin_rate == 1.0


def test_does_not_inherit_protocol():
    """SpanMarginCalculator must not inherit from MarginCalculator."""
    assert MarginCalculator not in SpanMarginCalculator.__bases__


# --------------------------------------------------------------------------- #
# B — Margin calculation
# --------------------------------------------------------------------------- #

def test_get_exposure_empty_book():
    pt = _tracker_with()
    snap = _snapshot({})
    calc = SpanMarginCalculator(pt, snap)
    assert calc.get_exposure({}) == 0.0


def test_get_exposure_single_position():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 0.15, SPAN_METRIC_SHORT_OPTION_MIN: 0.08}})
    calc = SpanMarginCalculator(pt, snap)
    exposure = calc.get_exposure({"NIFTY": 200.0})
    assert exposure == 10 * 200.0 * 1.0  # qty * price * multiplier(Equity=1.0)


def test_get_used_margin_single_position():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 0.15, SPAN_METRIC_SHORT_OPTION_MIN: 0.08}})
    calc = SpanMarginCalculator(pt, snap)
    # notional = 10 * 200 * 1 = 2000
    # risk_pct = max(0.15, 0.08) = 0.15
    # margin = 2000 * 0.15 * margin_rate(1.0) = 300
    margin = calc.get_used_margin({"NIFTY": 200.0})
    assert margin == 300.0


def test_get_used_margin_uses_short_option_min_when_higher():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 0.05, SPAN_METRIC_SHORT_OPTION_MIN: 0.12}})
    calc = SpanMarginCalculator(pt, snap)
    # risk_pct = max(0.05, 0.12) = 0.12
    margin = calc.get_used_margin({"NIFTY": 200.0})
    assert margin == 10 * 200.0 * 1.0 * 0.12


def test_get_used_margin_applies_margin_rate():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 0.15, SPAN_METRIC_SHORT_OPTION_MIN: 0.08}})
    calc = SpanMarginCalculator(pt, snap, margin_rate=1.5)
    # margin = 2000 * 0.15 * 1.5 = 450
    margin = calc.get_used_margin({"NIFTY": 200.0})
    assert margin == 450.0


def test_get_exposure_single_symbol():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG),
                       ("BANKNIFTY", 5, 200.0, PositionSide.LONG))
    snap = _snapshot({
        "NIFTY": {SPAN_METRIC_SCAN_RISK: 0.15, SPAN_METRIC_SHORT_OPTION_MIN: 0.08},
        "BANKNIFTY": {SPAN_METRIC_SCAN_RISK: 0.18, SPAN_METRIC_SHORT_OPTION_MIN: 0.10},
    })
    calc = SpanMarginCalculator(pt, snap)
    # Only NIFTY exposure
    nifty_exposure = calc.get_exposure({"NIFTY": 200.0, "BANKNIFTY": 400.0}, symbol="NIFTY")
    assert nifty_exposure == 10 * 200.0 * 1.0


# --------------------------------------------------------------------------- #
# C — Exception hierarchy
# --------------------------------------------------------------------------- #

def test_span_margin_error_is_base():
    assert issubclass(MissingRiskArray, SpanMarginError)
    assert issubclass(MissingRiskMetric, SpanMarginError)
    assert issubclass(UnsupportedInstrument, SpanMarginError)


def test_missing_risk_array_raised():
    pt = _tracker_with(("UNKNOWN", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({})  # no risk array for UNKNOWN
    calc = SpanMarginCalculator(pt, snap)
    with pytest.raises(MissingRiskArray):
        calc.get_used_margin({"UNKNOWN": 200.0})


def test_missing_risk_metric_raised():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 0.15}})  # missing short_option_min
    calc = SpanMarginCalculator(pt, snap)
    with pytest.raises(MissingRiskMetric):
        calc.get_used_margin({"NIFTY": 200.0})


def test_missing_scan_risk_raised():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SHORT_OPTION_MIN: 0.08}})  # missing scan_risk
    calc = SpanMarginCalculator(pt, snap)
    with pytest.raises(MissingRiskMetric):
        calc.get_used_margin({"NIFTY": 200.0})


# --------------------------------------------------------------------------- #
# D — Incremental margin
# --------------------------------------------------------------------------- #

def test_get_incremental_margin():
    pt = _tracker_with()
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 0.15, SPAN_METRIC_SHORT_OPTION_MIN: 0.08}})
    calc = SpanMarginCalculator(pt, snap)
    # notional = 50 * 200 * 1 = 10000
    # risk_pct = 0.15
    # incremental = 10000 * 0.15 = 1500
    result = calc.get_incremental_margin("NIFTY", 50, 200.0)
    assert result == 1500.0


def test_get_incremental_margin_with_lot_size():
    pt = _tracker_with()
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 0.15, SPAN_METRIC_SHORT_OPTION_MIN: 0.08}})
    calc = SpanMarginCalculator(pt, snap)
    # notional = 2 * 200 * 65 = 26000
    # risk_pct = 0.15
    # incremental = 26000 * 0.15 = 3900
    result = calc.get_incremental_margin("NIFTY", 2, 200.0, lot_size=65)
    assert result == 3900.0


def test_get_incremental_margin_missing_risk_array():
    pt = _tracker_with()
    snap = _snapshot({})
    calc = SpanMarginCalculator(pt, snap)
    with pytest.raises(MissingRiskArray):
        calc.get_incremental_margin("UNKNOWN", 50, 200.0)


# --------------------------------------------------------------------------- #
# E — Deterministic behaviour
# --------------------------------------------------------------------------- #

def test_same_inputs_same_output():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 0.15, SPAN_METRIC_SHORT_OPTION_MIN: 0.08}})
    calc = SpanMarginCalculator(pt, snap)
    prices = {"NIFTY": 200.0}
    a = calc.get_used_margin(prices)
    b = calc.get_used_margin(prices)
    assert a == b


def test_no_filesystem_io():
    """Calculator must not read/write files."""
    src = Path(__file__).resolve().parents[3] / "core" / "risk" / "span" / "span_calculator.py"
    content = src.read_text(encoding="utf-8")
    assert "open(" not in content
    assert "Path(" not in content
    assert ".read" not in content
    assert ".write" not in content


# --------------------------------------------------------------------------- #
# F — Import isolation
# --------------------------------------------------------------------------- #

def test_does_not_import_repository():
    src = Path(__file__).resolve().parents[3] / "core" / "risk" / "span" / "span_calculator.py"
    content = src.read_text(encoding="utf-8")
    assert "span_repository" not in content
    assert "SpanRepository" not in content


def test_does_not_import_parser():
    src = Path(__file__).resolve().parents[3] / "core" / "risk" / "span" / "span_calculator.py"
    content = src.read_text(encoding="utf-8")
    assert "span_parser" not in content
    assert "ParserRegistry" not in content


def test_does_not_import_pipeline():
    src = Path(__file__).resolve().parents[3] / "core" / "risk" / "span" / "span_calculator.py"
    content = src.read_text(encoding="utf-8")
    assert "span_pipeline" not in content


def test_does_not_import_readiness():
    src = Path(__file__).resolve().parents[3] / "core" / "risk" / "span" / "span_calculator.py"
    content = src.read_text(encoding="utf-8")
    assert "span_readiness" not in content


# --------------------------------------------------------------------------- #
# G — Multi-position integration
# --------------------------------------------------------------------------- #

def test_multi_position_exposure():
    pt = _tracker_with(
        ("NIFTY", 10, 100.0, PositionSide.LONG),
        ("BANKNIFTY", 5, 200.0, PositionSide.SHORT),
    )
    snap = _snapshot({
        "NIFTY": {SPAN_METRIC_SCAN_RISK: 0.15, SPAN_METRIC_SHORT_OPTION_MIN: 0.08},
        "BANKNIFTY": {SPAN_METRIC_SCAN_RISK: 0.18, SPAN_METRIC_SHORT_OPTION_MIN: 0.10},
    })
    calc = SpanMarginCalculator(pt, snap)
    prices = {"NIFTY": 200.0, "BANKNIFTY": 400.0}
    exposure = calc.get_exposure(prices)
    assert exposure == 10 * 200.0 + 5 * 400.0  # 2000 + 2000 = 4000


def test_multi_position_used_margin():
    pt = _tracker_with(
        ("NIFTY", 10, 100.0, PositionSide.LONG),
        ("BANKNIFTY", 5, 200.0, PositionSide.SHORT),
    )
    snap = _snapshot({
        "NIFTY": {SPAN_METRIC_SCAN_RISK: 0.15, SPAN_METRIC_SHORT_OPTION_MIN: 0.08},
        "BANKNIFTY": {SPAN_METRIC_SCAN_RISK: 0.18, SPAN_METRIC_SHORT_OPTION_MIN: 0.10},
    })
    calc = SpanMarginCalculator(pt, snap)
    prices = {"NIFTY": 200.0, "BANKNIFTY": 400.0}
    # NIFTY: notional=2000, risk=max(0.15,0.08)=0.15, margin=300
    # BANKNIFTY: notional=2000, risk=max(0.18,0.10)=0.18, margin=360
    # total = 660
    margin = calc.get_used_margin(prices)
    assert margin == 660.0
