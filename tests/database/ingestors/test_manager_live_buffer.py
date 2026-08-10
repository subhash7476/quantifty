import duckdb, pytest
from pathlib import Path
from core.database.manager import DatabaseManager

def _mk(tmp_path) -> DatabaseManager:
    DatabaseManager.reset_instance()
    return DatabaseManager(tmp_path, read_only=False)

def test_bootstrap_creates_tick_and_candle_tables(tmp_path):
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    tconn = duckdb.connect(str(tmp_path / "live_buffer" / "ticks_today.duckdb"), read_only=True)
    assert tconn.execute("SELECT count(*) FROM ticks").fetchone()[0] == 0
    tconn.close()
    cconn = duckdb.connect(str(tmp_path / "live_buffer" / "candles_today.duckdb"), read_only=True)
    assert cconn.execute("SELECT count(*) FROM candles").fetchone()[0] == 0
    cconn.close()

def test_ticks_writer_opens_ticks_only(tmp_path):
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    with db.live_ticks_writer() as conn:
        conn.execute("INSERT INTO ticks (symbol, timestamp, price, volume) VALUES ('X', now(), 1.0, 1)")
    # candles file must remain openable RW by another connection immediately (not held)
    c = duckdb.connect(str(tmp_path / "live_buffer" / "candles_today.duckdb"), read_only=False)
    c.close()

def test_reader_retries_transient_then_returns(tmp_path, monkeypatch):
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    calls = {"n": 0}
    real_connect = db._duckdb_connect
    def flaky(path, read_only=False):
        if "candles_today" in str(path) and read_only and calls["n"] < 2:
            calls["n"] += 1
            raise duckdb.IOException("Cannot open file: being used by another process")
        return real_connect(path, read_only=read_only)
    monkeypatch.setattr(db, "_duckdb_connect", flaky)
    with db.live_buffer_reader() as conns:
        assert "candles" in conns
    assert calls["n"] == 2  # retried twice, then succeeded
