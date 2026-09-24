"""MRLC-test candle builder: resample equity 1m -> 1h / 4h / 1d per symbol. DISABLED.

**Refused (operator instruction 2026-09-13)**, for the same reason as
scanner.py: a rebuild re-reads the equity breadth 1m store up to today, which
would extend MRLC's signal-level consumption into the sessions that are still
unread. The existing store (2023-01-02 -> 2026-08-28) is unaffected and remains
readable.

Bars are built from 1m rows with is_synthetic = FALSE (CAS carry-forward excluded).
Session buckets anchor at 09:15 IST (NSE cash session start).
Output: data/mrlc_test/candles.duckdb with tables c1h, c4h, c1d.
"""
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ONE_MIN_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
OUT_DB = ROOT / "data" / "mrlc_test" / "candles.duckdb"
START = "2023-01-01"

_BUCKET_SQL = {
    "c1h": """
        INSERT INTO c1h
        SELECT symbol,
               date_trunc('day', timestamp) + INTERVAL '9 hours 15 minutes'
                   + INTERVAL '1 hour' * (floor((epoch(timestamp) - epoch(date_trunc('day', timestamp)
                       + INTERVAL '9 hours 15 minutes')) / 3600)) AS bucket_ts,
               arg_min(open, timestamp) AS open,
               max(high) AS high,
               min(low) AS low,
               arg_max(close, timestamp) AS close,
               sum(volume) AS volume
        FROM src.candles
        WHERE symbol LIKE 'NSE_EQ|%' AND NOT is_synthetic
        GROUP BY symbol, bucket_ts
    """,
    "c4h": """
        INSERT INTO c4h
        SELECT symbol,
               date_trunc('day', timestamp) + INTERVAL '9 hours 15 minutes'
                   + INTERVAL '4 hours' * (floor((epoch(timestamp) - epoch(date_trunc('day', timestamp)
                       + INTERVAL '9 hours 15 minutes')) / 14400)) AS bucket_ts,
               arg_min(open, timestamp) AS open,
               max(high) AS high,
               min(low) AS low,
               arg_max(close, timestamp) AS close,
               sum(volume) AS volume
        FROM src.candles
        WHERE symbol LIKE 'NSE_EQ|%' AND NOT is_synthetic
        GROUP BY symbol, bucket_ts
    """,
    "c1d": """
        INSERT INTO c1d
        SELECT symbol,
               date_trunc('day', timestamp) AS bucket_ts,
               arg_min(open, timestamp) AS open,
               max(high) AS high,
               min(low) AS low,
               arg_max(close, timestamp) AS close,
               sum(volume) AS volume
        FROM src.candles
        WHERE symbol LIKE 'NSE_EQ|%' AND NOT is_synthetic
        GROUP BY symbol, bucket_ts
    """,
}


def main():
    raise SystemExit(
        "REFUSED: MRLC candle rebuild is DISABLED (operator instruction 2026-09-13).\n"
        "It re-reads the equity breadth 1m store to the present, extending MRLC's\n"
        "signal-level consumption into sessions that are still unread.\n"
        "See docs/reports/index_research/PTMS_P3_WINDOW_RECONCILIATION_2026-09-13.md sec 2."
    )


def _main_disabled():
    if OUT_DB.exists():
        OUT_DB.unlink()
    con = duckdb.connect(str(OUT_DB))
    con.execute("CREATE TABLE c1h (symbol VARCHAR, ts TIMESTAMP, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")
    con.execute("CREATE TABLE c4h (symbol VARCHAR, ts TIMESTAMP, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")
    con.execute("CREATE TABLE c1d (symbol VARCHAR, ts TIMESTAMP, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")

    files = sorted(ONE_MIN_DIR.glob("*.duckdb"))
    done = 0
    for f in files:
        d = f.stem
        if d < START:
            continue
        try:
            con.execute(f"ATTACH '{f.as_posix()}' AS src (READ_ONLY)")
            for table, sql in _BUCKET_SQL.items():
                con.execute(sql)
            con.execute("DETACH src")
        except Exception as exc:
            print(f"  !! {d}: {exc}")
        done += 1
        if done % 100 == 0:
            print(f"  processed {done} date files")

    for table in ("c1h", "c4h", "c1d"):
        n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        syms = con.execute(f"SELECT count(DISTINCT symbol) FROM {table}").fetchone()[0]
        span = con.execute(f"SELECT min(ts), max(ts) FROM {table}").fetchone()
        print(f"{table}: {n:,} bars, {syms} symbols, {span[0]} -> {span[1]}")
    con.close()


if __name__ == "__main__":
    main()
