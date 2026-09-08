"""NiftyShield PAPER window blueprint — read-only wall in the Options Wall theme.

Serves the Stage-2 PAPER validation window's persisted evidence under
`data/nifty_shield/` (the orchestrator-pinned data root, `session.py`). The
window runner owns every write; this blueprint only reads, and every read
opens its own short-lived connection (DuckDB cross-process lock discipline,
`chain_poller.py:11-19`) — no DatabaseManager singleton, no caching of
files the runner mutates.

Staleness rule: values are always shown with the timestamp they carry. When
the market is closed the chain marks are the poller's last snapshot ("frozen
at close") — labeled as such by the template, never presented as live.

Endpoints
---------
GET /nifty-shield/               render page
GET /nifty-shield/api/window     whole-window evidence (sessions, fact, metrics,
                                 merged structures, journal tail, pnl series)
GET /nifty-shield/api/session    one session (?date=YYYY-MM-DD)
GET /nifty-shield/api/marks      latest option-chain snapshot summary
GET /nifty-shield/api/live       liveness: heartbeat, STOP, pids, marks warmth
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
from flask import Blueprint, jsonify, render_template, request

from flask_app.middleware import login_required

nifty_shield_bp = Blueprint("nifty_shield", __name__, url_prefix="/nifty-shield")

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "nifty_shield"
CHAIN_DB = ROOT / "data" / "options" / "chain_cache.duckdb"
CHAIN_POLLER_PID = ROOT / "data" / "options" / "chain_poller.pid"
CHAIN_HB = ROOT / "data" / "options" / "chain_poller_heartbeat.json"
SESSION_PID = ROOT / "data" / "ops" / "session.pid"
ORCHESTRATOR_PID = ROOT / "data" / "ops" / "orchestrator.pid"
STOP_FILE = ROOT / "STOP"
SPAN_DIR = ROOT / "data" / "span"

INITIAL_CAPITAL = 1_000_000.0
MARKS_WARM_MAX_AGE_S = 60.0
POLLER_WARM_MAX_AGE_S = 60.0

JOURNAL_EVENT_WHITELIST = {
    "STARTUP", "RUNNING", "STOPPED",
    "FACT_PUBLISH_SKIPPED", "ENTRY_MARGIN", "ENTRY_SKIPPED",
    "STRUCTURE_CLOSE", "KILL_SWITCH_ACTIVATED", "WATCHDOG_STALE_DATA",
    "STRATEGY_ERROR", "STRATEGY_QUARANTINED", "SIGNAL_CONTRACT_REJECTED",
    "BROKER_ERROR",
}


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _read_jsonl(path: Path) -> List[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except OSError:
        return []


def _iso_age_s(ts: Optional[str]) -> Optional[float]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return max(0.0, (datetime.now(dt.tzinfo) - dt).total_seconds())


def _window_evidence() -> Dict[str, Any]:
    from scripts.nifty_shield_paper.assemble_report import load_window_evidence
    from scripts.nifty_shield_paper.metrics_report import risk_metrics_report

    journal_path = DATA_ROOT / "journal.jsonl"
    trades_path = DATA_ROOT / "trading" / "trading.db"
    metrics_path = DATA_ROOT / "metrics.json"

    ev = load_window_evidence(DATA_ROOT, INITIAL_CAPITAL)
    metrics = risk_metrics_report(
        str(journal_path), str(trades_path), initial_capital=INITIAL_CAPITAL,
        metrics_json=str(metrics_path) if metrics_path.exists() else None)

    ev["metrics"]["per_structure"] = metrics.per_structure
    return ev


def _merged_structures(ev: Dict[str, Any]) -> List[dict]:
    """One card per attempted structure: metric rows + audit rows, deduped by
    group_id, with leg fills from the ledger attached."""
    from scripts.nifty_shield_paper.audit import audit_window

    audit = audit_window(str(DATA_ROOT / "journal.jsonl"),
                         str(DATA_ROOT / "trading" / "trading.db"))
    by_gid: Dict[str, Any] = {a.group_id: a for a in audit.structures}
    fills = _leg_fills(DATA_ROOT / "trading" / "trading.db")

    out: List[dict] = []
    seen: set = set()
    for p in ev["metrics"]["per_structure"]:
        gid = p["group_id"]
        seen.add(gid)
        a = by_gid.get(gid)
        out.append({
            "group_id": gid,
            "session": p["session"],
            "structure": p["structure"],
            "status": (a.status if a and a.status in ("entered", "partial")
                       else "entered"),
            "closed": bool(p["closed"]),
            "exit_reason": a.exit_reason if a else None,
            "reason": None,
            "pnl_rs": p["pnl_rs"],
            "risk_r": p["risk_r"],
            "r": p["r"],
            "margin_rs": p["margin_rs"],
            "gross_exposure_rs": p["gross_exposure_rs"],
            "leg_symbols": a.leg_symbols if a else [],
            "filled_legs": a.filled_legs if a else [],
            "fills": [fills.get((p["session"], s), [])
                      for s in (a.leg_symbols if a else [])],
            "leg_positions": [_leg_position(fills.get((p["session"], s), []))
                              for s in (a.leg_symbols if a else [])],
        })
    for a in audit.structures:
        if a.status != "skipped" or a.group_id in seen:
            continue
        out.append({
            "group_id": a.group_id,
            "session": a.session,
            "structure": a.structure,
            "status": "skipped",
            "closed": False,
            "exit_reason": None,
            "reason": a.reason,
            "pnl_rs": 0.0,
            "risk_r": None,
            "r": None,
            "margin_rs": None,
            "gross_exposure_rs": None,
            "leg_symbols": a.leg_symbols,
            "filled_legs": [],
            "fills": [],
            "leg_positions": [],
        })
    out.sort(key=lambda s: (s["session"] or "", 0 if s["closed"] else 1))
    return out


def _leg_fills(db_path: Path) -> Dict[tuple, List[dict]]:
    """Ledger fills keyed by (session, symbol).

    Symbol alone pools every session that ever traded that strike, so a
    re-traded strike nets its quantities across sessions and the leg's average
    entry and open quantity both come out wrong. One structure per session makes
    (session, symbol) the leg's real identity.
    """
    out: Dict[tuple, List[dict]] = {}
    if not db_path.exists():
        return out
    try:
        con = sqlite3.connect(db_path)
        rows = con.execute(
            "SELECT symbol, side, quantity, entry_price, pnl, fees, timestamp "
            "FROM trades ORDER BY timestamp").fetchall()
        con.close()
    except sqlite3.Error:
        return out
    for sym, side, qty, price, pnl, fees, ts in rows:
        session = str(ts)[:10]
        out.setdefault((session, sym), []).append({
            "side": side, "quantity": qty, "price": price,
            "pnl": pnl, "fees": fees, "timestamp": ts,
        })
    return out


def _leg_position(fills: List[dict]) -> Optional[dict]:
    """Open signed quantity and average entry for one leg, or None when flat.

    `signed_qty` is in units (the ledger quantity is already lots x lot_size),
    so a caller marks the leg with `(ltp - avg_price) * signed_qty` and must not
    apply lot_size again. `avg_price` divides by the signed quantity, not its
    absolute value -- a short leg's cost is negative and dividing by |qty| would
    report a negative average entry.
    """
    signed_qty = 0.0
    cost = 0.0
    for t in fills:
        qty = float(t.get("quantity") or 0.0)
        price = float(t.get("price") or 0.0)
        sign = 1.0 if str(t.get("side", "")).upper() == "BUY" else -1.0
        signed_qty += qty * sign
        cost += price * qty * sign
    if signed_qty == 0:
        return None
    return {"signed_qty": signed_qty, "avg_price": cost / signed_qty}


def _journal_tail(limit: int = 60, session: Optional[str] = None) -> List[dict]:
    events = _read_jsonl(DATA_ROOT / "journal.jsonl")
    if session:
        events = [e for e in events
                  if str(e.get("timestamp", "")).startswith(session)]
    out = []
    for e in reversed(events):
        if e.get("event_type") not in JOURNAL_EVENT_WHITELIST:
            continue
        out.append({
            "timestamp": e.get("timestamp"),
            "event_type": e.get("event_type"),
            "severity": e.get("severity"),
            "source_component": e.get("source_component"),
            "message": e.get("message"),
            "metadata": e.get("metadata", {}),
        })
        if len(out) >= limit:
            break
    return out


def _latest_fact() -> Optional[dict]:
    facts_db = DATA_ROOT / "facts.duckdb"
    if not facts_db.exists():
        return None
    try:
        con = duckdb.connect(str(facts_db), read_only=True)
        row = con.execute(
            "SELECT session_date, checkpoint, regime, regime_confidence, "
            "vix_close, vix_at_checkpoint, regime_fact_version, model_hash, "
            "produced_by, trained_on FROM day_type_facts "
            "ORDER BY session_date DESC LIMIT 1").fetchone()
        con.close()
    except Exception:
        return None
    if row is None:
        return None
    vix_at = row[5]
    vix_close = row[4]
    vix = vix_at if vix_at is not None else vix_close
    vix_source = "13:00 checkpoint" if vix_at is not None else "EOD close"
    from strategies.nifty_shield_v1.config import DEFAULT_CONFIG
    from strategies.nifty_shield_v1.structures import select_structure
    structure = select_structure(row[2], vix, DEFAULT_CONFIG)
    return {
        "session_date": str(row[0]),
        "checkpoint": row[1],
        "regime": row[2],
        "regime_confidence": row[3],
        "vix": vix,
        "vix_source": vix_source,
        "structure": structure,
        "regime_fact_version": row[6],
        "model_hash": (row[7] or "")[:8],
        "produced_by": row[8],
        "trained_on": row[9],
    }


def _sessions_list(ev: Dict[str, Any]) -> List[dict]:
    by_session = {d["session"]: d for d in ev.get("session_details", [])}
    summaries = {s["session_date"]: s for s in ev.get("session_summaries", [])}
    closed = ev.get("counting", {}).get("closed_by_session", {})
    out = []
    for session in sorted(by_session, reverse=True):
        d = by_session[session]
        summ = summaries.get(session, {})
        recorder = summ.get("recorder") or {}
        out.append({
            "session": session,
            "summary": summ,
            "telemetry_clean": d.get("telemetry_clean"),
            "recorded": d.get("recorded"),
            "closed_structures": d.get("closed_structures", 0),
            "counts_toward_window": d.get("counts_toward_window"),
            "exclusion_reasons": d.get("exclusion_reasons", []),
            "span_snapshot_hash": recorder.get("span_snapshot_hash"),
            "bars_processed": summ.get("bars_processed"),
            "signals_pulled": summ.get("signals_pulled"),
            "closed_by_session": closed.get(session, 0),
        })
    return out


def _pnl_series(structures: List[dict]) -> List[dict]:
    closed = [s for s in structures if s["closed"] and s["pnl_rs"] is not None]
    closed.sort(key=lambda s: s["session"] or "")
    cum = 0.0
    out = []
    for s in closed:
        cum += float(s["pnl_rs"])
        out.append({"session": s["session"], "pnl_rs": s["pnl_rs"], "cum": round(cum, 2)})
    return out


def _chain_summary() -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "available": False, "error": None, "snapshot_ts": None, "expiry": None,
        "underlying_ltp": None, "rows": 0, "strikes": [],
    }
    if not CHAIN_DB.exists():
        base["error"] = "chain cache not present"
    else:
        con = None
        last = None
        for attempt in range(3):
            try:
                con = duckdb.connect(str(CHAIN_DB), read_only=True)
                last = con.execute(
                    "SELECT MAX(snapshot_timestamp) FROM option_chain_snapshot"
                ).fetchone()[0]
                break
            except Exception as exc:
                last = exc
                con = None
                time.sleep(0.05)
        if con is None:
            base["error"] = f"chain cache unreadable: {last}"
        elif last is None:
            base["error"] = "chain cache has no snapshot yet"
        else:
            try:
                base["snapshot_ts"] = str(last)
                row = con.execute(
                    "SELECT expiry_date, underlying_ltp, COUNT(*) "
                    "FROM option_chain_snapshot WHERE snapshot_timestamp = ? "
                    "GROUP BY expiry_date, underlying_ltp "
                    "ORDER BY COUNT(*) DESC LIMIT 1", [last]).fetchone()
                base["expiry"] = str(row[0]) if row else None
                base["underlying_ltp"] = float(row[1]) if row and row[1] is not None else None
                base["rows"] = int(row[2]) if row else 0
                if base["underlying_ltp"] and base["expiry"]:
                    atm = int(round(base["underlying_ltp"] / 50.0) * 50)
                    lo, hi = atm - 150, atm + 150
                    strike_rows = con.execute(
                        "SELECT strike_price, option_type, ltp, iv "
                        "FROM option_chain_snapshot "
                        "WHERE snapshot_timestamp = ? AND expiry_date = ? "
                        "AND strike_price >= ? AND strike_price <= ? "
                        "ORDER BY strike_price, option_type",
                        [last, base["expiry"], lo, hi]).fetchall()
                    base["strikes"] = [
                        {"strike": r[0], "option_type": r[1],
                         "ltp": float(r[2]) if r[2] is not None else None,
                         "iv": float(r[3]) if r[3] is not None else None}
                        for r in strike_rows]
                base["available"] = True
            except Exception as exc:
                base["error"] = f"chain query failed: {exc}"
            finally:
                con.close()

    hb = _read_json(CHAIN_HB) or {}
    base["poller"] = {
        "last_snapshot": hb.get("last_snapshot"),
        "rows": hb.get("rows"),
        "expiry": hb.get("expiry"),
        "age_s": _iso_age_s(hb.get("last_snapshot")),
        "warm": (hb.get("rows", 0) or 0) > 0
                and (_iso_age_s(hb.get("last_snapshot")) or 1e9) <= POLLER_WARM_MAX_AGE_S,
    }
    return base


def _live_status() -> Dict[str, Any]:
    from core.database.utils.market_hours import MarketHours
    from scripts.ops.pidfile import lock_alive

    hb = _read_json(DATA_ROOT / "heartbeat.json") or {}
    hb_ts = hb.get("timestamp")
    hb_age = _iso_age_s(hb_ts)
    poller_hb = _read_json(CHAIN_HB) or {}
    poller_age = _iso_age_s(poller_hb.get("last_snapshot"))
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        # The date the gate strip must scope to. Without it the dashboard falls
        # back to the latest published FACT's date, so before today's 13:00
        # checkpoint it labelled yesterday's structure "1 attempted this
        # session" — a stale count reading as a live one.
        "today": today,
        "market_open": MarketHours.is_market_open(),
        "stop_present": STOP_FILE.exists(),
        "heartbeat": {
            "present": bool(hb),
            "timestamp": hb_ts,
            "age_s": hb_age,
            "market_open": hb.get("market_open"),
            "data_healthy": hb.get("data_healthy"),
            "equity": hb.get("equity"),
            "bars_processed": hb.get("bars_processed"),
            "trades_today": hb.get("trades_today"),
            "kill_switched": hb.get("kill_switched"),
            "fresh": hb_age is not None and hb_age <= 30.0,
        },
        "processes": {
            "session": lock_alive(SESSION_PID),
            "orchestrator": lock_alive(ORCHESTRATOR_PID),
            "poller": lock_alive(CHAIN_POLLER_PID),
        },
        "marks": {
            "rows": poller_hb.get("rows", 0) or 0,
            "age_s": poller_age,
            "warm": (poller_hb.get("rows", 0) or 0) > 0
                    and (poller_age or 1e9) <= MARKS_WARM_MAX_AGE_S,
        },
        "span": {
            "present": (SPAN_DIR / f"nse_fo_span_{today}.parquet").exists(),
        },
    }


def _sanitize(obj: Any) -> Any:
    """Replace non-finite floats (e.g. float('inf') profit_factor) with None —
    Python's json emits bare `Infinity`, which is invalid JSON for the browser."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    return obj


