"""
TS Basis Daily Blueprint
------------------------
Serves the TS Basis Daily signals dashboard.
Shows top longs/shorts for the latest formation date with run/refresh capability.

Endpoints
---------
GET  /ts-basis-daily/               render page
GET  /ts-basis-daily/api/signals    signals for date (?date=YYYY-MM-DD)
GET  /ts-basis-daily/api/dates      available formation dates
POST /ts-basis-daily/api/refresh    trigger build + facts refresh
"""
import subprocess
import sys
import threading
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb
from flask import Blueprint, render_template, jsonify, request, current_app

from core.analytics.options_selection import select_book_options
from core.brokers.upstox_market_data import UpstoxMarketData
from flask_app.middleware import login_required

ts_basis_daily_bp = Blueprint(
    "ts_basis_daily",
    __name__,
    url_prefix="/ts-basis-daily",
)

ROOT = Path(__file__).resolve().parents[2]
FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"
SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"

_refresh_lock = threading.Lock()
_refresh_status = {"running": False, "message": "", "last_run": None}

_options_lock = threading.Lock()
_options_cache = {"formation": None, "contracts": []}


def _get_facts_con():
    if not FACTS_DB.exists():
        return None
    return duckdb.connect(str(FACTS_DB), read_only=True)


def _get_signals_con():
    if not SIG_DB.exists():
        return None
    return duckdb.connect(str(SIG_DB), read_only=True)


@ts_basis_daily_bp.route("/")
@login_required
def index():
    latest_date = None
    n_formations = 0
    if FACTS_DB.exists():
        con = _get_facts_con()
        if con:
            latest_date = con.execute(
                "SELECT MAX(formation_date) FROM carry_facts"
            ).fetchone()[0]
            n_formations = con.execute(
                "SELECT COUNT(DISTINCT formation_date) FROM carry_facts"
            ).fetchone()[0]
            con.close()
    return render_template(
        "ts_basis_daily/index.html",
        latest_date=str(latest_date) if latest_date else None,
        n_formations=n_formations,
        refresh_status=_refresh_status,
    )


@ts_basis_daily_bp.route("/api/signals")
@login_required
def api_signals():
    target = request.args.get("date")
    con = _get_facts_con()
    if con is None:
        return jsonify({"error": "Facts DB not found. Run refresh first."}), 404

    if target:
        try:
            target_date = date.fromisoformat(target)
        except ValueError:
            return jsonify({"error": f"Invalid date: {target}"}), 400
    else:
        target_date = con.execute(
            "SELECT MAX(formation_date) FROM carry_facts"
        ).fetchone()[0]

    rows = con.execute("""
        SELECT underlying, z_carry_neut, quintile, eligible
        FROM carry_facts WHERE formation_date = ?
        ORDER BY z_carry_neut
    """, [target_date]).fetchall()
    con.close()

    if not rows:
        return jsonify({
            "date": str(target_date),
            "shorts": [], "longs": [], "n_liquid": 0,
            "n_total": 0, "n_long": 0, "n_short": 0,
        })

    liquid_rows = [r for r in rows if r[3]]
    n_liq = len(liquid_rows)
    nq = max(1, round(0.20 * n_liq)) if n_liq >= 5 else 0

    # Get context from signals DB
    sc = _get_signals_con()
    n_total = 0
    if sc:
        n_total = sc.execute(
            "SELECT COUNT(*) FROM signals WHERE formation_date = ? AND z_ts IS NOT NULL",
            [target_date],
        ).fetchone()[0]
        sc.close()

    shorts = [
        {"underlying": r[0], "z_ts": round(r[1], 4) if r[1] else None}
        for r in rows if r[2] == 1 and r[3]
    ][:10]
    longs = [
        {"underlying": r[0], "z_ts": round(r[1], 4) if r[1] else None}
        for r in reversed(rows) if r[2] == 5 and r[3]
    ][:10]

    return jsonify({
        "date": str(target_date),
        "shorts": shorts,
        "longs": longs,
        "n_liquid": n_liq,
        "n_total": n_total or len(rows),
        "n_long": sum(1 for r in rows if r[2] == 5 and r[3]),
        "n_short": sum(1 for r in rows if r[2] == 1 and r[3]),
        "nq": nq,
    })


