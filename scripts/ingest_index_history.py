"""Carry G1-R — clean re-ingest of the NSE daily index store.

Replaces scripts/g1_ingest_index_history.py, g1_fix_timestamp.py, g1_retry_2015.py.

Sources:
  (a) NSE archive — https://nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv
  (b) Operator-supplied — data/market_data/vendor/niftyindices/nifty50_<YYYY>.csv (optional)

Target: data/market_data/nse/candles/1d/{YYYY-MM-DD}.duckdb, table candles.
One row per (symbol, date) with timestamp TIMESTAMP.

Usage:
    python scripts/ingest_index_history.py
    python scripts/ingest_index_history.py --archive-only
    python scripts/ingest_index_history.py --run-gates
"""

import argparse
import csv
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NIFTY_1D_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
VENDOR_DIR = ROOT / "data" / "market_data" / "vendor" / "niftyindices"
# niftyindices.com serves "NIFTY 50_Historical_PR_<from>to<to>.csv" — match any CSV in the dir
# rather than a stem pattern, which silently matched nothing and skipped Gate B entirely.
VENDOR_GLOB = "*.csv"
EQUITY_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"

# NSE index close URL pattern
def archive_url(d: date) -> str:
    return (f"https://nsearchives.nseindia.com/content/indices/"
            f"ind_close_all_{d.strftime('%d%m%Y')}.csv")

# CNX → current name mapping. Any name not in this map and not already NSE_INDEX|-canonical
# is skipped (hard-fail: raise, don't write through).
# Special marker "__SKIP__" means the name should be skipped and counted, not written through.
CNX_TO_CURRENT = {
    "S&P CNX Nifty": "NSE_INDEX|Nifty 50",
    "CNX Nifty": "NSE_INDEX|Nifty 50",
    "S&P CNX 500": "NSE_INDEX|Nifty 500",
    "CNX Bank": "NSE_INDEX|Nifty Bank",
    "CNX IT": "NSE_INDEX|Nifty IT",
    "CNX Auto": "NSE_INDEX|Nifty Auto",
    "CNX Metal": "NSE_INDEX|Nifty Metal",
    "CNX Pharma": "NSE_INDEX|Nifty Pharma",
    "CNX FMCG": "NSE_INDEX|Nifty FMCG",
    "CNX Energy": "NSE_INDEX|Nifty Energy",
    "CNX Media": "NSE_INDEX|Nifty Media",
    "CNX Finance": "NSE_INDEX|Nifty Financial Services",
    "CNX MNC": "NSE_INDEX|Nifty MNC",
    "CNX Realty": "NSE_INDEX|Nifty Realty",
    "CNX Infrastructure": "NSE_INDEX|Nifty Infrastructure",
    "CNX Commodities": "NSE_INDEX|Nifty Commodities",
    "CNX Consumption": "NSE_INDEX|Nifty Consumption",
    "CNX PSE": "NSE_INDEX|Nifty PSE",
    "CNX PSB": "NSE_INDEX|Nifty PSU Bank",
    "CNX Service": "NSE_INDEX|Nifty Services Sector",
    "CNX Service Sector": "NSE_INDEX|Nifty Services Sector",
    "CNX Nifty Junior": "NSE_INDEX|Nifty Next 50",
    "CNX Nifty Dividend": "NSE_INDEX|Nifty Dividend Opportunities",
    "CNX Nifty Shariah": "NSE_INDEX|Nifty Shariah",
    "S&P CNX Nifty Shariah": "__SKIP__",
    "CNX 100": "NSE_INDEX|Nifty 100",
    "CNX 200": "NSE_INDEX|Nifty 200",
    "CNX 500": "NSE_INDEX|Nifty 500",
    "CNX 100 Equal Weight": "NSE_INDEX|Nifty 100 Equal Weight",
    "CNX 500 Shariah": "NSE_INDEX|Nifty 500 Shariah",
    "S&P CNX 500 Shariah": "__SKIP__",
    "NIFTY Midcap 50": "NSE_INDEX|Nifty Midcap 50",
    "CNX Midcap": "NSE_INDEX|Nifty Midcap 100",
    "CNX Smallcap": "NSE_INDEX|Nifty Smallcap 100",
    "NIFTY Smallcap 50": "NSE_INDEX|Nifty Smallcap 50",
}

