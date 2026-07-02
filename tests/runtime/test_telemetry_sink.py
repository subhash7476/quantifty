"""
Unit tests for the LoopDriver runtime telemetry sink (Phase H).

Validates the small, inert-by-default metrics interface that gives visibility
into runtime behavior WITHOUT becoming a source of truth or affecting runtime
decisions:

- RuntimeMetric enumerates exactly the documented in-scope counters (4
  lifecycle, 4 runtime, 3 watchdog, 1 execution, 3 strategy guard — MM12.3)
  — no broker/PnL/portfolio metrics;
- TelemetrySink is the injected interface; NullTelemetrySink is the inert
  default (every increment is a no-op);
- InMemoryTelemetrySink accumulates counts and exposes a read-only snapshot;
- the sink module imports no strategy code (ADR-002 forbidden-import guard,
  mirroring the other core/runtime modules).
"""

import ast
from pathlib import Path

from core.runtime.metrics import (InMemoryTelemetrySink, NullTelemetrySink,
                                  RuntimeMetric, TelemetrySink)


# --------------------------------------------------------------------------- #
# Scope: exactly the documented metrics, grouped as specified
# --------------------------------------------------------------------------- #
def test_runtime_metric_has_exactly_the_documented_counters():
    assert {m.name for m in RuntimeMetric} == {
        # Lifecycle
        "STARTUP_COUNT", "RECOVERY_COUNT", "RECONCILIATION_COUNT", "STOP_COUNT",
        # Runtime
        "BARS_PROCESSED", "SIGNALS_RECEIVED", "SIGNALS_ROUTED", "LOOP_ITERATIONS",
        # Watchdog
        "HEARTBEATS_EMITTED", "STALE_DATA_EVENTS", "KILL_SWITCH_EVENTS",
        # Execution
        "EXECUTION_CALLS",
        # Strategy guard (MM12.3 — GuardedSignalSource, ADR-018/ADR-019)
        "STRATEGY_ERRORS", "STRATEGY_QUARANTINE_EVENTS",
        "SIGNAL_CONTRACT_REJECTIONS",
    }


# --------------------------------------------------------------------------- #
# NullTelemetrySink: the inert default — every call is a no-op
# --------------------------------------------------------------------------- #
def test_null_sink_increment_is_a_noop_and_returns_none():
    sink = NullTelemetrySink()
    assert isinstance(sink, TelemetrySink)
    assert sink.increment(RuntimeMetric.BARS_PROCESSED) is None
    assert sink.increment(RuntimeMetric.BARS_PROCESSED, 5) is None


# --------------------------------------------------------------------------- #
# InMemoryTelemetrySink: accumulate + read back
# --------------------------------------------------------------------------- #
def test_inmemory_unset_metric_reads_zero():
    assert InMemoryTelemetrySink().get(RuntimeMetric.STARTUP_COUNT) == 0


def test_inmemory_increment_accumulates():
    sink = InMemoryTelemetrySink()
    sink.increment(RuntimeMetric.BARS_PROCESSED)
    sink.increment(RuntimeMetric.BARS_PROCESSED)
    assert sink.get(RuntimeMetric.BARS_PROCESSED) == 2


def test_inmemory_increment_by_amount():
    sink = InMemoryTelemetrySink()
    sink.increment(RuntimeMetric.SIGNALS_RECEIVED, 3)
    sink.increment(RuntimeMetric.SIGNALS_RECEIVED, 2)
    assert sink.get(RuntimeMetric.SIGNALS_RECEIVED) == 5


def test_inmemory_counters_are_independent():
    sink = InMemoryTelemetrySink()
    sink.increment(RuntimeMetric.LOOP_ITERATIONS, 4)
    sink.increment(RuntimeMetric.EXECUTION_CALLS, 1)
    assert sink.get(RuntimeMetric.LOOP_ITERATIONS) == 4
    assert sink.get(RuntimeMetric.EXECUTION_CALLS) == 1
    assert sink.get(RuntimeMetric.BARS_PROCESSED) == 0


def test_inmemory_snapshot_returns_only_touched_metrics_and_is_isolated():
    sink = InMemoryTelemetrySink()
    sink.increment(RuntimeMetric.STARTUP_COUNT)
    snap = sink.snapshot()
    assert snap == {RuntimeMetric.STARTUP_COUNT: 1}
    # The snapshot is a copy — mutating it does not corrupt the sink.
    snap[RuntimeMetric.STARTUP_COUNT] = 999
    assert sink.get(RuntimeMetric.STARTUP_COUNT) == 1


def test_inmemory_rejects_non_metric_keys():
    sink = InMemoryTelemetrySink()
    try:
        sink.increment("bars_processed")  # not a RuntimeMetric
    except TypeError:
        return
    raise AssertionError("expected TypeError for a non-RuntimeMetric key")


# --------------------------------------------------------------------------- #
# ADR-002: the sink module imports no strategy code
# --------------------------------------------------------------------------- #
def test_metrics_module_has_no_forbidden_strategy_imports():
    src = (Path(__file__).resolve().parents[2]
           / "core" / "runtime" / "metrics.py").read_text(encoding="utf-8")
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
