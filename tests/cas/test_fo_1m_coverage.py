"""fo_equity_keys maps a renamed F&O name through the Upstox master.

NSE renamed ICICIPRULI to ICICILIFE on 2026-10-23 with the ISIN unchanged. The
EQUITY_L-derived instrument_master still carried the old symbol, so the name got
no 1m key, no bars were fetched and the TS Basis Daily build failed.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.cas.fo_1m_coverage import fo_equity_keys  # noqa: E402

D = date(2026, 10, 23)


def _stores(tmp_path, master_rows):
    fut = tmp_path / "fut.duckdb"
    with duckdb.connect(str(fut)) as c:
        c.execute("CREATE TABLE futures_bhavcopy (underlying VARCHAR, trade_date DATE, inst_type VARCHAR)")
        c.executemany("INSERT INTO futures_bhavcopy VALUES (?, ?, ?)",
                      [("ICICILIFE", D, "FUTSTK"), ("HDFCBANK", D, "FUTSTK"), ("NEWCO", D, "FUTSTK")])
    eq = tmp_path / "eq.duckdb"
    with duckdb.connect(str(eq)) as c:
        c.execute("CREATE TABLE instrument_master (symbol VARCHAR, series VARCHAR, isin VARCHAR)")
        c.executemany("INSERT INTO instrument_master VALUES (?, ?, ?)",
                      [("ICICIPRULI", "EQ", "INE726G01019"), ("HDFCBANK", "EQ", "INE040A01034")])
    master = tmp_path / "upstox.duckdb"
    with duckdb.connect(str(master)) as c:
        c.execute("CREATE TABLE instruments (tradingsymbol VARCHAR, instrument_type VARCHAR, "
                  "isin VARCHAR, snapshot_date VARCHAR)")
        if master_rows:
            c.executemany("INSERT INTO instruments VALUES (?, ?, ?, ?)", master_rows)
    con = duckdb.connect()
    con.execute(f"ATTACH '{fut}' AS fut (READ_ONLY)")
    con.execute(f"ATTACH '{eq}' AS eq (READ_ONLY)")
    return con, master


def test_renamed_name_falls_back_to_the_latest_upstox_snapshot(tmp_path):
    con, master = _stores(tmp_path, [
        ("ICICIPRULI", "EQ", "INE726G01019", "2026-10-23"),   # master lagged the rename that day
        ("ICICILIFE", "EQ", "INE726G01019", "2026-10-26"),
        ("ICICILIFE FUT 27 OCT 26", "FUT", None, "2026-10-26"),
    ])
    keys, unmapped = fo_equity_keys(con, D, master_db=master)
    assert keys == {"ICICILIFE": "NSE_EQ|INE726G01019", "HDFCBANK": "NSE_EQ|INE040A01034"}
    assert unmapped == ["NEWCO"]


def test_instrument_master_wins_over_the_upstox_master(tmp_path):
    con, master = _stores(tmp_path, [("HDFCBANK", "EQ", "INE000000000", "2026-10-26")])
    keys, _ = fo_equity_keys(con, D, master_db=master)
    assert keys["HDFCBANK"] == "NSE_EQ|INE040A01034"


def test_missing_upstox_master_leaves_names_unmapped(tmp_path):
    con, _ = _stores(tmp_path, [])
    keys, unmapped = fo_equity_keys(con, D, master_db=tmp_path / "absent.duckdb")
    assert keys == {"HDFCBANK": "NSE_EQ|INE040A01034"}
    assert unmapped == ["ICICILIFE", "NEWCO"]
