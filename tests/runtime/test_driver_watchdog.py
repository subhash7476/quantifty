"""
Unit tests for LoopDriver — RuntimeWatchdog integration (the plan's Phase F;
driven here as the safety phase before execution).

Validates DRIVER_SPECIFICATION.md §9 / ADR-004 in the still-execution-free loop:
- record_bar() is driven once per processed bar (live only);
- check_data_staleness() + write_heartbeat(bars_processed) run once per tick
  after the symbol sweep (live only);
- a stale-data trip emits WATCHDOG_STALE_DATA + KILL_SWITCH_ACTIVATED to the
  journal, edge-triggered (once per incident, no per-tick duplication);
- in REPLAY mode none of the watchdog methods are driven (§9.5 wall-clock gate);
- the watchdog is OPTIONAL — the loop runs unchanged without one;
- the driver introduces NO ExecutionHandler dependency and no process_signal
  call (ADR-006): signals are still only collected, never routed.
"""

import ast
import json
from pathlib import Path

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal

from _doubles import (FakeClock, FakeMarketDataProvider, FakeWatchdog,
                      bar_series, make_bar)


def _live_cfg(symbols=("A",), max_bars=None, poll=0.25):
    return DriverConfig(mode=Mode.LIVE, symbols=list(symbols),
                        max_bars=max_bars, poll_interval_s=poll)


def _replay_cfg(symbols=("A",), max_bars=None):
    return DriverConfig(mode=Mode.REPLAY, symbols=list(symbols), max_bars=max_bars)


class _StopAfterSleepsClock(FakeClock):
    """Bounds a live no-bar scenario: stop the driver after `after` polls."""

    def __init__(self, box, after=1):
        super().__init__()
        self._box = box
        self._after = after

    def sleep(self, seconds: float) -> None:
        super().sleep(seconds)
        if len(self.sleeps) >= self._after:
            self._box[0].stop()


# --------------------------------------------------------------------------- #
# (1) record_bar once per processed bar; (2) staleness; (3) heartbeat — live
# --------------------------------------------------------------------------- #
def test_record_bar_called_once_per_processed_bar():
    wd = FakeWatchdog()
    d = LoopDriver(_live_cfg(max_bars=3), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 5)}, live=True),
                   watchdog=wd)
    d.run()
    assert d.bars_processed == 3
    assert wd.record_bar_calls == 3


def test_staleness_check_driven_each_tick():
    wd = FakeWatchdog()
    d = LoopDriver(_live_cfg(max_bars=3), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 5)}, live=True),
                   watchdog=wd)
    d.run()
    assert wd.staleness_checks == 3            # one per tick (after each sweep)


def test_heartbeat_driven_each_tick_with_bar_counter():
    wd = FakeWatchdog()
    d = LoopDriver(_live_cfg(max_bars=3), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 5)}, live=True),
                   watchdog=wd)
    d.run()
    assert wd.heartbeats == [1, 2, 3]          # write_heartbeat(bars_processed) per tick


# --------------------------------------------------------------------------- #
# (4)+(5) journal events on a stale-data trip, edge-triggered
# --------------------------------------------------------------------------- #
def _run_stale_scenario(tmp_path, stale_after, none_bars, stop_after_sleeps):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    wd = FakeWatchdog(stale_after=stale_after)
    box = []
    clock = _StopAfterSleepsClock(box, after=stop_after_sleeps)
    script = [make_bar("A")] + [None] * none_bars
    d = LoopDriver(_live_cfg(), clock=clock,
                   provider=FakeMarketDataProvider({"A": script}, live=True),
                   journal=journal, watchdog=wd)
    box.append(d)
    d.run()
    events = [json.loads(l)["event_type"]
              for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]
    return d, events, wd


def test_watchdog_stale_data_event_emitted(tmp_path):
    d, events, _ = _run_stale_scenario(tmp_path, stale_after=2, none_bars=1,
                                       stop_after_sleeps=1)
    assert d.state is RuntimeState.STOPPED
    assert events.count("WATCHDOG_STALE_DATA") == 1


def test_kill_switch_activated_event_emitted(tmp_path):
    d, events, _ = _run_stale_scenario(tmp_path, stale_after=2, none_bars=1,
                                       stop_after_sleeps=1)
    assert events.count("KILL_SWITCH_ACTIVATED") == 1
    # The kill-switch event follows the staleness detection.
    assert events.index("WATCHDOG_STALE_DATA") < events.index("KILL_SWITCH_ACTIVATED")


def test_stale_events_edge_triggered_not_duplicated(tmp_path):
    # Two no-bar stale ticks before stopping — the events must still fire once.
    d, events, _ = _run_stale_scenario(tmp_path, stale_after=2, none_bars=2,
                                       stop_after_sleeps=2)
    assert events.count("WATCHDOG_STALE_DATA") == 1
    assert events.count("KILL_SWITCH_ACTIVATED") == 1


def test_loop_keeps_running_after_kill_switch(tmp_path):
    # §9.6: a kill-switched loop keeps running (and beating) until stopped.
    # Trip fires on staleness check #2; a 3rd check proves the loop ran ON past
    # the kill switch rather than dying on it (state==STOPPED alone can't, since
    # the finally block reaches STOPPED on every exit path).
    d, _, wd = _run_stale_scenario(tmp_path, stale_after=2, none_bars=2,
                                   stop_after_sleeps=2)
    assert d.state is RuntimeState.STOPPED
    assert wd.staleness_checks == 3


# --------------------------------------------------------------------------- #
# (live gate) REPLAY drives no watchdog method (§9.5)
# --------------------------------------------------------------------------- #
def test_replay_mode_drives_no_watchdog():
    wd = FakeWatchdog()
    d = LoopDriver(_replay_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   watchdog=wd)
    d.run()
    assert d.bars_processed == 3               # loop ran normally
    assert wd.record_bar_calls == 0
    assert wd.staleness_checks == 0
    assert wd.heartbeats == []


def test_replay_mode_emits_no_watchdog_journal_events(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    wd = FakeWatchdog(stale_after=1)           # would trip if ever driven
    d = LoopDriver(_replay_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   journal=journal, watchdog=wd)
    d.run()
    events = [json.loads(l)["event_type"]
              for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]
    assert "WATCHDOG_STALE_DATA" not in events
    assert "KILL_SWITCH_ACTIVATED" not in events


# --------------------------------------------------------------------------- #
# (6) the watchdog is OPTIONAL — loop runs unchanged without one
# --------------------------------------------------------------------------- #
def test_no_watchdog_runs_normally_live():
    d = LoopDriver(_live_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 4)}, live=True))
    d.run()
    assert d.bars_processed == 2
    assert d.state is RuntimeState.STOPPED


# --------------------------------------------------------------------------- #
# (8)+(9) no ExecutionHandler dependency / no process_signal call (ADR-006)
# --------------------------------------------------------------------------- #
def test_driver_has_no_executionhandler_dependency():
    src_path = Path(__file__).resolve().parents[2] / "core" / "runtime" / "driver.py"
    text = src_path.read_text(encoding="utf-8")
    tree = ast.parse(text)

    imported_names: set = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                imported_names.add(alias.name)
    # The driver may depend on the watchdog, but never on the handler directly.
    assert "ExecutionHandler" not in imported_names

    # ADR-006: the driver is not (yet) a caller of process_signal.
    calls_process_signal = any(
        isinstance(n, ast.Attribute) and n.attr == "process_signal"
        for n in ast.walk(tree)
    )
    assert not calls_process_signal
