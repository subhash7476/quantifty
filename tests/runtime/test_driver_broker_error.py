"""
Unit tests for LoopDriver Phase G — per-signal exception isolation (§8.4).

`ExecutionHandler.process_signal` may raise on a hard rule violation (e.g.
`enforce_risk_clearance`) or a broker fault. §8.4 requires that **one signal's
failure does not kill the loop**: the driver catches it, logs at error, emits a
`BROKER_ERROR` journal event (durable, §15.4), surfaces a telemetry log line
(§10), and continues to the next signal/bar. The raised exception is never
swallowed silently (Constitution §6).

Proven here:
1. a raising process_signal does NOT kill the loop — it survives, a later signal
   still routes, and the run ends STOPPED normally (the headline guarantee);
2. a failure mid-bar still routes the remaining signals in that same bar;
3. the failure is journaled as BROKER_ERROR with `error` + `signal_id` metadata,
   at WARNING severity (runtime default);
4. an explicit `metadata['signal_id']` is used when present;
5. the failure is surfaced as an edge-triggered telemetry log line (§10);
6. the loop survives even with no journal and no publisher wired;
7. EXECUTION_CALLS is not metered on a failed call (SIGNALS_ROUTED still is);
8. a publisher whose publish_log raises still cannot break the loop.

No real network / real handler: fakes from _doubles; a raising process_signal is
driven by `FakeExecutionHandler(raise_on=...)`.
"""

import json
from datetime import datetime

import pytz

from core.events import SignalEvent, SignalType
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal
from core.runtime.metrics import InMemoryTelemetrySink, RuntimeMetric
from core.runtime.telemetry_publisher import RuntimeTelemetryPublisher

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, FakeTelemetryTransport, bar_series,
                      make_bar, make_signal)

_UTC = pytz.UTC
_START = datetime(2026, 6, 5, 9, 15, tzinfo=_UTC)


def _replay_cfg(max_bars=None, tel_interval=0.0):
    return DriverConfig(mode=Mode.REPLAY, symbols=["A"], max_bars=max_bars,
                        telemetry_interval_s=tel_interval)


def _journal_lines(tmp_path):
    return [json.loads(l)
            for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]


# --------------------------------------------------------------------------- #
# (1) the headline: a raising process_signal does NOT kill the loop
# --------------------------------------------------------------------------- #
def test_raising_process_signal_does_not_kill_the_loop():
    handler = FakeExecutionHandler(raise_on="BOOM")
    source = FakeSignalSource([[make_signal("BOOM")], [make_signal("OK")]])
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source, execution=handler)
    d.run()

    assert d.state is RuntimeState.STOPPED          # ended cleanly, not via exception
    assert d.bars_processed == 2                     # the loop kept going past the failure
    routed_symbols = [s.symbol for s, _ in handler.routed]
    assert routed_symbols == ["OK"]                  # later signal routed; BOOM did not


# --------------------------------------------------------------------------- #
# (2) a failure mid-bar still routes the remaining signals in that bar
# --------------------------------------------------------------------------- #
def test_failure_does_not_skip_later_signals_in_same_bar():
    handler = FakeExecutionHandler(raise_on="BOOM")
    sig_boom, sig_ok = make_signal("BOOM"), make_signal("OK")
    d = LoopDriver(_replay_cfg(), execution=handler)
    d.start()                                        # → RUNNING (lifecycle only)
    d._dispatch_signals([sig_boom, sig_ok], make_bar("A", close=99.0))

    assert handler.routed == [(sig_ok, 99.0)]        # BOOM failed, OK still routed


# --------------------------------------------------------------------------- #
# (3) the failure is journaled BROKER_ERROR with error + signal_id, WARNING
# --------------------------------------------------------------------------- #
def test_broker_error_journaled_with_metadata_and_warning_severity(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(raise_on="BOOM")
    source = FakeSignalSource([[make_signal("BOOM")]])
    d = LoopDriver(_replay_cfg(max_bars=1), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 2)}),
                   source=source, execution=handler, journal=journal)
    d.run()

    broker_errors = [r for r in _journal_lines(tmp_path)
                     if r["event_type"] == "BROKER_ERROR"]
    assert len(broker_errors) == 1
    rec = broker_errors[0]
    assert rec["severity"] == "WARNING"
    assert "boom" in rec["metadata"]["error"].lower()
    assert rec["metadata"]["signal_id"]              # an identifier is present


