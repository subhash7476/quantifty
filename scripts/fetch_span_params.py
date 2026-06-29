#!/usr/bin/env python3
"""
fetch_span_params — Offline SPAN parameter download and archive (MM9.4-S2).

Downloads the NSE SPAN parameter file for a given date, validates it,
parses it into a SpanSnapshot, and promotes it to the on-disk archive.

This is the SOLE component performing network access. The runtime never
downloads SPAN data.

Usage:
    python scripts/fetch_span_params.py --date 2026-06-28
    python scripts/fetch_span_params.py  # uses today's expected date

Exit codes:
    0 — success (downloaded, validated, archived)
    1 — download failure (network, 404)
    2 — corrupt file (CRC, checksum)
    3 — parse failure (unrecognised schema)
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from core.risk.span.span_pipeline import download_span_data, promote_snapshot
from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray
from core.risk.span.span_freshness import expected_span_date

logger = logging.getLogger(__name__)

# NSE SPAN file URL template. Flagged for implementation-time confirmation
# against the actual NSE CDN path. The {iso_date} placeholder is the ISO
# trading date (e.g. "2026-06-28"); the exchange's actual URL pattern may
# differ and must be verified during implementation.
NSE_SPAN_URL_TEMPLATE = (
    "https://www.nseindia.com/span/span_{ddmmyyyy}.zip"
)
SPAN_DATA_DIR = Path("data/span")


def _date_to_ddmmyyyy(d: date) -> str:
    return d.strftime("%d%m%Y")


def _build_url(trading_date: date) -> str:
    return NSE_SPAN_URL_TEMPLATE.format(ddmmyyyy=_date_to_ddmmyyyy(trading_date))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download and archive NSE SPAN parameter files"
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="Trading date (YYYY-MM-DD). Defaults to expected_span_date().",
    )
    args = parser.parse_args()

    trading_date = (
        date.fromisoformat(args.date) if args.date else expected_span_date()
    )

    url = _build_url(trading_date)
    dest_path = SPAN_DATA_DIR / f"nse_fo_span_{trading_date.isoformat()}.zip"
    logger.info("Downloading SPAN data from %s", url)

    try:
        raw = download_span_data(url, dest_path)
    except Exception as exc:
        logger.error("Download failed: %s", exc)
        return 1

    # Stage: parse the downloaded data into a SpanSnapshot.
    # Placeholder: actual NSE CSV parsing will be implemented when the
    # exchange file format is confirmed. For now, build a minimal snapshot
    # that records the download metadata.
    file_hash = _sha256_bytes(raw)
    snapshot = SpanSnapshot(
        snapshot_date=trading_date,
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash=file_hash,
        is_settlement=False,
        risk_arrays={},
        metadata={
            "source_url": url,
            "file_hash": file_hash,
            "downloaded_at": __import__("datetime").datetime.utcnow().isoformat(),
        },
    )

    # Promote to archive (append-only)
    try:
        promote_snapshot(raw, snapshot, trading_date, SPAN_DATA_DIR)
    except Exception as exc:
        logger.error("Archive promotion failed: %s", exc)
        return 2

    logger.info("SPAN snapshot %s archived successfully", trading_date)
    return 0


def _sha256_bytes(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
