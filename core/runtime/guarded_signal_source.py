"""
GuardedSignalSource — the runtime boundary guard for the Strategy Contract
---------------------------------------------------------------------------
MM12.3 (docs/reports/MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md §7.3, §8;
ADR-018, ADR-019): the platform-owned SignalSource decorator composed around
every external strategy at the composition root. It enforces, on every bar,
in production, the same contract the offline conformance suite
(core/runtime/conformance.py, MM12.2) certifies before a PAPER run.

It is itself a conforming SignalSource — the frozen LoopDriver cannot tell
the difference, so this module requires zero diffs in core/runtime/driver.py
or core/execution/handler.py (MM12.3 acceptance criterion).

Two concerns, deliberately co-located by design (ADR-019's non-blocking
note, recorded at MM12.1 approval): with exactly one fault policy in
existence, splitting validation and quarantine into separate classes would
be speculative abstraction. Extraction is deferred until a second policy
exists (CLAUDE.md: no abstractions ahead of a concrete need).

1. Boundary validation (ADR-018) — per-signal, reject-and-journal:
   - shape (return value is a List[SignalEvent]);
   - timestamp discipline (signal.timestamp == the triggering bar's);
   - mandatory entry risk metadata on BUY/SELL (sl_distance > 0, risk_r > 0).
   One bad signal is dropped and journaled (SIGNAL_CONTRACT_REJECTED);
   contract-clean siblings in the same list still route. This validates
   exactly what core/runtime/conformance.py already codifies as the
   mechanically-checked §4 contract — the guard is that same contract
   enforced online instead of offline.

2. Fault policy (ADR-019) — quarantine-and-continue on the first uncaught
   on_bar (or on_start) exception, OR a malformed on_bar return value
   (non-list, or a list containing a non-SignalEvent element — a return-
   shape fault is treated identically to a raise, per the architecture's
   fault matrix §8.1): journal STRATEGY_ERROR (traceback digest) ->
   alerter.critical(...) -> latch QUARANTINED, journal STRATEGY_QUARANTINED
   (edge-triggered, once) -> return [] for this and every subsequent bar;
   the inner source is never invoked again. No retry, no auto-flatten.
   on_start faults are a startup refusal (journal, then re-raise — mirrors
   the platform's existing refuse-to-start posture, ADR-MM7F-1). on_stop
   faults are logged and swallowed so shutdown always completes.

Every side channel the guard itself uses (journal, telemetry, alerter) is
best-effort: a failure in any of them must never let an exception escape
into the LoopDriver (Constitution §6 — degrade trading, never observability;
this applies to the guard's own fault-handling code, not only to the
strategy's).

Non-responsibilities (MM12.3 task scope): the guard never sizes, prices,
evaluates alpha, modifies/default-fills a signal, executes orders, or reads
broker/portfolio state. It holds no handle to any of those (mirrors the
seam's own §5.4 restriction — conformance's no_forbidden_handles check
passes on a guard instance because it holds only core.runtime/core.alerts
objects).
"""

import traceback
from typing import List, Optional

from core.alerts.alerter import alerter as _default_alerter
from core.events import OHLCVBar, SignalEvent, SignalType
from core.logging import setup_logger
from core.runtime.event_journal import EventType, RuntimeEventJournal
from core.runtime.metrics import NullTelemetrySink, RuntimeMetric, TelemetrySink
from core.runtime.signal_source import SignalSource

_ENTRY_TYPES = (SignalType.BUY, SignalType.SELL)
_MANDATORY_ENTRY_METADATA = ("sl_distance", "risk_r")


