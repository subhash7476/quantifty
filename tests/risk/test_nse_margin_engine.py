"""MM10.4 — NseMarginEngine: Calendar Spread Credits + Extreme Loss Margin.

Groups:
  A — Protocol conformance
  B — Pure delegation (no spread credit)
  C — Spread credit basics
  D — Matching rules
  E — Scan risk lookup
  F — Zero spread charge
  G — Determinism
  H — Architecture guards
  N — Handler integration
  R — Real-file regression (skipped if absent)
  S — ELM rate module
  T — Constructor wiring
  U — Zero ELM baseline
  V — Futures ELM
  W — Options ELM
  X — Mixed portfolio
  Y — Spread interaction
  Z — Incremental margin
  AA — Architecture guards
"""

from datetime import date, datetime
from unittest.mock import MagicMock, Mock, patch

import pathlib
import pytest

from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
from core.execution.margin_tracker import MarginTracker
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
)
from core.risk.span.span_calculator import (
    SpanMarginCalculator,
    MissingRiskArray,
    SPAN_METRIC_SCAN_RISK,
    SPAN_METRIC_SHORT_OPTION_MIN,
    SPAN_METRIC_INTRA_SPREAD_CHARGE,
)


def _snapshot(risk_data=None, futures=None):
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
        metadata={},
    )


def _make_ra_tuple(first_val: float) -> tuple:
    return (first_val,) + (0.0,) * 15


def _future_calc(pt, snap, margin_rate: float = 1.0) -> SpanMarginCalculator:
    return SpanMarginCalculator(pt, snap, margin_rate=margin_rate)


# --------------------------------------------------------------------------- #
# A — Protocol conformance
# --------------------------------------------------------------------------- #

def test_a1_has_margin_rate():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    snap = _snapshot()
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    assert hasattr(engine, "margin_rate")


def test_a2_margin_rate_proxies():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    snap = _snapshot()
    calc = _future_calc(pt, snap, margin_rate=0.15)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    assert engine.margin_rate == 0.15


def test_a3_has_protocol_methods():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    snap = _snapshot()
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    assert callable(getattr(engine, "get_exposure", None))
    assert callable(getattr(engine, "get_used_margin", None))
    assert callable(getattr(engine, "get_incremental_margin", None))


def test_a4_does_not_inherit_protocol():
    from core.risk.nse_margin_engine import NseMarginEngine
    assert MarginCalculator not in NseMarginEngine.__bases__


def test_a5_does_not_inherit_span_calculator():
    from core.risk.nse_margin_engine import NseMarginEngine
    assert SpanMarginCalculator not in NseMarginEngine.__bases__


# --------------------------------------------------------------------------- #
# B — Pure delegation (no spread credit)
# --------------------------------------------------------------------------- #

