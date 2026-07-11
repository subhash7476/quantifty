"""CSMP Gate (a) — NSE cash-market daily bhavcopy ingestion.

Ingests the full NSE equity end-of-day series (2010-01-01 -> present by default)
into a dedicated DuckDB store for cross-sectional momentum research on the
NIFTY-200 universe (charter D1/D5). Raw prices only -- no adjustment (that is
gate (b)); all symbols, series EQ and BE only (point-in-time membership is
gate (c), so delisted names must be retained here).

Three source eras are auto-detected per date (verified empirically 2026-07-08):

  * SECFULL  sec_bhavdata_full_{DDMMYYYY}.csv     2020-01-01 -> present
             OHLC + volume + turnover + DELIVERY (deliv_qty, deliv_pct).
             Preferred whenever available -- it is the only delivery source.
  * LEGACY   cm{DD}{MON}{YYYY}bhav.csv.zip         2010-01-01 -> 2024-07-05
             OHLC + volume + turnover. NO delivery (stored NULL).
  * UDIFF    BhavCopy_NSE_CM_..._{YYYYMMDD}...zip  2024-06 -> present
             OHLC + volume + turnover. NO delivery. Fallback only.

Per date the richest available source wins (SECFULL > UDIFF > LEGACY), so the
era->source assignment is deterministic and re-runs reproduce the same store.

Units: `turnover` is always stored in RUPEES. LEGACY TOTTRDVAL is already
rupees; SECFULL TURNOVER_LACS (lakhs) and UDIFF TtlTrfVal (rupees) are
normalised on ingest.

Downloads are cached under data/market_data/bhavcopy_raw/ (content for 200,
a `.404` marker for confirmed-absent dates) so re-runs are resumable and do
not re-hit NSE. Transient failures (timeout / 5xx) are NOT cached and retried
on the next run.

Usage:
    python scripts/csmp/ingest_equity_bhavcopy.py
    python scripts/csmp/ingest_equity_bhavcopy.py --start 2023-01-01 --end 2023-03-31
"""

import argparse
import io
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zipfile import ZipFile, BadZipFile

import duckdb
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
RAW_DIR = ROOT / "data" / "market_data" / "bhavcopy_raw"
INDEX_1M_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"

DEFAULT_START = date(2010, 1, 1)
SECFULL_START = date(2020, 1, 1)
UDIFF_START = date(2024, 6, 1)
LEGACY_LAST = date(2024, 7, 5)

KEEP_SERIES = ("EQ", "BE")
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

_SESSION = None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS equity_bhavcopy (
    trade_date   DATE     NOT NULL,
    symbol       VARCHAR  NOT NULL,
    series       VARCHAR  NOT NULL,
    open         DOUBLE,
    high         DOUBLE,
    low          DOUBLE,
    close        DOUBLE,
    prev_close   DOUBLE,
    volume       BIGINT,
    turnover     DOUBLE,
    deliv_qty    BIGINT,
    deliv_pct    DOUBLE,
    PRIMARY KEY (trade_date, symbol, series)
);
CREATE TABLE IF NOT EXISTS symbol_changes (
    old_symbol   VARCHAR,
    new_symbol   VARCHAR,
    effective_dt DATE,
    company      VARCHAR
);
CREATE TABLE IF NOT EXISTS ingest_meta (
    trade_date DATE PRIMARY KEY,
    source     VARCHAR
);
CREATE TABLE IF NOT EXISTS trading_calendar (
    trade_date DATE PRIMARY KEY,
    source     VARCHAR,
    n_symbols  INTEGER
);
"""

INSERT_SQL = """
INSERT INTO equity_bhavcopy
    (trade_date, symbol, series, open, high, low, close, prev_close,
     volume, turnover, deliv_qty, deliv_pct)
SELECT trade_date, symbol, series, open, high, low, close, prev_close,
       volume, turnover, deliv_qty, deliv_pct
