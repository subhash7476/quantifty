"""TS Basis Daily — Recovery-State Filter Application.

Adds a `recovery_reject` column to ts_facts.duckdb/carry_facts,
marking signals where the basis is already reverting (mean-reversion
has started, forward edge is weak).

Rule: |z| > 0.70 AND dbasis1 * sign(z_ts) <= 0  →  recovery_reject = TRUE
       (the basis dislocation is already shrinking)

Runs idempotently — safe to call after every facts publish.

Usage:
  python scripts/signal_engine/ts_basis_daily/apply_recovery_filter.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"

Z_THRESHOLD = 0.70


def main():
    if not FACTS_DB.exists():
        print("Facts DB not found — run publish_facts.py first.")
        return 1

    if not SIG_DB.exists():
        print("Signals DB not found — run build_ts_basis_daily.py first.")
        return 1

    con = duckdb.connect(str(FACTS_DB))
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute("SET threads=4")

    # Ensure column exists
    cols = {r[2] for r in con.execute("PRAGMA table_info('carry_facts')").fetchall()}
    if "recovery_reject" not in cols:
        con.execute("ALTER TABLE carry_facts ADD COLUMN recovery_reject BOOLEAN DEFAULT FALSE")
        print("  Added recovery_reject column")

    # Reset all to FALSE (idempotent)
    con.execute("UPDATE carry_facts SET recovery_reject = FALSE")

    # Mark reverting signals
    con.execute(f"""
        WITH basis_delta AS (
            SELECT formation_date, underlying, z_ts, raw_ann_basis,
                   LAG(raw_ann_basis, 1) OVER (
                       PARTITION BY underlying ORDER BY formation_date
                   ) AS basis_lag1
            FROM sig.signals
            WHERE z_ts IS NOT NULL AND raw_ann_basis IS NOT NULL
        ),
        reverting AS (
            SELECT formation_date, underlying
            FROM basis_delta
            WHERE ABS(z_ts) > {Z_THRESHOLD}
              AND basis_lag1 IS NOT NULL
              AND (raw_ann_basis - basis_lag1) * CASE WHEN z_ts > 0 THEN 1 ELSE -1 END <= 0
        )
        UPDATE carry_facts SET recovery_reject = TRUE
        WHERE (formation_date, underlying) IN (
            SELECT formation_date, underlying FROM reverting
        )
    """)

    n_rejected = con.execute(
        "SELECT COUNT(*) FROM carry_facts WHERE recovery_reject = TRUE"
    ).fetchone()[0]
    n_total = con.execute("SELECT COUNT(*) FROM carry_facts").fetchone()[0]
    n_with_z = con.execute(
        f"SELECT COUNT(*) FROM carry_facts WHERE ABS(z_carry_neut) > {Z_THRESHOLD}"
    ).fetchone()[0]

    con.close()

    print(f"  Recovery filter applied: {n_rejected:,} rejected / {n_total:,} total facts")
    print(f"  ({n_rejected / max(n_with_z, 1) * 100:.1f}% of |z| > {Z_THRESHOLD} signals rejected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
