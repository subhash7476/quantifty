"""SFB Phase -1 / D1 — NSE F&O historical data ingestion via nsepython.

Replaces the old archive-URL scraping approach (legacy + UDiFF dual-format,
.404 markers, raw file cache). Uses nsepython.derivative_history() as the sole
fetcher — NSE's direct historical F&O API, single format across all eras.

Sources (underlying, expiry) pairs from the instrument master
(data/instruments/nse_fo_instruments.duckdb). Fetches each pair's full history
in the target date range via polite-paced API calls.

Grain: one row per (underlying, expiry_date, trade_date). Preserves all expiries.

Usage:
    python scripts/sfb/ingest_futures_bhavcopy.py
    python scripts/sfb/ingest_futures_bhavcopy.py --start 2012-01-01 --end 2022-12-31
"""

import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
INSTRUMENT_MASTER = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"

DEFAULT_START = date(2012, 1, 1)
DEFAULT_END = date(2025, 12, 31)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS futures_bhavcopy (
    underlying    VARCHAR   NOT NULL,
    expiry_dt     DATE      NOT NULL,
    trade_date    DATE      NOT NULL,
    inst_type     VARCHAR   NOT NULL,
    open          DOUBLE,
    high          DOUBLE,
    low           DOUBLE,
    close         DOUBLE,
    settle        DOUBLE,
    contracts     BIGINT,
    val_in_lakh   DOUBLE,
    open_int      BIGINT,
    chg_in_oi     BIGINT,
    ingested_at   TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (underlying, expiry_dt, trade_date)
);
CREATE TABLE IF NOT EXISTS ingest_meta (
    trade_date DATE PRIMARY KEY,
    source     VARCHAR
);
"""

INSERT_SQL = """
INSERT INTO futures_bhavcopy
    (underlying, expiry_dt, trade_date, inst_type, open, high, low, close,
     settle, contracts, val_in_lakh, open_int, chg_in_oi, ingested_at)
SELECT underlying, expiry_dt, trade_date, inst_type, open, high, low, close,
       settle, contracts, val_in_lakh, open_int, chg_in_oi, ?
FROM df
ON CONFLICT (underlying, expiry_dt, trade_date) DO UPDATE SET
    inst_type   = EXCLUDED.inst_type,
    open        = EXCLUDED.open,
    high        = EXCLUDED.high,
    low         = EXCLUDED.low,
    close       = EXCLUDED.close,
    settle      = EXCLUDED.settle,
    contracts   = EXCLUDED.contracts,
    val_in_lakh = EXCLUDED.val_in_lakh,
    open_int    = EXCLUDED.open_int,
    chg_in_oi   = EXCLUDED.chg_in_oi,
    ingested_at = ?
