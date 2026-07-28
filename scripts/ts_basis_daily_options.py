"""TS Basis Daily — options selection.

Maps the latest TS Basis Daily signal book to tradeable single-stock options:
  LONG  (Q5) -> buy CE
  SHORT (Q1) -> buy PE

Selection rules live in core/analytics/options_selection.py, shared with the
/ts-basis-daily/ Flask panel so the CLI and the page cannot drift apart.

Premium / OI are EOD from the stock-options bhavcopy (last available trade
date) — a liquidity and rough-cost reference, NOT a live quote. The web panel
shows live prices; re-check the live chain before trading.

Usage:
  python scripts/ts_basis_daily_options.py                 # latest formation
  python scripts/ts_basis_daily_options.py 2026-07-27      # specific date
  python scripts/ts_basis_daily_options.py --top 5 --min-dte 7
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.analytics.options_selection import (  # noqa: E402
    MIN_OI,
    DEFAULT_MIN_DTE,
    select_book_options,
)

ROOT = Path(__file__).resolve().parent.parent
FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"


def _arg_value(flag: str, default):
    for i, a in enumerate(sys.argv):
        if a == flag and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def get_book(target: date | None, top_n: int):
    con = duckdb.connect(str(FACTS_DB), read_only=True)
    if target is None:
        target = con.execute("SELECT MAX(formation_date) FROM carry_facts").fetchone()[0]
    rows = con.execute(
        "SELECT underlying, quintile FROM carry_facts "
        "WHERE formation_date = ? AND eligible ORDER BY z_carry_neut",
        [target],
    ).fetchall()
    con.close()
    shorts = [(u, "SHORT") for u, q in rows if q == 1][:top_n]
    longs = [(u, "LONG") for u, q in rows if q == 5][-top_n:][::-1]
    return target, longs + shorts


def main():
    if not FACTS_DB.exists():
        print(f"ERROR: missing {FACTS_DB}")
        return 1

    top_n = int(_arg_value("--top", 5))
    min_dte = int(_arg_value("--min-dte", DEFAULT_MIN_DTE))
    target = None
    for a in sys.argv[1:]:
        if a.startswith("20") and len(a) == 10 and a[4] == "-":
            try:
                target = date.fromisoformat(a)
            except ValueError:
                pass
            break

    target, book = get_book(target, top_n)
    contracts = select_book_options(book, min_dte=min_dte)

    print(f"\n{'='*90}")
    print(f"  TS Basis Daily — ATM options for {target}  (EOD ref; NOT a live quote)")
    print(f"{'='*90}")
    print(f"  {'Ticker':<11}{'Dir':<6}{'Opt':<4}{'Expiry':<12}{'Fwd':>9}{'Strike':>8}"
          f"{'Prem':>8}{'OI':>11}{'Lot':>8}{'PremCost':>11}")
    print(f"  {'-'*86}")

    notes = []
    for c in contracts:
        if c["strike"] is None:
            print(f"  {c['ticker']:<11}{c['direction']:<6}{c['opt_type']:<4}  NO CHAIN")
            continue
        print(f"  {c['ticker']:<11}{c['direction']:<6}{c['opt_type']:<4}"
              f"{str(c['expiry']):<12}{c['forward']:>9.1f}{c['strike']:>8.0f}"
              f"{c['settle']:>8.2f}{c['oi']:>11}{(c['lot_size'] or 0):>8}"
              f"{(c['premium_cost'] or 0):>11,.0f}")
        if c["snapped"]:
            notes.append(f"  {c['ticker']}: nearest strike {c['nearest_strike']:.0f} had "
                         f"OI<{MIN_OI}; snapped to liquid ATM {c['strike']:.0f}.")
        if c["instrument_key"] is None:
            notes.append(f"  {c['ticker']}: no instrument key resolved (not tradeable via API).")

    if notes:
        print(f"\n  Notes:")
        for n in notes:
            print(n)
    print(f"\n  Fwd = latest {min_dte}+DTE monthly future close (ATM anchor).  "
          f"Prem/OI = bhavcopy EOD.")
    print(f"  PremCost = premium x lot (1 lot debit).  Live prices: /ts-basis-daily/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