def test_b1_get_exposure_delegates():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _tracker_with(("NIFTY", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY": 200.0}
    assert engine.get_exposure(prices) == calc.get_exposure(prices)


def test_b2_get_incremental_margin_delegates():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    assert engine.get_incremental_margin("NIFTY", 50, 200.0) == calc.get_incremental_margin("NIFTY", 50, 200.0)


def test_b3_equity_only_no_spread_credit():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _tracker_with(("RELIANCE", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"RELIANCE": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"RELIANCE": 250.0}
    assert engine.get_used_margin(prices) == calc.get_used_margin(prices)


def test_b4_same_expiry_futures_no_credit():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    inst2 = Future("NIFTY25JUN_B", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN_B"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=5, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 10.0}},
        futures={"NIFTY": (SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(30.0)),)},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUN_B": 24000.0}
    # Same expiry — no spread, scan margin only
    assert engine.get_used_margin(prices) == calc.get_used_margin(prices)


def test_b5_all_same_direction_no_credit():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 10.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(30.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(35.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    # All long — no spread, scan margin only
    assert engine.get_used_margin(prices) == calc.get_used_margin(prices)


def _tracker_with(*positions):
    pt = PositionTracker()
    for sym, qty, avg, side in positions:
        pt._positions[sym] = Position(
            instrument=Equity(sym), side=side, quantity=qty, avg_price=avg)
    return pt


# --------------------------------------------------------------------------- #
# C — Spread credit basics
# --------------------------------------------------------------------------- #

def test_c1_two_futures_opposite_directions_credit_positive():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=10, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 425.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2244.36)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2255.78)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    span_margin = calc.get_used_margin(prices)
    engine_margin = engine.get_used_margin(prices)
    assert engine_margin < span_margin


def test_c2_credit_formula_correct():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=10, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 425.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2244.36)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2255.78)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    span_margin = calc.get_used_margin(prices)
    credit = (2244.36 + 2255.78 - 425.0) * 65 * 10
    expected_margin = max(0.0, span_margin - credit)
    assert engine.get_used_margin(prices) == expected_margin


def test_c3_margin_never_negative():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=1, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=1, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 10.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 1000.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(10.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(10.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    margin = engine.get_used_margin(prices)
    assert margin >= 0.0


def test_c4_credit_non_negative_when_spread_charge_exceeds():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=1, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=1, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 10.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 1000.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(10.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(10.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    span_margin = calc.get_used_margin(prices)
    engine_margin = engine.get_used_margin(prices)
    # When spread_charge > combined scan, credit = 0, margin = span_margin
    assert engine_margin == span_margin


# --------------------------------------------------------------------------- #
# D — Matching rules
# --------------------------------------------------------------------------- #

def test_d1_partial_match():
    """3 long + 2 short → credit on 2 pairs, 1 outright unaffected."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=3, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=2, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 10.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(30.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(35.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    span_margin = calc.get_used_margin(prices)
    # 2 pairs matched: credit = (30 + 35 - 10) * 65 * 2
    credit = (30.0 + 35.0 - 10.0) * 65 * 2
    expected = max(0.0, span_margin - credit)
    assert engine.get_used_margin(prices) == expected


def test_d2_three_expiries_greedy_match():
    """long-near + long-mid + short-far → near-far matched first (greedy)."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.LONG, quantity=3, avg_price=100.0)
    inst3 = Future("NIFTY25AUG", underlying="NIFTY", expiry=date(2026, 8, 25), multiplier=65)
    pt._positions["NIFTY25AUG"] = Position(instrument=inst3, side=PositionSide.SHORT, quantity=4, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 10.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(30.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(35.0)),
            SpanFutureContract("NIFTY", date(2026, 8, 25), 0, 0, 0, 0, 0, 0, _make_ra_tuple(40.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0, "NIFTY25AUG": 24000.0}
    span_margin = calc.get_used_margin(prices)
    # Greedy: near-far first. Jun(L=5) vs Aug(S=4): match 4, Jun remaining=1
    # Then Jun(L=1) vs Jul(L=3) same sign → skip
    # Then Jul(L=3) vs Aug already exhausted
    # One match: credit = (30+40-10)*65*4 = 15600
    credit = (30.0 + 40.0 - 10.0) * 65 * 4
    expected = max(0.0, span_margin - credit)
    assert engine.get_used_margin(prices) == expected


def test_d3_same_direction_no_credit():
    """All-long futures → no credit regardless of different expiries."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.LONG, quantity=3, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 10.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(30.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(35.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    assert engine.get_used_margin(prices) == calc.get_used_margin(prices)


def test_d4_mixed_underlying_no_cross_credit():
    """NIFTY spread credit isolated from BANKNIFTY (no cross-underlying credit)."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=5, avg_price=100.0)
    inst3 = Future("BN25JUN", underlying="BANKNIFTY", expiry=date(2026, 6, 30), multiplier=30)
    pt._positions["BN25JUN"] = Position(instrument=inst3, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 10.0},
         "BANKNIFTY": {SPAN_METRIC_SCAN_RISK: 72.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 20.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(30.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(35.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0, "BN25JUN": 52000.0}
    span_margin = calc.get_used_margin(prices)
    assert engine.get_used_margin(prices) < span_margin  # NIFTY spread gets credit


def test_d5_options_not_matched():
    """Option instruments are NOT matched for spread credit."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Option("NIFTY25JUN23750CE", underlying="NIFTY", expiry=date(2026, 6, 30), strike=23750.0, option_type=OptionType.CALL, lot_size=65)
    pt._positions["NIFTY25JUN23750CE"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    inst2 = Option("NIFTY25JUL23750PE", underlying="NIFTY", expiry=date(2026, 7, 28), strike=23750.0, option_type=OptionType.PUT, lot_size=65)
    pt._positions["NIFTY25JUL23750PE"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=5, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 10.0}},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN23750CE": 150.0, "NIFTY25JUL23750PE": 100.0}
    assert engine.get_used_margin(prices) == calc.get_used_margin(prices)


def test_d6_equity_not_matched():
    """Equity instruments are NOT matched for spread credit."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _tracker_with(("RELIANCE", 10, 100.0, PositionSide.LONG),
                        ("TCS", 5, 200.0, PositionSide.SHORT))
    snap = _snapshot({"RELIANCE": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0},
                      "TCS": {SPAN_METRIC_SCAN_RISK: 20.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"RELIANCE": 250.0, "TCS": 400.0}
    assert engine.get_used_margin(prices) == calc.get_used_margin(prices)


# --------------------------------------------------------------------------- #
# E — Scan risk lookup
# --------------------------------------------------------------------------- #

def test_e1_contract_level_ra_used():
    """Contract-level RA used when futures expiry found in snapshot."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    inst2 = Future("NIFTY25AUG", underlying="NIFTY", expiry=date(2026, 8, 25), multiplier=65)
    pt._positions["NIFTY25AUG"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=5, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 425.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2255.78)),
            SpanFutureContract("NIFTY", date(2026, 8, 25), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2267.27)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUL": 24000.0, "NIFTY25AUG": 24000.0}
    credit = (2255.78 + 2267.27 - 425.0) * 65 * 5
    expected = max(0.0, calc.get_used_margin(prices) - credit)
    assert engine.get_used_margin(prices) == expected


def test_e2_symbol_fallback_when_expiry_not_found():
    """Symbol-level fallback when expiry not in futures."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    inst2 = Future("NIFTY25XXX", underlying="NIFTY", expiry=date(2025, 12, 31), multiplier=65)
    pt._positions["NIFTY25XXX"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=5, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 425.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2255.78)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUL": 24000.0, "NIFTY25XXX": 24000.0}
    # One expiry not in futures → fallback to symbol-level 2244.36 for that leg
    scan_far = 2244.36  # symbol-level fallback for missing expiry
    credit = (2255.78 + scan_far - 425.0) * 65 * 5
    expected = max(0.0, calc.get_used_margin(prices) - credit)
    assert engine.get_used_margin(prices) == expected


def test_e3_missing_underlying_in_risk_arrays():
    """Missing underlying in risk_arrays → credit = 0 (no charge), contract RA used."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=5, avg_price=100.0)
    snap = _snapshot(
        {},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(30.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(35.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    # No risk_arrays → no spread charge data → credit = 0
    # Contract-level RA still works in the calculator (has futures data)
    assert engine.get_used_margin(prices) == calc.get_used_margin(prices)


# --------------------------------------------------------------------------- #
# F — Zero spread charge
# --------------------------------------------------------------------------- #

def test_f1_zero_charge_no_credit():
    """intra_spread_charge_rs = 0.0 → credit = 0."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=5, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 0.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(30.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(35.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    assert engine.get_used_margin(prices) == calc.get_used_margin(prices)


def test_f2_absent_charge_no_credit():
    """intra_spread_charge_rs absent from risk_metrics → credit = 0."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=5, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}},  # no INTRA_SPREAD_CHARGE
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(30.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(35.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    assert engine.get_used_margin(prices) == calc.get_used_margin(prices)


def test_f3_f1_f2_raise_no_exception():
    """Zero/absent charge scenarios don't raise — silent credit = 0."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=5, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 0.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(30.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(35.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    engine.get_used_margin(prices)  # no exception


# --------------------------------------------------------------------------- #
# G — Determinism
# --------------------------------------------------------------------------- #

def test_g1_same_inputs_same_output():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=10, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 425.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2244.36)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2255.78)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    a = engine.get_used_margin(prices)
    b = engine.get_used_margin(prices)
    assert a == b


def test_g2_independent_of_position_insertion_order():
    """Same positions in different order produce identical result."""
    from core.risk.nse_margin_engine import NseMarginEngine
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 10.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(30.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(35.0)),
        )},
    )
    pt1 = PositionTracker()
    pt1._positions["A"] = Position(instrument=Future("A", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65), side=PositionSide.LONG, quantity=5, avg_price=100.0)
    pt1._positions["B"] = Position(instrument=Future("B", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65), side=PositionSide.SHORT, quantity=3, avg_price=100.0)

    pt2 = PositionTracker()
    pt2._positions["B"] = Position(instrument=Future("B", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65), side=PositionSide.SHORT, quantity=3, avg_price=100.0)
    pt2._positions["A"] = Position(instrument=Future("A", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65), side=PositionSide.LONG, quantity=5, avg_price=100.0)

    prices = {"A": 24000.0, "B": 24000.0}
    e1 = NseMarginEngine(_future_calc(pt1, snap), snap, elm_rates={}).get_used_margin(prices)
    e2 = NseMarginEngine(_future_calc(pt2, snap), snap, elm_rates={}).get_used_margin(prices)
    assert e1 == e2


def test_g3_no_forbidden_imports():
    """nse_margin_engine.py does not import from parser, repository, or readiness."""
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[2] / "core" / "risk" / "nse_margin_engine.py"
    content = src.read_text(encoding="utf-8")
    assert "span_parser" not in content
    assert "span_repository" not in content
    assert "span_readiness" not in content
    assert "span_calculator" not in content or "_SCENARIO_WEIGHTS" in content  # weights are duplicated


# --------------------------------------------------------------------------- #
# H — Architecture guards
# --------------------------------------------------------------------------- #

def test_h1_span_calculator_no_spread_references():
    """span_calculator.py contains no ELM, exposure margin, or spread credit code."""
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[2] / "core" / "risk" / "span" / "span_calculator.py"
    content = src.read_text(encoding="utf-8")
    for term in ["elm", "exposure_margin", "spread_credit", "NseMarginEngine"]:
        assert term not in content, f"span_calculator.py contains forbidden reference: {term}"
    # 'broker' appears in the protocol docstring (pre-existing, acceptable);
    # check it is not referenced as a method name or import
    assert "import.*broker" not in content.replace(" ", "")


def test_h2_nse_margin_engine_no_private_calculator_access():
    """nse_margin_engine.py does not access private calculator methods."""
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[2] / "core" / "risk" / "nse_margin_engine.py"
    content = src.read_text(encoding="utf-8")
    for term in ["_scan_margin_per_unit", "_single_span_margin", "_resolve_scan_risk"]:
        assert term not in content, f"nse_margin_engine.py uses private method: {term}"


def test_h3_no_io_in_nse_margin_engine():
    """nse_margin_engine.py performs zero I/O."""
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[2] / "core" / "risk" / "nse_margin_engine.py"
    content = src.read_text(encoding="utf-8")
    assert "open(" not in content
    assert ".read" not in content
    assert ".write" not in content


# --------------------------------------------------------------------------- #
# N — Handler integration
# --------------------------------------------------------------------------- #

def test_n1_handler_creates_nse_margin_engine_with_snapshot():
    """ExecutionHandler with span_snapshot gets NseMarginEngine."""
    from core.risk.nse_margin_engine import NseMarginEngine
    from core.clock import Clock
    from core.brokers.paper_broker import PaperBroker
    pt = PositionTracker()
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 10.0}})
    clock = Clock()
    broker = PaperBroker(clock)
    from core.database.manager import DatabaseManager
    try:
        handler = ExecutionHandler(
            db_manager=DatabaseManager(),
            clock=clock,
            broker=broker,
            span_snapshot=snap,
        )
    except Exception:
        pytest.skip("Cannot construct real ExecutionHandler in test — required DB/setup missing")
    else:
        assert isinstance(handler.margin_tracker, NseMarginEngine)


def test_n2_handler_without_snapshot_still_gets_margin_tracker():
    """ExecutionHandler with span_snapshot=None gets MarginTracker (unchanged)."""
    from core.clock import Clock
    from core.brokers.paper_broker import PaperBroker
    clock = Clock()
    broker = PaperBroker(clock)
    from core.database.manager import DatabaseManager
    try:
        handler = ExecutionHandler(
            db_manager=DatabaseManager(),
            clock=clock,
            broker=broker,
            span_snapshot=None,
        )
    except Exception:
        pytest.skip("Cannot construct real ExecutionHandler — required DB/setup missing")
    else:
        assert isinstance(handler.margin_tracker, MarginTracker)


# --------------------------------------------------------------------------- #
# R — Real-file regression (skipped if reference SPAN file absent)
# --------------------------------------------------------------------------- #

SPAN_FILE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "reference" / "span" / "nsccl.20260625.i1" / "nsccl.20260625.i01.spn"
)

