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

from datetime import datetime

import pytz

from core.database.utils.market_hours import MarketHours
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.metrics import InMemoryTelemetrySink
from core.runtime.telemetry_publisher import RuntimeTelemetryPublisher

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, FakeTelemetryTransport, FakeWatchdog,
                      bar_series, make_bar, make_signal)

_UTC = pytz.UTC
_START = datetime(2026, 6, 5, 9, 15, tzinfo=_UTC)   # known bar-time for assertions
_HEALTH_KEYS = {"node", "state", "data_healthy", "market_open", "uptime_s", "last_tick"}


class _RaisingPublisher:
    """A hostile publisher: every publish raises. Proves publishing is best-effort."""

    def publish(self):
        raise RuntimeError("publish exploded")

    def publish_health(self, data):
        raise RuntimeError("health publish exploded")

    def publish_positions(self, data):
        raise RuntimeError("positions publish exploded")

    def close(self):
        return None


def _replay_cfg(max_bars=None, tel_interval=0.0):
    return DriverConfig(mode=Mode.REPLAY, symbols=["A"], max_bars=max_bars,
                        telemetry_interval_s=tel_interval)


def _live_cfg(max_bars=None, tel_interval=0.0, poll=0.25):
    return DriverConfig(mode=Mode.LIVE, symbols=["A"], max_bars=max_bars,
                        telemetry_interval_s=tel_interval, poll_interval_s=poll)


# --------------------------------------------------------------------------- #
# (1) health payload is published during a run, with the documented schema
# --------------------------------------------------------------------------- #
def test_health_payload_published_with_documented_schema():
    transport = FakeTelemetryTransport()
    sink = InMemoryTelemetrySink()
    pub = RuntimeTelemetryPublisher(transport, sink)
    d = LoopDriver(_replay_cfg(max_bars=3, tel_interval=0.0), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 4, start=_START)}),
                   telemetry=sink, publisher=pub)
    d.run()
    assert transport.published_health                      # health was published
    last = transport.published_health[-1]
    assert set(last.keys()) == _HEALTH_KEYS                # exact §10.5 schema
    assert last["node"] == "trade_loop"
    assert last["state"] == "RUNNING"                      # state during the loop
    assert last["data_healthy"] is True                    # no watchdog → healthy
    assert isinstance(last["market_open"], bool)
    assert isinstance(last["uptime_s"], float) and last["uptime_s"] >= 0.0


# --------------------------------------------------------------------------- #
# last_tick + market_open are derived from the deterministic trade clock
# --------------------------------------------------------------------------- #
def test_health_last_tick_and_market_open_track_the_trade_clock():
    transport = FakeTelemetryTransport()
    sink = InMemoryTelemetrySink()
    pub = RuntimeTelemetryPublisher(transport, sink)
    d = LoopDriver(_replay_cfg(max_bars=3, tel_interval=0.0), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 4, start=_START)}),
                   telemetry=sink, publisher=pub)
    d.run()
    last_bar_ts = _START.replace(minute=17)                # 3rd processed bar (start+2m)
    last = transport.published_health[-1]
    assert last["last_tick"] == last_bar_ts.isoformat()
    assert last["market_open"] == MarketHours.is_market_open(last_bar_ts)


# --------------------------------------------------------------------------- #
# data_healthy is a projection of the watchdog's PUBLIC flag (no private attrs)
# --------------------------------------------------------------------------- #
def test_health_data_healthy_reflects_watchdog_flag():
    wd = FakeWatchdog()
    wd.data_healthy = False                                # simulate a tripped feed
    d = LoopDriver(_live_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": [make_bar("A")]}, live=True),
                   watchdog=wd, execution=FakeExecutionHandler())
    d._clock.set_time(_START)                              # give last_tick a value
    assert d._build_health()["data_healthy"] is False

    d2 = LoopDriver(_replay_cfg(), clock=FakeClock(),
                    provider=FakeMarketDataProvider({"A": [make_bar("A")]}))
    d2._clock.set_time(_START)
    assert d2._build_health()["data_healthy"] is True      # no watchdog → healthy


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


# --------------------------------------------------------------------------- #
# (2) health publishing follows the SAME cadence as metrics (one per publish)
# --------------------------------------------------------------------------- #
def test_health_publishes_on_the_same_cadence_as_metrics():
    sink = InMemoryTelemetrySink()
    transport = FakeTelemetryTransport()
    pub = RuntimeTelemetryPublisher(transport, sink)
    d = LoopDriver(_replay_cfg(max_bars=3, tel_interval=0.0), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 4)}),
                   telemetry=sink, publisher=pub)
    d.run()
    # Metrics + health publish together each cadence tick — equal counts.
    assert len(transport.published_health) == len(transport.published) == 3


def test_health_publish_is_throttled_by_interval():
    sink = InMemoryTelemetrySink()
    transport = FakeTelemetryTransport()
    pub = RuntimeTelemetryPublisher(transport, sink)
    d = LoopDriver(_replay_cfg(max_bars=3, tel_interval=10_000.0), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 4)}),
                   telemetry=sink, publisher=pub)
    d.run()
    assert len(transport.published_health) == 1            # only the first tick


# --------------------------------------------------------------------------- #
# (4) a transport failure on health publish is non-fatal
# --------------------------------------------------------------------------- #
def test_health_transport_failure_is_non_fatal():
    transport = FakeTelemetryTransport(fail=True)          # publish_health raises
    sink = InMemoryTelemetrySink()
    pub = RuntimeTelemetryPublisher(transport, sink)
    d = LoopDriver(_replay_cfg(max_bars=2, tel_interval=0.0), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   telemetry=sink, publisher=pub)
    d.run()
    assert d.state is RuntimeState.STOPPED                 # loop survived
    assert d.bars_processed == 2
    assert transport.published_health == []                # failure swallowed


# --------------------------------------------------------------------------- #
# (9) the health projection is deterministic across identical runs
# --------------------------------------------------------------------------- #
def test_health_projection_is_deterministic_across_runs():
    def run_once():
        sink = InMemoryTelemetrySink()
        transport = FakeTelemetryTransport()
        pub = RuntimeTelemetryPublisher(transport, sink)
        d = LoopDriver(_replay_cfg(max_bars=2, tel_interval=0.0), clock=FakeClock(),
                       provider=FakeMarketDataProvider({"A": bar_series("A", 3, start=_START)}),
                       telemetry=sink, publisher=pub)
        d.run()
        # Drop uptime_s — it is wall-clock operational (§6.5), legitimately varies;
        # every other field is deterministic (trade clock / state / config).
        return [{k: v for k, v in h.items() if k != "uptime_s"}
                for h in transport.published_health]

    assert run_once() == run_once()
