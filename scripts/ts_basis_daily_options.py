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
    DEFAULT_MIN_DTE,
    select_book_options,
)

ROOT = Path(__file__).resolve().parent.parent
FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
Z_CLAMP = 3.0   # build_ts_basis_daily.Z_CLAMP: z_ts sits at ±3 exactly when |raw_z| >= 3


def stale_message(formation: date) -> str | None:
    """Why the latest formation is not current, or None when it is."""
    con = duckdb.connect(str(FUT_DB), read_only=True)
    source = con.execute("SELECT MAX(trade_date) FROM futures_bhavcopy WHERE inst_type='FUTSTK'").fetchone()[0]
    con.close()
    if formation is None or (source is not None and formation < source):
        return (f"STALE: latest TS Basis Daily formation is {formation} but the futures store has {source} — "
                f"refresh_all_strategies.py did not build it. Pass a date to view a past book.")
    return None


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
        "WHERE formation_date = ? AND eligible ORDER BY z_carry_neut, raw_z, underlying",
        [target],
    ).fetchall()
    con.close()
    shorts = [(u, "SHORT") for u, q in rows if q == 1][:top_n]
    longs = [(u, "LONG") for u, q in rows if q == 5][-top_n:][::-1]
    return target, longs + shorts


def get_clamp_book(target: date | None):
    """Every liquid name whose z sits at the ±Z_CLAMP clamp, strongest first on each side."""
    con = duckdb.connect(str(FACTS_DB), read_only=True)
    if target is None:
        target = con.execute("SELECT MAX(formation_date) FROM carry_facts").fetchone()[0]
    rows = con.execute(
        "SELECT underlying, raw_z FROM carry_facts "
        "WHERE formation_date = ? AND eligible AND ABS(raw_z) >= ?",
        [target, Z_CLAMP],
    ).fetchall()
    con.close()
    longs = [(u, "LONG") for u, z in sorted((r for r in rows if r[1] > 0), key=lambda r: (-r[1], r[0]))]
    shorts = [(u, "SHORT") for u, z in sorted((r for r in rows if r[1] < 0), key=lambda r: (r[1], r[0]))]
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

    latest = target is None
    target, book = get_book(target, top_n)
    if latest and (stale := stale_message(target)):
        print(stale, file=sys.stderr)
        return 2
    contracts = select_book_options(book, min_dte=min_dte)

    print(f"\n{'='*90}")
    print(f"  TS Basis Daily — ATM options for {target}  (live-anchored when market open; EOD fallback)")
    print(f"{'='*90}")
    print(f"  {'Ticker':<11}{'Dir':<6}{'Opt':<4}{'Expiry':<12}{'Fwd':>9}{'Strike':>8}"
          f"{'Prem':>8}{'OI':>11}{'Lot':>8}{'PremCost':>11}{'Src':>11}{'Screen':>10}")
    print(f"  {'-'*109}")

    notes = []
    for c in contracts:
        if c["screen"] == "no_tradeable_strike":
            print(f"  {c['ticker']:<11}{c['direction']:<6}{c['opt_type']:<4}"
                  f"  NO TRADEABLE STRIKE  ({c['screen_reason']})")
            continue
        if c["strike"] is None:
            print(f"  {c['ticker']:<11}{c['direction']:<6}{c['opt_type']:<4}  NO CHAIN")
            continue
        print(f"  {c['ticker']:<11}{c['direction']:<6}{c['opt_type']:<4}"
              f"{str(c['expiry']):<12}{c['forward']:>9.1f}{c['strike']:>8.0f}"
              f"{c['settle']:>8.2f}{c['oi']:>11}{(c['lot_size'] or 0):>8}"
              f"{(c['premium_cost'] or 0):>11,.0f}"
              f"{(c['anchor_source'] or '-'):>11}{(c['screen'] or '-'):>10}")
        if c["snapped"]:
            notes.append(f"  {c['ticker']}: snapped off nearest strike "
                         f"{c['nearest_strike']:.0f} to {c['strike']:.0f}.")
        if c["instrument_key"] is None:
            notes.append(f"  {c['ticker']}: no instrument key resolved (not tradeable via API).")

    if notes:
        print(f"\n  Notes:")
        for n in notes:
            print(n)
    print(f"\n  Fwd = live future LTP when Src=live, else EOD future close.  "
          f"Screen = live spread/OI/volume verdict (skipped = no live feed).")
    print(f"  PremCost = premium x lot (1 lot debit).  Live prices: /ts-basis-daily/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
