"""MM9.5-S4 Phase 2 — Negative-path integration (GAP-1, GAP-5)."""

import logging
from datetime import date, datetime

import pytest

from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType
from core.instruments.equity import Equity
from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray
from core.risk.span.span_calculator import SPAN_METRIC_SCAN_RISK, SPAN_METRIC_SHORT_OPTION_MIN
from core.database.manager import DatabaseManager
from core.clock import ReplayClock
from core.brokers.paper_broker import PaperBroker

FIXED_DT = datetime(2026, 6, 28, 10, 0, 0)


def _fake_db_init(self, *a, **kw):
    pass


def _build_handler(tmp_path, monkeypatch, span_snapshot=None, initial_capital=100_000.0):
    monkeypatch.setattr(DatabaseManager, "__init__", _fake_db_init)
    clock = ReplayClock(FIXED_DT)
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=str(tmp_path)),
        clock=clock, broker=PaperBroker(clock),
        config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
        span_snapshot=span_snapshot,
    )


def _make_snap(risk_data):
    return SpanSnapshot(
        snapshot_date=date(2026, 6, 28), schema_version="4.00",
        exchange="NSE", segment="FO", file_hash="s4_test",
        is_settlement=False,
        risk_arrays={sym: SpanRiskArray(sym, m) for sym, m in risk_data.items()},
        metadata={},
    )


def _order(symbol, qty=1):
    return NormalizedOrder(
        instrument=Equity(symbol), side=OrderSide.BUY, quantity=qty,
        order_type=OrderType.MARKET, strategy_id="s", signal_id="s", timestamp=FIXED_DT,
    )


@pytest.fixture(autouse=True)
def reset_db():
    DatabaseManager.reset_instance()


def _inject_price(handler, symbol, price=100.0):
    handler._price_cache[symbol] = type("PS", (), {"price": price})()


# --------------------------------------------------------------------------- #
# N1
# --------------------------------------------------------------------------- #

def test_missing_risk_array_rejected_not_crashed(tmp_path, monkeypatch):
    snap = _make_snap({})
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=snap)
    _inject_price(handler, "NIFTY")
    assert handler._check_margin_budget(_order("NIFTY"), 100.0) == (False, 1.0)


# --------------------------------------------------------------------------- #
# N2
# --------------------------------------------------------------------------- #

def test_missing_scan_risk_rejected_not_crashed(tmp_path, monkeypatch):
    snap = _make_snap({"NIFTY": {SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=snap)
    _inject_price(handler, "NIFTY")
    assert handler._check_margin_budget(_order("NIFTY"), 100.0) == (False, 1.0)


# --------------------------------------------------------------------------- #
# N3
# --------------------------------------------------------------------------- #

def test_missing_risk_array_warning_logged(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=_make_snap({}))
    _inject_price(handler, "NIFTY")
    import io, contextlib, logging, pathlib
    logger = logging.getLogger("execution_handler")
    stream = io.StringIO()
    handler_obj = logging.StreamHandler(stream)
    handler_obj.setLevel(logging.WARNING)
    logger.addHandler(handler_obj)
    try:
        handler._check_margin_budget(_order("NIFTY"), 100.0)
    finally:
        logger.removeHandler(handler_obj)
    assert "MARGIN_BUDGET_REJECTED" in stream.getvalue()


# --------------------------------------------------------------------------- #
# N4
# --------------------------------------------------------------------------- #

def test_zero_cash_balance_bypasses_gate(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=_make_snap({}), initial_capital=0.0)
    assert handler._check_margin_budget(_order("NIFTY"), 100.0) == (True, 0.0)


# --------------------------------------------------------------------------- #
# N5
# --------------------------------------------------------------------------- #

def test_empty_risk_arrays_position_held(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=_make_snap({}))
    _inject_price(handler, "NIFTY")
    from core.execution.position_models import Position, PositionSide
    from core.instruments.equity import Equity
    handler.position_tracker._positions["NIFTY"] = Position(
        instrument=Equity("NIFTY"), side=PositionSide.LONG, quantity=1, avg_price=100.0)
    assert handler._check_margin_budget(_order("NIFTY"), 100.0) == (False, 1.0)


# --------------------------------------------------------------------------- #
# N6
# --------------------------------------------------------------------------- #

def test_held_position_not_in_snapshot(tmp_path, monkeypatch):
    snap = _make_snap({"OTHER": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=snap)
    _inject_price(handler, "NIFTY")
    from core.execution.position_models import Position, PositionSide
    from core.instruments.equity import Equity
    handler.position_tracker._positions["NIFTY"] = Position(
        instrument=Equity("NIFTY"), side=PositionSide.LONG, quantity=1, avg_price=100.0)
    assert handler._check_margin_budget(_order("NIFTY"), 100.0) == (False, 1.0)
