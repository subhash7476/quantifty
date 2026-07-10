"""CSMP Gate (b) — NSE CF-CA CSV split ingestion (replaces bhavcopy-gap inference).

Parses NSE's structured corporate-actions CSV files (CF-CA-equities-*.csv)
for stock split / sub-division / face-value change records, derives adjustment
factors from the exchange-published old/new face values, and ingests them as
primary-source SPLIT events. No price-gap inference — every factor is derived
from the exchange's own Purpose text (e.g. 'Fv Splt Frm Rs 10 To Re 1').

Also handles ETF unit-splits from a hardcoded patch list (not in NSE feed).

Usage:
    python scripts/csmp/ingest_corporate_actions.py
"""

import csv
import io
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
RAW_DIR = ROOT / "data" / "market_data" / "corporate_actions_raw"

SESSION = None
SPECIAL_DIV_THRESHOLD = 0.20

ETF_SPLITS = [
    ("GOLDBEES", date(2019, 12, 19), 100, 1,
     "AMC notice; NSE equity CA feed has no ETF unit-split records"),
    ("AXISGOLD", date(2020, 7, 23), 100, 1, "AMC notice"),
    ("HDFCMFGETF", date(2021, 2, 17), 100, 1, "AMC notice"),
    ("GOLDSHARE", date(2021, 3, 25), 100, 1, "AMC notice"),
    ("BSLGOLDETF", date(2021, 11, 25), 100, 1, "AMC notice"),
    ("QGOLDHALF", date(2021, 12, 16), 100, 1, "AMC notice"),
    ("SETFGOLD", date(2022, 1, 6), 100, 1, "AMC notice"),
    ("LICMFGOLD", date(2026, 3, 6), 100, 1, "AMC notice"),
    ("IVZINGOLD", date(2026, 4, 30), 100, 1, "AMC notice"),
]