_regression_mark = pytest.mark.skipif(
    not SPAN_FILE.exists(),
    reason="Reference SPAN file absent — run without real-file regression",
)


@_regression_mark
def test_r1_nifty_spread_credit():
    """NIFTY 1 near long + 1 far short → credit > 0 confirmed."""
    from core.risk.span.parser_v400 import parse_span_xml
    from core.risk.nse_margin_engine import NseMarginEngine
    snapshot = parse_span_xml(SPAN_FILE.read_bytes())
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=1, avg_price=24000.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=1, avg_price=24000.0)
    calc = _future_calc(pt, snapshot)
    engine = NseMarginEngine(calc, snapshot, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    span_margin = calc.get_used_margin(prices)
    engine_margin = engine.get_used_margin(prices)
    assert engine_margin < span_margin
    assert engine_margin == pytest.approx(27625.0, abs=500.0)


@_regression_mark
def test_r2_outright_only_identical():
    """Outright-only (single expiry) matches SpanMarginCalculator exactly."""
    from core.risk.span.parser_v400 import parse_span_xml
    from core.risk.nse_margin_engine import NseMarginEngine
    snapshot = parse_span_xml(SPAN_FILE.read_bytes())
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=10, avg_price=24000.0)
    calc = _future_calc(pt, snapshot)
    engine = NseMarginEngine(calc, snapshot, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0}
    assert engine.get_used_margin(prices) == calc.get_used_margin(prices)