LIVE_MAX_AGE_SEC = 60


def _market_state(feed_ts_values, now=None):
    """(state, age_seconds) from feed timestamp freshness.

    Freshness is judged by the feed's own timestamp, NEVER by whether the price
    moved: a thinly-traded strike legitimately does not print on every poll, and
    treating an unchanged price as staleness would mislabel a healthy feed.

    abs(): the local clock can sit slightly behind the exchange feed, producing a
    small negative age. Distance from now is what matters, in either direction.
    """
    stamps = [t for t in feed_ts_values if t]
    if not stamps:
        return "STALE", None
    now = now or datetime.now(timezone.utc)
    try:
        age = (now - datetime.fromisoformat(max(stamps))).total_seconds()
    except (ValueError, TypeError):
        return "STALE", None
    return ("LIVE" if abs(age) <= LIVE_MAX_AGE_SEC else "CLOSED"), age


def _load_book(con, formation_date):
    """The 10-name book for a formation: top-5 Q5 (LONG) + top-5 Q1 (SHORT)."""
    rows = con.execute("""
        SELECT underlying, quintile FROM carry_facts
        WHERE formation_date = ? AND eligible ORDER BY z_carry_neut
    """, [formation_date]).fetchall()
    shorts = [(u, "SHORT") for u, q in rows if q == 1][:5]
    longs = [(u, "LONG") for u, q in rows if q == 5][-5:][::-1]
    return longs + shorts


def _resolve_contracts(force: bool = False):
    """Resolve the latest formation's book into option contracts, cached by
    formation date so the 2s live path never touches DuckDB.

    force=True always re-resolves (re-anchors/re-screens against fresh live
    data) and refreshes the cache; force=False (the 2s live path) reuses the
    cached contracts whenever the formation hasn't changed."""
    con = _get_facts_con()
    if con is None:
        return None, None, "Facts DB not found. Run refresh first."
    formation = con.execute("SELECT MAX(formation_date) FROM carry_facts").fetchone()[0]
    if formation is None:
        con.close()
        return None, None, "No formations in facts DB."

    with _options_lock:
        if not force and _options_cache.get("formation") == formation:
            con.close()
            return formation, _options_cache["contracts"], None
        book = _load_book(con, formation)
        con.close()
        contracts = select_book_options(book)
        _options_cache["formation"] = formation
        _options_cache["contracts"] = contracts
    return formation, contracts, None


@ts_basis_daily_bp.route("/api/options")
@login_required
def api_options():
    """Option contracts for the latest formation. DuckDB only, no network."""
    formation, contracts, err = _resolve_contracts(force=True)
    if err:
        return jsonify({"error": err}), 404

    out = []
    for c in contracts:
        out.append({
            "ticker": c["ticker"],
            "direction": c["direction"],
            "opt_type": c["opt_type"],
            "expiry": str(c["expiry"]) if c["expiry"] else None,
            "strike": c["strike"],
            "settle": c["settle"],
            "oi": c["oi"],
            "lot_size": c["lot_size"],
            "instrument_key": c["instrument_key"],
            "tradingsymbol": c["tradingsymbol"],
            "premium_cost": c["premium_cost"],
            "snapped": c["snapped"],
            "anchor_source": c["anchor_source"],
            "screen": c["screen"],
            "screen_reason": c["screen_reason"],
            "spread_pct": c["spread_pct"],
            "best_bid": c["best_bid"],
            "best_ask": c["best_ask"],
        })
    return jsonify({
        "formation_date": str(formation),
        "quote_date": str(contracts[0]["quote_date"]) if contracts and contracts[0]["quote_date"] else None,
        "contracts": out,
    })


