"""
MM8.2A + MM8.2B — BrokerUnavailableError threshold and escalation tests.

MM8.2A verifies:
  * ExecutionConfig.broker_error_threshold defaults to 3
  * ExecutionHandler initializes _consecutive_broker_errors = 0

MM8.2B verifies BrokerUnavailableError handling:
  * each failure journals BROKER_ERROR WARNING and increments counter
  * counter resets to 0 after successful place_order
  * kill switch fires when counter reaches threshold
  * process_signal returns None only at/after threshold (not before)

Uses the MM7C/MM7D.1 isolation construction pattern consistent with
tests/execution/test_handler_broker_auth_error.py.
"""

import json
import pytest

import core.execution.handler as handler_mod
from core.brokers.paper_broker import PaperBroker
from core.brokers.upstox_adapter import BrokerUnavailableError
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
from core.execution.persistence.execution_store import ExecutionStore
from core.runtime.event_journal import EventType, RuntimeEventJournal

from datetime import datetime
import pytz

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


def _build_handler(tmp_path, monkeypatch, threshold=3, **extra_kwargs):
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
        config=ExecutionConfig(mode=ExecutionMode.PAPER,
                               broker_error_threshold=threshold),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        **extra_kwargs,
    )


def _make_signal(suffix=""):
    return SignalEvent(
        strategy_id="test_strat",
        symbol="NSE_EQ|INE001",
        timestamp=FIXED_DT,
        signal_type=SignalType.BUY,
        confidence=0.9,
        metadata={"signal_id": f"SIG-UNAVAIL-{suffix}", "entry_price": 100.0},
    )


def _journal_lines(tmp_path):
    path = tmp_path / "events.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


# =========================================================================== #
# MM8.2A — Config and counter infrastructure
# =========================================================================== #

def test_execution_config_broker_error_threshold_defaults_to_3():
    assert ExecutionConfig().broker_error_threshold == 3


def test_execution_config_broker_error_threshold_is_configurable():
    cfg = ExecutionConfig(broker_error_threshold=5)
    assert cfg.broker_error_threshold == 5


def test_handler_initializes_consecutive_broker_errors_to_zero(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    assert handler._consecutive_broker_errors == 0


# =========================================================================== #
# MM8.2B — BrokerUnavailableError escalation
# =========================================================================== #

def test_broker_unavailable_increments_counter(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, threshold=3)
    call_count = [0]

    def _raise(*a, **k):
        call_count[0] += 1
        raise BrokerUnavailableError("timeout")

    monkeypatch.setattr(handler.broker, "place_order", _raise)
    handler._kill_switch_disabled = True

    # Two failures → counter should be 2, not yet at threshold
    handler.process_signal(_make_signal("1"), current_price=100.0)
    handler.process_signal(_make_signal("2"), current_price=100.0)

    assert handler._consecutive_broker_errors == 2


def test_broker_unavailable_journals_warning_each_failure(tmp_path, monkeypatch):
    journal = RuntimeEventJournal(path=str(tmp_path / "events.jsonl"))
    handler = _build_handler(tmp_path, monkeypatch, threshold=3, journal=journal)
    monkeypatch.setattr(handler.broker, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(
                            BrokerUnavailableError("unreachable")))
    handler._kill_switch_disabled = True

    handler.process_signal(_make_signal("1"), current_price=100.0)
    handler.process_signal(_make_signal("2"), current_price=100.0)

    broker_errors = [r for r in _journal_lines(tmp_path)
                     if r["event_type"] == EventType.BROKER_ERROR.value]
    assert len(broker_errors) == 2
    for rec in broker_errors:
        assert rec["severity"] == "WARNING"
        assert rec["source_component"] == "ExecutionHandler"


def test_kill_switch_fires_at_threshold(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, threshold=3)
    monkeypatch.setattr(handler.broker, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(
                            BrokerUnavailableError("down")))
    handler._kill_switch_disabled = True

    handler.process_signal(_make_signal("1"), current_price=100.0)
    handler.process_signal(_make_signal("2"), current_price=100.0)
    assert handler._kill_switched is False  # not yet at threshold

    handler.process_signal(_make_signal("3"), current_price=100.0)
    assert handler._kill_switched is True   # threshold reached


def test_counter_resets_on_successful_place_order(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, threshold=5)
    call_count = [0]

    def _sometimes_fail(*a, **k):
        call_count[0] += 1
        if call_count[0] <= 2:
            raise BrokerUnavailableError("transient")
        return "broker-id-ok"

    monkeypatch.setattr(handler.broker, "place_order", _sometimes_fail)
    handler._kill_switch_disabled = True

    # Two failures → counter = 2
    handler.process_signal(_make_signal("1"), current_price=100.0)
    handler.process_signal(_make_signal("2"), current_price=100.0)
    assert handler._consecutive_broker_errors == 2

    # Third call succeeds → counter resets to 0
    handler.process_signal(_make_signal("3"), current_price=100.0)
    assert handler._consecutive_broker_errors == 0


def test_process_signal_returns_none_after_kill_switch(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, threshold=3)
    monkeypatch.setattr(handler.broker, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(
                            BrokerUnavailableError("down")))
    handler._kill_switch_disabled = True

    handler.process_signal(_make_signal("1"), current_price=100.0)
    handler.process_signal(_make_signal("2"), current_price=100.0)
    handler.process_signal(_make_signal("3"), current_price=100.0)
    # kill switch now active
    r4 = handler.process_signal(_make_signal("4"), current_price=100.0)

    assert handler._kill_switched is True
    assert r4 is None  # kill-switch guard returns None