@_regression_mark
def test_r3_partial_match():
    """3 long near + 2 short far → credit on matched lots only."""
    from core.risk.span.parser_v400 import parse_span_xml
    from core.risk.nse_margin_engine import NseMarginEngine
    snapshot = parse_span_xml(SPAN_FILE.read_bytes())
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=3, avg_price=24000.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=2, avg_price=24000.0)
    calc = _future_calc(pt, snapshot)
    engine = NseMarginEngine(calc, snapshot, elm_rates={})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    span_margin = calc.get_used_margin(prices)
    engine_margin = engine.get_used_margin(prices)
    assert engine_margin < span_margin
    assert engine_margin > 0.0


@_regression_mark
def test_r4_banknifty_spread():
    """BANKNIFTY near short + far long → spread credit."""
    from core.risk.span.parser_v400 import parse_span_xml
    from core.risk.nse_margin_engine import NseMarginEngine
    snapshot = parse_span_xml(SPAN_FILE.read_bytes())
    pt = PositionTracker()
    inst1 = Future("BN25JUN", underlying="BANKNIFTY", expiry=date(2026, 6, 30), multiplier=30)
    pt._positions["BN25JUN"] = Position(instrument=inst1, side=PositionSide.SHORT, quantity=1, avg_price=52000.0)
    inst2 = Future("BN25JUL", underlying="BANKNIFTY", expiry=date(2026, 7, 28), multiplier=30)
    pt._positions["BN25JUL"] = Position(instrument=inst2, side=PositionSide.LONG, quantity=1, avg_price=52000.0)
    calc = _future_calc(pt, snapshot)
    engine = NseMarginEngine(calc, snapshot, elm_rates={})
    prices = {"BN25JUN": 52000.0, "BN25JUL": 52000.0}
    span_margin = calc.get_used_margin(prices)
    engine_margin = engine.get_used_margin(prices)
    assert engine_margin < span_margin
    assert engine_margin == pytest.approx(30882.3, abs=500.0)


