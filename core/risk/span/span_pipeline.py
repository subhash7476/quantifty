"""
SPAN Fetch Pipeline (MM9.4-S2).

Primitives for the offline download-and-archive pipeline. The fetch job
(scripts/fetch_span_params.py) uses these to download, validate, promote,
and archive SPAN parameter files.

The download function is injectable for testing. No runtime network I/O.
"""

import hashlib
import json
import logging
import pickle
from datetime import date
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray

logger = logging.getLogger(__name__)


def _default_download(url: str, dest: Path) -> bytes:
    """Real download via HTTP GET. Injectable for testing."""
    import urllib.request
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    return data


def download_span_data(
    url: str,
    dest_path: Path,
    download_fn: Optional[Callable[[str, Path], bytes]] = None,
) -> bytes:
    """Download SPAN parameter data from the given URL.

    Args:
        url:         The source URL.
        dest_path:   Path to write the downloaded file (for audit).
        download_fn: Injectable download function (default: HTTP GET).

    Returns:
        The raw downloaded bytes.
    """
    fn = download_fn or _default_download
    data = fn(url, dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(data)
    return data


def promote_snapshot(
    raw_bytes: bytes,
    parsed_snapshot: SpanSnapshot,
    snapshot_date: date,
    archive_dir: Path,
) -> None:
    """Promote a validated snapshot into the archive.

    Writes the raw ZIP and the parsed .parquet side-by-side. Never overwrites
    an existing valid snapshot (append-only).

    Args:
        raw_bytes:      The raw downloaded ZIP content.
        parsed_snapshot: The parsed SpanSnapshot.
        snapshot_date:   The snapshot's trading date.
        archive_dir:     The archive directory.
    """
    archive_dir.mkdir(parents=True, exist_ok=True)
    base = f"nse_fo_span_{snapshot_date.isoformat()}"
    zip_path = archive_dir / f"{base}.zip"
    parquet_path = archive_dir / f"{base}.parquet"

    # Append-only: skip any file that already exists
    if zip_path.exists():
        logger.info("Snapshot %s zip already archived; skipping", snapshot_date)
        return
    if parquet_path.exists():
        logger.info("Snapshot %s parquet already archived; skipping", snapshot_date)
        return

    with open(zip_path, "wb") as f:
        f.write(raw_bytes)
    with open(parquet_path, "wb") as f:
        pickle.dump(parsed_snapshot, f)

    logger.info("Promoted SPAN snapshot %s to archive", snapshot_date)


def list_archive_dates(archive_dir: Path) -> List[date]:
    """List all snapshot dates present in the archive."""
    dates = []
    for path in sorted(archive_dir.glob("nse_fo_span_*.parquet")):
        stem = path.stem
        date_str = stem.replace("nse_fo_span_", "")
        try:
            dates.append(date.fromisoformat(date_str))
        except ValueError:
            pass
    return dates


def latest_archive_date(archive_dir: Path) -> Optional[date]:
    """Return the most recent snapshot date in the archive, or None."""
    dates = list_archive_dates(archive_dir)
    return max(dates) if dates else None
