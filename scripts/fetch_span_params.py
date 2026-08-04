#!/usr/bin/env python3
"""
fetch_span_params — Daily NSCCL SPAN settlement-file download and archive.

Downloads the end-of-day SPAN settlement parameter file (PC-SPAN 4.00 XML,
fileFormat "4.00") that NSE Clearing publishes per trading day, parses it
with the frozen ParserV400, and promotes it (raw .zip + parsed .parquet)
to the on-disk archive.

The raw .zip is written to a staging path BEFORE any parsing is attempted and
is never deleted on a parse failure: a missed day is lost forever, a re-parse
is not. The settlement file (``nsccl.{YYYYMMDD}.s.zip``) is the one SE-5 needs
— intraday snapshots (``i1``/``i2``/...) are deliberately not archived. The
``is_settlement`` flag is taken from the file's ``<isSetl>`` element, never
hardcoded; if the file NSE publishes under the ``.s`` name is not a settlement
file, the job exits non-zero after retaining the raw payload.

URL (empirically determined 2026-08-04, see
docs/reports/SPAN_INGEST_ACTIVATION_REPORT.md):
    https://www.archive.nseclearing.in/content/allreports/fno/{DD-MM-YYYY}/nsccl.{YYYYMMDD}.s.zip
The archive host requires a browser User-Agent (added to _default_download in
span_pipeline.py); bare requests are connection-reset.

Usage:
    python scripts/fetch_span_params.py --date 2026-06-25
    python scripts/fetch_span_params.py  # uses expected_span_date()

Exit codes:
    0 — success (downloaded, parsed, archived)
    1 — download failure (network error, or HTTP 404 for the requested date)
    2 — archive failure (promote / post-archive verification)
    3 — parse failure (raw retained) / file is not a settlement snapshot
"""

import argparse
import dataclasses
import io
import logging
import re
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.risk.span as span  # noqa: E402  (import registers ParserV400)
from core.risk.span.span_freshness import expected_span_date  # noqa: E402
from core.risk.span.span_pipeline import download_span_data, promote_snapshot  # noqa: E402
from core.risk.span.span_repository import SpanRepository  # noqa: E402

logger = logging.getLogger(__name__)

SPAN_DATA_DIR = Path("data/span")
SPAN_STAGING_DIR = SPAN_DATA_DIR / "staging"
EQUITY_DB = Path("data/market_data/equity_bhavcopy.duckdb")

# F&O end-of-day settlement SPAN file. {path_date} = DD-MM-YYYY (archive folder),
# {yyyymmdd} = YYYYMMDD (NSCCL file naming).
NSE_SPAN_URL_TEMPLATE = (
    "https://www.archive.nseclearing.in/content/allreports/fno/"
    "{path_date}/nsccl.{yyyymmdd}.s.zip"
)


def build_url(trading_date: date) -> str:
    """The settlement-file URL for a trading date."""
    return NSE_SPAN_URL_TEMPLATE.format(
        path_date=trading_date.strftime("%d-%m-%Y"),
        yyyymmdd=trading_date.strftime("%Y%m%d"),
    )


def _may_cache_miss(d: date) -> bool:
    """A 404 only proves absence once the date has closed.

    Before that it means "not published yet" — caching the marker would
    suppress a file that arrives later the same day (the pitfall-register
    family that wrote 289 permanent markers for future dates).
    """
    return d < date.today()


def fetch_raw(url: str, dest_path: Path, trading_date: date,
              download_fn=None):
    """Download raw zip bytes to dest_path; classify 404 as MISSING (None).

    Classifies a date MISSING only on HTTP 404 — never on a parse or write
    failure. Caches the miss only for dates that have already closed.
    Raises on any network error (transient; not cached, not MISSING).
    """
    import urllib.error

    if dest_path.exists():
        return dest_path.read_bytes()
    miss_path = dest_path.with_name(dest_path.name + ".404")
    if miss_path.exists():
        return None
    try:
        return download_span_data(url, dest_path, download_fn=download_fn)
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and _may_cache_miss(trading_date):
            miss_path.write_bytes(b"")
        return None


