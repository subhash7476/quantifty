"""MM9.5-S3 — SpanMarginCalculator tests (absolute-Rs formula).

Groups:
  A — Protocol conformance
  B — Margin calculation (get_exposure, get_used_margin)
  C — Exception hierarchy
  D — Incremental margin
  E — Deterministic behaviour
  F — Import isolation
  G — Multi-position integration
  H — Snapshot param accessor
  I — Future contract RA routing (MM10.2-S1)
  J — Option contract RA routing (MM10.2-S2)
  K — Backward compatibility (MM10.2-S2)
"""

from datetime import date
from pathlib import Path

import pytest

from core.execution.position_tracker import PositionTracker
from core.execution.position_models import Position, PositionSide
from core.instruments.equity import Equity
from core.instruments.future import Future
from core.instruments.option import Option, OptionType
from core.instruments.instrument_base import InstrumentType
from core.risk.margin_calculator import MarginCalculator
from core.risk.span.span_snapshot import (
    SpanSnapshot,
    SpanRiskArray,
    SpanFutureContract,
    SpanOptionContract,
)
from core.risk.span.span_calculator import (
    SpanMarginCalculator,
    SpanMarginError,
    UnsupportedInstrument,
    MissingRiskArray,
    MissingRiskMetric,
    SPAN_METRIC_SCAN_RISK,
    SPAN_METRIC_SHORT_OPTION_MIN,
    SPAN_METRIC_PRICE_SCAN_RANGE,
    SPAN_METRIC_VOL_SCAN_RANGE,
    SPAN_METRIC_CVF,
    SPAN_METRIC_INTRA_SPREAD_CHARGE,
    SPAN_METRIC_RISK_FREE_RATE,
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
    """Build a SpanSnapshot with given risk arrays: {symbol: {metric: value}}.

    All metric values are in absolute Rs per underlying unit (MM9.5-S3 formula).
    """
    return SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="4.00",
        exchange="NSE",
        segment="FO",
        file_hash="test",
        is_settlement=False,
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
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    calc = SpanMarginCalculator(pt, snap)
    exposure = calc.get_exposure({"NIFTY": 200.0})
    assert exposure == 10 * 200.0 * 1.0  # qty * price * multiplier(Equity=1.0)


def test_get_used_margin_single_position():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    calc = SpanMarginCalculator(pt, snap)
    # risk = max(30.0, 16.0) = 30.0 (Rs/unit)
    # margin = qty * lot_size * risk * margin_rate = 10 * 1 * 30.0 * 1.0 = 300
    margin = calc.get_used_margin({"NIFTY": 200.0})
    assert margin == 300.0


def test_get_used_margin_uses_short_option_min_when_higher():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 10.0, SPAN_METRIC_SHORT_OPTION_MIN: 24.0}})
    calc = SpanMarginCalculator(pt, snap)
    # risk = max(10.0, 24.0) = 24.0
    # margin = 10 * 1 * 24.0 = 240
    margin = calc.get_used_margin({"NIFTY": 200.0})
    assert margin == 240.0


def test_get_used_margin_applies_margin_rate():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    calc = SpanMarginCalculator(pt, snap, margin_rate=1.5)
    # margin = 10 * 1 * 30.0 * 1.5 = 450
    margin = calc.get_used_margin({"NIFTY": 200.0})
    assert margin == 450.0


def test_get_exposure_single_symbol():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG),
                       ("BANKNIFTY", 5, 200.0, PositionSide.LONG))
    snap = _snapshot({
        "NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0},
        "BANKNIFTY": {SPAN_METRIC_SCAN_RISK: 72.0, SPAN_METRIC_SHORT_OPTION_MIN: 40.0},
    })
    calc = SpanMarginCalculator(pt, snap)
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
    # SOM absent — defaults to 0.0; scan_risk present
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0}})
    calc = SpanMarginCalculator(pt, snap)
    # SOM=0.0, max(30, 0)=30.0 → 10*1*30=300 — no raise
    assert calc.get_used_margin({"NIFTY": 200.0}) == 300.0


def test_missing_scan_risk_raised():
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})  # missing scan_risk
    calc = SpanMarginCalculator(pt, snap)
    with pytest.raises(MissingRiskMetric):
        calc.get_used_margin({"NIFTY": 200.0})


# --------------------------------------------------------------------------- #
# D — Incremental margin
# --------------------------------------------------------------------------- #

