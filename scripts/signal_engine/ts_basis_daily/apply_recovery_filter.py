"""TS Basis Daily — Signal Enrichment (post-facts).

Fills the market-state column in ts_facts.duckdb/carry_facts:

  basis_reverting — TRUE when the basis dislocation is already shrinking

raw_z (the unclamped z) is written by build_ts_basis_daily and carried into
facts by publish_facts. Runs idempotently after every facts publish.

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

    con.execute("UPDATE carry_facts SET basis_reverting = FALSE")

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
        UPDATE carry_facts SET basis_reverting = TRUE
        WHERE (formation_date, underlying) IN (
            SELECT formation_date, underlying FROM reverting
        )
    """)

    n_reverting = con.execute(
        "SELECT COUNT(*) FROM carry_facts WHERE basis_reverting = TRUE"
    ).fetchone()[0]

    n_raw_z = con.execute(
        "SELECT COUNT(*) FROM carry_facts WHERE raw_z IS NOT NULL"
    ).fetchone()[0]
    n_clamped = con.execute(
        "SELECT COUNT(*) FROM carry_facts WHERE ABS(z_carry_neut) >= 2.99 AND ABS(raw_z) > 3.01"
    ).fetchone()[0]

    n_total = con.execute("SELECT COUNT(*) FROM carry_facts").fetchone()[0]
    n_strong = con.execute(
        f"SELECT COUNT(*) FROM carry_facts WHERE ABS(z_carry_neut) > {Z_THRESHOLD}"
    ).fetchone()[0]

    con.close()

    print(f"  basis_reverting: {n_reverting:,} / {n_strong:,} strong-z ({n_reverting/max(n_strong,1)*100:.1f}%)")
    print(f"  raw_z:           {n_raw_z:,} / {n_total:,} populated, "
          f"{n_clamped:,} signals clamped with true |z| > 3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
