"""Carry — analytics fact publisher (WS-B).

Promotes the frozen construction (build_carry.py + neutralize.py) into a
production-runtime fact table per (formation_date, underlying): z_carry_neut,
quintile, eligible. Runtime reads facts; strategy emits from facts.

Usage: python scripts/signal_engine/carry/publish_facts.py
Output: data/signal_engine/carry/facts.duckdb

Bridge: CARRY_IMPLEMENTATION_BRIDGE.md §2 — "Analytics Produce Facts, runtime
read-only. Promote the frozen research code, do not reimplement it."
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))

from scripts.signal_engine.carry import build_carry, neutralize

FACTS_DB = ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"

QUINTILE_FRAC = 0.20


def _publish(sig_con, fac_db_path):
    """Read signals → compute quintile + eligible → write facts DB."""
    sig_con.execute("SET threads=4")
    rows = sig_con.execute("""
        SELECT s.formation_date, s.underlying, s.sector, s.z_carry, s.z_carry_neut, s.liquid
        FROM signals s
        WHERE s.z_carry_neut IS NOT NULL
        ORDER BY s.formation_date, s.underlying
    """).fetchall()

    by_date = defaultdict(list)
    for fdate, u, sec, z, zn, liq in rows:
        by_date[fdate].append(
            (u, sec, float(z) if z is not None else None, float(zn), bool(liq))
        )

    facts = []
    for fdate in sorted(by_date.keys()):
        day_rows = by_date[fdate]
        n = len(day_rows)
        if n < 5:
            continue

        # Compute nq over liquid names only (matches research harness: filter
        # by liquid=TRUE before quintile assignment, not after)
        liquid_rows = [r for r in day_rows if r[4]]
        n_liq = len(liquid_rows)
        if n_liq < 5:
            continue
        nq = max(1, round(QUINTILE_FRAC * n_liq))
        sorted_liq = sorted(liquid_rows, key=lambda r: r[3])
        # research-identical quintile: bottom nq = Q1 (SHORT), top nq = Q5 (LONG)
        u_to_q = {}
        for i, (u, sec, z, zn, liq) in enumerate(sorted_liq):
            if i < nq:
                u_to_q[u] = 1      # bottom → SHORT
            elif i >= n_liq - nq:
                u_to_q[u] = 5      # top → LONG
            else:
                u_to_q[u] = 3      # middle
        # Illiquid names get quintile=3 (not in portfolio)
        for u, sec, z, zn, liq in day_rows:
            if not liq:
                u_to_q[u] = 3

        for u, sec, z, zn, liq in day_rows:
            facts.append(
                (fdate, u, sec or None, z, zn, u_to_q[u], bool(liq))
            )

    if Path(fac_db_path).exists():
        Path(fac_db_path).unlink()

    fc = duckdb.connect(str(fac_db_path))
    fc.execute("""
        CREATE TABLE carry_facts (
            formation_date   DATE    NOT NULL,
            underlying       VARCHAR NOT NULL,
            sector           VARCHAR,
            z_carry          DOUBLE,
            z_carry_neut     DOUBLE,
            quintile         TINYINT, -- 1=lowest carry → SHORT, 5=highest carry → LONG
            eligible         BOOLEAN NOT NULL,
            PRIMARY KEY (formation_date, underlying)
        )
    """)
    fc.execute("""
        CREATE INDEX idx_facts_date ON carry_facts (formation_date)
    """)

    fc.executemany(
        "INSERT INTO carry_facts VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(str(fd), u, sec, z, zn, q, elig) for fd, u, sec, z, zn, q, elig in facts],
    )

    total = fc.execute("SELECT COUNT(*) FROM carry_facts").fetchone()[0]
    n_form = fc.execute(
        "SELECT COUNT(DISTINCT formation_date) FROM carry_facts"
    ).fetchone()[0]
    fc.close()

    return total, n_form


def main():
    print("=== Step 1: build_carry (frozen construction) ===")
    rc = build_carry.main()
    if rc != 0:
        print("build_carry FAILED — stopping")
        return rc

    print("=== Step 2: neutralize (frozen neutralization) ===")
    rc = neutralize.main()
    if rc != 0:
        print("neutralize FAILED — stopping")
        return rc

    print("=== Step 3: publish facts (quintile + eligibility) ===")
    sig_con = duckdb.connect(str(SIG_DB))
    total, n_form = _publish(sig_con, FACTS_DB)
    sig_con.close()

    print(f"Done: {total:,} facts across {n_form} formations → {FACTS_DB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
