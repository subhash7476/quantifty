"""TS Basis Daily — facts publisher.

Reads ts_signals.duckdb (z_ts) → computes quintile + eligible →
writes ts_facts.duckdb with the same schema as carry_facts so
CarryRebalancerHook can be reused unchanged.

Usage: python scripts/signal_engine/ts_basis_daily/publish_facts.py
Output: data/signal_engine/ts_basis_daily/ts_facts.duckdb
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

TS_SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
TS_FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"

QUINTILE_FRAC = 0.20


def main():
    if not TS_SIG_DB.exists():
        print(f"TS Basis Daily signals not found: {TS_SIG_DB}")
        print("Run scripts/signal_engine/ts_basis_daily/build_ts_basis_daily.py first.")
        return 1

    con = duckdb.connect(str(TS_SIG_DB), read_only=True)
    rows = con.execute("""
        SELECT formation_date, underlying, z_ts, liquid, fwd_ret_1m
        FROM signals WHERE z_ts IS NOT NULL
        ORDER BY formation_date, underlying
    """).fetchall()
    con.close()

    by_date = defaultdict(list)
    for fdate, u, z_ts, liq, fr in rows:
        by_date[fdate].append((u, float(z_ts), bool(liq)))

    facts = []
    for fdate in sorted(by_date.keys()):
        day_rows = by_date[fdate]
        liquid_rows = [r for r in day_rows if r[2]]
        n_liq = len(liquid_rows)
        if n_liq < 5:
            continue
        nq = max(1, round(QUINTILE_FRAC * n_liq))
        sorted_liq = sorted(liquid_rows, key=lambda r: r[1])
        u_to_q = {}
        for i, (u, z, liq) in enumerate(sorted_liq):
            if i < nq:
                u_to_q[u] = 1
            elif i >= n_liq - nq:
                u_to_q[u] = 5
            else:
                u_to_q[u] = 3
        for u, z, liq in day_rows:
            if not liq:
                u_to_q[u] = 3

        for u, z, liq in day_rows:
            facts.append((fdate, u, z, u_to_q[u], bool(liq)))

    TS_FACTS_DB.parent.mkdir(parents=True, exist_ok=True)
    existing_dates = set()
    if TS_FACTS_DB.exists():
        ec = duckdb.connect(str(TS_FACTS_DB), read_only=True)
        existing_dates = {r[0] for r in ec.execute(
            "SELECT DISTINCT formation_date FROM carry_facts"
        ).fetchall()}
        ec.close()

    if existing_dates:
        fact_rows = [r for r in facts if r[0] not in existing_dates]
        if not fact_rows:
            print("TS Basis Daily facts: up to date (0 new formations)")
            return 0
        fc = duckdb.connect(str(TS_FACTS_DB))
        fc.executemany(
            "INSERT INTO carry_facts VALUES (?, ?, ?, ?, ?)",
            [(str(fd), u, z, q, elig) for fd, u, z, q, elig in fact_rows],
        )
    else:
        fc = duckdb.connect(str(TS_FACTS_DB))
        fc.execute("""
            CREATE TABLE carry_facts (
                formation_date   DATE    NOT NULL,
                underlying       VARCHAR NOT NULL,
                z_carry_neut     DOUBLE,
                quintile         TINYINT,
                eligible         BOOLEAN NOT NULL,
                PRIMARY KEY (formation_date, underlying)
            )
        """)
        fc.execute("CREATE INDEX idx_facts_date ON carry_facts (formation_date)")
        fc.executemany(
            "INSERT INTO carry_facts VALUES (?, ?, ?, ?, ?)",
            [(str(fd), u, z, q, elig) for fd, u, z, q, elig in facts],
        )

    total = fc.execute("SELECT COUNT(*) FROM carry_facts").fetchone()[0]
    n_form = fc.execute("SELECT COUNT(DISTINCT formation_date) FROM carry_facts").fetchone()[0]
    fc.close()

    new_formations = len({r[0] for r in facts}) - len(existing_dates)
    print(f"TS Basis Daily facts: {total:,} rows across {n_form} formations "
          f"(+{max(0, new_formations)} new formations) -> {TS_FACTS_DB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
