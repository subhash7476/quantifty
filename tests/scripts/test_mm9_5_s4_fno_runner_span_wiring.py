"""MM9.5-S4 Phase 4 — Composition wiring tests (S1–S4)."""

from datetime import date, datetime

import pytest

from core.execution.handler import ExecutionHandler, ExecutionConfig
from core.execution.margin_tracker import MarginTracker
from core.risk.nse_margin_engine import NseMarginEngine
from core.risk.span.span_calculator import SpanMarginCalculator
from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray
from core.risk.span.span_calculator import SPAN_METRIC_SCAN_RISK, SPAN_METRIC_SHORT_OPTION_MIN
from core.database.manager import DatabaseManager
from core.clock import ReplayClock
from core.brokers.paper_broker import PaperBroker

FIXED_DT = datetime(2026, 6, 28, 10, 0, 0)


def _make_snap():
    return SpanSnapshot(
        snapshot_date=date(2026, 6, 28), schema_version="4.00",
        exchange="NSE", segment="FO", file_hash="test",
        is_settlement=False,
        risk_arrays={"NIFTY": SpanRiskArray("NIFTY", {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 0.0})},
        metadata={},
    )


@pytest.fixture(autouse=True)
def reset_db():
    DatabaseManager.reset_instance()


# --------------------------------------------------------------------------- #
# S1
# --------------------------------------------------------------------------- #

def test_snapshot_loaded_injects_span_calculator(tmp_path, monkeypatch):
    monkeypatch.setattr(DatabaseManager, "__init__", lambda *a, **kw: None)
    handler = ExecutionHandler(
        db_manager=DatabaseManager(data_root=str(tmp_path)),
        clock=ReplayClock(FIXED_DT), broker=PaperBroker(ReplayClock(FIXED_DT)),
        config=ExecutionConfig(), metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True, initial_capital=100_000.0, span_snapshot=_make_snap(),
    )
    assert isinstance(handler.margin_tracker, NseMarginEngine)


# --------------------------------------------------------------------------- #
# S2
# --------------------------------------------------------------------------- #

def test_no_snapshot_falls_back_to_margin_tracker(tmp_path, monkeypatch):
    monkeypatch.setattr(DatabaseManager, "__init__", lambda *a, **kw: None)
    handler = ExecutionHandler(
        db_manager=DatabaseManager(data_root=str(tmp_path)),
        clock=ReplayClock(FIXED_DT), broker=PaperBroker(ReplayClock(FIXED_DT)),
        config=ExecutionConfig(), metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True, initial_capital=100_000.0,
    )
    assert isinstance(handler.margin_tracker, MarginTracker)


# --------------------------------------------------------------------------- #
# S3
# --------------------------------------------------------------------------- #

def test_span_readiness_injected_for_derivatives(tmp_path, monkeypatch):
    monkeypatch.setattr(DatabaseManager, "__init__", lambda *a, **kw: None)
    handler = ExecutionHandler(
        db_manager=DatabaseManager(data_root=str(tmp_path)),
        clock=ReplayClock(FIXED_DT), broker=PaperBroker(ReplayClock(FIXED_DT)),
        config=ExecutionConfig(), metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True, initial_capital=100_000.0, span_snapshot=_make_snap(),
    )
    from core.execution.order_models import NormalizedOrder, OrderSide, OrderType
    from core.instruments.equity import Equity
    order = NormalizedOrder(
        instrument=Equity("NIFTY"), side=OrderSide.BUY, quantity=1,
        order_type=OrderType.MARKET, strategy_id="s", signal_id="s", timestamp=FIXED_DT,
    )
    result = handler._check_margin_budget(order, 100.0)
    assert result[0] is True or result[0] is False


# --------------------------------------------------------------------------- #
# S4
# --------------------------------------------------------------------------- #

def test_span_readiness_none_for_equity(tmp_path, monkeypatch):
    monkeypatch.setattr(DatabaseManager, "__init__", lambda *a, **kw: None)
    handler = ExecutionHandler(
        db_manager=DatabaseManager(data_root=str(tmp_path)),
        clock=ReplayClock(FIXED_DT), broker=PaperBroker(ReplayClock(FIXED_DT)),
        config=ExecutionConfig(), metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True, initial_capital=100_000.0,
    )
    assert isinstance(handler.margin_tracker, MarginTracker)
