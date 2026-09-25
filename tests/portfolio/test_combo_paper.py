"""TS Basis Daily combo forward-paper tests: B1 calendar reload, resume,
flat-on-empty, and the persisted P&L store (B2)."""
import sys
from datetime import date, datetime
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.portfolio.carry_rebalancer import CarryRebalancerHook
from core.execution.portfolio.combo_paper_store import (
    ComboPaperStore, book_returns,
)

D1, D2, D3 = date(2026, 9, 23), date(2026, 9, 24), date(2026, 9, 25)


def _facts_db(tmp_path, rows):
    """rows: (formation_date, underlying, z, quintile, reverting)."""
    db = tmp_path / "facts.duckdb"
    con = duckdb.connect(str(db))
    con.execute("""CREATE TABLE carry_facts (formation_date DATE, underlying VARCHAR,
                   z_carry_neut DOUBLE, quintile INTEGER, eligible BOOLEAN,
                   raw_z DOUBLE, basis_reverting BOOLEAN)""")
    for fd, u, z, q, rev in rows:
        con.execute("INSERT INTO carry_facts VALUES (?,?,?,?,TRUE,?,?)",
                    [fd, u, z, q, z, rev])
    con.close()
    return db


class _Metrics:
    cash_balance = 10_000_000.0
    max_equity = 10_000_000.0
    max_drawdown_pct = 0.0


class _Tracker:
    def get_all_positions(self):
        return {}

    def update_from_fill(self, fill):
        pass


class _Exec:
    metrics = _Metrics()
    pnl_tracker = None
    position_tracker = _Tracker()


def _combo_hook(db, sink=None):
    return CarryRebalancerHook(
        facts_db_path=str(db), execution_handler=_Exec(),
        metrics_sink=sink, min_abs_z=0.7, exclude_reverting=True,
        legs_by_quintile=True)


class TestCalendarReload:
    def test_date_published_after_construction_fires_after_reload(self, tmp_path):
        db = _facts_db(tmp_path, [(D1, "A", 2.0, 5, False)])
        hook = _combo_hook(db)
        con = duckdb.connect(str(db))
        con.execute("INSERT INTO carry_facts VALUES (?, 'A', 2.0, 5, TRUE, 2.0, FALSE)", [D2])
        con.close()
        assert hook(datetime.combine(D2, datetime.min.time()), None) is False
        hook.reload_calendar()
        assert hook(datetime.combine(D2, datetime.min.time()), None) is True


class TestResume:
    def test_restore_seeds_book_and_skips_processed_dates(self, tmp_path):
        db = _facts_db(tmp_path, [(D1, "A", 2.0, 5, False),
                                  (D2, "A", 2.0, 5, False)])
        hook = _combo_hook(db)
        hook.restore({"A": 5_000_000.0}, {}, D2)
        assert hook(datetime.combine(D1, datetime.min.time()), None) is False
        assert hook(datetime.combine(D2, datetime.min.time()), None) is False
        assert hook._book_longs == {"A": 5_000_000.0}


class TestFlatOnEmpty:
    def test_both_legs_filtered_out_closes_held_book(self, tmp_path):
        # Every leg fails a filter: A weak (|z|<=0.7), B reverting.
        db = _facts_db(tmp_path, [(D2, "A", 0.5, 5, False),
                                  (D2, "B", -2.0, 1, True)])
        seen = {}
        hook = _combo_hook(db, sink=lambda fd, deltas, held, m, cs:
                           seen.update(held=held, deltas=deltas))
        hook.restore({"A": 5_000_000.0}, {"B": 5_000_000.0}, D1)
        assert hook(datetime.combine(D2, datetime.min.time()), None) is True
        assert hook._book_longs == {} and hook._book_shorts == {}
        assert {d.action for d in seen["deltas"]} == {"CLOSE"}
        assert seen["held"].longs == {} and seen["held"].shorts == {}


def _fut_db(tmp_path, rows):
    """rows: (trade_date, underlying, expiry_dt, close)."""
    db = tmp_path / "fut.duckdb"
    con = duckdb.connect(str(db))
    con.execute("""CREATE TABLE futures_bhavcopy (underlying VARCHAR, expiry_dt DATE,
                   trade_date DATE, inst_type VARCHAR, close DOUBLE)""")
    for td, u, exp, c in rows:
        con.execute("INSERT INTO futures_bhavcopy VALUES (?,?,?,'FUTSTK',?)",
                    [u, exp, td, c])
    con.close()
    return db