@nifty_shield_bp.route("/")
@login_required
def index():
    return render_template("nifty_shield/index.html")


@nifty_shield_bp.route("/api/window")
@login_required
def api_window():
    if not (DATA_ROOT / "journal.jsonl").exists():
        return jsonify({"exists": False, "sessions": [], "structures": [],
                        "journal": [], "fact": None, "metrics": None,
                        "audit": None, "window": None, "pnl_series": []})
    ev = _window_evidence()
    structures = _merged_structures(ev)
    return jsonify(_sanitize({
        "exists": True,
        "fact": _latest_fact(),
        "sessions": _sessions_list(ev),
        "window": ev.get("counting"),
        "metrics": ev.get("metrics"),
        "audit": ev.get("audit"),
        "structures": structures,
        "pnl_series": _pnl_series(structures),
        "journal": _journal_tail(60),
        "replay_rows": ev.get("replay_rows", []),
        "drill_rows": ev.get("drill_rows", []),
    }))


@nifty_shield_bp.route("/api/session")
@login_required
def api_session():
    session_date = request.args.get("date", "")
    if not session_date:
        return jsonify({"error": "date required"}), 400
    ev = _window_evidence()
    structures = [s for s in _merged_structures(ev)
                  if s["session"] == session_date]
    sessions = {s["session"]: s for s in _sessions_list(ev)}
    pkg = DATA_ROOT / "sessions" / session_date
    return jsonify(_sanitize({
        "session": session_date,
        "summary": sessions.get(session_date, {}).get("summary"),
        "telemetry": _read_json(pkg / "telemetry.json"),
        "structures": structures,
        "journal": _journal_tail(200, session=session_date),
        "replay": _read_json(pkg / "replay_result.json"),
        "drill": _read_json(pkg / "drill" / "drill_result.json"),
    }))


