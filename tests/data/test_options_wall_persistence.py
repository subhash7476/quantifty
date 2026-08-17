"""Tests for the Options-Wall persistence layer.

Pins the three-table schema round-trips: scan_results append, session_regime
latest-wins read, and oi_baseline idempotent capture (INSERT OR IGNORE).
"""
from datetime import date, datetime

import duckdb

from core.analytics.chain_scanner import ScanResult
from core.data.options_provider import OptionChainRow
from core.options_wall import persistence


def _scan_row(strike, score):
    return ScanResult(
        underlying="NSE_INDEX|Nifty 50", expiry="2026-08-18", strike=strike,
        option_type=None, screen="premium_farm", structure="iron_fly",
        regime="Positive GEX (Stable)", score=score, credit=100.0,
        iv_minus_rv=score, pin_conviction=0.3, reason="x",
    )


def _chain_row(strike, otype, oi):
    return OptionChainRow(
        strike=strike, option_type=otype, instrument_key=f"K{strike}{otype}",
        tradingsymbol=f"K{strike}{otype}", expiry="2026-08-18", oi=oi,
    )


def test_write_scan_results(tmp_path):
    db = tmp_path / "results.duckdb"
    n = persistence.write_scan_results(
        [_scan_row(100.0, 8.0), _scan_row(101.0, 5.0)],
        "NSE_INDEX|Nifty 50", db_path=db)
    assert n == 2

    conn = duckdb.connect(str(db), read_only=True)
    rows = conn.execute("SELECT strike, score FROM scan_results ORDER BY score DESC").fetchall()
    conn.close()
    assert rows == [(100.0, 8.0), (101.0, 5.0)]


def test_scan_results_persist_iron_fly_legs(tmp_path):
    db = tmp_path / "results.duckdb"
    legs = [{"side": "SELL", "option_type": "CE", "strike": 100.0,
             "best_bid": 4.9, "best_ask": 5.1, "mid": 5.0},
            {"side": "BUY", "option_type": "CE", "strike": 102.0,
             "best_bid": 0.9, "best_ask": 1.1, "mid": 1.0}]
    r = ScanResult(
        underlying="NSE_INDEX|Nifty 50", expiry="2026-08-18", strike=100.0,
        option_type=None, screen="premium_farm", structure="iron_fly",
        regime="Positive GEX (Stable)", score=5.0, credit=10.0, iv_minus_rv=5.0,
        pin_conviction=0.9, reason="x", legs=legs)
    persistence.write_scan_results([r], "NSE_INDEX|Nifty 50", db_path=db)

    _, rows = persistence.latest_scan_results("NSE_INDEX|Nifty 50", db_path=db)
    assert rows[0]["legs"] == legs


def test_scan_results_schema_migrates_pre_existing_db(tmp_path):
    """A live scan_results table predating the legs column must ALTER cleanly and
    keep SELECT * column order aligned (legs appended last)."""
    db = tmp_path / "results.duckdb"
    conn = duckdb.connect(str(db))
    conn.execute(
        """CREATE TABLE scan_results (
            ts TIMESTAMP NOT NULL, underlying VARCHAR NOT NULL, expiry VARCHAR NOT NULL,
            strike DOUBLE, option_type VARCHAR, screen VARCHAR NOT NULL,
            structure VARCHAR NOT NULL, regime VARCHAR, score DOUBLE, credit DOUBLE,
            iv_minus_rv DOUBLE, pin_conviction DOUBLE, reason VARCHAR)""")
    conn.execute(
        "INSERT INTO scan_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [datetime(2026, 8, 14, 10, 0), "NSE_INDEX|Nifty 50", "2026-08-18", 100.0, None,
         "premium_farm", "iron_fly", "Positive GEX (Stable)", 5.0, 10.0, 5.0, 0.9, "old"])
    conn.close()

    legs = [{"side": "SELL", "option_type": "CE", "strike": 100.0,
             "best_bid": 4.9, "best_ask": 5.1, "mid": 5.0}]
    r = ScanResult(
        underlying="NSE_INDEX|Nifty 50", expiry="2026-08-18", strike=100.0,
        option_type=None, screen="premium_farm", structure="iron_fly",
        regime="Positive GEX (Stable)", score=6.0, credit=10.0, iv_minus_rv=6.0,
        pin_conviction=0.9, reason="new", legs=legs)
    persistence.write_scan_results([r], "NSE_INDEX|Nifty 50",
                                   ts=datetime(2026, 8, 14, 10, 0, 5), db_path=db)

    ts, rows = persistence.latest_scan_results("NSE_INDEX|Nifty 50", db_path=db)
    assert ts == datetime(2026, 8, 14, 10, 0, 5)   # newest cycle
    assert rows[0]["reason"] == "new"              # order not scrambled
    assert rows[0]["legs"] == legs


