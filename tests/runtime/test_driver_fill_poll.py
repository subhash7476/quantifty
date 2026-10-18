"""
LoopDriver - the live fill-poll seam (`fill_poll`, DRIVER_SPECIFICATION.md §8.3).

A broker that does not push fills (UpstoxAdapter has no WebSocket order-update
feed) is polled once per loop iteration, and once more when the loop ends. The
seam is opt-in and live-only: a driver built without `fill_poll`, or run in
REPLAY, takes exactly the path it took before the hook existed.

A poll that raises is never swallowed: it is logged and journaled, the loop
survives, and consecutive failures trip the handler's kill switch through the
public `activate_kill_switch` at the handler's own `broker_error_threshold`.
What the failure was decides what the trip is:

- a pure outage (BrokerUnavailableError) trips a RELEASABLE switch, lifted by the
  first sweep that reaches every order again - like the stale-data trip, because
  the fault is transient and a full sweep is what makes the ledger current;
- an auth failure trips a hard switch at once and ends polling (a dead token
  cannot poll; it takes a restart with a new one);
- anything else (an unreadable reply, an unresolved placement) trips a hard
  switch: the poll is not telling the ledger the truth until someone looks.

A rejected or cancelled order is a discrete event, not an outage: it is journaled
every time and never counts toward the threshold.
"""

import json
from datetime import datetime

import pytest
import pytz

from core.brokers.upstox_adapter import (
    BrokerAmbiguousPlacementError, BrokerAuthError, BrokerContractError,
    BrokerOrderNotFilledError, BrokerUnavailableError, EndedOrder)
from core.events import OrderStatus
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, FakeWatchdog, bar_series)

_START = datetime(2026, 6, 5, 9, 15, tzinfo=pytz.UTC)
_DOWN = BrokerUnavailableError("down")


def _driver(tmp_path, *, mode=Mode.LIVE, fill_poll=None, n_bars=4, script=None,
            timeline=None, watchdog=None):
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
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    execution = FakeExecutionHandler()
    driver = LoopDriver(
        DriverConfig(mode=mode, symbols=["A"], max_bars=n_bars),
        clock=FakeClock(),
        provider=FakeMarketDataProvider({"A": bars}, live=(mode is Mode.LIVE)),
        source=source, execution=execution, journal=journal, watchdog=watchdog,
        broker_positions=lambda: [], fill_poll=fill_poll)
    return driver, execution, timeline


def _events(tmp_path, event_type=None):
    path = tmp_path / "runtime_events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    return [e for e in events if event_type is None or e["event_type"] == event_type]


def _script(*outcomes):
    """A fill_poll that raises each given error in turn (None = succeed), then
    succeeds for ever. `.calls` counts the polls."""
    queue = list(outcomes)

    def poll():
        poll.calls += 1
        if queue:
            error = queue.pop(0)
            if error is not None:
                raise error
    poll.calls = 0
    return poll


def _always(error):
    def poll():
        poll.calls += 1
        raise error
    poll.calls = 0
    return poll


# --------------------------------------------------------------------------- #
# The seam: when it runs
# --------------------------------------------------------------------------- #

def test_live_driver_polls_before_each_bar_and_once_more_when_the_loop_ends(tmp_path):
    timeline = []
    driver, _, _ = _driver(tmp_path, fill_poll=lambda: timeline.append("poll"),
                           n_bars=3, timeline=timeline)

    driver.run()

    assert driver.state is RuntimeState.STOPPED
    # the startup gate's poll, one before each bar, one when the loop ends
    assert timeline == ["poll", "poll", "bar", "poll", "bar", "poll", "bar", "poll"]


def test_the_startup_gate_polls_before_it_reconciles_against_the_broker(tmp_path):
    """A fill that landed while the process was down must reach the ledger
    before positions are compared, or every restart refuses as a divergence."""
    timeline = []
    source = FakeSignalSource()
    driver = LoopDriver(
        DriverConfig(mode=Mode.LIVE, symbols=["A"], max_bars=1),
        clock=FakeClock(),
        provider=FakeMarketDataProvider({"A": bar_series("A", 1, start=_START)}, live=True),
        source=source, execution=FakeExecutionHandler(),
        journal=RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl")),
        broker_positions=lambda: timeline.append("reconcile") or [],
        fill_poll=lambda: timeline.append("poll"))

    driver.run()

    assert timeline[:2] == ["poll", "reconcile"]


