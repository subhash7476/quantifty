"""ISD G7a-d — vendor archive ingest (archive.zip → staging tree).

Stages the 100-ticker per-symbol CSVs into an ISOLATED tree
`data/market_data/nse/candles/1m_vendor/{TICKER}.duckdb` (never mixed with the
native store) plus a manifest jsonl recording, per member: zip CRC32, raw/kept
rows, tail-policy drops, date span, and session fingerprint (modal first/last
minute). Ticker→NSE-symbol resolution via the equity store's instrument_master ∪
symbol_isin; unresolved tickers are listed, never guessed (G7a).

Junk-tail policy (G7d): bars OUTSIDE 09:15..15:29 or on non-trading-grid times
with volume == 0 are DROPPED and counted. In-grid zero-volume bars are kept —
they are real flat minutes.
"""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from scripts.isd import (
    EQUITY_DB, SESSION_FIRST_MIN, SESSION_LAST_MIN, VENDOR_DIR, connect_ro,
)

MANIFEST_PATH = VENDOR_DIR / "manifest.jsonl"


def ticker_symbol_map() -> dict:
    """NSE symbol -> isin from instrument_master ∪ symbol_isin."""
    con = connect_ro(EQUITY_DB)
    try:
        rows = con.execute(
            "select symbol, isin from instrument_master where isin is not null "
            "union select symbol, isin from symbol_isin where isin is not null"
        ).fetchall()
    finally:
        con.close()
    return {s: i for s, i in rows}


def _parse_ts(raw: str):
    return dt.datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M:%S")


def stage_member(zf: zipfile.ZipFile, member: str, sym_map: dict) -> dict:
    """Stage one zip member into its own duckdb; returns manifest record.

    Parsing is pushed into DuckDB (read_csv over an extracted temp file) — a
    Python row loop over ~97M total rows would dominate runtime.
    """
    import tempfile

    import duckdb

    ticker = member.split("/")[-1][:-4]
    crc = zf.getinfo(member).CRC
    nse_symbol = ticker if ticker in sym_map else None
    isin = sym_map.get(ticker)

    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    out_path = VENDOR_DIR / f"{ticker}.duckdb"
    if out_path.exists():
        out_path.unlink()

    with tempfile.TemporaryDirectory() as td:
        src = Path(zf.extract(member, td))
        con_out = duckdb.connect(str(out_path))
        try:
            con_out.execute(f"""
                create table raw as
                select cast(date as TIMESTAMP) ts,
                       open::DOUBLE open, high::DOUBLE high,
                       low::DOUBLE low, close::DOUBLE as "close",
                       volume::BIGINT volume
                from read_csv('{src.as_posix()}',
                              header = true,
                              columns = {{'date': 'VARCHAR',
                                          'open': 'VARCHAR',
                                          'high': 'VARCHAR',
                                          'low': 'VARCHAR',
                                          'close': 'VARCHAR',
                                          'volume': 'VARCHAR'}})
            """)
            stats = con_out.execute("""
                select count(*) as rows_raw,
                       count(*) filter (
                         where (hour(ts)*60 + minute(ts) < ?
                                or hour(ts)*60 + minute(ts) > ?)
                           and coalesce(volume, 0) = 0) as tail_dropped,
                       min(cast(ts as DATE)), max(cast(ts as DATE))
                from raw
            """, [SESSION_FIRST_MIN, SESSION_LAST_MIN]).fetchone()
            con_out.execute(
                "create table vendor_1m (ts TIMESTAMP, open DOUBLE, "
                "high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")
            con_out.execute("""
                insert into vendor_1m
                select ts, open, high, low, "close", volume from raw
                where not ((hour(ts)*60 + minute(ts) < ? or
                            hour(ts)*60 + minute(ts) > ?)
                           and coalesce(volume, 0) = 0)
            """, [SESSION_FIRST_MIN, SESSION_LAST_MIN])
            con_out.execute("drop table raw")
        finally:
            con_out.close()

    rows_raw, tail_dropped, first_date, last_date = stats
    kept = int(rows_raw - tail_dropped)

    con = connect_ro(out_path)
    try:
        fp_first = con.execute("""
            select m, count(*) c from (
                select extract(hour from ts)*60 + extract(minute from ts) m,
                       rank() over (partition by cast(ts as DATE)
                                    order by ts) rk
                from vendor_1m)
            where rk = 1 group by m order by c desc limit 1""").fetchone()
        fp_last = con.execute("""
            select m, count(*) c from (
                select extract(hour from ts)*60 + extract(minute from ts) m,
                       rank() over (partition by cast(ts as DATE)
                                    order by ts desc) rk
                from vendor_1m)
            where rk = 1 group by m order by c desc limit 1""").fetchone()
    finally:
        con.close()

    return {
        "member": member, "ticker": ticker, "crc32": crc,
        "nse_symbol": nse_symbol, "isin": isin, "resolved": isin is not None,
        "rows_raw": int(rows_raw), "rows_kept": kept,
        "tail_dropped": int(tail_dropped),
        "first_date": str(first_date), "last_date": str(last_date),
        "modal_first_minute": int(fp_first[0]) if fp_first else None,
        "modal_last_minute": int(fp_last[0]) if fp_last else None,
    }


def run(zip_path=None) -> dict:
    zp = zip_path or None
    import scripts.isd as isd
    zp = zp or isd.VENDOR_ZIP
    sym_map = ticker_symbol_map()
    records = []
    with zipfile.ZipFile(str(zp)) as zf:
        members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        for member in sorted(members):
            records.append(stage_member(zf, member, sym_map))
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")

    unresolved = [r["ticker"] for r in records if not r["resolved"]]
    bad_fp = [r["ticker"] for r in records
              if r["resolved"] and (r["modal_first_minute"] != SESSION_FIRST_MIN
                                    or r["modal_last_minute"]
                                    != SESSION_LAST_MIN)]
    return {
        "gate": "G7a-d",
        "members": len(records),
        "unresolved_tickers": unresolved,
        "resolution_rate": round(1 - len(unresolved) / max(len(records), 1), 4),
        "bad_fingerprint_tickers": bad_fp,
        "tail_dropped_total": sum(r["tail_dropped"] for r in records),
        "manifest": str(MANIFEST_PATH),
        # G7a PASS bar: >=95% automated resolution; fingerprint census published.
        "pass": len(unresolved) / max(len(records), 1) <= 0.05
                and not bad_fp,
    }
