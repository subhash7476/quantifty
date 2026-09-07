"""Upstox basket-margin wrapper — parsing + graceful failure.

The benefit is derived as required - final, matching the Upstox order pad
(the pilot screenshot: 207082.47 - 72526.47 = 134556.00).
"""
import types

import pytest

import core.brokers.upstox_margin as um


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


@pytest.fixture
def _token(monkeypatch):
    monkeypatch.setattr(um, "credentials",
                        types.SimpleNamespace(get=lambda k: "tok"), raising=False)
    # credentials is imported inside the function; patch the module it comes from
    import core.auth.credentials as cred
    monkeypatch.setattr(cred, "credentials",
                        types.SimpleNamespace(get=lambda k: "tok"))


LEGS = [{"instrument_key": "NSE_FO|1", "transaction_type": "SELL", "quantity": 20},
        {"instrument_key": "NSE_FO|2", "transaction_type": "SELL", "quantity": 20},
        {"instrument_key": "NSE_FO|3", "transaction_type": "BUY", "quantity": 20},
        {"instrument_key": "NSE_FO|4", "transaction_type": "BUY", "quantity": 20}]


def test_parses_required_final_and_derives_benefit(_token, monkeypatch):
    payload = {"status": "success",
               "data": {"required_margin": 207082.47, "final_margin": 72526.47}}
    monkeypatch.setattr(um.requests, "post",
                        lambda *a, **k: _Resp(200, payload))
    out = um.fetch_basket_margin(LEGS)
    assert out["error"] is None
    assert out["required"] == pytest.approx(207082.47)
    assert out["final"] == pytest.approx(72526.47)
    assert out["benefit"] == pytest.approx(134556.00)


def test_no_legs_returns_error():
    out = um.fetch_basket_margin([])
    assert out["error"] == "no legs"
    assert out["required"] is None


def test_http_error_degrades(_token, monkeypatch):
    monkeypatch.setattr(um.requests, "post", lambda *a, **k: _Resp(401, {}))
    out = um.fetch_basket_margin(LEGS)
    assert out["required"] is None and "401" in out["error"]


def test_missing_fields_degrade(_token, monkeypatch):
    monkeypatch.setattr(um.requests, "post",
                        lambda *a, **k: _Resp(200, {"data": {}}))
    out = um.fetch_basket_margin(LEGS)
    assert out["required"] is None and "missing" in out["error"]
