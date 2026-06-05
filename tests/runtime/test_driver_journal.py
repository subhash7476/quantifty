"""
Unit tests for LoopDriver Phase B — journal emission on transitions.

Validates DRIVER_SPECIFICATION.md §15 wiring into the §3 lifecycle:
- STARTUP emitted on construction; RUNNING/PAUSED/RESUMED/STOPPING/STOPPED on
  their transitions, once per occurrence (edge-triggered);
- illegal transitions and enter_recovery emit nothing (Phase B scope);
- the journal is optional (no-op when absent) and write failure is non-fatal.

All journal writes route through tmp_path (no repo pollution).
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import InvalidStateTransition, LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal

_FIXED = datetime(2026, 6, 5, 9, 15, 0, tzinfo=ZoneInfo("Asia/Kolkata"))


def _driver_with_journal(tmp_path):
    journal = RuntimeEventJournal(
        path=str(tmp_path / "runtime_events.jsonl"),
        now=lambda: _FIXED,
    )
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=["NSE_INDEX|Nifty 50"])
    return LoopDriver(cfg, journal=journal)


def _events(tmp_path):
    p = tmp_path / "runtime_events.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()]


def _types(tmp_path):
    return [e["event_type"] for e in _events(tmp_path)]


# --------------------------------------------------------------------------- #
# Construction emits STARTUP
# --------------------------------------------------------------------------- #
def test_construction_emits_startup(tmp_path):
    _driver_with_journal(tmp_path)
    events = _events(tmp_path)
    assert len(events) == 1
    assert events[0]["event_type"] == "STARTUP"
    assert events[0]["severity"] == "INFO"
    assert events[0]["metadata"]["mode"] == "REPLAY"
    assert events[0]["metadata"]["symbols"] == ["NSE_INDEX|Nifty 50"]


# --------------------------------------------------------------------------- #
# Per-transition emission
# --------------------------------------------------------------------------- #
def test_start_emits_running(tmp_path):
    d = _driver_with_journal(tmp_path)
    d.start()
    assert _types(tmp_path) == ["STARTUP", "RUNNING"]


def test_pause_emits_paused_with_warning_severity(tmp_path):
    d = _driver_with_journal(tmp_path)
    d.start()
    d.pause()
    events = _events(tmp_path)
    assert events[-1]["event_type"] == "PAUSED"
    assert events[-1]["severity"] == "WARNING"


def test_resume_emits_resumed(tmp_path):
    d = _driver_with_journal(tmp_path)
    d.start()
    d.pause()
    d.resume()
    assert _types(tmp_path)[-1] == "RESUMED"


def test_stop_emits_stopping(tmp_path):
    d = _driver_with_journal(tmp_path)
    d.start()
    d.stop()
    assert _types(tmp_path)[-1] == "STOPPING"


def test_finalize_stop_emits_stopped(tmp_path):
    d = _driver_with_journal(tmp_path)
    d.start()
    d.stop()
    d.finalize_stop()
    assert _types(tmp_path)[-1] == "STOPPED"


def test_abort_startup_emits_stopped(tmp_path):
    d = _driver_with_journal(tmp_path)
    d.abort_startup()
    assert _types(tmp_path) == ["STARTUP", "STOPPED"]


def test_full_lifecycle_emits_expected_sequence(tmp_path):
    d = _driver_with_journal(tmp_path)
    d.start()
    d.pause()
    d.resume()
    d.stop()
    d.finalize_stop()
    assert _types(tmp_path) == [
        "STARTUP", "RUNNING", "PAUSED", "RESUMED", "STOPPING", "STOPPED",
    ]


# --------------------------------------------------------------------------- #
# Edge-triggering: nothing emitted on illegal transitions or recovery
# --------------------------------------------------------------------------- #
def test_illegal_transition_emits_nothing(tmp_path):
    d = _driver_with_journal(tmp_path)  # STARTUP, 1 event
    with pytest.raises(InvalidStateTransition):
        d.pause()  # illegal from STARTUP
    assert _types(tmp_path) == ["STARTUP"]  # no PAUSED line written


def test_enter_recovery_emits_nothing_in_phase_b(tmp_path):
    d = _driver_with_journal(tmp_path)
    d.enter_recovery()
    assert d.state is RuntimeState.RECOVERY
    assert _types(tmp_path) == ["STARTUP"]  # recovery events deferred to a later phase


def test_each_transition_emits_exactly_once(tmp_path):
    d = _driver_with_journal(tmp_path)
    d.start()
    # No duplicate RUNNING lines from a single start().
    assert _types(tmp_path).count("RUNNING") == 1


# --------------------------------------------------------------------------- #
# Journal is optional and write failure is non-fatal
# --------------------------------------------------------------------------- #
def test_no_journal_is_optional_and_transitions_still_work():
    d = LoopDriver(DriverConfig(mode=Mode.REPLAY, symbols=["A"]))  # no journal
    d.start()
    d.pause()
    d.resume()
    d.stop()
    d.finalize_stop()
    assert d.state is RuntimeState.STOPPED  # full lifecycle, no journal, no error


def test_journal_write_failure_does_not_break_transitions(tmp_path):
    # Journal pointed at a directory -> every append fails internally (swallowed).
    bad = tmp_path / "as_dir.jsonl"
    bad.mkdir()
    journal = RuntimeEventJournal(path=str(bad), now=lambda: _FIXED)
    d = LoopDriver(DriverConfig(mode=Mode.REPLAY, symbols=["A"]), journal=journal)
    d.start()  # must not raise despite journal write failing
    assert d.state is RuntimeState.RUNNING
