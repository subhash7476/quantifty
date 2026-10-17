"""
LoopDriver — the live fill-poll seam (`fill_poll`, DRIVER_SPECIFICATION.md §8.3).

A broker that does not push fills (UpstoxAdapter has no WebSocket order-update
feed) is polled once per loop iteration. The seam is opt-in and live-only: a
driver built without `fill_poll`, or run in REPLAY, takes exactly the path it
took before the hook existed.

A poll that raises is never swallowed: it is logged and journaled, the loop
survives, and consecutive failures trip the handler's kill switch through the
public `activate_kill_switch` — the path consecutive broker errors already use —
at the handler's own `broker_error_threshold`. An auth failure trips it at once.
"""

import json
from datetime import datetime

import pytz

from core.brokers.upstox_adapter import BrokerAuthError, BrokerUnavailableError
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, bar_series)

_START = datetime(2026, 6, 5, 9, 15, tzinfo=pytz.UTC)


def _driver(tmp_path, *, mode=Mode.LIVE, fill_poll=None, n_bars=4, script=None,
            journal=True, timeline=None):
    """`timeline` collects "bar" for every bar the source sees, so a test can
    read the order of polls and bars from one list."""
    bars = script if script is not None else bar_series("A", n_bars, start=_START)
    timeline = timeline if timeline is not None else []
    source = FakeSignalSource()
    real_on_bar = source.on_bar

    def on_bar(bar):
        timeline.append("bar")
        return real_on_bar(bar)
    source.on_bar = on_bar
    j = (RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
         if journal else None)
    execution = FakeExecutionHandler()
    driver = LoopDriver(
        DriverConfig(mode=mode, symbols=["A"], max_bars=n_bars),
        clock=FakeClock(),
        provider=FakeMarketDataProvider({"A": bars}, live=(mode is Mode.LIVE)),
        source=source, execution=execution, journal=j,
        broker_positions=lambda: [], fill_poll=fill_poll)
    return driver, execution, timeline


def _events(tmp_path):
    path = tmp_path / "runtime_events.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_live_driver_polls_fills_once_per_iteration_before_the_bar(tmp_path):
    timeline = []
    driver, _, _ = _driver(tmp_path, fill_poll=lambda: timeline.append("poll"),
                           n_bars=3, timeline=timeline)

    driver.run()

    assert driver.state is RuntimeState.STOPPED
    assert timeline == ["poll", "bar", "poll", "bar", "poll", "bar"]


def test_live_driver_polls_on_a_tick_with_no_bar(tmp_path):
    polls = []
    script = [None] + bar_series("A", 1, start=_START)
    driver, _, _ = _driver(tmp_path, fill_poll=lambda: polls.append(1),
                           n_bars=1, script=script)

    driver.run()

    assert len(polls) == 2  # the empty tick and the bar tick


def test_replay_driver_never_calls_fill_poll(tmp_path):
    polls = []
    driver, _, _ = _driver(tmp_path, mode=Mode.REPLAY,
                           fill_poll=lambda: polls.append(1), n_bars=3)

    driver.run()

    assert driver.state is RuntimeState.STOPPED
    assert polls == []


def test_driver_without_fill_poll_runs_as_before(tmp_path):
    driver, _, log = _driver(tmp_path, n_bars=3)

    driver.run()

    assert driver.state is RuntimeState.STOPPED
    assert log == ["bar", "bar", "bar"]


def test_fill_poll_keeps_running_while_the_kill_switch_is_latched(tmp_path):
    """Orders placed before a trip still fill; the poll is how that is learned."""
    polls = []
    driver, execution, _ = _driver(tmp_path, fill_poll=lambda: polls.append(1), n_bars=3)
    execution.activate_kill_switch("tripped before the run")

    driver.run()

    assert len(polls) == 3


def _failing(errors):
    """A fill_poll that raises the given errors in order, then succeeds."""
    queue = list(errors)

    def poll():
        if queue:
            error = queue.pop(0)
            if error is not None:
                raise error
    return poll


def test_a_raising_poll_does_not_kill_the_loop_and_is_journaled_once(tmp_path):
    poll = _failing([BrokerUnavailableError("down"), BrokerUnavailableError("down")])
    driver, execution, log = _driver(tmp_path, fill_poll=poll, n_bars=4)

    driver.run()

    assert driver.state is RuntimeState.STOPPED
    assert log == ["bar"] * 4
    assert not execution._kill_switched  # 2 failures < threshold 3
    errors = [e for e in _events(tmp_path) if e["event_type"] == "BROKER_ERROR"]
    assert len(errors) == 1  # the incident, not each failure
    assert "down" in errors[0]["message"]


def test_consecutive_poll_failures_trip_the_kill_switch_at_the_handler_threshold(
        tmp_path):
    poll = _failing([BrokerUnavailableError("down")] * 3)
    driver, execution, _ = _driver(tmp_path, fill_poll=poll, n_bars=5)
    assert execution.config.broker_error_threshold == 3

    driver.run()

    assert execution._kill_switched
    assert execution._kill_hard  # latched, like every non-stale-data trip
    events = [e["event_type"] for e in _events(tmp_path)]
    assert "KILL_SWITCH_ACTIVATED" in events


def test_a_successful_poll_resets_the_failure_count(tmp_path):
    down = BrokerUnavailableError("down")
    poll = _failing([down, down, None, down, down])
    driver, execution, _ = _driver(tmp_path, fill_poll=poll, n_bars=6)

    driver.run()

    assert not execution._kill_switched


def test_auth_failure_trips_the_kill_switch_at_once(tmp_path):
    poll = _failing([BrokerAuthError("token expired")])
    driver, execution, _ = _driver(tmp_path, fill_poll=poll, n_bars=3)

    driver.run()

    assert execution._kill_switched
    assert execution._kill_hard


def test_a_poll_that_raises_a_contract_error_counts_like_any_other_failure(tmp_path):
    poll = _failing([ValueError("malformed")] * 3)
    driver, execution, _ = _driver(tmp_path, fill_poll=poll, n_bars=5)

    driver.run()

    assert execution._kill_switched