def get_session():
    global SESSION
    if SESSION is None:
        s = requests.Session()
        retry = Retry(total=4, backoff_factor=2.0,
                      status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=4,
                              pool_maxsize=4)
        s.mount("https://", adapter)
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36",
        })
        SESSION = s
    return SESSION


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS corporate_actions (
    symbol       VARCHAR,
    ex_date      DATE,
    action_type  VARCHAR,
    purpose_raw  VARCHAR,
    ratio_or_fv  VARCHAR,
    source       VARCHAR,
    scripcode    VARCHAR,
    raw_json     VARCHAR
);
CREATE TABLE IF NOT EXISTS adjustment_factors (
    symbol       VARCHAR,
    ex_date      DATE,
    factor       DOUBLE,
    action_type  VARCHAR,
    source       VARCHAR,
    PRIMARY KEY (symbol, ex_date, action_type)
);
"""


def _parse_bse_date(val):
    if val is None:
        return None
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except (ValueError, OverflowError):
            pass
    return None


def _to_str(*args):
    for v in args:
        if v is not None and v != "":
            return str(v)
    return ""


def parse_nse_cf_ca_splits():
    """Extract split/sub-division/consolidation records from NSE CF-CA CSVs."""
    splits = []
    for fp in sorted(RAW_DIR.glob("CF-CA-equities-*.csv")):
        txt = fp.read_bytes().decode("utf-8-sig")
        for row in csv.DictReader(io.StringIO(txt)):
            purpose = (row.get("PURPOSE") or "").strip().lower()
            p_upper = purpose.upper()
            if not any(w in p_upper for w in ["SPLIT", "SPLT", "SUB-DIVISION",
                       "DIVISION OF", "CONSOLIDATION", "FV ", "FACE VALUE"]):
                continue
            sym = (row.get("SYMBOL") or "").strip().upper()
            ex_str = (row.get("EX-DATE") or "").strip()
            fv_str = (row.get("FACE VALUE") or "").strip()
            try:
                ex_date = datetime.strptime(ex_str, "%d-%b-%Y").date()
            except ValueError:
                continue
            nums = [int(s) for s in re.findall(r"\d+", purpose)]
            old_fv, new_fv = None, None
            if len(nums) >= 2:
                for i in range(len(nums) - 1):
                    if nums[i] >= 10 and nums[i + 1] <= nums[i]:
                        old_fv, new_fv = nums[i], nums[i + 1]
                        break
                if old_fv is None and nums[-2] >= 10:
                    old_fv, new_fv = nums[-2], nums[-1]
                if old_fv is None:
                    old_fv = max(nums)
                    remaining = [n for n in nums if n != old_fv]
                    new_fv = min(remaining) if remaining else old_fv
            if old_fv is None or old_fv == 0 or new_fv is None:
                continue
            source = f"NSE_CF-CA_{fp.name}"
            ratio_str = f"{old_fv}/{new_fv}"
            factor = new_fv / old_fv
            splits.append({
                "symbol": sym,
                "ex_date": ex_date,
                "action_type": "SPLIT",
                "purpose_raw": (row.get("PURPOSE") or "").strip(),
                "ratio_or_fv": ratio_str,
                "source": source,
                "scripcode": "",
                "raw_json": json.dumps(row, default=str)[:4000],
                "factor": factor,
            })
    return splits


def parse_bse_to_events(scripcode, symbol, raw):
    if raw is None:
        return []
    rows = []
    for b in (raw.get("Table1") or []):
        dt = _parse_bse_date(
            b.get("BCRD_FROM") or b.get("BCRD_from") or b.get("Ex_date"))
        if dt is None:
            continue
        rows.append({
            "symbol": symbol, "ex_date": dt, "action_type": "BONUS",
            "purpose_raw": _to_str(b.get("XTYPE")),
            "ratio_or_fv": _to_str(b.get("VALUE")),
            "source": f"BSE_{scripcode}",
            "scripcode": scripcode,
            "raw_json": json.dumps(b, default=str)[:4000],
        })
    for d in (raw.get("Table2") or []):
        dt = _parse_bse_date(d.get("Ex_date") or d.get("BCRD"))
        if dt is None:
            continue
        rows.append({
            "symbol": symbol, "ex_date": dt, "action_type": "DIVIDEND",
            "purpose_raw": _to_str(d.get("purpose") or d.get("purpose_name")),
            "ratio_or_fv": _to_str(d.get("Details") or d.get("Amount")),
            "source": f"BSE_{scripcode}",
            "scripcode": scripcode,
            "raw_json": json.dumps(d, default=str)[:4000],
        })
    seen = {(r["symbol"], r["ex_date"], r["purpose_raw"]) for r in rows}
    for d in (raw.get("Table") or []):
        dt = _parse_bse_date(d.get("BCRD_from") or d.get("BCRD_FROM")
                             or d.get("Ex_date"))
        if dt is None:
            continue
        purpose = _to_str(d.get("purpose_name") or d.get("purpose"))
        key = (symbol, dt, purpose)
        if key in seen:
            continue
        rows.append({
            "symbol": symbol, "ex_date": dt, "action_type": "DIVIDEND",
            "purpose_raw": purpose,
            "ratio_or_fv": _to_str(d.get("Amount")),
            "source": f"BSE_{scripcode}",
            "scripcode": scripcode,
            "raw_json": json.dumps(d, default=str)[:4000],
        })
    return rows


def derive_bonus_factor(ratio_str):
    s = ratio_str.lower().strip()
    if "issue" in s or ":" in s:
        if "issue" in s:
            parts_str = s.split("issue", 1)[-1]
        else:
            parts_str = s
        parts = [p.strip() for p in parts_str.split(":") if p.strip()]
        if len(parts) == 2:
            try:
                bonus, existing = int(parts[0]), int(parts[1])
                if existing > 0:
                    return existing / (existing + bonus)
            except ValueError:
                pass
    return None


def derive_split_factor(old_fv, new_fv):
    return new_fv / old_fv


def purge_and_rebuild(con):
    os.makedirs(RAW_DIR, exist_ok=True)
    con.execute(SCHEMA_SQL)

    n_del_ca = con.execute(
        "DELETE FROM corporate_actions WHERE action_type='SPLIT'").fetchone()[0]
    n_del_af = con.execute(
        "DELETE FROM adjustment_factors WHERE action_type='SPLIT'").fetchone()[0]
    print(f"Purged: {n_del_ca} SPLIT rows, {n_del_af} factors")

    con.execute("DELETE FROM corporate_actions WHERE action_type IN "
                "('BONUS', 'DIVIDEND')")
    con.execute("DELETE FROM adjustment_factors "
                "WHERE action_type IN ('BONUS', 'DIVIDEND')")

    # Re-parse BSE cache for bonuses + dividends
    cached = sorted(RAW_DIR.glob("bse_ca_*.json"))
    store_syms = {r[0] for r in con.execute(
        "SELECT DISTINCT symbol FROM equity_bhavcopy "
        "WHERE series='EQ'").fetchall()}

    events, factors = [], []
    for p in cached:
        code = p.stem.replace("bse_ca_", "")
        data = json.loads(p.read_bytes())
        has_data = any(isinstance(v, list) and len(v) > 0
                      for v in data.values())
        if not has_data:
            continue
        sym = None
        for tbl in ["Table1", "Table2", "Table"]:
            entries = data.get(tbl, [])
            if entries:
                s = entries[0].get("short_name") or entries[0].get("scrip_id")
                if s:
                    sym = s.upper()
                    break
        if sym is None or sym not in store_syms:
            continue
        for ev in parse_bse_to_events(code, sym, data):
            events.append(ev)
            if ev["action_type"] == "BONUS":
                f = derive_bonus_factor(ev["ratio_or_fv"])
                if f is not None:
                    factors.append({
                        "symbol": ev["symbol"], "ex_date": ev["ex_date"],
                        "factor": f, "action_type": "BONUS",
                        "source": ev["source"],
                    })

    if events:
        df_ev = pd.DataFrame(events).drop_duplicates(
            subset=["symbol", "ex_date", "action_type", "ratio_or_fv"])
        con.execute("INSERT INTO corporate_actions SELECT symbol, ex_date, "
                    "action_type, purpose_raw, ratio_or_fv, source, "
                    "scripcode, raw_json FROM df_ev")
        print(f"BSE events: {len(df_ev)}")

    if factors:
        df_fac = pd.DataFrame(factors).drop_duplicates(
            subset=["symbol", "ex_date", "action_type"])
        con.execute("INSERT INTO adjustment_factors SELECT symbol, ex_date, "
                    "factor, action_type, source FROM df_fac")
        print(f"Bonus factors: {len(df_fac)}")

    # --- PRIMARY: NSE CF-CA CSV splits ---
    nse_splits = parse_nse_cf_ca_splits()
    split_events = [{k: v for k, v in s.items() if k != "factor"}
                    for s in nse_splits]
    split_factors = [{"symbol": s["symbol"], "ex_date": s["ex_date"],
                      "factor": s["factor"], "action_type": "SPLIT",
                      "source": s["source"]} for s in nse_splits]
    if split_events:
        df_se = pd.DataFrame(split_events).drop_duplicates(
            subset=["symbol", "ex_date", "action_type"])
        con.execute("INSERT INTO corporate_actions SELECT symbol, ex_date, "
                    "action_type, purpose_raw, ratio_or_fv, source, "
                    "scripcode, raw_json FROM df_se")
        print(f"NSE CF-CA splits: {len(df_se)} events")
    if split_factors:
        df_sf = pd.DataFrame(split_factors).drop_duplicates(
            subset=["symbol", "ex_date", "action_type"])
        con.execute("INSERT INTO adjustment_factors SELECT symbol, ex_date, "
                    "factor, action_type, source FROM df_sf")
        print(f"NSE CF-CA split factors: {len(df_sf)}")

    return len(events), len(factors), len(nse_splits)


def ingest_etf_splits(con):
    rows = []
    for sym, dt, old_fv, new_fv, src in ETF_SPLITS:
        rows.append({
            "symbol": sym, "ex_date": dt,
            "action_type": "SPLIT",
            "purpose_raw": f"Gold ETF unit sub-division: FV {old_fv} -> "
                          f"{new_fv} ({src[:80]})",
            "ratio_or_fv": f"{old_fv}/{new_fv}",
            "source": f"ETF_AMC_notice_{dt.isoformat()}_{sym}",
            "scripcode": "",
            "raw_json": "{}",
        })
    df_ev = pd.DataFrame(rows)
    con.execute("INSERT INTO corporate_actions SELECT symbol, "
                "ex_date, action_type, purpose_raw, ratio_or_fv, source, "
                "scripcode, raw_json FROM df_ev")
    df_f = pd.DataFrame([{
        "symbol": s, "ex_date": d,
        "factor": derive_split_factor(o, n),
        "action_type": "SPLIT",
        "source": f"ETF_AMC_notice_{d.isoformat()}_{s}",
    } for s, d, o, n, _ in ETF_SPLITS])
    con.execute("INSERT INTO adjustment_factors SELECT symbol, ex_date, "
                "factor, action_type, source FROM df_f")
    print(f"ETF splits: {len(ETF_SPLITS)} events + factors")
    return len(ETF_SPLITS)


def ingest_special_dividends(con):
    divs = con.execute("""
        SELECT ca.symbol, ca.ex_date, ca.ratio_or_fv
        FROM corporate_actions ca WHERE ca.action_type = 'DIVIDEND'
        AND ca.ratio_or_fv != '' AND ca.ratio_or_fv != '0'
    """).fetchall()
    new_factors = []
    for sym, dt, amt_str in divs:
        try:
            amt = float(amt_str)
        except ValueError:
            continue
        if amt <= 0:
            continue
        prior = con.execute("""
            SELECT e.close FROM equity_bhavcopy e
            JOIN trading_calendar tc ON e.trade_date = tc.trade_date
                AND tc.n_symbols >= 200
            WHERE e.symbol = ? AND e.series = 'EQ'
            AND e.trade_date < ? ORDER BY e.trade_date DESC LIMIT 1
        """, [sym, dt]).fetchone()
        P = prior[0] if prior else None
        if P is None or P <= 0:
            continue
        if amt >= SPECIAL_DIV_THRESHOLD * P:
            if amt >= P:
                continue
            new_factors.append({
                "symbol": sym, "ex_date": dt,
                "factor": (P - amt) / P,
                "action_type": "SPECIAL_DIVIDEND",
                "source": f"bhavcopy_prior_close_{P:.2f}_div_{amt:.2f}",
            })
    if new_factors:
        df = pd.DataFrame(new_factors).drop_duplicates(
            subset=["symbol", "ex_date", "action_type"])
        con.execute("INSERT OR REPLACE INTO adjustment_factors SELECT symbol, "
                    "ex_date, factor, action_type, source FROM df")
        print(f"Special dividends (>= {SPECIAL_DIV_THRESHOLD:.0%}): "
              f"{len(df)} factors")
    return len(new_factors)


def main():
    con = duckdb.connect(str(DB_PATH))

    ne, nf, nse = purge_and_rebuild(con)
    netf = ingest_etf_splits(con)
    nsp = ingest_special_dividends(con)

    # Rebuild adjusted view
    con.execute("""
