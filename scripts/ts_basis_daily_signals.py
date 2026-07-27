"""TS Basis Daily — signal report.

Prints the exact long/short signals for the latest (or specified)
formation date. Reads from ts_facts.duckdb.

Usage:
  python scripts/ts_basis_daily_signals.py              # latest date
  python scripts/ts_basis_daily_signals.py 2026-07-21    # specific date
  python scripts/ts_basis_daily_signals.py --top N       # top-N (default 5)
  python scripts/ts_basis_daily_signals.py --all         # all quintiles
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"
SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"


def main():
    if not FACTS_DB.exists():
        print("ERROR: Facts DB not found. Run refresh_all_strategies.py first.")
        return 1

    show_all = "--all" in sys.argv
    top_n = 5
    for i, a in enumerate(sys.argv):
        if a == "--top" and i + 1 < len(sys.argv):
            try:
                top_n = int(sys.argv[i + 1])
            except ValueError:
                pass

    # Find target date
    target = None
    for a in sys.argv[1:]:
        if a.startswith("20") and len(a) == 10 and a[4] == "-":
            try:
                target = date.fromisoformat(a)
            except ValueError:
                pass
            break

    con = duckdb.connect(str(FACTS_DB), read_only=True)

    if target is None:
        target = con.execute(
            "SELECT MAX(formation_date) FROM carry_facts"
        ).fetchone()[0]

    q_map = {1: "SHORT", 3: "NEUTRAL", 5: "LONG"}
    rows = con.execute("""
        SELECT underlying, z_carry_neut, quintile, eligible
        FROM carry_facts WHERE formation_date = ?
        ORDER BY z_carry_neut
    """, [target]).fetchall()
    con.close()

    if not rows:
        print(f"No signals for {target}")
        return 1

    # Get signal counts from signals DB for context
    sc = duckdb.connect(str(SIG_DB), read_only=True)
    n_liquid = sc.execute(
        "SELECT COUNT(*) FROM signals WHERE formation_date = ? AND liquid = TRUE AND z_ts IS NOT NULL",
        [target],
    ).fetchone()[0]
    n_total = sc.execute(
        "SELECT COUNT(*) FROM signals WHERE formation_date = ? AND z_ts IS NOT NULL", [target]
    ).fetchone()[0]
    sc.close()

    print(f"\n{'='*60}")
    print(f"  TS Basis Daily — Signals for {target}")
    print(f"  {n_total} names scored, {n_liquid} liquid")
    print(f"{'='*60}")

    liquid_rows = [r for r in rows if r[3]]
    nq = max(1, round(0.20 * len(liquid_rows))) if len(liquid_rows) >= 5 else 0

    if not show_all:
        # Top-N shorts (lowest z_ts)
        shorts = [r for r in rows if r[2] in (1,) and r[3]][:top_n]
        # Top-N longs (highest z_ts)  
        longs = [r for r in rows if r[2] in (5,) and r[3]][-top_n:]

        print(f"\n  SHORT (Q1, lowest z_ts) — top {len(shorts)}:")
        print(f"  {'Underlying':<25} {'z_ts':>8}")
        print(f"  {'-'*33}")
        for u, z, q, e in shorts:
            print(f"  {u:<25} {z:>8.4f}")

        print(f"\n  LONG  (Q5, highest z_ts) — top {len(longs)}:")
        print(f"  {'Underlying':<25} {'z_ts':>8}")
        print(f"  {'-'*33}")
        for u, z, q, e in reversed(longs):
            print(f"  {u:<25} {z:>8.4f}")
    else:
        # All quintiles
        q_labels = {1: "Q1 SHORT", 5: "Q5 LONG", 3: "Q3 NEUTRAL"}
        for q in [1, 5, 3]:
            subset = [r for r in rows if r[2] == q]
            if not subset:
                continue
            print(f"\n  {q_labels.get(q, f'Q{q}')} ({len(subset)} names):")
            print(f"  {'Underlying':<25} {'z_ts':>8}")
            print(f"  {'-'*33}")
            for u, z, _, _ in (reversed(subset) if q == 5 else subset):
                print(f"  {u:<25} {z:>8.4f}")

    # Summary stats
    long_ct = sum(1 for r in rows if r[2] == 5)
    short_ct = sum(1 for r in rows if r[2] == 1)
    print(f"\n  Quintile breakdown: {short_ct} SHORT / {len(rows) - long_ct - short_ct} NEUTRAL / {long_ct} LONG")
    print(f"  Next: run scripts/ts_basis_daily_paper_replay.py for LoopDriver replay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
