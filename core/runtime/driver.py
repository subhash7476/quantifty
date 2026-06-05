"""
LoopDriver — the deterministic runtime orchestrator
----------------------------------------------------
Phases A–D (this file's current scope):
- A: the lifecycle state machine (§3) — six states + legal §3.2 transitions.
- B: journal emission on transitions (§15).
- C: the **tick loop** — pull bars from a MarketDataProvider, advance the Clock
  from each bar's timestamp, and count, until exhaustion / max_bars / stop()
  (§4 event flow, §6 clock, §7 market data).
- D: the **SignalSource pull** — call source.on_bar(bar) once per bar (after the
  clock advance, §7.2) and collect the returned signals in list order; run the
  source's on_start/on_stop lifecycle hooks (§5.2). Signals are counted, **not
  routed** — execution arrives in Phase E.

It does NOT yet route signals to the ExecutionHandler, drive the
RuntimeWatchdog, publish telemetry, or run recovery/reconciliation — those
arrive in later phases (docs/LOOPDRIVER_IMPLEMENTATION_PLAN.md). The loop is
still deliberately **inert**: it advances time, pulls signals, and counts, but
takes no trading action.

Governing law:
- ADR-003 (Deterministic Processing) / ADR-006 (sole runtime orchestrator):
  single thread, single loop, single fixed ordering. Time is data-driven — the
  clock is advanced from each bar's timestamp BEFORE any per-bar work, so live
  and replay traverse identical code. This file holds no strategy/signal/alpha
  logic and imports no strategy code (ADR-002).
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
running (kill-switched-but-running). It is handled in the execution/watchdog
phases, not modeled here.
"""

from enum import Enum
from typing import AbstractSet, Optional

from core.clock import Clock
from core.database.providers.base import MarketDataProvider
from core.runtime.config import DriverConfig
from core.runtime.event_journal import EventType, RuntimeEventJournal
from core.runtime.signal_source import SignalSource


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
    Single-threaded runtime orchestrator (Phases A–C: lifecycle + journal + loop).

    Construction places the driver in STARTUP and records the STARTUP event.
    run() drives the deterministic tick loop until exhaustion, max_bars, or
    stop(); the lifecycle verbs enforce the §3.2 state machine. The loop is
    inert in this phase — it advances the clock and counts bars but takes no
    trading action.

    Collaborators are injected; clock and provider are required only by run()
    (a lifecycle-only driver may be constructed without them). The journal is
    optional everywhere (no-op when absent).
    """

    def __init__(self, config: DriverConfig,
                 clock: Optional[Clock] = None,
                 provider: Optional[MarketDataProvider] = None,
                 journal: Optional[RuntimeEventJournal] = None,
                 source: Optional[SignalSource] = None):
        self._config = config
        self._clock = clock
        self._provider = provider
        self._journal = journal
        self._source = source
        self._state = RuntimeState.STARTUP
        self._bars_processed = 0
        self._signals_pulled = 0
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

    @property
    def bars_processed(self) -> int:
        """Count of bars consumed by the loop so far."""
        return self._bars_processed

    @property
    def signals_pulled(self) -> int:
        """Count of signals collected from the source so far (Phase D)."""
        return self._signals_pulled

    # -- Transition + journal plumbing -------------------------------------- #

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

    # -- Phase C: the deterministic tick loop ------------------------------- #

    def run(self) -> None:
        """
        Drive the deterministic loop until data exhaustion, the max_bars guard,
        or a stop() request, then shut down cleanly to STOPPED.

        Per tick (§4.1): for each configured symbol in fixed order, pull the
        next bar and — if one arrives — advance the clock to its timestamp
        BEFORE any per-bar work (§6, ADR-003), then count it. When no symbol
        yields a bar, the loop either ends (replay exhausted) or waits one
        poll_interval (live). Phase C takes no trading action on the bar.

        Requires an injected clock and market-data provider; raises otherwise.
        The finally block guarantees a clean STOPPING -> STOPPED shutdown on
        every exit path (normal end, stop(), or an unexpected error).
        """
        if self._clock is None or self._provider is None:
            raise RuntimeError(
                "LoopDriver.run() requires an injected clock and market-data provider"
            )

        if self._state in (RuntimeState.STARTUP, RuntimeState.RECOVERY):
            self.start()

        # Source warmup before the loop pulls any bar (§5.2). No context is
        # injected — the driver hands the source nothing that exposes the
        # ledger/broker/handler (§5.4).
        if self._source is not None:
            self._source.on_start()

        try:
            while self._state in (RuntimeState.RUNNING, RuntimeState.PAUSED):
                if self._at_max_bars():
                    break
                advanced = self._tick()
                if not advanced:
                    if self._is_exhausted():
                        break
                    # Live: no new bar yet — wait one poll interval (§7.3).
                    self._clock.sleep(self._config.poll_interval_s)
        finally:
            if self._state in (RuntimeState.RUNNING, RuntimeState.PAUSED):
                self.stop()
            if self._state is RuntimeState.STOPPING:
                self.finalize_stop()
            # Source teardown once, on every exit path (§5.2 on_stop).
            if self._source is not None:
                self._source.on_stop()

    def _tick(self) -> bool:
        """
        Pull one bar per configured symbol (fixed order); advance the clock,
        pull signals, and count each bar that arrives. Returns True if any symbol
        yielded a bar. Phase D pulls signals but does not route them — no
        execution, watchdog, or telemetry yet.
        """
        advanced = False
        for symbol in self._config.symbols:
            if self._at_max_bars():
                break
            bar = self._provider.get_next_bar(symbol)
            if bar is None:
                continue
            # Advance time from the bar BEFORE any per-bar work (§6, ADR-003).
            self._clock.set_time(bar.timestamp)
            # Pull signals after the clock advance, in list order (§5.2, §7.2).
            if self._source is not None:
                self._dispatch_signals(self._source.on_bar(bar), bar)
            self._bars_processed += 1
            advanced = True
        return advanced

    def _dispatch_signals(self, signals, bar) -> None:
        """
        Handle the signals pulled for one bar. Phase D only **counts** them
        (signals are pulled but not routed); the list is taken verbatim — its
        order IS the routing order and must not be re-ranked (§5.2). Phase E
        fills this seam in with ExecutionHandler routing (§8).
        """
        self._signals_pulled += len(signals)

    def _at_max_bars(self) -> bool:
        """True once the configured max_bars guard is reached (§13)."""
        return (self._config.max_bars is not None
                and self._bars_processed >= self._config.max_bars)

    def _is_exhausted(self) -> bool:
        """
        True when no configured symbol has more data. In replay this ends the
        run; in live the provider keeps reporting availability, so this stays
        False and the loop polls instead (§7.3/§7.4).
        """
        return not any(
            self._provider.is_data_available(s) for s in self._config.symbols
        )
