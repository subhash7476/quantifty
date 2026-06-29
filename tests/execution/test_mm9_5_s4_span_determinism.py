"""MM9.5-S4 Phase 3 — Determinism (GAP-6)."""

from datetime import date, datetime

import pytest

from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType
from core.instruments.equity import Equity
from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray
from core.risk.span.span_calculator import (
    SpanMarginCalculator,
    SPAN_METRIC_SCAN_RISK,
    SPAN_METRIC_SHORT_OPTION_MIN,
)
from core.execution.position_tracker import PositionTracker
from core.database.manager import DatabaseManager
from core.clock import ReplayClock
from core.brokers.paper_broker import PaperBroker

FIXED_DT = datetime(2026, 6, 28, 10, 0, 0)


def _make_snap(risk_data):
    return SpanSnapshot(
        snapshot_date=date(2026, 6, 28), schema_version="4.00",
        exchange="NSE", segment="FO", file_hash="test",
        is_settlement=False,
        risk_arrays={sym: SpanRiskArray(sym, m) for sym, m in risk_data.items()},
        metadata={},
    )


def _fake_db_init(self, *a, **kw):
    pass


@pytest.fixture(autouse=True)
def reset_db():
    DatabaseManager.reset_instance()


def _order(symbol, qty=1):
    return NormalizedOrder(
        instrument=Equity(symbol), side=OrderSide.BUY, quantity=qty,
        order_type=OrderType.MARKET, strategy_id="s", signal_id="s", timestamp=FIXED_DT,
    )


# --------------------------------------------------------------------------- #
# D1
# --------------------------------------------------------------------------- #

def test_span_gate_repeated_identical(tmp_path, monkeypatch):
    monkeypatch.setattr(DatabaseManager, "__init__", _fake_db_init)
    snap = _make_snap({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    handler = ExecutionHandler(
        db_manager=DatabaseManager(data_root=str(tmp_path)),
        clock=ReplayClock(FIXED_DT), broker=PaperBroker(ReplayClock(FIXED_DT)),
        config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True, initial_capital=100_000.0, span_snapshot=snap,
    )
    r1 = handler._check_margin_budget(_order("NIFTY"), 100.0)
    r2 = handler._check_margin_budget(_order("NIFTY"), 100.0)
    r3 = handler._check_margin_budget(_order("NIFTY"), 100.0)
    assert r1 == r2 == r3


# --------------------------------------------------------------------------- #
# D2
# --------------------------------------------------------------------------- #

def test_two_calculators_same_snapshot():
    snap = _make_snap({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    pt = PositionTracker()
    c1 = SpanMarginCalculator(pt, snap)
    c2 = SpanMarginCalculator(pt, snap)
    assert c1.get_used_margin({"NIFTY": 100.0}) == c2.get_used_margin({"NIFTY": 100.0})


# --------------------------------------------------------------------------- #
# D3
# --------------------------------------------------------------------------- #

def test_used_margin_deterministic():
    snap = _make_snap({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0}})
    calc = SpanMarginCalculator(PositionTracker(), snap)
    assert calc.get_used_margin({"NIFTY": 100.0}) == calc.get_used_margin({"NIFTY": 100.0})