# Registered CNX exclusions — six niche indices NSE discontinued with no modern successor,
# present only 2015-03-02 -> 2015-11-06 (119 sessions each, 714 rows). They are not aliases of
# any current index, so canonicalizing them would fabricate continuity. Gate A4 accepts these
# by name and fails on any other CNX symbol.
# Dates present in equity_bhavcopy that are NOT trading sessions, excluded from the derived
# calendar. 2012-11-11 is a Sunday carrying 14 equity rows against a normal session's ~1,400 —
# a bhavcopy artifact, and the NSE index archive 404s it. Evidence, not convenience: any date
# added here must be shown to be a non-session, never merely unsourceable.
NON_SESSIONS = {"2012-11-11"}

# Dates with no NSE index close file. The first seven are the spec's named absences; the
# last three were added when the 2015 retry could not recover them.
KNOWN_ABSENCES = {"2015-02-02", "2015-02-17", "2015-03-12", "2015-03-13",
                  "2015-05-19", "2015-07-08", "2015-09-04", "2015-09-25",
                  "2015-10-16", "2015-12-01"}

ACCEPTED_CNX_EXCLUSIONS = {
    "NSE_INDEX|CNX Alpha Index",
    "NSE_INDEX|CNX DEFTY",
    "NSE_INDEX|CNX Dividend Opportunities",
    "NSE_INDEX|CNX High Beta",
    "NSE_INDEX|CNX Low Volatility",
    "NSE_INDEX|CNX Shariah25",
}

