"""TS Basis facts publisher appends into the 7-column carry_facts layout.

The live ts_facts table carries raw_z and basis_reverting (the carry_facts layout
CarryRebalancerHook reads), while the publisher inserted 5 values positionally — so
every append since 2026-08-07 failed and the facts stayed at 07-24 (2026-09-30).
"""
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.signal_engine.ts_basis import publish_facts as P  # noqa: E402

D = date
CARRY_FACTS_7 = """
    CREATE TABLE carry_facts (
        formation_date DATE NOT NULL, underlying VARCHAR NOT NULL, z_carry_neut DOUBLE,
        quintile TINYINT, eligible BOOLEAN NOT NULL, raw_z DOUBLE,
        basis_reverting BOOLEAN DEFAULT FALSE, PRIMARY KEY (formation_date, underlying))
"""


def _signals(path, dates):
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE signals (formation_date DATE, underlying VARCHAR, raw_ann_basis DOUBLE, "
                "z_ts DOUBLE, fwd_ret_1m DOUBLE, liquid BOOLEAN)")
    for d in dates:
        for i in range(6):
            con.execute("INSERT INTO signals VALUES (?, ?, 0, ?, 0, TRUE)", [d, f"U{i}", float(i)])
    con.close()


def test_appends_new_formations_into_the_seven_column_layout(tmp_path, monkeypatch):
    sig, facts = tmp_path / "ts_signals.duckdb", tmp_path / "ts_facts.duckdb"
    _signals(sig, [D(2026, 7, 24), D(2026, 7, 31)])
    con = duckdb.connect(str(facts))
    con.execute(CARRY_FACTS_7)
    con.execute("INSERT INTO carry_facts (formation_date, underlying, z_carry_neut, quintile, eligible) "
                "SELECT DATE '2026-07-24', 'U' || i, i, 3, TRUE FROM range(6) t(i)")
    con.close()
    monkeypatch.setattr(P, "TS_SIG_DB", sig)
    monkeypatch.setattr(P, "TS_FACTS_DB", facts)

    assert P.main() == 0

    con = duckdb.connect(str(facts), read_only=True)
    rows = con.execute("SELECT underlying, quintile, basis_reverting FROM carry_facts "
                       "WHERE formation_date = DATE '2026-07-31' ORDER BY underlying").fetchall()
    con.close()
    assert [r[1] for r in rows] == [1, 3, 3, 3, 3, 5]
    assert all(r[2] is False for r in rows)


def test_fresh_store_is_created_in_the_carry_facts_layout(tmp_path, monkeypatch):
    sig, facts = tmp_path / "ts_signals.duckdb", tmp_path / "ts_facts.duckdb"
    _signals(sig, [D(2026, 7, 24)])
    monkeypatch.setattr(P, "TS_SIG_DB", sig)
    monkeypatch.setattr(P, "TS_FACTS_DB", facts)

    assert P.main() == 0

    con = duckdb.connect(str(facts), read_only=True)
    cols = [r[1] for r in con.execute("PRAGMA table_info('carry_facts')").fetchall()]
    con.close()
    assert cols == ["formation_date", "underlying", "z_carry_neut", "quintile", "eligible",
                    "raw_z", "basis_reverting"]
