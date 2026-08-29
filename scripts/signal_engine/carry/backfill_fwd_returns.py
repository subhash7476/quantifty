"""Backfill fwd_ret_1m in the monthly Carry signal store.

build_carry.py computes forward returns only for the formation dates built in
that same run (build_carry.py:308-314, `formation_date IN (fmt_dates)`), so an
incremental refresh fills the new month and leaves historical NULLs untouched.
The store on disk reached a state with fwd_ret_1m NULL in all 23,419 rows, which
silently empties run_train.py:262 and run_net_spread.py:196 -- both filter
`fwd_ret_1m IS NOT NULL` against it.

This fills every fillable NULL using the SAME join build_carry.py uses
(equity_bhavcopy_adjusted close at formation_date -> close at
fwd_formation_date). It is idempotent: rows already populated are untouched.

Unlike build_carry.py's unguarded UPDATE, this ASSERTS that the number of rows
filled matches the number the join said were fillable, and exits non-zero
otherwise -- a fill that quietly writes nothing is the failure being repaired.

Run with --dry-run to report without writing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"

FILLABLE_SQL = """
    SELECT s.formation_date, s.underlying,
           (a2.close - a1.close) / a1.close AS fwd_ret
    FROM signals s
    JOIN formations f
      ON f.formation_date = s.formation_date AND f.fwd_formation_date IS NOT NULL
    JOIN eq.equity_bhavcopy_adjusted a1
      ON a1.symbol = s.underlying AND a1.trade_date = s.formation_date
     AND a1.series = 'EQ' AND a1.close IS NOT NULL AND a1.close > 0
    JOIN eq.equity_bhavcopy_adjusted a2
      ON a2.symbol = s.underlying AND a2.trade_date = f.fwd_formation_date
     AND a2.series = 'EQ' AND a2.close IS NOT NULL AND a2.close > 0
    WHERE s.fwd_ret_1m IS NULL
"""


def main():
    dry = "--dry-run" in sys.argv
    if not SIG_DB.exists() or not EQ_DB.exists():
        print(f"ERROR: missing store ({SIG_DB.exists()=}, {EQ_DB.exists()=})")
        return 1

    con = duckdb.connect(str(SIG_DB), read_only=dry)
    con.execute("SET threads=2")
    con.execute("SET memory_limit='4GB'")
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")

    total = con.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    before = con.execute("SELECT COUNT(*) FROM signals WHERE fwd_ret_1m IS NULL").fetchone()[0]
    fillable = con.execute(f"SELECT COUNT(*) FROM ({FILLABLE_SQL})").fetchone()[0]
    print(f"rows={total:,}  null={before:,}  fillable={fillable:,}")

    if dry:
        print("dry-run: no write")
        return 0
    if fillable == 0:
        print("nothing to fill")
        return 0

    con.execute(f"CREATE TEMP TABLE fwd_returns AS {FILLABLE_SQL}")
    con.execute("""
        UPDATE signals s
        SET fwd_ret_1m = fr.fwd_ret
        FROM fwd_returns fr
        WHERE fr.formation_date = s.formation_date AND fr.underlying = s.underlying
    """)
    con.execute("DROP TABLE IF EXISTS fwd_returns")

    after = con.execute("SELECT COUNT(*) FROM signals WHERE fwd_ret_1m IS NULL").fetchone()[0]
    filled = before - after
    con.close()

    print(f"filled={filled:,}  remaining_null={after:,}")
    if filled != fillable:
        print(f"FAIL: expected to fill {fillable:,}, filled {filled:,}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
