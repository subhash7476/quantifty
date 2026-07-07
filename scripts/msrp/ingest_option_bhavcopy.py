"""Download NSE F&O bhavcopy for Nifty weekly options (2023-01-01 to yesterday).

Ingests both the legacy format (archives.nseindia.com, pre-2024-07-05) and the
UDiFF format (nsearchives.nseindia.com, 2024-07-08+), mapping into a unified
DuckDB schema. Filters symbol == 'NIFTY' exactly (not NIFTYNXT50).

Usage:
    python scripts/msrp/ingest_option_bhavcopy.py
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

DB_PATH = ROOT / "data" / "market_data" / "options_bhavcopy.duckdb"
NIFTY_1D_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
REPORT_PATH = ROOT / "docs" / "reports" / "MSRP_PHASE7_BHAVCOPY_AUDIT.md"

NIFTY_SYMBOL = "NSE_INDEX|Nifty 50"
LEGACY_CUTOVER = date(2024, 7, 5)

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
CREATE TABLE IF NOT EXISTS option_bhavcopy (
    symbol       VARCHAR   NOT NULL,
    expiry_dt    DATE      NOT NULL,
    strike       DOUBLE    NOT NULL,
    option_type  VARCHAR   NOT NULL,
    open         DOUBLE,
    high         DOUBLE,
    low          DOUBLE,
    close        DOUBLE,
    settle       DOUBLE,
    contracts    INTEGER,
    val_in_lakh  DOUBLE,
    open_int     INTEGER,
    chg_in_oi    INTEGER,
    trade_date   DATE      NOT NULL,
    ingested_at  TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (symbol, expiry_dt, strike, option_type, trade_date)
)
"""

