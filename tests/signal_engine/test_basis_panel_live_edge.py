"""build_basis_panel must apply the T-3 roll at the live edge.

Regression (TS_BASIS_DAILY_SIGNAL_AUDIT_2026-09-11 F1): trading days to expiry were
counted only against trade dates already in the futures store. While the near expiry
was still in the future the count was NULL, the roll never fired, and every live
formation at T-3..T-1 priced basis off the expiring contract.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))

import contract_arms as A  # noqa: E402

SEP_EXP = date(2026, 9, 29)
OCT_EXP = date(2026, 10, 27)


def _weekdays(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _panel(tmp_path, trade_dates, expiries, holidays=None, monkeypatch=None):
    fut = duckdb.connect(str(tmp_path / "fut.duckdb"))
    fut.execute("CREATE TABLE futures_bhavcopy (trade_date DATE, underlying VARCHAR, "
                "inst_type VARCHAR, expiry_dt DATE, close DOUBLE, settle DOUBLE, val_in_lakh DOUBLE)")
    eq = duckdb.connect(str(tmp_path / "eq.duckdb"))
    eq.execute("CREATE TABLE equity_bhavcopy (trade_date DATE, symbol VARCHAR, series VARCHAR, close DOUBLE)")
    eq.execute("CREATE TABLE symbol_entity_intervals (symbol VARCHAR, valid_from DATE, valid_to DATE, entity VARCHAR)")
    eq.execute("INSERT INTO symbol_entity_intervals VALUES ('XYZ', DATE '2000-01-01', NULL, 'XYZ')")
    for d in trade_dates:
        eq.execute("INSERT INTO equity_bhavcopy VALUES (?, 'XYZ', 'EQ', 100.0)", [d])
        for i, x in enumerate(expiries):
            if x >= d:
                fut.execute("INSERT INTO futures_bhavcopy VALUES (?, 'XYZ', 'FUTSTK', ?, ?, ?, 1000)",
                            [d, x, 100.5 + i, 100.5 + i])
    fut.close()
    eq.close()
    if holidays is not None:
        monkeypatch.setattr(A, "NSE_HOLIDAYS", frozenset(holidays))
    con = duckdb.connect()
    con.execute(f"ATTACH '{tmp_path / 'fut.duckdb'}' AS fut (READ_ONLY)")
    con.execute(f"ATTACH '{tmp_path / 'eq.duckdb'}' AS eq (READ_ONLY)")
    A.build_basis_panel(con)
    return dict(con.execute("SELECT trade_date, expiry_dt FROM basis_panel").fetchall())


def test_live_edge_t_minus_2_rolls_to_next_contract(tmp_path):
    # Store ends Fri 2026-09-25; Sept expiry Tue 09-29 is 2 sessions away (09-28, 09-29).
    sel = _panel(tmp_path, _weekdays(date(2026, 9, 1), date(2026, 9, 25)), [SEP_EXP, OCT_EXP])
    assert sel[date(2026, 9, 25)] == OCT_EXP     # T-2
    assert sel[date(2026, 9, 24)] == OCT_EXP     # T-3
    assert sel[date(2026, 9, 23)] == SEP_EXP     # T-4 keeps the near contract


def test_live_edge_matches_the_same_dates_built_after_expiry(tmp_path):
    days = _weekdays(date(2026, 9, 1), date(2026, 10, 2))
    (tmp_path / "live").mkdir()
    (tmp_path / "full").mkdir()
    live = _panel(tmp_path / "live", [d for d in days if d <= date(2026, 9, 25)], [SEP_EXP, OCT_EXP])
    full = _panel(tmp_path / "full", days, [SEP_EXP, OCT_EXP])
    assert {d: x for d, x in full.items() if d in live} == live


def test_forward_count_skips_known_holidays(tmp_path, monkeypatch):
    # Store ends Wed 09-30; synthetic expiry Tue 10-06. Weekdays after: 10-01, 10-02, 10-05, 10-06 = 4.
    # With 10-02 a holiday only 3 sessions remain, so the roll must fire.
    exp = date(2026, 10, 6)
    days = _weekdays(date(2026, 9, 1), date(2026, 9, 30))
    assert _panel(tmp_path, days, [exp, OCT_EXP], holidays={date(2026, 10, 2)},
                  monkeypatch=monkeypatch)[date(2026, 9, 30)] == OCT_EXP


def test_without_the_holiday_the_same_date_keeps_the_near_contract(tmp_path, monkeypatch):
    exp = date(2026, 10, 6)
    days = _weekdays(date(2026, 9, 1), date(2026, 9, 30))
    assert _panel(tmp_path, days, [exp, OCT_EXP], holidays={date(2026, 1, 26)},
                  monkeypatch=monkeypatch)[date(2026, 9, 30)] == exp


def test_raises_when_an_uncovered_year_could_flip_the_roll(tmp_path, monkeypatch):
    # Near expiry 2027-01-26 is 4 weekdays after 01-20, and no 2027 holidays are known.
    days = _weekdays(date(2027, 1, 4), date(2027, 1, 20))
    with pytest.raises(RuntimeError, match="2027"):
        _panel(tmp_path, days, [date(2027, 1, 26), date(2027, 2, 23)],
               holidays={date(2026, 12, 25)}, monkeypatch=monkeypatch)


def test_uncovered_year_far_from_expiry_does_not_raise(tmp_path, monkeypatch):
    # Near expiry 2027-01-26 is ~18 weekdays after 12-30; unknown holidays cannot reach the roll.
    days = _weekdays(date(2026, 12, 1), date(2026, 12, 30))
    sel = _panel(tmp_path, days, [date(2026, 12, 29), date(2027, 1, 26), date(2027, 2, 23)],
                 holidays={date(2026, 12, 25)}, monkeypatch=monkeypatch)
    assert sel[date(2026, 12, 30)] == date(2027, 1, 26)