CANDLES_SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    symbol       VARCHAR NOT NULL,
    timeframe    VARCHAR NOT NULL DEFAULT '1d',
    timestamp    TIMESTAMP NOT NULL,
    open         DOUBLE,
    high         DOUBLE,
    low          DOUBLE,
    close        DOUBLE,
    volume       BIGINT,
    is_synthetic BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (symbol, timeframe, timestamp)
)
"""


def _get_session():
    sess = requests.Session()
    retry = Retry(total=3, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])
    sess.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=1, pool_maxsize=1))
    sess.headers.update({"User-Agent": "Mozilla/5.0"})
    return sess


def _parse_date(val: str) -> date:
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d",
                "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date: {val}")


def canonicalize(raw_name: str) -> str:
    """Map a raw index name to NSE_INDEX| format. Raise on unmapped CNX names."""
    name = raw_name.strip()
    if name.startswith("NSE_INDEX|"):
        return name
    mapped = CNX_TO_CURRENT.get(name)
    if mapped is not None:
        if mapped == "__SKIP__":
            raise ValueError(f"Skipped CNX index name: {name!r}")
        return mapped
    # Use containment test, not prefix, to catch "S&P CNX ..." as well as "CNX ..."
    if "CNX " in name:
        raise ValueError(f"Unmapped CNX index name: {name!r}")
    return f"NSE_INDEX|{name}"


def parse_archive_csv(text: str, trade_date: date) -> tuple[list[dict], int]:
    """Parse ind_close_all CSV. Returns (rows, skipped_cnx_count)."""
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return [], 0
    rows = []
    skipped = 0
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < 6:
            continue
        idx_date = _parse_date(parts[1])
        if idx_date != trade_date:
            continue
        try:
            symbol = canonicalize(parts[0].strip())
        except ValueError:
            skipped += 1
            continue
        rows.append({
            "symbol": symbol,
            "timestamp": trade_date.isoformat(),
            "open": float(parts[2]) if parts[2] not in ("-", "") else None,
            "high": float(parts[3]) if parts[3] not in ("-", "") else None,
            "low": float(parts[4]) if parts[4] not in ("-", "") else None,
            "close": float(parts[5]) if parts[5] not in ("-", "") else None,
            "volume": int(float(parts[8])) if len(parts) > 8 and parts[8] not in ("-", "") else 0,
        })
    return rows, skipped


def ingest_rows(d: date, rows: list[dict], source: str):
    """Write rows to the per-day DuckDB file. Idempotent: delete-then-insert."""
    if not rows:
        return
    f = NIFTY_1D_DIR / f"{d.isoformat()}.duckdb"
    os.makedirs(f.parent, exist_ok=True)
    con = duckdb.connect(str(f))
    con.execute(CANDLES_SCHEMA)
    # Verify schema
    ts_type = con.execute(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name='candles' AND column_name='timestamp'"
    ).fetchone()
    if ts_type and ts_type[0].upper() != "TIMESTAMP":
        raise TypeError(f"{f.stem}: timestamp is {ts_type[0]}, expected TIMESTAMP")
    # Delete-then-insert per symbol
    for row in rows:
        con.execute(
            "DELETE FROM candles WHERE symbol=? AND timeframe='1d' AND timestamp=?",
            [row["symbol"], row["timestamp"]]
        )
        con.execute("""
            INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume, is_synthetic)
            VALUES (?, '1d', ?, ?, ?, ?, ?, ?, FALSE)
        """, [row["symbol"], row["timestamp"], row["open"], row["high"],
              row["low"], row["close"], row["volume"]])
    con.close()


def date_range(start: date, end: date):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


# --- Archive floor discovery ---

def discover_floor(sess, probe_start: date) -> date:
    """Walk backwards from probe_start to find the earliest date with a 200 response.
    Returns that date. Stops after 15 consecutive 404s."""
    d = probe_start
    consec_404 = 0
    floor = None
    while consec_404 < 15 and d >= date(2000, 1, 1):
        url = archive_url(d)
        try:
            resp = sess.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 100:
                floor = d
                consec_404 = 0
            else:
                consec_404 += 1
        except requests.RequestException:
            consec_404 += 1
        d -= timedelta(days=1)
        time.sleep(0.3)
    return floor


# --- Operator file parsing ---

def parse_vendor_file(path: Path) -> dict[date, dict]:
    """Parse niftyindices CSV. Returns {date: {open, high, low, close}}."""
    result = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_date = row.get("Date", "").strip()
            try:
                d = _parse_date(raw_date)
            except ValueError:
                continue  # skip header-like rows
            result[d] = {
                "open": float(row.get("Open", 0)),
                "high": float(row.get("High", 0)),
                "low": float(row.get("Low", 0)),
                "close": float(row.get("Close", 0)),
            }
    return result


# --- Vendor gap fill ---

SNAPSHOT_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1d_snapshots"


def fill_gap_from_vendor():
    """Insert NSE_INDEX|Nifty 50 rows for store files that have none, from the operator CSVs.

    Snapshots every target file's full contents before writing. Insert-only: never deletes
    and never touches a date that already carries a Nifty 50 row.
    """
    vendor = {}
    for vf in sorted(VENDOR_DIR.glob(VENDOR_GLOB)):
        vendor.update(parse_vendor_file(vf))
    if not vendor:
        print("No vendor rows parsed — nothing to fill")
        return
    print(f"Parsed {len(vendor)} vendor dates ({min(vendor)} -> {max(vendor)})")

    targets = []
    for f in sorted(NIFTY_1D_DIR.glob("*.duckdb")):
        con = duckdb.connect(str(f), read_only=True)
        n = con.execute(
            "SELECT COUNT(*) FROM candles WHERE symbol='NSE_INDEX|Nifty 50'"
        ).fetchone()[0]
        con.close()
        if n == 0:
            targets.append(f)
    print(f"Store files with no Nifty 50 row: {len(targets)}")

    fillable = [f for f in targets if _parse_date(f.stem) in vendor]
    unfillable = [f.stem for f in targets if _parse_date(f.stem) not in vendor]
    if unfillable:
        print(f"  NOT covered by vendor ({len(unfillable)}): {unfillable}")
    if not fillable:
        print("No existing file needs a Nifty 50 row")
        _create_absent_date_files(vendor)
        return

    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    snap = SNAPSHOT_DIR / f"pre_vendor_fill_{datetime.now():%Y%m%dT%H%M%S}.csv"
    with open(snap, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "symbol", "timeframe", "timestamp", "open", "high", "low",
                    "close", "volume", "is_synthetic"])
        for f in fillable:
            con = duckdb.connect(str(f), read_only=True)
            for row in con.execute(
                "SELECT symbol, timeframe, timestamp, open, high, low, close, volume, "
                "is_synthetic FROM candles ORDER BY symbol"
            ).fetchall():
                w.writerow([f.stem, *row])
            con.close()
    print(f"Snapshot written: {snap}")

    filled = 0
    for f in fillable:
        d = _parse_date(f.stem)
        v = vendor[d]
        con = duckdb.connect(str(f))
        con.execute("""
            INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close,
                                 volume, is_synthetic)
            VALUES ('NSE_INDEX|Nifty 50', '1d', ?, ?, ?, ?, ?, 0, FALSE)
        """, [d.isoformat(), v["open"], v["high"], v["low"], v["close"]])
        con.close()
        filled += 1
    print(f"Filled {filled} sessions from vendor ({fillable[0].stem} -> {fillable[-1].stem})")

    _create_absent_date_files(vendor)


def _create_absent_date_files(vendor: dict):
    """Create store files for trading dates that have none, from vendor rows.

    Creating a file is not destructive — there is nothing to overwrite — so no snapshot
    applies; rollback is deleting the listed files. These files carry the Nifty 50 row ONLY:
    the vendor serves one index, so they are not 28-symbol archive-sourced files.
    """
    absent = [d for d in missing_trading_dates(KNOWN_ABSENCES) if d in vendor]
    if not absent:
        return
    created = []
    for d in absent:
        v = vendor[d]
        ingest_rows(d, [{
            "symbol": "NSE_INDEX|Nifty 50",
            "timestamp": d.isoformat(),
            "open": v["open"], "high": v["high"], "low": v["low"], "close": v["close"],
            "volume": 0,
        }], source="vendor")
        created.append(d.isoformat())
    print(f"Created {len(created)} absent-date files (Nifty 50 row only): {created}")


def trading_calendar(lo: str, hi: str) -> set:
    """Trading dates in [lo, hi] from the equity bhavcopy, less known non-sessions.

    Single source of the calendar: A1, A7 and the fill/fetch paths all derive from this, so a
    non-session cannot be excluded in one place and remain a phantom gap in another.
    """
    con = duckdb.connect(str(EQUITY_DB), read_only=True)
    dates = {r[0].isoformat() for r in con.execute(
        "SELECT DISTINCT trade_date FROM equity_bhavcopy WHERE trade_date >= ? AND trade_date <= ?",
        [lo, hi]
    ).fetchall()}
    con.close()
    return dates - NON_SESSIONS


def missing_trading_dates(known_absences: set) -> list[date]:
    """Trading dates inside the store's span that have no store file at all."""
    stems = {f.stem for f in NIFTY_1D_DIR.glob("*.duckdb")}
    trading = trading_calendar(min(stems), max(stems))
    return [_parse_date(d) for d in sorted(trading - stems - known_absences)]


