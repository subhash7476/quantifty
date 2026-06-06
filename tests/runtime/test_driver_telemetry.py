"""
Unit tests for LoopDriver Phase H — Runtime Telemetry.

Validates that the driver feeds an injected TelemetrySink the in-scope runtime
counters (lifecycle / runtime / watchdog / execution) as observation only —
without changing runtime behavior, without becoming a source of truth, and
without telemetry failure ever stopping the loop (best-effort).

Proven here (the prompt's TDD requirements):
1. metrics increment correctly — a controlled replay run yields the exact
   counter snapshot;
2. existing runtime behavior is unchanged — bars/signals/routing are identical
   with an InMemoryTelemetrySink vs no sink at all;
3. telemetry failure does not break runtime — a sink that raises on every
   increment breaks neither construction nor the loop;
4. telemetry is optional — the driver runs with no sink injected;
5. runtime remains deterministic — two identical replay runs produce identical
   snapshots;
   plus the watchdog (heartbeat / stale / kill-switch) and execution counters,
   and the received-vs-routed distinction (PAUSED collects but does not route).
"""

import json

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal
from core.runtime.metrics import InMemoryTelemetrySink, RuntimeMetric, TelemetrySink

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, FakeWatchdog, bar_series, make_bar,
                      make_signal)

M = RuntimeMetric


class _RaisingSink(TelemetrySink):
    """A hostile sink: every increment raises. Proves telemetry is best-effort."""

    def increment(self, metric, count=1):
        raise RuntimeError("telemetry backend exploded")


def _replay_cfg(symbols=("A",), max_bars=None):
    return DriverConfig(mode=Mode.REPLAY, symbols=list(symbols), max_bars=max_bars)


def _live_cfg(symbols=("A",), max_bars=None, poll=0.25):
    return DriverConfig(mode=Mode.LIVE, symbols=list(symbols), max_bars=max_bars,
                        poll_interval_s=poll)


# --------------------------------------------------------------------------- #
# (1) metrics increment correctly — exact snapshot of a controlled replay run
# --------------------------------------------------------------------------- #
def test_controlled_replay_run_produces_exact_metric_snapshot():
    sink = InMemoryTelemetrySink()
    handler = FakeExecutionHandler()
    source = FakeSignalSource([[make_signal("A")], [make_signal("A")]])
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source, execution=handler, telemetry=sink)
    d.run()
    assert sink.snapshot() == {
        M.STARTUP_COUNT: 1,
        M.RECOVERY_COUNT: 1,
        M.RECONCILIATION_COUNT: 1,
        M.STOP_COUNT: 1,
        M.LOOP_ITERATIONS: 2,
        M.BARS_PROCESSED: 2,
        M.SIGNALS_RECEIVED: 2,
        M.SIGNALS_ROUTED: 2,
        M.EXECUTION_CALLS: 2,
    }


# --------------------------------------------------------------------------- #
# (2) existing runtime behavior is unchanged with vs without a sink
# --------------------------------------------------------------------------- #
def test_telemetry_does_not_change_runtime_behavior():
    def run(telemetry):
        handler = FakeExecutionHandler()
        source = FakeSignalSource([[make_signal("A")], [make_signal("A")]])
        d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                       provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                       source=source, execution=handler, telemetry=telemetry)
        d.run()
        return d.bars_processed, d.signals_pulled, len(handler.routed), d.state

    assert run(InMemoryTelemetrySink()) == run(None)


# --------------------------------------------------------------------------- #
# (3) telemetry failure does not break runtime — construction nor loop
# --------------------------------------------------------------------------- #
def test_raising_sink_does_not_break_construction_or_loop():
    handler = FakeExecutionHandler()
    source = FakeSignalSource([[make_signal("A")], [make_signal("A")]])
    # Construction meters STARTUP_COUNT; a raising sink must not break __init__.
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source, execution=handler, telemetry=_RaisingSink())
    d.run()
    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 2
    assert len(handler.routed) == 2          # routing unaffected by the bad sink


# --------------------------------------------------------------------------- #
# (4) telemetry is optional — driver runs with no sink injected
# --------------------------------------------------------------------------- #
def test_driver_runs_with_no_telemetry_sink():
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}))
    d.run()
    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 2


# --------------------------------------------------------------------------- #
# (5) runtime remains deterministic — identical runs, identical snapshots
# --------------------------------------------------------------------------- #
def test_metric_snapshot_is_deterministic_across_identical_runs():
    def run_once():
        sink = InMemoryTelemetrySink()
        source = FakeSignalSource([[make_signal("A")], [make_signal("A")]])
        d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                       provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                       source=source, execution=FakeExecutionHandler(), telemetry=sink)
        d.run()
        return sink.snapshot()

    assert run_once() == run_once()


