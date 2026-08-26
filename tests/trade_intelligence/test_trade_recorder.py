"""Tests for the universal TradeRecorder (fill-seam, strategy-agnostic)."""
import duckdb
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.order_lifecycle import FillEvent
from core.execution.order_models import (
    NormalizedOrder, OrderMetadata, OrderSide, OrderType,
)
from core.instruments.equity import Equity
from core.execution.portfolio.trade_recorder import TradeRecorder

T0 = datetime(2026, 8, 20, 9, 30, 0)
T1 = datetime(2026, 8, 22, 15, 5, 0)

# DuckDB permits one connection configuration per process per file, so tests
# open short-lived read connections AFTER recorder writes complete.


def make_order(strategy_id="strat_x", signal_id="sig_1", side=OrderSide.BUY,
               metadata=None):
    return NormalizedOrder(
        instrument=Equity("NSE_EQ|INE002A01018"),
        side=side, quantity=10, order_type=OrderType.MARKET,
        strategy_id=strategy_id, signal_id=signal_id, timestamp=T0,
        metadata=metadata or OrderMetadata(
            0.9, {"z": 2.1, "sector": "ENERGY"}),
    )


def make_fill(fill_id="f1", order_id="o1", qty=10.0, price=100.0, side="BUY",
              ts=T0, fee=1.5, symbol="NSE_EQ|INE002A01018"):
    return FillEvent(fill_id=fill_id, order_id=order_id, symbol=symbol,
                     quantity=qty, price=price, timestamp=ts, side=side,
                     fee=fee)


def row(db_path, trade_id):
    c = duckdb.connect(str(db_path), read_only=True)
    try:
        return c.execute(
            "SELECT * FROM executed_trades WHERE trade_id=?",
            [trade_id]).fetchone()
    finally:
        c.close()


def count(db_path):
    c = duckdb.connect(str(db_path), read_only=True)
    try:
        return c.execute(
            "SELECT COUNT(*) FROM executed_trades").fetchone()[0]
    finally:
        c.close()


@pytest.fixture
def db(tmp_path):
    return tmp_path / "ti.duckdb"


@pytest.fixture
def rec(tmp_path):
    r = TradeRecorder(db_path=str(tmp_path / "ti.duckdb"), index_dir=tmp_path)
    yield r


class TestEntry:
    def test_open_inserts_row(self, rec, db):
        rec.on_fill(make_fill(), make_order(), 0.0, 0.0)
        r = row(db, "f1")
        assert r is not None
        assert r[1] == "NSE_EQ|INE002A01018" and r[2] == "LONG"
        assert r[4] == T0 and r[5] == 100.0 and r[6] == 10.0
        assert r[9] == "strat_x"

    def test_signal_snapshot_immutable_json(self, rec, db):
        rec.on_fill(make_fill(), make_order(), 0.0, 0.0)
        snap = json.loads(row(db, "f1")[11])
        assert snap["z"] == 2.1 and snap["sector"] == "ENERGY"

    def test_short_direction(self, rec, db):
        rec.on_fill(make_fill(side="SELL", fill_id="fs"),
                    make_order(side=OrderSide.SELL), 0.0, 0.0)
        assert row(db, "fs")[2] == "SHORT"

    def test_regime_null_without_index_data(self, rec, db):
        rec.on_fill(make_fill(), make_order(), 0.0, 0.0)
        r = row(db, "f1")
        assert r[12] is None and r[13] is None

    def test_add_fill_vwap_and_fees(self, rec, db):
        rec.on_fill(make_fill(qty=10, price=100), make_order(), 0.0, 0.0)
        rec.on_fill(make_fill(fill_id="f2", qty=10, price=120),
                    make_order(), 10.0, 0.0)
        r = row(db, "f1")
        assert r[6] == 20.0
        assert r[5] == pytest.approx(110.0)          # VWAP
        assert r[17] == pytest.approx(3.0)           # fees accumulated


