"""
MM8.1B — BrokerAuthError escalation unit tests.

Verifies that ExecutionHandler.process_signal converts a BrokerAuthError raised
by broker.place_order() into an immediate session halt:
  * kill switch activated
  * BROKER_ERROR CRITICAL journaled with source_component="ExecutionHandler"
  * process_signal returns None (no ghost order)
  * no exception re-raised

Uses the MM7C/MM7D.1 isolation construction (monkeypatch ExecutionStore -> tmp)
consistent with tests/execution/test_handler_journal_injection.py.
"""

import json
import pytest

import core.execution.handler as handler_mod
from core.brokers.paper_broker import PaperBroker
from core.brokers.upstox_adapter import BrokerAuthError
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
from core.execution.persistence.execution_store import ExecutionStore
from core.runtime.event_journal import EventType, RuntimeEventJournal

from datetime import datetime
import pytz

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


def _build_handler(tmp_path, monkeypatch, **extra_kwargs):
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
        config=ExecutionConfig(mode=ExecutionMode.PAPER),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        **extra_kwargs,
    )


def _make_signal():
    return SignalEvent(
        strategy_id="test_strat",
        symbol="NSE_EQ|INE001",
        timestamp=FIXED_DT,
        signal_type=SignalType.BUY,
        confidence=0.9,
        metadata={"signal_id": "SIG-AUTH-001", "entry_price": 100.0},
    )


def _journal_lines(tmp_path):
    path = tmp_path / "events.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


# --------------------------------------------------------------------------- #
# (1) kill switch is activated on BrokerAuthError
# --------------------------------------------------------------------------- #
def test_kill_switch_activated_on_broker_auth_error(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    monkeypatch.setattr(handler.broker, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(BrokerAuthError("token expired")))
    handler._kill_switch_disabled = True  # disable drawdown/daily-limit guards

    handler.process_signal(_make_signal(), current_price=100.0)

    assert handler._kill_switched is True


# --------------------------------------------------------------------------- #
# (2) process_signal returns None (not the order) on BrokerAuthError
# --------------------------------------------------------------------------- #
def test_returns_none_on_broker_auth_error(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    monkeypatch.setattr(handler.broker, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(BrokerAuthError("401")))
    handler._kill_switch_disabled = True

    result = handler.process_signal(_make_signal(), current_price=100.0)

    assert result is None


# --------------------------------------------------------------------------- #
# (3) BROKER_ERROR CRITICAL is journaled with source_component="ExecutionHandler"
# --------------------------------------------------------------------------- #
def test_broker_auth_error_journaled_critical(tmp_path, monkeypatch):
    journal = RuntimeEventJournal(path=str(tmp_path / "events.jsonl"))
    handler = _build_handler(tmp_path, monkeypatch, journal=journal)
    monkeypatch.setattr(handler.broker, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(BrokerAuthError("invalid token")))
    handler._kill_switch_disabled = True

    handler.process_signal(_make_signal(), current_price=100.0)

    broker_errors = [r for r in _journal_lines(tmp_path)
                     if r["event_type"] == EventType.BROKER_ERROR.value]
    assert len(broker_errors) == 1
    rec = broker_errors[0]
    assert rec["severity"] == "CRITICAL"
    assert rec["source_component"] == "ExecutionHandler"
    assert "token" in rec["message"].lower() or "invalid" in rec["message"].lower()


# --------------------------------------------------------------------------- #
# (4) no exception is re-raised — process_signal completes normally
# --------------------------------------------------------------------------- #
def test_no_exception_reraised_on_broker_auth_error(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    monkeypatch.setattr(handler.broker, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(BrokerAuthError("expired")))
    handler._kill_switch_disabled = True

    # must not raise
    handler.process_signal(_make_signal(), current_price=100.0)


# --------------------------------------------------------------------------- #
# (5) kill switch fires even when no journal is wired
# --------------------------------------------------------------------------- #
def test_kill_switch_fires_without_journal(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)  # no journal kwarg
    monkeypatch.setattr(handler.broker, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(BrokerAuthError("no token")))
    handler._kill_switch_disabled = True

    result = handler.process_signal(_make_signal(), current_price=100.0)

    assert handler._kill_switched is True
    assert result is None
