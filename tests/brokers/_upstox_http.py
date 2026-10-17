"""
Stand-in for the HTTP layer under UpstoxAdapter (`requests.request`).

Routes are registered per (method, path under BASE_URL). Any other call — an
unregistered path, or a URL on another host — fails the test with an
AssertionError, so a test that installs this can never reach Upstox.
"""

import requests

from core.brokers.upstox_adapter import UpstoxAdapter


class _Response:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


class FakeUpstoxHttp:
    def __init__(self):
        self.calls = []
        self._routes = {}

    def route(self, method, path, *responses):
        """Each call to (method, path) returns the next response; the last one
        repeats. A response is a payload dict, or an exception to raise."""
        self._routes[(method, path)] = list(responses)

    def route_order(self, method, path, order_id, *responses):
        """Like route, but only for calls whose order_id param matches."""
        self._routes[(method, path, order_id)] = list(responses)

    def __call__(self, method, url, headers=None, json=None, params=None, timeout=None):
        base = UpstoxAdapter.BASE_URL
        path = url[len(base):] if url.startswith(base) else url
        self.calls.append({"method": method, "path": path, "json": json, "params": params})
        order_id = (params or {}).get("order_id")
        queue = (self._routes.get((method, path, order_id))
                 or self._routes.get((method, path)))
        if not queue:
            raise AssertionError(f"unrouted Upstox call: {method} {url}")
        response = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(response, Exception):
            raise response
        return _Response(response)

    def calls_to(self, method, path):
        return [c for c in self.calls if c["method"] == method and c["path"] == path]


def install(monkeypatch):
    """Replace requests.request for the test and stop the adapter sleeping."""
    fake = FakeUpstoxHttp()
    monkeypatch.setattr(requests, "request", fake)
    monkeypatch.setattr("core.brokers.upstox_adapter.time.sleep", lambda s: None)
    return fake


def placed(order_id):
    return {"status": "success", "data": {"order_id": order_id}}


def order_details(order_id, status, *, quantity, filled, average_price,
                  instrument_token, transaction_type, status_message=None):
    """The documented GET /v2/order/details response shape (Upstox API docs,
    get-order-details example), with the fields a fill needs made explicit."""
    return {
        "status": "success",
        "data": {
            "exchange": "NSE",
            "product": "I",
            "price": 0.0,
            "quantity": quantity,
            "status": status,
            "tag": None,
            "instrument_token": instrument_token,
            "trading_symbol": "SBIN-EQ",
            "order_type": "MARKET",
            "validity": "DAY",
            "trigger_price": 0.0,
            "disclosed_quantity": 0,
            "transaction_type": transaction_type,
            "average_price": average_price,
            "filled_quantity": filled,
            "pending_quantity": quantity - filled,
            "status_message": status_message,
            "exchange_order_id": "1300000025660919",
            "order_id": order_id,
            "variety": "SIMPLE",
            "order_timestamp": "2023-10-19 13:25:13",
            "exchange_timestamp": "2023-10-19 13:25:13",
            "is_amo": False,
        },
    }