CREATE OR REPLACE VIEW equity_bhavcopy_adjusted AS
WITH price_factors AS (
    SELECT af.symbol, af.ex_date, af.factor,
           EXP(SUM(LN(af.factor)) OVER (
               PARTITION BY af.symbol ORDER BY af.ex_date DESC
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           )) AS cum_price_factor
    FROM adjustment_factors af
    WHERE af.action_type IN ('BONUS', 'SPLIT', 'SPECIAL_DIVIDEND')
),
vol_factors AS (
    SELECT af.symbol, af.ex_date, af.factor,
           EXP(SUM(LN(af.factor)) OVER (
               PARTITION BY af.symbol ORDER BY af.ex_date DESC
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           )) AS cum_vol_factor
    FROM adjustment_factors af
    WHERE af.action_type IN ('BONUS', 'SPLIT')
)
SELECT
    e.trade_date, e.symbol, e.series,
    e.open   * COALESCE(pf.cum_price_factor, 1.0) AS open,
    e.high   * COALESCE(pf.cum_price_factor, 1.0) AS high,
    e.low    * COALESCE(pf.cum_price_factor, 1.0) AS low,
    e.close  * COALESCE(pf.cum_price_factor, 1.0) AS close,
    e.prev_close * COALESCE(pf.cum_price_factor, 1.0) AS prev_close,
    e.volume / COALESCE(NULLIF(vf.cum_vol_factor, 0), 1.0) AS volume,
    e.turnover,
    e.deliv_qty,
    e.deliv_pct