def test_get_incremental_margin():
    pt = _tracker_with()
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    calc = SpanMarginCalculator(pt, snap)
    # risk = 30.0 (Rs/unit), qty=50, lot=1 (default)
    # margin = 50 * 1 * 30.0 = 1500
    result = calc.get_incremental_margin("NIFTY", 50, 200.0)
    assert result == 1500.0


def test_get_incremental_margin_with_lot_size():
    pt = _tracker_with()
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    calc = SpanMarginCalculator(pt, snap)
    # risk = 30.0, qty=2, lot_size=65
    # margin = 2 * 65 * 30.0 = 3900
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
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    calc = SpanMarginCalculator(pt, snap)
    prices = {"NIFTY": 200.0}
    a = calc.get_used_margin(prices)
    b = calc.get_used_margin(prices)
    assert a == b


def test_no_filesystem_io():
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
        "NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0},
        "BANKNIFTY": {SPAN_METRIC_SCAN_RISK: 72.0, SPAN_METRIC_SHORT_OPTION_MIN: 40.0},
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
        "NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0},
        "BANKNIFTY": {SPAN_METRIC_SCAN_RISK: 72.0, SPAN_METRIC_SHORT_OPTION_MIN: 40.0},
    })
    calc = SpanMarginCalculator(pt, snap)
    prices = {"NIFTY": 200.0, "BANKNIFTY": 400.0}
    # NIFTY: qty=10, lot=1, risk=max(30,16)=30, margin=10*1*30=300
    # BANKNIFTY: qty=5, lot=1, risk=max(72,40)=72, margin=5*1*72=360
    # total = 660
    margin = calc.get_used_margin(prices)
    assert margin == 660.0


# --------------------------------------------------------------------------- #
# H — Snapshot param accessor
# --------------------------------------------------------------------------- #

def test_h1_get_snapshot_param_scan_risk():
    snap = _snapshot({"NIFTY": {
        SPAN_METRIC_SCAN_RISK: 30.0,
        SPAN_METRIC_SHORT_OPTION_MIN: 16.0,
    }})
    calc = SpanMarginCalculator(PositionTracker(), snap)
    assert calc.get_snapshot_param("NIFTY", SPAN_METRIC_SCAN_RISK) == 30.0


def test_h2_get_snapshot_param_price_scan_range():
    snap = _snapshot({"NIFTY": {
        SPAN_METRIC_SCAN_RISK: 30.0,
        SPAN_METRIC_SHORT_OPTION_MIN: 16.0,
        SPAN_METRIC_PRICE_SCAN_RANGE: 29.0,
        SPAN_METRIC_CVF: 1.0,
    }})
    calc = SpanMarginCalculator(PositionTracker(), snap)
    assert calc.get_snapshot_param("NIFTY", SPAN_METRIC_PRICE_SCAN_RANGE) == 29.0


def test_h3_get_snapshot_param_cvf():
    snap = _snapshot({"NIFTY": {
        SPAN_METRIC_SCAN_RISK: 30.0,
        SPAN_METRIC_SHORT_OPTION_MIN: 16.0,
        SPAN_METRIC_CVF: 1.0,
    }})
    calc = SpanMarginCalculator(PositionTracker(), snap)
    assert calc.get_snapshot_param("NIFTY", SPAN_METRIC_CVF) == 1.0


def test_h4_get_snapshot_param_missing_symbol_raises():
    calc = SpanMarginCalculator(PositionTracker(), _snapshot({}))
    with pytest.raises(MissingRiskArray):
        calc.get_snapshot_param("UNKNOWN", SPAN_METRIC_SCAN_RISK)


def test_h5_get_snapshot_param_missing_metric_raises():
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0}})
    calc = SpanMarginCalculator(PositionTracker(), snap)
    with pytest.raises(MissingRiskMetric):
        calc.get_snapshot_param("NIFTY", SPAN_METRIC_CVF)


def _make_ra_tuple(first_val: float) -> tuple:
    """16-element RA tuple with first element set, rest zero."""
    return (first_val,) + (0.0,) * 15


def _contract_snapshot(
    risk_data=None,
    futures=None,
    option_contracts=None,
):
    """Build a SpanSnapshot with optional risk arrays, futures, and option contracts."""
    return SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="4.00",
        exchange="NSE",
        segment="FO",
        file_hash="test",
        is_settlement=False,
        risk_arrays={
            sym: SpanRiskArray(symbol=sym, risk_metrics=metrics)
            for sym, metrics in (risk_data or {}).items()
        },
        futures=futures or {},
        option_contracts=option_contracts or {},
        metadata={},
    )


# --------------------------------------------------------------------------- #
# I — Future contract RA routing (MM10.2-S1)
# --------------------------------------------------------------------------- #

