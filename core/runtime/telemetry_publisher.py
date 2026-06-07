"""
Runtime telemetry publishing bridge — the external wire layer (Phase H, §10)
----------------------------------------------------------------------------
This is the **external publishing layer**: it takes the Runtime Observability
Layer's metric snapshot (`core/runtime/metrics.py` — the *sole* metrics source)
and forwards it over an injected wire transport (the ZMQ
`core/messaging/telemetry.py:TelemetryPublisher`, DRIVER_SPECIFICATION.md §10).

It is a **consumer** of telemetry, never a source of truth (ADR-001). It holds
no counters of its own (no second telemetry model, no duplication) — it only
reads `snapshot_source.snapshot()`. Publishing is **best-effort**: a transport
failure is logged and swallowed, never raised, so it can never stop trading
(§10.6; Constitution Principle 2).

Dependency injection, no globals, no singleton state:
- `transport` — anything satisfying the `TelemetryTransport` Protocol
  (`publish_metrics(data)` + `close()`). The real ZMQ `TelemetryPublisher`
  satisfies it structurally; unit tests inject a fake (no socket).
- `snapshot_source` — anything satisfying `SupportsSnapshot` (`snapshot()` →
  dict of `RuntimeMetric` → int); in production this is the **same**
  `InMemoryTelemetrySink` the `LoopDriver` increments, wired once at the
  entry-script layer so the writer (driver) and reader (this bridge) share one
  source.

It has **no reference to the LoopDriver** and reads no driver internals: the
driver merely calls `publish()` on its telemetry cadence and `close()` on
shutdown.

Platform infrastructure only — no strategy, signal, or alpha logic
(PLATFORM_CONSTITUTION Principle 5; ADR-002).
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable

from core.logging import setup_logger
from core.runtime.metrics import RuntimeMetric


@runtime_checkable
class TelemetryTransport(Protocol):
    """
    The wire-transport seam the bridge publishes through. The real
    `core/messaging/telemetry.py:TelemetryPublisher` satisfies this structurally
    (it already exposes both methods) — it is **not** modified to inherit this.
    """

    def publish_metrics(self, data: Dict[str, Any]) -> None: ...

    def publish_health(self, data: Dict[str, Any]) -> None: ...

    def publish_positions(self, data: Dict[str, Any]) -> None: ...

    def publish_log(self, level: str, message: str) -> None: ...

    def close(self) -> None: ...


@runtime_checkable
class SupportsSnapshot(Protocol):
    """A read-only metrics source — e.g. `InMemoryTelemetrySink`."""

    def snapshot(self) -> Dict[RuntimeMetric, int]: ...


class RuntimeTelemetryPublisher:
    """
    Publishes the current runtime metric snapshot over an injected transport.

    `publish()` reads a fresh snapshot, maps each `RuntimeMetric` key to its
    stable string name, and forwards the payload via `transport.publish_metrics`.
    Best-effort: any failure is logged and swallowed; `publish()` returns True on
    a clean send and False when a failure was swallowed.
    """

    def __init__(self, transport: TelemetryTransport,
                 snapshot_source: SupportsSnapshot,
                 logger: Optional[Any] = None):
        self._transport = transport
        self._source = snapshot_source
        self._logger = logger if logger is not None else setup_logger("telemetry_publisher")

    def publish(self) -> bool:
        """Read the current snapshot and publish it. Never raises."""
        try:
            snapshot = self._source.snapshot()
            payload = {metric.value: count for metric, count in snapshot.items()}
            self._transport.publish_metrics(payload)
            return True
        except Exception as exc:  # best-effort: publishing must never stop trading
            self._logger.error("Runtime telemetry publish failed: %s", exc)
            return False

    def publish_health(self, data: Dict[str, Any]) -> bool:
        """
        Publish a node health/liveness projection (§10.5) over the same transport.
        The caller (the LoopDriver, which owns runtime state) builds the payload;
        this bridge only forwards it. Best-effort: never raises; returns True on a
        clean send and False when a failure was swallowed.
        """
        try:
            self._transport.publish_health(data)
            return True
        except Exception as exc:  # best-effort: publishing must never stop trading
            self._logger.error("Runtime telemetry health publish failed: %s", exc)
            return False

    def publish_positions(self, data: Dict[str, Any]) -> bool:
        """
        Publish a positions snapshot (§10.4) over the same transport. The caller
        (the LoopDriver) builds the payload from a read-only position-tracker
        snapshot; this bridge only forwards it. Best-effort: never raises; returns
        True on a clean send and False when a failure was swallowed.
        """
        try:
            self._transport.publish_positions(data)
            return True
        except Exception as exc:  # best-effort: publishing must never stop trading
            self._logger.error("Runtime telemetry positions publish failed: %s", exc)
            return False

    def publish_log(self, level: str, message: str) -> bool:
        """
        Publish an edge-triggered log line (§10) over the same transport — used by
        the driver to surface a `BROKER_ERROR` to telemetry (§8.4), distinct from
        the throttled metrics/health/positions snapshots. Best-effort: never
        raises; returns True on a clean send and False when a failure was swallowed.
        """
        try:
            self._transport.publish_log(level, message)
            return True
        except Exception as exc:  # best-effort: publishing must never stop trading
            self._logger.error("Runtime telemetry log publish failed: %s", exc)
            return False

    def close(self) -> None:
        """Close the underlying transport, tolerating a failing close."""
        try:
            self._transport.close()
        except Exception as exc:
            self._logger.error("Runtime telemetry transport close failed: %s", exc)
