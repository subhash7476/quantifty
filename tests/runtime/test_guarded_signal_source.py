"""
MM12.3 — GuardedSignalSource fault-injection + boundary-enforcement tests.

Validates the runtime enforcement layer for the certified Strategy Contract
(MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md §7.3, §8; ADR-018, ADR-019):

- reject-and-journal per-signal contract violations (malformed metadata,
  invalid timestamp) while clean siblings still route (ADR-018);
- quarantine-and-continue on an uncaught on_bar fault or a malformed return
  value (ADR-019) — terminal for the process lifetime, no retry;
- on_start faults are a startup refusal (guard journals then re-raises);
- on_stop faults are logged and swallowed so shutdown completes;
- the guard journals STRATEGY_ERROR / STRATEGY_QUARANTINED /
  SIGNAL_CONTRACT_REJECTED and mirrors them into telemetry;
- the guard is itself a conforming SignalSource (passes the MM12.2 suite);
- replay determinism after quarantine ([] forever, deterministically).
"""

from datetime import timedelta

import pytest

from core.events import SignalEvent, SignalType
from core.runtime.conformance import run_conformance
from core.runtime.event_journal import EventType, RuntimeEventJournal, Severity
from core.runtime.guarded_signal_source import GuardedSignalSource
from core.runtime.metrics import InMemoryTelemetrySink, RuntimeMetric
from core.runtime.signal_source import SignalSource

from _doubles import bar_series

_SYM = "NSE_FO|53001"
_BARS = bar_series(_SYM, 4)


def _entry(bar, **overrides):
    metadata = {"sl_distance": 1.5, "risk_r": 500.0}
    metadata.update(overrides)
    return SignalEvent(strategy_id="fixture", symbol=bar.symbol,
                       timestamp=bar.timestamp, signal_type=SignalType.BUY,
                       confidence=1.0, metadata=metadata)


def _exit(bar):
    return SignalEvent(strategy_id="fixture", symbol=bar.symbol,
                       timestamp=bar.timestamp, signal_type=SignalType.EXIT,
                       confidence=1.0)


class _InertSource(SignalSource):
    def on_bar(self, bar):
        return []


class _ScriptedSource(SignalSource):
    """Returns the i-th scripted list per on_bar call; [] once exhausted."""

    def __init__(self, script=None):
        self._script = list(script or [])
        self.calls = 0

    def on_bar(self, bar):
        i = self.calls
        self.calls += 1
        return self._script[i](bar) if i < len(self._script) else []


class _RaisingSource(SignalSource):
    def __init__(self, message="strategy boom"):
        self._message = message
        self.calls = 0

    def on_bar(self, bar):
        self.calls += 1
        raise ValueError(self._message)


class _MalformedReturnSource(SignalSource):
    def on_bar(self, bar):
        return "not-a-list"


class _MalformedElementSource(SignalSource):
    def on_bar(self, bar):
        return ["not-a-signal-event"]


class _RaisingOnStart(SignalSource):
    def on_start(self, context=None):
        raise RuntimeError("warmup failed")

    def on_bar(self, bar):
        return []


class _RaisingOnStop(SignalSource):
    def on_bar(self, bar):
        return []

    def on_stop(self):
        raise RuntimeError("flush failed")


class _NullAlerter:
    """Hermetic stand-in for the real singleton Alerter (Telegram). Tests that
    are not specifically exercising the alert path must never touch the real
    channel, even though it is a safe no-op when unconfigured."""

    def critical(self, message):
        pass


def _guard(inner, journal=None, telemetry=None, **kwargs):
    kwargs.setdefault("alerter", _NullAlerter())
    return GuardedSignalSource(inner, journal, telemetry, **kwargs)


def _new_journal(tmp_path):
    return RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))


def _event_types(tmp_path):
    import json
    p = tmp_path / "runtime_events.jsonl"
    if not p.exists():
        return []
    return [json.loads(line)["event_type"] for line in p.read_text().splitlines()]


# --------------------------------------------------------------------------- #
# The guard is itself a conforming SignalSource (§7.3: "no driver change needed")
# --------------------------------------------------------------------------- #
def test_guard_wrapping_inert_source_is_conformant(tmp_path):
    def factory():
        return GuardedSignalSource(_InertSource(), _new_journal(tmp_path))
    run_conformance(factory, _BARS, latency_budget_s=1.0)


def test_guard_wrapping_raising_source_is_conformant():
    """A guard around a FAULTING source is still conformant: it contains the
    exception and deterministically returns [] on every call (ADR-019)."""
    def factory():
        return _guard(_RaisingSource(), journal=None)
    run_conformance(factory, _BARS)