def test_i1_lookup_future_scan_risk_exact_match():
    """_lookup_future_scan_risk returns correct value for exact expiry match."""
    fut_jul = SpanFutureContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), price=0.0, delta=0.0,
        time_to_expiry=0.0, risk_free_rate=0.0, price_scan_range=0.0,
        vol_scan_range=0.0, ra=_make_ra_tuple(2255.78),
    )
    snap = _contract_snapshot(futures={"NIFTY": (fut_jul,)})
    calc = SpanMarginCalculator(PositionTracker(), snap)
    result = calc._lookup_future_scan_risk("NIFTY", date(2026, 7, 28))
    assert result == 2255.78


def test_i2_lookup_future_scan_risk_expiry_miss():
    """_lookup_future_scan_risk returns None when expiry not found."""
    fut_jul = SpanFutureContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), price=0.0, delta=0.0,
        time_to_expiry=0.0, risk_free_rate=0.0, price_scan_range=0.0,
        vol_scan_range=0.0, ra=_make_ra_tuple(2255.78),
    )
    snap = _contract_snapshot(futures={"NIFTY": (fut_jul,)})
    calc = SpanMarginCalculator(PositionTracker(), snap)
    # expiry=Aug-2026 absent from snapshot
    assert calc._lookup_future_scan_risk("NIFTY", date(2026, 8, 25)) is None


def test_i3_per_expiry_scan_risk_differs():
    """Different expiries return different scan risk values."""
    fut_jun = SpanFutureContract(
        symbol="NIFTY", expiry=date(2026, 6, 30), price=0.0, delta=0.0,
        time_to_expiry=0.0, risk_free_rate=0.0, price_scan_range=0.0,
        vol_scan_range=0.0, ra=_make_ra_tuple(2244.36),
    )
    fut_jul = SpanFutureContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), price=0.0, delta=0.0,
        time_to_expiry=0.0, risk_free_rate=0.0, price_scan_range=0.0,
        vol_scan_range=0.0, ra=_make_ra_tuple(2255.78),
    )
    snap = _contract_snapshot(futures={"NIFTY": (fut_jun, fut_jul)})
    calc = SpanMarginCalculator(PositionTracker(), snap)
    jun_result = calc._lookup_future_scan_risk("NIFTY", date(2026, 6, 30))
    jul_result = calc._lookup_future_scan_risk("NIFTY", date(2026, 7, 28))
    assert jun_result == 2244.36
    assert jul_result == 2255.78
    assert jun_result != jul_result


