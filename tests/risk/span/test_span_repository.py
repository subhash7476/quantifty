"""Block I — SpanRepository latest/load/checksum (MM9.4-S2)."""

from datetime import date
from pathlib import Path

import pytest

from core.risk.span.span_repository import SpanRepository
from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray


def _write_fixture_snapshot(tmp_path: Path, snap: SpanSnapshot, zip_hash: str = ""):
    """Write a minimal .parquet fixture and companion .zip for testing."""
    import hashlib
    import pickle
    snap_dir = tmp_path / "span"
    snap_dir.mkdir(exist_ok=True)
    fname = f"nse_fo_span_{snap.snapshot_date.isoformat()}"
    parquet_path = snap_dir / f"{fname}.parquet"
    zip_path = snap_dir / f"{fname}.zip"
    # Serialise snapshot as pickle (stand-in for parquet; real path uses pyarrow)
    with open(parquet_path, "wb") as f:
        pickle.dump(snap, f)
    # Write companion zip with known content
    zip_content = b"fake zip content for " + snap.snapshot_date.isoformat().encode()
    with open(zip_path, "wb") as f:
        f.write(zip_content)
    return snap_dir, parquet_path, zip_path, hashlib.sha256(zip_content).hexdigest()


@pytest.fixture
def repo_with_snapshot(tmp_path):
    snap = SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash="",  # filled by _write_fixture
        risk_arrays={"NIFTY": SpanRiskArray("NIFTY", {"sr": 0.15})},
        metadata={},
    )
    snap_dir, _, _, actual_hash = _write_fixture_snapshot(tmp_path, snap)
    # Patch the hash
    snap_fixed = SpanSnapshot(
        snapshot_date=snap.snapshot_date,
        schema_version=snap.schema_version,
        exchange=snap.exchange,
        segment=snap.segment,
        file_hash=actual_hash,
        risk_arrays=snap.risk_arrays,
        metadata=snap.metadata,
    )
    # Overwrite with correct hash
    import pickle
    fname = f"nse_fo_span_{snap.snapshot_date.isoformat()}"
    with open(snap_dir / f"{fname}.parquet", "wb") as f:
        pickle.dump(snap_fixed, f)
    return SpanRepository(snap_dir)


def test_latest_version_returns_most_recent(tmp_path):
    snap_dir = tmp_path / "span"
    snap_dir.mkdir(exist_ok=True)
    for d in [date(2026, 6, 27), date(2026, 6, 28), date(2026, 6, 29)]:
        snap = SpanSnapshot(d, "v1", "NSE", "FO", "h", {}, {})
        import pickle
        fname = f"nse_fo_span_{d.isoformat()}.parquet"
        with open(snap_dir / fname, "wb") as f:
            pickle.dump(snap, f)
    repo = SpanRepository(snap_dir)
    assert repo.latest_version() == date(2026, 6, 29)


def test_latest_version_returns_none_when_empty(tmp_path):
    snap_dir = tmp_path / "span"
    snap_dir.mkdir(exist_ok=True)
    repo = SpanRepository(snap_dir)
    assert repo.latest_version() is None


def test_load_returns_snapshot(repo_with_snapshot):
    snap = repo_with_snapshot.load(date(2026, 6, 28))
    assert snap.snapshot_date == date(2026, 6, 28)
    assert snap.schema_version == "v1"
    assert "NIFTY" in snap.risk_arrays


def test_load_missing_raises(tmp_path):
    snap_dir = tmp_path / "span"
    snap_dir.mkdir(exist_ok=True)
    repo = SpanRepository(snap_dir)
    with pytest.raises(FileNotFoundError):
        repo.load(date(2026, 6, 28))


def test_load_checksum_mismatch_raises(tmp_path):
    snap = SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash="wrong_hash",
        risk_arrays={},
        metadata={},
    )
    snap_dir, _, _, _ = _write_fixture_snapshot(tmp_path, snap)
    repo = SpanRepository(snap_dir)
    with pytest.raises(ValueError, match="checksum mismatch"):
        repo.load(date(2026, 6, 28))


def test_load_no_zip_warns_and_succeeds(tmp_path):
    snap = SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash="some_hash",
        risk_arrays={},
        metadata={},
    )
    snap_dir, parquet_path, _, _ = _write_fixture_snapshot(tmp_path, snap)
    # Remove the .zip
    (snap_dir / f"nse_fo_span_2026-06-28.zip").unlink()
    repo = SpanRepository(snap_dir)
    # Should succeed (no zip to verify against)
    result = repo.load(date(2026, 6, 28))
    assert result.snapshot_date == date(2026, 6, 28)


def test_repository_does_not_cache(tmp_path):
    """Loading the same version twice returns independent copies."""
    snap = SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash="",
        risk_arrays={},
        metadata={},
    )
    snap_dir, _, _, actual_hash = _write_fixture_snapshot(tmp_path, snap)
    import pickle
    # Fix hash
    snap_fixed = SpanSnapshot(date(2026, 6, 28), "v1", "NSE", "FO", actual_hash, {}, {})
    with open(snap_dir / "nse_fo_span_2026-06-28.parquet", "wb") as f:
        pickle.dump(snap_fixed, f)
    repo = SpanRepository(snap_dir)
    a = repo.load(date(2026, 6, 28))
    b = repo.load(date(2026, 6, 28))
    assert a is not b  # different objects
    assert a == b  # same values