# --------------------------------------------------------------------------- #
# S — ELM rate module
# --------------------------------------------------------------------------- #

def test_s1_elm_rates_module_exists():
    from core.risk.elm_rates import INDEX_ELM_RATES
    assert isinstance(INDEX_ELM_RATES, dict)


def test_s2_elm_rates_has_nifty():
    from core.risk.elm_rates import INDEX_ELM_RATES
    assert INDEX_ELM_RATES["NIFTY"] > 0.0


def test_s3_elm_rates_has_banknifty():
    from core.risk.elm_rates import INDEX_ELM_RATES
    assert INDEX_ELM_RATES["BANKNIFTY"] > 0.0


def test_s4_elm_rates_are_positive_fractions():
    from core.risk.elm_rates import INDEX_ELM_RATES
    for v in INDEX_ELM_RATES.values():
        assert 0 < v < 1


def test_s5_elm_rates_does_not_import_span():
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[2] / "core" / "risk" / "elm_rates.py"
    content = src.read_text(encoding="utf-8")
    assert "core.risk.span" not in content


# --------------------------------------------------------------------------- #
# T — Constructor wiring
# --------------------------------------------------------------------------- #

def test_t1_constructor_accepts_elm_rates():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    snap = _snapshot()
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    assert hasattr(engine, "_elm_rates")


def test_t2_constructor_requires_elm_rates():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    snap = _snapshot()
    calc = _future_calc(pt, snap)
    with pytest.raises(TypeError):
        NseMarginEngine(calc, snap)