"""


def nse_fetch(symbol, start_date, end_date, instrument_type, expiry_date):
    """Fetch F&O historical data via nsepython. Returns list of row dicts
    or None if the API is unavailable."""
    try:
        from nsepython import derivative_history
        payload = derivative_history(
            symbol=symbol,
            start_date=start_date.strftime("%d-%m-%Y"),
            end_date=end_date.strftime("%d-%m-%Y"),
            instrumentType=instrument_type,
            expiry_date=expiry_date.strftime("%d-%m-%Y"),
        )
        if payload is None or (isinstance(payload, list) and len(payload) == 0):
            return None
        return payload
    except Exception as exc:
        return exc


def _parse_date(val: str) -> date:
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%b-%y"):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date: {val!r}")


def _f(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _i(val):
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _map_payload_row(row, inst_type):
    """Map nsepython API payload row to DuckDB schema."""
    # FH_* key format from nsepython
    trade_date = _parse_date(row.get("FH_TIMESTAMP", ""))
    if trade_date is None:
        return None
    symbol = (row.get("FH_SYMBOL") or "").strip()
    expiry_dt = _parse_date(row.get("FH_EXPIRY_DT", row.get("EXPIRY_DT", "")))
    if not symbol or not expiry_dt:
        return None
    val_rupees = _f(row.get("FH_TOT_TRADED_VAL", row.get("TOT_TRADED_VAL", 0)))
    val_lakh = val_rupees / 100000.0 if val_rupees is not None else None
    return {
        "underlying": symbol,
        "expiry_dt": expiry_dt,
        "trade_date": trade_date,
        "inst_type": inst_type,
        "open": _f(row.get("FH_OPEN_PRICE", row.get("OPEN_PRICE", 0))),
        "high": _f(row.get("FH_HIGH_PRICE", row.get("HIGH_PRICE", 0))),
        "low": _f(row.get("FH_LOW_PRICE", row.get("LOW_PRICE", 0))),
        "close": _f(row.get("FH_CLOSE_PRICE", row.get("CLOSE_PRICE", 0))),
        "settle": _f(row.get("FH_SETTLE_PRICE", row.get("SETTLE_PRICE", 0))),
        "contracts": _i(row.get("FH_TRADED_QTY", row.get("TRADED_QTY", 0))),
        "val_in_lakh": val_lakh,
        "open_int": _i(row.get("FH_OPEN_INT", row.get("OPEN_INT", 0))),
        "chg_in_oi": _i(row.get("FH_CHG_IN_OI", row.get("CHG_IN_OI", 0))),
    }


def _get_fo_pairs(con, start_date, end_date, instrument_type):
    """Get (symbol, expiry_date) pairs from the instrument master that are
    active within the target date range."""
    try:
        im_con = duckdb.connect(str(INSTRUMENT_MASTER))
        rows = im_con.execute("""
            SELECT DISTINCT ts.symbol, MAX(t.expiry) AS expiry
            FROM tradingsymbols ts
            JOIN (
                SELECT tradingsymbol, MAX(expiry) AS expiry
                FROM tradingsymbols
                WHERE instrument_type = ? AND expiry BETWEEN ? AND ?
                GROUP BY tradingsymbol
            ) t ON t.tradingsymbol = ts.tradingsymbol
            WHERE ts.instrument_type = ?
            GROUP BY ts.symbol
            ORDER BY ts.symbol
        """, [instrument_type, start_date, end_date, instrument_type]).fetchall()
        im_con.close()
        return rows
    except Exception:
        return []


def _get_futstk_pairs_from_bhavcopy(con, start_date, end_date):
    """Fallback: get (underlying, expiry) pairs already in the bhavcopy store."""
    rows = con.execute("""
        SELECT DISTINCT underlying, expiry_dt
        FROM futures_bhavcopy
        WHERE inst_type = 'FUTSTK'
          AND trade_date BETWEEN ? AND ?
        ORDER BY underlying, expiry_dt
    """, [start_date, end_date]).fetchall()
    return rows


def ingest_all(con, start_date, end_date, sleep_s=0.5):
    """Ingest FUTSTK data for all available symbols in the date range.
    Returns (rows_inserted, errors)."""
    # Try instrument master first, fall back to bhavcopy pairs
    pairs = _get_fo_pairs(con, start_date, end_date, "FUTSTK")
    if not pairs:
        pairs = _get_fo_pairs(con, start_date, end_date, "FUTIDX")
    if not pairs:
        pairs = _get_futstk_pairs_from_bhavcopy(con, start_date, end_date)

    if not pairs:
        print("No F&O pairs found in instrument master. "
              "Run fetch_instrument_master.py first or use --fallback-pairs.")
        return 0, 0

    total = 0
    errors = 0
    n_skipped = 0

    for i, (symbol, expiry) in enumerate(pairs):
        if i % 50 == 0 and i > 0:
            print(f"Progress: {i}/{len(pairs)} symbols, "
                  f"{total:,} rows inserted, {errors} errors")

        result = nse_fetch(symbol, start_date, end_date, "FUTSTK", expiry)
        if result is None:
            continue
        if isinstance(result, Exception):
            errors += 1
            if errors == 1:
                print(f"API error (first): {type(result).__name__}: {result}")
            continue

        # Map and insert
        rows = []
        for row in (result if isinstance(result, list) else [result]):
            mapped = _map_payload_row(row, "FUTSTK")
            if mapped:
                rows.append(mapped)

        if not rows:
            continue

        df = pd.DataFrame(rows)
        df = df.drop_duplicates(
            subset=["underlying", "expiry_dt", "trade_date"], keep="last")
        now_ts = datetime.now()

        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(INSERT_SQL, [now_ts, now_ts])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            errors += 1
            continue

        total += len(df)
        time.sleep(sleep_s)

    return total, errors


def _ingest_fallback_from_cache(con, start_date, end_date):
    """Fallback: ingest from previously cached focal_*/foudiff_* zip files."""
    RAW_DIR = ROOT / "data" / "market_data" / "bhavcopy_raw"
    if not RAW_DIR.exists():
        return 0

    from ingest_futures_bhavcopy_legacy import ingest_day  # noqa
    total = 0
    for prefix in ("focal", "foudiff"):
        for f in sorted(RAW_DIR.glob(f"{prefix}_*.zip")):
            ds = f.stem.split("_", 1)[1]
            d = date(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))
            if d < start_date or d > end_date:
                continue
            existing = con.execute(
                "SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date = ?",
                [d]
            ).fetchone()[0]
            if existing > 0:
                continue
            n, _ = ingest_day(con, d)
            if n > 0:
                total += n
    return total


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=lambda s: _parse_date(s),
                    default=DEFAULT_START)
    ap.add_argument("--end", type=lambda s: _parse_date(s),
                    default=DEFAULT_END)
    ap.add_argument("--sleep", type=float, default=0.5,
                    help="Seconds between API calls")
    ap.add_argument("--fallback-cache", action="store_true",
                    help="Also ingest from cached focal_*/foudiff_* files")
    args = ap.parse_args()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))
    con.execute(SCHEMA_SQL)

    n, errs = ingest_all(con, args.start, args.end, sleep_s=args.sleep)

    if args.fallback_cache:
        cached = _ingest_fallback_from_cache(con, args.start, args.end)
        n += cached
        if cached:
            print(f"Fallback cache: {cached:,} rows")

    con.close()

    print()
    print("=" * 56)
    print("INGESTION SUMMARY")
    print("=" * 56)
    print(f"Span:          {args.start} -> {args.end}")
    print(f"Rows inserted: {n:,}")
    print(f"API errors:    {errs}")
    n_all = duckdb.connect(str(DB_PATH)).execute(
        "SELECT COUNT(*) FROM futures_bhavcopy"
    ).fetchone()[0]
    print(f"Total in DB:   {n_all:,}")


if __name__ == "__main__":
    main()