def test_regime_latest_wins(tmp_path):
    db = tmp_path / "results.duckdb"
    base = {"trade_date": date(2026, 8, 14), "regime": "Positive GEX (Stable)",
            "net_gamma_total": 1.0, "zero_gamma_level": 24300.0, "pin_strike": 24350.0,
            "put_wall": 24000.0, "call_wall": 24500.0, "atm_iv": 11.0, "realized_vol": 9.4}
    persistence.write_regime("NSE_INDEX|Nifty 50", base, db_path=db)
    later = dict(base, regime="Negative GEX (Volatile)", net_gamma_total=-2.0)
    persistence.write_regime("NSE_INDEX|Nifty 50", later, db_path=db)

    latest = persistence.latest_regime("NSE_INDEX|Nifty 50", date(2026, 8, 14), db_path=db)
    assert latest["regime"] == "Negative GEX (Volatile)"
    assert latest["net_gamma_total"] == -2.0


def test_oi_baseline_idempotent(tmp_path):
    db = tmp_path / "results.duckdb"
    chain = [_chain_row(100.0, "CE", 5000), _chain_row(100.0, "PE", 4000)]
    persistence.capture_oi_baseline(chain, "NSE_INDEX|Nifty 50",
                                    date(2026, 8, 14), db_path=db)
    persistence.capture_oi_baseline([_chain_row(100.0, "CE", 9999)],
                                    "NSE_INDEX|Nifty 50",
                                    date(2026, 8, 14), db_path=db)  # re-capture: ignored

    baseline = persistence.get_oi_baseline("NSE_INDEX|Nifty 50", date(2026, 8, 14), db_path=db)
    assert baseline[(100.0, "CE")] == 5000  # first capture wins, not 9999
    assert baseline[(100.0, "PE")] == 4000


def test_latest_scan_results_returns_newest_cycle(tmp_path):
    db = tmp_path / "results.duckdb"
    t1 = datetime(2026, 8, 14, 10, 0, 0)
    t2 = datetime(2026, 8, 14, 10, 0, 5)
    persistence.write_scan_results(
        [_scan_row(100.0, 8.0), _scan_row(101.0, 5.0)],
        "NSE_INDEX|Nifty 50", ts=t1, db_path=db)
    persistence.write_scan_results(
        [_scan_row(102.0, 9.0)],
        "NSE_INDEX|Nifty 50", ts=t2, db_path=db)

    ts, rows = persistence.latest_scan_results("NSE_INDEX|Nifty 50", db_path=db)
    assert ts == t2
    assert [r["strike"] for r in rows] == [102.0]  # newest cycle only, not t1's rows


def test_regime_persists_spot_and_gamma_ladder(tmp_path):
    db = tmp_path / "results.duckdb"
    snap = {"trade_date": date(2026, 8, 14), "regime": "Positive GEX (Stable)",
            "net_gamma_total": 1.0, "zero_gamma_level": 24300.0, "pin_strike": 24350.0,
            "put_wall": 24000.0, "call_wall": 24500.0, "atm_iv": 11.0, "realized_vol": 9.4,
            "underlying_ltp": 24312.5, "gamma_by_strike": {24300.0: 5.0, 24350.0: 8.0}}
    persistence.write_regime("NSE_INDEX|Nifty 50", snap, db_path=db)

    latest = persistence.latest_regime("NSE_INDEX|Nifty 50", date(2026, 8, 14), db_path=db)
    assert latest["underlying_ltp"] == 24312.5
    assert latest["gamma_by_strike"] == {"24300.0": 5.0, "24350.0": 8.0}

    river = persistence.regime_river("NSE_INDEX|Nifty 50", db_path=db)
    assert river[-1]["underlying_ltp"] == 24312.5
    assert river[-1]["gamma_by_strike"] == {"24300.0": 5.0, "24350.0": 8.0}


