"""
Unit tests for LoopDriver Phase G — Execution Routing (the smallest slice).

Validates DRIVER_SPECIFICATION.md §8.1 / §4.1 step 4 / ADR-005 / ADR-006: when a
SignalSource emits SignalEvents, the LoopDriver — and only the LoopDriver — routes
each, in list order, to the canonical entry point
`ExecutionHandler.process_signal(signal, current_price=bar.close)`.

Proven here (the eight Phase-G requirements):
1. a signal emitted by the source is received by the ExecutionHandler, with
   current_price == bar.close (§8.1: always bar.close);
2. multiple signals are routed in list order (priority order is never re-ranked);
3. no signals → no execution calls (and counting still works);
4. existing watchdog behavior is undisturbed by routing (record_bar / heartbeat
   counters unchanged while routing fires);
5. existing journal behavior is unchanged — routing adds no new event types;
6. existing startup-gate behavior is unchanged — routing is blocked when the gate
   refuses to start (and only begins once RUNNING);
7. routing is deterministic — identical signals over identical bars produce an
   identical sequence of process_signal calls (live == replay path, §14.2);
8. ADR-006 is preserved — the driver is the SOLE runtime router; the SignalSource
   seam holds no execution coupling, and PAUSED suspends routing (§3.1) so routing
   only ever happens through the driver's RUNNING loop.

Scope is deliberately narrow (§8.2/§8.3/§8.4 deferred): the driver constructs and
submits no orders, handles no fills, and per-signal exception isolation /
BROKER_ERROR is the next Phase-G increment — not in this slice.
"""

import ast
import json
from pathlib import Path

from core.events import SignalType
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, FakeWatchdog, bar_series, make_bar,
                      make_signal)


def _replay_cfg(symbols=("A",), max_bars=None):
    return DriverConfig(mode=Mode.REPLAY, symbols=list(symbols), max_bars=max_bars)


def _live_cfg(symbols=("A",), max_bars=None, poll=0.25, require_recon=True):
    return DriverConfig(mode=Mode.LIVE, symbols=list(symbols), max_bars=max_bars,
                        poll_interval_s=poll,
                        require_reconciliation_on_start=require_recon)


def _events(tmp_path):
    return [json.loads(l)["event_type"]
            for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]


# --------------------------------------------------------------------------- #
# (1) signal emitted → ExecutionHandler receives it, priced at bar.close
# --------------------------------------------------------------------------- #
def test_signal_is_routed_to_execution_handler_at_bar_close():
    handler = FakeExecutionHandler()
    sig = make_signal("A")
    source = FakeSignalSource([[sig]])
    d = LoopDriver(_replay_cfg(max_bars=1), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": [make_bar("A", close=123.5)]}),
                   source=source, execution=handler)
    d.run()
    assert handler.routed == [(sig, 123.5)]        # received once, current_price=bar.close


# --------------------------------------------------------------------------- #
# (2) multiple signals routed in list order, across bars
# --------------------------------------------------------------------------- #
def test_multiple_signals_routed_in_list_order():
    handler = FakeExecutionHandler()
    s0 = [make_signal("A", SignalType.SELL), make_signal("B", SignalType.BUY)]
    s1 = [make_signal("C", SignalType.EXIT)]
    source = FakeSignalSource([s0, s1])            # bar0 → 2 signals, bar1 → 1
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source, execution=handler)
    d.run()
    assert [sig for sig, _ in handler.routed] == [s0[0], s0[1], s1[0]]   # exact order + identity


# --------------------------------------------------------------------------- #
# (3) no signals → no execution calls (counting still runs)
# --------------------------------------------------------------------------- #
def test_no_signals_means_no_execution_calls():
    handler = FakeExecutionHandler()
    source = FakeSignalSource()                    # every on_bar returns []
    d = LoopDriver(_replay_cfg(max_bars=3), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 4)}),
                   source=source, execution=handler)
    d.run()
    assert handler.routed == []
    assert d.signals_pulled == 0
    assert d.bars_processed == 3


# --------------------------------------------------------------------------- #
# (4) routing does not disturb the watchdog (live) — counters unchanged
# --------------------------------------------------------------------------- #
def test_routing_does_not_disturb_watchdog():
    wd = FakeWatchdog()
    handler = FakeExecutionHandler()
    source = FakeSignalSource([[make_signal("A")], [make_signal("A")], [make_signal("A")]])
    d = LoopDriver(_live_cfg(max_bars=3), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 5)}, live=True),
                   source=source, execution=handler, watchdog=wd)
    d.run()
    assert wd.record_bar_calls == 3                # one per processed bar (unchanged)
    assert wd.heartbeats == [1, 2, 3]              # per-tick heartbeat (unchanged)
    assert len(handler.routed) == 3               # routing fired alongside, undisturbed


