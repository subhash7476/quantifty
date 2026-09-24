"""Nifty Indices MCWB archive downloader.

Downloads the monthly "Market Capitalisation, Weightage, Beta for NIFTY 50 &
NIFTY Next 50" report ZIPs from niftyindices.com for Jan-2010 .. Jul-2026,
validates each archive (both legs present, 50 constituents each, weight
column parseable and summing to ~100%), and writes an auditable, resumable
manifest at data/reference/mcwb_manifest.json.

Era notes (verified by inspection):
- Modern era (Nov/Dec-2015 on): inner files nifty50_mcwb.csv and
  niftynext50_mcwb.csv at the zip root, plain-numeric weights.
- Legacy era (Jan-2010 .. Oct-2015): inner files niftymcwb.csv (S&P CNX
  Nifty) and jrniftymcwb.csv (CNX Nifty Junior, the Nifty Next 50
  predecessor). Folder prefixes, case, and suffixes vary by month
  (nested dirs, .csv.csv, _sep variants), weights carry '%' signs, and
  index titles are era-contemporary — match by containment, never prefix.
- Junior stems are tested before Nifty stems because 'niftymcwb' is a
  substring of 'jrniftymcwb'.

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
    for year in range(2010, 2027):
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


NIFTY50_STEMS = ("nifty50_mcwb", "niftymcwb")
NEXT50_STEMS = ("niftynext50", "jrniftymcwb")


def classify_inner(name):
    """'n50', 'next50', or None — by containment on the basename."""
    base = name.rsplit("/", 1)[-1].lower()
    if not base.endswith(".csv"):
        return None
    for stem in NEXT50_STEMS:
        if stem in base:
            return "next50"
    for stem in NIFTY50_STEMS:
        if stem in base:
            return "n50"
    return None


def parse_weight(text):
    """Legacy weights carry '%' and stray spaces; returns a float."""
    t = text.strip().rstrip("%").strip()
    if not t:
        return 0.0
    neg = t.startswith("(") and t.endswith(")")
    if neg:
        t = t[1:-1]
    v = float(t)
    return -v if neg else v


def parse_leg(raw):
    """(constituents, weight_sum, [tickers], placeholders) from inner CSV.

    Placeholder rows (weight '-' — e.g. NSE's DUMMYSIEMS dummy for the
    Siemens demerger, Apr/May-2025 Next 50 — or DUMMY* tickers with carved
    weights, e.g. the four Dummy Vedanta entities in Apr/May-2026) are
    skipped from membership and tallied separately. Padding/blank rows
    skipped; stops at footers.
    """
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)

    hdr_idx = None
    for i, row in enumerate(rows):
        if row and row[0].replace(" ", "").lower().startswith("sr.no"):
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
    tickers = []
    placeholders = []
    for row in rows[hdr_idx + 1:]:
        if not row or not row[0].strip():
            continue
        if not row[0].strip().isdigit():
            break
        wtext = row[wcol].strip() if len(row) > wcol else ""
        tick = row[1].strip() if len(row) > 1 else ""
        if wtext == "-" or tick.upper().startswith("DUMMY"):
            placeholders.append(tick or "?")
            continue
        constituents += 1
        try:
            total += parse_weight(wtext)
        except ValueError:
            raise ValueError(f"non-numeric weight in row {constituents}: {wtext!r}")
        tickers.append(tick)
    return constituents, round(total, 2), tickers, placeholders


def verify_zip(path: Path):
    """{leg: (inner_name, constituents, weight_sum, placeholders)}.

    Both legs required. Counts of 48..52 accepted: NSE genuinely runs
    49/51-member months (Tata DVR as 51st, Sep-Oct 2020 Next 50 at 49);
    anything else is invalid. Notes flag count != 50, non-pct-scale
    weights (Aug-2011), and placeholder rows.
    """
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            legs = {}
            for nm in sorted(names):
                leg = classify_inner(nm)
                if leg and leg not in legs:
                    legs[leg] = nm
            if "n50" not in legs:
                raise ValueError(f"no Nifty-50 leg in archive: {names}")
            if "next50" not in legs:
                raise ValueError(f"no Next-50/Junior leg in archive: {names}")
            out = {}
            for leg, nm in legs.items():
                raw = zf.read(nm).decode("utf-8", errors="replace")
                n, total, _, ph = parse_leg(raw)
                if not 48 <= n <= 52:
                    raise ValueError(f"{leg}: {n} constituents (expected ~50)")
                out[leg] = (nm, n, total, ph)
            return out
    except zipfile.BadZipFile as exc:
        raise ValueError(f"bad zip: {exc}") from exc


def read_leg_members(path: Path):
    """{leg: [ticker, ...]} in file order; validates via verify first."""
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        legs = {}
        for nm in sorted(names):
            leg = classify_inner(nm)
            if leg and leg not in legs:
                legs[leg] = nm
        out = {}
        for leg, nm in legs.items():
            raw = zf.read(nm).decode("utf-8", errors="replace")
            _, _, tickers, _ = parse_leg(raw)
            out[leg] = tickers
        return out


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
        "next50_constituents": None,
        "next50_weight_sum_pct": None,
        "schema": None,
        "status": None,
        "note": None,
    }

    def fill_valid(info):
        n50_inner, n, total, n50_ph = info["n50"]
        nx_inner, nx_n, nx_total, nx_ph = info["next50"]
        notes = []
        if n != 50:
            notes.append(f"n50 count {n}")
        if nx_n != 50:
            notes.append(f"next50 count {nx_n}")
        if not 95 <= total <= 105:
            notes.append(f"n50 weights not pct-scale (wsum {total})")
        if not 95 <= nx_total <= 105:
            notes.append(f"next50 weights not pct-scale (wsum {nx_total})")
        if n50_ph:
            notes.append(f"n50 placeholders skipped: {n50_ph}")
        if nx_ph:
            notes.append(f"next50 placeholders skipped: {nx_ph}")
        record.update(
            sha256=sha256_file(target),
            constituents=n,
            weight_sum_pct=total,
            next50_constituents=nx_n,
            next50_weight_sum_pct=nx_total,
            schema="modern" if n50_inner.rsplit("/", 1)[-1] == "nifty50_mcwb.csv" else "legacy",
            status="valid",
            note="; ".join(notes) or None)

    if target.exists() and not force:
        try:
            fill_valid(verify_zip(target))
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
            fill_valid(verify_zip(target))
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
                       "weight_sum_pct": None, "next50_constituents": None,
                       "next50_weight_sum_pct": None, "schema": None,
                       "status": "error", "note": str(exc)}
            records[rec["month"]] = rec
            print(f"{rec['month']} -> {rec['status']}"
                  + (f" ({rec['constituents']} cons, "
                     f"wsum {rec['weight_sum_pct']})"
                     if rec["status"] == "valid" else f" {rec['note']}"))

    ordered = [records[m.strftime("%Y-%m-%d")] for m in months]
    if args.months and MANIFEST_PATH.exists():
        # subset run: merge into the existing manifest, never clobber it.
        prior = {r["month"]: r
                 for r in json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["records"]}
        prior.update(records)
        full = sorted(prior)
        ordered = [prior[m] for m in full]
        start, end, n = full[0], full[-1], len(full)
    else:
        start, end, n = (months[0].strftime("%Y-%m-%d"),
                         months[-1].strftime("%Y-%m-%d"), len(months))
    statuses = {}
    for rec in ordered:
        statuses[rec["status"]] = statuses.get(rec["status"], 0) + 1

    manifest = {
        "source": "Nifty Indices Archives of Daily/Monthly Reports",
        "report_type": REPORT_TYPE,
        "start_month": start,
        "end_month": end,
        "months_requested": n,
        "status_summary": statuses,
        "records": ordered,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nmanifest written: {MANIFEST_PATH}")
    for k, v in sorted(statuses.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
