"""TS Basis Daily combo runner: facts-readiness gate, date selection, and a
store-backed cycle (resume, no double-processing)."""
import sys
import time
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.portfolio.combo_paper_store import ComboPaperStore
from scripts.ts_basis_daily_combo_forward import ComboRunner, facts_ready, pending_dates

D1, D2, D3 = date(2026, 9, 22), date(2026, 9, 23), date(2026, 9, 24)


def _facts(tmp_path, rows, reverting_any=True):
    """rows: (formation_date, underlying, z, quintile, reverting)."""
    db = tmp_path / "facts.duckdb"
    con = duckdb.connect(str(db))
    con.execute("""CREATE OR REPLACE TABLE carry_facts (formation_date DATE, underlying VARCHAR,
                   z_carry_neut DOUBLE, quintile INTEGER, eligible BOOLEAN,
                   raw_z DOUBLE, basis_reverting BOOLEAN DEFAULT FALSE)""")
    for fd, u, z, q, rev in rows:
        con.execute("INSERT INTO carry_facts VALUES (?,?,?,?,TRUE,?,?)",
                    [fd, u, z, q, z, rev and reverting_any])
    con.close()
    return db


class TestFactsReady:
    def test_missing(self, tmp_path):
        assert facts_ready(tmp_path / "none.duckdb")[0] is False

    def test_waits_while_file_is_still_changing(self, tmp_path):
        db = _facts(tmp_path, [(D1, "A", 2.0, 5, True)])
        ready, reason = facts_ready(db, settle_s=60)
        assert not ready and "settle" in reason

    def test_waits_until_recovery_flag_applied(self, tmp_path):
        db = _facts(tmp_path, [(D1, "A", 2.0, 5, True)], reverting_any=False)
        ready, reason = facts_ready(db, settle_s=0, now=time.time() + 1)
        assert not ready and "recovery" in reason

    def test_ready(self, tmp_path):
        db = _facts(tmp_path, [(D1, "A", 2.0, 5, True)])
        assert facts_ready(db, settle_s=0, now=time.time() + 1) == (True, "ready")


class TestPendingDates:
    def test_first_start_takes_latest_only(self, tmp_path):
        db = _facts(tmp_path, [(D1, "A", 2.0, 5, True), (D2, "A", 2.0, 5, False)])
        assert pending_dates(db, None) == [D2]

    def test_resume_takes_everything_after(self, tmp_path):
        db = _facts(tmp_path, [(d, "A", 2.0, 5, d == D1) for d in (D1, D2, D3)])
        assert pending_dates(db, D1) == [D2, D3]


def test_cycle_catches_up_then_idles(tmp_path):
    legs = [("A", 2.0, 5, False), ("B", -2.0, 1, False), ("R", 2.5, 5, True)]
    facts = _facts(tmp_path, [(d, u, z, q, rev) for d in (D1, D2) for u, z, q, rev in legs])
    fut = tmp_path / "fut.duckdb"
    con = duckdb.connect(str(fut))
    con.execute("""CREATE TABLE futures_bhavcopy (underlying VARCHAR, expiry_dt DATE,
                   trade_date DATE, inst_type VARCHAR, close DOUBLE)""")
    con.close()
    sig = tmp_path / "sig.duckdb"
    con = duckdb.connect(str(sig))
    con.execute("CREATE TABLE signals (formation_date DATE, underlying VARCHAR, fwd_ret_1m DOUBLE)")
    con.close()

    store = ComboPaperStore(tmp_path / "combo.duckdb")
    store.record(date(2026, 9, 21), longs={}, shorts={}, trades=[],
                 costs={"traded_value": 0.0, "fees": 0.0, "slippage": 0.0}, pnl={})
    runner = ComboRunner(store, facts_db=facts, fut_db=fut, sig_db=sig,
                         bhavcopy_db=None, settle_s=0)

    assert runner.cycle() == 2
    st = store.last_state()
    assert st["formation_date"] == D2
    assert set(st["longs"]) == {"A"} and set(st["shorts"]) == {"B"}   # R reverting
    assert runner.cycle() == 0 and runner.last_reason == "up to date"
