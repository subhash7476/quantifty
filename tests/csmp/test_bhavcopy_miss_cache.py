"""A 404 is only evidence of absence for a date that has already closed.

One forward-probing run on 2026-07-09 wrote 289 permanent `.404` markers
covering every date through 2026-12-31, which silently suppressed equity
ingestion for months while the EOD chain kept reporting success.
"""
import sys
from datetime import date, timedelta
from importlib import import_module
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "csmp"))
ingest = import_module("ingest_equity_bhavcopy")

TODAY = date.today()
PAST = TODAY - timedelta(days=30)
FUTURE = TODAY + timedelta(days=30)


class _Resp:
    status_code = 404
    content = b""

    def raise_for_status(self):
        pass


class _Session:
    def __init__(self):
        self.calls = 0

    def get(self, url, timeout=None, **kw):
        self.calls += 1
        return _Resp()


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "RAW_DIR", tmp_path)
    return tmp_path


def test_may_cache_miss_rejects_future_date():
    assert ingest._may_cache_miss(FUTURE) is False


def test_may_cache_miss_rejects_today():
    assert ingest._may_cache_miss(TODAY) is False


def test_may_cache_miss_allows_closed_date():
    assert ingest._may_cache_miss(PAST) is True


def test_fetch_does_not_cache_404_for_future_date(raw_dir, monkeypatch):
    monkeypatch.setattr(ingest, "get_session", _Session)
    assert ingest.fetch("secfull", FUTURE) is None
    assert list(raw_dir.glob("*.404")) == []


def test_fetch_does_not_cache_404_for_today(raw_dir, monkeypatch):
    monkeypatch.setattr(ingest, "get_session", _Session)
    assert ingest.fetch("secfull", TODAY) is None
    assert list(raw_dir.glob("*.404")) == []


def test_fetch_still_caches_404_for_closed_date(raw_dir, monkeypatch):
    monkeypatch.setattr(ingest, "get_session", _Session)
    assert ingest.fetch("secfull", PAST) is None
    assert [p.name for p in raw_dir.glob("*.404")] == [
        f"secfull_{PAST.year}{PAST.month:02d}{PAST.day:02d}.404"
    ]


def test_cached_miss_short_circuits_the_fetch(raw_dir, monkeypatch):
    session = _Session()
    monkeypatch.setattr(ingest, "get_session", lambda: session)
    _, miss_path = ingest._raw_paths("secfull", PAST)
    miss_path.write_bytes(b"")
    assert ingest.fetch("secfull", PAST) is None
    assert session.calls == 0