FROM equity_bhavcopy e
LEFT JOIN price_factors pf ON e.symbol = pf.symbol
    AND pf.ex_date > e.trade_date
    AND pf.ex_date = (
        SELECT MIN(pf2.ex_date) FROM adjustment_factors pf2
        WHERE pf2.symbol = e.symbol AND pf2.ex_date > e.trade_date
          AND pf2.action_type IN ('BONUS', 'SPLIT', 'SPECIAL_DIVIDEND')
    )
LEFT JOIN vol_factors vf ON e.symbol = vf.symbol
    AND vf.ex_date > e.trade_date
    AND vf.ex_date = (
        SELECT MIN(vf2.ex_date) FROM adjustment_factors vf2
        WHERE vf2.symbol = e.symbol AND vf2.ex_date > e.trade_date
          AND vf2.action_type IN ('BONUS', 'SPLIT')
    )
""")

    con.close()

    print()
    print("=" * 56)
    print("REBUILD SUMMARY")
    print("=" * 56)
    print(f"BSE Bonus/Div events: {ne:,}")
    print(f"Bonus factors: {nf:,}")
    print(f"NSE CF-CA split events: {nse:,}")
    print(f"ETF split events: {netf:,}")
    print(f"Special dividend factors: {nsp:,}")


if __name__ == "__main__":
    main()
