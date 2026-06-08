"""
RuntimeEventJournal — durable operational audit trail
-----------------------------------------------------
An append-only, one-JSON-object-per-line record of *what happened in the running
process and why* (DRIVER_SPECIFICATION.md section 15). It complements — and is
deliberately distinct from — the heartbeat snapshot (section 9), the live
telemetry stream (section 10), and the ledger (ADR-001):

    heartbeat  -> "Is the process alive?"   (latest-only snapshot)
    telemetry  -> "What is it seeing?"       (ephemeral, lossy stream)
    journal    -> "What happened, and why?"  (durable, ordered history)

Authority boundary (section 15.7, non-negotiable):
- The journal is APPEND-ONLY and is NEVER a source of position truth. It records
  *events about* trading, not authoritative state. This class therefore exposes
  no read/load/reconstruct API — only writes.
- The ledger (ExecutionHandler trackers + persistence) remains the sole
  authoritative trading record (ADR-001). Recovery restores from the ledger,
  never from this file.

Failure policy (section 15.6): a failed append is logged and swallowed — writing
the journal must never break the trade path (the same fire-and-forget principle
as telemetry, section 12.4).

Edge-triggering (section 15.4) — writing each state-transition/incident once per
occurrence rather than per tick — is the *caller's* (LoopDriver's) responsibility;
this class appends exactly what it is told, in call order.

Platform infrastructure only — no strategy, signal, or alpha logic
(PLATFORM_CONSTITUTION Principle 5; ADR-002).
"""

import json
import os
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional
from zoneinfo import ZoneInfo

from core.logging import setup_logger

_IST = ZoneInfo("Asia/Kolkata")


class Severity(Enum):
    """Event severity (DRIVER_SPECIFICATION.md section 15.3)."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class EventType(Enum):
    """
    The minimum required runtime event types (DRIVER_SPECIFICATION.md
    section 15.4). The LoopDriver may add more, but must emit at least these.
    """
    STARTUP = "STARTUP"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    RECONCILIATION_PASS = "RECONCILIATION_PASS"
    RECONCILIATION_FAIL = "RECONCILIATION_FAIL"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"
    KILL_SWITCH_ACTIVATED = "KILL_SWITCH_ACTIVATED"
    WATCHDOG_STALE_DATA = "WATCHDOG_STALE_DATA"
    BROKER_ERROR = "BROKER_ERROR"
    TELEMETRY_FAILURE = "TELEMETRY_FAILURE"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    # MM.4 instrument-master readiness gate (MASTER_MATERIALIZATION_POLICY.md §5).
    # UNAVAILABLE refuses live F&O start (BLOCK); STALE records a 1-day-stale
    # start (WARN) — durably, since telemetry is lossy and this is audit-relevant.
    INSTRUMENT_MASTER_UNAVAILABLE = "INSTRUMENT_MASTER_UNAVAILABLE"
    INSTRUMENT_MASTER_STALE = "INSTRUMENT_MASTER_STALE"


# Normative default severity per event type (section 15.4). BROKER_ERROR is
# "WARNING|CRITICAL" in the spec; it defaults to WARNING and the caller raises
# it to CRITICAL (e.g. a startup handshake failure) via the severity override.
_DEFAULT_SEVERITY: Dict["EventType", "Severity"] = {
    EventType.STARTUP: Severity.INFO,
    EventType.RECOVERY_STARTED: Severity.INFO,
    EventType.RECOVERY_COMPLETED: Severity.INFO,
    EventType.RECONCILIATION_PASS: Severity.INFO,
    EventType.RECONCILIATION_FAIL: Severity.CRITICAL,
    EventType.RUNNING: Severity.INFO,
    EventType.PAUSED: Severity.WARNING,
    EventType.RESUMED: Severity.INFO,
    EventType.KILL_SWITCH_ACTIVATED: Severity.CRITICAL,
    EventType.WATCHDOG_STALE_DATA: Severity.CRITICAL,
    EventType.BROKER_ERROR: Severity.WARNING,
    EventType.TELEMETRY_FAILURE: Severity.WARNING,
    EventType.STOPPING: Severity.INFO,
    EventType.STOPPED: Severity.INFO,
    EventType.INSTRUMENT_MASTER_UNAVAILABLE: Severity.CRITICAL,
    EventType.INSTRUMENT_MASTER_STALE: Severity.WARNING,
}


class RuntimeEventJournal:
    """
    Append-only writer for logs/runtime_events.jsonl (section 15.2).

    Usage:
        journal = RuntimeEventJournal()
        journal.record(EventType.STARTUP, "driver starting",
                       metadata={"mode": "LIVE", "symbols": ["NSE_INDEX|Nifty 50"]})

    Each record() call appends exactly one JSON object (one line) and returns the
    record it wrote (for the caller's convenience and for tests). Timestamps are
    tz-aware IST wall-clock — operational time, not the deterministic trade Clock
    (section 6.5).
    """

    def __init__(
        self,
        path: str = "logs/runtime_events.jsonl",
        source_component: str = "LoopDriver",
        now: Optional[Callable[[], datetime]] = None,
    ):
        """
        Args:
            path: target JSONL file (created on first append; parent dir made).
            source_component: default emitter name stamped on records when the
                caller does not override it (e.g. "RuntimeWatchdog",
                "ReconciliationEngine", "ExecutionHandler").
            now: injectable wall-clock for the timestamp; defaults to IST now.
                Wall-clock by design (section 6.5) — never the trade Clock.
        """
        self._path = path
        self._default_source = source_component
        self._now = now if now is not None else (lambda: datetime.now(_IST))
        self._logger = setup_logger("event_journal")

    def record(
        self,
        event_type: EventType,
        message: str,
        *,
        severity: Optional[Severity] = None,
        source_component: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Append one event to the journal and return the written record.

        Args:
            event_type: one of EventType (section 15.4).
            message: human-readable one-line description.
            severity: overrides the event type's default severity (section 15.4);
                e.g. raise a BROKER_ERROR to CRITICAL on a startup handshake fail.
            source_component: overrides the journal's default emitter name.
            metadata: free-form structured context; defaults to {}.

        Write failures are logged and swallowed (section 15.6) — the journal must
        never break the trade path.
        """
        if not isinstance(event_type, EventType):
            raise TypeError(
                f"event_type must be an EventType, got {type(event_type).__name__}"
            )
        if severity is not None and not isinstance(severity, Severity):
            raise TypeError(
                f"severity must be a Severity, got {type(severity).__name__}"
            )

        record: Dict[str, Any] = {
            "timestamp": self._now().isoformat(),
            "event_type": event_type.value,
            "severity": (severity or _DEFAULT_SEVERITY[event_type]).value,
            "source_component": source_component or self._default_source,
            "message": message,
            "metadata": metadata if metadata is not None else {},
        }

        self._append(record)
        return record

    def _append(self, record: Dict[str, Any]) -> None:
        """
        Append a single newline-terminated JSON line in append mode (section
        15.2). Never rewrites or truncates. Errors are logged, not raised
        (section 15.6). `default=str` keeps a non-serializable metadata value
        from ever breaking the trade path.
        """
        line = json.dumps(record, default=str)
        try:
            directory = os.path.dirname(self._path) or "."
            os.makedirs(directory, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as exc:
            self._logger.error("Runtime event journal append failed: %s", exc)
