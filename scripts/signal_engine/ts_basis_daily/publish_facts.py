"""TS Basis Daily — facts publisher (the only one).

Reads ts_signals.duckdb → quintiles among liquid names → rebuilds ts_facts.duckdb
with the carry_facts schema so CarryRebalancerHook can be reused unchanged.

Ordering is (z_ts, raw_z, underlying): z_ts is clamped at ±3, so the unclamped
z decides between names tied at the clamp.

Usage: python scripts/signal_engine/ts_basis_daily/publish_facts.py
Output: data/signal_engine/ts_basis_daily/ts_facts.duckdb
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]

TS_SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
TS_FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"

QUINTILE_FRAC = 0.20
MIN_LIQUID = 5


def publish(sig_db: Path, facts_db: Path) -> tuple[int, int]:
    built = facts_db.with_name(facts_db.stem + ".rebuild.duckdb")
    built.unlink(missing_ok=True)
    fc = duckdb.connect(str(built))
    fc.execute("SET threads=4")
    fc.execute(f"ATTACH '{sig_db}' AS sig (READ_ONLY)")
    fc.execute("""
        CREATE TABLE carry_facts (
            formation_date   DATE    NOT NULL,
            underlying       VARCHAR NOT NULL,
            z_carry_neut     DOUBLE,
            quintile         TINYINT,
            eligible         BOOLEAN NOT NULL,
            raw_z            DOUBLE,
            basis_reverting  BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (formation_date, underlying)
        )
    """)
    fc.execute(f"""
        INSERT INTO carry_facts (formation_date, underlying, z_carry_neut, quintile, eligible, raw_z)
        WITH liq AS (
            SELECT formation_date, underlying,
                   ROW_NUMBER() OVER (PARTITION BY formation_date ORDER BY z_ts, raw_z, underlying) AS rn_asc,
                   ROW_NUMBER() OVER (PARTITION BY formation_date ORDER BY z_ts DESC, raw_z DESC, underlying) AS rn_desc,
                   COUNT(*) OVER (PARTITION BY formation_date) AS n_liq
            FROM sig.signals WHERE z_ts IS NOT NULL AND liquid
        )
        SELECT s.formation_date, s.underlying, s.z_ts,
               CASE WHEN NOT s.liquid OR l.n_liq < {MIN_LIQUID} THEN 3
                    WHEN l.rn_asc <= GREATEST(1, CAST(ROUND({QUINTILE_FRAC} * l.n_liq) AS BIGINT)) THEN 1
                    WHEN l.rn_desc <= GREATEST(1, CAST(ROUND({QUINTILE_FRAC} * l.n_liq) AS BIGINT)) THEN 5
                    ELSE 3 END,
               s.liquid, s.raw_z
        FROM sig.signals s
        LEFT JOIN liq l ON l.formation_date = s.formation_date AND l.underlying = s.underlying
        WHERE s.z_ts IS NOT NULL
    """)
    fc.execute("CREATE INDEX idx_facts_date ON carry_facts (formation_date)")
    total = fc.execute("SELECT COUNT(*) FROM carry_facts").fetchone()[0]
    n_form = fc.execute("SELECT COUNT(DISTINCT formation_date) FROM carry_facts").fetchone()[0]
    fc.close()
    os.replace(built, facts_db)
    return total, n_form


def main():
    if not TS_SIG_DB.exists():
        print(f"TS Basis Daily signals not found: {TS_SIG_DB}")
        print("Run scripts/signal_engine/ts_basis_daily/build_ts_basis_daily.py first.")
        return 1
    total, n_form = publish(TS_SIG_DB, TS_FACTS_DB)
    print(f"TS Basis Daily facts: {total:,} rows across {n_form} formations -> {TS_FACTS_DB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
