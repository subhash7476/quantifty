#!/usr/bin/env python3
"""
Upstox Instrument Master — Daily Refresh
-----------------------------------------
Downloads the complete Upstox instruments JSON.GZ, filters for the segments the
platform trades or references (NSE_FO, MCX_FO, NSE_EQ, NSE_INDEX), and stores in
a local DuckDB for fast symbol lookup and as_of-aware resolution.

Run by the scheduled refresh job once per NSE trading day (08:30 IST). The CDN
fetch needs no authentication, so the refresh is decoupled from the OAuth session:
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
import shutil
import logging
import tempfile
import requests
import duckdb
import pyarrow as pa
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.database.utils.market_hours import MarketHours
from core.instruments.resolver import InstrumentResolver
from core.instruments.master_readiness import assess, ReadinessState

logger = logging.getLogger(__name__)

INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
DB_PATH = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"

# Segments the platform trades (FO/EQ) or references as an underlying (INDEX).
ACCEPTED_SEGMENTS = ("NSE_FO", "MCX_FO", "NSE_EQ", "NSE_INDEX")
# Derivative segments whose cleanly-typed shape the contract-shape guard asserts.
_DERIVATIVE_SEGMENTS = ("NSE_FO", "MCX_FO")
# The traded underlyings whose active expiry the refresh validates before publish.
DEFAULT_UNDERLYINGS = ("NIFTY", "BANKNIFTY")

# run_refresh exit codes (the OS scheduler surfaces a non-zero run as failed).
EXIT_OK = 0
EXIT_DOWNLOAD_ERROR = 1
EXIT_EMPTY = 2
EXIT_COVERAGE = 3

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
        # Per-snapshot DELETE+INSERT in one transaction: a failed INSERT rolls back
        # the DELETE, so a partial write never leaves a date's snapshot empty
        # (MASTER_MATERIALIZATION_POLICY.md §8#3).
        con.execute("BEGIN TRANSACTION")
        try:
            for sd in snapshot_dates:
                con.execute("DELETE FROM instruments WHERE snapshot_date = ?", [sd])
            con.execute(f"INSERT INTO instruments SELECT {', '.join(_COLUMNS)} FROM arrow_data")
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        con.execute(_CREATE_INDEX)
        return len(rows)
    finally:
        con.close()


@dataclass(frozen=True)
class RefreshResult:
    """Outcome of a validate-before-publish attempt. `reason` is 'published' on
    success, else why the snapshot was refused ('shape' | 'coverage' | 'absent' |
    'stale')."""
    published: bool
    reason: str
    rows_written: int
    snapshot_date: str


def ist_snapshot_date(now: Optional[datetime] = None) -> str:
    """The snapshot_date to stamp, computed in IST — never machine-local.

    The startup gate computes `expected_snapshot_date` in IST; stamping the
    snapshot off the machine-local clock would diverge by a day near the date
    boundary on an off-IST box and manufacture spurious staleness (MM.5
    operational finding #1)."""
    now = now or MarketHours.get_ist_now()
    return MarketHours.to_ist(now).date().isoformat()


def _contract_shape_ok(rows: list[dict]) -> bool:
    """The derivative segments must be cleanly typed CE/PE/FUT with options present
    — the upstream schema shift (0 OPTION rows) a date/coverage check alone misses
    (MM.5 source-contract guard). Vacuously true when the run carries no
    derivatives (the coverage step then BLOCKs an equity-only master)."""
    deriv_types = {r["instrument_type"] for r in rows
                   if r["exchange"] in _DERIVATIVE_SEGMENTS}
    if not deriv_types:
        return True
    if deriv_types - {"CE", "PE", "FUT"}:
        return False  # a stray type in a derivative segment — schema drift
    return {"CE", "PE"} <= deriv_types  # options must be present


def validate_and_publish(rows: list[dict], snapshot_date: str,
                         db_path: Path = DB_PATH, *,
                         underlyings: Iterable[str] = DEFAULT_UNDERLYINGS,
                         now: Optional[datetime] = None) -> RefreshResult:
    """Option A — stage → validate → promote. Write `rows` to a throwaway staging
    DB, validate coverage through the same resolver path the startup gate uses
    (`assess`), and only on success promote them to `db_path`. A bad download
    never replaces the prior good snapshot (MM.6_REFRESH_JOB_PLAN.md §4)."""
    now = now or MarketHours.get_ist_now()
    db_path = Path(db_path)

    if not _contract_shape_ok(rows):
        logger.error("Contract-shape guard failed — refusing to publish snapshot %s",
                     snapshot_date)
        return RefreshResult(False, "shape", 0, snapshot_date)

    staging_dir = Path(tempfile.mkdtemp(prefix="instr_master_stage_"))
    try:
        write_snapshot(rows, db_path=staging_dir / "staging.duckdb")
        verdict = assess(InstrumentResolver(db_path=staging_dir / "staging.duckdb"),
                         underlyings, now=now)
        if verdict.state is ReadinessState.BLOCK:
            logger.error("Coverage validation BLOCK(%s) for snapshot %s — refusing to "
                         "publish; prior snapshot preserved", verdict.reason, snapshot_date)
            return RefreshResult(False, verdict.reason or "coverage", 0, snapshot_date)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    count = write_snapshot(rows, db_path=db_path)
    logger.info("Instrument master snapshot %s published: %s rows in %s",
                snapshot_date, f"{count:,}", db_path)
    return RefreshResult(True, "published", count, snapshot_date)


def refresh(db_path: Path = DB_PATH, *,
            underlyings: Iterable[str] = DEFAULT_UNDERLYINGS,
            now: Optional[datetime] = None) -> int:
    """Download the master and publish today's snapshot if it validates. Returns
    rows written (0 if the parse was empty or validation refused). The OAuth
    backstop calls this with no args; the scheduled job uses `run_refresh`."""
    snapshot_date = ist_snapshot_date(now)
    rows = download_and_parse(snapshot_date)
    if not rows:
        logger.error("No rows parsed — aborting DB write")
        return 0
    return validate_and_publish(rows, snapshot_date, db_path,
                                underlyings=underlyings, now=now).rows_written


def run_refresh(db_path: Path = DB_PATH, *,
                now: Optional[datetime] = None,
                underlyings: Iterable[str] = DEFAULT_UNDERLYINGS,
                download: Optional[Callable[[str], list[dict]]] = None) -> int:
    """The scheduled-job entry point: trading-day guard → download → validate →
    publish, returning an exit code (0 ok/skip; non-zero = failure the OS scheduler
    surfaces). Every failure leaves the prior snapshot intact. `download` is
    injectable for tests; production uses `download_and_parse`."""
    now = now or MarketHours.get_ist_now()
    if not MarketHours.is_trading_day(now):
        logger.info("Non-trading day (%s) — skipping instrument-master refresh",
                    ist_snapshot_date(now))
        return EXIT_OK

    snapshot_date = ist_snapshot_date(now)
    download = download or download_and_parse
    try:
        rows = download(snapshot_date)
    except Exception as exc:
        logger.error("Instrument-master download failed: %s — prior snapshot preserved", exc)
        return EXIT_DOWNLOAD_ERROR
    if not rows:
        logger.error("Empty parse — prior snapshot preserved")
        return EXIT_EMPTY

    result = validate_and_publish(rows, snapshot_date, db_path,
                                  underlyings=underlyings, now=now)
    return EXIT_OK if result.published else EXIT_COVERAGE


def get_db_path() -> Path:
    return DB_PATH


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    rc = run_refresh()
    sys.exit(rc)
