"""Global index ticker — Nifty 50 and Sensex spot, polled by the app shell.

Register in flask_app/__init__.py:

    from flask_app.blueprints.index_ticker import index_ticker_bp
    app.register_blueprint(index_ticker_bp)

Serves GET /api/index-ticker:

    {
      "server_time": "10 Sep 15:33:34",
      "error": null,
      "indices": [
        {"key": "NIFTY",  "label": "NIFTY 50", "ltp": 24812.4,
         "net_change": -38.2, "change_pct": -0.15, "feed_ts": "..."},
        {"key": "SENSEX", "label": "SENSEX",   "ltp": 81022.1, ...}
      ]
    }

One batched upstream call per poll, shared by every page in the shell.
"""

from datetime import datetime

from flask import Blueprint, jsonify

from core.brokers.upstox_market_data import UpstoxMarketData
from flask_app.middleware import login_required

index_ticker_bp = Blueprint("index_ticker", __name__)

TICKER_INDICES = [
    ("NIFTY", "NIFTY 50", "NSE_INDEX|Nifty 50"),
    ("SENSEX", "SENSEX", "BSE_INDEX|SENSEX"),
]


@index_ticker_bp.route("/api/index-ticker")
@login_required
def api_index_ticker():
    keys = [k for _, _, k in TICKER_INDICES]
    result = UpstoxMarketData().fetch_quotes_batch(keys)
    quotes = result.get("quotes") or {}

    indices = []
    for key, label, ikey in TICKER_INDICES:
        q = quotes.get(ikey) or {}
        indices.append({
            "key": key,
            "label": label,
            "ltp": q.get("ltp"),
            "net_change": q.get("net_change"),
            "change_pct": q.get("change_pct"),
            "feed_ts": q.get("feed_ts"),
        })

    return jsonify({
        "server_time": datetime.now().strftime("%d %b %H:%M:%S"),
        "error": result.get("error"),
        "indices": indices,
    })
