"""Carry — analytics fact publisher (WS-B).

Promotes the frozen construction (build_carry.py + neutralize.py) into a
production-runtime fact table per (formation_date, underlying): z_carry_neut,
quintile, eligible. Runtime reads facts; strategy emits from facts.

Usage:
  Full rebuild: python scripts/signal_engine/carry/publish_facts.py
  Forward append: python scripts/signal_engine/carry/publish_facts.py --forward
Output: data/signal_engine/carry/facts.duckdb

Bridge: CARRY_IMPLEMENTATION_BRIDGE.md §2 — "Analytics Produce Facts, runtime
read-only. Promote the frozen research code, do not reimplement it."
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional, Set

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))

from scripts.signal_engine.carry import build_carry, neutralize

FACTS_DB = ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"

QUINTILE_FRAC = 0.20


def _load_existing_dates() -> Set:
    if not FACTS_DB.exists():
        return set()
    con = duckdb.connect(str(FACTS_DB), read_only=True)
    dates = {r[0] for r in con.execute(
        "SELECT DISTINCT formation_date FROM carry_facts"
    ).fetchall()}
    con.close()
    return dates


def _publish(sig_con, fac_db_path, forward: bool = False):
    sig_con.execute("SET threads=4")
    rows = sig_con.execute("""
        SELECT s.formation_date, s.underlying, s.sector, s.z_carry, s.z_carry_neut, s.liquid
        FROM signals s
        WHERE s.z_carry_neut IS NOT NULL
        ORDER BY s.formation_date, s.underlying
    """).fetchall()

    existing_dates = _load_existing_dates() if forward else set()

    by_date = defaultdict(list)
    for fdate, u, sec, z, zn, liq in rows:
        by_date[fdate].append(
            (u, sec, float(z) if z is not None else None, float(zn), bool(liq))
        )

    facts = []
    for fdate in sorted(by_date.keys()):
        if forward and fdate in existing_dates:
            continue

        day_rows = by_date[fdate]
        n = len(day_rows)
        if n < 5:
            continue

        liquid_rows = [r for r in day_rows if r[4]]
        n_liq = len(liquid_rows)
        if n_liq < 5:
            continue
        nq = max(1, round(QUINTILE_FRAC * n_liq))
        sorted_liq = sorted(liquid_rows, key=lambda r: r[3])
        u_to_q = {}
        for i, (u, sec, z, zn, liq) in enumerate(sorted_liq):
            if i < nq:
                u_to_q[u] = 1
            elif i >= n_liq - nq:
                u_to_q[u] = 5
            else:
                u_to_q[u] = 3
        for u, sec, z, zn, liq in day_rows:
            if not liq:
                u_to_q[u] = 3

        for u, sec, z, zn, liq in day_rows:
            facts.append(
                (fdate, u, sec or None, z, zn, u_to_q[u], bool(liq))
            )

    if not forward and FACTS_DB.exists():
        FACTS_DB.unlink()

    fc = duckdb.connect(str(fac_db_path))
    fc.execute("""
        CREATE TABLE IF NOT EXISTS carry_facts (
            formation_date   DATE    NOT NULL,
            underlying       VARCHAR NOT NULL,
            sector           VARCHAR,
            z_carry          DOUBLE,
            z_carry_neut     DOUBLE,
            quintile         TINYINT,
            eligible         BOOLEAN NOT NULL,
            raw_z            DOUBLE,
            basis_reverting  BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (formation_date, underlying)
        )
    """)
    fc.execute("""
        CREATE INDEX IF NOT EXISTS idx_facts_date ON carry_facts (formation_date)
    """)

    cols = {r[1] for r in fc.execute("PRAGMA table_info('carry_facts')").fetchall()}
    if "raw_z" not in cols:
        fc.execute("ALTER TABLE carry_facts ADD COLUMN raw_z DOUBLE")
    if "basis_reverting" not in cols:
        fc.execute("ALTER TABLE carry_facts ADD COLUMN basis_reverting BOOLEAN DEFAULT FALSE")

    if facts:
        fc.executemany(
            "INSERT OR REPLACE INTO carry_facts "
            "(formation_date, underlying, sector, z_carry, z_carry_neut, quintile, eligible) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(str(fd), u, sec, z, zn, q, elig) for fd, u, sec, z, zn, q, elig in facts],
        )

    total = fc.execute("SELECT COUNT(*) FROM carry_facts").fetchone()[0]
    n_form = fc.execute(
        "SELECT COUNT(DISTINCT formation_date) FROM carry_facts"
    ).fetchone()[0]
    max_date = fc.execute("SELECT MAX(formation_date) FROM carry_facts").fetchone()[0]
    fc.close()

    return total, n_form, max_date, len(facts)


def main():
    forward = "--forward" in sys.argv
    mode = "forward" if forward else "rebuild"

    if forward and "--incremental" not in sys.argv:
        sys.argv.append("--incremental")

    print(f"=== Step 1: build_carry (frozen construction) [{mode}] ===")
    rc = build_carry.main()
    if rc != 0:
        print("build_carry FAILED — stopping")
        return rc

    print(f"=== Step 2: neutralize (frozen neutralization) [{mode}] ===")
    rc = neutralize.main()
    if rc != 0:
        print("neutralize FAILED — stopping")
        return rc

    print(f"=== Step 3: publish facts (quintile + eligibility) [{mode}] ===")
    sig_con = duckdb.connect(str(SIG_DB))
    total, n_form, max_date, new_rows = _publish(sig_con, FACTS_DB, forward=forward)
    sig_con.close()

    print(f"Done: {total:,} facts across {n_form} formations "
          f"(max={max_date}, +{new_rows} new rows) -> {FACTS_DB}")
    return 0 if new_rows >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