def test_live_driver_polls_on_a_tick_with_no_bar(tmp_path):
    poll = _script()
    script = [None] + bar_series("A", 1, start=_START)
    driver, _, _ = _driver(tmp_path, fill_poll=poll, n_bars=1, script=script)

    driver.run()

    assert poll.calls == 4  # the startup gate, the empty tick, the bar tick, the final poll


def test_replay_driver_never_calls_fill_poll(tmp_path):
    poll = _script()
    driver, _, _ = _driver(tmp_path, mode=Mode.REPLAY, fill_poll=poll, n_bars=3)

    driver.run()

    assert driver.state is RuntimeState.STOPPED
    assert poll.calls == 0


def test_driver_without_fill_poll_runs_as_before(tmp_path):
    driver, _, timeline = _driver(tmp_path, n_bars=3)

    driver.run()

    assert driver.state is RuntimeState.STOPPED
    assert timeline == ["bar", "bar", "bar"]


def test_fill_poll_keeps_running_while_the_kill_switch_is_latched(tmp_path):
    """Orders placed before a trip still fill; the poll is how that is learned."""
    poll = _script()
    driver, execution, _ = _driver(tmp_path, fill_poll=poll, n_bars=3)
    execution.activate_kill_switch("tripped before the run")

    driver.run()

    assert poll.calls == 5  # startup gate + 3 bars + final


# --------------------------------------------------------------------------- #
# A raising poll: never swallowed, never fatal, counted toward the threshold
# --------------------------------------------------------------------------- #

def test_a_raising_poll_does_not_kill_the_loop_and_is_journaled_once(tmp_path):
    driver, execution, timeline = _driver(tmp_path, fill_poll=_script(_DOWN, _DOWN), n_bars=4)

    driver.run()

    assert driver.state is RuntimeState.STOPPED
    assert timeline == ["bar"] * 4
    assert not execution._kill_switched  # 2 failures < threshold 3
    errors = _events(tmp_path, "BROKER_ERROR")
    assert len(errors) == 1  # the incident, not each failure
    assert "down" in errors[0]["message"]


def test_a_successful_poll_resets_the_failure_count(tmp_path):
    poll = _script(_DOWN, _DOWN, None, _DOWN, _DOWN)
    driver, execution, _ = _driver(tmp_path, fill_poll=poll, n_bars=6)

    driver.run()

    assert not execution._kill_switched


# --------------------------------------------------------------------------- #
# What the trip is: releasable for an outage, hard for everything else
# --------------------------------------------------------------------------- #

def test_an_outage_trips_a_releasable_switch_and_the_first_clean_sweep_lifts_it(tmp_path):
    driver, execution, _ = _driver(tmp_path, fill_poll=_script(_DOWN, _DOWN, _DOWN), n_bars=5)
    assert execution.config.broker_error_threshold == 3

    driver.run()

    events = [e["event_type"] for e in _events(tmp_path)]
    assert "KILL_SWITCH_ACTIVATED" in events
    assert "KILL_SWITCH_RELEASED" in events
    assert not execution._kill_switched
    assert not execution._kill_hard


def test_a_persisting_outage_keeps_the_switch_tripped_but_releasable(tmp_path):
    poll = _always(_DOWN)
    driver, execution, _ = _driver(tmp_path, fill_poll=poll, n_bars=5)

    driver.run()

    assert execution._kill_switched
    assert not execution._kill_hard  # a later clean sweep could still lift it
    assert poll.calls == 7  # startup gate + 5 bars + final


@pytest.mark.parametrize("error", [
    BrokerContractError("unusable reply"),
    BrokerAmbiguousPlacementError("placement unresolved"),
    ValueError("anything else"),
], ids=["contract", "ambiguous-placement", "other"])
def test_any_other_failure_trips_a_hard_switch_that_a_clean_poll_does_not_lift(
        tmp_path, error):
    driver, execution, _ = _driver(tmp_path, fill_poll=_script(error, error, error), n_bars=5)

    driver.run()

    assert execution._kill_switched
    assert execution._kill_hard
    assert "KILL_SWITCH_RELEASED" not in [e["event_type"] for e in _events(tmp_path)]