def _sig_db(tmp_path, rows):
    """rows: (formation_date, underlying, fwd_ret_1m)."""
    db = tmp_path / "sig.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE signals (formation_date DATE, underlying VARCHAR, fwd_ret_1m DOUBLE)")
    for fd, u, r in rows:
        con.execute("INSERT INTO signals VALUES (?,?,?)", [fd, u, r])
    con.close()
    return db


class TestBookReturns:
    E1, E2 = date(2026, 9, 29), date(2026, 10, 27)

    def test_futures_and_spot_leg_returns(self, tmp_path):
        fut = _fut_db(tmp_path, [
            (D1, "A", self.E1, 100.0), (D2, "A", self.E1, 102.0),
            (D1, "B", self.E1, 50.0), (D2, "B", self.E1, 49.0),
        ])
        sig = _sig_db(tmp_path, [(D1, "A", 0.01), (D1, "B", -0.03)])
        r = book_returns(D1, D2, {"A": 5e6}, {"B": 5e6}, fut, sig)
        assert r["fut_long_ret"] == pytest.approx(0.02)
        assert r["fut_short_ret"] == pytest.approx(-0.02)
        assert r["fut_pnl"] == pytest.approx(5e6 * 0.02 + 5e6 * 0.02)
        assert r["spot_pnl"] == pytest.approx(5e6 * 0.01 + 5e6 * 0.03)
        assert r["n_unpriced_fut"] == 0 and r["n_unpriced_spot"] == 0

    def test_marks_on_expiry_day_use_next_contract_at_both_ends(self, tmp_path):
        fut = _fut_db(tmp_path, [
            (D1, "A", D2, 100.0), (D2, "A", D2, 110.0),        # expiring: ignored
            (D1, "A", self.E2, 101.0), (D2, "A", self.E2, 102.01),
        ])
        r = book_returns(D1, D2, {"A": 1e6}, {}, fut, _sig_db(tmp_path, []))
        assert r["fut_long_ret"] == pytest.approx(0.01)

    def test_unpriced_names_are_counted_and_contribute_zero(self, tmp_path):
        fut = _fut_db(tmp_path, [(D1, "A", self.E1, 100.0), (D2, "A", self.E1, 101.0)])
        r = book_returns(D1, D2, {"A": 1e6, "GONE": 1e6}, {}, fut, _sig_db(tmp_path, []))
        assert r["n_unpriced_fut"] == 1
        assert r["n_unpriced_spot"] == 2
        assert r["fut_pnl"] == pytest.approx(1e6 * 0.01)


class TestComboPaperStore:
    def _record(self, store, fd, longs, net):
        store.record(fd, longs=longs, shorts={}, trades=[],
                     costs={"traded_value": 0.0, "fees": 0.0, "slippage": 0.0},
                     pnl={"prev_date": None, "fut_pnl": net, "net_pnl_fut": net})

    def test_empty_store_has_no_state(self, tmp_path):
        assert ComboPaperStore(tmp_path / "p.duckdb").last_state() is None

    def test_round_trip_and_cumulative(self, tmp_path):
        store = ComboPaperStore(tmp_path / "p.duckdb")
        self._record(store, D1, {"A": 5e6}, 0.0)
        self._record(store, D2, {"A": 5e6, "B": 1e6}, 100_000.0)
        st = store.last_state()
        assert st["formation_date"] == D2
        assert st["longs"] == {"A": 5e6, "B": 1e6}
        assert st["cum_net_pnl_fut"] == pytest.approx(100_000.0)

    def test_rerecording_a_date_replaces_it(self, tmp_path):
        store = ComboPaperStore(tmp_path / "p.duckdb")
        self._record(store, D1, {"A": 5e6}, 0.0)
        self._record(store, D2, {"A": 5e6}, 50_000.0)
        self._record(store, D2, {"B": 5e6}, -20_000.0)
        con = duckdb.connect(str(tmp_path / "p.duckdb"), read_only=True)
        n = con.execute("SELECT COUNT(*) FROM combo_daily WHERE formation_date=?", [D2]).fetchone()[0]
        con.close()
        st = store.last_state()
        assert n == 1
        assert st["longs"] == {"B": 5e6}
        assert st["cum_net_pnl_fut"] == pytest.approx(-20_000.0)

    def test_drawdown_from_peak(self, tmp_path):
        store = ComboPaperStore(tmp_path / "p.duckdb")
        self._record(store, D1, {}, 1_000_000.0)
        self._record(store, D2, {}, -2_000_000.0)
        con = duckdb.connect(str(tmp_path / "p.duckdb"), read_only=True)
        dd = con.execute("SELECT drawdown_pct FROM combo_daily WHERE formation_date=?", [D2]).fetchone()[0]
        con.close()
        assert dd == pytest.approx((9_000_000 / 11_000_000 - 1) * 100)
