"""
SPAN On-Disk Repository (MM9.4-S2).

Read-only access to archived SPAN snapshots. The repository:
  - Reads serialised SpanSnapshot objects from .parquet files.
  - Verifies integrity by comparing the companion .zip's SHA-256 against
    the snapshot's stored file_hash.
  - Never downloads, refreshes, caches, or mutates data.

The repository owns nothing — it returns immutable values on each call.
"""

import hashlib
import logging
import pickle
from datetime import date
from pathlib import Path
from typing import Optional

from core.risk.span.span_snapshot import SpanSnapshot

logger = logging.getLogger(__name__)

# Default archive directory for SPAN snapshots.
SPAN_DATA_DIR = Path("data/span")


def _snapshot_path(archive_dir: Path, d: date) -> Path:
    fname = f"nse_fo_span_{d.isoformat()}"
    return archive_dir / f"{fname}.parquet"


def _zip_path(archive_dir: Path, d: date) -> Path:
    fname = f"nse_fo_span_{d.isoformat()}"
    return archive_dir / f"{fname}.zip"


class SpanRepository:
    """Read-only repository for archived SPAN snapshots.

    Args:
        data_dir: Directory containing .parquet and .zip snapshot pairs.
                  Defaults to SPAN_DATA_DIR.
    """

    def __init__(self, data_dir: Path = SPAN_DATA_DIR):
        self._data_dir = data_dir

    def latest_version(self) -> Optional[date]:
        """Return the most recent snapshot date, or None if the archive is empty."""
        dates = []
        for path in self._data_dir.glob("nse_fo_span_*.parquet"):
            stem = path.stem  # e.g. "nse_fo_span_2026-06-28"
            date_str = stem.replace("nse_fo_span_", "")
            try:
                dates.append(date.fromisoformat(date_str))
            except ValueError:
                logger.warning("Ignoring file with unparseable date: %s", path)
        return max(dates) if dates else None

    def load(self, version: date) -> SpanSnapshot:
        """Load a specific snapshot version.

        Reads the .parquet file, verifies the companion .zip checksum, and
        returns the immutable SpanSnapshot.

        Args:
            version: The snapshot date to load.

        Returns:
            A fully-populated SpanSnapshot.

        Raises:
            FileNotFoundError: If the .parquet file does not exist.
            ValueError:        If the companion .zip checksum does not match
                               the stored file_hash.
        """
        p_path = _snapshot_path(self._data_dir, version)
        if not p_path.exists():
            raise FileNotFoundError(
                f"No SPAN snapshot found for {version} at {p_path}"
            )

        with open(p_path, "rb") as f:
            snapshot: SpanSnapshot = pickle.load(f)

        # Verify integrity against companion .zip
        z_path = _zip_path(self._data_dir, version)
        if z_path.exists():
            actual_hash = _sha256_file(z_path)
            if actual_hash != snapshot.file_hash:
                raise ValueError(
                    f"SPAN snapshot {version} checksum mismatch: "
                    f"expected {snapshot.file_hash}, got {actual_hash}"
                )
        else:
            logger.warning(
                "No companion .zip found for %s; skipping checksum verification",
                version,
            )

        return snapshot


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
