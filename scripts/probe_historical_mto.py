#!/usr/bin/env python3
"""Download historical MTO files from NSE static archive (2010–2020).

Read-only probe against NSE's MTO_DDMMYYYY.DAT archive on archives.nseindia.com.
Never touches the DuckDB store or the sealed window (2023-01-01 to 2026-07-09).
"""

import sys
import os
import time
import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://archives.nseindia.com/archives/equities/mto/MTO_{ddmmyyyy}.DAT"
OUTPUT_DIR = "data/mto_probe"
REQUEST_DELAY = 1.0
START_DATE = "2010-01-01"
END_DATE = "2020-12-31"

_SESSION = None


def get_session():
    global _SESSION
    if _SESSION is None:
        s = requests.Session()
        retry = Retry(total=4, backoff_factor=2.0,
                      status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=2,
                              pool_maxsize=2)
        s.mount("https://", adapter)
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
        })
        try:
            s.get("https://www.nseindia.com", timeout=20)
        except requests.RequestException:
            pass
        _SESSION = s
    return _SESSION


def is_html_block(resp):
    ct = resp.headers.get("Content-Type", "")
    if "text/html" in ct:
        return True
    body = resp.text.strip()
    return body.startswith("<!") or body.startswith("<html") or body.startswith("<HTML")


def trading_days(start, end):
    d = datetime.date.fromisoformat(start)
    end_d = datetime.date.fromisoformat(end)
    while d <= end_d:
        if d.weekday() < 5:
            yield d
        d += datetime.timedelta(days=1)


def fetch_mto(date_obj):
    ddmmyyyy = date_obj.strftime("%d%m%Y")
    url = BASE_URL.format(ddmmyyyy=ddmmyyyy)
    try:
        resp = get_session().get(url, timeout=(15, 120))
        if resp.status_code == 404:
            return None, "ABSENT"
        if resp.status_code != 200:
            return None, f"TRANSIENT (HTTP {resp.status_code})"
        if is_html_block(resp):
            return None, "TRANSIENT (HTML block)"
        return resp.content, "OK"
    except requests.RequestException as e:
        return None, f"TRANSIENT ({e})"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 72)
    print("MTO Historical Download — 2010 to 2020")
    print(f"Output: {os.path.abspath(OUTPUT_DIR)}/")
    print("Read-only against NSE — no store, no sealed window")
    print("=" * 72)

    print("\nPriming session...")
    get_session()

    dates = list(trading_days(START_DATE, END_DATE))
    total = len(dates)
    print(f"Trading days in range: {total}\n")

    absent = 0
    transient = 0
    saved = 0
    skipped = 0
    errors_by_code = {}

    start_ts = time.time()

    for i, d in enumerate(dates):
        ddmmyyyy = d.strftime("%d%m%Y")
        out_path = os.path.join(OUTPUT_DIR, f"MTO_{ddmmyyyy}.DAT")

        if os.path.exists(out_path):
            skipped += 1
            continue

        if i > 0:
            time.sleep(REQUEST_DELAY)

        data, status = fetch_mto(d)

        pct = (i + 1) / total * 100

        if status == "OK":
            with open(out_path, "wb") as f:
                f.write(data)
            saved += 1
            print(f"[{pct:5.1f}%] {d}  SAVED ({len(data)} bytes)")
        elif status == "ABSENT":
            absent += 1
            if (i + 1) % 50 == 0:
                print(f"[{pct:5.1f}%] {d}  ABSENT  [{saved} saved, {absent} absent, {transient} transient]")
        else:
            transient += 1
            tag = status.split("(")[-1].rstrip(")")
            errors_by_code[tag] = errors_by_code.get(tag, 0) + 1
            print(f"[{pct:5.1f}%] {d}  {status}")

    elapsed = time.time() - start_ts

    print()
    print("=" * 72)
    print("Complete")
    print(f"  Range:     {START_DATE} to {END_DATE} ({total} trading days)")
    print(f"  Saved:     {saved}")
    print(f"  Skipped:   {skipped}")
    print(f"  Absent:    {absent}")
    print(f"  Transient: {transient}")
    if errors_by_code:
        print("  Error breakdown:")
        for k, v in sorted(errors_by_code.items()):
            print(f"    {k}: {v}")
    print(f"  Elapsed:   {elapsed:.0f}s")
    print("=" * 72)

    return 0 if saved > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