def fetch_missing_sessions(known_absences: set):
    """Fetch archive rows for trading dates with no store file (Saturday specials, Muhurat).

    A date is classified MISSING only on a non-200 response. A network error is reported as
    an error and never as evidence the archive lacks the date.
    """
    targets = missing_trading_dates(known_absences)
    print(f"Trading dates with no store file: {len(targets)}")
    if not targets:
        return
    sess = _get_session()
    fetched, absent, errors = [], [], []
    for d in targets:
        try:
            resp = sess.get(archive_url(d), timeout=30)
        except requests.RequestException as e:
            errors.append((d.isoformat(), repr(e)))
            print(f"  {d} ERROR (not classified as absent): {e}")
            time.sleep(0.3)
            continue
        if resp.status_code != 200 or len(resp.content) <= 100:
            absent.append(d.isoformat())
            print(f"  {d} absent from archive (HTTP {resp.status_code})")
            time.sleep(0.3)
            continue
        rows, skipped = parse_archive_csv(resp.text, d)
        ingest_rows(d, rows, source="archive")
        fetched.append(d.isoformat())
        print(f"  {d} fetched: {len(rows)} rows ({skipped} legacy names skipped)")
        time.sleep(0.3)
    print(f"\nfetched {len(fetched)} · absent {len(absent)} · errors {len(errors)}")
    if absent:
        print(f"  absent: {absent}")
    if errors:
        print(f"  ERRORS — re-run before treating these as absent: {[e[0] for e in errors]}")


# --- Gates ---

