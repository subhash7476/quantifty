"""Carry facts-refresh scheduler — Piece 1 of forward-PAPER plan.

Checks facts.duckdb staleness and runs publish_facts.py --forward to
append new formation dates. The staleness guard fails loudly if today
is past a formation date and the DB hasn't kept up — no silent stops.

Usage: python scripts/carry_refresh_facts.py
Exit codes: 0 = up-to-date, 1 = refreshed, 2 = stale (needs bhavcopy)
"""
from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FACTS_DB = ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
BHAVCOPY_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
PUBLISH = ROOT / "scripts" / "signal_engine" / "carry" / "publish_facts.py"


def _max_formation_date() -> date | None:
    if not FACTS_DB.exists():
        return None
    con = duckdb.connect(str(FACTS_DB), read_only=True)
    max_date = con.execute(
        "SELECT MAX(formation_date) FROM carry_facts"
    ).fetchone()[0]
    con.close()
    return max_date


def _max_bhavcopy_date() -> date | None:
    if not BHAVCOPY_DB.exists():
        return None
    con = duckdb.connect(str(BHAVCOPY_DB), read_only=True)
    max_date = con.execute(
        "SELECT MAX(trade_date) FROM futures_bhavcopy WHERE inst_type='FUTSTK'"
    ).fetchone()[0]
    con.close()
    return max_date


def _has_formation_passed(today: date) -> bool:
    """Check if today is at or past the last completed month-end formation."""
    max_facts = _max_formation_date()
    if max_facts is None:
        return True
    return today > max_facts


def main():
    today = date.today()
    max_facts_before = _max_formation_date()
    max_bhav = _max_bhavcopy_date()

    print(f"Today: {today}")
    print(f"Facts max formation (before): {max_facts_before}")
    print(f"Bhavcopy max trade:  {max_bhav}")

    if not _has_formation_passed(today):
        print("Up to date — no new formation expected yet.")
        return 0

    if max_bhav is None or max_bhav <= (max_facts_before or date(2000, 1, 1)):
        print("STALE: bhavcopy has not advanced past the last facts formation. "
              "Run futures bhavcopy ingest first.")
        return 2

    if max_facts_before is not None:
        con = duckdb.connect(str(BHAVCOPY_DB), read_only=True)

        next_month = max_facts_before.month + 1
        next_year = max_facts_before.year
        if next_month > 12:
            next_month = 1
            next_year += 1

        month_after_next = next_month + 1
        year_after_next = next_year
        if month_after_next > 12:
            month_after_next = 1
            year_after_next += 1

        next_month_data = con.execute("""
            SELECT COUNT(*) FROM futures_bhavcopy WHERE inst_type='FUTSTK'
            AND year(trade_date) = ? AND month(trade_date) = ?
        """, [next_year, next_month]).fetchone()[0]

        month_after_data = con.execute("""
            SELECT COUNT(*) FROM futures_bhavcopy WHERE inst_type='FUTSTK'
            AND year(trade_date) = ? AND month(trade_date) = ?
        """, [year_after_next, month_after_next]).fetchone()[0]

        con.close()

        if next_month_data == 0:
            print(f"STALE: last facts formation ({max_facts_before}) is the latest "
                  f"completed month — no bhavcopy data for {next_year}-{next_month:02d}. "
                  f"Run futures bhavcopy ingest first.")
            return 2

        if month_after_data == 0:
            print(f"Up to date: next month ({next_year}-{next_month:02d}) has bhavcopy "
                  f"but the following month ({year_after_next}-{month_after_next:02d}) "
                  f"does not, so {next_year}-{next_month:02d} is not yet a completed month. "
                  f"No new formation available.")
            return 0

    print(f"Refreshing: publishing facts up to {max_bhav}...")
    result = subprocess.run(
        [sys.executable, str(PUBLISH), "--forward"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"publish_facts FAILED (rc={result.returncode})")
        print(result.stderr)
        return result.returncode

    max_facts_after = _max_formation_date()

    if max_facts_after is None or max_facts_after <= (max_facts_before or date(2000, 1, 1)):
        print(f"REFRESH FAILED: MAX(formation_date) did not advance "
              f"(before={max_facts_before}, after={max_facts_after}). "
              f"publish_facts --forward added 0 new formations. "
              f"Check bhavcopy data and signal construction.")
        return 3

    new_formations = sum(1 for d in [
        max_facts_before, max_facts_after
    ] if d is not None)
    print(f"Refresh complete. Facts max: {max_facts_after} (was {max_facts_before})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
