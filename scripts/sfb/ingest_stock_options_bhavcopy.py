"""Download NSE F&O bhavcopy for OPTSTK (single-stock options).

Same approach as ingest_option_bhavcopy.py — downloads from the same NSE F&O
bhavcopy ZIP archives but filters for OPTSTK/STO (single-stock options)
instead of OPTIDX/IDO (index options).

Usage:
    python scripts/sfb/ingest_stock_options_bhavcopy.py
    python scripts/sfb/ingest_stock_options_bhavcopy.py 2016-02-11 2026-07-20
"""

import io
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

import duckdb
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "stock_options_bhavcopy.duckdb"

_DEFAULT_START = date(2016, 2, 11)
_LEGACY_CUTOVER = date(2024, 7, 5)

_UDIFF_SESSION = None


def _get_udiff_session():
    global _UDIFF_SESSION
    if _UDIFF_SESSION is None:
        _UDIFF_SESSION = requests.Session()
        retry = Retry(total=3, backoff_factor=2.0,
                      status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=1, pool_maxsize=1)
        _UDIFF_SESSION.mount("https://", adapter)
        _UDIFF_SESSION.headers.update({"User-Agent": "Mozilla/5.0"})
    return _UDIFF_SESSION


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stock_options_bhavcopy (
    underlying    VARCHAR   NOT NULL,
    expiry_dt     DATE      NOT NULL,
    strike        DOUBLE    NOT NULL,
    option_type   VARCHAR   NOT NULL,
    open          DOUBLE,
    high          DOUBLE,
    low           DOUBLE,
    close         DOUBLE,
    settle        DOUBLE,
    contracts     INTEGER,
    val_in_lakh   DOUBLE,
    open_int      INTEGER,
    chg_in_oi     INTEGER,
    trade_date    DATE      NOT NULL,
    ingested_at   TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (underlying, expiry_dt, strike, option_type, trade_date)
)
"""

INSERT_SQL = """
INSERT INTO stock_options_bhavcopy
    (underlying, expiry_dt, strike, option_type, open, high, low, close,
     settle, contracts, val_in_lakh, open_int, chg_in_oi, trade_date,
     ingested_at)
SELECT underlying, expiry_dt, strike, option_type, open, high, low,
       close, settle, contracts, val_in_lakh, open_int, chg_in_oi,
       trade_date, ?
FROM df
ON CONFLICT (underlying, expiry_dt, strike, option_type, trade_date)
DO UPDATE SET
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


def date_range(start: date, end: date):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


# --- Legacy format (pre-2024-07-05) ------------------------------------------

def legacy_url(d: date) -> str:
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
              "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    yyyy = d.strftime("%Y")
    mon = months[d.month - 1]
    dd = d.strftime("%d")
    return (f"https://archives.nseindia.com/content/historical/DERIVATIVES/"
            f"{yyyy}/{mon}/fo{dd}{mon}{yyyy}bhav.csv.zip")


def _parse_date(val: str):
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date: {val}")


def _ingest_legacy(con, d: date) -> int:
    url = legacy_url(d)
    resp = requests.get(url, timeout=60)
    if resp.status_code == 404:
        return 0
    resp.raise_for_status()

    z = ZipFile(io.BytesIO(resp.content))
    csv_raw = z.read(z.namelist()[0]).decode("latin-1")
    lines = csv_raw.split("\n")
    header = [h.strip() for h in lines[0].strip().split(",")]
    idx = {h: i for i, h in enumerate(header)}

    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.strip().split(",")
        if len(cols) < len(header):
            continue
        instr = cols[idx["INSTRUMENT"]].strip()
        if instr != "OPTSTK":
            continue
        opt_type = cols[idx["OPTION_TYP"]].strip()
        if opt_type not in ("CE", "PE"):
            continue
        try:
            expiry_dt = _parse_date(cols[idx["EXPIRY_DT"]])
            strike = float(cols[idx["STRIKE_PR"]])
            trade_date = _parse_date(cols[idx["TIMESTAMP"]]) if "TIMESTAMP" in idx else d
        except (ValueError, KeyError):
            continue

        def _f(i):
            try:
                return float(cols[i])
            except (ValueError, IndexError):
                return None

        def _i(i):
            try:
                return int(float(cols[i]))
            except (ValueError, IndexError):
                return 0

        rows.append({
            "underlying": cols[idx["SYMBOL"]].strip(),
            "expiry_dt": expiry_dt,
            "strike": strike,
            "option_type": opt_type,
            "open": _f(idx["OPEN"]),
            "high": _f(idx["HIGH"]),
            "low": _f(idx["LOW"]),
            "close": _f(idx["CLOSE"]),
            "settle": _f(idx["SETTLE_PR"]),
            "contracts": _i(idx["CONTRACTS"]),
            "val_in_lakh": _f(idx["VAL_INLAKH"]),
            "open_int": _i(idx["OPEN_INT"]),
            "chg_in_oi": _i(idx["CHG_IN_OI"]),
            "trade_date": trade_date,
        })

    if not rows:
        return 0
    return _insert_rows(con, pd.DataFrame(rows))


