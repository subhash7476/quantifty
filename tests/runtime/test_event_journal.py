"""
Unit tests for core.runtime.event_journal — RuntimeEventJournal.

Validates the Runtime Event Journal contract in DRIVER_SPECIFICATION.md
section 15:
- JSONL append-only file, one object per line, order preserved (15.2);
- the 6-field record schema with tz-aware IST timestamp (15.3);
- the 14 required event types and their normative default severities (15.4),
  with caller override;
- write failure is non-fatal (15.6);
- the journal is write-only — never a source of position truth (15.7).

All tests route writes through tmp_path (no repo pollution).
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from core.runtime.event_journal import (
    EventType,
    RuntimeEventJournal,
    Severity,
    _DEFAULT_SEVERITY,
)

_IST = ZoneInfo("Asia/Kolkata")
_FIXED = datetime(2026, 6, 5, 9, 15, 0, tzinfo=_IST)


def _journal(tmp_path, now=None):
    return RuntimeEventJournal(
        path=str(tmp_path / "runtime_events.jsonl"),
        now=now or (lambda: _FIXED),
    )


def _read_lines(tmp_path):
    p = tmp_path / "runtime_events.jsonl"
    return p.read_text(encoding="utf-8").splitlines()


# --------------------------------------------------------------------------- #
# Schema (15.3)
# --------------------------------------------------------------------------- #
def test_record_returns_all_six_fields(tmp_path):
    rec = _journal(tmp_path).record(EventType.STARTUP, "driver starting",
                                    metadata={"mode": "LIVE"})
    assert set(rec.keys()) == {
        "timestamp", "event_type", "severity",
        "source_component", "message", "metadata",
    }


def test_enums_serialized_as_string_values(tmp_path):
    rec = _journal(tmp_path).record(EventType.PAUSED, "paused")
    assert rec["event_type"] == "PAUSED"
    assert rec["severity"] == "WARNING"
    assert isinstance(rec["event_type"], str) and isinstance(rec["severity"], str)


def test_timestamp_is_tz_aware_ist_iso8601(tmp_path):
    rec = _journal(tmp_path).record(EventType.RUNNING, "running")
    assert rec["timestamp"] == "2026-06-05T09:15:00+05:30"
    parsed = datetime.fromisoformat(rec["timestamp"])
    assert parsed.utcoffset() is not None  # tz-aware


# --------------------------------------------------------------------------- #
# JSONL append-only behavior (15.2)
# --------------------------------------------------------------------------- #
def test_each_record_is_one_json_line(tmp_path):
    j = _journal(tmp_path)
    j.record(EventType.STARTUP, "one")
    j.record(EventType.RUNNING, "two")
    lines = _read_lines(tmp_path)
    assert len(lines) == 2
    for line in lines:
        json.loads(line)  # each line is independently valid JSON


def test_append_only_preserves_prior_lines_and_order(tmp_path):
    j = _journal(tmp_path)
    j.record(EventType.STARTUP, "first")
    first_snapshot = _read_lines(tmp_path)
    j.record(EventType.STOPPING, "second", metadata={"trigger": "stop()"})
    lines = _read_lines(tmp_path)
    assert len(lines) == 2
    assert lines[0] == first_snapshot[0]          # earlier line untouched
    assert json.loads(lines[0])["message"] == "first"
    assert json.loads(lines[1])["message"] == "second"


def test_new_journal_appends_to_existing_file(tmp_path):
    _journal(tmp_path).record(EventType.STARTUP, "run-1")
    # A fresh journal pointed at the same path must append, not truncate.
    _journal(tmp_path).record(EventType.STOPPED, "run-2")
    lines = _read_lines(tmp_path)
    assert [json.loads(l)["message"] for l in lines] == ["run-1", "run-2"]


def test_parent_directory_is_created(tmp_path):
    nested = tmp_path / "deep" / "logs"
    j = RuntimeEventJournal(path=str(nested / "runtime_events.jsonl"),
                            now=lambda: _FIXED)
    j.record(EventType.STARTUP, "x")
    assert (nested / "runtime_events.jsonl").exists()


# --------------------------------------------------------------------------- #
# Event types + default severity (15.4)
# --------------------------------------------------------------------------- #
def test_all_fourteen_event_types_present():
    expected = {
        "STARTUP", "RECOVERY_STARTED", "RECOVERY_COMPLETED",
        "RECONCILIATION_PASS", "RECONCILIATION_FAIL", "RUNNING",
        "PAUSED", "RESUMED", "KILL_SWITCH_ACTIVATED", "WATCHDOG_STALE_DATA",
        "BROKER_ERROR", "TELEMETRY_FAILURE", "STOPPING", "STOPPED",
    }
    assert {e.value for e in EventType} == expected
    assert len(EventType) == 14


def test_default_severity_defined_for_every_event_type():
    # No event type may be missing from the severity map (would KeyError live).
    assert set(_DEFAULT_SEVERITY.keys()) == set(EventType)


@pytest.mark.parametrize("event_type,expected", [
    (EventType.STARTUP, "INFO"),
    (EventType.RECONCILIATION_PASS, "INFO"),
    (EventType.RECONCILIATION_FAIL, "CRITICAL"),
    (EventType.PAUSED, "WARNING"),
    (EventType.KILL_SWITCH_ACTIVATED, "CRITICAL"),
    (EventType.WATCHDOG_STALE_DATA, "CRITICAL"),
    (EventType.BROKER_ERROR, "WARNING"),
    (EventType.TELEMETRY_FAILURE, "WARNING"),
    (EventType.STOPPED, "INFO"),
])
def test_normative_default_severities(tmp_path, event_type, expected):
    assert _journal(tmp_path).record(event_type, "msg")["severity"] == expected


def test_severity_override_wins(tmp_path):
    rec = _journal(tmp_path).record(EventType.BROKER_ERROR,
                                    "handshake failed at startup",
                                    severity=Severity.CRITICAL)
    assert rec["severity"] == "CRITICAL"


# --------------------------------------------------------------------------- #
# source_component + metadata
# --------------------------------------------------------------------------- #
def test_source_component_default_and_override(tmp_path):
    j = _journal(tmp_path)
    assert j.record(EventType.RUNNING, "x")["source_component"] == "LoopDriver"
    overridden = j.record(EventType.WATCHDOG_STALE_DATA, "stale",
                          source_component="RuntimeWatchdog")
    assert overridden["source_component"] == "RuntimeWatchdog"


def test_metadata_defaults_to_empty_dict_and_passthrough(tmp_path):
    j = _journal(tmp_path)
    assert j.record(EventType.RESUMED, "x")["metadata"] == {}
    meta = {"reason": "operator", "minutes_stale": 7}
    assert j.record(EventType.PAUSED, "x", metadata=meta)["metadata"] == meta


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def test_non_event_type_rejected(tmp_path):
    with pytest.raises(TypeError, match="event_type"):
        _journal(tmp_path).record("STARTUP", "x")  # type: ignore[arg-type]


def test_non_severity_override_rejected(tmp_path):
    with pytest.raises(TypeError, match="severity"):
        _journal(tmp_path).record(EventType.STARTUP, "x", severity="INFO")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Failure policy (15.6) + authority boundary (15.7)
# --------------------------------------------------------------------------- #
def test_write_failure_is_non_fatal(tmp_path):
    # Point the journal at a path that is an existing directory -> append fails.
    bad = tmp_path / "as_dir.jsonl"
    bad.mkdir()
    j = RuntimeEventJournal(path=str(bad), now=lambda: _FIXED)
    # Must not raise; returns the record it attempted to write (15.6).
    rec = j.record(EventType.BROKER_ERROR, "still alive", severity=Severity.CRITICAL)
    assert rec["event_type"] == "BROKER_ERROR"


def test_journal_is_write_only_no_position_truth_api():
    # 15.7: the journal must expose no read/reconstruct surface.
    public = {n for n in dir(RuntimeEventJournal) if not n.startswith("_")}
    forbidden = {"read", "load", "reconstruct", "positions", "replay",
                 "get_positions", "rebuild", "query"}
    assert public == {"record"}
    assert forbidden.isdisjoint(public)
