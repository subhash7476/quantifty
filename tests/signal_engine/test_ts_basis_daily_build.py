"""build_ts_basis_daily — regressions from TS_BASIS_DAILY_SIGNAL_AUDIT_2026-09-11.

F5: ADV was a median over per-contract rows and the join fanned out, so `liquid` was
    an arbitrary pick. F2/F4: the build could only append, never rebuild. F7: forward
    returns of each run's last date were never filled. F3 needs the unclamped z stored.
"""
from __future__ import annotations

import math
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "ts_basis_daily"))

import build_ts_basis_daily as B  # noqa: E402

EXPIRIES = [date(2026, 6, 30), date(2026, 7, 28), date(2026, 8, 25)]
# name -> (near-contract turnover, next-contract turnover), in lakh
TURNOVER = {"AAA": (300, 300), "BBB": (200, 100), "CCC": (900, 50), "DDD": (600, 10),
            "EEE": (700, 20), "FFF": (800, 30)}


def _sessions(n):
    out, d = [], date(2026, 6, 1)
    while len(out) < n:
        if d.weekday() < 5 and d != date(2026, 6, 26):
            out.append(d)
        d += timedelta(days=1)
    return out


def _write_day(fut, eq, d, day_idx):
    for k, (u, (v_near, v_next)) in enumerate(TURNOVER.items()):
        spot = 100.0 + k + day_idx * 0.1
        basis = 0.004 + 0.003 * math.sin(day_idx * 0.7 + k)
        if u == "FFF" and day_idx == 25:
            basis = 0.2                                   # one spike: raw_z far beyond 3
        eq.execute("INSERT INTO equity_bhavcopy VALUES (?, ?, 'EQ', ?)", [d, u, spot])
        eq.execute("INSERT INTO equity_bhavcopy_adjusted VALUES (?, ?, 'EQ', ?)", [d, u, spot])
        live = [x for x in EXPIRIES if x >= d][:2]
        for x, v in zip(live, (v_near, v_next)):
            fut.execute("INSERT INTO futures_bhavcopy VALUES (?, ?, 'FUTSTK', ?, ?, ?, ?)",
                        [d, u, x, spot * (1 + basis), spot * (1 + basis), v])


@pytest.fixture
def stores(tmp_path, monkeypatch):
    fut = duckdb.connect(str(tmp_path / "fut.duckdb"))
    fut.execute("CREATE TABLE futures_bhavcopy (trade_date DATE, underlying VARCHAR, inst_type VARCHAR, "
                "expiry_dt DATE, close DOUBLE, settle DOUBLE, val_in_lakh DOUBLE)")
    eq = duckdb.connect(str(tmp_path / "eq.duckdb"))
    eq.execute("CREATE TABLE equity_bhavcopy (trade_date DATE, symbol VARCHAR, series VARCHAR, close DOUBLE)")
    eq.execute("CREATE TABLE equity_bhavcopy_adjusted (trade_date DATE, symbol VARCHAR, series VARCHAR, close DOUBLE)")
    eq.execute("CREATE TABLE symbol_entity_intervals (symbol VARCHAR, valid_from DATE, valid_to DATE, entity VARCHAR)")
    for u in TURNOVER:
        eq.execute("INSERT INTO symbol_entity_intervals VALUES (?, DATE '2000-01-01', NULL, ?)", [u, u])
    days = _sessions(30)
    for i, d in enumerate(days[:-1]):
        _write_day(fut, eq, d, i)
    fut.close()
    eq.close()
    monkeypatch.setattr(B, "FUT_DB", tmp_path / "fut.duckdb")
    monkeypatch.setattr(B, "EQ_DB", tmp_path / "eq.duckdb")
    monkeypatch.setattr(B, "OUT_DB", tmp_path / "out" / "ts_signals.duckdb")
    monkeypatch.setattr(B, "BASELINE_DIR", tmp_path / "baselines")

    def add_last_day():
        f = duckdb.connect(str(tmp_path / "fut.duckdb"))
        e = duckdb.connect(str(tmp_path / "eq.duckdb"))
        _write_day(f, e, days[-1], len(days) - 1)
        f.close()
        e.close()

    return {"days": days, "add_last_day": add_last_day, "tmp": tmp_path}


def _run(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["build_ts_basis_daily.py", *args])
    return B.main()


def _rows(path):
    con = duckdb.connect(str(path), read_only=True)
    rows = con.execute("SELECT formation_date, underlying, raw_ann_basis, raw_z, z_ts, fwd_ret_1m, liquid "
                       "FROM signals ORDER BY 1, 2").fetchall()
    con.close()
    return rows