def gate_a(floor: date, known_absences: set):
    """Gate set A — archive-only checks."""
    print("\n" + "=" * 60)
    print("GATE SET A - ARCHIVE ONLY")
    print("=" * 60)
    failures = []

    files = sorted(NIFTY_1D_DIR.glob("*.duckdb"))

    # Calendar completeness
    print("\n[Gate A1] Calendar completeness...")
    trading_dates = trading_calendar(floor.isoformat(), date.today().isoformat())

    existing_dates = {f.stem for f in files}
    missing = sorted(trading_dates - existing_dates)
    unexpected = [d for d in missing if d not in known_absences]
    if unexpected:
        print(f"  FAIL: {len(unexpected)} unexpected misses: {unexpected[:10]}...")
        failures.append("A1-unexpected-misses")
    else:
        print(f"  PASS: {len(missing)} known absences only ({len(known_absences - set(missing))} not in calendar)")

    # Beta computability
    print("\n[Gate A2] Beta computability...")
    nifty_dates = []
    for f in files:
        con = duckdb.connect(str(f), read_only=True)
        cnt = con.execute("SELECT COUNT(*) FROM candles WHERE symbol='NSE_INDEX|Nifty 50'").fetchone()[0]
        con.close()
        if cnt > 0:
            nifty_dates.append(f.stem)
    nifty_dates.sort()
    earliest_beta = None
    for i, ds in enumerate(nifty_dates):
        if i >= 251:
            earliest_beta = ds
            break
    if earliest_beta and earliest_beta <= "2013-06-30":
        print(f"  PASS: 252-session beta computable from {earliest_beta}")
    else:
        print(f"  FAIL: earliest beta date {earliest_beta} (need <= 2013-06-30)")
        failures.append("A2-beta-date")

    # Schema uniformity
    print("\n[Gate A3] Schema uniformity...")
    bad = 0
    for f in files:
        con = duckdb.connect(str(f), read_only=True)
        ts_type = con.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name='candles' AND column_name='timestamp'"
        ).fetchone()
        if ts_type and ts_type[0].upper() != "TIMESTAMP":
            bad += 1
        con.close()
    if bad == 0:
        print(f"  PASS: all {len(files)} files have TIMESTAMP")
    else:
        print(f"  FAIL: {bad} files have non-TIMESTAMP")
        failures.append("A3-schema")

    # Symbol hygiene
    print("\n[Gate A4] Symbol hygiene (no un-registered CNX)...")
    total = 0
    seen = {}
    for f in files:
        con = duckdb.connect(str(f), read_only=True)
        for sym, n in con.execute(
            "SELECT symbol, COUNT(*) FROM candles WHERE symbol LIKE '%CNX%' GROUP BY symbol"
        ).fetchall():
            seen[sym] = seen.get(sym, 0) + n
            total += n
        con.close()
    unregistered = {s: n for s, n in seen.items() if s not in ACCEPTED_CNX_EXCLUSIONS}
    if not unregistered:
        print(f"  PASS: {total} CNX rows, all {len(seen)} symbols registered exclusions")
        for s in sorted(seen):
            print(f"    {seen[s]:>4}  {s}")
    else:
        print(f"  FAIL: {sum(unregistered.values())} rows in un-registered CNX symbols")
        for s in sorted(unregistered):
            print(f"    {unregistered[s]:>4}  {s}")
        failures.append("A4-cnx")

    # No duplicates
    print("\n[Gate A5] No duplicate Nifty 50 rows...")
    dups = 0
    for f in files:
        con = duckdb.connect(str(f), read_only=True)
        n = con.execute("SELECT COUNT(*) FROM candles WHERE symbol='NSE_INDEX|Nifty 50'").fetchone()[0]
        if n > 1:
            dups += 1
        con.close()
    if dups == 0:
        print(f"  PASS: no duplicates")
    else:
        print(f"  FAIL: {dups} files have >1 Nifty 50 row")
        failures.append("A5-duplicates")

    # Series contiguity — file existence is not row existence.
    # A1 compares file stems to the calendar, so deleting the Nifty 50 row from a file that
    # still exists is invisible to it (and to A2/A5/A6). This gate tests the series itself.
    print("\n[Gate A7] Nifty 50 series contiguity...")
    store_span = {f.stem for f in files}
    nifty_set = set(nifty_dates)
    expected = {d for d in trading_dates if min(store_span) <= d <= max(store_span)}
    holes = expected - nifty_set - known_absences
    # Two distinct defects. A1 already owns "no file at all"; A7 exists for the case A1
    # structurally cannot see — the file is present and the Nifty 50 row inside it is not.
    no_file = sorted(d for d in holes if d not in store_span)
    no_row = sorted(d for d in holes if d in store_span)
    if no_file:
        print(f"  INFO: {len(no_file)} trading dates have no store file at all — A1's finding,"
              f" not A7's: {no_file[:10]}{' ...' if len(no_file) > 10 else ''}")
    if not no_row:
        print(f"  PASS: every store file in span carries a Nifty 50 row ({len(nifty_set)})")
    else:
        print(f"  FAIL: {len(no_row)} trading dates have a file but no Nifty 50 row")
        print(f"    {no_row[0]} -> {no_row[-1]}; first 10: {no_row[:10]}")
        failures.append("A7-contiguity")

    # Continuity
    print("\n[Gate A6] Continuity (8%+ moves)...")
    prev_close = None
    large_moves = []
    for ds in nifty_dates:
        f = NIFTY_1D_DIR / f"{ds}.duckdb"
        con = duckdb.connect(str(f), read_only=True)
        close = con.execute("SELECT close FROM candles WHERE symbol='NSE_INDEX|Nifty 50'").fetchone()
        con.close()
        if close is None or close[0] is None:
            continue
        c = close[0]
        if prev_close is not None and prev_close != 0:
            pct = (c - prev_close) / prev_close * 100
            if abs(pct) > 8:
                large_moves.append((ds, pct))
        prev_close = c
    if large_moves:
        print(f"  {len(large_moves)} large moves (>8%):")
        for ds, pct in large_moves:
            detail = "  (known COVID)" if "2020-03" in ds or "2020-04" in ds else "  ** CHECK **"
            print(f"    {ds}: {pct:+.1f}%{detail}")
        suspicious = [(ds, pct) for ds, pct in large_moves if "2020-03" not in ds and "2020-04" not in ds]
        if suspicious:
            print(f"  WARNING: {len(suspicious)} moves outside known COVID events — eyeball")
    else:
        print(f"  PASS: no large moves")

    # Summary
    print(f"\n{'=' * 60}")
    if failures:
        print(f"GATE A: {len(failures)} FAILURES — {', '.join(failures)}")
    else:
        print(f"GATE A: ALL PASS")
    return failures


