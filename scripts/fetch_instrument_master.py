#!/usr/bin/env python3
"""
Upstox Instrument Master — Daily Refresh
-----------------------------------------
Downloads the complete Upstox instruments JSON.GZ, filters for the segments the
platform trades or references (NSE_FO, MCX_FO, NSE_EQ, NSE_INDEX), and stores in
a local DuckDB for fast symbol lookup and as_of-aware resolution.

Run once after OAuth login each morning:
    python scripts/fetch_instrument_master.py

Source:
    https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz

Output:
    data/instruments/nse_fo_instruments.duckdb
    Table: instruments(instrument_key, tradingsymbol, name, expiry, strike,
                       instrument_type, lot_size, exchange, isin, tick_size,
                       snapshot_date)
    PK: (instrument_key, snapshot_date)  — each daily run appends a snapshot, so
        contract attributes that change over time (e.g. the post-2024 SEBI lot
        revision) can be resolved as_of a date (see CANONICAL_INSTRUMENT_ARCHITECTURE.md §D7.4).
"""
import sys
import gzip
import json
import logging
import requests
import duckdb
import pyarrow as pa
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
DB_PATH = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"

# Segments the platform trades (FO/EQ) or references as an underlying (INDEX).
ACCEPTED_SEGMENTS = ("NSE_FO", "MCX_FO", "NSE_EQ", "NSE_INDEX")

_COLUMNS = (
    "instrument_key", "tradingsymbol", "name", "expiry", "strike",
    "instrument_type", "lot_size", "exchange", "isin", "tick_size",
    "snapshot_date",
)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS instruments (
    instrument_key  TEXT NOT NULL,
    tradingsymbol   TEXT NOT NULL,
    name            TEXT,
    expiry          TEXT,
    strike          DOUBLE,
    instrument_type TEXT,
    lot_size        INTEGER,
    exchange        TEXT,
    isin            TEXT,
    tick_size       DOUBLE,
    snapshot_date   TEXT NOT NULL,
    PRIMARY KEY (instrument_key, snapshot_date)
);
"""

_CREATE_INDEX = "CREATE INDEX IF NOT EXISTS idx_tradingsymbol ON instruments (tradingsymbol);"


def _parse_expiry(raw) -> str | None:
    """Convert Upstox expiry field (ms timestamp or date string) to YYYY-MM-DD."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)) and raw > 0:
        try:
            return datetime.utcfromtimestamp(raw / 1000).strftime("%Y-%m-%d")
        except Exception:
            return None
    if isinstance(raw, str) and raw:
        # Accept ISO date or datetime strings
        return raw[:10]
    return None


def parse_instruments(raw_items: list[dict], snapshot_date: str) -> list[dict]:
    """Filter the raw Upstox master to accepted segments and normalise each row.

    Pure (no I/O). Stamps every row with `snapshot_date` so successive daily runs
    accumulate point-in-time history. Extracts isin + tick_size (absent in the
    previous schema).
    """
    rows = []
    for item in raw_items:
        # Accept both 'segment' and 'exchange' as the segment identifier
        segment = item.get("segment") or item.get("exchange", "")
        if segment not in ACCEPTED_SEGMENTS:
            continue

        ikey = item.get("instrument_key") or item.get("key")
        if not ikey:
            continue

        itype = (
            item.get("instrument_type")
            or item.get("option_type")
            or ""
        ).upper()

        expiry_raw = item.get("expiry") or item.get("expiry_date")
        strike = item.get("strike_price") or item.get("strike") or 0.0
        isin = item.get("isin") or None
        # NSE_EQ instrument keys embed the ISIN: "NSE_EQ|INE002A01018"
        if isin is None and segment == "NSE_EQ" and "|" in ikey:
            candidate = ikey.split("|", 1)[1]
            if candidate.startswith("INE"):
                isin = candidate

        rows.append({
            "instrument_key":  ikey,
            "tradingsymbol":   item.get("tradingsymbol") or item.get("trading_symbol") or "",
            "name":            item.get("name") or "",
            "expiry":          _parse_expiry(expiry_raw),
            "strike":          float(strike) if strike else 0.0,
            "instrument_type": itype,
            "lot_size":        int(item.get("lot_size") or 0),
            "exchange":        segment,
            "isin":            isin,
            "tick_size":       float(item.get("tick_size") or 0.0),
            "snapshot_date":   snapshot_date,
        })

    return rows


def download_and_parse(snapshot_date: str | None = None) -> list[dict]:
    """Download and decompress the Upstox master. Returns normalised accepted rows."""
    snapshot_date = snapshot_date or date.today().isoformat()
    logger.info(f"Downloading instrument master from {INSTRUMENTS_URL} ...")
    resp = requests.get(INSTRUMENTS_URL, timeout=60)
    resp.raise_for_status()

    raw_json = gzip.decompress(resp.content)
    instruments = json.loads(raw_json)
    logger.info(f"Total instruments in master: {len(instruments):,}")

    rows = parse_instruments(instruments, snapshot_date)
    logger.info(f"Instruments parsed (accepted segments): {len(rows):,}")
    return rows


def write_snapshot(rows: list[dict], db_path: Path = DB_PATH) -> int:
    """Append a snapshot to the local DuckDB. Returns rows written.

    Idempotent within a snapshot_date (re-running the same day replaces that
    day's rows); preserves earlier snapshots so as_of resolution stays correct.
    """
    if not rows:
        return 0

    db_path.parent.mkdir(parents=True, exist_ok=True)
    arrow_data = pa.table({col: [r[col] for r in rows] for col in _COLUMNS})  # noqa: F841

    snapshot_dates = sorted({r["snapshot_date"] for r in rows})

    con = duckdb.connect(str(db_path))
    try:
        con.execute(_CREATE_TABLE)
        for sd in snapshot_dates:
            con.execute("DELETE FROM instruments WHERE snapshot_date = ?", [sd])
        con.execute(f"INSERT INTO instruments SELECT {', '.join(_COLUMNS)} FROM arrow_data")
        con.execute(_CREATE_INDEX)
        return len(rows)
    finally:
        con.close()


def refresh(db_path: Path = DB_PATH) -> int:
    """Download master and append today's snapshot. Returns rows written."""
    rows = download_and_parse()
    if not rows:
        logger.error("No rows parsed — aborting DB write")
        return 0
    count = write_snapshot(rows, db_path)
    logger.info(f"Instrument master snapshot written: {count:,} rows in {db_path}")
    return count


def get_db_path() -> Path:
    return DB_PATH


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    n = refresh()
    print(f"\nDone — {n:,} instruments stored at {DB_PATH}")