class GuardedSignalSource(SignalSource):
    """
    Wraps an external SignalSource and enforces the Strategy Contract at
    runtime. Composed at the composition root: `GuardedSignalSource(source,
    journal, telemetry)` (architecture §1, §7.3, §11.1).
    """

    def __init__(self,
                 inner: SignalSource,
                 journal: Optional[RuntimeEventJournal] = None,
                 telemetry: Optional[TelemetrySink] = None,
                 *,
                 strategy_id: Optional[str] = None,
                 alerter=_default_alerter):
        """
        Args:
            inner: the external SignalSource to guard. Never invoked again
                once quarantined.
            journal: durable event sink (§8.3 vocabulary). None disables
                journaling (e.g. a bare conformance run) without raising.
            telemetry: runtime counter sink. Defaults to NullTelemetrySink
                (inert), matching the LoopDriver's own default (Phase H).
            strategy_id: label stamped on STRATEGY_ERROR/STRATEGY_QUARANTINED
                journal records. ADR-019 wants the strategy identified even
                when the fault is a raise with no SignalEvent to read
                strategy_id from; defaults to the inner source's class name.
            alerter: the critical-alert channel (default: the platform's
                singleton Alerter — Telegram). Injectable for tests.
        """
        self._inner = inner
        self._journal = journal
        self._telemetry = telemetry if telemetry is not None else NullTelemetrySink()
        self._alerter = alerter
        self._strategy_id = strategy_id or type(inner).__name__
        self._quarantined = False
        self._logger = setup_logger("guarded_signal_source")

    @property
    def quarantined(self) -> bool:
        """True once the fault latch has tripped (edge-triggered, terminal)."""
        return self._quarantined

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def on_start(self, context: Optional[object] = None) -> None:
        """on_start faults are a startup refusal (§8.1), not quarantine:
        journal STRATEGY_ERROR, then re-raise so the composition root
        aborts before the driver reaches RUNNING."""
        try:
            self._inner.on_start(context)
        except Exception as exc:
            digest = self._digest(exc)
            self._record(EventType.STRATEGY_ERROR, f"on_start fault: {digest}",
                        metadata={"strategy_id": self._strategy_id, "error": digest})
            self._meter(RuntimeMetric.STRATEGY_ERRORS)
            raise

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        """Per architecture §7.3: (1) short-circuit if quarantined; (2) call
        the inner source inside a fault boundary; (3) validate shape + each
        signal against the contract; (4) drop violators and journal, passing
        only contract-clean signals to the driver."""
        if self._quarantined:
            return []

        try:
            result = self._inner.on_bar(bar)
        except Exception as exc:
            self._quarantine(exc)
            return []

        if not isinstance(result, list) or any(
                not isinstance(item, SignalEvent) for item in result):
            self._quarantine(TypeError(
                f"on_bar returned {type(result).__name__}, expected "
                "List[SignalEvent]"))
            return []

        clean: List[SignalEvent] = []
        for signal in result:
            reason = self._contract_violation(signal, bar)
            if reason is None:
                clean.append(signal)
            else:
                self._reject(signal, reason)
        return clean

    def on_stop(self) -> None:
        """Shutdown must always complete (§8.1): log and swallow, never
        raise — mirrors the driver's own telemetry-close handling."""
        try:
            self._inner.on_stop()
        except Exception as exc:
            self._logger.error(
                "GuardedSignalSource: inner on_stop raised (swallowed, "
                "shutdown proceeds): %s", exc)

    # ------------------------------------------------------------------ #
    # Boundary validation (ADR-018)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _contract_violation(signal: SignalEvent, bar: OHLCVBar) -> Optional[str]:
        """Returns a human-readable violation reason, or None if the signal
        is contract-clean. Mirrors core/runtime/conformance.py's
        check_timestamp_discipline / check_entry_risk_metadata exactly —
        the guard enforces online what conformance certifies offline."""
        if signal.timestamp != bar.timestamp:
            return (f"timestamp {signal.timestamp!r} != bar timestamp "
                    f"{bar.timestamp!r}")
        if signal.signal_type in _ENTRY_TYPES:
            for key in _MANDATORY_ENTRY_METADATA:
                value = signal.metadata.get(key)
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    numeric = None
                if numeric is None or numeric <= 0:
                    return f"metadata['{key}'] = {value!r} (must be numeric and > 0)"
        return None

    def _reject(self, signal: SignalEvent, reason: str) -> None:
        self._record(
            EventType.SIGNAL_CONTRACT_REJECTED,
            f"signal rejected: {reason}",
            metadata={
                "strategy_id": signal.strategy_id,
                "symbol": signal.symbol,
                "signal_type": signal.signal_type.value,
                "timestamp": signal.timestamp.isoformat(),
                "reason": reason,
            })
        self._meter(RuntimeMetric.SIGNAL_CONTRACT_REJECTIONS)

    # ------------------------------------------------------------------ #
    # Fault policy (ADR-019)
    # ------------------------------------------------------------------ #
    def _quarantine(self, exc: Exception) -> None:
        digest = self._digest(exc)
        self._record(EventType.STRATEGY_ERROR, f"on_bar fault: {digest}",
                    metadata={"strategy_id": self._strategy_id, "error": digest})
        self._meter(RuntimeMetric.STRATEGY_ERRORS)
        self._safe_alert(f"strategy quarantined: {self._strategy_id}: {digest}")
        if not self._quarantined:  # edge-triggered, once
            self._quarantined = True
            self._record(EventType.STRATEGY_QUARANTINED,
                        f"strategy quarantined: {self._strategy_id}",
                        metadata={"strategy_id": self._strategy_id})
            self._meter(RuntimeMetric.STRATEGY_QUARANTINE_EVENTS)

    @staticmethod
    def _digest(exc: Exception) -> str:
        return "".join(
            traceback.format_exception_only(type(exc), exc)).strip()

    # ------------------------------------------------------------------ #
    # Best-effort side channels — a failure here must never escape into
    # the driver (Constitution §6 applies to the guard's own fault path too).
    # ------------------------------------------------------------------ #
    def _record(self, event_type: EventType, message: str, *,
                metadata: Optional[dict] = None) -> None:
        if self._journal is None:
            return
        try:
            self._journal.record(event_type, message, metadata=metadata)
        except Exception as exc:
            self._logger.error("GuardedSignalSource: journal write failed: %s", exc)

    def _meter(self, metric: RuntimeMetric) -> None:
        try:
            self._telemetry.increment(metric)
        except Exception as exc:
            self._logger.error("GuardedSignalSource: telemetry increment failed: %s", exc)

    def _safe_alert(self, message: str) -> None:
        try:
            self._alerter.critical(message)
        except Exception as exc:
            self._logger.error("GuardedSignalSource: critical alert failed: %s", exc)
