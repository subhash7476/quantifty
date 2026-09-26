"""
Kill switch blocks entries, never exits (§D8).

Once the kill switch trips, an open position must still be closable through
`process_signal` — otherwise a trip mid-position (STOP file, broker errors,
drawdown) strands it, e.g. a NiftyShield short structure past its 15:35 exit.
A new ENTRY after the trip must still be blocked by the latch itself.
"""

from datetime import datetime

import pytz

import core.execution.handler as handler_mod
from core.brokers.paper_broker import PaperBroker
from core.brokers.upstox_adapter import BrokerUnavailableError
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.position_models import Position, PositionSide
from core.instruments.equity import Equity

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
HELD = "NSE_EQ|HELD"


def _build_handler(tmp_path, monkeypatch, **config_kwargs):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    clock = ReplayClock(FIXED_DT)
    handler = ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=PaperBroker(clock),
        config=ExecutionConfig(mode=ExecutionMode.PAPER, **config_kwargs),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=100000.0,
    )
    handler.position_tracker._positions[HELD] = Position(
        instrument=Equity(HELD), side=PositionSide.LONG, quantity=10, avg_price=100.0)
    return handler


def _signal(symbol, signal_type, suffix):
    return SignalEvent(
        strategy_id="test_strat",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=signal_type,
        confidence=0.9,
        metadata={"signal_id": f"SIG-KSX-{suffix}", "entry_price": 100.0},
    )


def _spy_place_order(handler, monkeypatch):
    calls = []
    original = handler.broker.place_order

    def _spy(order, *a, **k):
        calls.append(order)
        return original(order, *a, **k)

    monkeypatch.setattr(handler.broker, "place_order", _spy)
    return calls


def _assert_exit_closes_and_entry_blocked(handler, monkeypatch, exit_price):
    calls = _spy_place_order(handler, monkeypatch)

    result = handler.process_signal(_signal(HELD, SignalType.EXIT, "EXIT"),
                                    current_price=exit_price)

    assert result is not None, "EXIT must bypass the kill switch"
    assert len(calls) == 1
    assert calls[0].side.value == "SELL" and calls[0].quantity == 10
    assert handler.position_tracker.get_position(HELD).side == PositionSide.FLAT

    entry = handler.process_signal(_signal("NSE_EQ|FRESH", SignalType.BUY, "ENTRY"),
                                   current_price=100.0)

    assert entry is None, "ENTRY must stay blocked after the kill switch trips"
    assert len(calls) == 1, "a blocked ENTRY must never reach the broker"
    assert handler._kill_switched


def test_exit_closes_position_after_stop_file_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    handler = _build_handler(tmp_path, monkeypatch)
    (tmp_path / "STOP").write_text("")

    tripped = handler.process_signal(_signal("NSE_EQ|OTHER", SignalType.BUY, "TRIP"),
                                     current_price=100.0)
    assert tripped is None and handler._kill_switched

    # EXIT with the STOP file still present.
    calls = _spy_place_order(handler, monkeypatch)
    result = handler.process_signal(_signal(HELD, SignalType.EXIT, "EXIT"),
                                    current_price=100.0)
    assert result is not None, "EXIT must bypass the STOP-file gate"
    assert len(calls) == 1
    assert handler.position_tracker.get_position(HELD).side == PositionSide.FLAT

    # Removing STOP does not clear the latch: a fresh ENTRY stays blocked.
    (tmp_path / "STOP").unlink()
    entry = handler.process_signal(_signal("NSE_EQ|FRESH", SignalType.BUY, "ENTRY"),
                                   current_price=100.0)
    assert entry is None
    assert len(calls) == 1


def test_exit_closes_position_after_broker_error_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    handler = _build_handler(tmp_path, monkeypatch, broker_error_threshold=3)
    original = handler.broker.place_order

    def _down(*a, **k):
        raise BrokerUnavailableError("down")

    monkeypatch.setattr(handler.broker, "place_order", _down)
    for i in range(3):
        handler.process_signal(_signal(f"NSE_EQ|ERR{i}", SignalType.BUY, f"ERR{i}"),
                               current_price=100.0)
    assert handler._kill_switched

    monkeypatch.setattr(handler.broker, "place_order", original)
    _assert_exit_closes_and_entry_blocked(handler, monkeypatch, exit_price=100.0)


def test_exit_closes_position_after_drawdown_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    handler = _build_handler(tmp_path, monkeypatch, max_drawdown_limit=0.05)
    handler.position_tracker._positions["NSE_EQ|LOSS"] = Position(
        instrument=Equity("NSE_EQ|LOSS"), side=PositionSide.LONG,
        quantity=1000, avg_price=200.0)
    handler.update_market_price("NSE_EQ|LOSS", 150.0)

    tripped = handler.process_signal(_signal("NSE_EQ|OTHER", SignalType.BUY, "TRIP"),
                                     current_price=100.0)
    assert tripped is None and handler._kill_switched

    # Mark recovers so the drawdown gate alone would pass — only the latch
    # can block the ENTRY below.
    handler.update_market_price("NSE_EQ|LOSS", 200.0)
    _assert_exit_closes_and_entry_blocked(handler, monkeypatch, exit_price=100.0)
