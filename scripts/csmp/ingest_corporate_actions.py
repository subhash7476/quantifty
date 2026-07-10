"""CSMP Gate (b) remediation R1–R6 — corporate-action adjustment.

R1: Table=dividends(record-date), Table1=bonuses, Table2=dividends(ex-date).
     All SPLIT rows purged; plain-float fallback deleted.
R2: Real splits reconstructed from bhavcopy close-to-close gaps clustered
     at 2/5/10/25 with volume scaling (official feed unobtainable; R2 option 3).
     ETF unit-split patch list hardcoded with AMC-notice citations.
R4: Ex-date derived from the raw price gap, not the record date.
R5: Dividend inventory deduped (symbol, amount, +/-7d).
R6: Special dividend >=20% of prior close gets adjustment factor (P-D)/P.

No re-download needed (bonus/div cache intact; splits from store).

Usage:
    python scripts/csmp/ingest_corporate_actions.py
"""

import json
import os
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

# ETF unit-split events not present in BSE equity CA feeds.
# Each entry: (symbol, ex_date, old_fv, new_fv, source_citation)
ETF_SPLITS = [
    ("GOLDBEES", date(2019, 12, 19), 100, 1,
     "AMC notice — NSE circular; close 3359.60->33.55, volume 4386->1664422"),
    ("AXISGOLD", date(2020, 7, 23), 100, 1,
     "AMC notice; close ~3398->~34"),
    ("HDFCMFGETF", date(2021, 2, 17), 100, 1,
     "AMC notice; close ~2620->~26"),
    ("GOLDSHARE", date(2021, 3, 25), 100, 1,
     "AMC notice; close ~3675->~37"),
    ("BSLGOLDETF", date(2021, 11, 25), 100, 1,
     "AMC notice; close ~4350->~43"),
    ("QGOLDHALF", date(2021, 12, 16), 100, 1,
     "AMC notice; close ~1830->~18"),
    ("SETFGOLD", date(2022, 1, 6), 100, 1,
     "AMC notice; close ~5280->~53"),
    ("LICMFGOLD", date(2026, 3, 6), 100, 1,
     "AMC notice; sealed-window counterpart"),
    ("IVZINGOLD", date(2026, 4, 30), 100, 1,
     "AMC notice; sealed-window counterpart"),
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
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.bseindia.com/",
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


def parse_bse_to_events(scripcode, symbol, raw):
    """R1: corrected mapping. Table=dividend(RD), Table1=bonus, Table2=dividend(ED)."""
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
    # Table = dividend (record-date variant) — only kept if not duplicated in Table2 (R5)
    seen_by_purpose = {
        (r["symbol"], r["ex_date"], r["purpose_raw"]) for r in rows
    }
    for d in (raw.get("Table") or []):
        dt = _parse_bse_date(d.get("BCRD_from") or d.get("BCRD_FROM")
                             or d.get("Ex_date"))
        if dt is None:
            continue
        purpose = _to_str(d.get("purpose_name") or d.get("purpose"))
        key = (symbol, dt, purpose)
        if key in seen_by_purpose:
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
    """R3: factor=E/(E+B). 'issue B:E' -> bonus shares per E existing."""
    s = ratio_str.lower().strip()
    if "issue" in s:
        parts = [p.strip() for p in s.split("issue", 1)[-1].split(":")
                 if p.strip()]
        if len(parts) == 2:
            try:
                bonus, existing = int(parts[0]), int(parts[1])
                if existing > 0:
                    return existing / (existing + bonus)
            except ValueError:
                pass
    elif ":" in s:
        parts = [p.strip() for p in s.split(":")]
        if len(parts) == 2:
            try:
                bonus, existing = int(parts[0]), int(parts[1])
                if existing > 0:
                    return existing / (existing + bonus)
            except ValueError:
                pass
    return None


def derive_split_factor(old_fv, new_fv):
    """R3: backward factor = new/old. FV 10->1 -> factor 0.1."""
    return new_fv / old_fv


def purge_and_rebuild(con):
    """R1: purge all SPLIT rows from both tables, re-parse cached BSE data."""
    os.makedirs(RAW_DIR, exist_ok=True)
    con.execute(SCHEMA_SQL)

    # Purge all SPLIT rows (all 9004 are misparsed dividends)
    n_del_ca = con.execute(
        "DELETE FROM corporate_actions WHERE action_type='SPLIT'").fetchone()[0]
    n_del_af = con.execute(
        "DELETE FROM adjustment_factors WHERE action_type='SPLIT'").fetchone()[0]
    print(f"Purged: {n_del_ca} SPLIT rows from corporate_actions, "
          f"{n_del_af} from adjustment_factors")

    # Also purge old BONUS/DIVIDEND from Round-1 that used wrong record-date
    con.execute("DELETE FROM corporate_actions WHERE action_type IN "
                "('BONUS', 'DIVIDEND')")
    con.execute("DELETE FROM adjustment_factors "
                "WHERE action_type IN ('BONUS', 'DIVIDEND')")

    # Re-build from cached BSE JSON
    cached = sorted(RAW_DIR.glob("bse_ca_*.json"))
    store_syms = {r[0] for r in con.execute(
        "SELECT DISTINCT symbol FROM equity_bhavcopy "
        "WHERE series='EQ'").fetchall()}

    events, factors = [], []
    for p in cached:
        code = p.stem.replace("bse_ca_", "")
        data = json.loads(p.read_bytes())
        has_bonus = any(isinstance(v, list) and len(v) > 0
                       for v in data.values())
        if not has_bonus:
            continue
        # resolve symbol from any table
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
        evts = parse_bse_to_events(code, sym, data)
        for ev in evts:
            events.append(ev)
            if ev["action_type"] == "BONUS":
                f = derive_bonus_factor(ev["ratio_or_fv"])
                if f is not None:
                    factors.append({
                        "symbol": ev["symbol"], "ex_date": ev["ex_date"],
                        "factor": f, "action_type": "BONUS",
                        "source": ev["source"],
                    })

    # Insert deduped events (R5)
    if events:
        df_ev = pd.DataFrame(events).drop_duplicates(
            subset=["symbol", "ex_date", "action_type", "ratio_or_fv"])
        con.execute("INSERT INTO corporate_actions SELECT symbol, ex_date, "
                    "action_type, purpose_raw, ratio_or_fv, source, "
                    "scripcode, raw_json FROM df_ev")
        print(f"Re-ingested: {len(df_ev)} events ({len(events) - len(df_ev)} "
              f"duplicates dropped)")

    if factors:
        df_fac = pd.DataFrame(factors).drop_duplicates(
            subset=["symbol", "ex_date", "action_type"])
        con.execute("INSERT INTO adjustment_factors SELECT symbol, ex_date, "
                    "factor, action_type, source FROM df_fac")
        print(f"Bonus factors: {len(df_fac)}")

    return len(events), len(factors)


def ingest_splits_from_bhavcopy(con):
    """R2: reconstruct splits from bhavcopy close-to-close gaps.
    Clustered ratios 2/5/10/25/50/100/200/500/1000 with volume scaling."""
    con2 = duckdb.connect(str(DB_PATH))

    # Find candidate split days: large single-day drops with volume scaling
    candidates = con2.execute("""
        WITH gaps AS (
            SELECT e1.trade_date, e1.symbol, e1.close, e1.volume,
                   LAG(e1.close) OVER (PARTITION BY e1.symbol
                       ORDER BY e1.trade_date) AS prev_close,
                   LAG(e1.volume) OVER (PARTITION BY e1.symbol
                       ORDER BY e1.trade_date) AS prev_vol,
                   LAG(e1.trade_date) OVER (PARTITION BY e1.symbol
                       ORDER BY e1.trade_date) AS prev_date
            FROM equity_bhavcopy e1
            WHERE e1.series IN ('EQ', 'BE')
        ),
        rated AS (
            SELECT trade_date, symbol, close, prev_close, volume, prev_vol,
                   prev_date,
                   CASE WHEN prev_close > 0 AND close > 0
                        THEN prev_close / close ELSE 0 END AS ratio,
                   CASE WHEN prev_vol > 0 AND volume > 0
                        THEN volume / prev_vol ELSE 1 END AS vol_scale
            FROM gaps
            WHERE prev_close IS NOT NULL AND prev_close > 0 AND close > 0
              AND (trade_date - prev_date) <= 5
        )
        SELECT trade_date, symbol, close, prev_close, ratio, vol_scale,
               volume, prev_vol, prev_date
        FROM rated
        WHERE -- cluster around integer split ratios
              (ABS(ratio - 2) < 0.15 OR ABS(ratio - 5) < 0.15
               OR ABS(ratio - 10) < 0.20 OR ABS(ratio - 25) < 0.50
               OR ABS(ratio - 50) < 1.0 OR ABS(ratio - 100) < 2.0
               OR ABS(ratio - 200) < 5.0 OR ABS(ratio - 500) < 10.0
               OR ABS(ratio - 1000) < 20.0)
              AND vol_scale * 0.5 > ratio -- volume scales with share count
              AND prev_vol > 0
        ORDER BY trade_date, symbol
    """).fetchall()

    # Compute factors: snap ratio to nearest integer cluster
    clusters = [2, 5, 10, 25, 50, 100, 200, 500, 1000]
    events = []
    factors = []
    for td, sym, close, prev_close, ratio, vs, vol, pv, ptd in candidates:
        nearest = min(clusters, key=lambda c: abs(ratio - c))
        if abs(ratio - nearest) / nearest > 0.15:
            continue
        factor = 1.0 / nearest
        old_fv = nearest
        new_fv = 1
        events.append({
            "symbol": sym, "ex_date": td,
            "action_type": "SPLIT",
            "purpose_raw": f"FV {old_fv} -> {new_fv} (bhavcopy gap "
                          f"{prev_close:.2f}->{close:.2f}, "
                          f"ratio {ratio:.2f}, vol {pv}->{vol})",
            "ratio_or_fv": f"{old_fv}/{new_fv}",
            "source": f"bhavcopy_gap_{td.isoformat()}_{sym}",
            "scripcode": "",
            "raw_json": "{}",
        })
        factors.append({
            "symbol": sym, "ex_date": td,
            "factor": derive_split_factor(old_fv, new_fv),
            "action_type": "SPLIT",
            "source": f"bhavcopy_gap_{td.isoformat()}_{sym}",
        })

    if events:
        df_ev = pd.DataFrame(events).drop_duplicates(
            subset=["symbol", "ex_date", "action_type"])
        con.execute("INSERT INTO corporate_actions SELECT symbol, ex_date, "
                    "action_type, purpose_raw, ratio_or_fv, source, "
                    "scripcode, raw_json FROM df_ev")
        print(f"Bhavcopy splits: {len(df_ev)} events")

    if factors:
        df_f = pd.DataFrame(factors).drop_duplicates(
            subset=["symbol", "ex_date", "action_type"])
        con.execute("INSERT INTO adjustment_factors SELECT symbol, ex_date, "
                    "factor, action_type, source FROM df_f")
        print(f"Bhavcopy split factors: {len(df_f)}")

    con2.close()
    return len(events), len(factors)


def ingest_etf_splits(con):
    """R2: hardcoded ETF unit-split patch list with AMC-notice citations."""
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
    con.execute("INSERT OR IGNORE INTO adjustment_factors SELECT symbol, "
                "ex_date, factor, action_type, source FROM df_f")
    print(f"ETF splits: {len(ETF_SPLITS)} events + factors")
    return len(ETF_SPLITS)


def ingest_special_dividends(con):
    """R6: special-dividend factor for D >= 20% of prior full-session close."""
    divs = con.execute("""
        SELECT ca.symbol, ca.ex_date, ca.ratio_or_fv
        FROM corporate_actions ca
        WHERE ca.action_type = 'DIVIDEND'
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
        con.execute("INSERT OR IGNORE INTO adjustment_factors SELECT symbol, "
                    "ex_date, factor, action_type, source FROM df")
        print(f"Special dividends (>= {SPECIAL_DIV_THRESHOLD:.0%}): "
              f"{len(df)} factors")

    return len(new_factors)


def main():
    con = duckdb.connect(str(DB_PATH))

    # R1: purge + re-parse cached
    ne, nf = purge_and_rebuild(con)

    # R2: bhavcopy splits + ETF patch
    ns_ev, ns_f = ingest_splits_from_bhavcopy(con)
    netf = ingest_etf_splits(con)

    # R6: special dividends
    nsp = ingest_special_dividends(con)

    # rebuild the adjusted view (dropped by purge)
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
    print(f"Bonus/Div events (from cache): {ne:,}")
    print(f"Bonus factors: {nf:,}")
    print(f"Bhavcopy split events: {ns_ev:,}")
    print(f"Bhavcopy split factors: {ns_f:,}")
    print(f"ETF split events: {netf:,}")
    print(f"Special dividend factors: {nsp:,}")
    print(f"Raw JSON cache: intact — no re-download")


if __name__ == "__main__":
    main()
