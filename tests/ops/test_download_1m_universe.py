"""The daily 1m download must cover every F&O stock, not only the Nifty 200.

TS Basis Daily prices post-CAS spot off each F&O name's last continuous-session 1m
bar and fails its build on any gap (TS_BASIS_DAILY_SIGNAL_AUDIT_2026-09-11 F10).
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.download_all_data as D  # noqa: E402


def test_1m_universe_includes_every_futstk_underlying(tmp_path, monkeypatch):
    fut = duckdb.connect(str(tmp_path / "fut.duckdb"))
    fut.execute("CREATE TABLE futures_bhavcopy (trade_date DATE, underlying VARCHAR, inst_type VARCHAR)")
    fut.executemany("INSERT INTO futures_bhavcopy VALUES (?, ?, ?)", [
        (date(2026, 9, 9), "OLDNAME", "FUTSTK"),
        (date(2026, 9, 10), "ANGELONE", "FUTSTK"),
        (date(2026, 9, 10), "RELIANCE", "FUTSTK"),
        (date(2026, 9, 10), "NIFTY", "FUTIDX"),
    ])
    fut.close()
    eq = duckdb.connect(str(tmp_path / "eq.duckdb"))
    eq.execute("CREATE TABLE instrument_master (symbol VARCHAR, series VARCHAR, isin VARCHAR)")
    eq.executemany("INSERT INTO instrument_master VALUES (?, 'EQ', ?)",
                   [("ANGELONE", "INE732I01021"), ("RELIANCE", "INE002A01018"), ("OLDNAME", "INE999Z01011")])
    eq.close()
    csv = tmp_path / "nifty200.csv"
    csv.write_text("Symbol,ISIN Code\nRELIANCE,INE002A01018\nTCS,INE467B01029\n", encoding="utf-8")

    monkeypatch.setattr(D, "FUTURES_DB", tmp_path / "fut.duckdb")
    monkeypatch.setattr(D, "EQUITY_DB", tmp_path / "eq.duckdb")
    monkeypatch.setattr(D, "NIFTY200_CSV", csv)
    monkeypatch.setattr(D, "CANDLES_1M_DIR", tmp_path / "1m")
    calls = []
    monkeypatch.setattr(D, "_run", lambda script, args=None, label="", timeout=None: calls.append(args) or True)

    assert D._download_1m_candles(full=False, lookback=7)
    keys = set(calls[0][calls[0].index("--instrument_key") + 1].split(","))
    assert {"NSE_EQ|INE732I01021", "NSE_EQ|INE002A01018", "NSE_EQ|INE467B01029"} <= keys
    assert "NSE_EQ|INE999Z01011" not in keys          # no longer in F&O on the latest date
