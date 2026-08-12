"""
Ingest reference 1m Nifty + BankNifty CSVs into the per-date DuckDB 1m store.

Input:
  data/reference/NIFTY_2012-2023.csv.zip
  data/reference/BNF_2012-2023.csv.zip

Output:
  data/market_data/nse/candles/1m/{YYYY-MM-DD}.duckdb
  (upserts into existing files — skips dates already present)

The CSVs have 1-minute OHLC from 2012-01-02 to 2023-01-31 with no volume column.
July 2016 dates have ~750 bars (sub-minute ticks) — resampled to 1m.

Usage:
  python scripts/ingest_reference_1m.py
  python scripts/ingest_reference_1m.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REF_DIR = ROOT / "data" / "reference"
CANDLE_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"

NF_PATH = REF_DIR / "NIFTY_2012-2023.csv.zip"
BN_PATH  = REF_DIR / "BNF_2012-2023.csv.zip"

NF_SYMBOL = "NSE_INDEX|Nifty 50"
BN_SYMBOL = "NSE_INDEX|Nifty Bank"

TIMEFRAME = "1m"
SESSION_START = time(9, 15)
SESSION_END   = time(15, 30)
EXPECTED_BARS = 375  # 9:15 to 15:29 inclusive = 375 minutes


def parse_date(date_str: str) -> date:
    return date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))


def parse_timestamp(date_str: str, time_str: str) -> datetime:
    d = parse_date(date_str)
    parts = time_str.split(":")
    h, m = int(parts[0]), int(parts[1])
    return datetime(d.year, d.month, d.day, h, m)


def ingest_symbol(zip_path: Path, symbol: str, dry_run: bool = False) -> dict:
    """Ingest one symbol's CSV into per-date DuckDB files. Returns stats."""
    if not zip_path.exists():
        print(f"ERROR: {zip_path} not found")
        return {"status": "missing"}

    stats = {"dates_total": 0, "dates_ingested": 0, "dates_skipped": 0,
             "dates_existing": 0, "rows_total": 0}

    # Collect rows by date
    print(f"\nReading {zip_path.name} ...")
    date_bars: dict[date, list[dict]] = defaultdict(list)

    with zipfile.ZipFile(zip_path) as zf:
        inner = zf.namelist()[0]
        with zf.open(inner) as f:
            reader = csv.DictReader(f.read().decode("utf-8").splitlines())
            for row in reader:
                d = parse_date(row["Date"])
                date_bars[d].append({
                    "timestamp": parse_timestamp(row["Date"], row["Time"]),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                })

    stats["dates_total"] = len(date_bars)
    stats["rows_total"] = sum(len(v) for v in date_bars.values())
    print(f"  {stats['rows_total']} rows across {stats['dates_total']} dates")

    for d in sorted(date_bars):
        bars = date_bars[d]
        date_str = d.isoformat()

        # Skip if DuckDB already exists
        db_path = CANDLE_DIR / f"{date_str}.duckdb"
        if db_path.exists():
            # Check if this symbol already has rows
            try:
                con = duckdb.connect(str(db_path), read_only=True)
                existing = con.execute(
                    "SELECT COUNT(*) FROM candles WHERE symbol = ?", [symbol]
                ).fetchone()[0]
                con.close()
                if existing > 0:
                    stats["dates_existing"] += 1
                    continue
            except Exception:
                pass

        stats["dates_skipped"] += 1
        if dry_run:
            continue

        # Convert to DataFrame
        df = pd.DataFrame(bars)
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Resample to 1m if bars exceed expected OR have duplicate minute keys
        df["minute_bin"] = df["timestamp"].dt.floor("1min")
        dupes = df["minute_bin"].duplicated().sum()
        if dupes > 0:
            original_len = len(df)
            df = _resample_to_1m(df)
            if len(df) != original_len:
                print(f"    {date_str}: deduped {original_len} -> {len(df)} bars ({dupes} dupes)")

        df = df.drop(columns=["minute_bin"], errors="ignore")

        # Session-hour filter: 9:15 to 15:30
        hm = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
        df = df[(hm >= 555) & (hm <= 930)].reset_index(drop=True)

        if df.empty:
            continue

        # Add schema columns
        df["symbol"] = symbol
        df["timeframe"] = TIMEFRAME
        df["volume"] = 0
        df["is_synthetic"] = False

        # Reorder to match schema
        df = df[["symbol", "timeframe", "timestamp", "open", "high", "low",
                 "close", "volume", "is_synthetic"]]

        # Write or upsert
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            if db_path.exists():
                con = duckdb.connect(str(db_path))
                existing_syms = con.execute(
                    "SELECT DISTINCT symbol FROM candles"
                ).fetchall()
                existing_syms = {r[0] for r in existing_syms}
                if symbol in existing_syms:
                    con.execute("DELETE FROM candles WHERE symbol = ?", [symbol])
                con.execute("INSERT INTO candles SELECT * FROM df")
                con.close()
            else:
                con = duckdb.connect(str(db_path))
                con.execute("""
                    CREATE TABLE IF NOT EXISTS candles (
                        symbol        VARCHAR NOT NULL,
                        timeframe     VARCHAR NOT NULL,
                        timestamp     TIMESTAMP NOT NULL,
                        open          DOUBLE NOT NULL,
                        high          DOUBLE NOT NULL,
                        low           DOUBLE NOT NULL,
                        close         DOUBLE NOT NULL,
                        volume        BIGINT NOT NULL,
                        is_synthetic  BOOLEAN DEFAULT FALSE,
                        PRIMARY KEY (symbol, timeframe, timestamp)
                    )
                """)
                con.execute("INSERT INTO candles SELECT * FROM df")
                con.close()
            stats["dates_ingested"] += 1
        except Exception as exc:
            print(f"    ERROR {date_str}: {exc}")

    print(f"  Ingested: {stats['dates_ingested']}, "
          f"existing: {stats['dates_existing']}, "
          f"total: {stats['dates_total']}")
    return stats


def _resample_to_1m(df: pd.DataFrame) -> pd.DataFrame:
    """Resample sub-minute data to 1-minute OHLC bars."""
    df = df.copy()
    df["minute"] = df["timestamp"].dt.floor("1min")
    resampled = df.groupby("minute").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
    ).reset_index()
    resampled = resampled.rename(columns={"minute": "timestamp"})
    return resampled


def main():
    parser = argparse.ArgumentParser(description="Ingest reference 1m CSVs to DuckDB")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no writes")
    parser.add_argument("--symbol", choices=["nifty", "banknifty", "both"],
                        default="both", help="Which symbol to ingest")
    args = parser.parse_args()

    print("=" * 60)
    print("REFERENCE 1M INGEST -> DuckDB")
    print(f"Output: {CANDLE_DIR}")
    if args.dry_run:
        print("MODE: DRY RUN (no writes)")
    print("=" * 60)

    if args.symbol in ("nifty", "both"):
        ingest_symbol(NF_PATH, NF_SYMBOL, dry_run=args.dry_run)

    if args.symbol in ("banknifty", "both"):
        ingest_symbol(BN_PATH, BN_SYMBOL, dry_run=args.dry_run)

    print("\nDONE")


if __name__ == "__main__":
    main()
