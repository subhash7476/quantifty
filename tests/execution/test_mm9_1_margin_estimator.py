"""
MM9.1-S2 — Deterministic margin estimation helper (infrastructure only).

Verifies ExecutionHandler._estimate_required_margin: a pure, deterministic,
side-effect-free private helper. It is NOT invoked anywhere in the runtime
yet (consumed in MM9.1-S3). The estimate is intentionally simplistic —
long and short both reduce to quantity * price; SPAN replaces it in a
future MM9.x slice.

Uses the MM7C/MM8 isolation construction (monkeypatch ExecutionStore -> tmp)
consistent with tests/execution/test_handler_journal_injection.py.
"""

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.persistence.execution_store import ExecutionStore
from core.brokers.paper_broker import PaperBroker

from datetime import datetime
import pytz

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


def _build_handler(tmp_path, monkeypatch):
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
    )


# =========================================================================== #
# MM9.1-S2 — _estimate_required_margin
# =========================================================================== #

def test_estimate_required_margin_long_position(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    # LONG: quantity=10, price=100 -> 1000
    assert handler._estimate_required_margin(10, 100) == 1000


def test_estimate_required_margin_short_position(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    # SHORT: quantity=10, price=100 -> 1000 (intentionally identical to LONG)
    assert handler._estimate_required_margin(10, 100) == 1000


def test_estimate_required_margin_zero_quantity_returns_zero(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    assert handler._estimate_required_margin(0, 100) == 0


def test_estimate_required_margin_zero_price_returns_zero(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    assert handler._estimate_required_margin(10, 0) == 0


def test_estimate_required_margin_is_pure_and_deterministic(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    first = handler._estimate_required_margin(10, 100)
    second = handler._estimate_required_margin(10, 100)
    third = handler._estimate_required_margin(10, 100)
    assert first == second == third == 1000
