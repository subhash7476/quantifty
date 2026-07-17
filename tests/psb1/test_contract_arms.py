"""Unit tests for the four-arm contract suite (Prompt 5-C).

Each test builds a minimal DuckDB fixture and verifies the arm catches (or doesn't
catch) the target condition. The arms are pure functions over a read-only connection.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))
sys.path.insert(0, str(ROOT / "scripts" / "csmp"))

import contract_arms as A


def _build_fixture(tmp_path, rows_adj, rows_raw, intervals, factors, isin_map=None):
    """Build a minimal store fixture. Returns a read-only connection.

    rows_adj / rows_raw: list of (trade_date, symbol, series, open, close, turnover, prev_close)
    """
    db = tmp_path / "fixture.duckdb"
    con = duckdb.connect(str(db))
    for tbl, cols in [
        ("equity_bhavcopy_adjusted",
         "trade_date DATE, symbol VARCHAR, series VARCHAR, open DOUBLE, high DOUBLE, "
         "low DOUBLE, close DOUBLE, prev_close DOUBLE, volume DOUBLE, turnover DOUBLE, "
         "deliv_qty DOUBLE, deliv_pct DOUBLE"),
        ("equity_bhavcopy",
         "trade_date DATE, symbol VARCHAR, series VARCHAR, open DOUBLE, high DOUBLE, "
         "low DOUBLE, close DOUBLE, prev_close DOUBLE, volume DOUBLE, turnover DOUBLE, "
         "deliv_qty DOUBLE, deliv_pct DOUBLE"),
    ]:
        con.execute(f"CREATE TABLE {tbl} ({cols})")
        for r in rows_adj:
            con.execute(f"INSERT INTO {tbl} VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        [r[0], r[1], r[2], r[3], r[3], r[3], r[4], r[6], 0, r[5], 0, 0])
    con.execute("CREATE TABLE symbol_entity_intervals "
                "(symbol VARCHAR, valid_from DATE, valid_to DATE, entity VARCHAR)")
    for iv in intervals:
        con.execute("INSERT INTO symbol_entity_intervals VALUES (?,?,?,?)", iv)
    con.execute("CREATE TABLE adjustment_factors "
                "(symbol VARCHAR, ex_date DATE, factor DOUBLE, action_type VARCHAR, source VARCHAR)")
    for f in factors:
        con.execute("INSERT INTO adjustment_factors VALUES (?,?,?,?,?)", f)
    con.execute("CREATE TABLE symbol_isin (symbol VARCHAR, isin VARCHAR)")
    if isin_map:
        for sym, isin in isin_map:
            con.execute("INSERT INTO symbol_isin VALUES (?,?)", [sym, isin])
    con.close()
    return duckdb.connect(str(db), read_only=True)


# ──────────────────────────────────────────────────────────────────────────────
# Arm A — CA-shaped orphan detection
# ──────────────────────────────────────────────────────────────────────────────
def test_arm_a_catches_ca_shaped_orphan(tmp_path):
    """A 1:5 split move (survived ~0.2) with no factor should be flagged."""
    d1, d2 = date(2018, 4, 18), date(2018, 4, 19)
    rows = [
        (d1, "TEST", "EQ", 100.0, 100.0, 50.0, 100.0),   # close=100, turnover=50
        (d2, "TEST", "EQ", 20.0, 20.0, 60.0, 100.0),      # close=20 (1:5 split, no factor)
    ]
    intervals = [("TEST", d1, date(9999, 12, 31), "TEST")]
    con = _build_fixture(tmp_path, rows, [], intervals, [])
    fbe = {}  # no factors
    res = A.arm_a(con, fbe)
    assert len(res.violations) >= 1, "Arm A should catch the CA-shaped orphan"
    assert res.violations[0][4] == "CA-shaped-orphan"
    con.close()


def test_arm_a_passes_ca_explained(tmp_path):
    """A 1:5 split move WITH a matching spanning factor should NOT be flagged."""
    d1, d2 = date(2018, 4, 18), date(2018, 4, 19)
    rows = [
        (d1, "TEST", "EQ", 100.0, 100.0, 50.0, 100.0),
        (d2, "TEST", "EQ", 20.0, 20.0, 60.0, 100.0),
    ]
    intervals = [("TEST", d1, date(9999, 12, 31), "TEST")]
    factors = [("TEST", d2, 0.2, "SPLIT", "test")]
    con = _build_fixture(tmp_path, rows, [], intervals, factors)
    fbe = {"TEST": [(d2, 0.2)]}
    res = A.arm_a(con, fbe)
    assert len(res.violations) == 0, "Arm A should pass a CA-explained move"
    con.close()


def test_arm_a_large_genuine_not_ca_shaped(tmp_path):
    """A large (+50%) non-CA-shaped move goes to large_genuine, not violations."""
    d1, d2 = date(2020, 1, 1), date(2020, 1, 2)
    rows = [
        (d1, "TEST", "EQ", 100.0, 100.0, 50.0, 100.0),
        (d2, "TEST", "EQ", 150.0, 150.0, 60.0, 100.0),    # +50%, survived=1.5 (not CA-shaped)
    ]
    intervals = [("TEST", d1, date(9999, 12, 31), "TEST")]
    con = _build_fixture(tmp_path, rows, [], intervals, [])
    res = A.arm_a(con, {})
    assert len(res.violations) == 0
    assert len(res.large_genuine) >= 1
    con.close()


# ──────────────────────────────────────────────────────────────────────────────
# Arm B — cross-symbol splice detection
# ──────────────────────────────────────────────────────────────────────────────
def test_arm_b_catches_splice(tmp_path):
    """A 1000% jump across a symbol handoff should be flagged."""
    d1, d2 = date(2025, 6, 18), date(2025, 6, 19)
    rows = [
        (d1, "OLDSYM", "EQ", 1.0, 1.0, 50.0, 100.0),
        (d2, "NEWSYM", "EQ", 100.0, 100.0, 60.0, 100.0),
    ]
    intervals = [
        ("OLDSYM", d1, date(9999, 12, 31), "ENTITY1"),
        ("NEWSYM", d2, date(9999, 12, 31), "ENTITY1"),
    ]
    con = _build_fixture(tmp_path, rows, [], intervals, [])
    res = A.arm_b(con)
    assert len(res.splices) == 1
    assert res.splices[0][1] == "OLDSYM"
    assert res.splices[0][2] == "NEWSYM"
    con.close()


def test_arm_b_passes_clean_handoff(tmp_path):
    """A <20% move across a handoff should NOT be flagged."""
    d1, d2 = date(2025, 6, 18), date(2025, 6, 19)
    rows = [
        (d1, "OLDSYM", "EQ", 100.0, 100.0, 50.0, 100.0),
        (d2, "NEWSYM", "EQ", 105.0, 105.0, 60.0, 100.0),    # +5%
    ]
    intervals = [
        ("OLDSYM", d1, date(9999, 12, 31), "ENTITY1"),
        ("NEWSYM", d2, date(9999, 12, 31), "ENTITY1"),
    ]
    con = _build_fixture(tmp_path, rows, [], intervals, [])
    res = A.arm_b(con)
    assert len(res.splices) == 0
    con.close()


# ──────────────────────────────────────────────────────────────────────────────
# Arm C — prev_close ratio identity
# ──────────────────────────────────────────────────────────────────────────────
def test_arm_c_passes_consistent_adjustment(tmp_path):
    """If adj ratio == raw ratio, Arm C passes."""
    d1, d2 = date(2020, 1, 1), date(2020, 1, 2)
    # raw: close=100, prev_close=100 (consecutive). adj: close=50, prev_close=50 (factor=0.5)
    rows_adj = [
        (d1, "TEST", "EQ", 50.0, 50.0, 50.0, 100.0),     # close=50 (adj), prev_close=100 (adj from raw 200)
        (d2, "TEST", "EQ", 50.0, 50.0, 60.0, 100.0),      # close=50 (adj), prev_close=50 (=adj_close d1)
    ]
    # raw: close=100 on both days, prev_close=100
    rows_raw = rows_adj  # same for simplicity (ratio identity holds)
    intervals = [("TEST", d1, date(9999, 12, 31), "TEST")]
    con = _build_fixture(tmp_path, rows_adj, rows_raw, intervals, [])
    res = A.arm_c(con, {})
    assert len(res.violations) == 0
    con.close()


def test_arm_c_catches_first_session_exdate(tmp_path):
    """A first-session ex-date with unadjusted prev_close is flagged."""
    d1 = date(2010, 1, 4)
    # LITL-like: raw prev_close=576.70, close=58.10, factor=0.1 (SPLIT)
    # Bug: adj prev_close=576.70 (unadjusted). Expected: 57.67
    rows_adj = [(d1, "TEST", "EQ", 58.10, 58.10, 50.0, 576.70)]   # close=58.10, prev_close=576.70
    intervals = [("TEST", d1, date(9999, 12, 31), "TEST")]
    factors = [("TEST", d1, 0.1, "SPLIT", "test")]
    con = _build_fixture(tmp_path, rows_adj, rows_adj, intervals, factors)
    fbe = {"TEST": [(d1, 0.1)]}
    res = A.arm_c(con, fbe)
    assert len(res.violations) >= 1
    assert res.violations[0][5] == "first_session_exdate"
    con.close()


# ──────────────────────────────────────────────────────────────────────────────
# Arm D — factor evidence
# ──────────────────────────────────────────────────────────────────────────────
def test_arm_d_catches_no_reprice(tmp_path):
    """A factor whose implied_open ~ 1.0 (never repriced) is flagged as no_reprice."""
    d1, d2 = date(2021, 8, 4), date(2021, 8, 5)
    # DVL-like: factor=0.6667 (BONUS) but open=301, prev_close=300.75 (never repriced)
    rows_adj = [
        (d1, "DVL", "EQ", 300.75, 300.75, 50.0, 300.75),
        (d2, "DVL", "EQ", 281.05, 301.00, 60.0, 300.75),     # open=301 (~1.0 of prev_close)
    ]
    intervals = [("DVL", d1, date(9999, 12, 31), "DVL")]
    factors = [("DVL", d2, 0.6667, "BONUS", "test")]
    con = _build_fixture(tmp_path, rows_adj, rows_adj, intervals, factors)
    res = A.arm_d(con)
    assert len(res.violations) >= 1
    assert "no_reprice" in res.violations[0][5]
    con.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
