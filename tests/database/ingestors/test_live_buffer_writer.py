import duckdb, time
from datetime import datetime
from core.database.manager import DatabaseManager
from core.database.ingestors.live_buffer_writer import (
    LiveBufferWriter, TickFrame, Purge,
)
from core.data.MarketDataFeedV3_pb2 import FeedResponse

def _frame(symbol, ltp, ltt_ms, ltq):
    fr = FeedResponse()
    f = fr.feeds[symbol]
    f.ltpc.ltp = ltp
    f.ltpc.ltt = ltt_ms
    f.ltpc.ltq = ltq
    return fr.SerializeToString()

def _ticks(tmp_path):
    DatabaseManager.reset_instance()
    return duckdb.connect(str(tmp_path / "live_buffer" / "ticks_today.duckdb"), read_only=True)

def test_enqueued_frame_persists_tick(tmp_path):
    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    w = LiveBufferWriter(db)
    w.start()
    w.enqueue_frame(_frame("NSE_INDEX|Nifty 50", 24000.0, 1723276800000, 5))
    w.stop()  # drains
    c = _ticks(tmp_path)
    row = c.execute("SELECT symbol, price, volume FROM ticks").fetchone()
    c.close()
    assert row == ("NSE_INDEX|Nifty 50", 24000.0, 5)

def test_tick_path_never_opens_candles(tmp_path):
    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    opened = []
    real = db._duckdb_connect
    def spy(path, read_only=False):
        opened.append(str(path))
        return real(path, read_only=read_only)
    db._duckdb_connect = spy
    w = LiveBufferWriter(db)
    w.start()
    opened.clear()  # bootstrap (DDL-once) legitimately opens both files; isolate tick path
    w.enqueue_frame(_frame("X", 1.0, 1723276800000, 1))
    w.stop()
    assert not any("candles_today" in p for p in opened)
    assert any("ticks_today" in p for p in opened)

def test_drop_oldest_backpressure(tmp_path):
    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    w = LiveBufferWriter(db, max_queue=10)
    # do NOT start the worker; fill the queue past bound
    for i in range(25):
        w.enqueue_frame(_frame("X", float(i), 1723276800000, 1))
    assert w.dropped_frames >= 15
    assert w._ticks.qsize() <= 10

def test_stop_drains_all_buffered_ticks(tmp_path):
    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    w = LiveBufferWriter(db)
    w.start()
    for i in range(50):
        w.enqueue_frame(_frame("X", float(i + 1), 1723276800000 + i * 1000, 1))
    w.stop()
    c = _ticks(tmp_path)
    n = c.execute("SELECT count(*) FROM ticks").fetchone()[0]
    c.close()
    assert n == 50

def test_tick_flush_survives_transient_rw_collision(tmp_path):
    # HIGH-1: a cross-process reader holding ticks RO must not permanently drop a
    # dequeued tick batch. The writer's live_ticks_writer bounded-retries the RW
    # open (matching the real Windows error string); the batch survives in memory
    # through the retry.
    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    w = LiveBufferWriter(db)
    w.start()
    real = db._duckdb_connect
    state = {"n": 0}
    def flaky(path, read_only=False):
        if "ticks_today" in str(path) and not read_only and state["n"] < 3:
            state["n"] += 1
            raise duckdb.IOException("Cannot open file: being used by another process")
        return real(path, read_only=read_only)
    db._duckdb_connect = flaky
    for i in range(20):
        w.enqueue_frame(_frame("X", float(i + 1), 1723276800000 + i * 1000, 1))
    w.stop()
    c = _ticks(tmp_path)
    n = c.execute("SELECT count(*) FROM ticks").fetchone()[0]
    c.close()
    assert n == 20
    assert state["n"] == 3  # the transient collisions were retried, not fatal