@ts_basis_daily_bp.route("/api/options/live")
@login_required
def api_options_live():
    """Live quotes for the cached book. One batched upstream call.

    Instrument keys come from the server-side cache, never from the request,
    so the outbound call is driven by the strategy's own book.
    """
    formation, contracts, err = _resolve_contracts()
    if err:
        return jsonify({"error": err, "state": "STALE"}), 404

    keys = [c["instrument_key"] for c in contracts if c["instrument_key"]]
    result = UpstoxMarketData().fetch_quotes_batch(keys)

    if result["error"]:
        return jsonify({
            "state": "STALE", "error": result["error"],
            "formation_date": str(formation), "quotes": {},
        })

    quotes = result["quotes"]
    state, age = _market_state([q.get("feed_ts") for q in quotes.values()])

    return jsonify({
        "state": state,
        "error": None,
        "formation_date": str(formation),
        "feed_age_sec": round(age, 1) if age is not None else None,
        "server_time": datetime.now().strftime("%d %b %H:%M:%S"),
        "quotes": quotes,
    })


@ts_basis_daily_bp.route("/api/dates")
@login_required
def api_dates():
    con = _get_facts_con()
    if con is None:
        return jsonify({"dates": [], "latest": None})

    dates = [r[0] for r in con.execute(
        "SELECT DISTINCT formation_date FROM carry_facts ORDER BY formation_date"
    ).fetchall()]
    latest = dates[-1] if dates else None
    con.close()
    return jsonify({
        "dates": [str(d) for d in dates[-30:]],  # last 30 for dropdown
        "latest": str(latest) if latest else None,
        "total": len(dates),
    })


@ts_basis_daily_bp.route("/api/refresh", methods=["POST"])
@login_required
def api_refresh():
    global _refresh_status

    if _refresh_lock.locked():
        return jsonify({
            "ok": False,
            "message": "Refresh already in progress",
            "status": _refresh_status,
        }), 409

    def _do_refresh():
        global _refresh_status
        with _refresh_lock:
            _refresh_status = {"running": True, "message": "Building signals...", "last_run": datetime.now().isoformat()}
            try:
                build_script = ROOT / "scripts" / "signal_engine" / "ts_basis_daily" / "build_ts_basis_daily.py"
                result = subprocess.run(
                    [sys.executable, str(build_script), "--incremental"],
                    cwd=str(ROOT), capture_output=True, text=True, timeout=300,
                )
                if result.returncode != 0:
                    _refresh_status = {
                        "running": False,
                        "message": f"Build failed: {result.stderr[-500:]}",
                        "last_run": datetime.now().isoformat(),
                    }
                    return

                _refresh_status["message"] = "Publishing facts..."
                pub_script = ROOT / "scripts" / "signal_engine" / "ts_basis_daily" / "publish_facts.py"
                result2 = subprocess.run(
                    [sys.executable, str(pub_script)],
                    cwd=str(ROOT), capture_output=True, text=True, timeout=120,
                )

                _refresh_status = {
                    "running": False,
                    "message": "Refresh complete",
                    "last_run": datetime.now().isoformat(),
                }
            except subprocess.TimeoutExpired:
                _refresh_status = {
                    "running": False,
                    "message": "Refresh timed out",
                    "last_run": datetime.now().isoformat(),
                }
            except Exception as e:
                _refresh_status = {
                    "running": False,
                    "message": f"Error: {e}",
                    "last_run": datetime.now().isoformat(),
                }

    thread = threading.Thread(target=_do_refresh, daemon=True)
    thread.start()
    return jsonify({"ok": True, "message": "Refresh started"})


@ts_basis_daily_bp.route("/api/status")
@login_required
def api_status():
    return jsonify(_refresh_status)