def test_liquid_uses_daily_total_turnover_across_contracts(stores, monkeypatch):
    assert _run(monkeypatch) == 0
    con = duckdb.connect(str(B.OUT_DB), read_only=True)
    liq = dict(con.execute("SELECT underlying, BOOL_AND(liquid) FROM signals GROUP BY 1").fetchall())
    con.close()
    assert liq["AAA"] is True        # 300 + 300 per day clears 500; the per-contract median never did
    assert liq["BBB"] is False       # 200 + 100


def test_z_ts_is_raw_z_clamped_and_raw_z_keeps_the_tail(stores, monkeypatch):
    assert _run(monkeypatch) == 0
    rows = [r for r in _rows(B.OUT_DB) if r[3] is not None]
    assert rows
    assert all(r[4] == max(-3.0, min(3.0, r[3])) for r in rows)
    assert max(r[3] for r in rows) > 3.0


def test_names_without_enough_history_have_no_z(stores, monkeypatch):
    # DuckDB's GREATEST/LEAST skip NULLs: clamping a NULL raw_z must not yield ±3.
    assert _run(monkeypatch) == 0
    early = [r for r in _rows(B.OUT_DB) if r[0] <= stores["days"][B.MIN_OBS - 1]]
    assert early and all(r[3] is None and r[4] is None for r in early)


def test_incremental_run_matches_a_full_build(stores, monkeypatch):
    assert _run(monkeypatch) == 0
    stores["add_last_day"]()
    assert _run(monkeypatch, "--incremental") == 0
    incremental = _rows(B.OUT_DB)

    monkeypatch.setattr(B, "OUT_DB", stores["tmp"] / "full" / "ts_signals.duckdb")
    assert _run(monkeypatch) == 0
    assert incremental == _rows(B.OUT_DB)
    prev_last = stores["days"][-2]
    assert all(r[5] is not None for r in incremental if r[0] == prev_last)


def test_full_rebuild_replaces_the_store_and_keeps_a_baseline(stores, monkeypatch):
    assert _run(monkeypatch) == 0
    first = _rows(B.OUT_DB)
    assert _run(monkeypatch) == 0
    assert _rows(B.OUT_DB) == first
    baselines = list((stores["tmp"] / "baselines").glob("ts_basis_daily_signals_*.duckdb"))
    assert len(baselines) == 1 and baselines[0].stat().st_size > 0
    assert _rows(baselines[0]) == first


def test_drops_cells_priced_off_an_expiring_contract_with_no_successor(stores, monkeypatch):
    # F11: a name leaving F&O keeps pricing off its last contract into expiry, where
    # 365 / days_to_expiry turns a few paise of basis into a triple-digit annualized rate.
    fut = duckdb.connect(str(stores["tmp"] / "fut.duckdb"))
    eq = duckdb.connect(str(stores["tmp"] / "eq.duckdb"))
    for d in stores["days"][:-1]:
        if d <= EXPIRIES[0]:
            eq.execute("INSERT INTO equity_bhavcopy VALUES (?, 'GGG', 'EQ', 100.0)", [d])
            fut.execute("INSERT INTO futures_bhavcopy VALUES (?, 'GGG', 'FUTSTK', ?, 100.3, 100.3, 900)",
                        [d, EXPIRIES[0]])
    fut.close()
    eq.close()

    assert _run(monkeypatch) == 0
    by_name = {}
    for r in _rows(B.OUT_DB):
        by_name.setdefault(r[1], set()).add(r[0])
    roll_window = {date(2026, 6, 24), date(2026, 6, 25), date(2026, 6, 29), date(2026, 6, 30)}
    assert date(2026, 6, 23) in by_name["GGG"]
    assert not by_name["GGG"] & roll_window
    assert roll_window <= by_name["AAA"]          # names with a next contract roll and stay


def test_incremental_refuses_a_store_without_raw_z(stores, monkeypatch):
    B.OUT_DB.parent.mkdir(parents=True)
    con = duckdb.connect(str(B.OUT_DB))
    con.execute("CREATE TABLE signals (formation_date DATE, underlying VARCHAR, raw_ann_basis DOUBLE, "
                "z_ts DOUBLE, fwd_ret_1m DOUBLE, liquid BOOLEAN)")
    con.execute("INSERT INTO signals VALUES (DATE '2026-06-01', 'AAA', 0.1, NULL, NULL, TRUE)")
    con.close()
    with pytest.raises(SystemExit, match="without --incremental"):
        _run(monkeypatch, "--incremental")
    con = duckdb.connect(str(B.OUT_DB), read_only=True)
    assert con.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == 1
    con.close()
