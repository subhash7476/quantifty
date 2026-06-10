"""
Gate G1 — Wave 3B driver-level gate-ordering characterization.

Pins the CURRENT startup-gate call sequence so the Wave 3 Option-B post-gate
canonicalization pass has an executable insertion contract. This is the
driver-level post-gate ordering test deliberately deferred in Wave 3A
(G1_WAVE3A_CHARACTERIZATION_REPORT.md §7 gap 1) and named as the precondition
for Wave 3 implementation (G1_WAVE3_RESTORE_REVIEW.md §4 gap 4 / §6 step 2).
NO production code is changed; the hook does not exist yet — these tests
characterize the SLOT it will occupy.

The startup gate (driver.py:335-364 `_run_startup_gate`):

    enter_recovery()                                          driver.py:346
    RECOVERY_STARTED / RECOVERY_COMPLETED  (reuse _replay_state, never re-run)
    _check_master_readiness()   -> MM.4 gate                  driver.py:357
        <------------------- OPTION-B HOOK INSERTION POINT
    _reconcile_ledger()         -> reconciliation             driver.py:360
    start()                     -> RUNNING                    driver.py:363

Why a CALL-order spy and not just journal events: on the FRESH path
`_check_master_readiness` emits NO journal event (only WARN/BLOCK do), so the
journal shows RECOVERY_COMPLETED directly followed by RECONCILIATION_PASS with
nothing between — the readiness check is invisible to the journal there. The
hook's slot (strictly after readiness, strictly before reconcile) is therefore
provable only by recording the actual call sequence. The existing journal-event
ordering test (test_driver_master_readiness.py::test_master_check_runs_before_
reconciliation) covers the WARN path only; this file pins the call-level slot on
every verdict.
"""

import json
from datetime import date

import pytest

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal
from core.instruments.master_readiness import ReadinessState, ReadinessVerdict

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      bar_series)

_DERIV = "NSE_FO|53001"

_FRESH = ReadinessVerdict(ReadinessState.FRESH, None, date(2026, 6, 8), date(2026, 6, 8))
_WARN = ReadinessVerdict(ReadinessState.WARN, None, date(2026, 6, 5), date(2026, 6, 8))
_BLOCK = ReadinessVerdict(ReadinessState.BLOCK, "coverage", date(2026, 6, 8), date(2026, 6, 8))


@pytest.fixture
def alerts(monkeypatch):
    """Silence the driver's alerter (WARN/BLOCK call it) — no Telegram I/O."""
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


def _build(tmp_path, verdict, *, require_recon=True, broker=True):
    """A LIVE + derivative driver with a shared call recorder spanning BOTH gate
    steps: the master-readiness checker appends "READINESS", the reconciliation
    engine appends "RECONCILE". `seq` is therefore the exact interleaving the
    Option-B hook inserts into. `verdict=None` injects no checker (the current
    live-F&O-deferred reality: master_readiness wiring lands with the F&O entry
    script)."""
    seq = []
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=[])

    _real_reconcile = handler.reconciliation.reconcile

    def _recording_reconcile(broker_positions):
        seq.append("RECONCILE")
        return _real_reconcile(broker_positions)

    handler.reconciliation.reconcile = _recording_reconcile

    if verdict is None:
        readiness = None
    else:
        def readiness():
            seq.append("READINESS")
            return verdict

    cfg = DriverConfig(mode=Mode.LIVE, symbols=[_DERIV], max_bars=2,
                       poll_interval_s=0.25,
                       require_reconciliation_on_start=require_recon)
    d = LoopDriver(
        cfg, clock=FakeClock(),
        provider=FakeMarketDataProvider({_DERIV: bar_series(_DERIV, 3)}, live=True),
        journal=journal, execution=handler,
        broker_positions=(lambda: []) if broker else None,
        master_readiness=readiness,
    )
    return d, seq


def _events(tmp_path):
    return [json.loads(l)["event_type"]
            for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]


# --------------------------------------------------------------------------- #
# FRESH — the core insertion contract: readiness strictly before reconcile.
# The Option-B canonicalization pass slots between them: the post-migration
# sequence becomes ["READINESS", "CANONICALIZE", "RECONCILE"].
# --------------------------------------------------------------------------- #
def test_fresh_call_order_is_readiness_then_reconcile(tmp_path, alerts):
    d, seq = _build(tmp_path, _FRESH)
    d.run()
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert seq == ["READINESS", "RECONCILE"]   # the hook inserts at index 1


# --------------------------------------------------------------------------- #
# FRESH — WHY the journal cannot locate the slot: no master event is emitted on
# FRESH, so RECOVERY_COMPLETED is immediately followed by RECONCILIATION_PASS.
# The call-order spy above is the only proof the readiness check ran in the slot.
# --------------------------------------------------------------------------- #
def test_fresh_journal_has_no_master_event_in_the_slot(tmp_path, alerts):
    d, _ = _build(tmp_path, _FRESH)
    d.run()
    ev = _events(tmp_path)
    assert "INSTRUMENT_MASTER_STALE" not in ev
    assert "INSTRUMENT_MASTER_UNAVAILABLE" not in ev
    # Nothing between RECOVERY_COMPLETED and RECONCILIATION_PASS in the journal.
    assert ev.index("RECONCILIATION_PASS") == ev.index("RECOVERY_COMPLETED") + 1


# --------------------------------------------------------------------------- #
# WARN — the gate still passes, so the call slot is identical to FRESH: the
# Option-B hook runs on WARN too (a 1-day-stale-but-present master is usable).
# --------------------------------------------------------------------------- #
def test_warn_call_order_is_readiness_then_reconcile(tmp_path, alerts):
    d, seq = _build(tmp_path, _WARN)
    d.run()
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert seq == ["READINESS", "RECONCILE"]
    assert alerts.levels == ["warning"]
    ev = _events(tmp_path)
    # On WARN the journal DOES mark the slot (unlike FRESH).
    assert ev.index("INSTRUMENT_MASTER_STALE") < ev.index("RECONCILIATION_PASS")


# --------------------------------------------------------------------------- #
# BLOCK — the gate refuses to start: reconcile is never reached, so the hook
# (which sits before reconcile) is never reached either. Canonicalization only
# runs when the master is proven ready — never on a BLOCK.
# --------------------------------------------------------------------------- #
def test_block_stops_before_reconcile_and_before_hook_slot(tmp_path, alerts):
    d, seq = _build(tmp_path, _BLOCK)
    d.run()
    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 0                # loop never ran
    assert seq == ["READINESS"]                 # reconcile (and the hook) unreached
    assert alerts.levels == ["critical"]
    ev = _events(tmp_path)
    assert "RECONCILIATION_PASS" not in ev
    assert "RUNNING" not in ev


# --------------------------------------------------------------------------- #
# No checker injected (today's live-F&O-deferred reality) — readiness is a
# vacuous pass and is never invoked, so only RECONCILE is recorded. The Option-B
# hook will gate on the SAME condition as MM.4 (is_live ∧ has_derivatives ∧
# master-ready), so a no-checker live-derivative run does NOT canonicalize —
# consistent with the MM.4 vacuous-pass contract.
# --------------------------------------------------------------------------- #
def test_no_checker_records_reconcile_only(tmp_path, alerts):
    d, seq = _build(tmp_path, None)
    d.run()
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert seq == ["RECONCILE"]                 # readiness never invoked
    ev = _events(tmp_path)
    assert "INSTRUMENT_MASTER_UNAVAILABLE" not in ev
    assert "RECONCILIATION_PASS" in ev
