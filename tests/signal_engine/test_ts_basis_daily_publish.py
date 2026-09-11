"""TS Basis Daily facts publisher — the single implementation.

Regressions from TS_BASIS_DAILY_SIGNAL_AUDIT_2026-09-11: quintiles ordered only by the
clamped z_ts, so names tied at ±3 landed in the book arbitrarily (F3); the pipeline's
publisher ranked illiquid names alongside liquid ones, unlike the research construct;
and two publishers with different rules existed (F8).
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "ts_basis_daily"))

import publish_facts as P  # noqa: E402
import ts_basis_daily_options as O  # noqa: E402

D1 = date(2026, 9, 1)
D2 = date(2026, 9, 2)


def _signals(path, rows):
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE signals (formation_date DATE, underlying VARCHAR, raw_ann_basis DOUBLE, "
                "raw_z DOUBLE, z_ts DOUBLE, fwd_ret_1m DOUBLE, liquid BOOLEAN)")
    con.executemany("INSERT INTO signals VALUES (?, ?, 0.05, ?, ?, NULL, ?)",
                    [(d, u, rz, max(-3.0, min(3.0, rz)), liq) for d, u, rz, liq in rows])
    con.close()


def _facts(path, d):
    con = duckdb.connect(str(path), read_only=True)
    out = {u: (q, e, rz) for u, q, e, rz in con.execute(
        "SELECT underlying, quintile, eligible, raw_z FROM carry_facts WHERE formation_date = ?", [d]
    ).fetchall()}
    con.close()
    return out


def test_quintiles_rank_liquid_names_only(tmp_path):
    rows = [(D1, f"L{i:02d}", -2.0 + 0.3 * i, True) for i in range(10)]
    rows += [(D1, f"X{i}", -2.9 + 0.01 * i, False) for i in range(5)]      # illiquid, lowest z
    _signals(tmp_path / "sig.duckdb", rows)
    P.publish(tmp_path / "sig.duckdb", tmp_path / "facts.duckdb")
    f = _facts(tmp_path / "facts.duckdb", D1)
    assert sorted(u for u, v in f.items() if v[0] == 1) == ["L00", "L01"]   # nq = round(0.2 * 10)
    assert sorted(u for u, v in f.items() if v[0] == 5) == ["L08", "L09"]
    assert all(f[f"X{i}"][0] == 3 and f[f"X{i}"][1] is False for i in range(5))


def test_clamp_ties_break_on_unclamped_z(tmp_path):
    rows = [(D1, f"T{i}", 3.1 + 0.1 * i, True) for i in range(6)]            # all z_ts = 3.0
    rows += [(D1, f"B{i}", -3.5 - 0.1 * i, True) for i in range(4)]          # all z_ts = -3.0
    _signals(tmp_path / "sig.duckdb", rows)
    P.publish(tmp_path / "sig.duckdb", tmp_path / "facts.duckdb")
    f = _facts(tmp_path / "facts.duckdb", D1)
    assert sorted(u for u, v in f.items() if v[0] == 5) == ["T4", "T5"]
    assert sorted(u for u, v in f.items() if v[0] == 1) == ["B2", "B3"]
    assert f["T5"][2] == 3.6


def test_republish_rebuilds_rather_than_appends(tmp_path):
    rows = [(D1, f"N{i}", 0.2 * i, True) for i in range(10)]
    _signals(tmp_path / "sig.duckdb", rows)
    P.publish(tmp_path / "sig.duckdb", tmp_path / "facts.duckdb")
    con = duckdb.connect(str(tmp_path / "sig.duckdb"))
    con.execute("UPDATE signals SET raw_z = -raw_z, z_ts = -z_ts")
    con.executemany("INSERT INTO signals VALUES (?, ?, 0.05, ?, ?, NULL, TRUE)",
                    [(D2, f"N{i}", 0.2 * i, 0.2 * i) for i in range(10)])
    con.close()
    P.publish(tmp_path / "sig.duckdb", tmp_path / "facts.duckdb")
    assert _facts(tmp_path / "facts.duckdb", D1)["N9"][0] == 1               # corrected, not frozen
    assert _facts(tmp_path / "facts.duckdb", D2)["N9"][0] == 5


def test_fewer_than_five_liquid_names_publish_as_neutral(tmp_path):
    _signals(tmp_path / "sig.duckdb", [(D1, f"N{i}", 0.5 * i, i < 4) for i in range(8)])
    P.publish(tmp_path / "sig.duckdb", tmp_path / "facts.duckdb")
    assert {v[0] for v in _facts(tmp_path / "facts.duckdb", D1).values()} == {3}


def test_book_order_breaks_clamp_ties_on_unclamped_z(tmp_path, monkeypatch):
    rows = [(D1, f"T{i}", 3.1 + 0.1 * i, True) for i in range(15)]
    rows += [(D1, f"B{i}", -3.1 - 0.1 * i, True) for i in range(15)]
    _signals(tmp_path / "sig.duckdb", rows)
    P.publish(tmp_path / "sig.duckdb", tmp_path / "facts.duckdb")
    monkeypatch.setattr(O, "FACTS_DB", tmp_path / "facts.duckdb")
    _, book = O.get_book(D1, 5)
    assert [u for u, d in book if d == "LONG"] == ["T14", "T13", "T12", "T11", "T10"]
    assert [u for u, d in book if d == "SHORT"] == ["B14", "B13", "B12", "B11", "B10"]
