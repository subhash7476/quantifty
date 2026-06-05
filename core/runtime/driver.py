"""
LoopDriver — the deterministic runtime orchestrator
----------------------------------------------------
Phases A–B (this file's current scope): the **lifecycle state machine** (§3)
plus **journal emission on transitions** (§15). It models the six runtime
states and the legal transitions between them, rejects illegal transitions, and
records each lifecycle transition to the RuntimeEventJournal. It does NOT yet
pull market data, advance the clock, pull signals, route to the
ExecutionHandler, drive the RuntimeWatchdog, publish telemetry, or run
recovery/reconciliation — those arrive in later phases
(docs/LOOPDRIVER_IMPLEMENTATION_PLAN.md).

Governing law:
- ADR-003 (Deterministic Processing) / ADR-006 (sole runtime orchestrator):
  the LoopDriver is the single, neutral orchestrator. This file holds no
  strategy, signal, or alpha logic and imports no strategy code (ADR-002).
- §3.2 transitions (verbatim edges):
    construct()            -> STARTUP
    STARTUP   -> RECOVERY  (begin the recovery sub-phase)
    STARTUP   -> RUNNING   (validation passed)            [start]
    RECOVERY  -> RUNNING   (recovery + validation passed) [start]
    STARTUP   -> STOPPED   (refuse to start)              [abort_startup]
    RECOVERY  -> STOPPED   (refuse to start)              [abort_startup]
    RUNNING   -> PAUSED    [pause]
    PAUSED    -> RUNNING   [resume]
    RUNNING   -> STOPPING  [stop]
    PAUSED    -> STOPPING  [stop]
    STOPPING  -> STOPPED   (loop drained)                 [finalize_stop]

A kill-switch trip is deliberately **not** a state: per §3.2 the loop keeps
running (kill-switched-but-running) so heartbeat/telemetry continue. It will be
handled in the execution/watchdog phases, not modeled here.

Journal emission (§15, Phase B): each successful lifecycle transition emits one
event (STARTUP on construction, RUNNING, PAUSED, RESUMED, STOPPING, STOPPED).
Emission happens only after _transition() succeeds, so an illegal transition
(which raises) records nothing — edge-triggered, once per occurrence (§15.4).
The journal is optional: when absent, emission is a no-op (headless/unit use).
RECOVERY-phase events (RECOVERY_STARTED/COMPLETED, RECONCILIATION_*) are added
with the recovery gate in a later phase, not here.
"""

from enum import Enum
from typing import AbstractSet, Optional

from core.runtime.config import DriverConfig
from core.runtime.event_journal import EventType, RuntimeEventJournal


class RuntimeState(Enum):
    """The six LoopDriver lifecycle states (DRIVER_SPECIFICATION.md §3.1)."""
    STARTUP = "STARTUP"
    RECOVERY = "RECOVERY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


class InvalidStateTransition(RuntimeError):
    """
    Raised when a lifecycle transition is attempted from a state that does not
    permit it (DRIVER_SPECIFICATION.md §3.2). Carries the offending current and
    target states for diagnostics.
    """

    def __init__(self, current: RuntimeState, target: RuntimeState):
        self.current = current
        self.target = target
        super().__init__(
            f"Illegal LoopDriver transition: {current.value} -> {target.value}"
        )


class LoopDriver:
    """
    Single-threaded runtime orchestrator (Phases A–B: lifecycle + journal).

    Construction places the driver in STARTUP and records the STARTUP event.
    From there the lifecycle verbs drive the §3.2 state machine; each verb
    enforces its legal source states, then records its event. No verb performs
    IO beyond the (optional) journal in this phase.
    """

    def __init__(self, config: DriverConfig,
                 journal: Optional[RuntimeEventJournal] = None):
        self._config = config
        self._journal = journal
        self._state = RuntimeState.STARTUP
        # The process has entered STARTUP (§3.1); record it (§15.4).
        self._emit(
            EventType.STARTUP,
            "LoopDriver constructed; entering STARTUP",
            {"mode": config.mode.value, "symbols": list(config.symbols)},
        )

    @property
    def state(self) -> RuntimeState:
        """The current lifecycle state."""
        return self._state

    @property
    def config(self) -> DriverConfig:
        """The driver's immutable runtime configuration."""
        return self._config

    def _transition(self, target: RuntimeState,
                    allowed_from: AbstractSet[RuntimeState]) -> None:
        """
        Move to `target` iff the current state is in `allowed_from`; otherwise
        raise InvalidStateTransition. The single chokepoint for all state
        changes — every lifecycle verb goes through here.
        """
        if self._state not in allowed_from:
            raise InvalidStateTransition(self._state, target)
        self._state = target

    def _emit(self, event_type: EventType, message: str,
              metadata: Optional[dict] = None) -> None:
        """
        Record a lifecycle event to the journal if one is attached (§15).
        No-op when no journal is injected. Called only after a successful
        transition, so illegal transitions (which raise in _transition) emit
        nothing — edge-triggered, once per occurrence (§15.4).
        """
        if self._journal is not None:
            self._journal.record(event_type, message, metadata=metadata)

    # -- Lifecycle verbs (each edge in §3.2) -------------------------------- #

    def enter_recovery(self) -> None:
        """
        STARTUP -> RECOVERY: begin the recovery sub-phase of startup (§3.1).
        Recovery-phase journal events are added with the recovery gate in a
        later phase; this phase records nothing here.
        """
        self._transition(RuntimeState.RECOVERY, {RuntimeState.STARTUP})

    def start(self) -> None:
        """
        STARTUP|RECOVERY -> RUNNING: startup validation passed (§3.2). In later
        phases this is gated by recovery + reconciliation (§11); in this phase it
        is the bare transition plus the RUNNING event.
        """
        self._transition(
            RuntimeState.RUNNING,
            {RuntimeState.STARTUP, RuntimeState.RECOVERY},
        )
        self._emit(EventType.RUNNING, "driver running")

    def pause(self) -> None:
        """RUNNING -> PAUSED: suspend signal routing without going blind (§3.1)."""
        self._transition(RuntimeState.PAUSED, {RuntimeState.RUNNING})
        self._emit(EventType.PAUSED, "driver paused")

    def resume(self) -> None:
        """PAUSED -> RUNNING: resume routing."""
        self._transition(RuntimeState.RUNNING, {RuntimeState.PAUSED})
        self._emit(EventType.RESUMED, "driver resumed")

    def stop(self) -> None:
        """
        RUNNING|PAUSED -> STOPPING: begin a clean shutdown (stop requested,
        replay exhausted, or max_bars). The loop then drains before reaching
        STOPPED via finalize_stop() (§3.2).
        """
        self._transition(
            RuntimeState.STOPPING,
            {RuntimeState.RUNNING, RuntimeState.PAUSED},
        )
        self._emit(EventType.STOPPING, "driver stopping")

    def abort_startup(self) -> None:
        """
        STARTUP|RECOVERY -> STOPPED: refuse to start (§3.2, §11.4). The driver
        never trades on an unvalidated/inconsistent ledger; in later phases this
        is the failed-startup-gate path (which will add the RECONCILIATION_FAIL
        context before this STOPPED event).
        """
        self._transition(
            RuntimeState.STOPPED,
            {RuntimeState.STARTUP, RuntimeState.RECOVERY},
        )
        self._emit(EventType.STOPPED, "driver refused to start")

    def finalize_stop(self) -> None:
        """STOPPING -> STOPPED: shutdown complete; terminal state (§3.1)."""
        self._transition(RuntimeState.STOPPED, {RuntimeState.STOPPING})
        self._emit(EventType.STOPPED, "driver stopped")
