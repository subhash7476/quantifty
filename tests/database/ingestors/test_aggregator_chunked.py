import duckdb
from datetime import datetime
from contextlib import contextmanager
from core.database.manager import DatabaseManager
from core.database.ingestors.db_tick_aggregator import DBTickAggregator

def _seed_ticks(tmp_path, symbol, base_minute):
    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    db.bootstrap_live_buffer()
    with db.live_ticks_writer() as conn:
        # three ticks in one completed minute
        for i, price in enumerate([100.0, 105.0, 102.0]):
            conn.execute(
                "INSERT INTO ticks (symbol, timestamp, price, volume) VALUES (?, ?, ?, ?)",
                [symbol, base_minute.replace(second=i * 10), price, 10],
            )
    return db

def test_aggregate_writes_ohlc_for_completed_minute(tmp_path):
    base = datetime(2020, 1, 1, 10, 0, 0)  # far in the past -> always "completed"
    db = _seed_ticks(tmp_path, "X", base)
    agg = DBTickAggregator(db_manager=db)
    agg.aggregate(["X"], db, None)
    c = duckdb.connect(str(tmp_path / "live_buffer" / "candles_today.duckdb"), read_only=True)
    row = c.execute("SELECT open, high, low, close, volume, is_synthetic FROM candles WHERE symbol='X'").fetchone()
    c.close()
    assert row == (100.0, 105.0, 100.0, 102.0, 30, False)

def test_aggregate_opens_candles_per_symbol_not_batch(tmp_path):
    base = datetime(2020, 1, 1, 10, 0, 0)
    db = _seed_ticks(tmp_path, "A", base)
    with db.live_ticks_writer() as conn:
        conn.execute("INSERT INTO ticks (symbol, timestamp, price, volume) VALUES ('B', ?, 5.0, 1)", [base])
    opens = {"candles": 0}
    real = db.live_candles_writer
    @contextmanager
    def counting():
        opens["candles"] += 1
        with real() as conn:
            yield conn
    db.live_candles_writer = counting
    agg = DBTickAggregator(db_manager=db)
    agg.aggregate(["A", "B"], db, None)
    assert opens["candles"] == 2  # one short-lived open per symbol, not one batch hold
