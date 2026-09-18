"""JEV-NMS-1 §23 development Jev calls (1,600 ordinary cached requests).

Primary: the 100 D1 sessions x ten §5 slots on the sealed h15 template (1,000).
Secondary: the first 30 D1 sessions in seed order (D2) x ten slots on the h5 and
h30 templates (600). Order: D1 seed order, slots ascending, h15 first, then
h5, then h30 for D2.

Before the ledger entry and any send, every state passes the L1 fence (stage
development: eligible D-eval sessions only) and the request audit (features
rebuilt from the SHA-256-checked store equal the sealed features), and the
F1/A2/A3 seal chain and the step-1/2, L1, L2 and L3 artifacts are verified.

§12: ordinary scored requests never bypass the cache and a cached key is never
re-sent. The run is resumable: `development_started` (all 1,600 planned keys)
is written once; a state whose key is already cached is a cache hit and is not
sent again. Historical calls are after-the-fact (§11); no timing validity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from scripts.jev_nms_1.draws import SLOTS
from scripts.jev_nms_1.eligibility import load_seal
from scripts.jev_nms_1.features import load_window_bars, raw_features, rounded, slot_index
from scripts.jev_nms_1.fence import Fence
from scripts.jev_nms_1.rulings import load_a3
from scripts.jev_nms_1.s0 import CACHE, _append
from scripts.jev_nms_1.transport import (
    MODEL, Transport, cache_key, canonical_request, transport_id, validate_response,
)

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "jev_market_state"
LEDGER = OUT / "ledger.jsonl"
HASHES = {
    "eligibility_step1.json": "b5d1cd48b11667c15a3d744ebea81db7d0a11c7aa03a7e4420e2e9dc98344c77",
    "draws_step2.json": "e4c1f3c957b49ebfcfb0915ff0f5675467a953e58a9b82546a9ba4e007733de8",
    "features_step2.json": "29997617dba1888c4f66ff28da85e4ad42f3866b8b5bcd59d2b43e0404049eb3",
    "l1_step3.json": "502070d8148a73f1c94a63a334e2ce73da3ccd59a200e5d25e4a0838407ca11f",
    "l2_step4.json": "c27b65eba39c76052e5e94271ee33bea60e917d643140eedaa880dfc0143be92",
    "l3_step5.json": "cb67b5551371ce5d85c4085cff004c0a70b557d411654f309605f0a90fc72c35",
}
N_PRIMARY, N_SECONDARY = 1000, 600


def _artifact(name: str) -> dict:
    raw = (OUT / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASHES[name]:
        raise RuntimeError(f"{name} does not match its accepted SHA-256")
    return json.loads(raw.decode("utf-8"))


def _template(config: dict, name: str) -> dict:
    ref = config["templates"][name]
    raw = (REPO / ref["file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise RuntimeError(f"{name} template does not match its sealed SHA-256")
    return json.loads(raw.decode("utf-8"))


def planned_states(draws: dict) -> list[tuple[str, str]]:
    d = draws["draws"]
    out = [("h15", f"{x}|{s}") for x in d["d1_dev"]["output"] for s in SLOTS]
    out += [(h, f"{x}|{s}") for h in ("h5", "h30") for x in d["d2_dev_secondary"]["output"] for s in SLOTS]
    return out


def prepare(store: Path) -> tuple[list[dict], dict, dict]:
    config, _ = load_seal()
    load_a3()
    templates = {n: _template(config, n) for n in ("h5", "h15", "h30")}
    elig, draws, feats, l1, l2, l3 = (_artifact(n) for n in HASHES)
    if not l1["passed"] or l2["decision"].get("result") != "PASS" or l3["summary"]["valid"] != 100:
        raise RuntimeError("an earlier probe did not complete as accepted")
    d = draws["draws"]
    ev = sorted(r["date"] for r in elig["sessions"]["d_eval"] if r["eligible"])
    if not (d["check_d1_otherwise_eligible_equals_eligible_d_eval"] and len(set(d["d1_dev"]["output"])) == 100
            and set(d["d1_dev"]["output"]) <= set(ev) and d["d2_dev_secondary"]["output"] == d["d1_dev"]["output"][:30]):
        raise RuntimeError("D1/D2 draw verification failed")
    fence = Fence(elig, store)
    recs = {r["date"]: r for r in elig["sessions"]["d_eval"]}
    bars, planned = {}, []
    for tpl, key in planned_states(draws):
        fence.check("development", key)
        day, slot = key.split("|")
        if day not in bars:
            bars[day] = load_window_bars(store, day, recs[day]["file_sha256"])
        t = slot_index(slot)
        rebuilt = rounded(raw_features(bars[day][:t], t, recs[day]["prev_1529_close"]))
        sealed = {k: v for k, v in feats["states"][key].items() if k != "set"}
        if rebuilt != sealed or feats["states"][key]["set"] != "d_eval":
            raise RuntimeError(f"request audit failed for {key}")
        body = canonical_request(templates[tpl], sealed)
        planned.append({"template": tpl, "state": key, "body": body, "key": cache_key(body)})
    if len(planned) != N_PRIMARY + N_SECONDARY or len({p["key"] for p in planned}) != len(planned):
        raise RuntimeError("development must be exactly 1,600 distinct requests")
    return planned, templates, config


def _cache() -> dict:
    if not CACHE.exists():
        return {}
    return {r["key"]: r for r in map(json.loads, CACHE.read_text(encoding="utf-8").splitlines())}


def _started() -> dict | None:
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["event"] == "development_started":
            return rec
    return None


def _as_of(state: str) -> dict:
    h, m = map(int, state[11:].split(":"))
    last = h * 60 + m - 1
    return {"last_bar": f"{state[:10]} {last // 60:02d}:{last % 60:02d}",
            "payload_built_at": datetime.now(timezone.utc).isoformat(
                timespec="milliseconds").replace("+00:00", "Z")}


def run(store: Path, transport: Transport | None = None) -> dict:
    planned, templates, config = prepare(store)
    tid = transport_id(config["transport"])
    cache = _cache()
    foreign = [p["key"] for p in planned if p["key"] in cache and cache[p["key"]].get("stage") != "development"]
    if foreign:
        raise RuntimeError(f"{len(foreign)} development keys are cached by another stage")
    started = _started()
    if started is None:
        run_id = "DEV-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _append(LEDGER, {"event": "development_started", "run_id": run_id, "stage": "development",
                         "model": MODEL, "transport_id": tid,
                         "templates": {n: config["templates"][n]["sha256"] for n in templates},
                         "planned": [{"template": p["template"], "state": p["state"], "key": p["key"]}
                                     for p in planned],
                         "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    else:
        run_id = started["run_id"]
        if [x["key"] for x in started["planned"]] != [p["key"] for p in planned]:
            raise RuntimeError("planned keys differ from the development_started ledger entry")
    transport = transport or Transport()
    sent = hits = 0
    try:
        for p in planned:
            if p["key"] in cache:
                hits += 1
                continue
            tpl = templates[p["template"]]
            as_of = _as_of(p["state"])
            attempts = transport.send_historical(p["body"])
            final = attempts[-1]
            validity = (validate_response(final["raw"].encode("utf-8"), tpl["question_id"],
                                          tuple(tpl["question"]["criteria"]))
                        if final.get("status") == 200 else
                        {"valid": False, "reason": f"no HTTP 200 ({final.get('outcome')} {final.get('status')})"})
            rec = {"key": p["key"], "request_sha256": p["key"], "run_id": run_id, "stage": "development",
                   "state": p["state"], "template": p["template"], "question_id": tpl["question_id"],
                   "model_requested": MODEL, "transport_id": tid,
                   "request_bytes": p["body"].decode("utf-8"), "state_as_of": as_of,
                   "attempts": [{k: v for k, v in a.items() if k != "raw"} for a in attempts],
                   "retries": len(attempts) - 1, "response_raw": final.get("raw"),
                   "validity": validity, "cache": "miss_sent", "authoritative": True}
            _append(CACHE, rec)
            cache[p["key"]] = rec
            sent += 1
    finally:
        transport.close()
    return {"run_id": run_id, "sent_this_invocation": sent, "cache_hits_this_invocation": hits,
            "complete": all(p["key"] in cache for p in planned)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, required=True)
    ap.add_argument("--audit-only", action="store_true")
    args = ap.parse_args()
    if args.audit_only:
        planned, _, _ = prepare(args.store)
        print(len(planned), "planned; first", planned[0]["state"], planned[0]["template"], planned[0]["key"])
        return
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY is not set")
    out = run(args.store)
    if out["complete"]:
        cache = _cache()
        planned, _, _ = prepare(args.store)
        recs = [cache[p["key"]] for p in planned]
        _append(LEDGER, {"event": "development_calls_completed", "run_id": out["run_id"],
                         "records": len(recs), "valid": sum(r["validity"]["valid"] for r in recs),
                         "cache_sha256": hashlib.sha256(CACHE.read_bytes()).hexdigest(),
                         "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    print(json.dumps(out))


if __name__ == "__main__":
    main()