def test_regime_schema_migrates_pre_existing_db(tmp_path):
    """A live DB created before the spot/gamma columns must ALTER cleanly and keep
    SELECT * column order aligned with the read cols list (new cols appended last)."""
    db = tmp_path / "results.duckdb"
    conn = duckdb.connect(str(db))
    conn.execute(
        """CREATE TABLE session_regime (
            trade_date DATE NOT NULL, underlying VARCHAR NOT NULL, ts TIMESTAMP NOT NULL,
            regime VARCHAR, net_gamma_total DOUBLE, zero_gamma_level DOUBLE,
            pin_strike DOUBLE, put_wall DOUBLE, call_wall DOUBLE, atm_iv DOUBLE,
            realized_vol DOUBLE)""")
    conn.execute(
        "INSERT INTO session_regime VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [date(2026, 8, 13), "NSE_INDEX|Nifty 50", datetime(2026, 8, 13, 15, 0),
         "Positive GEX (Stable)", 1.0, 24300.0, 24350.0, 24000.0, 24500.0, 11.0, 9.4])
    conn.close()

    snap = {"trade_date": date(2026, 8, 14), "regime": "Negative GEX (Volatile)",
            "underlying_ltp": 24000.0, "gamma_by_strike": {24000.0: 1.0}}
    persistence.write_regime("NSE_INDEX|Nifty 50", snap, db_path=db)

    river = persistence.regime_river("NSE_INDEX|Nifty 50", db_path=db)
    assert [r["trade_date"] for r in river] == [date(2026, 8, 13), date(2026, 8, 14)]
    assert river[0]["underlying_ltp"] is None       # old row, pre-migration
    assert river[0]["regime"] == "Positive GEX (Stable)"  # order not scrambled
    assert river[1]["underlying_ltp"] == 24000.0    # new row
    assert river[1]["gamma_by_strike"] == {"24000.0": 1.0}


def test_regime_river_latest_per_day_ascending(tmp_path):
    db = tmp_path / "results.duckdb"
    base = {"regime": "Positive GEX (Stable)", "net_gamma_total": 1.0,
            "zero_gamma_level": 24300.0, "pin_strike": 24350.0, "put_wall": 24000.0,
            "call_wall": 24500.0, "atm_iv": 11.0, "realized_vol": 9.4}
    persistence.write_regime("NSE_INDEX|Nifty 50", dict(base, trade_date=date(2026, 8, 13)),
                             ts=datetime(2026, 8, 13, 15, 0), db_path=db)
    persistence.write_regime("NSE_INDEX|Nifty 50", dict(base, trade_date=date(2026, 8, 14),
                             regime="Negative GEX (Volatile)"),
                             ts=datetime(2026, 8, 14, 10, 0), db_path=db)
    persistence.write_regime("NSE_INDEX|Nifty 50", dict(base, trade_date=date(2026, 8, 14),
                             regime="Positive GEX (Stable)"),
                             ts=datetime(2026, 8, 14, 10, 5), db_path=db)

    river = persistence.regime_river("NSE_INDEX|Nifty 50", db_path=db)
    assert [r["trade_date"] for r in river] == [date(2026, 8, 13), date(2026, 8, 14)]
    assert river[1]["regime"] == "Positive GEX (Stable)"  # latest ts within the day wins


def test_open_trades_self_heals_missing_trades_table(tmp_path):
    """A results DB that predates the trades table (only scan tables exist) must
    read as empty without a Catalog Error — the executor's first step runs
    open_trades before open_paper_trade, so the read path cannot depend on a
    writer having initialized the schema first."""
    db = tmp_path / "results.duckdb"
    conn = duckdb.connect(str(db))
    conn.execute("CREATE TABLE scan_results (ts TIMESTAMP NOT NULL, underlying VARCHAR)")
    conn.execute("INSERT INTO scan_results VALUES (?,?)",
                 [datetime(2026, 8, 14, 10, 0), "NSE_INDEX|Nifty 50"])
    conn.commit()
    conn.close()

    assert persistence.open_trades("NSE_INDEX|Nifty 50", db_path=db) == []

    conn = duckdb.connect(str(db), read_only=True)
    tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
    conn.close()
    assert "trades" in tables  # healed, not just papered over

    assert persistence.open_trades("NSE_INDEX|Nifty 50", db_path=db) == []  # idempotent
