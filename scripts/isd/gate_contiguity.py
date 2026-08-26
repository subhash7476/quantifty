"""ISD G1 — session contiguity over the native 1m store.

Two layers:
  L1 session presence: every equity-store trading-calendar date in the ISD era
     (2023-01-02 → latest) has a per-day file with NSE_EQ bars. The certified
     daily store's `trading_calendar` is the ground truth; special closures
     (e.g. 2024-11-20, Maharashtra Assembly Elections) are absent there by
     construction, so a matching absence in the 1m tree is EXPECTED, not a hole.
  L2 intraday completeness: for each present (symbol, minute-of-day) slot in
     09:15..15:29 the file carries exactly one bar; shortfalls are counted into
     an explicit ledger (parquet under data/isd/) rather than silently ignored.
"""
from __future__ import annotations

import json

import duckdb

from scripts.isd import (
    EQUITY_DB, ISD_DATA_DIR, SESSION_FIRST_MIN, SESSION_LAST_MIN, connect_ro,
)

ISD_ERA_START = "2023-01-02"


def currency_check(present_dates: list, calendar_dates: list, today_iso: str) -> dict:
    """G2 — the store must be current through the last completed session.

    present_dates: session dates actually present in the 1m tree (iso strings).
    calendar_dates: all trading-calendar dates >= ISD_ERA_START (iso strings).
    today_iso: current date (IST) — today's session is not yet completed.
    """
    completed = [d for d in calendar_dates if d < today_iso]
    last_expected = completed[-1] if completed else None
    last_present = max(present_dates) if present_dates else None
    return {
        "gate": "G2",
        "latest_session_file": last_present,
        "last_completed_trading_session": last_expected,
        "pass": bool(last_expected) and last_present == last_expected,
    }


def expected_sessions() -> list:
    con = connect_ro(EQUITY_DB)
    try:
        rows = con.execute(
            "select trade_date from trading_calendar "
            "where trade_date >= ? order by trade_date",
            [ISD_ERA_START]).fetchall()
    finally:
        con.close()
    return [r[0].isoformat() for r in rows]


def audit_session(path, session_iso: str) -> dict:
    """Per-file intraday completeness: missing (symbol, minute) slots."""
    con = connect_ro(path)
    try:
        n_sym = con.execute(
            "select count(distinct symbol) from candles "
            "where symbol like 'NSE_EQ%'").fetchone()[0]
        n_bars = con.execute(
            "select count(*) from candles where symbol like 'NSE_EQ%'"
        ).fetchone()[0]
        # bars outside the regular grid (should be zero for NSE cash)
        n_outside = con.execute(
            "select count(*) from candles where symbol like 'NSE_EQ%' "
            "and (hour(timestamp)*60 + minute(timestamp) < ? "
            "or hour(timestamp)*60 + minute(timestamp) > ?)",
            [SESSION_FIRST_MIN, SESSION_LAST_MIN]).fetchone()[0]
        # duplicate slots
        total, distinct_slots = con.execute(
            "select count(*), count(distinct (symbol, "
            "hour(timestamp)*60 + minute(timestamp))) from candles "
            "where symbol like 'NSE_EQ%'").fetchone()
    finally:
        con.close()
    expected = n_sym * (SESSION_LAST_MIN - SESSION_FIRST_MIN + 1)
    return {
        "session": session_iso,
        "symbols": int(n_sym),
        "eq_bars": int(n_bars),
        "expected_slots": int(expected),
        "missing_slots": int(expected - distinct_slots),
        "duplicate_slots": int(total - distinct_slots),
        "bars_outside_grid": int(n_outside),
    }


def run(sessions: list) -> dict:
    """sessions: [(iso, path)] as returned by scripts.isd.eq_sessions().

    Absence classes:
      `today_pending`   — current/next session; per-day 1m lands at EOD.
      `weekend_special` — NSE special/mock session on a non-weekday; bhavcopy
                          exists but equity 1m capture is not guaranteed. Out
                          of program scope BY RULE, published here.
      `eq_1m_missing`   — regular weekday session whose file carries no
                          NSE_EQ bars, or no file at all. DEFECT — blocks.
    """
    import datetime as dt

    from core.database.utils.market_hours import MarketHours
    have = {iso for iso, _ in sessions}
    today = MarketHours.get_ist_now().date().isoformat()
    want = [d for d in expected_sessions() if d < today]
    absent = []
    for d in want:
        if d in have:
            continue
        wd = dt.date.fromisoformat(d).weekday()
        absent.append({"date": d,
                       "class": "weekend_special" if wd >= 5
                       else "eq_1m_missing"})

    ledger_rows = []
    agg = {"symbols": 0, "missing_slots": 0, "duplicate_slots": 0,
           "bars_outside_grid": 0}
    for iso, path in sessions:
        r = audit_session(path, iso)
        for k in agg:
            agg[k] += r[k]
        if r["missing_slots"] or r["duplicate_slots"] or r["bars_outside_grid"]:
            ledger_rows.append(r)

    ISD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ledger_path = ISD_DATA_DIR / "g1_contiguity_ledger.jsonl"
    with open(ledger_path, "w", encoding="utf-8") as fh:
        for row in ledger_rows:
            fh.write(json.dumps(row) + "\n")

    defects = [a for a in absent if a["class"] == "eq_1m_missing"]
    return {
        "gate": "G1",
        "expected_sessions": len(want),
        "present_sessions": len(have),
        "absent_classes": absent,
        "aggregate": agg,
        "ledger_path": str(ledger_path),
        "ledger_entries": len(ledger_rows),
        # PASS: every regular weekday session before today carries equity 1m;
        # weekend specials are out of scope by rule and published here.
        "pass": not defects,
    }