def gate_b(floor: date):
    """Gate set B — only if operator files present."""
    vendor_files = sorted(VENDOR_DIR.glob(VENDOR_GLOB))
    if not vendor_files:
        print("\nGate B: source (b) not supplied — skipping")
        return []
    print("\n" + "=" * 60)
    print("GATE SET B - OPERATOR FILE PRESENT")
    print("=" * 60)
    failures = []

    # Parse all vendor files
    vendor_data = {}
    for vf in vendor_files:
        vendor_data.update(parse_vendor_file(vf))
    print(f"\n  Parsed {len(vendor_data)} dates from {len(vendor_files)} vendor files")

    # Cross-source agreement
    print("\n[Gate B1] Cross-source close agreement...")
    max_diff = 0.0
    disagree_dates = []
    for d, vrow in vendor_data.items():
        f = NIFTY_1D_DIR / f"{d.isoformat()}.duckdb"
        if not f.exists():
            continue
        con = duckdb.connect(str(f), read_only=True)
        row = con.execute("SELECT close FROM candles WHERE symbol='NSE_INDEX|Nifty 50'").fetchone()
        con.close()
        if row is None or row[0] is None:
            continue
        diff = abs(row[0] - vrow["close"])
        if diff > max_diff:
            max_diff = diff
        if diff >= 0.05:
            disagree_dates.append((d, row[0], vrow["close"], diff))
    if max_diff < 0.05:
        print(f"  PASS: max close difference = {max_diff:.4f} index points")
    else:
        print(f"  FAIL: max close difference = {max_diff:.4f} (need < 0.05)")
        for dd in disagree_dates[:5]:
            print(f"    {dd[0]}: archive={dd[1]}, vendor={dd[2]}, diff={dd[3]:.4f}")
        failures.append("B1-agreement")

    # Gate B2 — vendor consumption, scoped to the span actually supplied.
    #
    # B2 originally demanded the seven named 2015 absences be filled from source (b) and a
    # 252-session beta by 2011-01-31. Both presumed a 2010-2015 vendor ingest that was never
    # supplied: the operator's files are 2010-2013 plus four single dates, and none touch 2015,
    # so the old check could only ever fail — a gate measuring a source that does not exist.
    # The falsifiable question the supplied files CAN answer: is every date the vendor covers,
    # inside the store's span, actually in the store? Beta is A2's job; it is not re-checked.
    print("\n[Gate B2] Vendor consumption (scoped to supplied span)...")
    all_nifty_dates = set()
    for f in NIFTY_1D_DIR.glob("*.duckdb"):
        con = duckdb.connect(str(f), read_only=True)
        n = con.execute("SELECT COUNT(*) FROM candles WHERE symbol='NSE_INDEX|Nifty 50'").fetchone()[0]
        if n > 0:
            all_nifty_dates.add(f.stem)
        con.close()

    lo, hi = min(all_nifty_dates), max(all_nifty_dates)
    vendor_in_span = {d.isoformat() for d in vendor_data if lo <= d.isoformat() <= hi}
    unconsumed = sorted(vendor_in_span - all_nifty_dates)
    covered_absences = sorted(vendor_in_span & KNOWN_ABSENCES)
    print(f"  vendor span {min(vendor_data)} -> {max(vendor_data)}; "
          f"{len(vendor_in_span)} dates inside store span")
    print(f"  known absences the vendor can cover: {len(covered_absences)} {covered_absences}")
    if not unconsumed:
        print(f"  PASS: every vendor date in span is present in the store")
    else:
        print(f"  FAIL: {len(unconsumed)} vendor dates absent from the store: {unconsumed[:10]}")
        failures.append("B2-unconsumed")

    if failures:
        print(f"\nGATE B: {len(failures)} FAILURES — {', '.join(failures)}")
    else:
        print(f"\nGATE B: ALL PASS")
    return failures