def test_a_stale_feed_blocks_the_release_so_the_watchdog_owns_it(tmp_path):
    """The handler has one switch: lifting an outage trip while the data feed is
    still stale would lift the watchdog's trip too."""
    watchdog = FakeWatchdog()
    watchdog.data_healthy = False
    watchdog.record_bar = lambda: None  # the feed stays stale for the whole run
    driver, execution, _ = _driver(tmp_path, fill_poll=_script(_DOWN, _DOWN, _DOWN),
                                   n_bars=5, watchdog=watchdog)

    driver.run()

    assert execution._kill_switched


def test_a_hard_trip_that_lands_during_an_outage_trip_is_not_released(tmp_path):
    driver, execution, _ = _driver(tmp_path, fill_poll=_script(_DOWN, _DOWN, _DOWN), n_bars=5)
    execution.activate_kill_switch("drawdown")  # hard, before the outage trip

    driver.run()

    assert execution._kill_switched
    assert execution._kill_hard


# --------------------------------------------------------------------------- #
# F - an auth failure is one incident: one event, one trip, then no more polling
# --------------------------------------------------------------------------- #

def test_auth_failure_trips_hard_journals_once_and_ends_polling(tmp_path):
    poll = _always(BrokerAuthError("token expired"))
    driver, execution, _ = _driver(tmp_path, fill_poll=poll, n_bars=5)

    driver.run()

    assert driver.state is RuntimeState.STOPPED
    assert execution._kill_switched
    assert execution._kill_hard
    assert poll.calls == 1  # a dead token is not polled again
    assert len(_events(tmp_path, "BROKER_ERROR")) == 1


# --------------------------------------------------------------------------- #
# E - a rejected / cancelled order is an event, not an outage
# --------------------------------------------------------------------------- #

def test_not_filled_orders_are_journaled_each_time_and_never_trip_the_switch(tmp_path):
    ended = BrokerOrderNotFilledError("order X-1 rejected by Upstox with 0 filled: funds")
    poll = _script(ended, ended, ended, ended, ended)
    driver, execution, _ = _driver(tmp_path, fill_poll=poll, n_bars=5)

    driver.run()

    assert not execution._kill_switched
    errors = _events(tmp_path, "BROKER_ERROR")
    assert len(errors) == 5
    assert all("rejected" in e["message"] for e in errors)


def test_a_not_filled_report_resets_the_outage_count(tmp_path):
    ended = BrokerOrderNotFilledError("order X-1 cancelled by Upstox")
    poll = _script(_DOWN, _DOWN, ended, _DOWN, _DOWN)
    driver, execution, _ = _driver(tmp_path, fill_poll=poll, n_bars=6)

    driver.run()

    assert not execution._kill_switched


# --------------------------------------------------------------------------- #
# A reject that rides on a worse error is still journaled; the shutdown poll is
# still observed
# --------------------------------------------------------------------------- #

def test_a_reject_carried_on_another_error_is_journaled_every_time(tmp_path):
    def raising_with_a_reject():
        error = BrokerContractError("unusable reply")
        error.not_filled = [EndedOrder(
            "corr-9", OrderStatus.REJECTED, "order X-9 rejected by Upstox with 0 filled: funds")]
        raise error

    driver, _, _ = _driver(tmp_path, fill_poll=raising_with_a_reject, n_bars=4)

    driver.run()

    rejects = [e for e in _events(tmp_path, "BROKER_ERROR") if "X-9 rejected" in e["message"]]
    assert len(rejects) == 6  # every poll (startup gate + 4 bars + final), though the incident is journaled once


def test_a_trip_made_by_the_shutdown_poll_is_journaled(tmp_path):
    poll = _script(None, _DOWN, _DOWN, _DOWN)  # the startup poll succeeds; the third failure is the final poll
    driver, execution, _ = _driver(tmp_path, fill_poll=poll, n_bars=2)

    driver.run()

    assert execution._kill_switched
    assert "KILL_SWITCH_ACTIVATED" in [e["event_type"] for e in _events(tmp_path)]
