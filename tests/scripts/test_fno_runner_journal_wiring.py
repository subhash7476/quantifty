"""
MM8.1A — fno_runner journal wiring tests.

Verifies that build_runner passes the RuntimeEventJournal it receives into the
ExecutionHandler, so the handler holds the same reference the driver holds.

Uses the existing _runner_harness.build() isolation construction.
"""

from core.runtime.event_journal import RuntimeEventJournal
from _runner_harness import EQUITY, NoopSource, build


def test_build_runner_passes_journal_to_handler(tmp_path, monkeypatch):
    journal = RuntimeEventJournal(path=str(tmp_path / "events.jsonl"))
    d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,),
              journal=journal)
    assert d._execution._journal is journal


def test_build_runner_handler_journal_is_none_when_not_supplied(tmp_path, monkeypatch):
    d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,))
    assert d._execution._journal is None
