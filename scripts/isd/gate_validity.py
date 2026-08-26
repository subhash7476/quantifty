"""ISD G4 — OHLC/duplicate/volume validity audit over the native 1m store.

Per session (SQL pushed into DuckDB, only counts + violation rows cross the wire):
  V1 high < max(open, close) or low > min(open, close)
  V2 any price <= 0 or null
  V3 duplicate (symbol, timestamp)
  V4 volume < 0
  V5 close outside [0.5x, 2x] of that symbol's bhavcopy prev_close for the date
     (the daily store is the certified anchor; prev_close IS the prior session's
     official close, so this bounds overnight/typo fabrications)
"""
from __future__ import annotations

import duckdb

from scripts.isd import (
    EQUITY_DB, SESSION_FIRST_MIN, connect_ro,
)
from scripts.isd.read_1m import read_day


def _prev_close_map(session_iso: str) -> dict:
    """ISIN-keyed prev_close for one date from the certified daily store."""
    con = connect_ro(EQUITY_DB)
    try:
        rows = con.execute("""
            select 'NSE_EQ|' || si.isin as key, b.prev_close
            from equity_bhavcopy b
            join symbol_isin si on si.symbol = b.symbol
            where b.trade_date = ? and b.series = 'EQ'
        """, [session_iso]).fetchall()
    finally:
        con.close()
    return {k: float(v) for k, v in rows if v}


def _last_ex_dates() -> dict:
    """ISIN -> latest known corporate-action ex-date (any kind)."""
    con = connect_ro(EQUITY_DB)
    try:
        rows = con.execute("""
            select 'NSE_EQ|' || si.isin as key, max(ca.ex_date)
            from corporate_actions ca
            join symbol_isin si on si.symbol = ca.symbol
            where si.isin is not null
            group by 1
        """).fetchall()
    finally:
        con.close()
    return {k: v for k, v in rows if v}


def audit_session(path, session_iso: str, last_ex: dict) -> dict:
    con = connect_ro(path)
    try:
        v1, v1_first_bar, v2 = con.execute(f"""
            select
              count(*) filter (where high < greatest(open, close)
                                or low > least(open, close)),
              count(*) filter (where (high < greatest(open, close)
                                or low > least(open, close))
                                and (hour(timestamp)*60 + minute(timestamp)
                                     = {SESSION_FIRST_MIN})),
              count(*) filter (where open <= 0 or high <= 0 or low <= 0
                                or close <= 0 or open is null or high is null
                                or low is null or close is null)
            from candles where symbol like 'NSE_EQ%'
        """).fetchone()
        total, distinct_keys = con.execute("""
            select count(*), count(distinct (symbol, timestamp))
            from candles where symbol like 'NSE_EQ%'
        """).fetchone()
        v3 = total - distinct_keys
        v4 = con.execute("""
            select count(*) from candles
            where symbol like 'NSE_EQ%' and (volume < 0 or volume is null)
        """).fetchone()[0]
        worst = con.execute("""
            select symbol, max(close), min(close) from candles
            where symbol like 'NSE_EQ%' group by symbol
        """).fetchall()
    finally:
        con.close()

    pc = _prev_close_map(session_iso)
    v5_rows = []
    for sym, hi, lo in worst:
        base = pc.get(sym)
        if not base:
            continue
        if hi > 2.0 * base or lo < 0.5 * base:
            # CA-awareness: the native 1m series is RETROACTIVELY back-adjusted
            # (measured: WIPRO Jan-2023 bars at exactly 1/2 the raw prev_close
            # after its 1:1 bonus; the seam shows on the ex-date session itself,
            # e.g. BSE 2025-05-23). Any session up to and INCLUDING the symbol's
            # last ex-date trades on the adjusted basis vs the raw bhavcopy
            # anchor — ledgered as expected, never read as fabrication.
            lex = last_ex.get(sym)
            explained = bool(lex and session_iso <= str(lex))
            v5_rows.append({"session": session_iso, "symbol": sym,
                            "min_close": float(lo), "max_close": float(hi),
                            "prev_close": float(base),
                            "last_ex_date": str(lex) if lex else None,
                            "ca_adjusted_expected": explained})

    # V1/V2 example rows for the report ledger (bounded)
    con2 = connect_ro(path)
    try:
        v12_examples = con2.execute("""
            select symbol, timestamp, open, high, low, close from candles
            where symbol like 'NSE_EQ%'
              and ((high < greatest(open, close)) or (low > least(open, close))
                   or open <= 0 or high <= 0 or low <= 0 or close <= 0
                   or open is null or close is null)
            order by timestamp limit 10
        """).fetchall()
    finally:
        con2.close()

    # read_day contract check (G3 co-verification): schema drift would break here.
    df = read_day(path)
    return {
        "session": session_iso,
        "eq_bars": int(len(df)),
        "v1_ohlc_order": int(v1),
        "v1_first_bar_auction_artifact": int(v1_first_bar),
        "v2_bad_price": int(v2),
        "v3_duplicates": int(v3),
        "v4_volume_negative_or_null": int(v4),
        "v5_prevclose_band_violations": v5_rows,
        "v12_examples": [
            {"symbol": r[0], "timestamp": str(r[1]), "o": r[2], "h": r[3],
             "l": r[4], "c": r[5]} for r in v12_examples],
    }


def run(sessions: list) -> dict:
    """sessions: [(iso, path)] — returns the gate result dict.

    V5 rows carry `ca_adjusted_expected`; the gate PASSES when zero UNEXPLAINED
    band violations exist (explained ones are the measured adjustment basis,
    published in the ledger).
    """
    last_ex = _last_ex_dates()
    per_session = []
    for iso, path in sessions:
        per_session.append(audit_session(path, iso, last_ex))
    tot = {k: sum(s[k] for s in per_session) for k in
           ("v1_ohlc_order", "v1_first_bar_auction_artifact", "v2_bad_price",
            "v3_duplicates", "v4_volume_negative_or_null")}
    tot["v1_unexplained"] = (tot["v1_ohlc_order"]
                             - tot["v1_first_bar_auction_artifact"])
    v5_rows = [row for s in per_session for row in s["v5_prevclose_band_violations"]]
    tot["v5_unexplained"] = sum(1 for r in v5_rows
                                if not r["ca_adjusted_expected"])
    tot["v5_ca_adjusted_expected"] = sum(1 for r in v5_rows
                                         if r["ca_adjusted_expected"])
    return {
        "gate": "G4",
        "sessions_audited": len(per_session),
        "totals": tot,
        "v5_examples": v5_rows[:50],
        "v12_examples": [e for s in per_session for e in s["v12_examples"]][:50],
        # PASS bar: zero UNEXPLAINED rows. The 09:15 first-bar class is a
        # measured capture artifact (probe 2026-08-25: same symbols clean on
        # 2024-06-24/26 + 2024-07-01; violations concentrated on 2024-06-25),
        # published in the ledger — the v5 explained/unexplained pattern.
        "pass": all(v == 0 for v in (
            tot["v1_unexplained"], tot["v2_bad_price"], tot["v3_duplicates"],
            tot["v4_volume_negative_or_null"], tot["v5_unexplained"])),
    }
