"""build_carry.py incremental maintenance: off-grid pruning, forward pointers, forward returns.

Each nightly --incremental run used to insert that day as the week's formation and never
remove it, and forward returns were computed only for the formations added in that run —
whose next formation does not exist yet — so none was ever filled (2026-09-30).
"""
import sys
from datetime import date
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))
sys.path.insert(0, str(ROOT))

import build_carry as B  # noqa: E402

D = date


@pytest.fixture
def sig(tmp_path):
    eq = duckdb.connect(str(tmp_path / "eq.duckdb"))
    eq.execute("CREATE TABLE equity_bhavcopy_adjusted "
               "(symbol VARCHAR, trade_date DATE, series VARCHAR, close DOUBLE)")
    closes = {D(2026, 7, 17): 100.0, D(2026, 7, 23): 104.0, D(2026, 7, 24): 110.0,
              D(2026, 7, 31): 121.0, D(2026, 8, 7): 133.1, D(2026, 8, 10): 140.0}
    eq.executemany("INSERT INTO equity_bhavcopy_adjusted VALUES ('AAA', ?, 'EQ', ?)",
                   list(closes.items()))
    eq.close()

    con = duckdb.connect(str(tmp_path / "sig.duckdb"))
    con.execute("CREATE TABLE formations (formation_date DATE PRIMARY KEY, fwd_formation_date DATE, "
                "n_liquid INT, n_scored INT, mean_basis DOUBLE, sd_basis DOUBLE)")
    con.execute("CREATE TABLE signals (formation_date DATE, underlying VARCHAR, entity VARCHAR, "
                "sector VARCHAR, raw_ann_basis DOUBLE, div_adj_basis DOUBLE, resid_carry DOUBLE, "
                "z_carry DOUBLE, z_carry_neut DOUBLE, beta DOUBLE, fwd_ret_1m DOUBLE, liquid BOOLEAN, "
                "PRIMARY KEY (formation_date, underlying))")
    # The live state: 07-17 points at the phantom Thursday 07-23 with a return measured
    # to it; 07-23 and 07-28 are phantoms; nothing after 07-24 has a forward return.
    stored = [(D(2026, 7, 17), D(2026, 7, 23), 0.04), (D(2026, 7, 23), None, None),
              (D(2026, 7, 24), D(2026, 7, 28), None), (D(2026, 7, 28), None, None),
              (D(2026, 7, 31), None, None), (D(2026, 8, 7), None, None)]
    for fd, nxt, ret in stored:
        con.execute("INSERT INTO formations VALUES (?, ?, 1, 1, 0, 0)", [fd, nxt])
        con.execute("INSERT INTO signals (formation_date, underlying, fwd_ret_1m, liquid) "
                    "VALUES (?, 'AAA', ?, TRUE)", [fd, ret])
    con.execute(f"ATTACH '{tmp_path / 'eq.duckdb'}' AS eq (READ_ONLY)")
    yield con
    con.close()


def _formations(con):
    return con.execute("SELECT formation_date, fwd_formation_date FROM formations ORDER BY 1").fetchall()


def _fwd(con):
    return dict(con.execute("SELECT formation_date, fwd_ret_1m FROM signals ORDER BY 1").fetchall())


GRID = [D(2026, 7, 17), D(2026, 7, 24), D(2026, 7, 31), D(2026, 8, 7)]


def test_prune_removes_formations_that_fell_off_the_weekly_grid(sig):
    assert B._prune_offgrid(sig, GRID) == [D(2026, 7, 23), D(2026, 7, 28)]
    assert [f for f, _ in _formations(sig)] == GRID
    assert sorted(_fwd(sig)) == GRID


def test_repoint_links_each_formation_to_the_next_stored_one(sig):
    B._prune_offgrid(sig, GRID)
    B._repoint_forward(sig)
    assert _formations(sig) == [(D(2026, 7, 17), D(2026, 7, 24)), (D(2026, 7, 24), D(2026, 7, 31)),
                                (D(2026, 7, 31), D(2026, 8, 7)), (D(2026, 8, 7), None)]
    # 07-17's return was measured to the phantom 07-23; a moved pointer invalidates it.
    assert _fwd(sig)[D(2026, 7, 17)] is None


def test_fill_computes_every_pending_forward_return(sig):
    B._prune_offgrid(sig, GRID)
    B._repoint_forward(sig)
    assert B._fill_forward_returns(sig) == 3
    fwd = _fwd(sig)
    assert fwd[D(2026, 7, 17)] == pytest.approx(0.10)     # 100 -> 110, not 100 -> 104
    assert fwd[D(2026, 7, 24)] == pytest.approx(0.10)
    assert fwd[D(2026, 7, 31)] == pytest.approx(0.10)
    assert fwd[D(2026, 8, 7)] is None                     # no next formation yet


def test_repoint_leaves_correct_pointers_and_returns_alone(sig):
    B._prune_offgrid(sig, GRID)
    B._repoint_forward(sig)
    B._fill_forward_returns(sig)
    sig.execute("UPDATE signals SET fwd_ret_1m = 0.5 WHERE formation_date = DATE '2026-07-24'")
    assert B._repoint_forward(sig) == 0
    assert _fwd(sig)[D(2026, 7, 24)] == 0.5


def test_final_only_leaves_the_link_to_an_incomplete_week_open(sig):
    # Monday night: 08-10 is this week's formation so far. 08-07 -> 08-10 is a one-day
    # return that ts_basis, which never rewrites rows, would keep for good.
    sig.execute("INSERT INTO formations VALUES (DATE '2026-08-10', NULL, 1, 1, 0, 0)")
    sig.execute("INSERT INTO signals (formation_date, underlying, liquid) VALUES (DATE '2026-08-10', 'AAA', TRUE)")
    B._prune_offgrid(sig, GRID + [D(2026, 8, 10)])
    B._repoint_forward(sig)
    B._fill_forward_returns(sig, final_only=True)
    fwd = _fwd(sig)
    assert fwd[D(2026, 7, 31)] == pytest.approx(0.10)
    assert fwd[D(2026, 8, 7)] is None
