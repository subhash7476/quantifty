"""
LoopDriver — the deterministic runtime orchestrator
----------------------------------------------------
Phases A–H + H-ZMQ (this file's current scope):
- A: the lifecycle state machine (§3) — six states + legal §3.2 transitions.
- B: journal emission on transitions (§15).
- C: the **tick loop** — pull bars from a MarketDataProvider, advance the Clock
  from each bar's timestamp, and count, until exhaustion / max_bars / stop()
  (§4 event flow, §6 clock, §7 market data).
- D: the **SignalSource pull** — call source.on_bar(bar) once per bar (after the
  clock advance, §7.2) and collect the returned signals in list order; run the
  source's on_start/on_stop lifecycle hooks (§5.2). Signals are counted, **not
  routed** — execution arrives in the execution phase.
- W: the **RuntimeWatchdog drive** (§9, ADR-004) — record_bar() per processed
  bar, check_data_staleness() + write_heartbeat(bars) once per tick after the
  symbol sweep, all **live-mode only** (§9.5). A stale-feed trip is recorded
  edge-triggered as WATCHDOG_STALE_DATA + KILL_SWITCH_ACTIVATED. The watchdog
  owns its kill-switch action against its own ExecutionHandler; the driver only
  drives it and observes its public health flag.
- F: the **startup gate / recovery** (§11, ADR-001) — when an ExecutionHandler is
  injected, validate before RUNNING: confirm recovery (reuse _replay_state, never
  re-restore) → RECOVERY_STARTED/RECOVERY_COMPLETED; reconcile the restored
  ledger against broker truth → RECONCILIATION_PASS, or refuse to start
  (RECONCILIATION_FAIL → STOPPED) on divergence. LIVE mode requires a handler;
  the no-handler path is replay/inert/test only (PHASE_F_STARTUP_GATE_PLAN §3.1).
- G: the **execution routing** (§8, ADR-005/006) — each pulled SignalEvent is
  forwarded, in list order, to the canonical ExecutionHandler entry point
  process_signal(signal, current_price=bar.close). Routing is gated on handler
  presence and the RUNNING state (PAUSED suspends it, §3.1). The driver is the
  sole runtime caller of process_signal; it routes only — sizing/risk/orders/
  fills stay the handler's (ADR-005). Per-signal exception isolation (§8.4,
  BROKER_ERROR) and telemetry are deliberately NOT in this slice.

- H: **runtime telemetry** (Phase H) — an injected, inert-by-default TelemetrySink
  (core/runtime/metrics.py) is fed in-scope runtime counters (lifecycle, runtime,
  watchdog, execution) at each observable event via _meter(). Telemetry is
  **observation only**: it never affects an execution/signal/reconciliation/
  recovery decision, is never a source of truth, and a faulty sink can never stop
  the loop (every increment is best-effort, swallowed-and-logged).
- H (ZMQ): **external telemetry publishing** (§10) — an optional injected
  RuntimeTelemetryPublisher (core/runtime/telemetry_publisher.py) is driven once
  per tick via _drive_telemetry(), throttled to telemetry_interval_s by the
  deterministic clock (§10.2). On each cadence it publishes two things over the ZMQ
  wire transport: the metric snapshot (§10.3 — *consuming* the Observability Layer,
  the sole counter source) and a node **health projection** (§10.5, _build_health):
  state / data_healthy / market_open / uptime / last_tick — a read-only projection
  of state the driver owns or reads publicly (no private execution internals).
  Gated on publisher presence (NOT live-only). Best-effort: a publish/transport
  failure is swallowed-and-logged, never stopping the loop (§10.6).

Per-signal execution-failure isolation (§8.4, BROKER_ERROR) still arrives in a
later increment (docs/LOOPDRIVER_IMPLEMENTATION_PLAN.md). The loop now closes the
data → signal → execution path: it validates the ledger at startup, advances time,
pulls signals, **routes them to the handler**, guards against stale data, **counts
what it does**, and **publishes that count externally** (when a publisher is wired)
for observability. It still owns no execution behavior of its own — it only forwards
to process_signal, the single trade path (ADR-006); publishing is downstream of
truth and never feeds back into it (ADR-001).

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

import time
from enum import Enum
from typing import AbstractSet, Any, Callable, Dict, List, Optional

from core.alerts.alerter import alerter
from core.clock import Clock
from core.database.providers.base import MarketDataProvider
from core.database.utils.market_hours import MarketHours
from core.execution.handler import ExecutionHandler
from core.execution.watchdog import RuntimeWatchdog
from core.instruments.master_readiness import ReadinessState, ReadinessVerdict
from core.logging import setup_logger
from core.runtime.config import DriverConfig
from core.runtime.instrument_scope import has_derivatives
from core.runtime.event_journal import EventType, RuntimeEventJournal
from core.runtime.metrics import NullTelemetrySink, RuntimeMetric, TelemetrySink
from core.runtime.signal_source import SignalSource
from core.runtime.telemetry_publisher import RuntimeTelemetryPublisher


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
                 source: Optional[SignalSource] = None,
                 watchdog: Optional[RuntimeWatchdog] = None,
                 execution: Optional[ExecutionHandler] = None,
                 broker_positions: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                 telemetry: Optional[TelemetrySink] = None,
                 publisher: Optional[RuntimeTelemetryPublisher] = None,
                 master_readiness: Optional[Callable[[], ReadinessVerdict]] = None):
        self._config = config
        self._clock = clock
        self._provider = provider
        self._journal = journal
        self._source = source
        self._watchdog = watchdog
        self._execution = execution
        # Optional broker-book source for the startup reconciliation gate (§11.3).
        # The real live fetch is deferred (PROJECT_STATE Planned #6); when absent
        # reconciliation is vacuously clear (no broker book to compare).
        self._broker_positions = broker_positions
        # MM.4 master-readiness checker — a zero-arg callable returning a
        # ReadinessVerdict (the entry script builds it over the resolver, keeping
        # the driver decoupled from the master). Evaluation only; the gate never
        # resolves/refreshes a master (Decision 6). Absent = no check (vacuous,
        # mirroring broker_positions); live F&O wiring is deferred.
        self._master_readiness = master_readiness
        # Runtime telemetry (Phase H) — observation only, never a source of truth
        # and never in the trade decision path. Defaults to the inert no-op sink
        # so the loop runs identically with or without telemetry wired. Increments
        # are best-effort (_meter swallows sink failures): telemetry must never
        # stop trading.
        self._telemetry = telemetry if telemetry is not None else NullTelemetrySink()
        # External telemetry publishing bridge (Phase H, §10) — optional and
        # best-effort. It is a *consumer* of the metric snapshot (it must be wired
        # to the SAME telemetry sink above); the driver only calls publish() on
        # cadence and close() on shutdown — no other coupling. Absent = no
        # publishing, loop unchanged. NOT live-gated: §10 telemetry is not
        # live-only (unlike the watchdog, §9.5).
        self._publisher = publisher
        # Last telemetry-publish time, by the deterministic clock (§10.2 throttle).
        self._last_publish_at = None
        # Wall-clock process-start mark for the health uptime field (§10.5). Uptime
        # is an operational concern, so it uses wall-clock — separate from the
        # data-driven trade Clock (§6.5) and never on the decision path.
        self._start_monotonic = time.monotonic()
        self._logger = setup_logger("loop_driver")
        self._state = RuntimeState.STARTUP
        self._bars_processed = 0
        self._signals_pulled = 0
        # Last observed watchdog health, for edge-triggered staleness journaling
        # (§9 / §15.4). Presumed healthy until the watchdog reports otherwise.
        self._data_was_healthy = True
        # Last observed handler kill-switch state, for edge-triggered
        # KILL_SWITCH_ACTIVATED journaling from a single source (IN-001, §10.7) —
        # any cause (stale data via the watchdog, drawdown, broker, daily-limit).
        self._kill_switch_was_active = False
        # The process has entered STARTUP (§3.1); record it (§15.4) and count it.
        self._emit(
            EventType.STARTUP,
            "LoopDriver constructed; entering STARTUP",
            {"mode": config.mode.value, "symbols": list(config.symbols)},
        )
        self._meter(RuntimeMetric.STARTUP_COUNT)

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

    def _meter(self, metric: RuntimeMetric, count: int = 1) -> None:
        """
        Bump a runtime telemetry counter (Phase H), best-effort. Telemetry is
        observational only — it never affects an execution/signal/reconciliation/
        recovery decision and is never a source of truth. A faulty sink must not
        stop trading (Constitution §6 forbids silent failure, so the swallowed
        error is logged, not lost), so every increment is wrapped here and the
        loop is never broken by a telemetry fault.
        """
        try:
            self._telemetry.increment(metric, count)
        except Exception as exc:  # best-effort: telemetry never breaks the loop
            self._logger.error("Telemetry increment failed for %s: %s", metric, exc)

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
        # A clean stop (STOPPING -> STOPPED). A refuse-to-start (abort_startup)
        # is a distinct lifecycle outcome and is NOT counted here.
        self._meter(RuntimeMetric.STOP_COUNT)

    # -- Phase F: startup gate / recovery ----------------------------------- #

    def _run_startup_gate(self) -> bool:
        """
        The §11 startup-validation gate, run only when an ExecutionHandler is
        injected. Confirms recovery (reuse — never re-restore, ADR-001) and
        reconciliation against broker truth before STARTUP -> RUNNING.

        Returns True if the gate passed (driver is now RUNNING) or False if it
        refused (driver is now STOPPED and the loop must not run). Refuse-to-start
        is the safe default: trading on an unvalidated ledger is prohibited
        (§11.4; ADR-001; Constitution §7).
        """
        self.enter_recovery()
        self._emit(EventType.RECOVERY_STARTED, "startup recovery begun")
        # Recovery already ran at handler construction (load_db_state=True);
        # the driver reuses it and NEVER re-restores (ADR-001 — a second restore
        # path would create a second source of position truth).
        self._emit(EventType.RECOVERY_COMPLETED, "ledger restored from persistence")
        self._meter(RuntimeMetric.RECOVERY_COUNT)

        # MM.4: the instrument master must be trustworthy BEFORE reconciliation
        # matches positions through canonical identity (§5 / Decision 2). A BLOCK
        # refuses to start, like a reconciliation failure.
        if not self._check_master_readiness():
            return False

        # Option-B post-gate canonicalization (G1 Wave 3): re-resolve the restored
        # ledger's identity through the now-verified master, AFTER readiness and
        # BEFORE reconciliation. Currently a no-op (the in-place-swap body lands in
        # the #8/#7 waves); the call site IS the contract.
        self._canonicalize_restored_ledger()

        if not self._reconcile_ledger():
            return False

        self.start()
        return True

    def _check_master_readiness(self) -> bool:
        """
        MM.4 instrument-master readiness gate (MASTER_MATERIALIZATION_POLICY.md
        §4/§5). Enforced ONLY on the live derivative path — LIVE mode, a derivative
        universe, and an injected checker; otherwise it is skipped (equity-only
        LIVE, paper, and replay keep today's soft fallback — no behavior change).

        Returns True to proceed (FRESH/WARN, or not applicable) or False if it
        refused (BLOCK → STOPPED). The driver evaluates a handed-in verdict; it
        never downloads/refreshes/repairs the master (Decision 6).
        """
        if not (self._config.is_live
                and has_derivatives(self._config.symbols)
                and self._master_readiness is not None):
            return True

        verdict = self._master_readiness()
        meta = {
            "reason": verdict.reason,
            "latest_snapshot_date": verdict.latest.isoformat() if verdict.latest else None,
            "expected": verdict.expected.isoformat() if verdict.expected else None,
        }
        if verdict.state is ReadinessState.BLOCK:
            # Refuse to start — mirrors the RECONCILIATION_FAIL contract (§5).
            self._emit(EventType.INSTRUMENT_MASTER_UNAVAILABLE,
                       f"instrument master not ready ({verdict.reason})", metadata=meta)
            alerter.critical(
                f"LoopDriver refused to start: instrument master not ready "
                f"({verdict.reason})"
            )
            self.abort_startup()
            return False
        if verdict.state is ReadinessState.WARN:
            # Start, but record the degraded start durably (telemetry is lossy).
            self._emit(EventType.INSTRUMENT_MASTER_STALE,
                       "instrument master 1 trading day stale; starting with warning",
                       metadata=meta)
            alerter.warning(
                f"LoopDriver starting on a 1-day-stale instrument master "
                f"(latest={verdict.latest}, expected={verdict.expected})"
            )
            self._publish_log(
                "WARNING",
                f"INSTRUMENT_MASTER_STALE latest={verdict.latest} expected={verdict.expected}",
            )
        return True

    def _canonicalize_restored_ledger(self) -> None:
        """
        Option-B post-gate canonicalization pass (G1 Wave 3).

        Slotted strictly AFTER `_check_master_readiness()` proves the master is
        present and strictly BEFORE `_reconcile_ledger()` (G1_WAVE3B_GATE_ORDERING_
        REVIEW.md §1). Enforced ONLY on the live derivative path, gated on the SAME
        condition as MM.4 — LIVE ∧ derivatives ∧ an injected master-readiness
        checker (so the master was actually verified, not vacuously passed) — so
        paper / replay / equity-only-LIVE are a no-op. It runs only on a gate-pass
        (FRESH/WARN); a BLOCK aborts before it (no canonicalization on a refused
        start).

        Canonicalizes both halves of the restored ledger, each the handler's own
        in-place `.instrument` swap (ADR-001; the driver only triggers them in the
        slot): restored POSITIONS (#7-as-restored) and restored ORDERS (#8), both
        futures EQUITY->FUTURE and option parser-lot->master-lot with the display
        symbol preserved byte-for-byte (so reconciliation, run next, still matches
        — H3). `CanonicalInstrument` stays internal (the G1 / 4C.7 boundary).
        """
        if not (self._config.is_live
                and has_derivatives(self._config.symbols)
                and self._master_readiness is not None):
            return
        self._execution.canonicalize_restored_positions()
        self._execution.canonicalize_restored_orders()

    def _reconcile_ledger(self) -> bool:
        """
        Reconcile the restored ledger against broker truth (§11.3). Driven only
        when a broker-positions source is handed in and reconciliation is
        required; otherwise vacuously clear — no broker book to compare (paper/
        replay) or an explicit operator override. A non-empty alert list refuses
        to start. Returns True if consistent (or vacuous), False if it refused.

        The driver consumes the engine's verdict and NEVER overwrites the ledger
        (ADR-001). In LIVE the broker-positions source is not yet wired (Planned
        #6), so live reconciliation is structurally present but vacuous for now;
        it gains teeth when that source lands with execution routing.
        """
        # One reconciliation cycle occurred (counted whether it runs the engine,
        # is vacuously clear, passes, or fails — a cycle happened either way).
        self._meter(RuntimeMetric.RECONCILIATION_COUNT)
        if (self._config.require_reconciliation_on_start
                and self._broker_positions is not None):
            # #6a (W3): the broker-positions source can fault (auth/transport).
            # An uncaught raise here used to escape run() and strand the driver
            # in RECOVERY with no durable record. Convert it into the same
            # refuse-to-start contract as a real divergence — never start a live
            # run unable to read the broker book.
            try:
                broker_book = self._broker_positions()
            except Exception as exc:
                self._emit(
                    EventType.RECONCILIATION_FAIL,
                    f"broker-positions source failed: {exc}",
                )
                alerter.critical(
                    f"LoopDriver refused to start: broker-positions source "
                    f"raised ({exc})"
                )
                self.abort_startup()
                return False
            alerts = self._execution.reconciliation.reconcile(broker_book)
            if alerts:
                self._emit(
                    EventType.RECONCILIATION_FAIL,
                    f"ledger inconsistent with broker: {len(alerts)} alert(s)",
                )
                alerter.critical(
                    f"LoopDriver refused to start: reconciliation found "
                    f"{len(alerts)} divergence(s)"
                )
                self.abort_startup()
                return False
        self._emit(EventType.RECONCILIATION_PASS, "ledger consistent with broker")
        return True

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

        # LIVE requires an ExecutionHandler — the ledger/recovery/reconciliation
        # authority a real run cannot do without (§11). The no-handler path is
        # for replay/inert/test only; a live run without it is a wiring error,
        # caught here before any state change (PHASE_F_STARTUP_GATE_PLAN §3.1).
        if self._config.is_live and self._execution is None:
            raise RuntimeError("LIVE mode requires an injected ExecutionHandler")

        if self._state in (RuntimeState.STARTUP, RuntimeState.RECOVERY):
            if self._execution is not None:
                # Startup-validation gate (§11): recovery + reconciliation must
                # pass before RUNNING. A refusal leaves the driver STOPPED and
                # the loop never runs.
                if not self._run_startup_gate():
                    return
            else:
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
                # §4.1 step 6: publish telemetry (throttled, best-effort) after
                # the symbol sweep, before the watchdog (step 7).
                self._drive_telemetry()
                # Once per tick after the symbol sweep (§9.3/§9.4, §4.1 step 7):
                # staleness check + heartbeat, even on a no-bar tick (that is
                # exactly when a frozen feed must be caught). Live only.
                self._drive_watchdog()
                # IN-001: journal a kill-switch activation once, from the handler's
                # own edge — after routing (this tick) and the watchdog drive, so
                # every cause is caught (drawdown/broker/limit and stale-data).
                self._check_kill_switch()
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
            # Close the telemetry transport on shutdown (best-effort, §14.7).
            if self._publisher is not None:
                try:
                    self._publisher.close()
                except Exception as exc:  # publishing must never break shutdown
                    self._logger.error("Telemetry publisher close failed: %s", exc)

    def _tick(self) -> bool:
        """
        Pull one bar per configured symbol (fixed order); advance the clock,
        pull signals, and count each bar that arrives. Returns True if any symbol
        yielded a bar. Phase D pulls signals but does not route them — no
        execution, watchdog, or telemetry yet.
        """
        # One loop iteration = one _tick() invocation (the unit of the per-tick
        # pipeline, §4.1), counted before the symbol sweep (Phase H telemetry).
        self._meter(RuntimeMetric.LOOP_ITERATIONS)
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
            # Stamp the bar arrival for staleness (§9.2), live only (§9.5).
            if self._config.is_live and self._watchdog is not None:
                self._watchdog.record_bar()
            self._bars_processed += 1
            self._meter(RuntimeMetric.BARS_PROCESSED)
            advanced = True
        return advanced

    def _dispatch_signals(self, signals, bar) -> None:
        """
        Route the signals pulled for one bar to the ExecutionHandler (Phase G,
        §8.1). The list is taken verbatim — its order IS the routing order and is
        never re-ranked (§5.2); each signal is forwarded to the canonical entry
        point `process_signal(signal, current_price=bar.close)` in that order.
        `current_price` is **always** `bar.close` — deterministic, no driver-side
        pricing (§8.1), so live and replay traverse the identical routing path.

        `signals_pulled` counts every collected signal **unconditionally** (the
        Phase D contract). Routing, by contrast, is gated twice:
        - **handler presence** — the no-handler path (replay/inert/test) has no
          ExecutionHandler to route to; it collects/counts only;
        - **RUNNING state** — PAUSED suspends routing without going blind (§3.1):
          bars are still pulled and signals still collected, but no new
          `process_signal` call is issued.

        ADR-006: the driver is the **sole** runtime caller of `process_signal`.
        The seam (§5.4) holds no handler handle, so a SignalSource can never route
        directly — all trading intent flows through here and nowhere else. This
        routes only; sizing/risk/orders/fills remain the handler's (ADR-005).

        Per-signal exception isolation (§8.4): `process_signal` may raise on a hard
        rule violation or a broker fault. Each call is wrapped so **one signal's
        failure does not kill the loop** — the failure is logged, journaled
        (`BROKER_ERROR`), surfaced to telemetry, and routing continues to the next
        signal/bar. The exception is never swallowed silently (Constitution §6).
        """
        self._signals_pulled += len(signals)
        # Every collected signal is "received" (counted unconditionally, like
        # signals_pulled) — distinct from "routed", which is gated below.
        self._meter(RuntimeMetric.SIGNALS_RECEIVED, len(signals))
        if self._execution is None or self._state is not RuntimeState.RUNNING:
            return
        for signal in signals:
            self._meter(RuntimeMetric.SIGNALS_ROUTED)
            try:
                result = self._execution.process_signal(signal, bar.close)
            except Exception as exc:  # §8.4: a single signal must not kill the loop
                self._handle_signal_error(signal, exc)
                continue
            if result is not None:
                self._meter(RuntimeMetric.EXECUTION_CALLS)

    def _handle_signal_error(self, signal, exc: Exception) -> None:
        """
        §8.4 response to a raised `process_signal`: log at error, journal a
        `BROKER_ERROR` (WARNING; durable, §15.4) with `error`/`signal_id`, and
        surface an edge-triggered telemetry log line (§10). Never re-raises — the
        loop survives. The exception is logged, not swallowed (Constitution §6).
        """
        signal_id = self._signal_identifier(signal)
        self._logger.error("process_signal failed for signal %s: %s", signal_id, exc)
        self._emit(EventType.BROKER_ERROR, f"process_signal raised: {exc}",
                   metadata={"error": str(exc), "signal_id": signal_id})
        self._publish_log("ERROR", f"BROKER_ERROR signal={signal_id}: {exc}")

    @staticmethod
    def _signal_identifier(signal) -> str:
        """A stable ops identifier for a signal: its explicit `signal_id` if the
        source supplied one, else a composed `strategy_id:symbol:timestamp`. The
        driver does not reimplement the handler's internal id derivation."""
        return (signal.metadata.get("signal_id")
                or f"{signal.strategy_id}:{signal.symbol}:{signal.timestamp.isoformat()}")

    def _publish_log(self, level: str, message: str) -> None:
        """Best-effort edge-triggered telemetry log line (§10). Gated on publisher
        presence and wrapped so a faulty publisher can never stop the loop."""
        if self._publisher is None:
            return
        try:
            self._publisher.publish_log(level, message)
        except Exception as exc:  # best-effort: telemetry never breaks the loop
            self._logger.error("Telemetry log publish failed: %s", exc)

    def _drive_telemetry(self) -> None:
        """
        Publish the runtime metric snapshot externally once per cadence interval
        (§10.2), best-effort. Gated only on **publisher presence** — §10 telemetry
        is NOT live-only (unlike the watchdog, §9.5), so it runs in replay too.

        The throttle uses the injected deterministic clock (never wall-clock), so
        live and replay stay reproducible (ADR-003): the driver publishes at most
        once per `telemetry_interval_s` of clock time. Publishing is observation
        only and best-effort — the bridge swallows transport errors, and this call
        is additionally wrapped so even a faulty publisher cannot stop the loop
        (§10.6; publisher failures must never stop trading).
        """
        if self._publisher is None:
            return
        now = self._clock.now()
        if (self._last_publish_at is not None and now is not None
                and (now - self._last_publish_at).total_seconds()
                < self._config.telemetry_interval_s):
            return
        try:
            self._publisher.publish()
            # Health projection (§10.5) on the same cadence — observation only.
            self._publisher.publish_health(self._build_health())
            # Positions projection (§10.4) on the same cadence — observation only.
            self._publisher.publish_positions(self._build_positions())
        except Exception as exc:  # best-effort: telemetry never breaks the loop
            self._logger.error("Telemetry publish drive failed: %s", exc)
        self._last_publish_at = now

    def _build_health(self) -> Dict[str, Any]:
        """
        Build the node health/liveness projection published over telemetry
        (§10.5) — the "observable without broker login" surface (Constitution §6),
        complementary to the on-disk heartbeat.json (§9.4).

        It is a **read-only projection** of state the driver already owns or reads
        publicly — it introduces no new source of truth (ADR-001) and reaches into
        NO private execution internals (no `_kill_switched`/`_trades_today`):
        - `state`     — the driver's own RuntimeState (covers loop/startup/recovery);
        - `data_healthy` — the watchdog's PUBLIC `data_healthy` flag (True when no
          watchdog is wired, i.e. nothing is monitoring staleness);
        - `market_open` — `MarketHours.is_market_open(clock.now())`, keyed to the
          trade clock so it is deterministic in replay and wall-clock-correct live;
        - `last_tick`  — the trade clock's current time (data-driven, §6);
        - `uptime_s`   — wall-clock process uptime (operational, §6.5);
        - `node`       — the configured telemetry node name.
        """
        now = self._clock.now() if self._clock is not None else None
        return {
            "node": self._config.telemetry_node,
            "state": self._state.value,
            "data_healthy": self._watchdog.data_healthy if self._watchdog is not None else True,
            "market_open": MarketHours.is_market_open(now),
            "uptime_s": round(time.monotonic() - self._start_monotonic, 6),
            "last_tick": now.isoformat() if now is not None else None,
        }

    def _build_positions(self) -> Dict[str, Any]:
        """
        Build the positions snapshot published over telemetry (§10.4).

        A **read-only projection** of ledger truth — the handler's
        `position_tracker.get_all_positions()` (ADR-001) — keyed by symbol. It
        computes NO PnL: per-position `pnl_pct` is a documented placeholder
        (`0.0`) until live mark-to-market is wired (§10.4), never faked. With no
        ExecutionHandler injected (replay/inert/test) the book is empty `{}`.
        """
        if self._execution is None:
            return {}
        return {
            symbol: {
                "quantity": pos.quantity,
                "avg_price": pos.avg_price,
                "side": pos.side.value,
                "pnl_pct": 0.0,  # placeholder until live MTM (§10.4 known gap)
            }
            for symbol, pos in self._execution.position_tracker.get_all_positions().items()
        }

    def _drive_watchdog(self) -> None:
        """
        Drive the passive RuntimeWatchdog once per tick after the symbol sweep
        (§9.3/§9.4): staleness check, then heartbeat (self-throttled in the
        watchdog). **Live mode only** (§9.5) — in replay the wall-clock watchdog
        would false-trip, so the driver never touches it.

        A stale-feed trip is recorded edge-triggered (§15.4) on the data_healthy
        True->False edge: the driver journals WATCHDOG_STALE_DATA (the stale-data
        *cause*). The watchdog activates the handler's kill switch synchronously as
        it flips health; the resulting KILL_SWITCH_ACTIVATED is journaled by
        `_check_kill_switch` from the handler's own kill-switch edge (IN-001) — a
        single source for every cause, not a watchdog-specific proxy. Recovery
        re-arms the edge. The driver reads only the watchdog's public health flag.
        """
        if not self._config.is_live or self._watchdog is None:
            return
        self._watchdog.check_data_staleness()
        self._watchdog.write_heartbeat(self._bars_processed)
        # Count each driver heartbeat-drive call (the real watchdog self-throttles
        # the actual disk write — this is the driver's observable cadence, not a
        # disk-write count).
        self._meter(RuntimeMetric.HEARTBEATS_EMITTED)
        healthy = self._watchdog.data_healthy
        if self._data_was_healthy and not healthy:
            self._emit(EventType.WATCHDOG_STALE_DATA,
                       "data feed stale; watchdog tripped kill switch")
            # Edge-triggered (once per incident). KILL_SWITCH_ACTIVATED is NOT
            # emitted here — it is journaled once from the handler kill-switch edge
            # (_check_kill_switch, IN-001), regardless of cause.
            self._meter(RuntimeMetric.STALE_DATA_EVENTS)
        self._data_was_healthy = healthy

    def _check_kill_switch(self) -> None:
        """
        IN-001: journal KILL_SWITCH_ACTIVATED from a SINGLE observation of the
        handler's own kill-switch edge (`_kill_switched` False->True, §10.7) —
        covering every cause exactly once (stale data via the watchdog, drawdown,
        broker fault, daily-trade-limit). Edge-triggered: once per activation,
        never per tick. NOT live-gated — a handler trip in replay/paper (e.g.
        drawdown during routing) is journaled too. Read-only of the handler's flag;
        the kill-switch action itself stays the handler's (ADR-001).
        """
        if self._execution is None:
            return
        active = self._execution._kill_switched
        if active and not self._kill_switch_was_active:
            self._emit(EventType.KILL_SWITCH_ACTIVATED, "handler kill switch activated")
            self._meter(RuntimeMetric.KILL_SWITCH_EVENTS)
        self._kill_switch_was_active = active

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
