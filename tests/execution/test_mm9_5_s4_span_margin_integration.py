"""MM9.5-S4 Phase 1 — SPAN margin gate end-to-end (GAP-7, GAP-4)."""

from datetime import date, datetime

import pytest

from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType
from core.instruments.equity import Equity
from core.instruments.future import Future
from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray
from core.risk.span.span_calculator import (
    SPAN_METRIC_SCAN_RISK,
    SPAN_METRIC_SHORT_OPTION_MIN,
)
from core.database.manager import DatabaseManager
from core.clock import ReplayClock
from core.brokers.paper_broker import PaperBroker

FIXED_DT = datetime(2026, 6, 28, 10, 0, 0)


def _fake_db_init(self, *a, **kw):
    pass


def _build_handler(tmp_path, monkeypatch, span_snapshot=None, initial_capital=100_000.0, max_utilisation=0.80):
    monkeypatch.setattr(DatabaseManager, "__init__", _fake_db_init)
    clock = ReplayClock(FIXED_DT)
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=str(tmp_path)),
        clock=clock,
        broker=PaperBroker(clock),
        config=ExecutionConfig(max_capital_utilisation=max_utilisation),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
        span_snapshot=span_snapshot,
    )


def _make_snap(risk_data=None):
    if risk_data is None:
        risk_data = {
            "NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0},
        }
    return SpanSnapshot(
        snapshot_date=date(2026, 6, 28), schema_version="4.00",
        exchange="NSE", segment="FO", file_hash="s4_test",
        is_settlement=False,
        risk_arrays={sym: SpanRiskArray(sym, m) for sym, m in risk_data.items()},
        metadata={},
    )


@pytest.fixture(autouse=True)
def reset_db():
    DatabaseManager.reset_instance()


def _order(symbol, qty=1):
    return NormalizedOrder(
        instrument=Equity(symbol),
        side=OrderSide.BUY, quantity=qty, order_type=OrderType.MARKET,
        strategy_id="s", signal_id="s", timestamp=FIXED_DT,
    )


# --------------------------------------------------------------------------- #
# I1
# --------------------------------------------------------------------------- #

def test_span_gate_approves_under_limit(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=_make_snap(), initial_capital=100_000.0)
    approved, utilisation = handler._check_margin_budget(_order("NIFTY"), 100.0)
    assert approved is True
    assert utilisation < 0.80


# --------------------------------------------------------------------------- #
# I2
# --------------------------------------------------------------------------- #

def test_span_gate_rejects_over_limit(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=_make_snap(), initial_capital=100.0)
    approved, utilisation = handler._check_margin_budget(_order("NIFTY", qty=10), 100.0)
    assert approved is False
    assert utilisation > 0.80


# --------------------------------------------------------------------------- #
# I3
# --------------------------------------------------------------------------- #

def test_span_gate_boundary_equal(tmp_path, monkeypatch):
    capital = 30.0 / 0.80  # scan_risk=30, lot=1, qty=1 → utilisation=30/capital=0.80
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=_make_snap(), initial_capital=capital)
    _, utilisation = handler._check_margin_budget(_order("NIFTY"), 100.0)
    assert utilisation == pytest.approx(0.80, rel=1e-9)


# --------------------------------------------------------------------------- #
# I4
# --------------------------------------------------------------------------- #

def test_span_gate_includes_used_current(tmp_path, monkeypatch):
    snap = _make_snap({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=snap)
    handler._price_cache["NIFTY"] = type("PS", (), {"price": 100.0})()
    from core.execution.order_lifecycle import FillEvent
    handler.position_tracker.update_from_fill(FillEvent(
        fill_id="f1", order_id="o1", symbol="NIFTY",
        quantity=1, price=100.0, timestamp=FIXED_DT, side="BUY",
    ))
    _, utilisation = handler._check_margin_budget(_order("NIFTY"), 100.0)
    assert utilisation == pytest.approx(60.0 / 100_000.0, rel=1e-9)


# --------------------------------------------------------------------------- #
# I5
# --------------------------------------------------------------------------- #

def test_span_gate_futures_multiplier(tmp_path, monkeypatch):
    snap = _make_snap({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=snap)
    inst = Future("NIFTY", "NIFTY", date(2026, 6, 28))
    object.__setattr__(inst, "multiplier", 65)
    order = NormalizedOrder(
        instrument=inst, side=OrderSide.BUY, quantity=2, order_type=OrderType.MARKET,
        strategy_id="s", signal_id="s", timestamp=FIXED_DT,
    )
    _, utilisation = handler._check_margin_budget(order, 100.0)
    assert utilisation == pytest.approx(3900.0 / 100_000.0, rel=1e-9)


# --------------------------------------------------------------------------- #
# I6
# --------------------------------------------------------------------------- #

def test_span_gate_margin_rate_haircut(tmp_path, monkeypatch):
    snap = _make_snap({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=snap)
    handler.margin_tracker.margin_rate = 1.5
    _, utilisation = handler._check_margin_budget(_order("NIFTY"), 100.0)
    assert utilisation == pytest.approx(45.0 / 100_000.0, rel=1e-9)


# --------------------------------------------------------------------------- #
# I7
# --------------------------------------------------------------------------- #

def test_span_gate_price_independence(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=_make_snap())
    _, u1 = handler._check_margin_budget(_order("NIFTY"), 100.0)
    _, u2 = handler._check_margin_budget(_order("NIFTY"), 500.0)
    assert u1 == u2


# --------------------------------------------------------------------------- #
# I8
# --------------------------------------------------------------------------- #

def test_span_gate_single_execution_deterministic(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, span_snapshot=_make_snap())
    order = _order("NIFTY")
    assert handler._check_margin_budget(order, 100.0) == handler._check_margin_budget(order, 100.0)
