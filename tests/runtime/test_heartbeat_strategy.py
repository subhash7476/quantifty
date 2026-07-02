"""
MM12.4 — HeartbeatSignalSource conformance + acceptance tests.

Proves the reference strategy:
1. Passes MM12.2 Layers 1+2 conformance (CONFORMANT gate).
2. Passes GuardedSignalSource as a wrapped source.
3. Produces deterministic output across two fresh instances.
4. The factory exports correctly from the external-style package.
"""

from reference_strategies.heartbeat import build_signal_source
from reference_strategies.heartbeat.source import HeartbeatSignalSource
from core.runtime.conformance import (
    ConformanceViolation,
    check_constructor_surface,
    check_entry_risk_metadata,
    check_import_surface,
    check_is_signal_source,
    check_lifecycle,
    check_no_forbidden_handles,
    check_on_bar_not_coroutine,
    check_replay_equivalence,
    check_return_shape,
    check_timestamp_discipline,
    run_conformance,
)
from core.runtime.guarded_signal_source import GuardedSignalSource
from _doubles import bar_series

import os
import pytest
from pathlib import Path

_SYM = "NSE_EQ|INE000A01012"
_BARS = bar_series(_SYM, 100)


def _factory():
    return build_signal_source()


def test_conformant_heartbeat_layers_1_and_2():
    """HeartbeatSignalSource passes the full MM12.2 conformance suite."""
    run_conformance(_factory, _BARS, latency_budget_s=1.0)


def test_conformant_heartbeat_can_be_wrapped_in_guard():
    """A wrapped HeartbeatSignalSource is itself a conforming SignalSource."""
    run_conformance(
        lambda: GuardedSignalSource(_factory()),
        _BARS, latency_budget_s=1.0,
    )


def test_heartbeat_contract_violations():
    """HeartbeatSignalSource produces no contract-violating signals by construction."""
    source = _factory()
    source.on_start()
    bar = _BARS[0]
    signals = source.on_bar(bar)
    assert isinstance(signals, list)
    for sig in signals:
        if sig.signal_type in ("BUY", "SELL"):
            assert "sl_distance" in sig.metadata
            assert "risk_r" in sig.metadata
            assert sig.metadata["sl_distance"] > 0
            assert sig.metadata["risk_r"] > 0


def test_heartbeat_guard_zero_rejection():
    """Running the heartbeat through the guard produces zero rejections/quarantines."""
    from core.runtime.metrics import InMemoryTelemetrySink, RuntimeMetric
    from core.runtime.event_journal import EventType, RuntimeEventJournal
    import json, tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        journal_path = f.name

    try:
        telemetry = InMemoryTelemetrySink()
        journal = RuntimeEventJournal(path=journal_path)
        inner = _factory()
        guarded = GuardedSignalSource(inner, journal=journal, telemetry=telemetry)

        guarded.on_start()
        for bar in _BARS:
            guarded.on_bar(bar)
        guarded.on_stop()

        # Zero guard events
        assert telemetry.get(RuntimeMetric.STRATEGY_ERRORS) == 0
        assert telemetry.get(RuntimeMetric.STRATEGY_QUARANTINE_EVENTS) == 0
        assert telemetry.get(RuntimeMetric.SIGNAL_CONTRACT_REJECTIONS) == 0

        # Journal must not contain guard events
        if os.path.exists(journal_path):
            with open(journal_path) as jf:
                for line in jf:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    assert record["event_type"] not in (
                        EventType.STRATEGY_ERROR.value,
                        EventType.STRATEGY_QUARANTINED.value,
                        EventType.SIGNAL_CONTRACT_REJECTED.value,
                    ), f"Unexpected guard event: {record['event_type']}"
    finally:
        if os.path.exists(journal_path):
            os.unlink(journal_path)
