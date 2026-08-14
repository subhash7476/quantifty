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