def test_i4_future_uses_contract_level_ra():
    """get_used_margin uses contract-level RA for Future instrument."""
    pt = PositionTracker()
    inst = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(
        instrument=inst, side=PositionSide.LONG, quantity=10, avg_price=100.0,
    )
    fut_jun = SpanFutureContract(
        symbol="NIFTY", expiry=date(2026, 6, 30), price=0.0, delta=0.0,
        time_to_expiry=0.0, risk_free_rate=0.0, price_scan_range=0.0,
        vol_scan_range=0.0, ra=_make_ra_tuple(2244.36),
    )
    fut_jul = SpanFutureContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), price=0.0, delta=0.0,
        time_to_expiry=0.0, risk_free_rate=0.0, price_scan_range=0.0,
        vol_scan_range=0.0, ra=_make_ra_tuple(2255.78),
    )
    snap = _contract_snapshot(
        risk_data={"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}},
        futures={"NIFTY": (fut_jun, fut_jul)},
    )
    calc = SpanMarginCalculator(pt, snap)
    margin = calc.get_used_margin({"NIFTY25JUL": 24000.0})
    contract_margin = 10 * 65 * 2255.78
    symbol_margin = 10 * 65 * 2244.36
    assert margin == contract_margin
    assert margin != symbol_margin


def test_i5_future_contract_miss_falls_back_to_symbol():
    """Future expiry miss falls back to symbol-level scan risk."""
    pt = PositionTracker()
    inst = Future("NIFTY25JAN", underlying="NIFTY", expiry=date(2027, 1, 1), multiplier=65)
    pt._positions["NIFTY25JAN"] = Position(
        instrument=inst, side=PositionSide.LONG, quantity=10, avg_price=100.0,
    )
    fut_jul = SpanFutureContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), price=0.0, delta=0.0,
        time_to_expiry=0.0, risk_free_rate=0.0, price_scan_range=0.0,
        vol_scan_range=0.0, ra=_make_ra_tuple(2255.78),
    )
    snap = _contract_snapshot(
        risk_data={"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}},
        futures={"NIFTY": (fut_jul,)},
    )
    calc = SpanMarginCalculator(pt, snap)
    margin = calc.get_used_margin({"NIFTY25JAN": 24000.0})
    assert margin == 10 * 65 * 2244.36


def test_i6_equity_path_unchanged():
    """Equity position with no futures data still produces correct margin."""
    pt = _tracker_with(("RELIANCE", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"RELIANCE": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    calc = SpanMarginCalculator(pt, snap)
    margin = calc.get_used_margin({"RELIANCE": 250.0})
    assert margin == 300.0  # 10 * 1 * max(30, 16) = 300


# --------------------------------------------------------------------------- #
# J — Option contract RA routing (MM10.2-S2)
# --------------------------------------------------------------------------- #

def test_j1_lookup_option_scan_risk_exact_match():
    """_lookup_option_scan_risk returns correct value for exact match."""
    opt = SpanOptionContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), strike=23750.0, option_type="C",
        price=0.0, delta=0.0, implied_vol=0.0, ra=_make_ra_tuple(608.20),
    )
    snap = _contract_snapshot(
        risk_data={"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}},
        option_contracts={"NIFTY": (opt,)},
    )
    calc = SpanMarginCalculator(PositionTracker(), snap)
    result = calc._lookup_option_scan_risk("NIFTY", date(2026, 7, 28), 23750.0, "CE")
    assert result == 608.20


def test_j2_lookup_option_scan_risk_miss():
    """_lookup_option_scan_risk returns None for strike/expiry/type miss."""
    opt = SpanOptionContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), strike=23750.0, option_type="C",
        price=0.0, delta=0.0, implied_vol=0.0, ra=_make_ra_tuple(608.20),
    )
    snap = _contract_snapshot(
        risk_data={"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}},
        option_contracts={"NIFTY": (opt,)},
    )
    calc = SpanMarginCalculator(PositionTracker(), snap)
    assert calc._lookup_option_scan_risk("NIFTY", date(2026, 7, 28), 24000.0, "CE") is None


def test_j3_type_normalization_ce_matches_c():
    """'CE' (instrument model) matches 'C' (SPAN XML) in snapshot."""
    opt = SpanOptionContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), strike=23750.0, option_type="C",
        price=0.0, delta=0.0, implied_vol=0.0, ra=_make_ra_tuple(608.20),
    )
    snap = _contract_snapshot(
        risk_data={"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}},
        option_contracts={"NIFTY": (opt,)},
    )
    calc = SpanMarginCalculator(PositionTracker(), snap)
    result = calc._lookup_option_scan_risk("NIFTY", date(2026, 7, 28), 23750.0, "CE")
    assert result == 608.20


def test_j4_som_floor_applied():
    """SOM floor raised when SOM exceeds contract scan risk."""
    opt = SpanOptionContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), strike=23750.0, option_type="C",
        price=0.0, delta=0.0, implied_vol=0.0, ra=_make_ra_tuple(10.0),
    )
    snap = _contract_snapshot(
        risk_data={"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 50.0}},
        option_contracts={"NIFTY": (opt,)},
    )
    calc = SpanMarginCalculator(PositionTracker(), snap)
    result = calc._lookup_option_scan_risk("NIFTY", date(2026, 7, 28), 23750.0, "CE")
    assert result == 50.0


def test_j5_option_uses_contract_level_ra():
    """get_used_margin uses contract-level RA for Option instrument."""
    pt = PositionTracker()
    inst = Option(
        "NIFTY25JUL23750CE", underlying="NIFTY", expiry=date(2026, 7, 28),
        strike=23750.0, option_type=OptionType.CALL, lot_size=65,
    )
    pt._positions["NIFTY25JUL23750CE"] = Position(
        instrument=inst, side=PositionSide.LONG, quantity=10, avg_price=100.0,
    )
    opt = SpanOptionContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), strike=23750.0, option_type="C",
        price=0.0, delta=0.0, implied_vol=0.0, ra=_make_ra_tuple(608.20),
    )
    snap = _contract_snapshot(
        risk_data={"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}},
        option_contracts={"NIFTY": (opt,)},
    )
    calc = SpanMarginCalculator(pt, snap)
    margin = calc.get_used_margin({"NIFTY25JUL23750CE": 24000.0})
    contract_margin = 10 * 65 * 608.20
    symbol_margin = 10 * 65 * 2244.36
    assert margin == contract_margin
    assert margin != symbol_margin


def test_j6_option_contract_miss_falls_back_to_symbol():
    """Option strike miss falls back to symbol-level scan risk."""
    pt = PositionTracker()
    inst = Option(
        "NIFTY25JUL99999CE", underlying="NIFTY", expiry=date(2026, 7, 28),
        strike=99999.0, option_type=OptionType.CALL, lot_size=65,
    )
    pt._positions["NIFTY25JUL99999CE"] = Position(
        instrument=inst, side=PositionSide.LONG, quantity=10, avg_price=100.0,
    )
    opt = SpanOptionContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), strike=23750.0, option_type="C",
        price=0.0, delta=0.0, implied_vol=0.0, ra=_make_ra_tuple(608.20),
    )
    snap = _contract_snapshot(
        risk_data={"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}},
        option_contracts={"NIFTY": (opt,)},
    )
    calc = SpanMarginCalculator(pt, snap)
    margin = calc.get_used_margin({"NIFTY25JUL99999CE": 24000.0})
    assert margin == 10 * 65 * 2244.36


# --------------------------------------------------------------------------- #
# K — Backward compatibility (MM10.2-S2)
# --------------------------------------------------------------------------- #

def test_k1_equity_portfolio_unchanged():
    """Three equity positions produce identical results to pre-MM10.2."""
    pt = _tracker_with(
        ("NIFTY", 10, 100.0, PositionSide.LONG),
        ("BANKNIFTY", 5, 200.0, PositionSide.SHORT),
    )
    snap = _snapshot({
        "NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0},
        "BANKNIFTY": {SPAN_METRIC_SCAN_RISK: 72.0, SPAN_METRIC_SHORT_OPTION_MIN: 40.0},
    })
    calc = SpanMarginCalculator(pt, snap)
    prices = {"NIFTY": 200.0, "BANKNIFTY": 400.0}
    margin = calc.get_used_margin(prices)
    assert margin == 660.0  # same as test_multi_position_used_margin


def test_k2_incremental_margin_remains_symbol_level():
    """get_incremental_margin still uses symbol-level path (documented asymmetry)."""
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    calc = SpanMarginCalculator(PositionTracker(), snap)
    result = calc.get_incremental_margin("NIFTY", 10, 200.0, lot_size=65)
    assert result == 10 * 65 * 30.0  # 19500


def test_k3_mixed_portfolio_equity_future_option():
    """Equity + Future + Option in same get_used_margin call."""
    pt = PositionTracker()
    eq = Equity("RELIANCE")
    object.__setattr__(eq, "multiplier", 1.0)
    pt._positions["RELIANCE"] = Position(
        instrument=eq, side=PositionSide.LONG, quantity=100, avg_price=200.0)

    fut = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(
        instrument=fut, side=PositionSide.LONG, quantity=10, avg_price=24000.0)

    opt = Option(
        "NIFTY25JUL23750CE", underlying="NIFTY", expiry=date(2026, 7, 28),
        strike=23750.0, option_type=OptionType.CALL, lot_size=65,
    )
    pt._positions["NIFTY25JUL23750CE"] = Position(
        instrument=opt, side=PositionSide.LONG, quantity=10, avg_price=100.0)

    fut_jul = SpanFutureContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), price=0.0, delta=0.0,
        time_to_expiry=0.0, risk_free_rate=0.0, price_scan_range=0.0,
        vol_scan_range=0.0, ra=_make_ra_tuple(2255.78),
    )
    opt_ce = SpanOptionContract(
        symbol="NIFTY", expiry=date(2026, 7, 28), strike=23750.0, option_type="C",
        price=0.0, delta=0.0, implied_vol=0.0, ra=_make_ra_tuple(608.20),
    )
    snap = _contract_snapshot(
        risk_data={
            "NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0},
            "BANKNIFTY": {SPAN_METRIC_SCAN_RISK: 5513.40, SPAN_METRIC_SHORT_OPTION_MIN: 0.0},
            "RELIANCE": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0},
        },
        futures={"NIFTY": (fut_jul,)},
        option_contracts={"NIFTY": (opt_ce,)},
    )
    calc = SpanMarginCalculator(pt, snap)
    prices = {"RELIANCE": 250.0, "NIFTY25JUL": 24000.0, "NIFTY25JUL23750CE": 24000.0}
    margin = calc.get_used_margin(prices)
    eq_margin = 100 * 1 * 30.0
    fut_margin = 10 * 65 * 2255.78
    opt_margin = 10 * 65 * 608.20
    assert margin == pytest.approx(eq_margin + fut_margin + opt_margin, abs=0.01)
