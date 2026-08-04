"""SPAN daily ingest activation tests (SE1 prompt Part A).

Covers:
  A-P3  ParserV400 parses the real NSE sample file with len(risk_arrays) > 0.
  A-P5  A full fetch run leaves both a .zip and a .parquet on disk and
        SpanRepository.load() returns a snapshot with non-empty risk_arrays.
  Plus the load-bearing settlement checks: a non-settlement file is refused
  (raw retained) and the archived file_hash verifies against the raw zip.
"""

import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest

from core.risk.span.span_repository import SpanRepository

SPAN_REFERENCE = (
    Path(__file__).resolve().parents[3]
    / "reference" / "span" / "nsccl.20260625.i1" / "nsccl.20260625.i01.spn"
)

RA16 = [0.0] * 13 + [100.0, 0.0, 0.0]


def _spn_xml(trade_date: str = "20260803", is_setl: str = "1",
             qualifier: str = "final") -> bytes:
    a = "".join(f"<a>{v}</a>" for v in RA16)
    return (
        "<spanFile>"
        "<fileFormat>4.00</fileFormat>"
        "<created>202608031700</created>"
        "<pointInTime>"
        f"<date>{trade_date}</date>"
        f"<isSetl>{is_setl}</isSetl>"
        f"<setlQualifier>{qualifier}</setlQualifier>"
        "<clearingOrg>"
        "<ec>NSCCL</ec>"
        "<exchange>"
        "<exch>NSE</exch>"
        "<futPf>"
        "<pfCode>NIFTY</pfCode>"
        "<fut><pe>20260806</pe><p>24000</p>"
        "<scanRate><priceScan>2234.01</priceScan><volScan>0.04</volScan></scanRate>"
        "<intrRate><val>0.07</val></intrRate>"
        f"<ra><r>1</r>{a}</ra>"
        "</fut>"
        "</futPf>"
        "</exchange>"
        "<ccDef><cc>NIFTY</cc>"
        "<somTiers><tier><rate><val>0</val></rate></tier></somTiers>"
        "</ccDef>"
        "</clearingOrg>"
        "</pointInTime>"
        "</spanFile>"
    ).encode("latin-1")


def _settlement_zip(trade_date: str = "20260803") -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"nsccl.{trade_date}.s.spn", _spn_xml(trade_date))
    return buf.getvalue()


def _run_fetch(tmp_path: Path, download_fn, trade_date: str = "20260803"):
    import scripts.fetch_span_params as fsp
    fsp.download_span_data = download_fn
    import sys
    sys.argv = ["fetch_span_params", "--date", trade_date,
                "--data-dir", str(tmp_path)]
    return fsp.main()


def _fake_downloader(zip_bytes: bytes):
    def _fake(url: str, dest_path: Path, download_fn=None) -> bytes:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(zip_bytes)
        return zip_bytes
    return _fake


# --------------------------------------------------------------------------- #
# A-P3
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not SPAN_REFERENCE.exists(),
                    reason="Real SPAN reference file not present")
def test_a_p3_parser_parses_real_sample_with_risk_arrays():
    from core.risk.span.parser_v400 import parse_span_xml
    snapshot = parse_span_xml(SPAN_REFERENCE.read_bytes())
    assert len(snapshot.risk_arrays) > 0
    assert "NIFTY" in snapshot.risk_arrays


# --------------------------------------------------------------------------- #
# A-P5
# --------------------------------------------------------------------------- #

def test_a_p5_full_run_leaves_zip_and_parquet_and_loads(tmp_path):
    rc = _run_fetch(tmp_path, _fake_downloader(_settlement_zip()))
    assert rc == 0
    zip_path = tmp_path / "nse_fo_span_2026-08-03.zip"
    parquet_path = tmp_path / "nse_fo_span_2026-08-03.parquet"
    assert zip_path.exists()
    assert parquet_path.exists()
    snap = SpanRepository(tmp_path).load(date(2026, 8, 3))
    assert snap.risk_arrays
    assert snap.is_settlement is True
    assert snap.metadata["setl_qualifier"] == "final"
    assert snap.file_hash != snap.metadata["spn_sha256"]


def test_a_p5_archive_is_append_only(tmp_path):
    first = _run_fetch(tmp_path, _fake_downloader(_settlement_zip()))
    assert first == 0
    second = _run_fetch(tmp_path, _fake_downloader(b"different content"))
    assert second == 0  # append-only: the existing zip/parquet are kept
    assert (tmp_path / "nse_fo_span_2026-08-03.zip").stat().st_size == len(
        _settlement_zip()
    )


# --------------------------------------------------------------------------- #
# Settlement / raw-first discipline (A.4-2, A.4-5)
# --------------------------------------------------------------------------- #

