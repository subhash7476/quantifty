"""SFB Phase -1 / D1 — Upstox-based futures historical data ingestion.

Fetches daily OHLCV+OI candles for NSE FUT instruments via Upstox V3 API
and stores them in DuckDB. Uses the existing UpstoxClient + CredentialManager.

Requires: valid Upstox access token in config/credentials.json.
If token is expired, run: python scripts/auth_upstox_cli.py

Usage:
    python scripts/sfb/ingest_futures_upstox.py --from 2025-06-01 --to 2025-06-07
    python scripts/sfb/ingest_futures_upstox.py --from 2025-01-01 --to 2025-12-31 --sleep 0.5
"""

import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import duckdb
from core.auth.credentials import credentials
from core.api.upstox_client import UpstoxClient

DB_PATH = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
INSTRUMENT_MASTER = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS futures_candles (
    instrument_key  VARCHAR   NOT NULL,
    tradingsymbol   VARCHAR,
    expiry_dt       DATE,
    timestamp       TIMESTAMP NOT NULL,
    open            DOUBLE,
    high            DOUBLE,
    low             DOUBLE,
    close           DOUBLE,
    volume          BIGINT,
    open_interest   BIGINT,
    ingested_at     TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (instrument_key, timestamp)
);
"""

INSERT_SQL = """
INSERT INTO futures_candles
    (instrument_key, tradingsymbol, expiry_dt,
     timestamp, open, high, low, close, volume, open_interest, ingested_at)
SELECT instrument_key, tradingsymbol, expiry_dt,
       timestamp, open, high, low, close, volume, open_interest, ?
FROM df
ON CONFLICT (instrument_key, timestamp) DO UPDATE SET
    open          = EXCLUDED.open,
    high          = EXCLUDED.high,
    low           = EXCLUDED.low,
    close         = EXCLUDED.close,
    volume        = EXCLUDED.volume,
    open_interest = EXCLUDED.open_interest,
    ingested_at   = ?
"""


def get_fut_instruments():
    """Return list of (instrument_key, tradingsymbol, expiry) for NSE_FO FUT."""
    if not INSTRUMENT_MASTER.exists():
        print("Instrument master not found. Run: python scripts/fetch_instrument_master.py")
        return []
    con = duckdb.connect(str(INSTRUMENT_MASTER))
    rows = con.execute("""
        SELECT instrument_key, tradingsymbol, expiry
        FROM instruments
        WHERE instrument_type = 'FUT'
          AND exchange = 'NSE_FO'
        ORDER BY tradingsymbol, expiry
    """).fetchall()
    con.close()
    return [(r[0], r[1], r[2]) for r in rows]


def _parse_date(v):
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%b-%y"):
        try:
            return datetime.strptime(v.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date: {v!r}")


def main():
    import argparse, pandas as pd

    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_date", type=_parse_date,
                    default=date.today() - timedelta(days=7))
    ap.add_argument("--to", dest="to_date", type=_parse_date,
                    default=date.today() - timedelta(days=1))
    ap.add_argument("--sleep", type=float, default=0.3,
                    help="Delay between API calls (seconds)")
    ap.add_argument("--limit", type=int, default=0,
                    help="Limit to first N instruments (0 = all)")
    args = ap.parse_args()

    # Auth
    token = credentials.get("access_token")
    if not token:
        print("No access token found in config/credentials.json.")
        print("Run: python scripts/auth_upstox_cli.py")
        return
    client = UpstoxClient(token)

    # Instruments
    instruments = get_fut_instruments()
    if args.limit > 0:
        instruments = instruments[:args.limit]
    print(f"FUT instruments: {len(instruments)}")
    if not instruments:
        return

    # DB
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute(SCHEMA_SQL)

    to_str = args.to_date.strftime("%Y-%m-%d")
    from_str = args.from_date.strftime("%Y-%m-%d")
    total_candles = 0
    total_instruments = 0
    errors = 0

    print(f"Fetching {from_str} to {to_str} ({args.sleep}s delay)...")
    t0 = time.time()

    for i, (key, symbol, expiry) in enumerate(instruments):
        if i > 0 and i % 50 == 0:
            elapsed = time.time() - t0
            rate = total_candles / max(elapsed, 1)
            print(f"  {i}/{len(instruments)} | {total_candles} candles | "
                  f"{rate:.0f} candles/s | {errors} errors")

        try:
            candles = client.fetch_historical_candles_v3(
                instrument_key=key,
                unit="days",
                interval=1,
                to_date=to_str,
                from_date=from_str,
            )
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  [{key}] API error: {e}", file=sys.stderr)
            time.sleep(args.sleep)
            continue

        if not candles:
            time.sleep(args.sleep)
            continue

        # Parse expiry from the master (YYYY-MM-DD string)
        expiry_dt = _parse_date(expiry) if expiry else None

        rows = []
        for c in candles:
            rows.append({
                "instrument_key": key,
                "tradingsymbol": symbol,
                "expiry_dt": expiry_dt,
                "timestamp": c["timestamp"],
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
                "volume": c["volume"],
                "open_interest": c.get("open_interest"),
            })

        df = pd.DataFrame(rows).drop_duplicates(
            subset=["instrument_key", "timestamp"], keep="last")
        now = datetime.now()
        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(INSERT_SQL, [now, now])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            errors += 1
            if errors <= 5:
                print(f"  [{key}] DB insert error", file=sys.stderr)
            time.sleep(args.sleep)
            continue

        total_candles += len(rows)
        total_instruments += 1
        time.sleep(args.sleep)

    con.close()

    # Stats
    con = duckdb.connect(str(DB_PATH))
    r = con.execute(
        "SELECT COUNT(1), MIN(timestamp), MAX(timestamp) FROM futures_candles"
    ).fetchone()
    n_keys = con.execute(
        "SELECT COUNT(DISTINCT instrument_key) FROM futures_candles"
    ).fetchone()[0]
    con.close()

    elapsed = time.time() - t0
    print()
    print("=" * 56)
    print("INGESTION COMPLETE")
    print("=" * 56)
    print(f"Date range:       {from_str} to {to_str}")
    print(f"Candles inserted: {total_candles:,}")
    print(f"Instruments:      {total_instruments}")
    print(f"Errors:           {errors}")
    print(f"Store:            {r[0]:,} rows, {r[1]} to {r[2]}")
    print(f"Distinct keys:    {n_keys}")
    print(f"Time:             {elapsed:.1f}s")
    print(f"Rate:             {total_candles / max(elapsed, 1):.1f} candles/s")


if __name__ == "__main__":
    main()