INSERT_SQL = """
INSERT INTO option_bhavcopy
    (symbol, expiry_dt, strike, option_type, open, high, low, close,
     settle, contracts, val_in_lakh, open_int, chg_in_oi, trade_date,
     ingested_at)
SELECT symbol, expiry_dt, strike, option_type, open, high, low,
       close, settle, contracts, val_in_lakh, open_int, chg_in_oi,
       trade_date, ?
FROM df
ON CONFLICT (symbol, expiry_dt, strike, option_type, trade_date)
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
    header = lines[0].strip().split(",")
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.strip().split(",")
        if len(cols) < len(header):
            continue
        # F2 fix: exact symbol match
        symbol = cols[1].strip()
        if symbol != "NIFTY":
            continue
        instr = cols[0].strip()
        if instr != "OPTIDX":
            continue
        opt_type = cols[4].strip()
        if opt_type not in ("CE", "PE"):
            continue
        try:
            expiry_dt = _parse_date(cols[2])
            strike = float(cols[3])
        except (ValueError, KeyError):
            continue

        def _f(i):
            try:
                return float(cols[i])
            except (ValueError, IndexError):
                return None

        def _i(i):
            try:
                return int(cols[i])
            except (ValueError, IndexError):
                return 0

        trade_date = _parse_date(cols[14]) if len(cols) > 14 else d

        rows.append({
            "symbol": symbol, "expiry_dt": expiry_dt, "strike": strike,
            "option_type": opt_type,
            "open": _f(5), "high": _f(6), "low": _f(7), "close": _f(8),
            "settle": _f(9), "contracts": _i(10), "val_in_lakh": _f(11),
            "open_int": _i(12), "chg_in_oi": _i(13), "trade_date": trade_date,
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
    header = lines[0].strip().split(",")

    def _col_idx(name):
        for i, h in enumerate(header):
            if h.strip() == name:
                return i
        return None

    i_instr = _col_idx("FinInstrmTp")
    i_symb = _col_idx("TckrSymb")
    i_exp = _col_idx("XpryDt")
    i_strike = _col_idx("StrkPric")
    i_opt = _col_idx("OptnTp")
    i_open = _col_idx("OpnPric")
    i_high = _col_idx("HghPric")
    i_low = _col_idx("LwPric")
    i_close = _col_idx("ClsPric")
    i_settle = _col_idx("SttlmPric")
    i_oi = _col_idx("OpnIntrst")
    i_choi = _col_idx("ChngInOpnIntrst")
    i_vol = _col_idx("TtlTradgVol")
    i_val = _col_idx("TtlTrfVal")
    i_td = _col_idx("TradDt")

    if None in (i_instr, i_symb, i_strike, i_opt):
        return 0  # unexpected header

    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.strip().split(",")
        if len(cols) < len(header):
            continue
        if cols[i_instr].strip() != "IDO":
            continue
        symbol = cols[i_symb].strip()
        if symbol != "NIFTY":  # F2: exact match
            continue
        opt_type = cols[i_opt].strip()
        if opt_type not in ("CE", "PE"):
            continue

        try:
            expiry_dt = _parse_date(cols[i_exp])
            strike = float(cols[i_strike].strip())
        except (ValueError, KeyError):
            continue

        def _f(idx):
            try:
                return float(cols[idx].strip() or 0)
            except (ValueError, IndexError):
                return None

        def _i(idx):
            try:
                return int(float(cols[idx].strip() or 0))
            except (ValueError, IndexError):
                return 0

        trade_date = _parse_date(cols[i_td]) if i_td is not None else d

        # UDiFF TtlTrfVal is in rupees; legacy is in lakhs
        val_rupees = _f(i_val)
        val_lakh = val_rupees / 100000.0 if val_rupees is not None else None

        rows.append({
            "symbol": symbol, "expiry_dt": expiry_dt,
            "strike": strike, "option_type": opt_type,
            "open": _f(i_open), "high": _f(i_high), "low": _f(i_low),
            "close": _f(i_close), "settle": _f(i_settle),
            "contracts": _i(i_vol), "val_in_lakh": val_lakh,
            "open_int": _i(i_oi), "chg_in_oi": _i(i_choi),
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


# --- Ingestion loop ------------------------------------------------------------

def _ingest_single_day(con, d: date) -> int:
    """Try legacy then UDiFF; return rows inserted (0 means skip/404)."""
    if d <= LEGACY_CUTOVER:
        # Try legacy format first
        count = _ingest_legacy(con, d)
        if count > 0:
            return count
        # Legacy empty/404 — also try UDiFF (NSE may have backfilled)
        if d >= date(2024, 6, 1):
            return _ingest_udiff(con, d)
        return 0
    else:
        return _ingest_udiff(con, d)


# --- Audit --------------------------------------------------------------------

def load_nifty_close(trade_date: date) -> float | None:
    f = NIFTY_1D_DIR / f"{trade_date.isoformat()}.duckdb"
    if not f.exists():
        return None
    con = duckdb.connect(str(f), read_only=True)
    try:
        row = con.execute(
            "SELECT close FROM candles WHERE symbol = ?",
            [NIFTY_SYMBOL],
        ).fetchone()
        return float(row[0]) if row else None
    finally:
        con.close()


def run_audit(con: duckdb.DuckDBPyConnection) -> str:
    lines = []

    total = con.execute("SELECT COUNT(*) FROM option_bhavcopy").fetchone()[0]
    dr = con.execute(
        "SELECT MIN(trade_date), MAX(trade_date) FROM option_bhavcopy"
    ).fetchone()
    num_exp = con.execute(
        "SELECT COUNT(DISTINCT expiry_dt) FROM option_bhavcopy"
    ).fetchone()[0]
    n_tradedays = con.execute(
        "SELECT COUNT(DISTINCT trade_date) FROM option_bhavcopy"
    ).fetchone()[0]
    lines.append(f"Total rows ingested: {total:,}")
    lines.append(f"Date range: {dr[0]} to {dr[1]}")
    lines.append(f"Distinct trade dates: {n_tradedays}")
    lines.append(f"Distinct expiry dates: {num_exp}")
    lines.append("")

    # --- per-expiry weekly liquidity (F3 fix: filter to weekly-like <= 30 DTE,
    #     remove ZeroCtrDays name, show distinct trade dates with 0 volume)
    lines.append("## Per-Expiry Weekly Liquidity")
    lines.append(
        "Expiries with <= 30 DTE from their earliest observation (the weekly/fortnightly set). "
        "ZeroVolDays = distinct trade_dates where summed daily contracts = 0."
    )
    weekly = con.execute(
        """
        WITH ranked AS (
            SELECT expiry_dt, trade_date,
                   COUNT(DISTINCT strike) AS n_strikes,
                   CAST(AVG(contracts) AS BIGINT) AS avg_ctr,
                   CAST(AVG(open_int) AS BIGINT) AS avg_oi,
                   SUM(contracts) AS day_ctr
            FROM option_bhavcopy
            GROUP BY expiry_dt, trade_date
        ),
        by_exp AS (
            SELECT expiry_dt,
                   MIN(trade_date) AS first_seen,
                   MAX(trade_date) AS last_seen,
                   COUNT(DISTINCT trade_date) AS n_trade_days,
                   CAST(AVG(avg_ctr) AS BIGINT) AS avg_contracts,
                   CAST(AVG(avg_oi) AS BIGINT) AS avg_oi,
                   COUNT(DISTINCT trade_date) FILTER (WHERE day_ctr = 0) AS zero_vol_days
            FROM ranked
            GROUP BY expiry_dt
        )
        SELECT expiry_dt, n_trade_days AS days_observed,
               avg_contracts, avg_oi, zero_vol_days
        FROM by_exp
        WHERE (last_seen - first_seen) <= 30
        ORDER BY expiry_dt
        """
    ).fetchall()

    if weekly:
        fmt = "{:<14s}  {:>5s}  {:>12s}  {:>10s}  {:>12s}"
        lines.append(fmt.format("Expiry", "Days", "Avg Ctr", "Avg OI", "ZeroVolDays"))
        lines.append("-" * 60)
        for r in weekly:
            lines.append(fmt.format(str(r[0]), str(r[1]), str(r[2]), str(r[3]),
                                    str(r[4])))
    else:
        lines.append("(no weekly expiry data)")
    lines.append("")

    # --- ATM liquidity audit (split by era)
    lines.append("## ATM-Adjacent Strike Quality (\u00b1200 from Nifty close)")
    lines.append("")

    trade_dates = con.execute(
        "SELECT DISTINCT trade_date FROM option_bhavcopy ORDER BY trade_date"
    ).fetchall()

    atm_records = []
    for (td,) in trade_dates:
        nifty_close = load_nifty_close(td)
        if nifty_close is None:
            continue
        atm_low = nifty_close - 200
        atm_high = nifty_close + 200
        rows = con.execute(
            """
            SELECT strike, option_type, expiry_dt, open, close, settle,
                   contracts, open_int
            FROM option_bhavcopy
            WHERE trade_date = ? AND strike BETWEEN ? AND ?
            ORDER BY strike, option_type
            """,
            [td, atm_low, atm_high],
        ).fetchall()
        for r in rows:
            atm_records.append((td, nifty_close) + r)

    if atm_records:
        df_atm = pd.DataFrame(
            atm_records,
            columns=["trade_date", "nifty_close", "strike", "option_type",
                     "expiry_dt", "open", "close", "settle",
                     "contracts", "open_int"],
        )

        # Split by expiry regime
        df_atm["era"] = df_atm["trade_date"].apply(
            lambda td: "Thursday regime" if td < date(2026, 1, 1) else "Tuesday regime"
        )

        for era_label in ("Thursday regime", "Tuesday regime"):
            era = df_atm[df_atm["era"] == era_label]
            if len(era) == 0:
                lines.append(f"**{era_label}**: no data")
                lines.append("")
                continue
            td_unique = era["trade_date"].nunique()
            days_active = era.groupby("trade_date")["contracts"].sum().gt(0).sum()
            pct = round(100 * days_active / td_unique, 1) if td_unique else 0
            avg_oi = int(era["open_int"].mean())

            # F3 fix: stale-open grouped by (expiry_dt, strike, option_type)
            era_sorted = era.sort_values(
                ["expiry_dt", "strike", "option_type", "trade_date"]
            )
            era_sorted["prev_settle"] = era_sorted.groupby(
                ["expiry_dt", "strike", "option_type"]
            )["settle"].shift(1)
            stale = (
                (era_sorted["open"] == era_sorted["prev_settle"])
                & (era_sorted["contracts"] < 10)
            ).sum()

            lines.append(f"### {era_label}")
            lines.append(f"- Trade dates: {td_unique}")
            lines.append(f"- Days with ATM contracts > 0: {days_active}/{td_unique} ({pct}%)")
            lines.append(f"- Avg ATM open interest: {avg_oi:,}")
            lines.append(f"- Stale-open candidates (open==prev_settle same contract, ctr<10): {stale}")
            lines.append("")

        # Overall verdict
        overall_active = df_atm.groupby("trade_date")["contracts"].sum().gt(0)
        overall_pct = round(100 * overall_active.sum() / overall_active.count(), 1)
        overall_oi = int(df_atm["open_int"].mean())

        if overall_pct >= 80 and overall_oi > 1000:
            verdict = "PASS"
            reason = (f"ATM strikes have {overall_pct}% of days with contracts>0 "
                      f"and average OI of {overall_oi:,} (>1000).")
        else:
            verdict = "FAIL"
            reason = (f"ATM strikes have {overall_pct}% active days "
                      f"(need >=80%) and/or average OI {overall_oi:,} (need >1000).")
        lines.append(f"### Overall Verdict: {verdict}")
        lines.append(f"Reason: {reason}")
    else:
        lines.append("No ATM-adjacent strike data available (need Nifty 1d close files).")
        lines.append("")
        lines.append("Verdict: FAIL")
        lines.append("Reason: Cannot evaluate liquidity without Nifty close data.")

    return "\n".join(lines)


# --- Main ---------------------------------------------------------------------

def main():
    os.makedirs(DB_PATH.parent, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))
    con.execute(SCHEMA_SQL)

    # F2 fix: remove NIFTYNXT50 rows that were mistakenly ingested
    n_removed = con.execute(
        "DELETE FROM option_bhavcopy WHERE symbol <> 'NIFTY'"
    ).fetchone()[0]
    if n_removed > 0:
        print(f"Purged {n_removed:,} non-NIFTY rows (NIFTYNXT50 contamination)")

    end = date.today() - timedelta(days=1)
    start = date(2023, 1, 1)

    total_inserted = 0
    total_skipped = 0
    total_404 = 0
    consec_both_404 = 0

    for d in date_range(start, end):
        existing = con.execute(
            "SELECT COUNT(*) FROM option_bhavcopy WHERE trade_date = ?",
            [d],
        ).fetchone()[0]
        if existing > 0:
            print(f"{d.isoformat()}  SKIP  ({existing} rows already present)")
            total_skipped += 1
            consec_both_404 = 0
            continue

        # Fast-skip: if BOTH formats exhausted for 30 consecutive days
        # in the legacy era (pre-cutover), the legacy archive has genuinely ended.
        # In the UDiFF era, individual timeouts due to server throttling
        # are expected — never fast-skip the forward-backfill.
        if consec_both_404 >= 30 and d <= LEGACY_CUTOVER:
            print(f"{d.isoformat()}  SKIP  (legacy exhausted, 30+ consecutive misses)")
            total_skipped += 1
            continue

        try:
            count = _ingest_single_day(con, d)
            if count > 0:
                print(f"{d.isoformat()}  OK    {count} Nifty option rows")
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

    print()
    print("=" * 60)
    print("LIQUIDITY AUDIT")
    print("=" * 60)

    con = duckdb.connect(str(DB_PATH))
    report = run_audit(con)
    con.close()

    print()
    print(report)

    con = duckdb.connect(str(DB_PATH))
    total_all = con.execute("SELECT COUNT(*) FROM option_bhavcopy").fetchone()[0]
    dr_all = con.execute(
        "SELECT MIN(trade_date), MAX(trade_date) FROM option_bhavcopy"
    ).fetchone()
    con.close()

    os.makedirs(REPORT_PATH.parent, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write("# MSRP Phase 7 \u2014 Bhavcopy Ingestion Audit\n\n")
        f.write(f"*Generated: {datetime.now().isoformat()}*\n\n")
        f.write("## Ingestion Summary\n\n")
        f.write(f"- Date range: {start} to {end}\n")
        f.write(f"- Data coverage: {dr_all[0]} to {dr_all[1]}\n")
        f.write(f"- Rows in database: {total_all:,}\n")
        f.write(f"- Rows inserted this run: {total_inserted:,}\n")
        f.write(f"- Dates skipped (already present): {total_skipped}\n")
        f.write(f"- Dates with 404 (holiday/unavailable): {total_404}\n")
        f.write(f"- Non-NIFTY rows purged (NIFTYNXT50): {n_removed:,}\n\n")
        f.write(report)
        f.write("\n")

    print(f"\nAudit report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
