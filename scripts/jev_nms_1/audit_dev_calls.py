"""JEV-NMS-1 read-only audit of the 1,600 development call records.

Reads only the committed cache, ledger and development artifact. No network
access, no Jev call, and no write to any experiment artifact.

The TypeSafe request ID is 32 hex digits after `req_`. Where its first 48 bits
decode as a Unix-millisecond timestamp (the UUIDv7 layout), the decoded time
is compared with the locally recorded send/receive window; this is reported as
evidence only, since the ID format is not documented by TypeSafe.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "jev_market_state"
MODEL = "jev-1.13.0"
REQ_ID = re.compile(r"^req_[0-9a-f]{32}$")


def _iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def id_time(request_id: str) -> datetime:
    return datetime.fromtimestamp(int(request_id[4:16], 16) / 1000, tz=timezone.utc)


def ledger_prefix_sha(lines: list[str], event: str) -> str:
    for i, line in enumerate(lines):
        if json.loads(line)["event"] == event:
            return hashlib.sha256("".join(x + "\n" for x in lines[:i + 1]).encode("utf-8")).hexdigest()
    raise KeyError(event)


def audit() -> dict:
    cache_bytes = (OUT / "cache.jsonl").read_bytes()
    ledger_text = (OUT / "ledger.jsonl").read_text(encoding="utf-8")
    ledger_lines = ledger_text.splitlines()
    events = [json.loads(x) for x in ledger_lines]
    recs = [json.loads(x) for x in cache_bytes.decode("utf-8").splitlines()]
    dev = [r for r in recs if r["stage"] == "development"]
    other = [r for r in recs if r["stage"] != "development"]
    started = next(e for e in events if e["event"] == "development_started")
    done = next(e for e in events if e["event"] == "development_calls_completed")
    planned = [p["key"] for p in started["planned"]]

    problems = []
    for r in dev:
        a = r["attempts"][-1] if r["attempts"] else {}
        raw = r.get("response_raw") or ""
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {}
        checks = {
            "request_sha256": hashlib.sha256(r["request_bytes"].encode("utf-8")).hexdigest()
            == r["key"] == r["request_sha256"],
            "request_model": json.loads(r["request_bytes"])["model"] == MODEL,
            "http_200": a.get("status") == 200 and a.get("outcome") == "http",
            "raw_response_model": body.get("model") == MODEL,
            "raw_matches_parse": (body.get("answers", {}).get(r["question_id"], {}).get("probabilities")
                                  == r["validity"]["probabilities"]),
            "request_id": bool(REQ_ID.match(a.get("request_id") or ""))
            and a.get("headers", {}).get("x-typesafe-request-id") == a.get("request_id"),
            "content_length": a.get("headers", {}).get("content-length") == str(len(raw.encode("utf-8"))),
            "server_headers": a.get("headers", {}).get("server") == "istio-envoy"
            and "date" in a.get("headers", {}) and a.get("upstream_ms") is not None,
            "valid": r["validity"]["valid"] is True and r["validity"]["model"] == MODEL,
            "retries_0": r["retries"] == 0 and len(r["attempts"]) == 1,
            "provenance": r["run_id"] == started["run_id"] and r["cache"] == "miss_sent"
            and r["authoritative"] is True,
        }
        bad = [k for k, v in checks.items() if not v]
        if bad:
            problems.append({"state": r["state"], "template": r["template"], "failed": bad})

    ids = [r["attempts"][-1]["request_id"] for r in dev]
    other_ids = {a["request_id"] for r in other for a in r["attempts"] if a.get("request_id")}
    # timing evidence: server Date header and ID-embedded time vs the local send/receive window
    date_skew, id_skew = [], []
    for r in dev:
        a = r["attempts"][-1]
        sent, recv = _iso(a["request_sent_at"]), _iso(a["response_received_at"])
        hd = parsedate_to_datetime(a["headers"]["date"])
        date_skew.append(max((sent.replace(microsecond=0) - hd).total_seconds(), (hd - recv).total_seconds(), 0))
        it = id_time(a["request_id"])
        id_skew.append(max((sent - it).total_seconds(), (it - recv).total_seconds(), 0))
    sends = sorted(_iso(r["attempts"][-1]["request_sent_at"]) for r in dev)
    id_order = [id_time(i) for i in ids]
    gaps = [(b - a).total_seconds() for a, b in zip(sends, sends[1:])]
    analysis = json.loads((OUT / "development_step6.json").read_text(encoding="utf-8"))
    return {
        "cache_records": len(recs),
        "by_stage": dict(Counter(r["stage"] for r in recs)),
        "dev_records": len(dev),
        "dev_by_template": dict(Counter(r["template"] for r in dev)),
        "dev_keys_distinct": len({r["key"] for r in dev}),
        "dev_keys_equal_started_in_order": [r["key"] for r in dev] == planned,
        "dev_keys_overlap_other_stages": len({r["key"] for r in dev} & {r["key"] for r in other}),
        "request_ids": len(ids), "request_ids_distinct": len(set(ids)),
        "request_ids_overlap_other_stages": len(set(ids) & other_ids),
        "request_ids_monotonic_in_send_order": id_order == sorted(id_order),
        "retries_total": sum(r["retries"] for r in dev),
        "distinct_raw_response_bodies": len({r["response_raw"] for r in dev}),
        "per_record_problems": problems,
        "server_date_outside_local_window_max_s": max(date_skew),
        "id_time_outside_local_window_max_s": max(id_skew),
        "send_window": [sends[0].isoformat(), sends[-1].isoformat()],
        "max_gap_between_sends_s": max(gaps), "min_gap_between_sends_s": min(gaps),
        "usage_tokens": {"input": sum(r["validity"]["usage"]["input_tokens"] for r in dev),
                         "output": sum(r["validity"]["usage"]["output_tokens"] for r in dev)},
        "usage_tokens_other_stages": {
            "input": sum(r["validity"]["usage"]["input_tokens"] for r in other if r["validity"].get("usage")),
            "output": sum(r["validity"]["usage"]["output_tokens"] for r in other if r["validity"].get("usage"))},
        "cache_sha256": hashlib.sha256(cache_bytes).hexdigest(),
        "calls_completed_event": {k: done[k] for k in ("records", "valid", "cache_sha256", "run_id")},
        "ledger_sha256_through_calls_completed": ledger_prefix_sha(ledger_lines, "development_calls_completed"),
        "ledger_sha256_through_development_completed": ledger_prefix_sha(ledger_lines, "development_completed"),
        "ledger_sha256_through_a3_ruling": ledger_prefix_sha(ledger_lines, "a3_ruling"),
        "analysis_cache_sha256": analysis["cache_sha256"],
        "analysis_valid_observations": {h: v["valid_observations"] for h, v in analysis["horizons"].items()},
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=1, default=str))
