"""Build consolidated Nifty 50 daily index database.

Pre-computes Nifty 50 daily close from the 1d index files into a single
DuckDB database for fast beta computation.

Incremental by default: only per-date files whose trade_date is not already
stored are opened and inserted, so a daily run touches one new file instead of
re-reading every file. Keying on "not already present" (not just "newer than
max") also picks up backfilled older sessions. Pass --full to wipe and rebuild.
"""
from __future__ import annotations

import sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[3]
INDEX_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
OUT_DB = ROOT / "data" / "signal_engine" / "carry" / "nifty50.duckdb"
INDEX_SYMBOL = "NSE_INDEX|Nifty 50"

full = "--full" in sys.argv

out = duckdb.connect(str(OUT_DB))
out.execute("CREATE TABLE IF NOT EXISTS nifty50 (trade_date DATE PRIMARY KEY, close DOUBLE)")
if full:
    out.execute("DELETE FROM nifty50")

existing = {r[0].isoformat() for r in out.execute("SELECT trade_date FROM nifty50").fetchall()}

files = sorted(INDEX_DIR.glob("*.duckdb"))
todo = [f for f in files if f.stem not in existing]
print(f"{len(files)} daily files, {len(existing)} already stored, {len(todo)} to process...")

inserted = 0
for i, fpath in enumerate(todo):
    if (i + 1) % 500 == 0:
        print(f"  {i+1}/{len(todo)}")
    td = fpath.stem
    sub = duckdb.connect(str(fpath), read_only=True)
    r = sub.execute(
        f"SELECT close FROM candles WHERE symbol='{INDEX_SYMBOL}'"
    ).fetchone()
    sub.close()
    if r and r[0] is not None and r[0] > 0:
        out.execute("INSERT OR IGNORE INTO nifty50 VALUES (?, ?)", [td, r[0]])
        inserted += 1

total = out.execute("SELECT COUNT(*) FROM nifty50").fetchone()[0]
out.close()
print(f"Done: {inserted:,} rows inserted, {total:,} total in {OUT_DB}")