# --------------------------------------------------------------------------- #
# Reject-and-journal: contract-violating signals are dropped, siblings route
# --------------------------------------------------------------------------- #
def test_malformed_metadata_signal_is_dropped_clean_sibling_routes(tmp_path):
    bad = _entry(_BARS[0], sl_distance=None)
    good = _exit(_BARS[0])
    source = _ScriptedSource([lambda bar: [bad, good]])
    journal = _new_journal(tmp_path)
    guard = GuardedSignalSource(source, journal)

    result = guard.on_bar(_BARS[0])

    assert result == [good]
    assert "SIGNAL_CONTRACT_REJECTED" in _event_types(tmp_path)
    assert not guard.quarantined


@pytest.mark.parametrize("metadata", [
    {"sl_distance": None, "risk_r": 500.0},
    {"sl_distance": 1.5, "risk_r": None},
    {"sl_distance": 0.0, "risk_r": 500.0},
    {"sl_distance": 1.5, "risk_r": -1.0},
    {"sl_distance": "wide", "risk_r": 500.0},
])
def test_all_malformed_metadata_shapes_are_dropped(tmp_path, metadata):
    bad = _entry(_BARS[0], **metadata)
    source = _ScriptedSource([lambda bar: [bad]])
    guard = GuardedSignalSource(source, _new_journal(tmp_path))

    result = guard.on_bar(_BARS[0])

    assert result == []
    assert not guard.quarantined


def test_invalid_timestamp_signal_is_dropped_not_quarantined(tmp_path):
    drifted = SignalEvent(strategy_id="fixture", symbol=_BARS[0].symbol,
                          timestamp=_BARS[0].timestamp + timedelta(minutes=1),
                          signal_type=SignalType.EXIT, confidence=1.0)
    source = _ScriptedSource([lambda bar: [drifted]])
    journal = _new_journal(tmp_path)
    guard = GuardedSignalSource(source, journal)

    result = guard.on_bar(_BARS[0])

    assert result == []
    assert not guard.quarantined
    assert "SIGNAL_CONTRACT_REJECTED" in _event_types(tmp_path)
    assert "STRATEGY_QUARANTINED" not in _event_types(tmp_path)


def test_exit_signal_never_requires_risk_metadata(tmp_path):
    source = _ScriptedSource([lambda bar: [_exit(bar)]])
    guard = GuardedSignalSource(source, _new_journal(tmp_path))
    assert guard.on_bar(_BARS[0]) == [_exit(_BARS[0])]


def test_clean_signal_passes_through_unmodified(tmp_path):
    good = _entry(_BARS[0])
    source = _ScriptedSource([lambda bar: [good]])
    guard = GuardedSignalSource(source, _new_journal(tmp_path))
    assert guard.on_bar(_BARS[0]) == [good]


def test_rejected_signal_increments_telemetry_counter(tmp_path):
    bad = _entry(_BARS[0], sl_distance=None)
    source = _ScriptedSource([lambda bar: [bad]])
    telemetry = InMemoryTelemetrySink()
    guard = GuardedSignalSource(source, _new_journal(tmp_path), telemetry)
    guard.on_bar(_BARS[0])
    assert telemetry.get(RuntimeMetric.SIGNAL_CONTRACT_REJECTIONS) == 1


# --------------------------------------------------------------------------- #
# Quarantine-and-continue: on_bar raise / malformed return
# --------------------------------------------------------------------------- #
def test_on_bar_exception_quarantines_and_returns_empty(tmp_path):
    source = _RaisingSource()
    journal = _new_journal(tmp_path)
    guard = _guard(source, journal)

    result = guard.on_bar(_BARS[0])

    assert result == []
    assert guard.quarantined
    events = _event_types(tmp_path)
    assert "STRATEGY_ERROR" in events
    assert "STRATEGY_QUARANTINED" in events


def test_quarantine_is_terminal_inner_source_never_invoked_again(tmp_path):
    source = _RaisingSource()
    guard = _guard(source, _new_journal(tmp_path))

    guard.on_bar(_BARS[0])
    assert source.calls == 1

    for bar in _BARS[1:]:
        result = guard.on_bar(bar)
        assert result == []
    assert source.calls == 1  # never invoked again post-quarantine


def test_quarantine_journal_entry_is_edge_triggered_once(tmp_path):
    source = _RaisingSource()
    journal = _new_journal(tmp_path)
    guard = _guard(source, journal)

    for bar in _BARS:
        guard.on_bar(bar)

    events = _event_types(tmp_path)
    assert events.count("STRATEGY_QUARANTINED") == 1
    # STRATEGY_ERROR is only emitted on the actual fault (once — the inner
    # source is never invoked again post-quarantine, §8.2).
    assert events.count("STRATEGY_ERROR") == 1


