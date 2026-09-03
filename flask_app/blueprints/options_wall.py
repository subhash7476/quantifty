"""Options-Wall dashboard blueprint.

Reads the persisted scan trail (`wall_scan_results.duckdb`) and renders the ranked
farm list + regime river. A refresh endpoint triggers `scan_and_persist()` in a
background thread so the panel can pull a fresh scan on demand.

Endpoints
---------
GET  /options/wall/               render page
GET  /options/wall/api/farm       latest scan_results + current regime
GET  /options/wall/api/regime     regime river (latest per trade_date)
POST /options/wall/api/refresh    trigger scan_and_persist in a background thread
GET  /options/wall/api/status     refresh status
"""

from __future__ import annotations

import threading
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from core.logging import setup_logger
from core.options_wall import persistence
from core.options_wall.engine import UNDERLYINGS
from flask_app.middleware import login_required

logger = setup_logger("options_wall_bp")

options_wall_bp = Blueprint("options_wall", __name__, url_prefix="/options/wall")

_refresh_lock = threading.Lock()
_refresh_status = {"running": False, "message": "", "last_run": None}


def _sym(index: str) -> str:
    return UNDERLYINGS.get(index.upper(), UNDERLYINGS["NIFTY"])


@options_wall_bp.route("/")
@login_required
def index():
    return render_template("options_wall/index.html")


@options_wall_bp.route("/api/farm")
@login_required
def api_farm():
    index = request.args.get("index", "NIFTY").upper()
    sym = _sym(index)
    ts, rows = persistence.latest_scan_results(sym)
    river = persistence.regime_river(sym, 1)
    regime = river[-1] if river else None
    return jsonify({
        "index": index,
        "ts": ts.isoformat() if ts else None,
        "regime": regime,
        "rows": rows,
    })


@options_wall_bp.route("/api/trades")
@login_required
def api_trades():
    index = request.args.get("index", "NIFTY").upper()
    from core.options_wall.engine import trades_view
    rows = trades_view(index)
    for r in rows:
        for k in ("entry_ts", "exit_ts"):
            if r.get(k) is not None:
                r[k] = r[k].isoformat()
    return jsonify({"index": index, "trades": rows})


@options_wall_bp.route("/api/regime")
@login_required
def api_regime():
    index = request.args.get("index", "NIFTY").upper()
    days = request.args.get("days", 30, type=int)
    sym = _sym(index)
    return jsonify({"index": index, "river": persistence.regime_river(sym, days)})


@options_wall_bp.route("/api/refresh", methods=["POST"])
@login_required
def api_refresh():
    if _refresh_lock.locked():
        return jsonify({
            "ok": False, "message": "Refresh already in progress",
            "status": _refresh_status,
        }), 409

    def _do_refresh():
        global _refresh_status
        with _refresh_lock:
            _refresh_status = {"running": True, "message": "Scanning...",
                               "last_run": datetime.now().isoformat()}
            try:
                from core.options_wall.engine import scan_and_persist
                written = scan_and_persist()
                _refresh_status = {"running": False, "message": f"Persisted {written}",
                                   "last_run": datetime.now().isoformat()}
            except Exception as e:
                logger.error("wall refresh failed: %s", e)
                _refresh_status = {"running": False, "message": f"Error: {e}",
                                   "last_run": datetime.now().isoformat()}

    threading.Thread(target=_do_refresh, daemon=True).start()
    return jsonify({"ok": True, "message": "Refresh started"})


@options_wall_bp.route("/api/status")
@login_required
def api_status():
    return jsonify(_refresh_status)
