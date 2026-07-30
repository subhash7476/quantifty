"""Trade Intelligence — M3 Option Snapshot.

Reads today's open trades from trade_intelligence.duckdb and enriches
them with ATM option characteristics: type, strike, expiry, DTE,
premium, OI, lot size.

Uses the same option selection logic as ts_basis_daily_options.py
(select_book_options from core/analytics/options_selection.py).

Usage:
  python scripts/signal_engine/ts_basis_daily/snapshot_options.py
  python scripts/signal_engine/ts_basis_daily/snapshot_options.py 2026-07-28
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from core.analytics.options_selection import select_book_options

TI_DB = ROOT / "data" / "signal_engine" / "trade_intelligence" / "trade_intelligence.duckdb"
FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"


def main():
    target = None
    for a in sys.argv[1:]:
        if a.startswith("20") and len(a) == 10 and a[4] == "-":
            try:
                target = date.fromisoformat(a)
            except ValueError:
                pass
            break

    if target is None:
        fc = duckdb.connect(str(FACTS_DB), read_only=True)
        target = fc.execute(
            "SELECT MAX(formation_date) FROM carry_facts"
        ).fetchone()[0]
        fc.close()

    if target is None:
        print("No formation dates found in facts DB.")
        return 1

    print(f"Target date: {target}")

    # Read open trades for this date
    ti = duckdb.connect(str(TI_DB))
    rows = ti.execute(
        "SELECT trade_id, underlying, side FROM trades WHERE entry_date = ?",
        [target],
    ).fetchall()
    ti.close()

    if not rows:
        print(f"No open trades found for {target}.")
        return 1

    book = [(r[1], r[2]) for r in rows]
    print(f"  {len(book)} trades to enrich")

    # Resolve option contracts
    contracts = select_book_options(book, today=target)
    resolved = [c for c in contracts if c.get("strike")]

    print(f"  {len(resolved)}/{len(book)} options resolved")

    if not resolved:
        print("No options resolved — nothing to update.")
        return 1

    # Update TI DB
    ti = duckdb.connect(str(TI_DB))
    updates = 0
    for c in resolved:
        trade_id = f"{c['ticker']}_{target}_{c['direction']}"
        dte = (c["expiry"] - target).days if c.get("expiry") else None
        ti.execute("""
            UPDATE trades
            SET opt_type = ?, opt_strike = ?, opt_expiry = ?,
                opt_dte = ?, opt_premium = ?, opt_oi = ?, opt_lot_size = ?
            WHERE trade_id = ?
        """, (
            c.get("opt_type"),
            c.get("strike"),
            c.get("expiry"),
            dte,
            c.get("settle"),
            c.get("oi"),
            c.get("lot_size"),
            trade_id,
        ))
        updates += 1

    ti.close()
    print(f"  {updates} trades enriched with option data")

    # Show sample
    ti = duckdb.connect(str(TI_DB), read_only=True)
    sample = ti.execute("""
        SELECT underlying, side, opt_type, opt_strike, opt_expiry,
               opt_dte, opt_premium, opt_oi
        FROM trades WHERE entry_date = ? AND opt_type IS NOT NULL
        LIMIT 5
    """, [target]).fetchall()
    ti.close()

    if sample:
        print(f"\n  {'Underlying':<16} {'Side':>6} {'Type':>4} {'Strike':>8} "
              f"{'Expiry':>12} {'DTE':>4} {'Premium':>9} {'OI':>8}")
        print(f"  {'-'*75}")
        for u, s, ot, st, ex, dte, prem, oi in sample:
            print(f"  {u:<16} {s:>6} {ot or '--':>4} "
                  f"{float(st) if st else 0:>8.0f} "
                  f"{str(ex) if ex else '--':>12} "
                  f"{int(dte) if dte else 0:>4} "
                  f"{float(prem) if prem else 0:>9.2f} "
                  f"{int(oi) if oi else 0:>8}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