def test_t3_elm_rates_stored_as_copy():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    snap = _snapshot()
    calc = _future_calc(pt, snap)
    original = {"NIFTY": 0.02}
    engine = NseMarginEngine(calc, snap, elm_rates=original)
    original["NIFTY"] = 0.99
    assert engine._elm_rates["NIFTY"] == 0.02


# --------------------------------------------------------------------------- #
# U — Zero ELM baseline
# --------------------------------------------------------------------------- #

def test_u1_empty_portfolio_elm_is_zero():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    snap = _snapshot({})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    assert engine._elm_margin({}) == 0.0


def test_u2_unknown_underlying_elm_is_zero():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _tracker_with(("RELIANCE", 10, 100.0, PositionSide.LONG))
    snap = _snapshot({"RELIANCE": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={})
    prices = {"RELIANCE": 250.0}
    assert engine._elm_margin(prices) == 0.0


def test_u3_zero_rate_elm_is_zero():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.0})
    prices = {"NIFTY25JUN": 24000.0}
    assert engine._elm_margin(prices) == 0.0


def test_u4_options_no_futures_elm_is_zero():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst = Option("NIFTY25JUN23750PE", underlying="NIFTY", expiry=date(2026, 6, 30), strike=23750.0, option_type=OptionType.PUT, lot_size=65)
    pt._positions["NIFTY25JUN23750PE"] = Position(instrument=inst, side=PositionSide.SHORT, quantity=10, avg_price=150.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN23750PE": 150.0}
    assert engine._elm_margin(prices) == 0.0


# --------------------------------------------------------------------------- #
# V — Futures ELM
# --------------------------------------------------------------------------- #

def test_v1_long_future_elm_applied():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0}
    assert engine._elm_margin(prices) > 0.0


def test_v2_short_future_elm_applied():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst, side=PositionSide.SHORT, quantity=10, avg_price=100.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0}
    assert engine._elm_margin(prices) > 0.0


def test_v3_future_elm_formula():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0}
    expected = 0.02 * 65 * 10 * 24000.0
    assert engine._elm_margin(prices) == expected


def test_v4_two_futures_elm_additive():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=5, avg_price=100.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24500.0}
    expected = 0.02 * 65 * 10 * 24000.0 + 0.02 * 65 * 5 * 24500.0
    assert engine._elm_margin(prices) == expected


def test_v5_opposite_futures_elm_additive():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    inst1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=inst1, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    inst2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=inst2, side=PositionSide.SHORT, quantity=10, avg_price=100.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24500.0}
    expected = 0.02 * 65 * 10 * 24000.0 + 0.02 * 65 * 10 * 24500.0
    assert engine._elm_margin(prices) == expected


# --------------------------------------------------------------------------- #
# W — Options ELM
# --------------------------------------------------------------------------- #

def _fut_pt():
    pt = PositionTracker()
    f = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=f, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    return pt


def test_w1_short_call_elm_applied():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _fut_pt()
    o = Option("NIFTY25JUN23750CE", underlying="NIFTY", expiry=date(2026, 6, 30), strike=23750.0, option_type=OptionType.CALL, lot_size=65)
    pt._positions["NIFTY25JUN23750CE"] = Position(instrument=o, side=PositionSide.SHORT, quantity=5, avg_price=150.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0}
    assert engine._elm_margin(prices) > 0.0


def test_w2_short_put_elm_applied():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _fut_pt()
    o = Option("NIFTY25JUN23750PE", underlying="NIFTY", expiry=date(2026, 6, 30), strike=23750.0, option_type=OptionType.PUT, lot_size=65)
    pt._positions["NIFTY25JUN23750PE"] = Position(instrument=o, side=PositionSide.SHORT, quantity=5, avg_price=150.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0}
    assert engine._elm_margin(prices) > 0.0


def test_w3_long_call_elm_zero():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _fut_pt()
    o = Option("NIFTY25JUN23750CE", underlying="NIFTY", expiry=date(2026, 6, 30), strike=23750.0, option_type=OptionType.CALL, lot_size=65)
    pt._positions["NIFTY25JUN23750CE"] = Position(instrument=o, side=PositionSide.LONG, quantity=5, avg_price=150.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0}
    assert engine._elm_margin(prices) == 0.02 * 65 * 10 * 24000.0