def extract_spn_bytes(zip_bytes: bytes):
    """Return (spn_bytes, inner_name) from the NSCCL zip.

    Raises ValueError if the archive does not contain exactly one .spn.
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        spn_names = [n for n in zf.namelist() if n.lower().endswith(".spn")]
        if len(spn_names) != 1:
            raise ValueError(
                f"archive must contain exactly one .spn, found {len(spn_names)}: "
                f"{[n for n in zf.namelist()][:10]}"
            )
        return zf.read(spn_names[0]), spn_names[0]


def _sha256_bytes(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _setl_qualifier(spn_bytes: bytes) -> str:
    m = re.search(rb"<setlQualifier>([^<]*)</setlQualifier>", spn_bytes)
    return m.group(1).decode("latin-1") if m else ""


BACKFILL_STOP_AFTER_MISSES = 3
BACKFILL_SKIP_PARSED = True


def archive_one_date(trading_date: date, archive_dir: Path,
                     download_fn=None) -> int:
    """Download, parse, and archive one trading date's settlement file.

    Shared by the daily run and the backfill. Returns the documented exit
    code (0 success, 1 source-absent, 2 promote/verify failure, 3 parse /
    not-settlement failure with the raw retained)."""
    staging_dir = archive_dir / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    url = build_url(trading_date)

    # Raw-first: write the zip to staging before any parse is attempted.
    staging_path = staging_dir / f"nsccl_{trading_date.isoformat()}.zip"
    raw = fetch_raw(url, staging_path, trading_date, download_fn)
    if raw is None:
        logger.error(
            "SPAN settlement file for %s: HTTP 404 (absent)%s",
            trading_date,
            "" if trading_date >= date.today() else " — cached as missing",
        )
        return 1

    logger.info("Downloaded %d bytes from %s", len(raw), url)

    # Parse via the frozen ParserV400 (registered under "4.00").
    try:
        spn_bytes, inner_name = extract_spn_bytes(raw)
        snapshot = span.parse_span_xml("4.00", spn_bytes)
    except (ValueError, zipfile.BadZipFile, span.UnsupportedSpanSchema) as exc:
        logger.error(
            "SPAN parse failed for %s: %s — raw zip retained at %s",
            trading_date, exc, staging_path,
        )
        return 3

    if not snapshot.is_settlement:
        logger.error(
            "SPAN file for %s is not a settlement snapshot (isSetl=0, "
            "qualifier=%r): SE-5 needs the settlement file. Raw zip retained "
            "at %s",
            trading_date, _setl_qualifier(spn_bytes), staging_path,
        )
        return 3

    # file_hash must be the hash of the ARCHIVED zip (SpanRepository.load
    # verifies the companion .zip against it). The parser hashes the .spn
    # bytes, so override with the zip hash; keep the .spn hash in metadata.
    setl_qualifier = _setl_qualifier(spn_bytes)
    snapshot = dataclasses.replace(
        snapshot,
        file_hash=_sha256_bytes(raw),
        metadata={
            **snapshot.metadata,
            "source_url": url,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "setl_qualifier": setl_qualifier,
            "inner_spn_name": inner_name,
            "zip_sha256": _sha256_bytes(raw),
            "spn_sha256": _sha256_bytes(spn_bytes),
        },
    )

    try:
        promote_snapshot(raw, snapshot, trading_date, archive_dir)
    except Exception as exc:  # noqa: BLE001 - promote failure is fatal to archive
        logger.error("Archive promotion failed for %s: %s", trading_date, exc)
        return 2

    # Asserted, not printed: a full run must leave a loadable archive.
    try:
        loaded = SpanRepository(archive_dir).load(trading_date)
        assert loaded.risk_arrays, "archived snapshot has empty risk_arrays"
    except Exception as exc:  # noqa: BLE001
        logger.error("Post-archive verification failed for %s: %s", trading_date, exc)
        return 2

    logger.info(
        "SPAN settlement snapshot %s archived (%d underlyings, isSetl=1)",
        trading_date, len(snapshot.risk_arrays),
    )
    return 0


def _archive_parquet_path(archive_dir: Path, d: date) -> Path:
    return archive_dir / f"nse_fo_span_{d.isoformat()}.parquet"


def _trading_days_desc(end: date) -> list:
    """Trading days <= end, newest first, from the equity store calendar.

    The equity bhavcopy calendar is the F&O trading calendar at month
    granularity; SPAN is published per F&O trading day."""
    import duckdb
    con = duckdb.connect(str(EQUITY_DB), read_only=True)
    try:
        rows = con.execute(
            "SELECT trade_date FROM trading_calendar WHERE trade_date <= ? "
            "ORDER BY trade_date DESC",
            [end],
        ).fetchall()
    finally:
        con.close()
    return [r[0] for r in rows]


def backfill(archive_dir: Path, end: date, start: date | None = None,
             download_fn=None) -> int:
    """Walk backward from `end` over trading days, archiving each settlement
    file, and stop at the retention edge (a run of consecutive 404s).

    A.4-6 discipline inside the walk: a 404 on a past trading day inside the
    window is a real miss (cached via the existing .404 marker); the run of
    misses that ends the walk is the retention boundary, reported separately
    from source gaps. Already-parsed dates are skipped (resumable)."""
    days = _trading_days_desc(end)
    if start is not None:
        days = [d for d in days if d >= start]

    counts = {"archived": 0, "skipped": 0, "missing": 0, "error": 0}
    consecutive_misses = 0
    boundary = None       # newest date confirmed absent (retention edge)
    last_success = None
    errors = []

    for d in days:
        if BACKFILL_SKIP_PARSED and _archive_parquet_path(archive_dir, d).exists():
            counts["skipped"] += 1
            print(f"{d.isoformat()} skipped", flush=True)
            continue
        rc = archive_one_date(d, archive_dir, download_fn)
        if rc == 0:
            counts["archived"] += 1
            consecutive_misses = 0
            last_success = d
            print(f"{d.isoformat()} archived", flush=True)
        elif rc == 1:
            counts["missing"] += 1
            consecutive_misses += 1
            print(f"{d.isoformat()} missing", flush=True)
            if consecutive_misses >= BACKFILL_STOP_AFTER_MISSES:
                boundary = d
                logger.warning(
                    "retention edge reached at %s after %d consecutive 404s; "
                    "stopping the walk",
                    d, consecutive_misses,
                )
                print(f"retention edge at {d.isoformat()} — stopping", flush=True)
                break
        else:
            counts["error"] += 1
            errors.append((d.isoformat(), rc))
            consecutive_misses = 0
            print(f"{d.isoformat()} ERROR rc={rc}", flush=True)

    print(f"backfill summary: {counts}")
    print(f"boundary bracket: first_absent={boundary}, last_present={last_success}")
    if errors:
        print(f"errors: {errors}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download and archive the daily NSCCL SPAN settlement file"
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="Trading date (YYYY-MM-DD). Defaults to expected_span_date().",
    )
    parser.add_argument(
        "--data-dir", type=str, default=str(SPAN_DATA_DIR),
        help="Archive directory (default: data/span).",
    )
    parser.add_argument(
        "--backfill", action="store_true",
        help="Walk backward from --date (default expected_span_date()) over "
             "trading days, archiving each settlement file until the "
             "retention edge. Resumable; already-parsed dates are skipped.",
    )
    parser.add_argument(
        "--start", type=str, default=None,
        help="With --backfill: oldest date to include (YYYY-MM-DD), for "
             "chunking the walk.",
    )
    args = parser.parse_args()

    archive_dir = Path(args.data_dir)
    trading_date = (
        date.fromisoformat(args.date) if args.date else expected_span_date()
    )

    if args.backfill:
        start = date.fromisoformat(args.start) if args.start else None
        return backfill(archive_dir, trading_date, start=start)

    return archive_one_date(trading_date, archive_dir)


if __name__ == "__main__":
    sys.exit(main())