# --------------------------------------------------------------------------- #
# (5) routing adds no new journal event types
# --------------------------------------------------------------------------- #
def test_routing_emits_no_new_journal_events(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler()
    source = FakeSignalSource([[make_signal("A")], [make_signal("A")]])
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source, execution=handler, journal=journal)
    d.run()
    ev = set(_events(tmp_path))
    # The slice introduces no execution-specific journal events (BROKER_ERROR is
    # deferred). The set is exactly the standard startup-gate + lifecycle events.
    assert ev <= {"STARTUP", "RECOVERY_STARTED", "RECOVERY_COMPLETED",
                  "RECONCILIATION_PASS", "RUNNING", "STOPPING", "STOPPED"}
    assert "BROKER_ERROR" not in ev
    assert len(handler.routed) == 2               # routing actually happened


# --------------------------------------------------------------------------- #
# (6) startup gate unchanged — a gate refusal blocks all routing
# --------------------------------------------------------------------------- #
def test_routing_blocked_when_startup_gate_refuses():
    handler = FakeExecutionHandler(reconcile_alerts=["DIVERGENCE"])
    source = FakeSignalSource([[make_signal("A")]])
    d = LoopDriver(_live_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}, live=True),
                   source=source, execution=handler,
                   broker_positions=lambda: [{"symbol": "A", "qty": 1}])
    d.run()
    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 0                   # loop never ran
    assert handler.routed == []                    # nothing routed — gate refused first


# --------------------------------------------------------------------------- #
# (7) routing is deterministic across identical runs
# --------------------------------------------------------------------------- #
def test_routing_is_deterministic_across_identical_runs():
    def run_once():
        handler = FakeExecutionHandler()
        script = [[make_signal("A", SignalType.BUY)],
                  [make_signal("B", SignalType.SELL)]]
        source = FakeSignalSource(script)
        d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                       provider=FakeMarketDataProvider({"A": bar_series("A", 2)}),
                       source=source, execution=handler)
        d.run()
        return [(sig.symbol, sig.signal_type, price) for sig, price in handler.routed]

    assert run_once() == run_once()


# --------------------------------------------------------------------------- #
# (8) ADR-006 — driver is the sole router; seam has no coupling; PAUSED suspends
# --------------------------------------------------------------------------- #
def test_signal_source_seam_has_no_execution_coupling():
    # §5.4 / ADR-006: the seam cannot route — it neither imports the
    # ExecutionHandler nor names process_signal. Routing exists ONLY in the driver.
    src_path = Path(__file__).resolve().parents[2] / "core" / "runtime" / "signal_source.py"
    text = src_path.read_text(encoding="utf-8")
    tree = ast.parse(text)

    names_process_signal = any(
        isinstance(n, ast.Attribute) and n.attr == "process_signal"
        for n in ast.walk(tree)
    )
    imports_handler = any(
        isinstance(n, ast.ImportFrom) and n.module and "execution" in n.module
        for n in ast.walk(tree)
    )
    assert not names_process_signal
    assert not imports_handler


def test_running_driver_routes_through_process_signal():
    # The positive ADR-006 truth: in RUNNING, the driver IS the caller of
    # process_signal, pairing each signal with bar.close.
    handler = FakeExecutionHandler()
    d = LoopDriver(_replay_cfg(), execution=handler)   # lifecycle-only; no run()
    d.start()                                          # STARTUP → RUNNING
    sig = make_signal("A")
    d._dispatch_signals([sig], make_bar("A", close=77.0))
    assert handler.routed == [(sig, 77.0)]


def test_paused_driver_collects_but_does_not_route():
    # §3.1: PAUSED suspends routing without going blind — signals are still
    # collected/counted, but no new process_signal call is made.
    handler = FakeExecutionHandler()
    d = LoopDriver(_replay_cfg(), execution=handler)
    d.start()                                          # → RUNNING
    d.pause()                                          # → PAUSED
    assert d.state is RuntimeState.PAUSED
    d._dispatch_signals([make_signal("A")], make_bar("A", close=50.0))
    assert handler.routed == []                        # routing suspended
    assert d.signals_pulled == 1                       # but still collected/counted


def test_no_handler_collects_but_does_not_route():
    # The no-handler path (replay/inert/test) has nothing to route to: signals are
    # collected/counted only, exactly as Phase D — routing is presence-gated.
    source = FakeSignalSource([[make_signal("A"), make_signal("B")]])
    d = LoopDriver(_replay_cfg(max_bars=1), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": [make_bar("A")]}),
                   source=source)                       # no execution handler
    d.run()
    assert d.signals_pulled == 2
    assert d.state is RuntimeState.STOPPED
