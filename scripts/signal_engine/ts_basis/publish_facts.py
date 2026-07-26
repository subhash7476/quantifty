"""TS Basis — facts publisher (shadow sleeve, Piece 3).

Reads ts_signals.duckdb (z_ts) → computes quintile + eligible →
writes ts_facts.duckdb with the same schema as carry_facts so
CarryRebalancerHook can be reused unchanged.

Shadow/observational only — not a co-equal capital allocation.
TS Basis remains de-authorized; forward paper is the only path
that can ever re-qualify it.

Usage: python scripts/signal_engine/ts_basis/publish_facts.py
Output: data/signal_engine/ts_basis/ts_facts.duckdb
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

TS_SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis" / "ts_signals.duckdb"
TS_FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis" / "ts_facts.duckdb"

QUINTILE_FRAC = 0.20


def main():
    if not TS_SIG_DB.exists():
        print(f"TS Basis signals not found: {TS_SIG_DB}")
        print("Run scripts/signal_engine/ts_basis/build_ts_signals.py first.")
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
    if TS_FACTS_DB.exists():
        TS_FACTS_DB.unlink()

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
    n_form = fc.execute(
        "SELECT COUNT(DISTINCT formation_date) FROM carry_facts"
    ).fetchone()[0]
    fc.close()

    print(f"TS Basis facts: {total:,} rows across {n_form} formations -> {TS_FACTS_DB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
