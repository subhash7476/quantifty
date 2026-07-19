"""Standalone F&O ingestion runner — fetches FUTSTK data from NSE.

Run this from an unblocked network (not this dev environment).
Three strategies tried in order:
  1. nsepython.derivative_history() — NSE's direct F&O API
  2. UDiFF bhavcopy from nsearchives.nseindia.com (2024-06 onward)
  3. Legacy bhavcopy from archives.nseindia.com (pre-2024-07)

Usage:
    python scripts/sfb/run_fno_ingestion.py
    python scripts/sfb/run_fno_ingestion.py --start 2012-01-01 --end 2022-12-31
"""

import calendar
import io
import os
import sys
import time
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
INSTRUMENT_MASTER = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"
RAW_DIR = ROOT / "data" / "market_data" / "bhavcopy_raw"

DEFAULT_START = date(2012, 1, 1)
DEFAULT_END = date(2025, 12, 31)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS futures_bhavcopy (
    underlying    VARCHAR   NOT NULL,
    expiry_dt     DATE      NOT NULL,
    trade_date    DATE      NOT NULL,
    inst_type     VARCHAR   NOT NULL,
    open          DOUBLE, high    DOUBLE, low     DOUBLE, close   DOUBLE,
    settle        DOUBLE,
    contracts     BIGINT,
    val_in_lakh   DOUBLE,
    open_int      BIGINT,
    chg_in_oi     BIGINT,
    ingested_at   TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (underlying, expiry_dt, trade_date)
);
CREATE TABLE IF NOT EXISTS ingest_meta (
    trade_date DATE PRIMARY KEY, source VARCHAR
);
"""

INSERT_SQL = """
INSERT INTO futures_bhavcopy
    (underlying, expiry_dt, trade_date, inst_type,
     open, high, low, close, settle,
     contracts, val_in_lakh, open_int, chg_in_oi, ingested_at)
SELECT underlying, expiry_dt, trade_date, inst_type,
       open, high, low, close, settle,
       contracts, val_in_lakh, open_int, chg_in_oi, ?
FROM df
ON CONFLICT (underlying, expiry_dt, trade_date) DO UPDATE SET
    inst_type   = EXCLUDED.inst_type,
    open        = EXCLUDED.open,
    high        = EXCLUDED.high,
    low         = EXCLUDED.low,
    close       = EXCLUDED.close,
    settle      = EXCLUDED.settle,
    contracts   = EXCLUDED.contracts,
    val_in_lakh = EXCLUDED.val_in_lakh,
    open_int    = EXCLUDED.open_int,
    chg_in_oi   = EXCLUDED.chg_in_oi,
    ingested_at = ?
