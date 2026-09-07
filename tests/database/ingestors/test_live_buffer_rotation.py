from datetime import datetime, timedelta

import duckdb

from core.database.ingestors.live_buffer_writer import LiveBufferWriter, Purge, TickFrame
from core.database.manager import DatabaseManager


def _mk(tmp_path) -> DatabaseManager:
    DatabaseManager.reset_instance()
    return DatabaseManager(tmp_path, read_only=False)


def _seed(db, n_old, n_today, cutoff):
    with db.live_ticks_writer() as conn:
        for i in range(n_old):
            conn.execute("INSERT INTO ticks (symbol, timestamp, price, volume) VALUES (?,?,?,?)",
                         ["OLD", cutoff - timedelta(seconds=i + 1), 10.0 + i, i])
        for i in range(n_today):
            conn.execute("INSERT INTO ticks (symbol, timestamp, price, volume) VALUES (?,?,?,?)",
                         ["NEW", cutoff + timedelta(seconds=i), 20.0 + i, i])
    with db.live_candles_writer() as conn:
        for i in range(n_old):
            conn.execute(
                "INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) "
                "VALUES (?, '1m', ?, 1, 2, 0.5, 1.5, 10)",
                ["OLD", cutoff - timedelta(minutes=i + 1)])
        for i in range(n_today):
            conn.execute(
                "INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) "
                "VALUES (?, '1m', ?, 1, 2, 0.5, 1.5, 10)",
                ["NEW", cutoff + timedelta(minutes=i)])


def _rows(path, table):
    conn = duckdb.connect(str(path), read_only=True)
    try:
        return conn.execute(f"SELECT symbol, count(*) FROM {table} GROUP BY 1 ORDER BY 1").fetchall()
    finally:
        conn.close()


def test_rotation_keeps_rows_at_or_after_cutoff_and_drops_older(tmp_path):
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    cutoff = datetime(2026, 9, 4, 0, 0, 0)
    _seed(db, n_old=5, n_today=3, cutoff=cutoff)

    kept = db.rotate_live_buffer(cutoff)

    assert kept == {"ticks": 3, "candles": 3}
    base = tmp_path / "live_buffer"
    assert _rows(base / "ticks_today.duckdb", "ticks") == [("NEW", 3)]
    assert _rows(base / "candles_today.duckdb", "candles") == [("NEW", 3)]


def test_rotation_reclaims_file_space(tmp_path):
    """A DELETE leaves the blocks allocated; rotation must actually shrink."""
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    ticks = tmp_path / "live_buffer" / "ticks_today.duckdb"
    cutoff = datetime(2026, 9, 4, 0, 0, 0)

    # 200 close-per-batch writes is what inflates the file in production
    for batch in range(200):
        with db.live_ticks_writer() as conn:
            conn.executemany(
                "INSERT INTO ticks (symbol, timestamp, price, volume) VALUES (?,?,?,?)",
                [["OLD", cutoff - timedelta(seconds=batch * 10 + k + 1), 1.0 * k, k]
                 for k in range(10)])
    inflated = ticks.stat().st_size

    db.rotate_live_buffer(cutoff)

    assert ticks.stat().st_size < inflated
    conn = duckdb.connect(str(ticks), read_only=True)
    try:
        assert conn.execute("SELECT count(*) FROM ticks").fetchone()[0] == 0
    finally:
        conn.close()


def test_rotation_leaves_no_temp_file(tmp_path):
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    db.rotate_live_buffer(datetime(2026, 9, 4))
    assert list((tmp_path / "live_buffer").glob("*.tmp")) == []


def test_purge_command_routes_to_rotation(tmp_path):
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    seen = {}

    def _capture(cutoff):
        seen["cutoff"] = cutoff
        return {}

    db.rotate_live_buffer = _capture
    cutoff = datetime(2026, 9, 4)

    LiveBufferWriter(db)._handle_purge(Purge(cutoff))

    assert seen["cutoff"] == cutoff


def test_pending_ticks_flush_on_shutdown_not_stranded(tmp_path):
    """The interval buffer must not swallow ticks when the writer stops."""
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    w = LiveBufferWriter(db)
    flushed = []
    w._flush_ticks = lambda frames: flushed.extend(frames)

    w._pending = [TickFrame(b"a"), TickFrame(b"b")]
    w._final_drain()

    assert len(flushed) == 2
    assert w._pending == []


def test_ticks_buffer_until_interval_elapses(tmp_path):
    """Below the interval and below the size cap, nothing is written."""
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    w = LiveBufferWriter(db)
    calls = []
    w._flush_ticks = lambda frames: calls.append(len(frames))
    w._last_flush = float("inf")  # interval can never appear elapsed

    w._coalesce_ticks(TickFrame(b"a"))
    w._coalesce_ticks(TickFrame(b"b"))

    assert calls == []
    assert len(w._pending) == 2


def test_aggregate_forces_pending_ticks_to_land(tmp_path):
    """A bar built while ticks sit in the buffer would be written short."""
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    w = LiveBufferWriter(db)
    flushed = []
    w._flush_ticks = lambda frames: flushed.extend(frames)
    w._pending = [TickFrame(b"a")]

    w._force_flush()

    assert len(flushed) == 1
    assert w._pending == []
