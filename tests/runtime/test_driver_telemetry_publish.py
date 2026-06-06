"""
Unit tests for LoopDriver Phase H — ZMQ TelemetryPublisher integration.

Validates that the driver drives the external publishing bridge
(RuntimeTelemetryPublisher) on its telemetry cadence as observation only:
publishing the Runtime Observability Layer snapshot externally without ever
affecting runtime behavior, and never able to stop the loop.

Proven here (the prompt's TDD requirements):
1. telemetry can be published — the transport receives the metric snapshot
   during a run;
2. publisher is optional — the driver constructs and runs without one;
3. runtime functions without a publisher (the inert loop is unchanged);
4. publisher failures are non-fatal — a publisher whose publish() raises does
   not stop the loop;
5. existing metrics collection is unchanged — the counter snapshot is identical
   with vs without a publisher (publishing only reads, never writes);
   plus the §10.2 throttle, deterministic publish sequence, and close()-on-stop.

No real network: a FakeTelemetryTransport double records calls; the real
RuntimeTelemetryPublisher + InMemoryTelemetrySink are used (real code).
"""

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.metrics import InMemoryTelemetrySink
from core.runtime.telemetry_publisher import RuntimeTelemetryPublisher

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, FakeTelemetryTransport, bar_series,
                      make_signal)


class _RaisingPublisher:
    """A hostile publisher: publish() raises. Proves publishing is best-effort."""

    def publish(self):
        raise RuntimeError("publish exploded")

    def close(self):
        return None


def _replay_cfg(max_bars=None, tel_interval=0.0):
    return DriverConfig(mode=Mode.REPLAY, symbols=["A"], max_bars=max_bars,
                        telemetry_interval_s=tel_interval)


# --------------------------------------------------------------------------- #
# (1) telemetry can be published — transport receives the snapshot during run
# --------------------------------------------------------------------------- #
def test_publisher_receives_metric_snapshot_during_run():
    sink = InMemoryTelemetrySink()
    transport = FakeTelemetryTransport()
    pub = RuntimeTelemetryPublisher(transport, sink)
    source = FakeSignalSource([[make_signal("A")], [make_signal("A")]])
    d = LoopDriver(_replay_cfg(max_bars=3, tel_interval=0.0), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 4)}),
                   source=source, execution=FakeExecutionHandler(),
                   telemetry=sink, publisher=pub)
    d.run()
    assert transport.published                            # at least one publish
    assert transport.published[-1]["bars_processed"] == 3 # snapshot reflects the run
    assert transport.published[-1]["startup_count"] == 1


# --------------------------------------------------------------------------- #
# (2)+(3) publisher is optional — driver runs without one
# --------------------------------------------------------------------------- #
def test_driver_runs_without_a_publisher():
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}))
    d.run()
    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 2


# --------------------------------------------------------------------------- #
# (4) publisher failure is non-fatal — a raising publish() does not stop the loop
# --------------------------------------------------------------------------- #
def test_raising_publisher_does_not_break_the_loop():
    d = LoopDriver(_replay_cfg(max_bars=2, tel_interval=0.0), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   execution=FakeExecutionHandler(), telemetry=InMemoryTelemetrySink(),
                   publisher=_RaisingPublisher())
    d.run()
    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 2


# --------------------------------------------------------------------------- #
# (5) existing metrics collection is unchanged with vs without a publisher
# --------------------------------------------------------------------------- #
def test_publishing_does_not_change_metric_collection():
    def run(with_publisher):
        sink = InMemoryTelemetrySink()
        pub = RuntimeTelemetryPublisher(FakeTelemetryTransport(), sink) if with_publisher else None
        source = FakeSignalSource([[make_signal("A")], [make_signal("A")]])
        d = LoopDriver(_replay_cfg(max_bars=2, tel_interval=0.0), clock=FakeClock(),
                       provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                       source=source, execution=FakeExecutionHandler(),
                       telemetry=sink, publisher=pub)
        d.run()
        return sink.snapshot()

    assert run(True) == run(False)


# --------------------------------------------------------------------------- #
# (§10.2) the publish cadence is throttled by telemetry_interval_s
# --------------------------------------------------------------------------- #
def test_publish_is_throttled_by_interval():
    sink = InMemoryTelemetrySink()
    transport = FakeTelemetryTransport()
    pub = RuntimeTelemetryPublisher(transport, sink)
    # Bars are 1 minute apart (FakeClock advances to each bar.timestamp); a huge
    # interval means only the first tick publishes, the rest are throttled.
    d = LoopDriver(_replay_cfg(max_bars=3, tel_interval=10_000.0), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 4)}),
                   telemetry=sink, publisher=pub)
    d.run()
    assert len(transport.published) == 1


# --------------------------------------------------------------------------- #
# (9) the published sequence is deterministic across identical runs
# --------------------------------------------------------------------------- #
def test_published_sequence_is_deterministic_across_runs():
    def run_once():
        sink = InMemoryTelemetrySink()
        transport = FakeTelemetryTransport()
        pub = RuntimeTelemetryPublisher(transport, sink)
        source = FakeSignalSource([[make_signal("A")], [make_signal("A")]])
        d = LoopDriver(_replay_cfg(max_bars=2, tel_interval=0.0), clock=FakeClock(),
                       provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                       source=source, execution=FakeExecutionHandler(),
                       telemetry=sink, publisher=pub)
        d.run()
        return transport.published

    assert run_once() == run_once()


# --------------------------------------------------------------------------- #
# (lifecycle) the transport is closed on shutdown
# --------------------------------------------------------------------------- #
def test_publisher_closed_on_stop():
    transport = FakeTelemetryTransport()
    sink = InMemoryTelemetrySink()
    pub = RuntimeTelemetryPublisher(transport, sink)
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   telemetry=sink, publisher=pub)
    d.run()
    assert transport.closed == 1
