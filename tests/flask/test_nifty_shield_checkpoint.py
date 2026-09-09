"""The NiftyShield panel's 13:00-checkpoint answer.

The panel exists so the operator does not read the journal to learn whether the
checkpoint fired. The states must be derivable from the session-scoped facts
store plus the wall clock alone.
"""
from datetime import datetime

import duckdb
import pytest

from flask_app.blueprints import nifty_shield


def _facts_store(root, sessions):
    con = duckdb.connect(str(root / "facts.duckdb"))
    con.execute("CREATE TABLE day_type_facts (session_date DATE, checkpoint VARCHAR)")
    for s in sessions:
        con.execute("INSERT INTO day_type_facts VALUES (?, '13pm')", [s])
    con.close()


def _journal(root, lines):
    (root / "journal.jsonl").write_text("\n".join(lines), encoding="utf-8")


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.setattr(nifty_shield, "DATA_ROOT", tmp_path)
    return tmp_path


def test_reports_fired_when_todays_fact_is_in_the_session_scoped_store(data_root):
    _facts_store(data_root, ["2026-09-09"])

    result = nifty_shield._checkpoint_status("2026-09-09", now=datetime(2026, 9, 9, 13, 45))

    assert result["state"] == "published"
    assert result["fact_published_today"] is True


def test_reports_not_due_before_the_checkpoint(data_root):
    _facts_store(data_root, [])

    result = nifty_shield._checkpoint_status("2026-09-09", now=datetime(2026, 9, 9, 11, 0))

    assert result["state"] == "not_due"


def test_reports_pending_inside_the_retry_window(data_root):
    _facts_store(data_root, [])

    result = nifty_shield._checkpoint_status("2026-09-09", now=datetime(2026, 9, 9, 13, 10))

    assert result["state"] == "pending"


def test_reports_missed_once_the_retry_window_has_closed(data_root):
    _facts_store(data_root, [])

    result = nifty_shield._checkpoint_status("2026-09-09", now=datetime(2026, 9, 9, 15, 0))

    assert result["state"] == "missed"


def test_missed_with_no_journal_line_explains_the_silent_latch(data_root):
    """The driver's expired-window branch latches WITHOUT calling the publisher,
    so a genuine miss journals nothing. A blank reason must not read as a panel bug."""
    _facts_store(data_root, [])

    result = nifty_shield._checkpoint_status("2026-09-09", now=datetime(2026, 9, 9, 15, 0))

    assert result["skip_reason"] is None
    assert "window expired before any bar produced a ready fact" in result["note"]


def test_surfaces_the_publishers_own_reason_when_it_journaled_one(data_root):
    _facts_store(data_root, [])
    _journal(data_root, [
        '{"timestamp": "2026-09-09T13:05:00+05:30", "event_type": "FACT_PUBLISH_SKIPPED",'
        ' "severity": "WARNING", "source_component": "R", "message": "not ready: 40 bars < 100"}',
    ])

    result = nifty_shield._checkpoint_status("2026-09-09", now=datetime(2026, 9, 9, 15, 0))

    assert result["skip_reason"]["message"] == "not ready: 40 bars < 100"
    assert "window expired before any bar" not in result["note"]


def test_reports_the_entry_block_separately_from_the_checkpoint(data_root):
    """A fired checkpoint with no trade is an ENTRY question, not a checkpoint one."""
    _facts_store(data_root, ["2026-09-09"])
    _journal(data_root, [
        '{"timestamp": "2026-09-09T13:04:06+05:30", "event_type": "ENTRY_SKIPPED",'
        ' "severity": "INFO", "source_component": "R", "message": "credit 57.50 is 79% of 72.86"}',
    ])

    result = nifty_shield._checkpoint_status("2026-09-09", now=datetime(2026, 9, 9, 13, 45))

    assert result["state"] == "published"
    assert result["entry_blocked"]["message"] == "credit 57.50 is 79% of 72.86"


def test_an_unreadable_store_is_reported_as_unknown_not_as_a_miss(data_root):
    (data_root / "facts.duckdb").write_bytes(b"not a duckdb file")

    result = nifty_shield._checkpoint_status("2026-09-09", now=datetime(2026, 9, 9, 15, 0))

    assert result["state"] == "unknown"
    assert result["fact_published_today"] is None
