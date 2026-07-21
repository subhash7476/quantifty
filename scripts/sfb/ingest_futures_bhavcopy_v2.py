"""Download NSE F&O bhavcopy for FUTSTK and FUTIDX contracts.

Same approach as ingest_option_bhavcopy.py — downloads the same NSE F&O bhavcopy
ZIP archives (legacy + UDiFF) but filters for futures instead of options.

Ingests both:
  - Legacy format (archives.nseindia.com, pre-2024-07-05)
  - UDiFF format (nsearchives.nseindia.com, 2024-07-08+)

Usage:
    python scripts/sfb/ingest_futures_bhavcopy_v2.py
    python scripts/sfb/ingest_futures_bhavcopy_v2.py 2016-01-01 2026-07-31
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

DB_PATH = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"

_DEFAULT_START = date(2016, 2, 11)
_LEGACY_CUTOVER = date(2024, 7, 5)

_UDIFF_SESSION = None


def _get_udiff_session():
    global _UDIFF_SESSION
    if _UDIFF_SESSION is None:
        _UDIFF_SESSION = requests.Session()
        retry = Retry(total=3, backoff_factor=2.0,
                      status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=1,
                             pool_maxsize=1)
        _UDIFF_SESSION.mount("https://", adapter)
        _UDIFF_SESSION.headers.update({"User-Agent": "Mozilla/5.0"})
    return _UDIFF_SESSION


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS futures_bhavcopy (
    underlying    VARCHAR   NOT NULL,
    expiry_dt     DATE      NOT NULL,
    trade_date    DATE      NOT NULL,
    inst_type     VARCHAR   NOT NULL,
    open          DOUBLE,
    high          DOUBLE,
    low           DOUBLE,
    close         DOUBLE,
    settle        DOUBLE,
    contracts     BIGINT,
    val_in_lakh   DOUBLE,
    open_int      BIGINT,
    chg_in_oi     BIGINT,
    ingested_at   TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (underlying, expiry_dt, trade_date)
);
CREATE TABLE IF NOT EXISTS ingest_meta (
    trade_date DATE PRIMARY KEY,
    source     VARCHAR
);
"""

INSERT_SQL = """
INSERT INTO futures_bhavcopy
    (underlying, expiry_dt, trade_date, inst_type, open, high, low, close,
     settle, contracts, val_in_lakh, open_int, chg_in_oi, ingested_at)
SELECT underlying, expiry_dt, trade_date, inst_type, open, high, low, close,
       settle, contracts, val_in_lakh, open_int, chg_in_oi, ?
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
    header = lines[0].strip().split(",")
    idx = {h: i for i, h in enumerate(header)}
    rows = []

    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.strip().split(",")
        if len(cols) < len(header):
            continue
        instr = cols[idx["INSTRUMENT"]].strip()
        if instr not in ("FUTSTK", "FUTIDX"):
            continue
        try:
            expiry_dt = _parse_date(cols[idx["EXPIRY_DT"]])
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
            "trade_date": trade_date,
            "inst_type": instr,
            "open": _f(idx["OPEN"]),
            "high": _f(idx["HIGH"]),
            "low": _f(idx["LOW"]),
            "close": _f(idx["CLOSE"]),
            "settle": _f(idx["SETTLE_PR" if "SETTLE_PR" in idx else "SETTLE_PRICE"]),
            "contracts": _i(idx["CONTRACTS"]),
            "val_in_lakh": _f(idx["VAL_INLAKH"]),
            "open_int": _i(idx["OPEN_INT"]),
            "chg_in_oi": _i(idx["CHG_IN_OI"]),
        })

    if not rows:
        return 0
    return _insert_rows(con, pd.DataFrame(rows), "legacy")


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

    i_fin = idx.get("FinInstrmTp")
    i_symb = idx.get("TckrSymb")
    i_exp = idx.get("XpryDt")
    i_open = idx.get("OpnPric")
    i_high = idx.get("HghPric")
    i_low = idx.get("LwPric")
    i_close = idx.get("ClsPric")
    i_settle = idx.get("SttlmPric")
    i_oi = idx.get("OpnIntrst")
    i_choi = idx.get("ChngInOpnIntrst")
    i_vol = idx.get("TtlTradgVol")
    i_val = idx.get("TtlTrfVal")
    i_td = idx.get("TradDt")

    if None in (i_fin, i_symb, i_exp):
        return 0

    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.strip().split(",")
        if len(cols) < len(header):
            continue
        fin_type = cols[i_fin].strip()
        if fin_type not in ("STF", "IDF"):
            continue
        inst_type = "FUTSTK" if fin_type == "STF" else "FUTIDX"
        try:
            expiry_dt = _parse_date(cols[i_exp])
            trade_date = _parse_date(cols[i_td]) if i_td is not None else d
        except (ValueError, KeyError):
            continue

        def _f(idx2):
            try:
                return float(cols[idx2].strip() or 0)
            except (ValueError, IndexError):
                return None

        def _i(idx2):
            try:
                return int(float(cols[idx2].strip() or 0))
            except (ValueError, IndexError):
                return 0

        val_rupees = _f(i_val) if i_val is not None else None
        val_lakh = val_rupees / 100000.0 if val_rupees is not None else None

        rows.append({
            "underlying": cols[i_symb].strip(),
            "expiry_dt": expiry_dt,
            "trade_date": trade_date,
            "inst_type": inst_type,
            "open": _f(i_open) if i_open is not None else None,
            "high": _f(i_high) if i_high is not None else None,
            "low": _f(i_low) if i_low is not None else None,
            "close": _f(i_close) if i_close is not None else None,
            "settle": _f(i_settle) if i_settle is not None else None,
            "contracts": _i(i_vol) if i_vol is not None else 0,
            "val_in_lakh": val_lakh,
            "open_int": _i(i_oi) if i_oi is not None else 0,
            "chg_in_oi": _i(i_choi) if i_choi is not None else 0,
        })

    if not rows:
        return 0
    return _insert_rows(con, pd.DataFrame(rows), "foudiff")


def _insert_rows(con, df: pd.DataFrame, source: str) -> int:
    now_ts = datetime.now()
    df = df.drop_duplicates(subset=["underlying", "expiry_dt", "trade_date"], keep="last")
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute(INSERT_SQL, [now_ts, now_ts])
        # Record the source for this trade date if not already present
        if len(df) > 0:
            td = df["trade_date"].iloc[0]
            con.execute("""
                INSERT INTO ingest_meta (trade_date, source)
                VALUES (?, ?)
                ON CONFLICT (trade_date) DO NOTHING
            """, [td, source])
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
            "SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date = ?",
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
                print(f"{d.isoformat()}  OK    {count} future rows")
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
    r = con.execute("SELECT COUNT(*), MIN(trade_date), MAX(trade_date) FROM futures_bhavcopy").fetchone()
    print(f"Total in DB:    {r[0]:,} rows, {r[1]} to {r[2]}")

    r2 = con.execute("SELECT inst_type, COUNT(*), MIN(trade_date), MAX(trade_date) FROM futures_bhavcopy GROUP BY inst_type").fetchall()
    for row in r2:
        print(f"  {row[0]}: {row[1]:,} rows, {row[2]} to {row[3]}")
    con.close()


if __name__ == "__main__":
    main()
