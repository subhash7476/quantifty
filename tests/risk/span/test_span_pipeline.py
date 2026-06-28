"""Block L — fetch pipeline / archive management (MM9.4-S2)."""

from datetime import date
from pathlib import Path
from typing import Optional

from core.risk.span.span_pipeline import (
    download_span_data,
    promote_snapshot,
    latest_archive_date,
    list_archive_dates,
)


def test_download_injectable():
    """The download function is injectable — test with a no-op."""
    def _fake_download(url: str, dest: Path) -> bytes:
        return b"fake data"
    result = download_span_data(
        url="https://example.com/span.zip",
        dest_path=Path("/tmp/test.zip"),
        download_fn=_fake_download,
    )
    assert result == b"fake data"


def test_promote_snapshot_creates_parquet_and_zip(tmp_path):
    promote_snapshot(
        raw_bytes=b"fake zip content",
        parsed_snapshot={"date": "2026-06-28"},
        snapshot_date=date(2026, 6, 28),
        archive_dir=tmp_path,
    )
    assert (tmp_path / "nse_fo_span_2026-06-28.zip").exists()
    assert (tmp_path / "nse_fo_span_2026-06-28.parquet").exists()


def test_promote_does_not_overwrite(tmp_path):
    (tmp_path / "nse_fo_span_2026-06-28.zip").write_text("existing")
    promote_snapshot(
        raw_bytes=b"new content",
        parsed_snapshot={"date": "2026-06-28"},
        snapshot_date=date(2026, 6, 28),
        archive_dir=tmp_path,
    )
    assert (tmp_path / "nse_fo_span_2026-06-28.zip").read_text() == "existing"


def test_list_archive_dates(tmp_path):
    (tmp_path / "nse_fo_span_2026-06-27.parquet").write_text("")
    (tmp_path / "nse_fo_span_2026-06-28.parquet").write_text("")
    dates = list_archive_dates(tmp_path)
    assert date(2026, 6, 27) in dates
    assert date(2026, 6, 28) in dates


def test_latest_archive_date(tmp_path):
    (tmp_path / "nse_fo_span_2026-06-28.parquet").write_text("")
    result = latest_archive_date(tmp_path)
    assert result == date(2026, 6, 28)


def test_latest_archive_date_empty(tmp_path):
    assert latest_archive_date(tmp_path) is None
