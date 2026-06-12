"""
MM.7F #6a — W3 gate hardening: a raising `broker_positions` is a startup REFUSAL.

This file previously RED-documented hazard W3 (MM7_LIVE_WIRING_REVIEW.md §3.2):
a raising `broker_positions()` propagated uncaught out of `run()`, leaving the
driver stuck in RECOVERY with no STOPPED, no RECONCILIATION_FAIL, no journal.

#6a converts that escape into the same refusal contract as a real reconciliation
divergence and a master BLOCK: the gate catches the exception, emits
RECONCILIATION_FAIL, raises a critical alert, and calls abort_startup() →
STOPPED. The loop never runs (bars_processed == 0). These assertions are the
FLIP of the old defect pins — the failure is now a clean, durable refusal.

Scope: gate hardening only. No adapter, no reconciliation-logic change, no broker
change (MM7F §7 #6a).
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
    """Capture the driver's alerter — no Telegram I/O."""
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
# #6a core: the broker_positions exception is CAUGHT — run() does not raise and
# returns cleanly (refuse-to-start, not an escaped fault).
# --------------------------------------------------------------------------- #
def test_broker_positions_exception_does_not_escape_run(tmp_path, alerts):
    def boom():
        raise RuntimeError("broker auth failed")

    d = _driver(tmp_path, boom)
    d.run()   # no exception escapes the gate

    assert d.state is RuntimeState.STOPPED


# --------------------------------------------------------------------------- #
# #6a consequence: the driver reaches STOPPED (clean refusal), and the loop
# never ran — bars_processed == 0 (KEPT from the W3 characterization).
# --------------------------------------------------------------------------- #
def test_driver_reaches_stopped_after_broker_positions_raises(tmp_path, alerts):
    def boom():
        raise RuntimeError("broker transport down")

    d = _driver(tmp_path, boom)
    d.run()

    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 0   # loop never ran


# --------------------------------------------------------------------------- #
# #6a journal + alert: RECONCILIATION_FAIL and STOPPED are journaled, a critical
# alert fires, and no PASS/RUNNING is recorded — the durable refusal record the
# defect used to lack.
# --------------------------------------------------------------------------- #
def test_reconciliation_fail_and_stopped_journaled_with_critical_alert(tmp_path, alerts):
    def boom():
        raise RuntimeError("broker 401")

    d = _driver(tmp_path, boom)
    d.run()

    ev = _events(tmp_path)
    assert "RECOVERY_COMPLETED" in ev
    # The refusal contract — the FLIP of the old defect pins.
    assert "RECONCILIATION_FAIL" in ev
    assert "STOPPED" in ev
    # The gate refused before passing reconciliation or entering the loop.
    assert "RECONCILIATION_PASS" not in ev
    assert "RUNNING" not in ev
    # A broker-source failure is now loud, like any reconciliation refusal.
    assert "critical" in alerts.levels