"""

MONTHS = ["JAN","FEB","MAR","APR","MAY","JUN",
          "JUL","AUG","SEP","OCT","NOV","DEC"]


def _pd(v):
    if v is None: return None
    try: return float(v)
    except: return None

def _pi(v):
    if v is None: return None
    try: return int(float(v))
    except: return None

def _parse_date(v):
    for fmt in ("%d-%b-%Y","%d-%B-%Y","%d-%m-%Y","%Y-%m-%d","%d-%b-%y"):
        try: return datetime.strptime(v.strip(), fmt).date()
        except: pass
    raise ValueError(f"Cannot parse: {v}")


# --- Strategy 1: nsepython ---

def _last_thursday(year, month):
    """Return the last Thursday of the given year/month (NSE F&O expiry)."""
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    d = date(year, month, last_day)
    while d.weekday() != 3:  # Thursday
        d -= timedelta(days=1)
    return d


def _get_expiries(start, end):
    """Compute all monthly expiries covering the date range.
    Uses last-Thursday rule with a one-month buffer on each side.
    
    NOTE: NSE shifts expiry to Wednesday when the last Thursday is a
    holiday. Strategies 2/3 (bhavcopy) naturally handle this since they
    fetch per-date from actual trade records. Strategy 1 may miss a few
    days on holiday-shifted expiries — bhavcopy is the authoritative source."""
    expiries = []
    y, m = start.year, start.month
    # Start one month before to catch the near contract active at start
    if m == 1:
        y -= 1; m = 12
    else:
        m -= 1
    end_y, end_m = end.year, end.month
    # Go one month past end to catch the far contract
    if end_m == 12:
        end_y += 1; end_m = 1
    else:
        end_m += 1
    while (y < end_y) or (y == end_y and m <= end_m):
        exp = _last_thursday(y, m)
        expiries.append(exp)
        if m == 12:
            y += 1; m = 1
        else:
            m += 1
    return expiries


def fetch_nsepython(symbol, start, end, expiry):
    try:
        from nsepython import derivative_history
        payload = derivative_history(
            symbol=symbol,
            start_date=start.strftime("%d-%m-%Y"),
            end_date=end.strftime("%d-%m-%Y"),
            instrumentType="FUTSTK",
            expiry_date=expiry.strftime("%d-%m-%Y"),
        )
        if not payload:
            return None
        rows = []
        for row in (payload if isinstance(payload, list) else [payload]):
            td = _parse_date(row.get("FH_TIMESTAMP",""))
            sym = (row.get("FH_SYMBOL") or "").strip()
            ex = _parse_date(row.get("FH_EXPIRY_DT",""))
            if not td or not sym or not ex:
                continue
            val = _pd(row.get("FH_TOT_TRADED_VAL",0))
            rows.append({
                "underlying": sym, "expiry_dt": ex, "trade_date": td,
                "inst_type": "FUTSTK",
                "open": _pd(row.get("FH_OPEN_PRICE",0)),
                "high": _pd(row.get("FH_HIGH_PRICE",0)),
                "low": _pd(row.get("FH_LOW_PRICE",0)),
                "close": _pd(row.get("FH_CLOSE_PRICE",0)),
                "settle": _pd(row.get("FH_SETTLE_PRICE",0)),
                "contracts": _pi(row.get("FH_TRADED_QTY",0)),
                "val_in_lakh": val / 1e5 if val else None,
                "open_int": _pi(row.get("FH_OPEN_INT",0)),
                "chg_in_oi": _pi(row.get("FH_CHG_IN_OI",0)),
            })
        return rows
    except Exception as e:
        print(f"    [{symbol} {expiry}] nsepython error: {type(e).__name__}: {e}", file=sys.stderr)
        return None


# --- NSE opener (shared by Strategies 2 & 3, stdlib only) ---

_NSE_OPENER = None

_BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;"
               "q=0.9,image/webp,image/apng,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def _get_nse_opener():
    global _NSE_OPENER
    if _NSE_OPENER is not None:
        return _NSE_OPENER
    import http.cookiejar, urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=ctx),
    )
    try:
        req = urllib.request.Request("https://www.nseindia.com",
                                      headers=_BROWSER_HEADERS)
        opener.open(req, timeout=20)
    except Exception:
        pass
    _NSE_OPENER = opener
    return opener


def _nse_fetch(url, timeout=30):
    """Fetch a URL through the cookie-enabled NSE opener. Returns body or None."""
    req = urllib.request.Request(url, headers=_BROWSER_HEADERS)
    try:
        resp = _get_nse_opener().open(req, timeout=timeout)
        if resp.status == 200:
            body = resp.read()
            if body[:4] == b"PK\x03\x04":
                return body
        elif resp.status == 404:
            pass
        else:
            return None  # distinguish from 404 for callers that care
    except Exception:
        pass
    return None


# --- Strategy 2: UDiFF bhavcopy ---

def fetch_udiff_zip(d):
    ds = d.strftime("%Y%m%d")
    url = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{ds}_F_0000.csv.zip"
    try:
        return _nse_fetch(url, timeout=30)
    except Exception as e:
        print(f"    [{d}] fetch error: {type(e).__name__}: {e}", file=sys.stderr)
    return None

def parse_udiff_zip(raw, d):
    z = zipfile.ZipFile(io.BytesIO(raw))
    lines = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    hdr = [h.strip() for h in lines[0].strip().split(",")]
    idx = {h: i for i, h in enumerate(hdr)}
    rows = []
    for line in lines[1:]:
        if not line.strip(): continue
        c = line.split(",")
        if len(c) < len(hdr): continue
        if c[idx["FinInstrmTp"]].strip() not in ("STF", "IDF"): continue
        try:
            td = _parse_date(c[idx["TradDt"]])
            ex = _parse_date(c[idx["XpryDt"]])
        except:
            continue
        val = _pd(c[idx["TtlTrfVal"]])
        rows.append({
            "underlying": c[idx["TckrSymb"]].strip(),
            "expiry_dt": ex, "trade_date": td,
            "inst_type": "FUTSTK" if c[idx["FinInstrmTp"]].strip() == "STF" else "FUTIDX",
            "open": _pd(c[idx["OpnPric"]]),
            "high": _pd(c[idx["HghPric"]]),
            "low": _pd(c[idx["LwPric"]]),
            "close": _pd(c[idx["ClsPric"]]),
            "settle": _pd(c[idx["SttlmPric"]]),
            "contracts": _pi(c[idx["TtlTradgVol"]]),
            "val_in_lakh": val / 1e5 if val else None,
            "open_int": _pi(c[idx["OpnIntrst"]]),
            "chg_in_oi": _pi(c[idx["ChngInOpnIntrst"]]),
        })
    return rows


# --- Strategy 3: Legacy bhavcopy ---

def fetch_legacy_zip(d):
    mon = MONTHS[d.month - 1]
    url = (f"https://archives.nseindia.com/content/historical/DERIVATIVES/"
           f"{d.year}/{mon}/fo{d.day:02d}{mon}{d.year}bhav.csv.zip")
    try:
        return _nse_fetch(url, timeout=30)
    except Exception as e:
        print(f"    [{d}] fetch error: {type(e).__name__}: {e}", file=sys.stderr)
    return None

def parse_legacy_zip(raw, d):
    z = zipfile.ZipFile(io.BytesIO(raw))
    lines = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    hdr = [h.strip() for h in lines[0].strip().split(",")]
    idx = {h: i for i, h in enumerate(hdr)}
    rows = []
    for line in lines[1:]:
        if not line.strip(): continue
        c = line.split(",")
        if len(c) < len(hdr): continue
        if c[idx["INSTRUMENT"]].strip() not in ("FUTSTK", "FUTIDX"): continue
        try:
            td = _parse_date(c[idx["TIMESTAMP"]]) if "TIMESTAMP" in idx else d
            ex = _parse_date(c[idx["EXPIRY_DT"]])
        except:
            continue
        rows.append({
            "underlying": c[idx["SYMBOL"]].strip(),
            "expiry_dt": ex, "trade_date": td,
            "inst_type": c[idx["INSTRUMENT"]].strip(),
            "open": _pd(c[idx["OPEN"]]),
            "high": _pd(c[idx["HIGH"]]),
            "low": _pd(c[idx["LOW"]]),
            "close": _pd(c[idx["CLOSE"]]),
            "settle": _pd(c[idx["SETTLE_PR"]]),
            "contracts": _pi(c[idx["CONTRACTS"]]),
            "val_in_lakh": _pd(c[idx["VAL_INLAKH"]]),
            "open_int": _pi(c[idx["OPEN_INT"]]),
            "chg_in_oi": _pi(c[idx["CHG_IN_OI"]]),
        })
    return rows


# --- Main ---

def _insert(con, rows):
    if not rows: return 0
    import pandas as pd
    df = pd.DataFrame(rows).drop_duplicates(
        subset=["underlying","expiry_dt","trade_date"], keep="last")
    now = datetime.now()
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute(INSERT_SQL, [now, now])
        con.execute("COMMIT")
    except:
        con.execute("ROLLBACK")
        raise
    return len(df)


def _get_futstk_symbols():
    """Get FUTSTK symbols from the instrument master or a hardcoded starter list."""
    if INSTRUMENT_MASTER.exists():
        try:
            im = duckdb.connect(str(INSTRUMENT_MASTER))
            syms = [r[0] for r in im.execute(
                "SELECT DISTINCT symbol FROM tradingsymbols "
                "WHERE instrument_type='FUTSTK' ORDER BY symbol"
            ).fetchall()]
            im.close()
            if syms:
                return syms
        except:
            pass
    # Hardcoded starter list of liquid FUTSTK symbols
    return [
        "RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","ITC","SBIN",
        "BHARTIARTL","KOTAKBANK","LT","WIPRO","AXISBANK","HCLTECH",
        "MARUTI","TATAMOTORS","SUNPHARMA","TITAN","BAJFINANCE","ADANIENT",
        "NTPC","ONGC","POWERGRID","M&M","TATASTEEL","HINDUNILVR",
        "ULTRACEMCO","ASIANPAINT","BAJAJFINSV","HDFC","DMART",
        "NESTLEIND","JSWSTEEL","HDFCLIFE","SBILIFE","TECHM",
        "INDUSINDBK","DIVISLAB","DRREDDY","CIPLA","GRASIM",
        "BRITANNIA","EICHERMOT","APOLLOHOSP","COALINDIA","BPCL",
        "IOC","HINDALCO","ADANIPORTS","GAIL","LICI",
    ]


def date_range(start, end):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def main():
    import argparse, duckdb, pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=lambda s: _parse_date(s), default=DEFAULT_START)
    ap.add_argument("--end", type=lambda s: _parse_date(s), default=DEFAULT_END)
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--skip-nsepython", action="store_true",
                    help="Skip nsepython strategy")
    ap.add_argument("--udiff-only", action="store_true",
                    help="Only use UDiFF format (2024-06 onward)")
    args = ap.parse_args()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute(SCHEMA_SQL)

    total = 0

    # Quick connectivity probe (uses the NSE opener)
    print("Probing NSE connectivity...")
    nse_blocked = True
    try:
        import urllib.request
        probe_url = ("https://www.nseindia.com/api/historical/derivatives"
                     "?symbol=RELIANCE&expiry_date=30-01-2025&instrumentType=FUTSTK"
                     "&from=01-01-2025&to=10-01-2025")
        req = urllib.request.Request(probe_url, headers=_BROWSER_HEADERS)
        resp = _get_nse_opener().open(req, timeout=15)
        if resp.status == 200:
            body = resp.read()
            if b'"data"' in body:
                nse_blocked = False
                print("  NSE API: OK")
            else:
                print(f"  NSE API: HTTP 200 but no data (likely blocked)")
        else:
            print(f"  NSE API: HTTP {resp.status} (blocked)")
    except Exception as e:
        print(f"  NSE API: UNREACHABLE ({type(e).__name__}: {e})")
    if nse_blocked:
        print("  => NSE is blocking this IP. Run from a residential connection.")
        print("     All three strategies will fail. Aborting.\n")
        con.close()
        return
    print()

    # Strategy 1: nsepython (per-symbol per-expiry)
    if not args.skip_nsepython and not args.udiff_only:
        print("=== Strategy 1: nsepython API ===")
        symbols = _get_futstk_symbols()
        # Compute expiries programmatically — the instrument master only has
        # recent contracts, not historical ones from 2012.
        expiries_list = _get_expiries(args.start, args.end)
        print(f"  {len(symbols)} symbols, {len(expiries_list)} monthly expiries "
              f"({expiries_list[0]} to {expiries_list[-1]})")
        n_checked = 0
        for i, symbol in enumerate(symbols):
            if i > 0 and i % 20 == 0:
                print(f"  {i}/{len(symbols)}, {total:,} rows so far")
            for exp in expiries_list:
                n_checked += 1
                result = fetch_nsepython(symbol, args.start, args.end, exp)
                if result:
                    n = _insert(con, result)
                    if n:
                        total += n
                        print(f"  {symbol} {exp}: {n} rows")
                time.sleep(args.sleep)
        print(f"  Strategy 1 done: {n_checked} calls, {total:,} rows total")

    # Strategy 2: UDiFF bhavcopy (per-date)
    udiff_start = max(args.start, date(2024, 6, 1))
    if udiff_start <= args.end:
        print(f"\n=== Strategy 2: UDiFF bhavcopy ({udiff_start} to {args.end}) ===")
        udiff_hits = udiff_misses = 0
        for d in date_range(udiff_start, args.end):
            existing = con.execute(
                "SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date=?", [d]
            ).fetchone()[0]
            if existing > 0:
                continue
            raw = fetch_udiff_zip(d)
            if raw:
                rows = parse_udiff_zip(raw, d)
                if rows:
                    n = _insert(con, rows)
                    if n:
                        total += n
                        udiff_hits += 1
                        print(f"  {d}: {n} rows")
                else:
                    udiff_misses += 1
            else:
                udiff_misses += 1
            time.sleep(args.sleep)
        print(f"  Strategy 2 done: {udiff_hits} hits, {udiff_misses} misses")

    # Strategy 3: Legacy bhavcopy (per-date, pre-2024)
    if not args.udiff_only:
        legacy_end = min(args.end, date(2024, 7, 5))
        if args.start <= legacy_end:
            legacy_start = max(args.start, date(2010,1,1))
            print(f"\n=== Strategy 3: Legacy bhavcopy ({legacy_start} to {legacy_end}) ===")
            legacy_hits = legacy_misses = 0
            for d in date_range(legacy_start, legacy_end):
                existing = con.execute(
                    "SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date=?", [d]
                ).fetchone()[0]
                if existing > 0:
                    continue
                raw = fetch_legacy_zip(d)
                if raw:
                    rows = parse_legacy_zip(raw, d)
                    if rows:
                        n = _insert(con, rows)
                        if n:
                            total += n
                            legacy_hits += 1
                            print(f"  {d}: {n} rows")
                    else:
                        legacy_misses += 1
                else:
                    legacy_misses += 1
                time.sleep(args.sleep)
            print(f"  Strategy 3 done: {legacy_hits} hits, {legacy_misses} misses")

    con.close()

    # Final stats
    con = duckdb.connect(str(DB_PATH))
    r = con.execute("SELECT COUNT(*), MIN(trade_date), MAX(trade_date) FROM futures_bhavcopy").fetchone()
    train = con.execute("SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date <= '2018-12-31'").fetchone()[0]
    holdout = con.execute("SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date > '2018-12-31' AND trade_date <= '2022-12-30'").fetchone()[0]
    sealed = con.execute("SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date > '2022-12-30'").fetchone()[0]
    con.close()

    print("\n" + "="*56)
    print("INGESTION COMPLETE")
    print("="*56)
    print(f"Total rows inserted this run: {total:,}")
    print(f"Store: {r[0]:,} rows, {r[1]} to {r[2]}")
    print(f"  TRAIN (<=2018):    {train:,} rows")
    print(f"  HOLDOUT (2019-22): {holdout:,} rows")
    print(f"  SEALED (>2022):    {sealed:,} rows")
    if train > 50000 and holdout > 2500:
        print("\nTRAIN and HOLDOUT thresholds met — ready for D2/D3/D5.")
    else:
        print("\nInsufficient TRAIN/HOLDOUT — D5 degeneracy gates will fail.")


if __name__ == "__main__":
    main()
