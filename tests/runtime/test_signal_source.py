"""
Unit tests for core.runtime.signal_source.SignalSource.

Validates the abstract contract specified in DRIVER_SPECIFICATION.md section 5:
- on_bar is the one mandatory method (pull model);
- on_start / on_stop are optional no-op lifecycle hooks;
- the list returned by on_bar is the routing order (priority preserved);
- the same interface expresses the four required client shapes (section 5.3)
  without the driver branching on type;
- the module imports no strategy code (ADR-002 / ADR-006, section 5.1).
"""

import ast
import queue
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pytest

from core.events import OHLCVBar, SignalEvent, SignalType
from core.runtime.signal_source import SignalSource


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def make_bar(close: float = 100.0, ts: Optional[datetime] = None) -> OHLCVBar:
    ts = ts or datetime(2026, 6, 5, 9, 15, 0)
    return OHLCVBar(
        symbol="NSE_INDEX|Nifty 50",
        timestamp=ts,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=0.0,
    )


def make_signal(symbol: str = "NSE_INDEX|Nifty 50",
                signal_type: SignalType = SignalType.BUY,
                ts: Optional[datetime] = None) -> SignalEvent:
    return SignalEvent(
        strategy_id="test",
        symbol=symbol,
        timestamp=ts or datetime(2026, 6, 5, 9, 15, 0),
        signal_type=signal_type,
        confidence=1.0,
    )


# --------------------------------------------------------------------------- #
# Minimal concrete sources used only by the tests (NOT shipped in core)
# --------------------------------------------------------------------------- #
class _SilentSource(SignalSource):
    """A do-nothing source: the normal 'no action this bar' case."""

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        return []


class _FixedSource(SignalSource):
    """Returns a preset list of signals on every bar, in order."""

    def __init__(self, signals: List[SignalEvent]):
        self._signals = signals

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        return list(self._signals)


class _LifecycleSource(SignalSource):
    """Records lifecycle-hook invocations to verify default hooks are wired."""

    def __init__(self):
        self.started_with = "UNSET"
        self.stopped = False

    def on_start(self, context=None) -> None:
        self.started_with = context

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        return []

    def on_stop(self) -> None:
        self.stopped = True


class _MissingOnBarSource(SignalSource):
    """Deliberately does NOT implement on_bar — must stay abstract."""
    pass


# --------------------------------------------------------------------------- #
# Abstractness
# --------------------------------------------------------------------------- #
def test_cannot_instantiate_abstract_base():
    with pytest.raises(TypeError):
        SignalSource()  # type: ignore[abstract]


def test_subclass_without_on_bar_is_still_abstract():
    with pytest.raises(TypeError):
        _MissingOnBarSource()  # type: ignore[abstract]


def test_on_bar_is_the_only_abstract_method():
    assert SignalSource.__abstractmethods__ == frozenset({"on_bar"})


# --------------------------------------------------------------------------- #
# on_bar contract
# --------------------------------------------------------------------------- #
def test_minimal_subclass_instantiable_and_returns_list():
    src = _SilentSource()
    result = src.on_bar(make_bar())
    assert isinstance(result, list)


def test_empty_list_is_valid_do_nothing():
    assert _SilentSource().on_bar(make_bar()) == []


def test_returns_signal_events():
    sig = make_signal()
    result = _FixedSource([sig]).on_bar(make_bar())
    assert result == [sig]
    assert all(isinstance(s, SignalEvent) for s in result)


def test_priority_order_is_preserved():
    s1 = make_signal(symbol="A", signal_type=SignalType.BUY)
    s2 = make_signal(symbol="B", signal_type=SignalType.SELL)
    s3 = make_signal(symbol="C", signal_type=SignalType.EXIT)
    src = _FixedSource([s1, s2, s3])
    # The list order IS the routing order — the source must return it verbatim.
    assert src.on_bar(make_bar()) == [s1, s2, s3]


# --------------------------------------------------------------------------- #
# Optional lifecycle hooks default to no-ops
# --------------------------------------------------------------------------- #
def test_default_on_start_is_noop_returns_none():
    assert _SilentSource().on_start() is None


def test_default_on_start_accepts_optional_context():
    src = _SilentSource()
    assert src.on_start(None) is None
    assert src.on_start(object()) is None  # arbitrary read-only context


def test_default_on_stop_is_noop_returns_none():
    assert _SilentSource().on_stop() is None


def test_overridden_lifecycle_hooks_are_invoked():
    src = _LifecycleSource()
    ctx = object()
    src.on_start(ctx)
    src.on_stop()
    assert src.started_with is ctx
    assert src.stopped is True


# --------------------------------------------------------------------------- #
# The four client shapes (section 5.3) all fit one interface
# --------------------------------------------------------------------------- #
def test_discretionary_queue_source_drains_synchronously():
    """A thread-safe queue the UI writes to; on_bar drains it synchronously."""

    class _QueueSource(SignalSource):
        def __init__(self):
            self.q: "queue.Queue[SignalEvent]" = queue.Queue()

        def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
            drained: List[SignalEvent] = []
            while not self.q.empty():
                drained.append(self.q.get_nowait())
            return drained

    src = _QueueSource()
    assert src.on_bar(make_bar()) == []          # nothing enqueued yet
    a, b = make_signal(symbol="A"), make_signal(symbol="B")
    src.q.put(a)
    src.q.put(b)
    assert src.on_bar(make_bar()) == [a, b]      # drained in FIFO order
    assert src.on_bar(make_bar()) == []          # queue now empty


def test_replay_source_returns_signals_due_at_bar_timestamp():
    """Replays recorded signals keyed by timestamp — reproduction, not alpha."""

    class _ReplaySource(SignalSource):
        def __init__(self, recorded: List[SignalEvent]):
            self._by_ts = {s.timestamp: s for s in recorded}

        def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
            due = self._by_ts.get(bar.timestamp)
            return [due] if due else []

    t0 = datetime(2026, 6, 5, 9, 15, 0)
    t1 = t0 + timedelta(minutes=1)
    rec0 = make_signal(ts=t0)
    rec1 = make_signal(ts=t1)
    src = _ReplaySource([rec0, rec1])
    assert src.on_bar(make_bar(ts=t0)) == [rec0]
    assert src.on_bar(make_bar(ts=t1)) == [rec1]
    assert src.on_bar(make_bar(ts=t1 + timedelta(minutes=1))) == []


# --------------------------------------------------------------------------- #
# Architectural invariant: no strategy imports (ADR-002 / ADR-006)
# --------------------------------------------------------------------------- #
def test_module_imports_no_strategy_or_alpha_code():
    """
    Static guard mirroring DRIVER_SPECIFICATION.md section 14.1: the seam must
    import nothing from strategy/research/orchestration-bypass packages.
    """
    forbidden_roots = {
        "strategies", "backtest", "runner", "ftmo",
        "models", "scanners", "research", "analytics",
    }
    src_path = Path(__file__).resolve().parents[2] / "core" / "runtime" / "signal_source.py"
    tree = ast.parse(src_path.read_text(encoding="utf-8"))

    imported_roots: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
                if alias.name.startswith("core."):
                    imported_roots.add(alias.name.split(".")[1])
        elif isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            imported_roots.add(parts[0])
            if parts[0] == "core" and len(parts) > 1:
                imported_roots.add(parts[1])

    assert forbidden_roots.isdisjoint(imported_roots), (
        f"signal_source.py must not import strategy/alpha code; "
        f"found roots: {sorted(imported_roots)}"
    )