# --- UDiFF format (2024-07-08+) -----------------------------------------------

def udiff_url(d: date) -> str:
    ds = d.strftime("%Y%m%d")
    return (f"https://nsearchives.nseindia.com/content/fo/"
            f"BhavCopy_NSE_FO_0_0_0_{ds}_F_0000.csv.zip")


def _ingest_udiff(con, d: date) -> int:
    url = udiff_url(d)
    sess = _get_udiff_session()
    resp = sess.get(url, timeout=(15, 120))
    if resp.status_code == 404:
        return 0
    resp.raise_for_status()

    z = ZipFile(io.BytesIO(resp.content))
    csv_raw = z.read(z.namelist()[0]).decode("latin-1")
    lines = csv_raw.split("\n")
    header = [h.strip() for h in lines[0].strip().split(",")]
    idx = {h: i for i, h in enumerate(header)}

    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.strip().split(",")
        if len(cols) < len(header):
            continue
        if cols[idx["FinInstrmTp"]].strip() != "STO":
            continue
        opt_type = cols[idx["OptnTp"]].strip()
        if opt_type not in ("CE", "PE"):
            continue

        try:
            expiry_dt = _parse_date(cols[idx["XpryDt"]])
            strike = float(cols[idx["StrkPric"]].strip())
            trade_date = _parse_date(cols[idx["TradDt"]])
        except (ValueError, KeyError):
            continue

        def _f(i):
            try:
                return float(cols[i].strip() or 0)
            except (ValueError, IndexError):
                return None

        def _i(i):
            try:
                return int(float(cols[i].strip() or 0))
            except (ValueError, IndexError):
                return 0

        val_rupees = _f(idx["TtlTrfVal"])
        val_lakh = val_rupees / 100000.0 if val_rupees is not None else None

        rows.append({
            "underlying": cols[idx["TckrSymb"]].strip(),
            "expiry_dt": expiry_dt,
            "strike": strike,
            "option_type": opt_type,
            "open": _f(idx["OpnPric"]),
            "high": _f(idx["HghPric"]),
            "low": _f(idx["LwPric"]),
            "close": _f(idx["ClsPric"]),
            "settle": _f(idx["SttlmPric"]),
            "contracts": _i(idx["TtlTradgVol"]),
            "val_in_lakh": val_lakh,
            "open_int": _i(idx["OpnIntrst"]),
            "chg_in_oi": _i(idx["ChngInOpnIntrst"]),
            "trade_date": trade_date,
        })

    if not rows:
        return 0
    return _insert_rows(con, pd.DataFrame(rows))


def _insert_rows(con, df: pd.DataFrame) -> int:
    now_ts = datetime.now()
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute(INSERT_SQL, [now_ts, now_ts])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return len(df)


def _ingest_single_day(con, d: date) -> int:
    if d <= _LEGACY_CUTOVER:
        count = _ingest_legacy(con, d)
        if count > 0:
            return count
        if d >= date(2024, 6, 1):
            return _ingest_udiff(con, d)
        return 0
    else:
        return _ingest_udiff(con, d)


def main():
    start = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_START
    end = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today() - timedelta(days=1)

    os.makedirs(DB_PATH.parent, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))
    con.execute(SCHEMA_SQL)

    total_inserted = 0
    total_skipped = 0
    total_404 = 0
    consec_both_404 = 0

    for d in date_range(start, end):
        existing = con.execute(
            "SELECT COUNT(*) FROM stock_options_bhavcopy WHERE trade_date = ?",
            [d],
        ).fetchone()[0]
        if existing > 0:
            print(f"{d.isoformat()}  SKIP  ({existing} rows already present)")
            total_skipped += 1
            consec_both_404 = 0
            continue

        if consec_both_404 >= 30 and d <= _LEGACY_CUTOVER:
            print(f"{d.isoformat()}  SKIP  (legacy exhausted, 30+ consecutive misses)")
            total_skipped += 1
            continue

        try:
            count = _ingest_single_day(con, d)
            if count > 0:
                print(f"{d.isoformat()}  OK    {count} stock option rows")
                total_inserted += count
                consec_both_404 = 0
                time.sleep(0.5)
            else:
                print(f"{d.isoformat()}  404   (no data)")
                total_404 += 1
                consec_both_404 += 1
        except Exception as exc:
            print(f"{d.isoformat()}  ERROR {exc}")
            total_404 += 1
            consec_both_404 += 1

    con.close()

    print()
    print("=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"Date range:     {start} to {end}")
    print(f"Rows inserted this run: {total_inserted:,}")
    print(f"Dates skipped (already present): {total_skipped}")
    print(f"Dates with 404: {total_404}")

    con = duckdb.connect(str(DB_PATH))
    r = con.execute("SELECT COUNT(*), MIN(trade_date), MAX(trade_date) FROM stock_options_bhavcopy").fetchone()
    print(f"Total in DB:    {r[0]:,} rows, {r[1]} to {r[2]}")
    print(f"Distinct underlyings: {con.execute('SELECT COUNT(DISTINCT underlying) FROM stock_options_bhavcopy').fetchone()[0]:,}")
    con.close()


if __name__ == "__main__":
    main()
