"""
A transient stale-data trip must not latch the kill switch for the day.

2026-10-06: Upstox was unreachable 11:49-11:55, the watchdog tripped the kill
switch at 11:54, bars resumed at 11:56 — and the latch stayed until the process
died, so the 13:01 entry was rejected ("every leg rejected by a handler gate").
Only the stale-data trip is releasable. Drawdown, broker, STOP-file and
daily-limit trips stay latched, and a hard trip landing while a stale trip is
active must survive the recovery.
"""

from datetime import datetime, timedelta

from core.database.utils.market_hours import MarketHours
from core.execution.watchdog import RuntimeWatchdog

from test_kill_switch_exit_bypass import _build_handler


def test_stale_trip_is_released_on_recovery(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    handler.activate_kill_switch("Data feed stale (5.0m)", releasable=True)
    assert handler._kill_switched

    assert handler.release_kill_switch("bars flowing again") is True
    assert not handler._kill_switched


def test_default_trip_is_never_released(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    handler.activate_kill_switch("Max drawdown (5.0%) reached.")

    assert handler.release_kill_switch("bars flowing again") is False
    assert handler._kill_switched


def test_hard_trip_during_a_stale_trip_survives_the_recovery(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    handler.activate_kill_switch("Data feed stale (5.0m)", releasable=True)
    handler.activate_kill_switch("NiftyShield day loss Rs 31,000")

    assert handler.release_kill_switch("bars flowing again") is False
    assert handler._kill_switched


def test_release_without_a_trip_is_a_no_op(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    assert handler.release_kill_switch("bars flowing again") is False


def test_stale_trip_after_a_hard_trip_does_not_become_releasable(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    handler.activate_kill_switch("BrokerAuthError: expired")
    handler.activate_kill_switch("Data feed stale (5.0m)", releasable=True)

    assert handler.release_kill_switch("bars flowing again") is False
    assert handler._kill_switched


class _Execution:
    def __init__(self):
        self.calls = []

    def activate_kill_switch(self, reason, *, releasable=False):
        self.calls.append(("activate", releasable))

    def release_kill_switch(self, reason):
        self.calls.append(("release",))
        return True


def test_watchdog_trips_releasable_and_releases_on_recovery(monkeypatch):
    monkeypatch.setattr(MarketHours, "is_market_open", staticmethod(lambda: True))
    execution = _Execution()
    wd = RuntimeWatchdog(execution, heartbeat_path="unused.json")
    wd._last_bar_timestamp = datetime.now() - timedelta(minutes=6)

    wd.check_data_staleness()
    assert execution.calls == [("activate", True)]
    assert wd.data_healthy is False

    wd.record_bar()
    assert execution.calls == [("activate", True), ("release",)]
    assert wd.data_healthy is True


def test_watchdog_does_not_release_without_a_stale_trip(monkeypatch):
    execution = _Execution()
    wd = RuntimeWatchdog(execution, heartbeat_path="unused.json")

    wd.record_bar()

    assert execution.calls == []