class TestExit:
    def test_close_populates_outcome(self, rec, db):
        rec.on_fill(make_fill(), make_order(), 0.0, 0.0)
        rec.on_fill(make_fill(fill_id="f2", side="SELL", price=110.0, ts=T1),
                    None, 10.0, 95.0)
        r = row(db, "f1")
        assert r[14] == T1 and r[15] == 110.0
        assert r[16] == pytest.approx(95.0)
        assert r[17] == pytest.approx(3.0)
        assert r[18] == 2                            # days_held
        assert r[19] == "CLOSED"

    def test_signal_columns_unchanged_after_exit(self, rec, db):
        rec.on_fill(make_fill(), make_order(), 0.0, 0.0)
        before = row(db, "f1")[:13]
        rec.on_fill(make_fill(fill_id="f2", side="SELL", ts=T1),
                    None, 10.0, 5.0)
        after = row(db, "f1")[:13]
        assert before == after

    def test_exit_reason_from_closing_order_metadata(self, rec, db):
        closing = make_order(metadata=OrderMetadata(
            0.0, {"exit_reason": "EXIT_SL"}))
        rec.on_fill(make_fill(), make_order(), 0.0, 0.0)
        rec.on_fill(make_fill(fill_id="f2", side="SELL", ts=T1),
                    closing, 10.0, -50.0)
        assert row(db, "f1")[19] == "EXIT_SL"

    def test_partial_reduce_then_finalize(self, rec, db):
        rec.on_fill(make_fill(qty=10, price=100), make_order(), 0.0, 0.0)
        rec.on_fill(make_fill(fill_id="f2", side="SELL", qty=4, price=105),
                    None, 10.0, 20.0)
        r = row(db, "f1")
        assert r[14] is None                          # still open
        assert r[16] == pytest.approx(20.0)           # pnl so far
        rec.on_fill(make_fill(fill_id="f3", side="SELL", qty=6, price=108),
                    None, 6.0, 48.0)
        r = row(db, "f1")
        assert r[15] == 108.0
        assert r[16] == pytest.approx(68.0)
        assert r[19] == "CLOSED"

    def test_flip_closes_old_and_opens_new(self, rec, db):
        rec.on_fill(make_fill(), make_order(), 0.0, 0.0)
        rec.on_fill(make_fill(fill_id="f2", side="SELL", qty=12, price=90),
                    None, 10.0, -100.0)
        closed = row(db, "f1")
        opened = row(db, "f2")
        assert closed[19] == "CLOSED"                 # old long closed
        assert opened is not None and opened[2] == "SHORT"
        assert opened[6] == 2.0                       # residual short qty


class TestRobustness:
    def test_duplicate_fill_idempotent(self, rec, db):
        rec.on_fill(make_fill(), make_order(), 0.0, 0.0)
        rec.on_fill(make_fill(), make_order(), 0.0, 0.0)
        assert count(db) == 1

    def test_restart_recovery_via_db_lookup(self, tmp_path, db):
        p = str(tmp_path / "ti.duckdb")
        r1 = TradeRecorder(db_path=p, index_dir=tmp_path)
        r1.on_fill(make_fill(), make_order(), 0.0, 0.0)
        r2 = TradeRecorder(db_path=p, index_dir=tmp_path)   # fresh instance
        r2.on_fill(make_fill(fill_id="f2", side="SELL", ts=T1),
                   None, 10.0, 7.0)
        assert row(db, "f1")[19] == "CLOSED"

    def test_never_raises_on_db_error(self, tmp_path):
        r = TradeRecorder(db_path=str(tmp_path / "ok.duckdb"),
                          index_dir=tmp_path)
        r._db_path = tmp_path / "nope" / "gone.duckdb"      # break the path
        r.on_fill(make_fill(), make_order(), 0.0, 0.0)      # must not raise
        assert r.stats["errors"] >= 1

    def test_disabled_recorder_noop(self, tmp_path):
        r = TradeRecorder(db_path=str(tmp_path / "d.duckdb"),
                          enabled=False)
        r.on_fill(make_fill(), make_order(), 0.0, 0.0)
        assert not (tmp_path / "d.duckdb").exists()
