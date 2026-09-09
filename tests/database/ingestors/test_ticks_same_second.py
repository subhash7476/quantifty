"""The ticks table must keep every distinct update inside a single second.

Upstox stamps `ltt` to the whole second while pushing several updates within
that second. The old PRIMARY KEY (symbol, timestamp) + INSERT OR IGNORE kept the
first and discarded the rest, so intra-second highs and lows never reached the
1m bars the aggregator builds.
"""
from datetime import datetime

import duckdb

from core.database.ingestors.live_buffer_writer import LiveBufferWriter
from core.database.manager import DatabaseManager


def _mk(tmp_path) -> DatabaseManager:
    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    db.bootstrap_live_buffer()
    return db


def _ticks(tmp_path):
    conn = duckdb.connect(str(tmp_path / "live_buffer" / "ticks_today.duckdb"), read_only=True)
    try:
        return conn.execute(
            "SELECT symbol, timestamp, price, volume FROM ticks ORDER BY seq"
        ).fetchall()
    finally:
        conn.close()


SECOND = datetime(2026, 9, 4, 10, 15, 30)


def test_distinct_prices_in_one_second_are_all_kept(tmp_path):
    db = _mk(tmp_path)
    w = LiveBufferWriter(db)

    w._flush_ticks([])  # no-op guard
    w._parse = lambda raw: [("NSE_INDEX|Nifty 50", SECOND, float(raw), 0)]
    for price in (100.0, 105.0, 98.0, 101.0):
        w._flush_ticks([type("F", (), {"raw": price})()])

    rows = _ticks(tmp_path)
    assert [r[2] for r in rows] == [100.0, 105.0, 98.0, 101.0]


def test_intra_second_high_and_low_reach_the_aggregated_bar(tmp_path):
    """The whole point: max/min over a second must see more than one price."""
    db = _mk(tmp_path)
    w = LiveBufferWriter(db)
    w._parse = lambda raw: [("NSE_INDEX|Nifty 50", SECOND, float(raw), 0)]
    for price in (100.0, 130.0, 70.0, 110.0):
        w._flush_ticks([type("F", (), {"raw": price})()])

    conn = duckdb.connect(str(tmp_path / "live_buffer" / "ticks_today.duckdb"), read_only=True)
    try:
        op, hi, lo, cl = conn.execute(
            "SELECT first(price ORDER BY timestamp ASC, seq ASC), max(price), min(price), "
            "last(price ORDER BY timestamp ASC, seq ASC) FROM ticks"
        ).fetchone()
    finally:
        conn.close()
    assert (op, hi, lo, cl) == (100.0, 130.0, 70.0, 110.0)


def test_seq_makes_ordering_deterministic_within_a_second(tmp_path):
    """Ties on timestamp are otherwise unordered — seq is what fixes open/close."""
    db = _mk(tmp_path)
    w = LiveBufferWriter(db)
    w._parse = lambda raw: [("NSE_INDEX|Nifty 50", SECOND, float(raw), 0)]
    for price in (11.0, 22.0, 33.0):
        w._flush_ticks([type("F", (), {"raw": price})()])

    conn = duckdb.connect(str(tmp_path / "live_buffer" / "ticks_today.duckdb"), read_only=True)
    try:
        seqs = [r[0] for r in conn.execute("SELECT seq FROM ticks ORDER BY seq").fetchall()]
        prices = [r[0] for r in conn.execute(
            "SELECT price FROM ticks ORDER BY seq").fetchall()]
    finally:
        conn.close()
    assert seqs == sorted(seqs) and len(set(seqs)) == 3
    assert prices == [11.0, 22.0, 33.0]


def test_identical_repeat_is_dropped(tmp_path):
    """A reconnect re-sends current state; an unchanged tick adds nothing and
    would double-count in sum(volume)."""
    db = _mk(tmp_path)
    w = LiveBufferWriter(db)
    w._parse = lambda raw: [("NSE_INDEX|Nifty 50", SECOND, 100.0, 7)]
    for _ in range(4):
        w._flush_ticks([type("F", (), {"raw": b""})()])

    assert len(_ticks(tmp_path)) == 1


def test_repeat_after_a_change_is_kept(tmp_path):
    """Only the immediately preceding tick is suppressed, not a real re-visit."""
    db = _mk(tmp_path)
    w = LiveBufferWriter(db)
    seq = [("NSE_INDEX|Nifty 50", SECOND, 100.0, 1),
           ("NSE_INDEX|Nifty 50", SECOND, 101.0, 1),
           ("NSE_INDEX|Nifty 50", SECOND, 100.0, 1)]
    w._parse = lambda raw: [seq[raw]]
    for i in range(3):
        w._flush_ticks([type("F", (), {"raw": i})()])

    assert [r[2] for r in _ticks(tmp_path)] == [100.0, 101.0, 100.0]


def test_repeat_suppression_is_per_symbol(tmp_path):
    db = _mk(tmp_path)
    w = LiveBufferWriter(db)
    w._parse = lambda raw: [("NSE_INDEX|Nifty 50", SECOND, 100.0, 0),
                            ("NSE_INDEX|Nifty Bank", SECOND, 100.0, 0)]
    w._flush_ticks([type("F", (), {"raw": b""})()])

    assert len(_ticks(tmp_path)) == 2


def test_rotation_migrates_a_pre_seq_store(tmp_path):
    """Existing files have the old 6-column shape and no seq."""
    db = _mk(tmp_path)
    path = tmp_path / "live_buffer" / "ticks_today.duckdb"
    conn = duckdb.connect(str(path))
    try:
        conn.execute("DROP TABLE ticks")
        conn.execute("CREATE TABLE ticks (symbol VARCHAR NOT NULL, timestamp TIMESTAMP NOT NULL, "
                     "price DOUBLE NOT NULL, volume BIGINT NOT NULL, bid DOUBLE, ask DOUBLE, "
                     "PRIMARY KEY (symbol, timestamp))")
        conn.execute("INSERT INTO ticks VALUES ('A', TIMESTAMP '2026-09-04 10:00:00', 1.0, 1, NULL, NULL)")
    finally:
        conn.close()

    kept = db.rotate_live_buffer(datetime(2026, 9, 4))

    assert kept["ticks"] == 1
    conn = duckdb.connect(str(path), read_only=True)
    try:
        cols = {r[1] for r in conn.execute('PRAGMA table_info("ticks")').fetchall()}
        assert "seq" in cols
        assert conn.execute("SELECT price FROM ticks").fetchone()[0] == 1.0
    finally:
        conn.close()
