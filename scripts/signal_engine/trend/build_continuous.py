"""Build roll-adjusted continuous futures prices from raw bhavcopy.

Uses near-month selector + T-3 roll rule (same as Carry). Back-adjusts via
cumulative roll ratio using SQL window functions.
Output: data/signal_engine/trend/continuous.duckdb
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))
import contract_arms as A

FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
OUT_DB = ROOT / "data" / "signal_engine" / "trend" / "continuous.duckdb"


def main():
    con = duckdb.connect()
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute(f"ATTACH '{OUT_DB}' AS out")
    con.execute("SET threads=4")

    print("Building near-month panel...")
    n_cells = A.build_basis_panel(con)
    print(f"  {n_cells:,} cells")

    # Create output table
    con.execute("""
        CREATE TABLE IF NOT EXISTS out.trend_continuous (
            underlying VARCHAR,
            trade_date DATE,
            adj_close DOUBLE,
            raw_close DOUBLE,
            roll_flag BOOLEAN,
            PRIMARY KEY (underlying, trade_date)
        )
    """)
    con.execute("DELETE FROM out.trend_continuous")

    print("Computing roll-adjusted continuous series...")
    con.execute("""
        INSERT INTO out.trend_continuous
        WITH gaps AS (
            SELECT underlying, trade_date, fut_close, expiry_dt,
                   CASE WHEN expiry_dt != LEAD(expiry_dt) OVER (PARTITION BY underlying ORDER BY trade_date)
                        THEN LEAD(fut_close) OVER (PARTITION BY underlying ORDER BY trade_date)
                             / NULLIF(fut_close, 0)
                        ELSE 1.0 END AS gap
            FROM basis_panel
        ),
        cumed AS (
            SELECT underlying, trade_date, fut_close, gap,
                   CASE WHEN gap != 1.0 THEN TRUE ELSE FALSE END AS roll_flag,
                   EXP(SUM(CASE WHEN gap > 0 THEN LN(gap) ELSE 0 END) OVER (
                       PARTITION BY underlying
                       ORDER BY trade_date DESC
                       ROWS UNBOUNDED PRECEDING
                   )) AS cum_ratio
            FROM gaps
        )
        SELECT underlying, trade_date,
               fut_close * cum_ratio AS adj_close,
               fut_close AS raw_close,
               roll_flag
        FROM cumed
        ORDER BY underlying, trade_date
    """)

    cnt = con.execute("SELECT COUNT(*) FROM out.trend_continuous").fetchone()[0]
    uls = con.execute("SELECT COUNT(DISTINCT underlying) FROM out.trend_continuous").fetchone()[0]
    dater = con.execute("SELECT MIN(trade_date), MAX(trade_date) FROM out.trend_continuous").fetchone()
    rolls = con.execute("SELECT COUNT(*) FROM out.trend_continuous WHERE roll_flag = TRUE").fetchone()[0]
    print(f"Done: {cnt:,} rows, {uls} underlyings")
    print(f"  Range: {dater[0]} -> {dater[1]}")
    print(f"  Roll events: {rolls}")

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