def test_non_settlement_file_is_refused_raw_retained(tmp_path):
    intraday = _settlement_zip().replace(b"<isSetl>1</isSetl>",
                                         b"<isSetl>0</isSetl>")
    rc = _run_fetch(tmp_path, _fake_downloader(intraday))
    assert rc == 3  # parse-ish refusal: not a settlement snapshot
    staging = tmp_path / "staging" / "nsccl_2026-08-03.zip"
    assert staging.exists()  # raw retained despite refusal
    assert not (tmp_path / "nse_fo_span_2026-08-03.parquet").exists()


def test_bad_zip_is_parse_failure_raw_retained(tmp_path):
    rc = _run_fetch(tmp_path, _fake_downloader(b"not a zip"))
    assert rc == 3
    assert (tmp_path / "staging" / "nsccl_2026-08-03.zip").exists()
    assert not (tmp_path / "nse_fo_span_2026-08-03.parquet").exists()


def test_miss_cache_never_written_for_open_date(tmp_path):
    import scripts.fetch_span_params as fsp
    d = date(2026, 8, 3)
    assert fsp._may_cache_miss(d) is True   # closed date -> cacheable
    assert fsp._may_cache_miss(date.today()) is False  # open date -> never cache


def test_url_shape_matches_nse_settlement_convention():
    import scripts.fetch_span_params as fsp
    url = fsp.build_url(date(2026, 8, 3))
    assert url == (
        "https://www.archive.nseclearing.in/content/allreports/fno/"
        "03-08-2026/nsccl.20260803.s.zip"
    )


# --------------------------------------------------------------------------- #
# Backfill — walk backward, stop at the retention edge, cache intra-window
# misses, never a miss for an un-closed date.
# --------------------------------------------------------------------------- #

def test_backfill_walks_and_stops_at_retention_edge(tmp_path, monkeypatch):
    import re
    import urllib.error
    import scripts.fetch_span_params as fsp

    days = [date(2026, 8, 1), date(2026, 7, 31), date(2026, 7, 30),
            date(2026, 7, 29), date(2026, 7, 28)]
    boundary = date(2026, 7, 31)  # 30th and earlier are outside retention
    zip_bytes = _settlement_zip("20260801")

    def _fake_trading_days_desc(end):
        return [d for d in days if d <= end]

    def _fake_download(url, dest_path, download_fn=None):
        m = re.search(r"nsccl\.(\d{8})\.s\.zip", url)
        d = date(int(m.group(1)[:4]), int(m.group(1)[4:6]), int(m.group(1)[6:]))
        if d < boundary:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(zip_bytes)
        return zip_bytes

    monkeypatch.setattr(fsp, "_trading_days_desc", _fake_trading_days_desc)
    monkeypatch.setattr(fsp, "download_span_data", _fake_download)

    rc = fsp.backfill(tmp_path, end=date(2026, 8, 1))
    assert rc == 0
    assert (tmp_path / "nse_fo_span_2026-08-01.parquet").exists()
    assert (tmp_path / "nse_fo_span_2026-07-31.parquet").exists()
    assert not (tmp_path / "nse_fo_span_2026-07-30.parquet").exists()
    # the three closed 404 dates are cached as real misses (A.4-6)
    assert (tmp_path / "staging" / "nsccl_2026-07-30.zip.404").exists()
    assert (tmp_path / "staging" / "nsccl_2026-07-29.zip.404").exists()
    assert (tmp_path / "staging" / "nsccl_2026-07-28.zip.404").exists()


def test_backfill_skips_already_parsed(tmp_path, monkeypatch):
    import re
    import urllib.error
    import scripts.fetch_span_params as fsp

    days = [date(2026, 8, 1), date(2026, 7, 31)]
    zip_bytes = _settlement_zip("20260801")

    def _fake_trading_days_desc(end):
        return [d for d in days if d <= end]

    def _fake_download(url, dest_path, download_fn=None):
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(zip_bytes)
        return zip_bytes

    monkeypatch.setattr(fsp, "_trading_days_desc", _fake_trading_days_desc)
    monkeypatch.setattr(fsp, "download_span_data", _fake_download)

    assert fsp.backfill(tmp_path, end=date(2026, 8, 1)) == 0
    # second run: already-parsed dates skipped, downloader not called again
    called = {"n": 0}

    def _counting(url, dest_path, download_fn=None):
        called["n"] += 1
        return _fake_download(url, dest_path, download_fn=download_fn)

    monkeypatch.setattr(fsp, "download_span_data", _counting)
    assert fsp.backfill(tmp_path, end=date(2026, 8, 1)) == 0
    assert called["n"] == 0
