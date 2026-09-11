"""select_eod_options — the EOD Telegram book prices options strictly at the formation date's close.

The live selector anchors on the futures LTP at run time and reads each chain at its
latest stored date. The Telegram book must instead use that day's futures close, and
the close of a strike that actually traded that day. On 2026-09-10, 18,389 of 27,956
option rows had no trades, and their `close` carries an earlier day's print
(ZYDUSLIFE 1000 CE: close 176.00, settle 122.16, 0 contracts).
"""
from datetime import date

import duckdb
import pytest

import core.analytics.options_selection as S

ON = date(2026, 9, 10)
LATER = date(2026, 9, 11)
NEAR = date(2026, 9, 15)       # < 7 days out: skipped
EXPIRY = date(2026, 9, 29)


@pytest.fixture
def stores(tmp_path, monkeypatch):
    o = duckdb.connect(str(tmp_path / "opt.duckdb"))
    o.execute("CREATE TABLE stock_options_bhavcopy (underlying VARCHAR, expiry_dt DATE, strike DOUBLE, "
              "option_type VARCHAR, close DOUBLE, settle DOUBLE, contracts BIGINT, open_int BIGINT, trade_date DATE)")
    f = duckdb.connect(str(tmp_path / "fut.duckdb"))
    f.execute("CREATE TABLE futures_bhavcopy (underlying VARCHAR, inst_type VARCHAR, expiry_dt DATE, "
              "close DOUBLE, trade_date DATE)")
    i = duckdb.connect(str(tmp_path / "inst.duckdb"))
    i.execute("CREATE TABLE instruments (snapshot_date DATE, instrument_type VARCHAR, tradingsymbol VARCHAR, "
              "name VARCHAR, strike DOUBLE, expiry VARCHAR, instrument_key VARCHAR, lot_size INTEGER)")
    i.execute("INSERT INTO instruments VALUES (?, 'EQ', 'AAA', 'AAA LTD', NULL, NULL, 'NSE_EQ|X', NULL)", [ON])
    for strike in (95.0, 100.0, 105.0, 110.0):
        for opt in ("CE", "PE"):
            i.execute("INSERT INTO instruments VALUES (?, ?, ?, 'AAA LTD', ?, ?, ?, 500)",
                      [ON, opt, f"AAA{strike:g}{opt}", strike, EXPIRY.isoformat(), f"NSE_FO|{strike:g}{opt}"])
    o.close(); f.close(); i.close()
    monkeypatch.setattr(S, "OPT_DB", tmp_path / "opt.duckdb")
    monkeypatch.setattr(S, "FUT_DB", tmp_path / "fut.duckdb")
    monkeypatch.setattr(S, "INST_DB", tmp_path / "inst.duckdb")
    return tmp_path


def _insert(path, table, rows):
    con = duckdb.connect(str(path))
    cols = {"stock_options_bhavcopy": 9, "futures_bhavcopy": 5}[table]
    con.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * cols)})", rows)
    con.close()


def test_premium_is_the_formation_dates_close_at_the_nearest_traded_strike(stores):
    _insert(stores / "fut.duckdb", "futures_bhavcopy", [
        ("AAA", "FUTSTK", EXPIRY, 101.0, ON),
        ("AAA", "FUTSTK", EXPIRY, 109.0, LATER),          # a later close must not move ATM
    ])
    _insert(stores / "opt.duckdb", "stock_options_bhavcopy", [
        ("AAA", NEAR, 100.0, "CE", 2.0, 2.0, 50, 9000, ON),
        ("AAA", EXPIRY, 95.0, "CE", 8.1, 8.0, 12, 5000, ON),
        ("AAA", EXPIRY, 100.0, "CE", 9.9, 6.2, 0, 7000, ON),    # nearest listed, untraded: stale close
        ("AAA", EXPIRY, 105.0, "CE", 3.4, 3.1, 40, 6000, ON),   # traded, 4.0 from the forward
        ("AAA", EXPIRY, 100.0, "CE", 4.4, 4.4, 90, 7000, LATER),
    ])
    [row] = S.select_eod_options([("AAA", "LONG")], on=ON)
    assert row["expiry"] == EXPIRY
    assert row["forward"] == 101.0
    assert row["strike"] == 105.0 and row["premium"] == 3.4
    assert row["quote_date"] == ON and row["lot_size"] == 500 and row["premium_cost"] == 1700.0


def test_name_with_no_traded_strike_near_atm_is_skipped_with_the_date(stores):
    _insert(stores / "fut.duckdb", "futures_bhavcopy", [("AAA", "FUTSTK", EXPIRY, 101.0, ON)])
    _insert(stores / "opt.duckdb", "stock_options_bhavcopy", [
        ("AAA", EXPIRY, strike, "PE", 5.0, 5.0, 0, 1000, ON) for strike in (95.0, 100.0, 105.0, 110.0)
    ] + [("AAA", EXPIRY, 100.0, "PE", 5.5, 5.5, 30, 1000, LATER)])
    [row] = S.select_eod_options([("AAA", "SHORT")], on=ON)
    assert row["opt_type"] == "PE" and row["strike"] is None and row["premium"] is None
    assert "2026-09-10" in row["screen_reason"] and "no trades" in row["screen_reason"]


def test_name_without_a_futures_close_that_day_is_skipped(stores):
    _insert(stores / "fut.duckdb", "futures_bhavcopy", [("AAA", "FUTSTK", EXPIRY, 101.0, LATER)])
    _insert(stores / "opt.duckdb", "stock_options_bhavcopy", [("AAA", EXPIRY, 100.0, "CE", 5.0, 5.0, 9, 1000, ON)])
    [row] = S.select_eod_options([("AAA", "LONG")], on=ON)
    assert row["strike"] is None
    assert "futures close" in row["screen_reason"] and "2026-09-10" in row["screen_reason"]
