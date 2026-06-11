"""
MM.7A — W3 characterization: a raising `broker_positions` escapes `run()` uncaught.

Pins the CURRENT (defective) behavior the MM.7 wiring review named as hazard W3
(MM7_LIVE_WIRING_REVIEW.md §3.2; PROJECT_STATE.md Planned #6). The startup gate
calls `self._broker_positions()` inside `_reconcile_ledger`, which runs BEFORE
`run()`'s `try/finally` (driver.py:508-524). So when the injected broker-book
callable raises (broker auth / transport fault), the exception propagates
straight out of `run()` and the driver is left stuck in RECOVERY — no STOPPED,
no RECONCILIATION_FAIL, no journal record of a refusal.

This is a RED-documenting characterization: the assertions encode the defect, so
the test is GREEN today and FLIPS when Planned #6 converts the failure into a
startup refusal → journal event → STOPPED (the same contract as
RECONCILIATION_FAIL). It does NOT fix W3.
"""

import json

import pytest

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      bar_series)

_DERIV = "NSE_FO|53001"


@pytest.fixture
def alerts(monkeypatch):
    """Silence the driver's alerter — no Telegram I/O."""
    class _Rec:
        def __init__(self):
            self.levels = []

        def info(self, m):
            self.levels.append("info")

        def warning(self, m):
            self.levels.append("warning")

        def critical(self, m):
            self.levels.append("critical")

    rec = _Rec()
    monkeypatch.setattr("core.runtime.driver.alerter", rec)
    return rec


def _events(tmp_path):
    p = tmp_path / "runtime_events.jsonl"
    if not p.exists():
        return []
    return [json.loads(l)["event_type"] for l in p.read_text().splitlines()]


def _driver(tmp_path, broker_positions):
    """LIVE + derivative driver with no master checker (vacuous readiness pass),
    so the gate reaches reconciliation, where broker_positions is invoked."""
    cfg = DriverConfig(mode=Mode.LIVE, symbols=[_DERIV], max_bars=2,
                       poll_interval_s=0.25)
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=[])
    return LoopDriver(
        cfg, clock=FakeClock(),
        provider=FakeMarketDataProvider({_DERIV: bar_series(_DERIV, 3)}, live=True),
        journal=journal, execution=handler,
        broker_positions=broker_positions,
        master_readiness=None,
    )


# --------------------------------------------------------------------------- #
# W3 core: the broker_positions exception propagates uncaught out of run().
# --------------------------------------------------------------------------- #
def test_broker_positions_exception_escapes_run(tmp_path, alerts):
    def boom():
        raise RuntimeError("broker auth failed")

    d = _driver(tmp_path, boom)
    with pytest.raises(RuntimeError, match="broker auth failed"):
        d.run()


# --------------------------------------------------------------------------- #
# W3 consequence: the driver is left stuck in RECOVERY — never STOPPED.
# --------------------------------------------------------------------------- #
def test_driver_remains_recovery_after_broker_positions_raises(tmp_path, alerts):
    def boom():
        raise RuntimeError("broker transport down")

    d = _driver(tmp_path, boom)
    with pytest.raises(RuntimeError):
        d.run()

    # The defect: stuck mid-startup, not a clean refusal.
    assert d.state is RuntimeState.RECOVERY
    assert d.bars_processed == 0   # loop never ran


# --------------------------------------------------------------------------- #
# W3 journal gap: recovery progressed, but there is NO STOPPED and NO
# RECONCILIATION_FAIL — the failure leaves no durable refusal record.
# --------------------------------------------------------------------------- #
def test_no_stopped_or_reconciliation_fail_journaled(tmp_path, alerts):
    def boom():
        raise RuntimeError("broker 401")

    d = _driver(tmp_path, boom)
    with pytest.raises(RuntimeError):
        d.run()

    ev = _events(tmp_path)
    # The gate got as far as reusing recovery before reconcile raised.
    assert "RECOVERY_COMPLETED" in ev
    # The defect surface: none of the clean-refusal events were emitted.
    assert "RECONCILIATION_FAIL" not in ev
    assert "RECONCILIATION_PASS" not in ev
    assert "STOPPED" not in ev
    assert "RUNNING" not in ev
    # No critical alert either — W3 is silent, unlike RECONCILIATION_FAIL.
    assert alerts.levels == []