# --------------------------------------------------------------------------- #
# (4) an explicit metadata['signal_id'] is preferred when present
# --------------------------------------------------------------------------- #
def test_broker_error_uses_explicit_signal_id(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    sig = SignalEvent(strategy_id="strat", symbol="BOOM", timestamp=_START,
                      signal_type=SignalType.BUY, confidence=1.0,
                      metadata={"signal_id": "SIG-7"})
    handler = FakeExecutionHandler(raise_on="BOOM")
    d = LoopDriver(_replay_cfg(), execution=handler, journal=journal)
    d.start()
    d._dispatch_signals([sig], make_bar("A", close=10.0))

    rec = [r for r in _journal_lines(tmp_path) if r["event_type"] == "BROKER_ERROR"][0]
    assert rec["metadata"]["signal_id"] == "SIG-7"


# --------------------------------------------------------------------------- #
# (5) the failure is surfaced as an edge-triggered telemetry log line (§10)
# --------------------------------------------------------------------------- #
def test_broker_error_published_as_telemetry_log_line():
    sink = InMemoryTelemetrySink()
    transport = FakeTelemetryTransport()
    pub = RuntimeTelemetryPublisher(transport, sink)
    handler = FakeExecutionHandler(raise_on="BOOM")
    source = FakeSignalSource([[make_signal("BOOM")]])
    d = LoopDriver(_replay_cfg(max_bars=1), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 2)}),
                   source=source, execution=handler, telemetry=sink, publisher=pub)
    d.run()

    assert len(transport.published_logs) == 1
    level, message = transport.published_logs[0]
    assert level == "ERROR"
    assert "BROKER_ERROR" in message


# --------------------------------------------------------------------------- #
# (6) the loop survives a failure with no journal and no publisher wired
# --------------------------------------------------------------------------- #
def test_loop_survives_broker_error_without_journal_or_publisher():
    handler = FakeExecutionHandler(raise_on="BOOM")
    source = FakeSignalSource([[make_signal("BOOM")], [make_signal("OK")]])
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source, execution=handler)   # no journal, no publisher
    d.run()

    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 2
    assert [s.symbol for s, _ in handler.routed] == ["OK"]


# --------------------------------------------------------------------------- #
# (7) EXECUTION_CALLS is not metered on a failed call; SIGNALS_ROUTED still is
# --------------------------------------------------------------------------- #
def test_execution_calls_not_metered_on_failed_call():
    sink = InMemoryTelemetrySink()
    handler = FakeExecutionHandler(raise_on="BOOM")
    d = LoopDriver(_replay_cfg(), execution=handler, telemetry=sink)
    d.start()
    d._dispatch_signals([make_signal("BOOM")], make_bar("A", close=10.0))

    snap = sink.snapshot()
    assert snap.get(RuntimeMetric.SIGNALS_ROUTED) == 1
    assert snap.get(RuntimeMetric.EXECUTION_CALLS, 0) == 0


# --------------------------------------------------------------------------- #
# (8) a publisher whose publish_log raises still cannot break the loop
# --------------------------------------------------------------------------- #
class _LogRaisingPublisher:
    """publish/health/positions are inert; publish_log explodes (hostile)."""

    def publish(self):
        return True

    def publish_health(self, data):
        return True

    def publish_positions(self, data):
        return True

    def publish_log(self, level, message):
        raise RuntimeError("log publish exploded")

    def close(self):
        return None


def test_raising_publish_log_does_not_break_the_loop():
    handler = FakeExecutionHandler(raise_on="BOOM")
    source = FakeSignalSource([[make_signal("BOOM")], [make_signal("OK")]])
    d = LoopDriver(_replay_cfg(max_bars=2, tel_interval=0.0), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source, execution=handler,
                   telemetry=InMemoryTelemetrySink(), publisher=_LogRaisingPublisher())
    d.run()

    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 2
    assert [s.symbol for s, _ in handler.routed] == ["OK"]
