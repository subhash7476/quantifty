"""
Unit tests for LoopDriver Phase G — IN-001 KILL_SWITCH_ACTIVATED single source.

Before this increment the driver emitted KILL_SWITCH_ACTIVATED only from the
watchdog's data-health proxy (the data_healthy True->False edge), so a kill
switch the *handler* tripped itself (drawdown / daily-limit / broker fault during
process_signal) went **un-journaled**. IN-001 moves the emission to a single
observation of the handler's own kill-switch edge (`_kill_switched` False->True,
§10.7), covering every cause exactly once. WATCHDOG_STALE_DATA stays on the
watchdog path (stale data is its specific cause).

Proven here:
1. a handler-caused kill switch (no watchdog, no stale data) IS now journaled —
   the IN-001 gap closed;
2. the event is edge-triggered: once per activation, never per-tick;
3. KILL_SWITCH_EVENTS is metered exactly once on the same edge;
4. no trip -> no event and a zero counter;
5. it is observed in REPLAY/paper too (not live-gated, unlike the watchdog);
6. the loop keeps running after the kill switch (a later bar still processes).

`FakeExecutionHandler(kill_switch_on=...)` flips its own `_kill_switched` after
routing the named signal — simulating a handler-decided trip.
"""

import json

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal
from core.runtime.metrics import InMemoryTelemetrySink, RuntimeMetric

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, bar_series, make_signal)


def _replay_cfg(max_bars=None):
    return DriverConfig(mode=Mode.REPLAY, symbols=["A"], max_bars=max_bars)


def _events(tmp_path):
    return [json.loads(l)["event_type"]
            for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]


# --------------------------------------------------------------------------- #
# (1) the IN-001 win: a handler-caused kill switch is journaled (no watchdog)
# --------------------------------------------------------------------------- #
def test_handler_caused_kill_switch_is_journaled(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(kill_switch_on="DRAW")
    source = FakeSignalSource([[make_signal("DRAW")], [make_signal("OK")]])
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source, execution=handler, journal=journal)
    d.run()

    ev = _events(tmp_path)
    assert ev.count("KILL_SWITCH_ACTIVATED") == 1     # previously un-journaled — now caught
    assert "WATCHDOG_STALE_DATA" not in ev            # not a stale-data cause; no watchdog


# --------------------------------------------------------------------------- #
# (2) edge-triggered — once per activation, not per tick
# --------------------------------------------------------------------------- #
def test_kill_switch_event_is_edge_triggered_once(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(kill_switch_on="DRAW")
    # Trip on bar 0; bars 1 and 2 keep ticking with the switch still latched.
    source = FakeSignalSource([[make_signal("DRAW")], [make_signal("OK")], [make_signal("OK")]])
    d = LoopDriver(_replay_cfg(max_bars=3), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 4)}),
                   source=source, execution=handler, journal=journal)
    d.run()

    assert _events(tmp_path).count("KILL_SWITCH_ACTIVATED") == 1


# --------------------------------------------------------------------------- #
# (3) KILL_SWITCH_EVENTS metered exactly once on the same edge
# --------------------------------------------------------------------------- #
def test_kill_switch_metric_counted_once(tmp_path):
    sink = InMemoryTelemetrySink()
    handler = FakeExecutionHandler(kill_switch_on="DRAW")
    source = FakeSignalSource([[make_signal("DRAW")], [make_signal("OK")]])
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source, execution=handler, telemetry=sink)
    d.run()

    assert sink.get(RuntimeMetric.KILL_SWITCH_EVENTS) == 1


# --------------------------------------------------------------------------- #
# (4) no trip → no event, zero counter
# --------------------------------------------------------------------------- #
def test_no_kill_switch_no_event(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    sink = InMemoryTelemetrySink()
    handler = FakeExecutionHandler()                  # never trips
    source = FakeSignalSource([[make_signal("OK")], [make_signal("OK")]])
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source, execution=handler, journal=journal, telemetry=sink)
    d.run()

    assert "KILL_SWITCH_ACTIVATED" not in _events(tmp_path)
    assert sink.get(RuntimeMetric.KILL_SWITCH_EVENTS) == 0


# --------------------------------------------------------------------------- #
# (5) observed in REPLAY/paper too — NOT live-gated (unlike the watchdog, §9.5)
# --------------------------------------------------------------------------- #
def test_kill_switch_observed_in_replay_mode(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(kill_switch_on="DRAW")
    source = FakeSignalSource([[make_signal("DRAW")]])
    d = LoopDriver(_replay_cfg(max_bars=1), clock=FakeClock(),     # REPLAY
                   provider=FakeMarketDataProvider({"A": bar_series("A", 2)}),
                   source=source, execution=handler, journal=journal)
    d.run()

    assert _events(tmp_path).count("KILL_SWITCH_ACTIVATED") == 1


# --------------------------------------------------------------------------- #
# (6) §9.6 — the loop keeps running after the kill switch
# --------------------------------------------------------------------------- #
def test_loop_keeps_running_after_handler_kill_switch():
    handler = FakeExecutionHandler(kill_switch_on="DRAW")
    source = FakeSignalSource([[make_signal("DRAW")], [make_signal("OK")]])
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source, execution=handler)
    d.run()

    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 2                       # ran ON past the kill switch
    assert [s.symbol for s, _ in handler.routed] == ["DRAW", "OK"]