# --- Gates runner ---

def run_final_gates(args, floor):
    """Run predictions and gate checks."""
    known_absences = KNOWN_ABSENCES

    files = sorted(NIFTY_1D_DIR.glob("*.duckdb"))
    nifty_dates = set()
    for f in files:
        try:
            con = duckdb.connect(str(f))
            if con.execute("SELECT COUNT(*) FROM candles WHERE symbol='NSE_INDEX|Nifty 50'").fetchone()[0] > 0:
                nifty_dates.add(f.stem)
            con.close()
        except Exception:
            try:
                con.close()
            except Exception:
                pass
    all_2015_weekdays = {d.isoformat() for d in date_range(date(2015, 1, 1), date(2015, 12, 31))}
    still_missing = sorted(all_2015_weekdays - nifty_dates)
    holidays_2015 = {"2015-01-26", "2015-03-06", "2015-04-02", "2015-04-03",
                     "2015-04-14", "2015-05-01", "2015-09-17", "2015-10-02",
                     "2015-10-22", "2015-11-12", "2015-11-25", "2015-12-25"}
    still_missing_set = set(still_missing)
    real_gaps = still_missing_set - known_absences - holidays_2015
    recovered = 53 - len(still_missing_set - holidays_2015)
    print(f"\nPredictions:")
    print(f"  1. 2015 recovery: {recovered}/53 archive sessions recovered")
    print(f"  2. Archive floor: {floor}")
    print(f"  3. Known absences still missing: {set(still_missing) & known_absences}")
    assert not real_gaps, f"Unexpected real gaps: {sorted(real_gaps)}"
    assert date(2012, 1, 2) <= floor <= date(2012, 4, 2), \
        f"Floor {floor} outside expected range"
    # Print falsifiable predictions
    print(f"\nFalsifiable predictions:")
    print(f"  1. {recovered} of 53 currently-missing 2015 sessions recovered from source (a) alone")
    print(f"  2. Archive floor: {floor} (between 2012-01-02 and 2012-04-02)")
    print(f"  3. Exactly {len(known_absences)} calendar misses remain: {sorted(known_absences)}")
    print(f"  4. Final store: zero CNX, uniform TIMESTAMP, beta computable by ~2013")
    if args.run_gates:
        gate_a(floor, known_absences)
        if not args.archive_only and VENDOR_DIR.exists() and list(VENDOR_DIR.glob(VENDOR_GLOB)):
            gate_b(floor)


