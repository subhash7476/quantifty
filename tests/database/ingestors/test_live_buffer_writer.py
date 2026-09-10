import duckdb, time
from datetime import datetime, time as _time

import pytz
from core.database.manager import DatabaseManager
from core.database.ingestors.live_buffer_writer import (
    LiveBufferWriter, TickFrame, Purge,
)
from core.data.MarketDataFeedV3_pb2 import FeedResponse

_IST = pytz.timezone("Asia/Kolkata")
# The writer drops ticks whose `ltt` is not in the current session, so a
# fixed historical epoch would now be discarded before it reaches the table.
_TODAY_MS = int(_IST.localize(datetime.combine(
    datetime.now(_IST).date(), _time(10, 0))).timestamp() * 1000)

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
    w.enqueue_frame(_frame("NSE_INDEX|Nifty 50", 24000.0, _TODAY_MS, 5))
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
    w.enqueue_frame(_frame("X", 1.0, _TODAY_MS, 1))
    w.stop()
    assert not any("candles_today" in p for p in opened)
    assert any("ticks_today" in p for p in opened)

def test_drop_oldest_backpressure(tmp_path):
    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    w = LiveBufferWriter(db, max_queue=10)
    # do NOT start the worker; fill the queue past bound
    for i in range(25):
        w.enqueue_frame(_frame("X", float(i), _TODAY_MS, 1))
    assert w.dropped_frames >= 15
    assert w._ticks.qsize() <= 10

def test_stop_drains_all_buffered_ticks(tmp_path):
    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    w = LiveBufferWriter(db)
    w.start()
    for i in range(50):
        w.enqueue_frame(_frame("X", float(i + 1), _TODAY_MS + i * 1000, 1))
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
        w.enqueue_frame(_frame("X", float(i + 1), _TODAY_MS + i * 1000, 1))
    w.stop()
    c = _ticks(tmp_path)
    n = c.execute("SELECT count(*) FROM ticks").fetchone()[0]
    c.close()
    assert n == 20
    assert state["n"] == 3  # the transient collisions were retried, not fatal


def test_prior_session_ltt_tick_is_dropped_at_the_write_boundary(tmp_path, caplog):
    """2026-09-10 root cause. The tick timestamp is the exchange's `ltt`, so a
    symbol that has not traded today is broadcast with a PRIOR session's
    timestamp; the aggregator then buckets it into a prior-session candle. The
    connect snapshot arrived ~1 s after the startup rotation carrying the
    previous evening's index dissemination (16:00), and the three bars it
    produced cost that session its 13:00 DayType fact.

    The rotation cannot catch this — it is a one-shot that already ran. A tick
    stamped outside the current session must never enter the buffer, and the
    drop must be logged, not silent."""
    import logging

    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    w = LiveBufferWriter(db)
    w.start()
    stale_ms = _TODAY_MS - 24 * 60 * 60 * 1000          # same clock time, yesterday
    with caplog.at_level(logging.WARNING):
        w.enqueue_frame(_frame("NSE_INDEX|Nifty 50", 23431.5, stale_ms, 0))
        w.enqueue_frame(_frame("NSE_INDEX|Nifty 50", 24000.0, _TODAY_MS, 5))
        w.stop()

    c = _ticks(tmp_path)
    rows = c.execute("SELECT symbol, timestamp, price FROM ticks").fetchall()
    c.close()
    assert [r[2] for r in rows] == [24000.0]
    assert rows[0][1].date() == datetime.now(_IST).date()
    assert any("outside session" in r.getMessage() for r in caplog.records)
