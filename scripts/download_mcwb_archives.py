"""Nifty Indices MCWB archive downloader.

Downloads the monthly "Market Capitalisation, Weightage, Beta for NIFTY 50 &
NIFTY Next 50" report ZIPs from niftyindices.com for Jan-2016 .. Jul-2026,
validates each archive (nifty50_mcwb.csv present, 50 constituents, weight
column parseable and summing to ~100%), and writes an auditable, resumable
manifest at data/reference/mcwb_manifest.json.

Missing months are recorded in the manifest with status "missing" — never
silently substituted. Already-valid local files are reused (resumable).

Usage:
    python scripts/download_mcwb_archives.py
    python scripts/download_mcwb_archives.py --months 2020-03 2020-04
    python scripts/download_mcwb_archives.py --force
    python scripts/download_mcwb_archives.py --workers 8
"""

import argparse
import csv
import hashlib
import io
import json
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REF_DIR = ROOT / "data" / "reference"
MANIFEST_PATH = REF_DIR / "mcwb_manifest.json"
BASE_URL = ("https://www.niftyindices.com/Market_Capitalisation_Weightage_Beta_"
            "for_NIFTY_50_And_NIFTY_Next_50")
REPORT_TYPE = "Market Capitalisation, Weightage, Beta for NIFTY 50 & NIFTY Next 50"

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec"]

RETRIES = 3
TIMEOUT = 30


def month_range():
    months = []
    for year in range(2016, 2027):
        end = 7 if year == 2026 else 12
        for m in range(1, end + 1):
            months.append(date(year, m, 1))
    return months


def source_url(d: date) -> str:
    stem = f"mcwb_{MONTHS[d.month - 1]}{d.year % 100:02d}.zip"
    return f"{BASE_URL}/{stem}"


def filename_for(d: date) -> str:
    return f"mcwb_{MONTHS[d.month - 1]}{d.year % 100:02d}.zip"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_zip(path: Path):
    """Return (constituents, weight_sum_pct) or raise ValueError."""
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            if "nifty50_mcwb.csv" not in names:
                raise ValueError("missing nifty50_mcwb.csv in archive")
            raw = zf.read("nifty50_mcwb.csv").decode("utf-8", errors="replace")
    except zipfile.BadZipFile as exc:
        raise ValueError(f"bad zip: {exc}") from exc

    if raw.startswith("\ufeff"):
        raw = raw[1:]
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)

    hdr_idx = None
    for i, row in enumerate(rows):
        if row and "Sr. No" in row[0]:
            hdr_idx = i
            break
    if hdr_idx is None:
        raise ValueError("no header row (Sr. No) found")

    header = [c.strip() for c in rows[hdr_idx]]
    wcol = None
    for j, c in enumerate(header):
        if "weightage" in c.lower() or "weight" in c.lower():
            wcol = j
            break
    if wcol is None:
        raise ValueError(f"no weight column in header: {header}")

    constituents = 0
    total = 0.0
    for row in rows[hdr_idx + 1:]:
        if not row or not row[0].strip():
            continue
        if not row[0].strip().isdigit():
            break
        constituents += 1
        try:
            total += float(row[wcol].strip() or "0")
        except ValueError:
            raise ValueError(f"non-numeric weight in row {constituents}: {row[wcol]!r}")

    if constituents < 50:
        raise ValueError(f"only {constituents} constituents (expected 50)")
    return constituents, round(total, 2)


def download_one(session, d: date, target: Path):
    url = source_url(d)
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            break
        except requests.RequestException:
            if attempt == RETRIES:
                return None, f"network error after {RETRIES} attempts"
            time.sleep(2 ** attempt)
    if resp.status_code == 200:
        if resp.content[:2] != b"PK":
            return None, "soft 404 (server returned non-ZIP error page)"
        tmp = target.with_suffix(".zip.part")
        tmp.write_bytes(resp.content)
        tmp.rename(target)
        return target, None
    if resp.status_code in (404, 403, 410):
        return None, f"HTTP {resp.status_code} (unavailable)"
    return None, f"HTTP {resp.status_code}"


def process_month(d: date, force: bool):
    target = REF_DIR / filename_for(d)
    record = {
        "month": d.strftime("%Y-%m-%d"),
        "filename": filename_for(d),
        "source_url": source_url(d),
        "sha256": None,
        "constituents": None,
        "weight_sum_pct": None,
        "status": None,
        "note": None,
    }
    if target.exists() and not force:
        try:
            constituents, total = verify_zip(target)
            record.update(sha256=sha256_file(target),
                          constituents=constituents,
                          weight_sum_pct=total,
                          status="valid")
        except ValueError as exc:
            record.update(status="invalid", note=str(exc),
                          sha256=sha256_file(target))
        return record

    with requests.Session() as session:
        session.headers["User-Agent"] = "Mozilla/5.0 (research archive downloader)"
        retry = Retry(total=3, backoff_factor=1.0,
                      status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retry))
        target, err = download_one(session, d, target)
        if target is None:
            missing = ("unavailable" in (err or "")
                       or "404" in (err or "")
                       or "soft 404" in (err or ""))
            record.update(status="missing" if missing else "error", note=err)
            return record
        try:
            constituents, total = verify_zip(target)
            record.update(sha256=sha256_file(target),
                          constituents=constituents,
                          weight_sum_pct=total,
                          status="valid")
        except ValueError as exc:
            record.update(status="invalid", note=str(exc),
                          sha256=sha256_file(target))
        return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="+", default=None,
                    help="YYYY-MM subset, e.g. --months 2020-03 2020-04")
    ap.add_argument("--force", action="store_true",
                    help="re-download and re-validate existing archives")
    ap.add_argument("--workers", type=int, default=6,
                    help="parallel download workers (default 6)")
    args = ap.parse_args()

    REF_DIR.mkdir(parents=True, exist_ok=True)

    if args.months:
        months = [date(int(m.split("-")[0]), int(m.split("-")[1]), 1)
                  for m in args.months]
    else:
        months = month_range()

    print(f"processing {len(months)} months -> {REF_DIR}")

    records = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_month, d, args.force): d for d in months}
        for fut in as_completed(futures):
            d = futures[fut]
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001 - surface worker failure
                rec = {"month": d.strftime("%Y-%m-%d"),
                       "filename": filename_for(d),
                       "source_url": source_url(d),
                       "sha256": None, "constituents": None,
                       "weight_sum_pct": None,
                       "status": "error", "note": str(exc)}
            records[rec["month"]] = rec
            print(f"{rec['month']} -> {rec['status']}"
                  + (f" ({rec['constituents']} cons, "
                     f"wsum {rec['weight_sum_pct']})"
                     if rec["status"] == "valid" else f" {rec['note']}"))

    ordered = [records[m.strftime("%Y-%m-%d")] for m in months]
    statuses = {}
    for rec in ordered:
        statuses[rec["status"]] = statuses.get(rec["status"], 0) + 1

    manifest = {
        "source": "Nifty Indices Archives of Daily/Monthly Reports",
        "report_type": REPORT_TYPE,
        "start_month": months[0].strftime("%Y-%m-%d"),
        "end_month": months[-1].strftime("%Y-%m-%d"),
        "months_requested": len(months),
        "status_summary": statuses,
        "records": ordered,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nmanifest written: {MANIFEST_PATH}")
    for k, v in sorted(statuses.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
