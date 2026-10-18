"""A test run must never be able to write to the operator's live stores.

2026-10-07: a full regression in the live checkout grew trade_intelligence.duckdb
by 65 MB, rewrote data/execution.db and overwrote the ISD repair manifest. 99% of
the 8,704 rows in executed_trades are test fixtures (g1restore, test_margin, mm7c,
...): ExecutionConfig.trade_recorder_enabled defaults True and TradeRecorder()
defaults to the live DuckDB path, so every handler a test built recorded into it.
"""
from pathlib import Path

from core.execution.persistence.execution_store import ExecutionStore
from core.execution.portfolio import trade_recorder

REPO = Path(__file__).resolve().parents[1]


def _inside_repo_data(path) -> bool:
    return (REPO / "data") in (REPO / Path(path)).resolve().parents


def test_trade_recorder_default_db_is_not_the_live_store():
    assert not _inside_repo_data(trade_recorder.DEFAULT_DB_PATH)


def test_execution_store_default_db_is_not_the_live_store():
    assert not _inside_repo_data(ExecutionStore().db_path)


def test_a_handler_built_with_defaults_does_not_record_into_the_live_ti_store(tmp_path):
    live = REPO / "data" / "signal_engine" / "trade_intelligence" / "trade_intelligence.duckdb"
    before = (live.stat().st_size, live.stat().st_mtime) if live.exists() else None
    rec = trade_recorder.TradeRecorder()
    assert rec._db_path != live
    after = (live.stat().st_size, live.stat().st_mtime) if live.exists() else None
    assert after == before
