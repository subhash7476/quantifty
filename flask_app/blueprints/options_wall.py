"""Options-Wall dashboard blueprint — strictly read-only.

Reads the persisted scan trail (`wall_scan_results.duckdb`) and renders the ranked
farm list + regime river. The poller is the results DB's sole writer; this
blueprint opens only read-only connections, so no scan is triggered from here.

Endpoints
---------
GET  /options/wall/               render page
GET  /options/wall/api/farm       latest scan_results + current regime
GET  /options/wall/api/trades     open + closed paper flies with live marks
GET  /options/wall/api/regime     regime river (latest per trade_date)
GET  /options/wall/api/health     poller step health from the heartbeat file
"""

from __future__ import annotations

import json
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from core.options_wall import persistence
from core.options_wall.engine import UNDERLYINGS
from core.options_wall.health import WALL_HEARTBEAT_PATH
from flask_app.middleware import login_required

options_wall_bp = Blueprint("options_wall", __name__, url_prefix="/options/wall")

HEARTBEAT_STALE_S = 60


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


@options_wall_bp.route("/api/margin")
@login_required
def api_margin():
    """Exchange margin (Upstox) for the ATM iron fly of the given index.

    Reconstructs the executor's ATM/wing structure from the newest snapshot and
    asks Upstox for the required/final margin + spread benefit. Makes no DB write
    (single-writer discipline intact); an outbound broker call only.
    """
    index = request.args.get("index", "NIFTY").upper()
    lots = request.args.get("lots", 1, type=int)
    from core.options_wall.engine import iron_fly_margin_legs
    from core.brokers.upstox_margin import fetch_basket_margin

    fly = iron_fly_margin_legs(index, lots=max(1, lots))
    if fly is None:
        return jsonify({"index": index, "margin": None,
                        "error": "no snapshot / structure unavailable"})
    margin = fetch_basket_margin(fly["legs"])
    return jsonify({"index": index, "fly": fly, "margin": margin,
                    "error": margin.get("error")})


@options_wall_bp.route("/api/evidence")
@login_required
def api_evidence():
    """Expectancy analytics over closed paper flies (read-only).

    Overall + breakdowns by exit reason, GEX regime at entry, and IV−RV band.
    `index=ALL` aggregates across underlyings; otherwise one index.
    """
    index = request.args.get("index", "NIFTY").upper()
    from core.options_wall.evidence import evidence_summary
    name = None if index == "ALL" else index
    return jsonify({"index": index, "summary": evidence_summary(name)})


@options_wall_bp.route("/api/close", methods=["POST"])
@login_required
def api_close():
    """Queue a manual close for one open paper trade (Flask → poller).

    Writes only a request file — never the results DB — so the poller stays the
    DB's sole writer. The poller closes the trade at current marks next cycle.
    """
    body = request.get_json(silent=True) or {}
    index = str(body.get("index", request.args.get("index", "NIFTY"))).upper()
    trade_id = body.get("trade_id")
    if trade_id is None:
        return jsonify({"ok": False, "error": "trade_id required"}), 400
    sym = _sym(index)
    open_ids = {t["trade_id"] for t in persistence.open_trades(sym)}
    if int(trade_id) not in open_ids:
        return jsonify({"ok": False, "error": "not an open trade"}), 404
    from core.options_wall import commands
    from core.database.utils.market_hours import MarketHours
    commands.request_close(int(trade_id), index)
    return jsonify({"ok": True, "queued": True, "trade_id": int(trade_id),
                    "market_open": MarketHours.is_derivatives_open()})


@options_wall_bp.route("/api/regime")
@login_required
def api_regime():
    index = request.args.get("index", "NIFTY").upper()
    days = request.args.get("days", 30, type=int)
    sym = _sym(index)
    return jsonify({"index": index, "river": persistence.regime_river(sym, days)})


def _health_payload() -> dict:
    unknown = {"status": "UNKNOWN", "steps": {}, "heartbeat_age_s": None, "stale": True}
    try:
        hb = json.loads(WALL_HEARTBEAT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return unknown
    last = hb.get("last_snapshot")
    if not last:
        return unknown
    age = (datetime.now() - datetime.fromisoformat(last)).total_seconds()
    stale = age > HEARTBEAT_STALE_S
    return {
        "status": "UNKNOWN" if stale else hb.get("status", "UNKNOWN"),
        "steps": hb.get("steps", {}),
        "heartbeat_age_s": round(age, 1),
        "stale": stale,
    }


@options_wall_bp.route("/api/health")
@login_required
def api_health():
    return jsonify(_health_payload())
