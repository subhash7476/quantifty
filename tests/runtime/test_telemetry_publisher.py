"""
Unit tests for the Phase H ZMQ telemetry publishing bridge
(core/runtime/telemetry_publisher.py).

The bridge is the external publishing layer: it CONSUMES the Runtime
Observability Layer's metric snapshot (the sole metrics source) and forwards it
over an injected wire transport. It is observation only — best-effort, never a
source of truth, never able to stop trading (ADR-001, §10.6).

Proven here:
- a metric snapshot is published to the transport, with RuntimeMetric keys
  mapped to their stable string names;
- the bridge reads a FRESH snapshot each publish (no caching / no duplicate
  counter model — the Observability Layer stays the sole source);
- a transport failure is swallowed (publish returns False, never raises);
- close() delegates to the transport and is also failure-tolerant;
- the real core/messaging TelemetryPublisher structurally satisfies the
  transport contract the bridge calls (publish_metrics + close) — no socket;
- the module imports no strategy code (ADR-002).

No real network: a FakeTelemetryTransport double records calls.
"""

import ast
from pathlib import Path

from core.runtime.metrics import InMemoryTelemetrySink, RuntimeMetric
from core.runtime.telemetry_publisher import RuntimeTelemetryPublisher

from _doubles import FakeTelemetryTransport


def _sink_with(**counters):
    sink = InMemoryTelemetrySink()
    for name, count in counters.items():
        sink.increment(RuntimeMetric[name], count)
    return sink


# --------------------------------------------------------------------------- #
# (1) a metric snapshot is published, keyed by stable metric names
# --------------------------------------------------------------------------- #
def test_publish_sends_metric_snapshot_to_transport():
    transport = FakeTelemetryTransport()
    sink = _sink_with(STARTUP_COUNT=1, BARS_PROCESSED=3, EXECUTION_CALLS=2)
    pub = RuntimeTelemetryPublisher(transport=transport, snapshot_source=sink)

    assert pub.publish() is True
    assert transport.published == [
        {"startup_count": 1, "bars_processed": 3, "execution_calls": 2}
    ]


def test_publish_maps_runtime_metric_keys_to_strings():
    transport = FakeTelemetryTransport()
    pub = RuntimeTelemetryPublisher(transport, _sink_with(LOOP_ITERATIONS=4))
    pub.publish()
    (payload,) = transport.published
    assert list(payload.keys()) == ["loop_iterations"]   # str, not the enum


# --------------------------------------------------------------------------- #
# (empty) an empty snapshot still publishes an empty payload
# --------------------------------------------------------------------------- #
def test_publish_empty_snapshot_sends_empty_payload():
    transport = FakeTelemetryTransport()
    pub = RuntimeTelemetryPublisher(transport, InMemoryTelemetrySink())
    assert pub.publish() is True
    assert transport.published == [{}]


# --------------------------------------------------------------------------- #
# (fresh read) the bridge reads a fresh snapshot each publish — no caching
# --------------------------------------------------------------------------- #
def test_publish_reads_a_fresh_snapshot_each_call():
    transport = FakeTelemetryTransport()
    sink = InMemoryTelemetrySink()
    pub = RuntimeTelemetryPublisher(transport, sink)

    sink.increment(RuntimeMetric.BARS_PROCESSED, 1)
    pub.publish()
    sink.increment(RuntimeMetric.BARS_PROCESSED, 1)
    pub.publish()

    assert transport.published == [{"bars_processed": 1}, {"bars_processed": 2}]


# --------------------------------------------------------------------------- #
# (4) a transport failure is swallowed — publish returns False, never raises
# --------------------------------------------------------------------------- #
def test_publish_swallows_transport_failure_and_returns_false():
    transport = FakeTelemetryTransport(fail=True)
    pub = RuntimeTelemetryPublisher(transport, _sink_with(BARS_PROCESSED=1))
    assert pub.publish() is False          # no exception escapes


# --------------------------------------------------------------------------- #
# close() delegates to the transport and tolerates a failing close
# --------------------------------------------------------------------------- #
def test_close_delegates_to_transport():
    transport = FakeTelemetryTransport()
    RuntimeTelemetryPublisher(transport, InMemoryTelemetrySink()).close()
    assert transport.closed == 1


def test_close_swallows_transport_failure():
    transport = FakeTelemetryTransport(fail_on_close=True)
    pub = RuntimeTelemetryPublisher(transport, InMemoryTelemetrySink())
    pub.close()                            # must not raise


# --------------------------------------------------------------------------- #
# (contract) the real ZMQ TelemetryPublisher satisfies the transport seam
# --------------------------------------------------------------------------- #
def test_messaging_telemetry_publisher_satisfies_transport_contract():
    # The bridge calls publish_metrics(data) + close(); prove the real wire
    # transport exposes both (structural DI contract), without opening a socket.
    from core.messaging.telemetry import TelemetryPublisher
    assert callable(getattr(TelemetryPublisher, "publish_metrics", None))
    assert callable(getattr(TelemetryPublisher, "close", None))


# --------------------------------------------------------------------------- #
# (ADR-002) the bridge module imports no strategy code
# --------------------------------------------------------------------------- #
def test_publisher_module_has_no_forbidden_strategy_imports():
    src = (Path(__file__).resolve().parents[2]
           / "core" / "runtime" / "telemetry_publisher.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    forbidden = ("strategies", "runner", "backtest", "state", "models", "ftmo")
    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        for mod in modules:
            assert not any(part in forbidden for part in mod.split(".")), mod