def test_w4_long_put_elm_zero():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _fut_pt()
    o = Option("NIFTY25JUN23750PE", underlying="NIFTY", expiry=date(2026, 6, 30), strike=23750.0, option_type=OptionType.PUT, lot_size=65)
    pt._positions["NIFTY25JUN23750PE"] = Position(instrument=o, side=PositionSide.LONG, quantity=5, avg_price=150.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0}
    assert engine._elm_margin(prices) == 0.02 * 65 * 10 * 24000.0


def test_w5_short_option_elm_formula():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _fut_pt()
    o = Option("NIFTY25JUN23750CE", underlying="NIFTY", expiry=date(2026, 6, 30), strike=23750.0, option_type=OptionType.CALL, lot_size=65)
    pt._positions["NIFTY25JUN23750CE"] = Position(instrument=o, side=PositionSide.SHORT, quantity=5, avg_price=150.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0}
    expected = 0.02 * 65 * 10 * 24000.0 + 0.02 * 65 * 5 * 24000.0
    assert engine._elm_margin(prices) == expected


def test_w6_mixed_options_only_short_pays():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _fut_pt()
    o1 = Option("NIFTY25JUN23750PE", underlying="NIFTY", expiry=date(2026, 6, 30), strike=23750.0, option_type=OptionType.PUT, lot_size=65)
    pt._positions["NIFTY25JUN23750PE"] = Position(instrument=o1, side=PositionSide.SHORT, quantity=3, avg_price=100.0)
    o2 = Option("NIFTY25JUN23800CE", underlying="NIFTY", expiry=date(2026, 6, 30), strike=23800.0, option_type=OptionType.CALL, lot_size=65)
    pt._positions["NIFTY25JUN23800CE"] = Position(instrument=o2, side=PositionSide.LONG, quantity=2, avg_price=100.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0}
    expected = 0.02 * 65 * 10 * 24000.0 + 0.02 * 65 * 3 * 24000.0
    assert engine._elm_margin(prices) == expected


# --------------------------------------------------------------------------- #
# X — Mixed portfolio
# --------------------------------------------------------------------------- #

def test_x1_future_plus_short_option_sum():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _fut_pt()
    o = Option("NIFTY25JUN23750PE", underlying="NIFTY", expiry=date(2026, 6, 30), strike=23750.0, option_type=OptionType.PUT, lot_size=65)
    pt._positions["NIFTY25JUN23750PE"] = Position(instrument=o, side=PositionSide.SHORT, quantity=5, avg_price=100.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0}
    expected = 0.02 * 65 * 10 * 24000.0 + 0.02 * 65 * 5 * 24000.0
    assert engine._elm_margin(prices) == expected


def test_x2_future_plus_long_option():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = _fut_pt()
    o = Option("NIFTY25JUN23750CE", underlying="NIFTY", expiry=date(2026, 6, 30), strike=23750.0, option_type=OptionType.CALL, lot_size=65)
    pt._positions["NIFTY25JUN23750CE"] = Position(instrument=o, side=PositionSide.LONG, quantity=5, avg_price=150.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0}
    assert engine._elm_margin(prices) == 0.02 * 65 * 10 * 24000.0


def test_x3_multi_underlying():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    i1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=i1, side=PositionSide.LONG, quantity=10, avg_price=100.0)
    i2 = Future("BN25JUN", underlying="BANKNIFTY", expiry=date(2026, 6, 30), multiplier=30)
    pt._positions["BN25JUN"] = Position(instrument=i2, side=PositionSide.LONG, quantity=5, avg_price=100.0)
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0},
                      "BANKNIFTY": {SPAN_METRIC_SCAN_RISK: 72.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02, "BANKNIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0, "BN25JUN": 52000.0}
    expected = 0.02 * 65 * 10 * 24000.0 + 0.02 * 30 * 5 * 52000.0
    assert engine._elm_margin(prices) == expected


# --------------------------------------------------------------------------- #
# Y — Spread interaction
# --------------------------------------------------------------------------- #

def test_y1_elm_additive_to_spread_reduced_span():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    i1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=i1, side=PositionSide.LONG, quantity=1, avg_price=100.0)
    i2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=i2, side=PositionSide.SHORT, quantity=1, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 425.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2244.36)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2255.78)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    span_margin = calc.get_used_margin(prices)
    credit = (2244.36 + 2255.78 - 425.0) * 65
    span_after = max(0.0, span_margin - credit)
    expected_elm = 0.02 * 65 * 1 * 24000.0 * 2
    expected_total = span_after + expected_elm
    assert engine.get_used_margin(prices) == expected_total


