"""
Runtime telemetry counters — observability for the LoopDriver (Phase H)
-----------------------------------------------------------------------
A small, lightweight metrics seam that gives visibility into runtime behavior
WITHOUT changing it. Telemetry here is **observational only** — it is never a
source of truth and never affects an execution, signal, reconciliation, or
recovery decision (ADR-001: the ledger is truth; this is downstream of it).

This is deliberately distinct from `core/messaging/telemetry.py` (the ZMQ
`TelemetryPublisher` wire transport, DRIVER_SPECIFICATION.md §10). This module
is internal in-process counting — no transport, no dashboards, no alerting.

Design (DI, inert default):
- `TelemetrySink` — the injected interface the driver calls. One method,
  `increment(metric, count=1)`.
- `NullTelemetrySink` — the inert default: every increment is a no-op, so the
  LoopDriver runs identically whether or not telemetry is wired.
- `InMemoryTelemetrySink` — accumulates counts in a plain dict; `snapshot()` /
  `get()` read them back. Suitable for tests and a lightweight in-process view.

Best-effort contract: the driver wraps every increment so a faulty sink can
never break the trade path (failure of telemetry must not stop trading). No
globals, no singleton state — a sink is an ordinary injected object.

Platform infrastructure only — no strategy, signal, or alpha logic
(PLATFORM_CONSTITUTION Principle 5; ADR-002).
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict


class RuntimeMetric(Enum):
    """
    The runtime counters the LoopDriver (and MM12.3's GuardedSignalSource)
    expose, grouped: lifecycle, runtime, watchdog, execution, strategy guard.
    Deliberately excludes broker, PnL, and portfolio metrics — out of scope.
    """
    # Lifecycle
    STARTUP_COUNT = "startup_count"
    RECOVERY_COUNT = "recovery_count"
    RECONCILIATION_COUNT = "reconciliation_count"
    STOP_COUNT = "stop_count"
    # Runtime
    BARS_PROCESSED = "bars_processed"
    SIGNALS_RECEIVED = "signals_received"
    SIGNALS_ROUTED = "signals_routed"
    LOOP_ITERATIONS = "loop_iterations"
    # Watchdog
    HEARTBEATS_EMITTED = "heartbeats_emitted"
    STALE_DATA_EVENTS = "stale_data_events"
    KILL_SWITCH_EVENTS = "kill_switch_events"
    # Execution
    EXECUTION_CALLS = "execution_calls"
    # Strategy guard (MM12.3 — GuardedSignalSource, ADR-018/ADR-019)
    STRATEGY_ERRORS = "strategy_errors"
    STRATEGY_QUARANTINE_EVENTS = "strategy_quarantine_events"
    SIGNAL_CONTRACT_REJECTIONS = "signal_contract_rejections"


class TelemetrySink(ABC):
    """
    The injected runtime-telemetry interface. The LoopDriver holds one and bumps
    a counter at each observable runtime event. Implementations must treat
    `increment` as best-effort and side-effect-free with respect to trading.
    """

    @abstractmethod
    def increment(self, metric: RuntimeMetric, count: int = 1) -> None:
        """Add `count` to `metric`'s running total."""


class NullTelemetrySink(TelemetrySink):
    """The inert default: every increment is a no-op (telemetry is optional)."""

    def increment(self, metric: RuntimeMetric, count: int = 1) -> None:
        return None


class InMemoryTelemetrySink(TelemetrySink):
    """
    Accumulates counts in a plain dict. `get` reads one counter (unset = 0);
    `snapshot` returns an isolated copy of the touched counters. No reset,
    export, or thread-safety — kept lightweight by design.
    """

    def __init__(self) -> None:
        self._counts: Dict[RuntimeMetric, int] = {}

    def increment(self, metric: RuntimeMetric, count: int = 1) -> None:
        if not isinstance(metric, RuntimeMetric):
            raise TypeError(
                f"metric must be a RuntimeMetric, got {type(metric).__name__}"
            )
        self._counts[metric] = self._counts.get(metric, 0) + count

    def get(self, metric: RuntimeMetric) -> int:
        return self._counts.get(metric, 0)

    def snapshot(self) -> Dict[RuntimeMetric, int]:
        return dict(self._counts)
