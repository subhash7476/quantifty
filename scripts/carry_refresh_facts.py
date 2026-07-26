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
    """Check if today is at or past the next expected formation date.

    Formation dates are the last trading day of each month. We check if
    today >= the last trading day of the current month (rough heuristic).
    """
    max_facts = _max_formation_date()
    if max_facts is None:
        return True
    return today > max_facts


def main():
    today = date.today()
    max_facts = _max_formation_date()
    max_bhav = _max_bhavcopy_date()

    print(f"Today: {today}")
    print(f"Facts max formation: {max_facts}")
    print(f"Bhavcopy max trade:  {max_bhav}")

    if not _has_formation_passed(today):
        print("Up to date — no new formation expected yet.")
        return 0

    if max_bhav is None or max_bhav <= (max_facts or date(2000, 1, 1)):
        print("STALE: bhavcopy has not advanced past the last facts formation. "
              "Run futures bhavcopy ingest first.")
        return 2

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

    new_max = _max_formation_date()
    print(f"Refresh complete. Facts max: {new_max} (was {max_facts})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
