"""JEV-NMS-1 raw-HTTP transport (§11, §12, §12a, §25).

Canonical request bytes (§12a): UTF-8 JSON, `,`/`:` separators, top-level
order model, state, questions; state keys in §6 order as fixed-decimal
literals (bp 1 decimal, er_30 3 decimals, minutes integer, negative zero as
0); one question object {type, instructions, criteria} keyed by its question
ID. Cache key = SHA-256 of those bytes.

Transport: stdlib http.client.HTTPSConnection, keep-alive, POST
/v1/systemone, 20 s per attempt (connect + read, enforced as one deadline).
Historical retry policy: retry only on connection error, timeout, HTTP 429 or
5xx; at most 3 retries with 2/4/8 s back-off; never after HTTP 200
(schema-invalid included) or any other 4xx; identical bytes every attempt.

The API key is read from TYPESAFE_API_KEY at send time, placed only in the
Authorization header, and never logged, returned, persisted or hashed.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import math
import os
import socket
import time
from datetime import datetime, timezone

HOST = "api.typesafe.ai"
PATH = "/v1/systemone"
MODEL = "jev-1.13.0"
TIMEOUT_S = 20.0
HISTORICAL_BACKOFF_S = (2, 4, 8)
CLASSES = ("trending_up", "trending_down", "range_bound", "disorderly")
DECIMALS = {"minutes_since_open": None, "er_30": 3}
SUM_TOLERANCE = 1e-6
SAFE_HEADER_EXCLUDE = ("authorization", "cookie", "set-cookie")


def _literal(field: str, value) -> str:
    places = DECIMALS.get(field, 1)
    if places is None:
        return str(int(value))
    text = format(float(value), f".{places}f")
    return text[1:] if text.startswith("-") and float(text) == 0 else text


def canonical_request(template: dict, state: dict) -> bytes:
    fields = template["state_field_order"]
    state_json = "{" + ",".join(f"{json.dumps(k)}:{_literal(k, state[k])}" for k in fields) + "}"
    q = template["question"]
    question = json.dumps({"type": q["type"], "instructions": q["instructions"],
                           "criteria": q["criteria"]}, separators=(",", ":"), ensure_ascii=False)
    body = (f'{{"model":{json.dumps(MODEL)},"state":{state_json},'
            f'"questions":{{{json.dumps(template["question_id"])}:{question}}}}}')
    return body.encode("utf-8")


def cache_key(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def transport_id(transport_config: dict) -> str:
    return hashlib.sha256(json.dumps(transport_config, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_response(raw: bytes, question_id: str, classes: tuple = CLASSES) -> dict:
    """Schema/validity of a 200 body against the template's classes. Never raises."""
    out = {"valid": False, "reason": None, "choice": None, "probabilities": None,
           "confidence": None, "model": None, "usage": None, "probability_sum": None}
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        out["reason"] = f"unparseable: {type(exc).__name__}"
        return out
    out["model"] = doc.get("model") if isinstance(doc, dict) else None
    out["usage"] = doc.get("usage") if isinstance(doc, dict) else None
    answer = (doc.get("answers") or {}).get(question_id) if isinstance(doc, dict) else None
    if not isinstance(answer, dict):
        out["reason"] = "missing answers[question_id]"
        return out
    probs, choice = answer.get("probabilities"), answer.get("choice")
    out["confidence"] = answer.get("confidence")
    if out["model"] != MODEL:
        out["reason"] = f"model identifier mismatch: {out['model']!r}"
        return out
    if not isinstance(probs, dict) or set(probs) != set(classes):
        out["reason"] = f"probability keys {sorted(probs) if isinstance(probs, dict) else probs!r}"
        return out
    values = [probs[k] for k in classes]
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
               and 0.0 <= v <= 1.0 for v in values):
        out["reason"] = "probability value outside [0, 1] or non-numeric"
        return out
    out["probabilities"] = dict(zip(classes, values))
    out["probability_sum"] = math.fsum(values)
    if choice not in classes:
        out["reason"] = f"choice {choice!r} is not a frozen class"
        return out
    out["choice"] = choice
    out["valid"] = True
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Transport:
    """One persistent keep-alive connection; historical retry policy."""

    def __init__(self, connection_factory=None, sleep=time.sleep):
        self._factory = connection_factory or (
            lambda: http.client.HTTPSConnection(HOST, 443, timeout=TIMEOUT_S))
        self._sleep = sleep
        self._conn = None

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _attempt(self, body: bytes) -> dict:
        key = os.environ["TYPESAFE_API_KEY"]
        headers = {"Content-Type": "application/json", "Connection": "keep-alive",
                   "Authorization": f"Bearer {key}"}
        rec = {"request_sent_at": _now()}
        t0 = time.perf_counter()
        deadline = t0 + TIMEOUT_S
        try:
            if self._conn is None:
                self._conn = self._factory()
            reused = self._conn.sock is not None
            self._conn.timeout = TIMEOUT_S
            self._conn.request("POST", PATH, body=body, headers=headers)
            if self._conn.sock is not None:
                self._conn.sock.settimeout(max(deadline - time.perf_counter(), 0.001))
            resp = self._conn.getresponse()
            if self._conn.sock is not None:
                self._conn.sock.settimeout(max(deadline - time.perf_counter(), 0.001))
            raw = resp.read()
            elapsed = time.perf_counter() - t0
            rec.update({
                "outcome": "http", "status": resp.status, "raw": raw.decode("utf-8", "replace"),
                "response_received_at": _now(), "latency_ms": round(elapsed * 1000, 1),
                "connection_reused": reused,
                "request_id": resp.getheader("x-typesafe-request-id"),
                "upstream_ms": resp.getheader("x-envoy-upstream-service-time"),
                "headers": {k: v for k, v in resp.getheaders()
                            if k.lower() not in SAFE_HEADER_EXCLUDE}})
            if resp.getheader("connection", "").lower() == "close":
                self.close()
        except (socket.timeout, TimeoutError) as exc:
            self.close()
            rec.update({"outcome": "timeout", "error": type(exc).__name__,
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 1)})
        except (OSError, http.client.HTTPException) as exc:
            self.close()
            rec.update({"outcome": "connection_error", "error": type(exc).__name__,
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 1)})
        return rec

    def send_historical(self, body: bytes) -> list[dict]:
        """All attempts in order; the last is the one whose result is used."""
        attempts = []
        for i in range(len(HISTORICAL_BACKOFF_S) + 1):
            rec = self._attempt(body)
            attempts.append(rec)
            if not retryable(rec) or i == len(HISTORICAL_BACKOFF_S):
                break
            self._sleep(HISTORICAL_BACKOFF_S[i])
        return attempts


def retryable(rec: dict) -> bool:
    if rec["outcome"] in ("timeout", "connection_error"):
        return True
    return rec["status"] == 429 or 500 <= rec["status"] <= 599