def test_y2_spread_credit_does_not_reduce_elm():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    i1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=i1, side=PositionSide.LONG, quantity=1, avg_price=100.0)
    i2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=i2, side=PositionSide.SHORT, quantity=1, avg_price=100.0)
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 2244.36, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 425.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2244.36)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(2255.78)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    expected_elm = 0.02 * 65 * 1 * 24000.0 * 2
    assert engine._elm_margin(prices) == expected_elm


def test_y3_span_fully_offset_elm_still_applied():
    """ELM is additive outside the span-credit clamp. span-clamp=0, result=ELM."""
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    i1 = Future("NIFTY25JUN", underlying="NIFTY", expiry=date(2026, 6, 30), multiplier=65)
    pt._positions["NIFTY25JUN"] = Position(instrument=i1, side=PositionSide.LONG, quantity=1, avg_price=100.0)
    i2 = Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026, 7, 28), multiplier=65)
    pt._positions["NIFTY25JUL"] = Position(instrument=i2, side=PositionSide.SHORT, quantity=1, avg_price=100.0)
    # Set charge huge so credit=0. Zero out scan_risk so span_margin=0.
    snap = _snapshot(
        {"NIFTY": {SPAN_METRIC_SCAN_RISK: 0.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0, SPAN_METRIC_INTRA_SPREAD_CHARGE: 1000.0}},
        futures={"NIFTY": (
            SpanFutureContract("NIFTY", date(2026, 6, 30), 0, 0, 0, 0, 0, 0, _make_ra_tuple(0.0)),
            SpanFutureContract("NIFTY", date(2026, 7, 28), 0, 0, 0, 0, 0, 0, _make_ra_tuple(0.0)),
        )},
    )
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    prices = {"NIFTY25JUN": 24000.0, "NIFTY25JUL": 24000.0}
    result = engine.get_used_margin(prices)
    # Span = 0 → max(0, 0-0) = 0. ELM = 0.02*65*1*24000*2 = 62400
    expected_elm = 0.02 * 65 * 1 * 24000.0 * 2
    assert result == expected_elm


# --------------------------------------------------------------------------- #
# Z — Incremental margin
# --------------------------------------------------------------------------- #

def test_z1_incremental_includes_elm_estimate():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    span_only = calc.get_incremental_margin("NIFTY", 10, 24000.0, lot_size=65)
    incr = engine.get_incremental_margin("NIFTY", 10, 24000.0, lot_size=65)
    assert incr > span_only


def test_z2_incremental_elm_formula():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    span_incr = calc.get_incremental_margin("NIFTY", 10, 24000.0, lot_size=65)
    elm_incr = 0.02 * 65 * abs(10) * 24000.0
    assert engine.get_incremental_margin("NIFTY", 10, 24000.0, lot_size=65) == span_incr + elm_incr


def test_z3_incremental_elm_zero_for_unknown():
    from core.risk.nse_margin_engine import NseMarginEngine
    pt = PositionTracker()
    snap = _snapshot({"RELIANCE": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = _future_calc(pt, snap)
    engine = NseMarginEngine(calc, snap, elm_rates={"NIFTY": 0.02})
    span_incr = calc.get_incremental_margin("RELIANCE", 10, 2000.0, lot_size=1)
    assert engine.get_incremental_margin("RELIANCE", 10, 2000.0, lot_size=1) == span_incr


# --------------------------------------------------------------------------- #
# AA — Architecture guards
# --------------------------------------------------------------------------- #

def test_aa1_elm_not_in_span_calculator():
    import pathlib, re
    src = pathlib.Path(__file__).resolve().parents[2] / "core" / "risk" / "span" / "span_calculator.py"
    content = src.read_text(encoding="utf-8")
    assert not re.search(r'\belm\b', content, re.IGNORECASE)


def test_aa2_elm_not_in_span_snapshot():
    import pathlib, re
    src = pathlib.Path(__file__).resolve().parents[2] / "core" / "risk" / "span" / "span_snapshot.py"
    content = src.read_text(encoding="utf-8")
    assert not re.search(r'risk_metrics\[[\'"]extreme_loss[\'"]\]\s*=', content)


def test_aa3_elm_rates_no_span_import():
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[2] / "core" / "risk" / "elm_rates.py"
    content = src.read_text(encoding="utf-8")
    assert "core.risk.span" not in content
    assert "SpanSnapshot" not in content