def test_malformed_return_type_quarantines(tmp_path):
    guard = _guard(_MalformedReturnSource(), _new_journal(tmp_path))
    result = guard.on_bar(_BARS[0])
    assert result == []
    assert guard.quarantined


def test_malformed_element_type_quarantines(tmp_path):
    guard = _guard(_MalformedElementSource(), _new_journal(tmp_path))
    result = guard.on_bar(_BARS[0])
    assert result == []
    assert guard.quarantined


def test_quarantine_increments_telemetry_counters(tmp_path):
    telemetry = InMemoryTelemetrySink()
    guard = _guard(_RaisingSource(), _new_journal(tmp_path), telemetry)
    guard.on_bar(_BARS[0])
    guard.on_bar(_BARS[1])
    assert telemetry.get(RuntimeMetric.STRATEGY_ERRORS) == 1
    assert telemetry.get(RuntimeMetric.STRATEGY_QUARANTINE_EVENTS) == 1


def test_quarantine_fires_critical_alert():
    calls = []

    class _SpyAlerter:
        def critical(self, message):
            calls.append(message)

    guard = GuardedSignalSource(_RaisingSource(), journal=None, alerter=_SpyAlerter())
    guard.on_bar(_BARS[0])
    assert len(calls) == 1


def test_alerter_fault_does_not_escape_quarantine_path():
    """§8.2/Constitution §6: no exception may escape into LoopDriver, even
    when the guard's OWN side-effect channel (alert delivery) is down."""

    class _BrokenAlerter:
        def critical(self, message):
            raise RuntimeError("telegram down")

    guard = GuardedSignalSource(_RaisingSource(), journal=None, alerter=_BrokenAlerter())
    result = guard.on_bar(_BARS[0])  # must not raise
    assert result == []
    assert guard.quarantined


def test_broken_journal_does_not_escape_on_bar():
    class _BrokenJournal:
        def record(self, *a, **k):
            raise RuntimeError("disk full")

    guard = _guard(_RaisingSource(), journal=_BrokenJournal())
    result = guard.on_bar(_BARS[0])  # must not raise
    assert result == []
    assert guard.quarantined


def test_broken_telemetry_does_not_escape_on_bar(tmp_path):
    class _BrokenTelemetry:
        def increment(self, metric, count=1):
            raise RuntimeError("sink down")

    guard = _guard(_RaisingSource(), _new_journal(tmp_path), _BrokenTelemetry())
    result = guard.on_bar(_BARS[0])
    assert result == []
    assert guard.quarantined


def test_no_auto_retry_deterministic_quarantine_across_bars(tmp_path):
    """A deterministic strategy that throws on bar N throws on N again — the
    guard does not retry; it latches quarantine and never re-invokes."""
    source = _RaisingSource()
    guard = _guard(source, _new_journal(tmp_path))
    results = [guard.on_bar(bar) for bar in _BARS]
    assert results == [[] for _ in _BARS]
    assert source.calls == 1


# --------------------------------------------------------------------------- #
# Replay determinism after quarantine (§6, §7.2 replay-twice)
# --------------------------------------------------------------------------- #
def test_replay_determinism_after_quarantine():
    """Two fresh guarded instances over the identical corpus, where the inner
    source raises on the same bar both times, must emit byte-identical
    (empty) streams on every run — the guard's fault handling is itself
    deterministic (ADR-019 / architecture §6)."""
    def factory():
        return _guard(_RaisingSource(), journal=None)

    g1 = factory()
    g2 = factory()
    stream1 = [g1.on_bar(bar) for bar in _BARS]
    stream2 = [g2.on_bar(bar) for bar in _BARS]
    assert stream1 == stream2 == [[] for _ in _BARS]


# --------------------------------------------------------------------------- #
# on_start: refusal, not containment
# --------------------------------------------------------------------------- #
def test_on_start_fault_journals_then_reraises(tmp_path):
    journal = _new_journal(tmp_path)
    guard = GuardedSignalSource(_RaisingOnStart(), journal)

    with pytest.raises(RuntimeError, match="warmup failed"):
        guard.on_start()

    assert "STRATEGY_ERROR" in _event_types(tmp_path)
    assert not guard.quarantined  # on_start faults are a startup refusal, not quarantine


def test_on_start_success_passes_through():
    class _RecordingSource(SignalSource):
        def __init__(self):
            self.started_with = "UNSET"

        def on_start(self, context=None):
            self.started_with = context

        def on_bar(self, bar):
            return []

    inner = _RecordingSource()
    guard = GuardedSignalSource(inner, journal=None)
    ctx = object()
    guard.on_start(ctx)
    assert inner.started_with is ctx


