"""Download the NSE CF-CA equities corporate-action report into the raw CA archive.

The CA ingest (`ingest_corporate_actions.py`) reads pre-downloaded CF-CA CSVs from
`data/market_data/corporate_actions_raw/` but nothing in the repo fetched them — the
archive went stale at 2026-07-10 and 11 unregistered corporate actions reached the
four-arm contract suite as Arm A HALTs before anyone noticed.

Files are written with the archive's existing convention and non-overlapping ranges:

    CF-CA-equities-DD-MM-YYYY-to-DD-MM-YYYY.csv

Usage:
    python scripts/csmp/download_corporate_actions.py --from 11-07-2026 --to 12-09-2026
    python scripts/csmp/download_corporate_actions.py            # gap-fill to today
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "market_data" / "corporate_actions_raw"
API = "https://www.nseindia.com/api/corporates-corporateActions"
FMT = "%d-%m-%Y"
MAX_SPAN_DAYS = 365
NEWLINE = b"\n"
BOM = b"\xef\xbb\xbf"
HEADER = b'"SYMBOL"'


def _session():
    s = requests.Session()
    retry = Retry(total=4, backoff_factor=1.5,
                  status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/csv,application/json,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-actions",
    })
    s.get("https://www.nseindia.com", timeout=20)
    s.get("https://www.nseindia.com/companies-listing/corporate-filings-actions", timeout=20)
    return s


def _latest_archived_end() -> date:
    """Latest to_date already covered by a CF-CA file in the archive."""
    ends = []
    for p in RAW_DIR.glob("CF-CA-equities-*-to-*.csv"):
        try:
            ends.append(datetime.strptime(p.stem.split("-to-")[1], FMT).date())
        except ValueError:
            continue
    if not ends:
        sys.exit("No existing CF-CA file to continue from — pass --from explicitly.")
    return max(ends)


def fetch(frm: date, to: date) -> bytes:
    if (to - frm).days > MAX_SPAN_DAYS:
        sys.exit(f"Span {frm}..{to} exceeds {MAX_SPAN_DAYS} days; NSE rejects wide ranges.")
    s = _session()
    r = s.get(API, params={"index": "equities", "from_date": frm.strftime(FMT),
                           "to_date": to.strftime(FMT), "csv": "true"}, timeout=60)
    r.raise_for_status()
    # Raw bytes, never r.text: NSE declares no charset, so requests decodes the UTF-8 BOM
    # as latin-1 and re-encoding yields C3AF C2BB C2BF instead of EFBBBF — a double-encoded
    # BOM that mangles the first column name for every downstream reader.
    body = r.content
    if "text/html" in r.headers.get("Content-Type", "") or body.lstrip().startswith(b"<"):
        sys.exit("NSE returned an HTML shell, not CSV — the gate-(a) G4 failure mode. "
                 "Refusing to write a wrong-content file.")
    if body.count(NEWLINE) < 2:
        sys.exit(f"Response has no data rows ({len(body)} bytes) — refusing to write.")
    if not (body.startswith(BOM + HEADER) or body.startswith(HEADER)):
        sys.exit(f"Unexpected header bytes {body[:16]!r} — refusing to write.")
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm",
                    help="DD-MM-YYYY (default: day after the archive's latest end)")
    ap.add_argument("--to", dest="to", help="DD-MM-YYYY (default: today)")
    a = ap.parse_args()

    frm = datetime.strptime(a.frm, FMT).date() if a.frm else _latest_archived_end() + timedelta(days=1)
    to = datetime.strptime(a.to, FMT).date() if a.to else date.today()
    if frm > to:
        print(f"Archive already covers through {frm - timedelta(days=1)} — nothing to fetch.")
        return

    out = RAW_DIR / f"CF-CA-equities-{frm.strftime(FMT)}-to-{to.strftime(FMT)}.csv"
    if out.exists():
        sys.exit(f"{out.name} already exists — refusing to overwrite.")

    body = fetch(frm, to)
    out.write_bytes(body)
    n_rows = body.count(NEWLINE) - 1
    print(f"Wrote {out.name}: {len(body):,} bytes, {n_rows} rows ({frm} -> {to})")


if __name__ == "__main__":
    main()
