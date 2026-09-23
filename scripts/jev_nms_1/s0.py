"""JEV-NMS-1 §23 S0 — the preregistered unscored smoke/structural probe.

Exactly the 10 D3 states (5 D-fit sessions x {10:00, 14:30}), each sent once
as an ordinary cached request using the sealed h15 template (A2-4). Outputs are
checked for parsing/validity only (§11A item 9); nothing here scores, fits or
interprets them.

Before any send: the A2 seal, the template hash, the step-1/step-2 artifacts
and a request audit (every state's features rebuilt from the store's D and the
recorded C_prev must equal the sealed feature artifact field by field). The run
is written to the ledger before any result is visible (§22). Cache and S0
artifacts are append-only / create-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from scripts.jev_nms_1.eligibility import load_seal
from scripts.jev_nms_1.features import load_window_bars, raw_features, rounded, slot_index
from scripts.jev_nms_1.transport import (
    MODEL, SUM_TOLERANCE, Transport, cache_key, canonical_request, transport_id,
    validate_response,
)

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "jev_market_state"
CACHE = OUT / "cache.jsonl"
ARTIFACT_NAME = "s0_step3.json"
HASHES = {
    "eligibility_step1.json": "b5d1cd48b11667c15a3d744ebea81db7d0a11c7aa03a7e4420e2e9dc98344c77",
    "draws_step2.json": "e4c1f3c957b49ebfcfb0915ff0f5675467a953e58a9b82546a9ba4e007733de8",
    "features_step2.json": "29997617dba1888c4f66ff28da85e4ad42f3866b8b5bcd59d2b43e0404049eb3",
}


def _artifact(name: str) -> dict:
    raw = (OUT / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASHES[name]:
        raise RuntimeError(f"{name} does not match its accepted SHA-256")
    return json.loads(raw.decode("utf-8"))


def _append(path: Path, rec: dict) -> None:
    with open(path, "a", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")


def cached_keys() -> set[str]:
    if not CACHE.exists():
        return set()
    return {json.loads(line)["key"] for line in CACHE.read_text(encoding="utf-8").splitlines()}


def prepare(store: Path) -> tuple[list[dict], dict, dict]:
    config, _ = load_seal()
    tpl_ref = config["templates"]["h15"]
    tpl_raw = (REPO / tpl_ref["file"]).read_bytes()
    if hashlib.sha256(tpl_raw).hexdigest() != tpl_ref["sha256"]:
        raise RuntimeError("h15 template does not match its sealed SHA-256")
    template = json.loads(tpl_raw.decode("utf-8"))
    elig, draws, feats = (_artifact(n) for n in HASHES)
    by_date = {r["date"]: r for r in elig["sessions"]["d_fit"]}
    planned = []
    for key in draws["draws"]["d3_s0"]["states"]:
        d, slot = key.split("|")
        rec = by_date[d]
        if not rec["eligible"]:
            raise RuntimeError(f"S0 state {key} is not an eligible D-fit session")
        t = slot_index(slot)
        bars = load_window_bars(store, d, rec["file_sha256"])
        rebuilt = rounded(raw_features(bars[:t], t, rec["prev_1529_close"]))
        sealed = {k: v for k, v in feats["states"][key].items() if k != "set"}
        if rebuilt != sealed:  # request audit: payload == I_t, field by field
            raise RuntimeError(f"request audit failed for {key}: {rebuilt} != {sealed}")
        body = canonical_request(template, sealed)
        planned.append({"state": key, "body": body, "key": cache_key(body)})
    return planned, template, config


def _last_bar_stamp(slot: str) -> str:
    h, m = map(int, slot.split(":"))
    total = h * 60 + m - 1
    return f"{total // 60:02d}:{total % 60:02d}"


def run(store: Path, transport: Transport | None = None) -> dict:
    target = OUT / ARTIFACT_NAME
    if target.exists():
        raise SystemExit(f"{target} exists; S0 is never re-run")
    planned, template, config = prepare(store)
    for p in planned:
        p["state_as_of"] = {"last_bar": f"{p['state'][:10]} {_last_bar_stamp(p['state'][11:])}"}
    if len(planned) != 10 or len({p["key"] for p in planned}) != 10:
        raise RuntimeError("S0 must be exactly 10 distinct requests")
    run_id = "S0-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tid = transport_id(config["transport"])
    already = cached_keys()
    _append(OUT / "ledger.jsonl", {"event": "s0_started", "run_id": run_id, "stage": "S0",
                                   "template": "h15", "model": MODEL, "transport_id": tid,
                                   "planned": [{"state": p["state"], "key": p["key"]} for p in planned],
                                   "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    transport = transport or Transport()
    records = []
    try:
        for p in planned:
            if p["key"] in already:  # §12: a cached key is never re-sent
                records.append({"state": p["state"], "key": p["key"], "cache": "hit_not_sent"})
                continue
            p["state_as_of"]["payload_built_at"] = datetime.now(timezone.utc).isoformat(
                timespec="milliseconds").replace("+00:00", "Z")
            attempts = transport.send_historical(p["body"])
            final = attempts[-1]
            validity = (validate_response(final["raw"].encode("utf-8"), template["question_id"])
                        if final.get("status") == 200 else
                        {"valid": False, "reason": f"no HTTP 200 ({final.get('outcome')} "
                                                  f"{final.get('status')})"})
            rec = {"key": p["key"], "run_id": run_id, "stage": "S0", "state": p["state"],
                   "template": "h15", "question_id": template["question_id"], "model_requested": MODEL,
                   "transport_id": tid, "request_bytes": p["body"].decode("utf-8"),
                   "request_sha256": p["key"], "state_as_of": p["state_as_of"],
                   "attempts": [{k: v for k, v in a.items() if k != "raw"} for a in attempts],
                   "retries": len(attempts) - 1, "response_raw": final.get("raw"),
                   "validity": validity, "cache": "miss_sent", "authoritative": True}
            _append(CACHE, rec)
            records.append(rec)
    finally:
        transport.close()
    return {"run_id": run_id, "transport_id": tid, "records": records}


def summarize(result: dict) -> dict:
    recs = [r for r in result["records"] if r.get("cache") == "miss_sent"]
    valid = [r for r in recs if r["validity"]["valid"]]
    sums = [r["validity"]["probability_sum"] for r in valid]
    return {
        "scheduled": 10, "sent": len(recs), "valid": len(valid), "invalid": len(recs) - len(valid),
        "schema_invalid": sum(1 for r in recs if not r["validity"]["valid"]
                              and r["attempts"][-1].get("status") == 200),
        "transport_failed": sum(1 for r in recs if r["attempts"][-1].get("status") != 200),
        "retries": sum(r["retries"] for r in recs),
        "models": sorted({r["validity"].get("model") for r in recs if r["validity"].get("model")}),
        "probability_sums_within_1e-6": all(abs(s - 1.0) <= SUM_TOLERANCE for s in sums),
        "max_abs_sum_deviation": max((abs(s - 1.0) for s in sums), default=None),
        "request_ids_captured": sum(1 for r in recs if r["attempts"][-1].get("request_id")),
        "timing_note": "historical call: §11 t+15/t+60 timing validity applies to P only",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, required=True)
    ap.add_argument("--audit-only", action="store_true", help="seal checks + request audit; no send")
    args = ap.parse_args()
    if args.audit_only:
        planned, _, _ = prepare(args.store)
        for p in planned:
            print(p["state"], p["key"])
        return
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY is not set")
    result = run(args.store)
    result["summary"] = summarize(result)
    result["built_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    target = OUT / ARTIFACT_NAME
    with open(target, "x", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(result, indent=1, sort_keys=True))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    _append(OUT / "ledger.jsonl", {"event": "s0_completed", "run_id": result["run_id"],
                                   "artifact": ARTIFACT_NAME, "sha256": digest,
                                   "summary": result["summary"], "at": result["built_at"]})
    print(json.dumps(result["summary"], indent=1))
    print(f"{target}  sha256={digest}")


if __name__ == "__main__":
    main()
