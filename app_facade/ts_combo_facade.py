"""TS Basis Daily combo paper book — read-only bridge for the TS Basis page.

Reads the combo runner's store (bounded retry: the runner may be writing) and
its heartbeat, and marks the held futures live against the last formation's
close. The runner is an orchestrator child; this module never writes.
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

import duckdb

from core.analytics.options_selection import FUT_DB, INST_DB, future_key
from core.execution.portfolio.combo_paper_store import read_snapshot
from scripts.ops import pidfile

ROOT = Path(__file__).resolve().parents[1]
COMBO_DIR = ROOT / "data" / "paper" / "ts_daily_combo"
COMBO_DB = COMBO_DIR / "combo_paper.duckdb"
STATUS_PATH = COMBO_DIR / "status.json"
LOCK_PATH = COMBO_DIR / "combo_runner.pid"
HEARTBEAT_STALE_S = 300

_marks_lock = threading.Lock()
_marks_cache: dict = {"key": None, "marks": {}}


def runner_status(now: Optional[datetime] = None) -> dict:
    now = now or datetime.now()
    try:
        payload = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = {}
    age = None
    if payload.get("last_heartbeat"):
        age = (now - datetime.fromisoformat(payload["last_heartbeat"])).total_seconds()
    alive = pidfile.lock_alive(LOCK_PATH) and age is not None and age <= HEARTBEAT_STALE_S
    return {"running": alive, "heartbeat_age_s": round(age) if age is not None else None,
            "state": payload.get("state"), "reason": payload.get("reason")}


def _jsonable(v):
    return v.isoformat() if isinstance(v, (date, datetime)) else v


def combo_panel(n_days: int = 20) -> dict:
    status = runner_status()
    try:
        snap = read_snapshot(COMBO_DB, n_days=n_days)
    except duckdb.IOException:
        return {"status": status, "error": "Paper store busy — the runner is writing; retrying."}
    if snap is None:
        return {"status": status, "error": None, "empty": True}
    return {
        "status": status, "error": None, "empty": False,
        "meta": snap["meta"],
        "last_formation": _jsonable(snap["last_formation"]),
        "totals": {k: _jsonable(v) for k, v in snap["totals"].items()},
        "positions": [{k: _jsonable(v) for k, v in p.items()} for p in snap["positions"]],
        "daily": [{k: _jsonable(v) for k, v in d.items()} for d in snap["daily"]],
    }


def _resolve_marks(tickers, formation: date, today: date) -> dict:
    """ticker -> (instrument_key, ref_close, expiry): the nearest contract expiring
    after today (the contract the next formation's P&L is marked on), and its
    close at the last formation."""
    if not tickers:
        return {}
    f = duckdb.connect(str(FUT_DB), read_only=True)
    try:
        rows = f.execute("""
            WITH c AS (
                SELECT underlying, MIN(expiry_dt) AS exp FROM futures_bhavcopy
                WHERE inst_type = 'FUTSTK' AND trade_date = ? AND expiry_dt > ?
                  AND underlying IN (SELECT UNNEST(?::VARCHAR[]))
                GROUP BY underlying)
            SELECT c.underlying, c.exp, b.close FROM c
            JOIN futures_bhavcopy b ON b.underlying = c.underlying AND b.expiry_dt = c.exp
                 AND b.trade_date = ? AND b.inst_type = 'FUTSTK'
        """, [formation, today, list(tickers), formation]).fetchall()
    finally:
        f.close()
    inst = duckdb.connect(str(INST_DB), read_only=True)
    try:
        snap = inst.execute("SELECT MAX(snapshot_date) FROM instruments").fetchone()[0]
        out = {}
        for ticker, expiry, close in rows:
            key = future_key(inst, snap, ticker, expiry)
            if key and close:
                out[ticker] = (key, float(close), expiry)
        return out
    finally:
        inst.close()


def combo_live(fetch_quotes: Callable[[list], dict], today: Optional[date] = None) -> dict:
    """Live mark of the held book: P&L since the last formation's close."""
    today = today or date.today()
    try:
        snap = read_snapshot(COMBO_DB, n_days=1)
    except duckdb.IOException:
        return {"error": "Paper store busy", "rows": {}, "feed_ts": []}
    if not snap or not snap["positions"]:
        return {"error": None, "rows": {}, "feed_ts": [], "total_pnl": 0.0}
    formation = snap["last_formation"]
    tickers = sorted(p["underlying"] for p in snap["positions"])
    cache_key = (formation, today, tuple(tickers))
    with _marks_lock:
        if _marks_cache["key"] != cache_key:
            _marks_cache["marks"] = _resolve_marks(tickers, formation, today)
            _marks_cache["key"] = cache_key
        marks = dict(_marks_cache["marks"])

    result = fetch_quotes([m[0] for m in marks.values()])
    if result.get("error"):
        return {"error": result["error"], "rows": {}, "feed_ts": []}
    quotes = result["quotes"]
    rows, total, feed_ts = {}, 0.0, []
    for p in snap["positions"]:
        u = p["underlying"]
        mark = marks.get(u)
        q = quotes.get(mark[0]) if mark else None
        if not q or q.get("ltp") is None:
            rows[u] = {"ltp": None, "ref_close": mark[1] if mark else None, "pnl": None}
            continue
        sign = 1.0 if p["side"] == "LONG" else -1.0
        ret = q["ltp"] / mark[1] - 1.0
        pnl = sign * p["cap"] * ret
        total += pnl
        feed_ts.append(q.get("feed_ts"))
        rows[u] = {"ltp": q["ltp"], "ref_close": mark[1], "ret_pct": round(ret * 100, 3),
                   "pnl": round(pnl), "expiry": mark[2].isoformat()}
    return {"error": None, "rows": rows, "feed_ts": feed_ts, "total_pnl": round(total),
            "n_unpriced": sum(1 for r in rows.values() if r["pnl"] is None),
            "formation_date": formation.isoformat()}
