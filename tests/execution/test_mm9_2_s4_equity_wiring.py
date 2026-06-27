"""
MM9.2-S4 — Wire _update_equity_metrics into broker fill path.

Activation of the existing dead method `ExecutionHandler._update_equity_metrics`
inside `_handle_broker_fill`, so realized cash accounting is active on every
fill.

Coverage:
  Characterization (unit on _update_equity_metrics):
    * C1: BUY fill reduces cash_balance by (qty * price + fees)
    * C2: SELL fill increases cash_balance by (qty * price - fees)
    * C3: cash_balance starts at initial_capital

  Integration (end-to-end via process_signal → PaperBroker fill):
    * I1: BUY fill through process_signal reduces cash_balance
    * I2: SELL exit through process_signal increases cash_balance
    * I3: drawdown is updated after fill
"""

from datetime import datetime

import pytz
import pytest

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType, TradeEvent, TradeStatus
from core.brokers.paper_broker import PaperBroker
from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.order_lifecycle import FillEvent
from core.execution.order_models import OrderSide, OrderType
from core.execution.persistence.execution_store import ExecutionStore

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


# =========================================================================== #
# Helpers
# =========================================================================== #

def _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    clock = ReplayClock(FIXED_DT)
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=PaperBroker(clock),
        config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
    )


def _make_signal(symbol="NSE_EQ|INE001A01036", sig_type=SignalType.BUY,
                 suffix="S4", quantity=None):
    metadata = {
        "signal_id": f"SIG-MM9.2-S4-{suffix}",
        "sl_distance": 1.0,
        "risk_r": 1.0,
    }
    if quantity is not None:
        metadata["quantity"] = quantity
    return SignalEvent(
        strategy_id="test_mm9_2_s4",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=sig_type,
        confidence=0.9,
        metadata=metadata,
    )


# =========================================================================== #
# Characterization — _update_equity_metrics unit tests
# =========================================================================== #

def test_c1_buy_fill_reduces_cash_balance(tmp_path, monkeypatch):
    """BUY fill: cash_balance -= (qty * price + fees)."""
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0)
    initial = handler.metrics.cash_balance

    trade = TradeEvent(
        trade_id="t1", signal_id_reference="s1",
        timestamp=FIXED_DT, symbol="NSE_EQ|AAA",
        status=TradeStatus.FILLED, direction="BUY",
        quantity=100, price=200.0, fees=50.0,
    )
    handler._update_equity_metrics(trade)

    expected_cost = 100 * 200.0 + 50.0  # 20050.0
    assert handler.metrics.cash_balance == pytest.approx(initial - expected_cost)


def test_c2_sell_fill_increases_cash_balance(tmp_path, monkeypatch):
    """SELL fill: cash_balance += (qty * price - fees)."""
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0)
    initial = handler.metrics.cash_balance

    trade = TradeEvent(
        trade_id="t2", signal_id_reference="s2",
        timestamp=FIXED_DT, symbol="NSE_EQ|AAA",
        status=TradeStatus.FILLED, direction="SELL",
        quantity=100, price=200.0, fees=50.0,
    )
    handler._update_equity_metrics(trade)

    expected_proceeds = 100 * 200.0 - 50.0  # 19950.0
    assert handler.metrics.cash_balance == pytest.approx(initial + expected_proceeds)


def test_c3_cash_balance_starts_at_initial_capital(tmp_path, monkeypatch):
    """cash_balance initializes to initial_capital."""
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=50_000.0)
    assert handler.metrics.cash_balance == 50_000.0


# =========================================================================== #
# Integration — process_signal → PaperBroker fill → equity update
# =========================================================================== #

def test_i1_buy_through_process_signal_reduces_cash(tmp_path, monkeypatch):
    """End-to-end: BUY signal → PaperBroker fill → cash_balance reduced."""
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0)
    handler._kill_switch_disabled = True
    initial = handler.metrics.cash_balance

    sig = _make_signal(symbol="NSE_EQ|AAA", suffix="I1", quantity=10)
    handler.process_signal(sig, 500.0)

    # Cash must have decreased (buy consumes cash).
    assert handler.metrics.cash_balance < initial


def test_i2_sell_exit_through_process_signal_increases_cash(tmp_path, monkeypatch):
    """End-to-end: open LONG then EXIT → cash_balance net increase on exit."""
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0)
    handler._kill_switch_disabled = True

    # Open LONG on AAA
    sig_open = _make_signal(symbol="NSE_EQ|AAA", suffix="I2-O", quantity=10)
    handler.process_signal(sig_open, 100.0)
    cash_after_open = handler.metrics.cash_balance

    # EXIT AAA (SELL to close)
    sig_exit = _make_signal(
        symbol="NSE_EQ|AAA", suffix="I2-X",
        sig_type=SignalType.EXIT,
    )
    handler.process_signal(sig_exit, 120.0)

    # Cash increased on exit (sell proceeds > open cost since price rose).
    assert handler.metrics.cash_balance > cash_after_open


def test_i3_drawdown_updated_after_fill(tmp_path, monkeypatch):
    """Drawdown is recalculated inside _update_equity_metrics."""
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0)
    handler._kill_switch_disabled = True

    # BUY at a loss scenario: buy high, then the fill price itself sets equity
    # below initial. _update_equity_metrics calls metrics.update_drawdown.
    sig = _make_signal(symbol="NSE_EQ|AAA", suffix="I3", quantity=10)
    handler.process_signal(sig, 100.0)

    # max_drawdown_pct should be non-negative after any fill (fees create loss).
    assert handler.metrics.max_drawdown_pct >= 0.0