@nifty_shield_bp.route("/api/marks")
@login_required
def api_marks():
    return jsonify(_chain_summary())


def _leg_symbols_for(group_id: str) -> List[str]:
    """Leg tradingsymbols for one structure group, read from the journal's
    ENTRY_MARGIN / ENTRY_SKIPPED metadata (the same source _merged_structures
    uses). Returns [] if the group is unknown or has no legs."""
    events = _read_jsonl(DATA_ROOT / "journal.jsonl")
    for e in reversed(events):
        md = e.get("metadata") or {}
        if md.get("group_id") == group_id and e.get("event_type") in (
                "ENTRY_MARGIN", "ENTRY_SKIPPED"):
            return list(md.get("leg_symbols", []) or [])
    return []


def _leg_marks(symbols: List[str]) -> "tuple[Dict[str, dict], Optional[str]]":
    """Latest-snapshot LTP/IV/lot for the given tradingsymbols, keyed by the
    chain cache's `tradingsymbol` (which equals the strategy's leg symbols).
    Returns (marks_dict, snapshot_ts). A fresh read_only connection per call
    keeps this safe under the poller's DuckDB cross-process lock."""
    out: Dict[str, dict] = {}
    ts: Optional[str] = None
    if not symbols or not CHAIN_DB.exists():
        return out, ts
    placeholders = ",".join("?" for _ in symbols)
    for _ in range(3):
        con = None
        try:
            con = duckdb.connect(str(CHAIN_DB), read_only=True)
            ts = con.execute(
                "SELECT MAX(snapshot_timestamp) FROM option_chain_snapshot"
            ).fetchone()[0]
            if ts is None:
                con.close()
                return out, ts
            rows = con.execute(
                "SELECT tradingsymbol, ltp, iv, lot_size, underlying_ltp "
                "FROM option_chain_snapshot WHERE snapshot_timestamp = ? "
                f"AND tradingsymbol IN ({placeholders})", [ts, *symbols]).fetchall()
            con.close()
            ts = str(ts)
            for sym, ltp, iv, lot, und in rows:
                out[sym] = {
                    "ltp": float(ltp) if ltp is not None else None,
                    "iv": float(iv) if iv is not None else None,
                    "lot_size": int(lot) if lot is not None else None,
                    "underlying_ltp": float(und) if und is not None else None,
                    "snapshot_ts": ts,
                }
            return out, ts
        except Exception:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass
            time.sleep(0.05)
    return out, ts


@nifty_shield_bp.route("/api/marks/legs")
@login_required
def api_marks_legs():
    gid = request.args.get("g", "")
    if not gid:
        return jsonify({"error": "g required"}), 400
    symbols = _leg_symbols_for(gid)
    marks, ts = _leg_marks(symbols)
    return jsonify(_sanitize({
        "group_id": gid,
        "symbols": symbols,
        "marks": marks,
        "snapshot_ts": ts,
    }))


@nifty_shield_bp.route("/api/live")
@login_required
def api_live():
    return jsonify(_live_status())
