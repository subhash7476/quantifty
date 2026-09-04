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
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from core.options_wall import persistence
from core.options_wall.engine import UNDERLYINGS
from flask_app.middleware import login_required

options_wall_bp = Blueprint("options_wall", __name__, url_prefix="/options/wall")


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