FROM df
ON CONFLICT (trade_date, symbol, series) DO UPDATE SET
    open       = EXCLUDED.open,
    high       = EXCLUDED.high,
    low        = EXCLUDED.low,
    close      = EXCLUDED.close,
    prev_close = EXCLUDED.prev_close,
    volume     = EXCLUDED.volume,
    turnover   = EXCLUDED.turnover,
    deliv_qty  = EXCLUDED.deliv_qty,
    deliv_pct  = EXCLUDED.deliv_pct
"""


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


def date_range(start: date, end: date):
    """All seven weekdays. NSE holds occasional Saturday budget sessions
    (2015-02-28, 2020-02-01) and the Diwali Muhurat session falls on a Sunday
    in some years (2013-11-03, 2016-10-30, 2019-10-27, 2023-11-12), so no day
    may be structurally unreachable (G8). Non-trading days simply 404 and are
    cached as absent; the F&O oracle adjudicates the rest."""
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _parse_date(val: str) -> date:
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%b-%y"):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date: {val!r}")


# --- source URLs --------------------------------------------------------------

def legacy_url(d: date) -> str:
    mon = MONTHS[d.month - 1]
    return (f"https://archives.nseindia.com/content/historical/EQUITIES/"
            f"{d.year}/{mon}/cm{d.day:02d}{mon}{d.year}bhav.csv.zip")


def secfull_url(d: date) -> str:
    return (f"https://nsearchives.nseindia.com/products/content/"
            f"sec_bhavdata_full_{d.day:02d}{d.month:02d}{d.year}.csv")


def udiff_url(d: date) -> str:
    return (f"https://nsearchives.nseindia.com/content/cm/"
            f"BhavCopy_NSE_CM_0_0_0_{d.year}{d.month:02d}{d.day:02d}_F_0000.csv.zip")


SOURCES = {
    "secfull": (secfull_url, "csv"),
    "udiff": (udiff_url, "zip"),
    "legacy": (legacy_url, "zip"),
}


def sources_for(d: date):
    order = []
    if d >= SECFULL_START:
        order.append("secfull")
    if d >= UDIFF_START:
        order.append("udiff")
    if d <= LEGACY_LAST:
        order.append("legacy")
    return order


# --- resumable raw fetch ------------------------------------------------------

class NonConformingBody(requests.RequestException):
    """HTTP 200 whose body is not the expected archive (e.g. NSE's HTML block
    page returned under bulk-access throttling). Treated as transient so the
    poisoned body is never cached and a later run can retry cleanly (F2)."""


def _valid_body(name: str, content: bytes) -> bool:
    if SOURCES[name][1] == "zip":
        return content[:4] == b"PK\x03\x04"
    head = content[:4096].lstrip().upper()
    return head.startswith(b"SYMBOL") and b"SERIES" in head


def _raw_paths(name: str, d: date):
    ext = SOURCES[name][1]
    stem = f"{name}_{d.year}{d.month:02d}{d.day:02d}"
    return RAW_DIR / f"{stem}.{ext}", RAW_DIR / f"{stem}.404"


def fetch(name: str, d: date, attempts: int = 3):
    """Return raw bytes, or None if the source confirmed 404 (absent).

    Validates the body BEFORE caching: a non-conforming HTTP 200 (block page)
    is retried with backoff and, if still bad, raised as a transient failure
    so it is never written to the cache (F2). Only clean bodies are cached.
    Raises requests.RequestException on transient failure (not cached).
    """
    data_path, miss_path = _raw_paths(name, d)
    if data_path.exists():
        return data_path.read_bytes()
    if miss_path.exists():
        return None
    url = SOURCES[name][0](d)
    last_head = b""
    for attempt in range(attempts):
        resp = get_session().get(url, timeout=(15, 120))
        if resp.status_code == 404:
            miss_path.write_bytes(b"")
            return None
        resp.raise_for_status()
        if _valid_body(name, resp.content):
            data_path.write_bytes(resp.content)
            time.sleep(0.4)
            return resp.content
        last_head = resp.content[:120]
        time.sleep(2.0 * (attempt + 1))
    raise NonConformingBody(
        f"{name} {d}: HTTP 200 but body failed {SOURCES[name][1]} validation "
        f"after {attempts} attempts (head={str(last_head)[:80]!r})")


# --- parsers ------------------------------------------------------------------

def _f(val):
    val = val.strip()
    if val in ("", "-"):
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _i(val):
    v = _f(val)
    return None if v is None else int(v)


def parse_legacy(raw: bytes, d: date):
    z = ZipFile(io.BytesIO(raw))
    lines = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    header = [h.strip() for h in lines[0].split(",")]
    idx = {h: i for i, h in enumerate(header)}
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        c = line.split(",")
        if len(c) < len(header):
            continue
        series = c[idx["SERIES"]].strip()
        if series not in KEEP_SERIES:
            continue
        rows.append({
            "trade_date": _parse_date(c[idx["TIMESTAMP"]]) if "TIMESTAMP" in idx
            else d,
            "symbol": c[idx["SYMBOL"]].strip(),
            "series": series,
            "open": _f(c[idx["OPEN"]]),
            "high": _f(c[idx["HIGH"]]),
            "low": _f(c[idx["LOW"]]),
            "close": _f(c[idx["CLOSE"]]),
            "prev_close": _f(c[idx["PREVCLOSE"]]),
            "volume": _i(c[idx["TOTTRDQTY"]]),
            "turnover": _f(c[idx["TOTTRDVAL"]]),
            "deliv_qty": None,
            "deliv_pct": None,
        })
    return rows


def parse_secfull(raw: bytes, d: date):
    lines = raw.decode("latin-1").splitlines()
    header = [h.strip() for h in lines[0].split(",")]
    idx = {h: i for i, h in enumerate(header)}
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        c = line.split(",")
        if len(c) < len(header):
            continue
        series = c[idx["SERIES"]].strip()
        if series not in KEEP_SERIES:
            continue
        turnover_lacs = _f(c[idx["TURNOVER_LACS"]])
        rows.append({
            "trade_date": _parse_date(c[idx["DATE1"]]),
            "symbol": c[idx["SYMBOL"]].strip(),
            "series": series,
            "open": _f(c[idx["OPEN_PRICE"]]),
            "high": _f(c[idx["HIGH_PRICE"]]),
            "low": _f(c[idx["LOW_PRICE"]]),
            "close": _f(c[idx["CLOSE_PRICE"]]),
            "prev_close": _f(c[idx["PREV_CLOSE"]]),
            "volume": _i(c[idx["TTL_TRD_QNTY"]]),
            "turnover": None if turnover_lacs is None else turnover_lacs * 1e5,
            "deliv_qty": _i(c[idx["DELIV_QTY"]]),
            "deliv_pct": _f(c[idx["DELIV_PER"]]),
        })
    return rows


def parse_udiff(raw: bytes, d: date):
    z = ZipFile(io.BytesIO(raw))
    lines = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    header = [h.strip() for h in lines[0].split(",")]
    idx = {h: i for i, h in enumerate(header)}
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        c = line.split(",")
        if len(c) < len(header):
            continue
        if c[idx["FinInstrmTp"]].strip() != "STK":
            continue
        series = c[idx["SctySrs"]].strip()
        if series not in KEEP_SERIES:
            continue
        rows.append({
            "trade_date": _parse_date(c[idx["TradDt"]]),
            "symbol": c[idx["TckrSymb"]].strip(),
            "series": series,
            "open": _f(c[idx["OpnPric"]]),
            "high": _f(c[idx["HghPric"]]),
            "low": _f(c[idx["LwPric"]]),
            "close": _f(c[idx["ClsPric"]]),
            "prev_close": _f(c[idx["PrvsClsgPric"]]),
            "volume": _i(c[idx["TtlTradgVol"]]),
            "turnover": _f(c[idx["TtlTrfVal"]]),
            "deliv_qty": None,
            "deliv_pct": None,
        })
    return rows


PARSERS = {"legacy": parse_legacy, "secfull": parse_secfull, "udiff": parse_udiff}


def _insert(con, rows):
    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["trade_date", "symbol", "series"], keep="last")
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute(INSERT_SQL)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return len(df)


def ingest_day(con, d: date):
    """Return (rows_inserted, source_name) or (0, None) if absent, or
    (-1, None) if a transient fetch failure blocked the date.

    A transient/non-conforming failure of one source falls through to the next
    applicable source (SECFULL block pages must not abort a day that LEGACY can
    still serve — the 2022-08-08 failure class); -1 is returned only if every
    applicable source failed transiently and none yielded rows."""
    any_transient = False
    for name in sources_for(d):
        try:
            raw = fetch(name, d)
        except (requests.RequestException, BadZipFile) as exc:
            print(f"{d}  {name:<7} transient-fail {type(exc).__name__}")
            any_transient = True
            continue
        if raw is None:
            continue
        try:
            rows = PARSERS[name](raw, d)
        except (BadZipFile, KeyError, ValueError) as exc:
            print(f"{d}  {name:<7} parse-fail {type(exc).__name__}: {exc}")
            continue
        if not rows:
            continue
        # G4: identity guard. On a holiday NSE answers with HTTP 200 carrying the
        # PREVIOUS trading day's file. _valid_body() checks shape, not identity,
        # so verify every row is dated as requested; on any mismatch discard the
        # payload and treat the date as confirmed-absent (do NOT write rows onto
        # another date, do NOT record ingest_meta).
        file_dates = {r["trade_date"] for r in rows}
        if file_dates != {d}:
            got = ", ".join(str(x) for x in sorted(file_dates))
            print(f"{d}  {name:<7} identity-mismatch (file dated {got}); discarded")
            continue
        return _insert(con, rows), name
    return (-1, None) if any_transient else (0, None)


# --- calendar oracle (F&O bhavcopy = independent "was NSE open?" truth) -------

def legacy_fo_url(d: date) -> str:
    mon = MONTHS[d.month - 1]
    return (f"https://archives.nseindia.com/content/historical/DERIVATIVES/"
            f"{d.year}/{mon}/fo{d.day:02d}{mon}{d.year}bhav.csv.zip")


def udiff_fo_url(d: date) -> str:
    return (f"https://nsearchives.nseindia.com/content/fo/"
            f"BhavCopy_NSE_FO_0_0_0_{d.year}{d.month:02d}{d.day:02d}_F_0000.csv.zip")


def fo_is_trading(d: date):
    """Independent oracle: was NSE open on d? True / False, or None if the
    probe could not be resolved (transient). The F&O archive is a separate
    product on the identical trading calendar, so it disambiguates a genuine
    equity source hole (F&O present, equity absent) from a market holiday
    (both absent), and it captures Saturday special sessions (F3/F5). Spans the
    whole range: legacy F&O (<= 2024-07) then UDIFF F&O (2024-06+), so the
    sealed-window tail is covered rather than trusting index filenames (R4)."""
    candidates = []
    if d <= LEGACY_LAST:
        candidates.append(("focal", legacy_fo_url(d)))
    if d >= UDIFF_START:
        candidates.append(("foudiff", udiff_fo_url(d)))
    if not candidates:
        return None
    transient = False
    for prefix, url in candidates:
        stem = f"{prefix}_{d.year}{d.month:02d}{d.day:02d}"
        data_path = RAW_DIR / f"{stem}.zip"
        miss_path = RAW_DIR / f"{stem}.404"
        if data_path.exists():
            return True
        if miss_path.exists():
            continue
        try:
            resp = get_session().get(url, timeout=(15, 120))
        except requests.RequestException:
            transient = True
            continue
        if resp.status_code == 200 and resp.content[:4] == b"PK\x03\x04":
            data_path.write_bytes(resp.content)
            time.sleep(0.4)
            return True
        if resp.status_code == 404:
            miss_path.write_bytes(b"")
            continue
        transient = True
    return None if transient else False


def index_trading_days():
    """Trading days corroborated by the in-repo 1m index store. G5: the file is
    OPENED and its bars inspected, never trusted by filename. A filename date is
    accepted only if the file carries >= 100 distinct symbols whose bar-date
    (CAST(timestamp AS DATE)) equals the filename date. This rejects backfill
    artifacts (1-symbol files) and mis-stamped files (bars dated to another day)
    while still catching real Sunday Muhurat sessions. The 1m files are not
    cleanly date-partitioned, so bars are filtered by date, not assumed
    homogeneous."""
    days = set()
    if not INDEX_1M_DIR.exists():
        return days
    for f in INDEX_1M_DIR.glob("*.duckdb"):
        try:
            fdate = date.fromisoformat(f.stem)
        except ValueError:
            continue
        try:
            c = duckdb.connect(str(f), read_only=True)
            n = c.execute(
                "SELECT COUNT(DISTINCT symbol) FROM candles "
                "WHERE CAST(timestamp AS DATE) = ?", [fdate]).fetchone()[0]
            c.close()
        except Exception:
            n = 0
        if n >= 100:
            days.add(fdate)
    return days


def build_trading_calendar(con, start: date, end: date):
    """Authoritative NSE trading calendar for the span, written to
    `trading_calendar`. 2023+ uses the in-repo 1m index calendar (offline);
    pre-2023 probes the F&O oracle for any day not already known-trading.
    Returns (n_days, n_unresolved)."""
    eq_days = {r[0] for r in con.execute(
        "SELECT DISTINCT trade_date FROM equity_bhavcopy "
        "WHERE trade_date BETWEEN ? AND ?", [start, end]).fetchall()}
    # H1: record session breadth (distinct EQ/BE symbols) so downstream gates can
    # tell a full ~1,500-symbol session from a restricted special session (e.g.
    # the gold-ETF-only Akshaya Tritiya / Dhanteras Sundays: 7 and 14 symbols).
    eq_counts = dict(con.execute(
        "SELECT trade_date, COUNT(DISTINCT symbol) FROM equity_bhavcopy "
        "WHERE trade_date BETWEEN ? AND ? GROUP BY 1", [start, end]).fetchall())
    idx = {d for d in index_trading_days() if start <= d <= end}
    entries = {d: "equity_store" for d in eq_days}
    for d in idx:
        entries.setdefault(d, "index_1m")

    # Probe the independent F&O oracle for EVERY day not already known-trading,
    # across the whole span (not just pre-2023): this closes the sealed-window
    # gap where a day missing from both index_1m and the store would otherwise
    # never surface as a hole (R4).
    unresolved = 0
    for d in date_range(start, end):
        if d in entries:
            continue
        r = fo_is_trading(d)
        if r is True:
            entries[d] = "fo_probe"
        elif r is None:
            # N1: a transient probe failure is NOT a confirmed holiday. Persist
            # it explicitly so the audit can see the day was never adjudicated
            # (absence must not read as confirmation). fo_is_trading writes no
            # cache marker on transient, so a later run re-probes and resolves.
            entries[d] = "unresolved"
            unresolved += 1

    rows = []
    for d, s in sorted(entries.items()):
        # n_symbols is the equity cross-section on that day; 0 for non-store
        # trading days (coverage holes) and NULL for unadjudicated (unresolved).
        if s == "unresolved":
            n = None
        else:
            n = eq_counts.get(d, 0)
        rows.append((d, s, n))
    df = pd.DataFrame(rows, columns=["trade_date", "source", "n_symbols"])
    con.execute("DELETE FROM trading_calendar WHERE trade_date BETWEEN ? AND ?",
                [start, end])
    con.execute("INSERT INTO trading_calendar (trade_date, source, n_symbols) "
                "SELECT trade_date, source, n_symbols FROM df")
    n_trading = sum(1 for s in entries.values() if s != "unresolved")
    return n_trading, unresolved


def ingest_symbol_changes(con):
    url = "https://nsearchives.nseindia.com/content/equities/symbolchange.csv"
    try:
        resp = get_session().get(url, timeout=(15, 60))
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"symbol_changes: UNOBTAINABLE ({type(exc).__name__}); "
              f"table left empty. Manual source: {url}")
        return 0
    rows = []
    for line in resp.content.decode("latin-1").splitlines():
        c = line.split(",")
        if len(c) < 4:
            continue
        try:
            eff = _parse_date(c[3])
        except ValueError:
            continue
        rows.append({
            "old_symbol": c[1].strip(),
            "new_symbol": c[2].strip(),
            "effective_dt": eff,
            "company": c[0].strip(),
        })
    if not rows:
        return 0
    df = pd.DataFrame(rows).drop_duplicates()
    con.execute("DELETE FROM symbol_changes")
    con.execute("INSERT INTO symbol_changes SELECT old_symbol, new_symbol, "
                "effective_dt, company FROM df")
    return len(df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=lambda s: _parse_date(s),
                    default=DEFAULT_START)
    ap.add_argument("--end", type=lambda s: _parse_date(s),
                    default=date.today() - timedelta(days=1))
    args = ap.parse_args()

    os.makedirs(DB_PATH.parent, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))
    con.execute(SCHEMA_SQL)
    # migration for stores created before the n_symbols column (H1)
    con.execute("ALTER TABLE trading_calendar ADD COLUMN IF NOT EXISTS "
                "n_symbols INTEGER")

    inserted = present = absent = failed = 0
    for d in date_range(args.start, args.end):
        n_exist = con.execute(
            "SELECT COUNT(*) FROM equity_bhavcopy WHERE trade_date = ?", [d]
        ).fetchone()[0]
        if n_exist > 0:
            present += 1
            continue
        n, src = ingest_day(con, d)
        if n > 0:
            print(f"{d}  {src:<7} {n:>5} rows")
            con.execute(
                "INSERT INTO ingest_meta VALUES (?, ?) "
                "ON CONFLICT (trade_date) DO UPDATE SET source = EXCLUDED.source",
                [d, src])
            inserted += n
        elif n == 0:
            print(f"{d}  absent (holiday/source hole)")
            absent += 1
        else:
            failed += 1

    n_sym = ingest_symbol_changes(con)

    # G4: reconcile ingest_meta to actual stored dates. Pre-fix runs recorded a
    # meta row for holiday dates whose 200-response held the previous day's file
    # (rows never landed on the requested date) — those are phantoms. A meta row
    # is legitimate only if that date has rows in equity_bhavcopy.
    meta_before = con.execute("SELECT COUNT(*) FROM ingest_meta").fetchone()[0]
    con.execute("DELETE FROM ingest_meta WHERE trade_date NOT IN "
                "(SELECT DISTINCT trade_date FROM equity_bhavcopy)")
    meta_after = con.execute("SELECT COUNT(*) FROM ingest_meta").fetchone()[0]
    phantoms = meta_before - meta_after

    cal_n, cal_unresolved = build_trading_calendar(con, args.start, args.end)
    con.close()

    print()
    print("=" * 56)
    print("INGESTION SUMMARY")
    print("=" * 56)
    print(f"Span:                 {args.start} -> {args.end}")
    print(f"Rows inserted:        {inserted:,}")
    print(f"Dates already present:{present}")
    print(f"Dates absent (404):   {absent}")
    print(f"Dates fetch-failed:   {failed}")
    print(f"Symbol-change rows:   {n_sym:,}")
    print(f"Phantom meta purged:  {phantoms}")
    print(f"Trading-calendar days:{cal_n:,} (unresolved probes: {cal_unresolved})")
    if failed or cal_unresolved:
        print("\nWARNING: transient failures were NOT cached; re-run to retry.")


if __name__ == "__main__":
    main()