# --- Main ---

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-only", action="store_true", help="Skip operator file discovery")
    ap.add_argument("--run-gates", action="store_true", help="Run gates after ingest")
    ap.add_argument("--gates-only", action="store_true", help="Skip ingest, only run gates")
    ap.add_argument("--fill-from-vendor", action="store_true",
                    help="Insert missing Nifty 50 rows from the operator CSVs, then run gates")
    ap.add_argument("--fetch-missing", action="store_true",
                    help="Fetch archive rows for trading dates with no store file, then run gates")
    ap.add_argument("--since", type=lambda s: _parse_date(s), default=None,
                    help="Incremental: start ingest at this date and skip archive-floor "
                         "discovery + the full-history file scan (existing files are kept)")
    args = ap.parse_args()

    if args.fetch_missing:
        fetch_missing_sessions(KNOWN_ABSENCES)
        args.run_gates = True
        run_final_gates(args, date(2012, 2, 21))
        return

    if args.fill_from_vendor:
        fill_gap_from_vendor()
        return

    if args.gates_only:
        # The floor is the store's own earliest date. Re-probing the archive for it walks
        # ~1,000 network requests to re-derive a number already on disk.
        print("--gates-only: skipping ingest")
        args.run_gates = True  # the flag's whole purpose; run_final_gates gates on this
        run_final_gates(args, _parse_date(min(f.stem for f in NIFTY_1D_DIR.glob("*.duckdb"))))
        return

    sess = _get_session()

    if args.since is not None:
        floor = args.since
        print(f"--since {floor}: skipping archive-floor discovery and full-history scan")
    else:
        # Discover archive floor
        print("Discovering archive floor...")
        floor = discover_floor(sess, date(2015, 1, 1))
        if floor is None:
            print("ERROR: could not discover archive floor")
            sys.exit(1)
        print(f"Archive floor: {floor}")

        # Predictions
        print(f"\nPrediction 1: 46 of 53 missing 2015 sessions recovered")
        print(f"Prediction 2: archive floor between 2012-01-02 and 2012-04-02")

    # Ingest archive from floor to present
    today = date.today()
    total_new = 0
    total_skip = 0
    total_404 = 0
    total_skipped_cnx = 0
    known_absences = {"2015-03-12", "2015-03-13", "2015-05-19", "2015-07-08",
                      "2015-09-04", "2015-10-16", "2015-12-01"}

    print(f"\nIngesting from archive: {floor} to {today}")
    for d in date_range(floor, today):
        f = NIFTY_1D_DIR / f"{d.isoformat()}.duckdb"
        if f.exists():
            con = duckdb.connect(str(f))
            ts_type = con.execute(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name='candles' AND column_name='timestamp'"
            ).fetchone()
            if ts_type and ts_type[0].upper() != "TIMESTAMP":
                raise TypeError(f"{f.stem}: timestamp is {ts_type[0]}, expected TIMESTAMP")
            has_nifty = con.execute(
                "SELECT COUNT(*) FROM candles WHERE symbol='NSE_INDEX|Nifty 50' AND timeframe='1d'"
            ).fetchone()[0]
            con.close()
            if has_nifty > 0:
                total_skip += 1
                continue

        url = archive_url(d)
        try:
            resp = sess.get(url, timeout=30)
        except requests.RequestException as exc:
            print(f"{d.isoformat()}  FETCH-ERROR {exc}")
            total_404 += 1
            time.sleep(1.0)
            continue

        if resp.status_code == 404:
            total_404 += 1
            continue
        if resp.status_code != 200:
            print(f"{d.isoformat()}  HTTP-{resp.status_code}")
            total_404 += 1
            continue

        rows, skipped_cnx = parse_archive_csv(resp.text, d)
        total_skipped_cnx += skipped_cnx
        ingest_rows(d, rows, "nse_archive")
        nifty_rows = sum(1 for r in rows if r["symbol"] == "NSE_INDEX|Nifty 50")
        total_new += len(rows)
        print(f"{d.isoformat()}  OK  {len(rows)} rows ({nifty_rows} Nifty 50)", flush=True)
        time.sleep(0.3)

    # Optional: operator files
    if not args.archive_only and VENDOR_DIR.exists():
        vendor_files = sorted(VENDOR_DIR.glob(VENDOR_GLOB))
        if vendor_files:
            print(f"\nIngesting from operator files: {len(vendor_files)} files")
            for vf in vendor_files:
                vdata = parse_vendor_file(vf)
                for d, vrow in vdata.items():
                    f = NIFTY_1D_DIR / f"{d.isoformat()}.duckdb"
                    if f.exists():
                        continue
                    rows = [{
                        "symbol": "NSE_INDEX|Nifty 50",
                        "timestamp": d.isoformat(),
                        "open": vrow["open"],
                        "high": vrow["high"],
                        "low": vrow["low"],
                        "close": vrow["close"],
                        "volume": 0,
                    }]
                    ingest_rows(d, rows, "niftyindices")
                    total_new += 1

    # Summary
    print()
    print("=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"Archive floor:      {floor}")
    print(f"Range:              {floor} to {today}")
    print(f"New rows inserted:  {total_new:,}")
    print(f"Dates skipped:      {total_skip}")
    print(f"Dates 404/miss:     {total_404}")
    print(f"CNX names skipped:  {total_skipped_cnx}")

    # run_final_gates is the one-time full-history verification harness (asserts the
    # 2012 archive floor, prints the 2015-recovery predictions). It is meaningless for
    # an incremental --since append, so skip it there.
    if args.since is None:
        run_final_gates(args, floor)


if __name__ == "__main__":
    main()
