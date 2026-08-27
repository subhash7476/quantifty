"""Point-in-time CAS category (I = F&O-eligible, II = everything else).

SEBI's Closing Auction Session applies only to Category I stocks. Membership
changes over time, so this is a per-symbol interval table, not an era flag.

Derived from futures bhavcopy rather than the F&O instrument master: the master
is a current snapshot, and a snapshot cannot answer "was this symbol F&O-eligible
on 2026-08-04". The bhavcopy is genuinely point-in-time.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
FUTURES_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
OUT_DB = ROOT / "data" / "cas" / "cas_category.duckdb"


def is_cat1(symbol: str, on, con) -> bool:
    """True if `symbol` had a STOCK futures contract trading on `on`.

    FUTIDX is excluded: an index underlying (BANKNIFTY, NIFTY) is not a cash
    equity and so can never be a CAS Category I stock.
    """
    row = con.execute(
        "SELECT 1 FROM futures_bhavcopy WHERE underlying = ? AND trade_date = ? "
        "AND inst_type = 'FUTSTK' LIMIT 1",
        [symbol, on],
    ).fetchone()
    return row is not None


def build_intervals(con) -> list:
    """One (symbol, effective_from, effective_to) row per contiguous eligibility run."""
    rows = con.execute(
        "SELECT DISTINCT underlying, trade_date FROM futures_bhavcopy "
        "WHERE inst_type = 'FUTSTK' ORDER BY underlying, trade_date"
    ).fetchall()
    out = []
    current_symbol = None
    run_start = run_end = None
    for symbol, trade_date in rows:
        if symbol != current_symbol:
            if current_symbol is not None:
                out.append((current_symbol, run_start, run_end))
            current_symbol, run_start, run_end = symbol, trade_date, trade_date
        else:
            run_end = trade_date
    if current_symbol is not None:
        out.append((current_symbol, run_start, run_end))
    return out


def build(out_path: Path = OUT_DB) -> int:
    src = duckdb.connect(str(FUTURES_DB), read_only=True)
    try:
        intervals = build_intervals(src)
    finally:
        src.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    dst = duckdb.connect(str(out_path))
    try:
        dst.execute("DROP TABLE IF EXISTS cas_category")
        dst.execute(
            "CREATE TABLE cas_category "
            "(symbol VARCHAR, effective_from DATE, effective_to DATE)"
        )
        dst.executemany(
            "INSERT INTO cas_category VALUES (?, ?, ?)", intervals
        )
    finally:
        dst.close()
    return len(intervals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DB)
    args = parser.parse_args()
    print(f"wrote {build(args.out)} category intervals to {args.out}")
