"""Build consolidated Nifty 50 daily index database.

Pre-computes Nifty 50 daily close from 3,563 1d files into a single
DuckDB database for fast beta computation.
"""
from __future__ import annotations

import sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[3]
INDEX_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
OUT_DB = ROOT / "data" / "signal_engine" / "carry" / "nifty50.duckdb"
INDEX_SYMBOL = "NSE_INDEX|Nifty 50"

out = duckdb.connect(str(OUT_DB))
out.execute("CREATE TABLE IF NOT EXISTS nifty50 (trade_date DATE PRIMARY KEY, close DOUBLE)")
out.execute("DELETE FROM nifty50")

dates = sorted(INDEX_DIR.glob("*.duckdb"))
n = len(dates)
print(f"Processing {n} daily files...")

inserted = 0
for i, fpath in enumerate(dates):
    if (i + 1) % 500 == 0:
        print(f"  {i+1}/{n}")
    td = fpath.stem
    try:
        sub = duckdb.connect(str(fpath), read_only=True)
        r = sub.execute(
            f"SELECT close FROM candles WHERE symbol='{INDEX_SYMBOL}'"
        ).fetchone()
        sub.close()
        if r and r[0] is not None and r[0] > 0:
            out.execute("INSERT OR IGNORE INTO nifty50 VALUES (?, ?)", [td, r[0]])
            inserted += 1
    except Exception:
        pass

out.close()
print(f"Done: {inserted:,} rows written to {OUT_DB}")
