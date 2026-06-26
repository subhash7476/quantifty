"""
MM8.1C — EXECUTION_CALLS gating tests.

Verifies that LoopDriver meters EXECUTION_CALLS only when process_signal returns
a non-None value (i.e., the broker execution path was reached), not on:
  * None returns (kill-switch, stacking guard, drawdown guard, etc.)
  * raises (already covered by test_driver_broker_error.py)

New metric semantics: "broker execution path reached" (non-None return).
Prior semantics: "process_signal returned without raising" (any non-raise exit).
"""

from _doubles import (FakeExecutionHandler, FakeClock, FakeMarketDataProvider,
                      FakeSignalSource, bar_series, make_bar, make_signal)
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver
from core.runtime.metrics import InMemoryTelemetrySink, RuntimeMetric


def _replay_cfg():
    return DriverConfig(mode=Mode.REPLAY, symbols=["A"], max_bars=None)


class _NoneReturningHandler(FakeExecutionHandler):
    """Simulates a handler that always returns None (kill-switch / early exit)."""
    def process_signal(self, signal, current_price):
        return None


class _NonNullReturningHandler(FakeExecutionHandler):
    """Simulates a handler that always returns a value (broker path reached)."""
    def process_signal(self, signal, current_price):
        return object()  # any non-None sentinel


# --------------------------------------------------------------------------- #
# (1) EXECUTION_CALLS is NOT metered when process_signal returns None
# --------------------------------------------------------------------------- #
def test_execution_calls_not_metered_on_none_return():
    sink = InMemoryTelemetrySink()
    handler = _NoneReturningHandler()
    d = LoopDriver(_replay_cfg(), execution=handler, telemetry=sink)
    d.start()
    d._dispatch_signals([make_signal("A")], make_bar("A", close=10.0))

    assert sink.get(RuntimeMetric.SIGNALS_ROUTED) == 1
    assert sink.snapshot().get(RuntimeMetric.EXECUTION_CALLS, 0) == 0


# --------------------------------------------------------------------------- #
# (2) EXECUTION_CALLS IS metered when process_signal returns non-None
# --------------------------------------------------------------------------- #
def test_execution_calls_metered_on_non_none_return():
    sink = InMemoryTelemetrySink()
    handler = _NonNullReturningHandler()
    d = LoopDriver(_replay_cfg(), execution=handler, telemetry=sink)
    d.start()
    d._dispatch_signals([make_signal("A")], make_bar("A", close=10.0))

    assert sink.get(RuntimeMetric.SIGNALS_ROUTED) == 1
    assert sink.get(RuntimeMetric.EXECUTION_CALLS) == 1


# --------------------------------------------------------------------------- #
# (3) two signals: one returns non-None, one returns None → count = 1
# --------------------------------------------------------------------------- #
class _SelectiveHandler(FakeExecutionHandler):
    """Returns non-None only for symbol 'EXEC', None for everything else."""
    def process_signal(self, signal, current_price):
        if signal.symbol == "EXEC":
            return object()
        return None


def test_execution_calls_counts_only_non_none_returns():
    sink = InMemoryTelemetrySink()
    handler = _SelectiveHandler()
    d = LoopDriver(_replay_cfg(), execution=handler, telemetry=sink)
    d.start()
    d._dispatch_signals(
        [make_signal("EXEC"), make_signal("SKIP")],
        make_bar("A", close=10.0),
    )

    assert sink.get(RuntimeMetric.SIGNALS_ROUTED) == 2
    assert sink.get(RuntimeMetric.EXECUTION_CALLS) == 1
