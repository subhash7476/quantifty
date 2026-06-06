"""
Unit tests for LoopDriver Phase F — Startup Gate / Recovery.

Validates DRIVER_SPECIFICATION.md §11 / ADR-001 / Constitution §7, and the
working-sequence addition that LIVE mode requires an injected ExecutionHandler
(docs/PHASE_F_STARTUP_GATE_PLAN.md §3.1):

- gate runs when an ExecutionHandler is injected: RECOVERY_STARTED →
  RECOVERY_COMPLETED → RECONCILIATION_PASS → RUNNING, in that order;
- a non-empty reconcile result refuses to start (STOPPED + RECONCILIATION_FAIL,
  loop never runs);
- the driver never re-restores state itself (reuse _replay_state, ADR-001);
- reconciliation is driven only when a broker-positions source is handed in;
  with no source it is vacuously clear (PASS, reconcile not called) — including
  in LIVE, where real broker-book fetch is deferred (Planned #6);
- require_reconciliation_on_start=False skips reconciliation;
- LIVE without a handler raises (wiring error); REPLAY without a handler runs
  ungated (Phases A–E behavior preserved);
- a gate abort never starts/stops the SignalSource and runs zero bars.

Still execution-free — no process_signal anywhere (ADR-006).
"""

import json

import pytest

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, bar_series)

_POS = [{"symbol": "A", "qty": 1}]            # any non-empty broker book


def _live_cfg(symbols=("A",), max_bars=None, poll=0.25, require_recon=True):
    return DriverConfig(mode=Mode.LIVE, symbols=list(symbols), max_bars=max_bars,
                        poll_interval_s=poll,
                        require_reconciliation_on_start=require_recon)


def _replay_cfg(symbols=("A",), max_bars=None):
    return DriverConfig(mode=Mode.REPLAY, symbols=list(symbols), max_bars=max_bars)


def _events(tmp_path):
    return [json.loads(l)["event_type"]
            for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]


# --------------------------------------------------------------------------- #
# Gate pass: recovery + reconciliation events, in order, then RUNNING
# --------------------------------------------------------------------------- #
def test_gate_pass_reaches_running_with_events_in_order(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=[])
    d = LoopDriver(_live_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}, live=True),
                   journal=journal, execution=handler,
                   broker_positions=lambda: _POS)
    d.run()
    ev = _events(tmp_path)
    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 2
    for earlier, later in [("STARTUP", "RECOVERY_STARTED"),
                           ("RECOVERY_STARTED", "RECOVERY_COMPLETED"),
                           ("RECOVERY_COMPLETED", "RECONCILIATION_PASS"),
                           ("RECONCILIATION_PASS", "RUNNING")]:
        assert ev.index(earlier) < ev.index(later)
    assert handler.reconciliation.reconcile_calls == [_POS]   # called with the book


# --------------------------------------------------------------------------- #
# Gate fail: non-empty reconcile → refuse to start
# --------------------------------------------------------------------------- #
def test_reconciliation_fail_refuses_to_start(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=["DIVERGENCE"])
    d = LoopDriver(_live_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}, live=True),
                   journal=journal, execution=handler,
                   broker_positions=lambda: _POS)
    d.run()
    ev = _events(tmp_path)
    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 0                # loop never ran
    assert "RECONCILIATION_FAIL" in ev
    assert "RUNNING" not in ev
    assert ev.index("RECOVERY_COMPLETED") < ev.index("RECONCILIATION_FAIL")
    # The refusal is recorded CRITICAL (plan §7 / journal default severity).
    records = [json.loads(l)
               for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]
    fail = next(r for r in records if r["event_type"] == "RECONCILIATION_FAIL")
    assert fail["severity"] == "CRITICAL"


# --------------------------------------------------------------------------- #
# Recovery is reused, never re-run by the driver (ADR-001)
# --------------------------------------------------------------------------- #
def test_gate_does_not_re_restore_state():
    handler = FakeExecutionHandler(reconcile_alerts=[])
    d = LoopDriver(_live_cfg(max_bars=1), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 2)}, live=True),
                   execution=handler)
    d.run()
    assert handler.replay_state_calls == 0     # driver must not call _replay_state


# --------------------------------------------------------------------------- #
# LIVE requires a handler; REPLAY does not (§3.1)
# --------------------------------------------------------------------------- #
def test_live_without_handler_raises():
    d = LoopDriver(_live_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 2)}, live=True))
    with pytest.raises(RuntimeError, match="LIVE mode requires an injected ExecutionHandler"):
        d.run()


def test_replay_no_handler_runs_ungated(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    d = LoopDriver(_replay_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   journal=journal)
    d.run()
    ev = _events(tmp_path)
    assert d.bars_processed == 3
    assert d.state is RuntimeState.STOPPED
    assert "RECOVERY_STARTED" not in ev        # gate skipped (no handler, not live)
    assert "RECONCILIATION_PASS" not in ev
    assert ev[:2] == ["STARTUP", "RUNNING"]


# --------------------------------------------------------------------------- #
# Vacuous reconciliation: no broker-positions source => PASS, reconcile not called
# --------------------------------------------------------------------------- #
def test_replay_with_handler_no_source_is_vacuous_pass(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=["WOULD-FAIL"])   # ignored: no source
    d = LoopDriver(_replay_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   journal=journal, execution=handler)
    d.run()
    ev = _events(tmp_path)
    assert handler.reconciliation.reconcile_calls == []   # never called
    assert "RECONCILIATION_PASS" in ev
    assert "RECONCILIATION_FAIL" not in ev
    assert "RUNNING" in ev


def test_live_with_handler_no_source_is_vacuous_pass(tmp_path):
    # LIVE reconciliation is structurally present but vacuous until the broker
    # book source is wired (Planned #6) — execution-free, nothing to protect yet.
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=["WOULD-FAIL"])
    d = LoopDriver(_live_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}, live=True),
                   journal=journal, execution=handler)            # no broker_positions
    d.run()
    ev = _events(tmp_path)
    assert handler.reconciliation.reconcile_calls == []
    assert "RECONCILIATION_PASS" in ev
    assert "RUNNING" in ev
    assert d.state is RuntimeState.STOPPED


def test_require_reconciliation_false_skips_reconcile(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=["WOULD-FAIL"])
    d = LoopDriver(_live_cfg(max_bars=2, require_recon=False), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}, live=True),
                   journal=journal, execution=handler,
                   broker_positions=lambda: _POS)               # present but overridden
    d.run()
    ev = _events(tmp_path)
    assert handler.reconciliation.reconcile_calls == []   # override skips reconcile
    assert "RECONCILIATION_PASS" in ev
    assert "RUNNING" in ev


# --------------------------------------------------------------------------- #
# A gate abort never starts/stops the source and runs zero bars
# --------------------------------------------------------------------------- #
def test_gate_abort_does_not_touch_source():
    handler = FakeExecutionHandler(reconcile_alerts=["DIVERGENCE"])
    source = FakeSignalSource()
    d = LoopDriver(_live_cfg(max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}, live=True),
                   execution=handler, source=source,
                   broker_positions=lambda: _POS)
    d.run()
    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 0
    assert source.started == 0                 # on_start never fired
    assert source.stopped == 0                 # on_stop never fired