# --------------------------------------------------------------------------- #
# on_stop: logged and swallowed, never escapes
# --------------------------------------------------------------------------- #
def test_on_stop_fault_is_swallowed_not_raised():
    guard = GuardedSignalSource(_RaisingOnStop(), journal=None)
    guard.on_stop()  # must not raise


def test_on_stop_success_passes_through():
    class _RecordingSource(SignalSource):
        def __init__(self):
            self.stopped = False

        def on_bar(self, bar):
            return []

        def on_stop(self):
            self.stopped = True

    inner = _RecordingSource()
    guard = GuardedSignalSource(inner, journal=None)
    guard.on_stop()
    assert inner.stopped is True


# --------------------------------------------------------------------------- #
# Journal vocabulary + severities (ADR-018/019, §8.3)
# --------------------------------------------------------------------------- #
def test_journal_event_types_exist_with_documented_severities():
    assert EventType.STRATEGY_ERROR.value == "STRATEGY_ERROR"
    assert EventType.STRATEGY_QUARANTINED.value == "STRATEGY_QUARANTINED"
    assert EventType.SIGNAL_CONTRACT_REJECTED.value == "SIGNAL_CONTRACT_REJECTED"


def test_signal_contract_rejected_severity_is_warning(tmp_path):
    journal = _new_journal(tmp_path)
    rec = journal.record(EventType.SIGNAL_CONTRACT_REJECTED, "dropped")
    assert rec["severity"] == "WARNING"


def test_strategy_quarantined_severity_is_critical(tmp_path):
    journal = _new_journal(tmp_path)
    rec = journal.record(EventType.STRATEGY_QUARANTINED, "quarantined")
    assert rec["severity"] == "CRITICAL"


def test_strategy_error_record_carries_strategy_id_and_traceback(tmp_path):
    import json
    journal = _new_journal(tmp_path)
    guard = _guard(_RaisingSource("boom-detail"), journal, strategy_id="my_strategy_v1")
    guard.on_bar(_BARS[0])

    lines = (tmp_path / "runtime_events.jsonl").read_text().splitlines()
    error_records = [json.loads(l) for l in lines if json.loads(l)["event_type"] == "STRATEGY_ERROR"]
    assert len(error_records) == 1
    assert error_records[0]["metadata"]["strategy_id"] == "my_strategy_v1"
    assert "boom-detail" in error_records[0]["metadata"]["error"]

    quarantine_records = [json.loads(l) for l in lines if json.loads(l)["event_type"] == "STRATEGY_QUARANTINED"]
    assert quarantine_records[0]["metadata"]["strategy_id"] == "my_strategy_v1"


# --------------------------------------------------------------------------- #
# Non-responsibilities: the guard never mutates signals
# --------------------------------------------------------------------------- #
def test_guard_never_mutates_a_clean_signal_it_passes_through(tmp_path):
    good = _entry(_BARS[0])
    source = _ScriptedSource([lambda bar: [good]])
    guard = GuardedSignalSource(source, _new_journal(tmp_path))
    result = guard.on_bar(_BARS[0])
    assert result[0] is good  # identity-preserved, never rebuilt/defaulted


def test_multiple_clean_signals_preserve_routing_order(tmp_path):
    """§4.4: the returned list order IS the routing order; the guard must
    never re-rank contract-clean signals (EXIT-before-entry convention)."""
    exit_a = _exit(_BARS[0])
    entry_b = _entry(_BARS[0])
    source = _ScriptedSource([lambda bar: [exit_a, entry_b]])
    guard = GuardedSignalSource(source, _new_journal(tmp_path))
    result = guard.on_bar(_BARS[0])
    assert result == [exit_a, entry_b]  # order preserved, not just membership


# --------------------------------------------------------------------------- #
# Both faults across bars in one run (ADR-019: "validation and quarantine as
# one surface... exercise a contract-violating signal and an on_bar raise in
# the same bar")
# --------------------------------------------------------------------------- #
def test_contract_violation_then_raise_on_subsequent_bar(tmp_path):
    bad = _entry(_BARS[0], sl_distance=None)

    def _boom(bar):
        raise ValueError("boom")

    source = _ScriptedSource([lambda bar: [bad], _boom])
    journal = _new_journal(tmp_path)
    guard = _guard(source, journal)

    r0 = guard.on_bar(_BARS[0])
    r1 = guard.on_bar(_BARS[1])

    assert r0 == []
    assert r1 == []
    events = _event_types(tmp_path)
    assert "SIGNAL_CONTRACT_REJECTED" in events
    assert "STRATEGY_QUARANTINED" in events
