"""
MM8.1A — ExecutionHandler journal injection unit tests.

Verifies that ExecutionHandler.__init__ accepts an optional RuntimeEventJournal
and stores it as self._journal, with no behavioral side-effects.

Uses the MM7C/MM7D.1 isolation construction (monkeypatch ExecutionStore -> tmp)
consistent with the rest of tests/execution/.
"""

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.persistence.execution_store import ExecutionStore
from core.brokers.paper_broker import PaperBroker
from core.runtime.event_journal import RuntimeEventJournal

from datetime import datetime
import pytz

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


def _build_handler(tmp_path, monkeypatch, **extra_kwargs):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    clock = ReplayClock(FIXED_DT)
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=PaperBroker(clock),
        config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        **extra_kwargs,
    )


def test_handler_stores_journal_when_injected(tmp_path, monkeypatch):
    journal = RuntimeEventJournal(path=str(tmp_path / "events.jsonl"))
    handler = _build_handler(tmp_path, monkeypatch, journal=journal)
    assert handler._journal is journal


def test_handler_stores_none_when_no_journal_injected(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    assert handler._journal is None
