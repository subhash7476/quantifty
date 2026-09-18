import json
import socket

import pytest

from scripts.jev_nms_1.transport import (
    CLASSES, Transport, cache_key, canonical_request, validate_response,
)

TEMPLATE = {"question_id": "market_state",
            "state_field_order": ["minutes_since_open", "gap_bp", "er_30"],
            "question": {"type": "choice", "instructions": "Pick.",
                         "criteria": {c: c for c in CLASSES}}}


def test_canonical_bytes_order_and_fixed_decimals():
    body = canonical_request(TEMPLATE, {"er_30": 0.14, "gap_bp": -0.0, "minutes_since_open": 45})
    assert body == (b'{"model":"jev-1.13.0","state":{"minutes_since_open":45,"gap_bp":0.0,"er_30":0.140},'
                    b'"questions":{"market_state":{"type":"choice","instructions":"Pick.","criteria":'
                    b'{"trending_up":"trending_up","trending_down":"trending_down",'
                    b'"range_bound":"range_bound","disorderly":"disorderly"}}}}')
    json.loads(body)
    assert cache_key(body) == cache_key(bytes(body))


def _ok(probs=None, model="jev-1.13.0", choice="range_bound"):
    probs = probs or {"trending_up": 0.1, "trending_down": 0.1, "range_bound": 0.6, "disorderly": 0.2}
    return json.dumps({"model": model, "answers": {"market_state": {
        "choice": choice, "probabilities": probs, "confidence": 0.6}}}).encode()


def test_validation():
    assert validate_response(_ok(), "market_state")["valid"]
    assert not validate_response(_ok(model="jev-1.12.0"), "market_state")["valid"]
    assert not validate_response(_ok(choice="up"), "market_state")["valid"]
    assert not validate_response(_ok({"a": 1.0}), "market_state")["valid"]
    assert not validate_response(b"not json", "market_state")["valid"]
    bad = {"trending_up": 1.5, "trending_down": 0, "range_bound": 0, "disorderly": 0}
    assert not validate_response(_ok(bad), "market_state")["valid"]


class _Resp:
    def __init__(self, status, body=b"{}"):
        self.status, self._body = status, body

    def read(self):
        return self._body

    def getheader(self, k, default=None):
        return {"x-typesafe-request-id": "rid", "x-envoy-upstream-service-time": "12"}.get(k, default)

    def getheaders(self):
        return [("x-typesafe-request-id", "rid"), ("set-cookie", "secret")]


class _Conn:
    def __init__(self, script, sent):
        self.script, self.sent, self.sock, self.timeout = script, sent, None, None

    def request(self, method, path, body, headers):
        self.sent.append((body, headers))
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        self._resp = step

    def getresponse(self):
        return self._resp

    def close(self):
        pass


def _run(script, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "SECRET-KEY-VALUE")
    sent, sleeps = [], []
    t = Transport(connection_factory=lambda: _Conn(script, sent), sleep=sleeps.append)
    return t.send_historical(b"BODY"), sent, sleeps


def test_retry_on_429_then_success_with_identical_bytes(monkeypatch):
    attempts, sent, sleeps = _run([_Resp(429), _Resp(200, _ok())], monkeypatch)
    assert [a["status"] for a in attempts] == [429, 200] and sleeps == [2]
    assert all(b == b"BODY" for b, _ in sent)


def test_no_retry_after_200_even_if_schema_invalid_or_after_other_4xx(monkeypatch):
    assert len(_run([_Resp(200, b"garbage")], monkeypatch)[0]) == 1
    assert len(_run([_Resp(400)], monkeypatch)[0]) == 1


def test_at_most_three_retries_with_2_4_8_backoff(monkeypatch):
    attempts, _, sleeps = _run([socket.timeout(), _Resp(503), ConnectionResetError(),
                                _Resp(500), _Resp(200, _ok())], monkeypatch)
    assert len(attempts) == 4 and sleeps == [2, 4, 8]
    assert [a["outcome"] for a in attempts] == ["timeout", "http", "connection_error", "http"]


def test_api_key_never_appears_in_records(monkeypatch):
    attempts, sent, _ = _run([_Resp(200, _ok())], monkeypatch)
    assert "SECRET-KEY-VALUE" not in json.dumps(attempts)
    assert "set-cookie" not in json.dumps(attempts).lower()
    assert sent[0][1]["Authorization"] == "Bearer SECRET-KEY-VALUE"
