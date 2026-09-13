from datetime import date, datetime

import duckdb

import scripts.cas.mark_synthetic_bars as marker
from scripts.cas.mark_synthetic_bars import mark_file

SYM = "NSE_EQ|INE002A01018"


def _make_file(tmp_path, session, bars):
    path = tmp_path / f"{session.isoformat()}.duckdb"
    con = duckdb.connect(str(path))
    con.execute(
        "CREATE TABLE candles (symbol VARCHAR, instrument_key VARCHAR, "
        "timeframe VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE, "
        "low DOUBLE, close DOUBLE, volume BIGINT, is_synthetic BOOLEAN)"
    )
    con.executemany(
        "INSERT INTO candles VALUES (?, '', '1m', ?, ?, ?, ?, ?, ?, FALSE)", bars
    )
    con.close()
    return path


def test_flat_zero_volume_bars_in_the_auction_window_are_marked(tmp_path):
    session = date(2026, 8, 24)
    bars = [
        (SYM, datetime(2026, 8, 24, 15, 14), 1305.0, 1305.1, 1302.9, 1304.1, 68944),
        (SYM, datetime(2026, 8, 24, 15, 15), 1304.1, 1304.1, 1304.1, 1304.1, 0),
        (SYM, datetime(2026, 8, 24, 15, 16), 1304.1, 1304.1, 1304.1, 1304.1, 0),
        (SYM, datetime(2026, 8, 24, 15, 29), 1309.8, 1309.8, 1309.8, 1309.8, 377584),
    ]
    path = _make_file(tmp_path, session, bars)

    assert mark_file(path, session, {SYM}) == 2

    con = duckdb.connect(str(path), read_only=True)
    flagged = con.execute(
        "SELECT timestamp FROM candles WHERE is_synthetic ORDER BY timestamp"
    ).fetchall()
    con.close()
    assert [t[0].minute for t in flagged] == [15, 16]


def test_the_auction_print_is_never_marked(tmp_path):
    session = date(2026, 8, 24)
    bars = [
        (SYM, datetime(2026, 8, 24, 15, 14), 1305.0, 1305.1, 1302.9, 1304.1, 68944),
        (SYM, datetime(2026, 8, 24, 15, 29), 1309.8, 1309.8, 1309.8, 1309.8, 377584),
    ]
    path = _make_file(tmp_path, session, bars)

    assert mark_file(path, session, {SYM}) == 0


def test_pre_cas_sessions_are_untouched(tmp_path):
    session = date(2026, 7, 29)
    bars = [
        (SYM, datetime(2026, 7, 29, 15, 14), 1042.6, 1042.6, 1042.4, 1042.6, 2383),
        (SYM, datetime(2026, 7, 29, 15, 15), 1042.6, 1042.6, 1042.6, 1042.6, 0),
    ]
    path = _make_file(tmp_path, session, bars)

    assert mark_file(path, session, {SYM}) == 0


def test_category_two_symbols_are_not_marked(tmp_path):
    session = date(2026, 8, 24)
    bars = [
        (SYM, datetime(2026, 8, 24, 15, 14), 100.0, 100.0, 100.0, 100.0, 500),
        (SYM, datetime(2026, 8, 24, 15, 20), 100.0, 100.0, 100.0, 100.0, 0),
    ]
    path = _make_file(tmp_path, session, bars)

    assert mark_file(path, session, cat1_symbols=set()) == 0


def test_index_symbols_are_rejected_even_if_passed_in(tmp_path):
    # NSE_INDEX volume is always 0, so the equity predicate would mark the
    # index's real closing value as fabricated. The guard rejects them.
    idx = "NSE_INDEX|Nifty 50"
    session = date(2026, 8, 4)
    bars = [
        (idx, datetime(2026, 8, 4, 15, 14), 24462.9, 24466.1, 24451.1, 24463.45, 0),
        (idx, datetime(2026, 8, 4, 15, 20), 24463.45, 24463.45, 24463.45, 24463.45, 0),
        (idx, datetime(2026, 8, 4, 15, 29), 24614.9, 24614.9, 24614.9, 24614.9, 0),
    ]
    path = _make_file(tmp_path, session, bars)

    assert mark_file(path, session, {idx}) == 0


# --- run(): snapshot safety and date scoping -------------------------------

_AUCTION_BARS = [
    (SYM, datetime(2026, 8, 24, 15, 14), 1305.0, 1305.1, 1302.9, 1304.1, 68944),
    (SYM, datetime(2026, 8, 24, 15, 15), 1304.1, 1304.1, 1304.1, 1304.1, 0),
    (SYM, datetime(2026, 8, 24, 15, 29), 1309.8, 1309.8, 1309.8, 1309.8, 377584),
]


def _synthetic_count(path):
    con = duckdb.connect(str(path), read_only=True)
    try:
        return con.execute("SELECT count(*) FROM candles WHERE is_synthetic").fetchone()[0]
    finally:
        con.close()


def _store(tmp_path, monkeypatch, sessions):
    for session in sessions:
        bars = [(s, ts.replace(year=session.year, month=session.month, day=session.day),
                 o, h, lo, c, v) for s, ts, o, h, lo, c, v in _AUCTION_BARS]
        _make_file(tmp_path, session, bars)
    monkeypatch.setattr(marker, "NATIVE_1M_DIR", tmp_path)
    monkeypatch.setattr(marker, "cat1_isin_symbols", lambda session: {SYM})


def test_a_rerun_never_overwrites_the_first_snapshot(tmp_path, monkeypatch):
    """The snapshot's whole value is that it predates the FIRST mark."""
    session = date(2026, 8, 24)
    _store(tmp_path, monkeypatch, [session])
    path = tmp_path / f"{session.isoformat()}.duckdb"
    snapshot = path.with_suffix(".duckdb.pre_cas_mark")

    assert marker.run(apply=True)["bars_flagged"] == 1
    assert _synthetic_count(path) == 1
    assert _synthetic_count(snapshot) == 0

    marker.run(apply=True)

    assert _synthetic_count(snapshot) == 0


def test_since_limits_which_sessions_are_touched(tmp_path, monkeypatch):
    early, late = date(2026, 8, 24), date(2026, 8, 31)
    _store(tmp_path, monkeypatch, [early, late])

    result = marker.run(apply=True, since=late)

    assert result["sessions"] == 1
    assert _synthetic_count(tmp_path / f"{late.isoformat()}.duckdb") == 1
    assert _synthetic_count(tmp_path / f"{early.isoformat()}.duckdb") == 0
    assert not (tmp_path / f"{early.isoformat()}.duckdb.pre_cas_mark").exists()
