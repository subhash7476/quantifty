"""
MM8.4 — Integration and acceptance sweep.

Cross-slice invariants that per-slice unit tests cannot catch individually.
Each test names the MM8 success criterion it validates (spec §7).

§7.5 — Execution metrics reflect actual execution attempts.
       BrokerUnavailableError must return None (not the order) so that
       MM8.1C's EXECUTION_CALLS gate does NOT meter failed placements.
"""

import pytest

import core.execution.handler as handler_mod
from core.brokers.paper_broker import PaperBroker
from core.brokers.upstox_adapter import BrokerUnavailableError
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
from core.execution.persistence.execution_store import ExecutionStore

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
        metadata={"signal_id": f"SIG-ACC-{suffix}", "entry_price": 100.0},
    )


# --------------------------------------------------------------------------- #
# §7.5a — process_signal returns None on BrokerUnavailableError (first failure)
#
# Exposes the cross-slice bug: MM8.2B except block fell through to `return order`,
# so even the first BrokerUnavailableError returned non-None, causing
# EXECUTION_CALLS to be metered (contradicting §7.5 / Gap G2).
# --------------------------------------------------------------------------- #
def test_process_signal_returns_none_on_first_broker_unavailable(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, threshold=5)
    monkeypatch.setattr(handler.broker, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(
                            BrokerUnavailableError("timeout")))
    handler._kill_switch_disabled = True

    result = handler.process_signal(_make_signal("1"), current_price=100.0)

    assert result is None, (
        "BrokerUnavailableError must return None (no ghost order, no metered call) "
        "regardless of threshold position (MM8 §7.5 / Gap G2)"
    )


# --------------------------------------------------------------------------- #
# §7.5b — successive below-threshold failures all return None
# --------------------------------------------------------------------------- #
def test_all_below_threshold_failures_return_none(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, threshold=5)
    monkeypatch.setattr(handler.broker, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(
                            BrokerUnavailableError("down")))
    handler._kill_switch_disabled = True

    results = [
        handler.process_signal(_make_signal(str(i)), current_price=100.0)
        for i in range(4)   # 4 failures, threshold=5
    ]

    assert all(r is None for r in results), (
        "Every BrokerUnavailableError below threshold must return None"
    )


# --------------------------------------------------------------------------- #
# §7.5c — successful placement returns non-None (metrics correctly metered)
# --------------------------------------------------------------------------- #
def test_successful_placement_returns_non_none(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, threshold=3)
    handler._kill_switch_disabled = True

    result = handler.process_signal(_make_signal("1"), current_price=100.0)

    assert result is not None, (
        "Successful broker placement must return non-None "
        "so EXECUTION_CALLS is correctly metered (MM8 §7.5)"
    )


# --------------------------------------------------------------------------- #
# §7.5d — counter resets on success even after prior BrokerUnavailableErrors
# --------------------------------------------------------------------------- #
def test_success_after_unavailable_errors_returns_non_none(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, threshold=5)
    call_count = [0]

    def _sometimes_fail(*a, **k):
        call_count[0] += 1
        if call_count[0] <= 2:
            raise BrokerUnavailableError("transient")
        return "broker-ok"

    monkeypatch.setattr(handler.broker, "place_order", _sometimes_fail)
    handler._kill_switch_disabled = True

    handler.process_signal(_make_signal("1"), current_price=100.0)  # fail
    handler.process_signal(_make_signal("2"), current_price=100.0)  # fail
    result = handler.process_signal(_make_signal("3"), current_price=100.0)  # success

    assert result is not None
    assert handler._consecutive_broker_errors == 0
