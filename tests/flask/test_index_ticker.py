from pathlib import Path

from flask import Flask

ROOT = Path(__file__).resolve().parents[2]


class _FakeMarketData:
    def fetch_quotes_batch(self, keys):
        return {"quotes": {"NSE_INDEX|Nifty 50": {"ltp": 23248.1, "net_change": -229.7,
                                                  "change_pct": -0.98, "feed_ts": "t"}},
                "error": None}


def _client(monkeypatch):
    from flask_app.blueprints import index_ticker
    monkeypatch.setattr(index_ticker, "UpstoxMarketData", _FakeMarketData)
    app = Flask(__name__, template_folder=str(ROOT / "flask_app" / "templates"))
    app.config["SECRET_KEY"] = "test"
    app.register_blueprint(index_ticker.index_ticker_bp)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["username"] = "tester"
    return client


def test_index_ticker_returns_both_indices_in_page_order(monkeypatch):
    payload = _client(monkeypatch).get("/api/index-ticker").get_json()
    assert payload["error"] is None
    assert [i["key"] for i in payload["indices"]] == ["NIFTY", "SENSEX"]
    assert payload["indices"][0]["ltp"] == 23248.1
    assert payload["indices"][1]["ltp"] is None      # missing upstream quote → null, not a crash


def test_app_factory_registers_the_index_ticker_blueprint():
    source = (ROOT / "flask_app" / "__init__.py").read_text(encoding="utf-8")
    assert "app.register_blueprint(index_ticker_bp)" in source