# --------------------------------------------------------------------------- #
# watchdog counter: heartbeats emitted once per tick (live)
# --------------------------------------------------------------------------- #
def test_heartbeats_emitted_counted_per_tick_live():
    sink = InMemoryTelemetrySink()
    d = LoopDriver(_live_cfg(max_bars=3), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 5)}, live=True),
                   watchdog=FakeWatchdog(), execution=FakeExecutionHandler(),
                   telemetry=sink)
    d.run()
    assert sink.get(M.HEARTBEATS_EMITTED) == 3
    assert sink.get(M.LOOP_ITERATIONS) == 3
    assert sink.get(M.BARS_PROCESSED) == 3


# --------------------------------------------------------------------------- #
# watchdog counters: a stale-feed trip increments stale + kill-switch once
# --------------------------------------------------------------------------- #
class _StopAfterSleepsClock(FakeClock):
    def __init__(self, box, after=1):
        super().__init__()
        self._box = box
        self._after = after

    def sleep(self, seconds):
        super().sleep(seconds)
        if len(self.sleeps) >= self._after:
            self._box[0].stop()


def test_stale_data_and_kill_switch_events_counted_once():
    sink = InMemoryTelemetrySink()
    wd = FakeWatchdog(stale_after=2)
    box = []
    clock = _StopAfterSleepsClock(box, after=2)
    d = LoopDriver(_live_cfg(), clock=clock,
                   provider=FakeMarketDataProvider({"A": [make_bar("A"), None, None]}, live=True),
                   watchdog=wd, execution=FakeExecutionHandler(), telemetry=sink)
    box.append(d)
    d.run()
    assert sink.get(M.STALE_DATA_EVENTS) == 1
    assert sink.get(M.KILL_SWITCH_EVENTS) == 1


# --------------------------------------------------------------------------- #
# REPLAY drives no watchdog → no watchdog counters
# --------------------------------------------------------------------------- #
def test_replay_emits_no_watchdog_counters():
    sink = InMemoryTelemetrySink()
    d = LoopDriver(_replay_cfg(max_bars=3), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 5)}),
                   watchdog=FakeWatchdog(stale_after=1), telemetry=sink)
    d.run()
    assert sink.get(M.HEARTBEATS_EMITTED) == 0
    assert sink.get(M.STALE_DATA_EVENTS) == 0
    assert sink.get(M.KILL_SWITCH_EVENTS) == 0


# --------------------------------------------------------------------------- #
# a reconciliation FAIL still counts the recovery + reconciliation cycle
# --------------------------------------------------------------------------- #
def test_reconciliation_fail_counts_cycle_but_not_stop_or_bars():
    sink = InMemoryTelemetrySink()
    handler = FakeExecutionHandler(reconcile_alerts=["DIVERGENCE"])
    d = LoopDriver(_live_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}, live=True),
                   execution=handler, telemetry=sink,
                   broker_positions=lambda: [{"symbol": "A", "qty": 1}])
    d.run()
    assert d.state is RuntimeState.STOPPED          # refused to start
    assert sink.get(M.RECOVERY_COUNT) == 1          # recovery cycle happened
    assert sink.get(M.RECONCILIATION_COUNT) == 1    # reconciliation cycle happened
    assert sink.get(M.BARS_PROCESSED) == 0          # loop never ran
    assert sink.get(M.STOP_COUNT) == 0              # refuse-to-start is not a clean stop


# --------------------------------------------------------------------------- #
# received vs routed: PAUSED collects (received) but does not route
# --------------------------------------------------------------------------- #
def test_paused_counts_received_but_not_routed():
    sink = InMemoryTelemetrySink()
    handler = FakeExecutionHandler()
    d = LoopDriver(_replay_cfg(), execution=handler, telemetry=sink)
    d.start()                                        # → RUNNING
    d.pause()                                        # → PAUSED
    d._dispatch_signals([make_signal("A"), make_signal("B")], make_bar("A", close=50.0))
    assert sink.get(M.SIGNALS_RECEIVED) == 2         # collected
    assert sink.get(M.SIGNALS_ROUTED) == 0           # not routed (PAUSED)
    assert sink.get(M.EXECUTION_CALLS) == 0
    assert handler.routed == []


# --------------------------------------------------------------------------- #
# telemetry adds no new journal events (observability stays separate)
# --------------------------------------------------------------------------- #
def test_telemetry_adds_no_new_journal_events(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=FakeSignalSource([[make_signal("A")]]),
                   execution=FakeExecutionHandler(), journal=journal,
                   telemetry=InMemoryTelemetrySink())
    d.run()
    events = {json.loads(l)["event_type"]
              for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()}
    assert events <= {"STARTUP", "RECOVERY_STARTED", "RECOVERY_COMPLETED",
                      "RECONCILIATION_PASS", "RUNNING", "STOPPING", "STOPPED"}
