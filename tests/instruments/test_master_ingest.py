"""
Phase 4C.1 — Extend the instrument-master SSOT.

CANONICAL_INSTRUMENT_ARCHITECTURE.md §D1.2 / §D7.2: the master ingests only
NSE_FO + MCX_FO today (fetch_instrument_master.py:83) and has no isin/tick_size
columns and no point-in-time history. These tests drive:
  - ingest of NSE_EQ + NSE_INDEX (equity/index are first-class, §D2.2),
  - extraction of isin + tick_size (§D3, §D5),
  - effective-dated snapshots (snapshot_date) so resolution can be as_of-aware
    (§D7.4 — lot sizes change, e.g. the post-2024 SEBI NIFTY 50->75 revision).

The pure parse step and the DB write step are exercised directly; the network
download is not under test.
"""
import duckdb

from scripts.fetch_instrument_master import parse_instruments, write_snapshot


def _raw():
    """A synthetic slice of the Upstox complete-instruments master."""
    return [
        {  # index option (NSE_FO)
            "segment": "NSE_FO", "instrument_key": "NSE_FO|54710",
            "tradingsymbol": "NIFTY26FEB2522500CE", "name": "NIFTY",
            "expiry": "2026-02-25", "strike_price": 22500.0,
            "instrument_type": "CE", "lot_size": 75, "tick_size": 0.05,
        },
        {  # index future (NSE_FO)
            "segment": "NSE_FO", "instrument_key": "NSE_FO|53001",
            "tradingsymbol": "NIFTY26FEBFUT", "name": "NIFTY",
            "expiry": "2026-02-26", "strike_price": 0.0,
            "instrument_type": "FUT", "lot_size": 75, "tick_size": 0.05,
        },
        {  # cash equity (NSE_EQ) — must be ingested now
            "segment": "NSE_EQ", "instrument_key": "NSE_EQ|INE002A01018",
            "tradingsymbol": "RELIANCE", "name": "RELIANCE INDUSTRIES",
            "expiry": None, "strike_price": 0.0,
            "instrument_type": "EQ", "lot_size": 1, "tick_size": 0.05,
            "isin": "INE002A01018",
        },
        {  # index (NSE_INDEX) — must be ingested now
            "segment": "NSE_INDEX", "instrument_key": "NSE_INDEX|Nifty 50",
            "tradingsymbol": "Nifty 50", "name": "NIFTY",
            "expiry": None, "strike_price": 0.0,
            "instrument_type": "INDEX", "lot_size": 0, "tick_size": 0.0,
        },
        {  # commodity future (MCX_FO) — still ingested
            "segment": "MCX_FO", "instrument_key": "MCX_FO|12345",
            "tradingsymbol": "CRUDEOIL26FEBFUT", "name": "CRUDE OIL",
            "expiry": "2026-02-19", "strike_price": 0.0,
            "instrument_type": "FUT", "lot_size": 100, "tick_size": 1.0,
        },
        {  # BSE equity — out of scope, must be dropped
            "segment": "BSE_EQ", "instrument_key": "BSE_EQ|INE002A01018",
            "tradingsymbol": "RELIANCE", "name": "RELIANCE INDUSTRIES",
            "instrument_type": "EQ", "lot_size": 1,
        },
    ]


def test_parse_includes_eq_and_index_and_fo_excludes_other_exchanges():
    rows = parse_instruments(_raw(), snapshot_date="2026-02-01")
    segments = {r["exchange"] for r in rows}
    assert segments == {"NSE_FO", "NSE_EQ", "NSE_INDEX", "MCX_FO"}
    keys = {r["instrument_key"] for r in rows}
    assert "BSE_EQ|INE002A01018" not in keys


def test_parse_extracts_isin_and_tick_size():
    rows = parse_instruments(_raw(), snapshot_date="2026-02-01")
    eq = next(r for r in rows if r["instrument_key"] == "NSE_EQ|INE002A01018")
    assert eq["isin"] == "INE002A01018"
    assert eq["tick_size"] == 0.05
    opt = next(r for r in rows if r["instrument_key"] == "NSE_FO|54710")
    assert opt["tick_size"] == 0.05


def test_parse_stamps_snapshot_date_on_every_row():
    rows = parse_instruments(_raw(), snapshot_date="2026-02-01")
    assert rows
    assert all(r["snapshot_date"] == "2026-02-01" for r in rows)


def test_write_snapshot_creates_queryable_table_with_new_columns(tmp_path):
    db = tmp_path / "instruments.duckdb"
    rows = parse_instruments(_raw(), snapshot_date="2026-02-01")
    n = write_snapshot(rows, db_path=db)
    assert n == len(rows)

    con = duckdb.connect(str(db), read_only=True)
    cols = {c[0] for c in con.execute("DESCRIBE instruments").fetchall()}
    assert {"isin", "tick_size", "snapshot_date"} <= cols
    eq = con.execute(
        "SELECT isin, tick_size FROM instruments WHERE instrument_key = ?",
        ["NSE_EQ|INE002A01018"],
    ).fetchone()
    con.close()
    assert eq == ("INE002A01018", 0.05)


def test_write_snapshot_accumulates_history_across_dates(tmp_path):
    """The SEBI 50->75 lot revision: same contract, two snapshots, both retained."""
    db = tmp_path / "instruments.duckdb"
    old = [{
        "segment": "NSE_FO", "instrument_key": "NSE_FO|54710",
        "tradingsymbol": "NIFTY24JAN0022500CE", "name": "NIFTY",
        "expiry": "2024-01-25", "strike_price": 22500.0,
        "instrument_type": "CE", "lot_size": 50, "tick_size": 0.05,
    }]
    new = [{
        "segment": "NSE_FO", "instrument_key": "NSE_FO|54710",
        "tradingsymbol": "NIFTY24DEC0022500CE", "name": "NIFTY",
        "expiry": "2024-12-25", "strike_price": 22500.0,
        "instrument_type": "CE", "lot_size": 75, "tick_size": 0.05,
    }]
    write_snapshot(parse_instruments(old, "2024-01-01"), db_path=db)
    write_snapshot(parse_instruments(new, "2024-12-01"), db_path=db)

    con = duckdb.connect(str(db), read_only=True)
    rows = con.execute(
        "SELECT snapshot_date, lot_size FROM instruments "
        "WHERE instrument_key = ? ORDER BY snapshot_date",
        ["NSE_FO|54710"],
    ).fetchall()
    con.close()
    assert rows == [("2024-01-01", 50), ("2024-12-01", 75)]


def test_write_snapshot_is_idempotent_within_a_date(tmp_path):
    db = tmp_path / "instruments.duckdb"
    rows = parse_instruments(_raw(), snapshot_date="2026-02-01")
    write_snapshot(rows, db_path=db)
    write_snapshot(rows, db_path=db)  # re-run same day

    con = duckdb.connect(str(db), read_only=True)
    total = con.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
    con.close()
    assert total == len(rows)
