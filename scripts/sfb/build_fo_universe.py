"""SFB Phase -1 / D3 — Point-in-time F&O-eligible universe with liquidity floor.

Builds fo_eligible_intervals — the set of underlyings with liquid single-stock
futures at each point in time, as (underlying, valid_from, valid_to) half-open
intervals (mirroring symbol_entity_intervals).

Eligibility rule (liquidity-gated presence):
  An underlying is eligible on date t iff it has FUTSTK prints and its trailing
  63-session median daily contracts (computed from data < t) is at or above a
  minimum threshold.

  This is a PIT-safe proxy for the NSE F&O securities list (which the repo does
  not have as a downloadable historical record). It does not use the official
  SEBI/NSE eligibility notices.

Contract units: both legacy (CONTRACTS) and UDiFF (TtlTradgVol) store the number
of contracts traded, so the same `contracts` column is comparable across format
boundaries. Documented here for audit.

Default liquidity threshold: median daily contracts >= 100 over trailing 63
sessions. This is proposed as a default — the operator must ratify it before
it feeds the F1 universe.

Usage:
    python scripts/sfb/build_fo_universe.py
"""

import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"

# Proposed default: minimum median daily contracts over trailing 63 sessions.
# Operator-ratifiable pre-registration §11 universe item.
LIQUIDITY_WINDOW = 63
MIN_MEDIAN_CONTRACTS = 100

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS fo_eligible_intervals (
    underlying  VARCHAR NOT NULL,
    valid_from  DATE    NOT NULL,
    valid_to    DATE    NOT NULL,
    PRIMARY KEY (underlying, valid_from)
);
"""


def build_fo_eligible_intervals(con, min_median=None, window=None):
    """Build liquidity-gated PIT F&O eligibility intervals.

    An underlying is eligible on date t iff:
      (a) it has at least one FUTSTK row on t, AND
      (b) its median daily contracts over the trailing <window>
          sessions (< t) is >= <min_median>.

    Intervals coalesce consecutive eligible days into [valid_from, valid_to).
    """
    if min_median is None:
        min_median = MIN_MEDIAN_CONTRACTS
    if window is None:
        window = LIQUIDITY_WINDOW
    con.execute(SCHEMA_SQL)
    con.execute("DELETE FROM fo_eligible_intervals")

    # Pre-compute trailing liquidity per underlying per trade date
    con.execute("""
        CREATE OR REPLACE TEMP TABLE eligible_dates AS
        WITH daily_ct AS (
            SELECT underlying, trade_date,
                   SUM(contracts) AS tot_contracts
            FROM futures_bhavcopy
            WHERE inst_type = 'FUTSTK'
            GROUP BY underlying, trade_date
        ),
        ranked AS (
            SELECT underlying, trade_date, tot_contracts,
                   ROW_NUMBER() OVER (
                       PARTITION BY underlying ORDER BY trade_date
                   ) AS rn
            FROM daily_ct
        ),
        trailing_median AS (
            SELECT a.underlying, a.trade_date,
                   a.tot_contracts,
                   MEDIAN(b.tot_contracts) AS med_contracts_63d
            FROM ranked a
            JOIN ranked b
                 ON b.underlying = a.underlying
                 AND b.rn > a.rn - 1 - ?
                 AND b.rn < a.rn
            WHERE a.rn > ?
            GROUP BY a.underlying, a.trade_date, a.tot_contracts
        )
        SELECT underlying, trade_date
        FROM trailing_median
        WHERE med_contracts_63d >= ?
          AND tot_contracts > 0
        ORDER BY underlying, trade_date
    """, [window, window, min_median])

    rows = con.execute("""
        SELECT underlying, trade_date FROM eligible_dates
        ORDER BY underlying, trade_date
    """).fetchall()

    intervals = []
    for und, td in rows:
        vt = td + pd.Timedelta(days=1)
        if intervals and intervals[-1][0] == und and intervals[-1][2] == td:
            intervals[-1] = (und, intervals[-1][1], vt)
        else:
            intervals.append((und, td, vt))

    # Merge adjacent intervals for same underlying
    merged = []
    for und, vf, vt in intervals:
        if merged and merged[-1][0] == und and merged[-1][2] >= vf:
            merged[-1] = (und, merged[-1][1], max(merged[-1][2], vt))
        else:
            merged.append((und, vf, vt))

    if not merged:
        con.execute("DELETE FROM fo_eligible_intervals")
        con.execute("DROP TABLE eligible_dates")
        return 0

    df = pd.DataFrame(merged, columns=["underlying", "valid_from", "valid_to"])
    con.execute("INSERT INTO fo_eligible_intervals SELECT underlying, valid_from, "
                "valid_to FROM df")
    con.execute("DROP TABLE eligible_dates")
    return len(merged)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-median", type=int, default=MIN_MEDIAN_CONTRACTS,
                    help=f"Minimum median daily contracts (default {MIN_MEDIAN_CONTRACTS})")
    ap.add_argument("--window", type=int, default=LIQUIDITY_WINDOW,
                    help=f"Trailing window in sessions (default {LIQUIDITY_WINDOW})")
    args = ap.parse_args()

    con = duckdb.connect(str(DB_PATH))
    n = build_fo_eligible_intervals(con, min_median=args.min_median, window=args.window)
    con.close()
    print(f"F&O eligible intervals: {n:,}")
    print(f"Liquidity floor: median daily contracts >= {args.min_median} "
          f"over trailing {args.window} sessions")


if __name__ == "__main__":
    main()
