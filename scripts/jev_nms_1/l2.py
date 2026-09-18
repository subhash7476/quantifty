"""JEV-NMS-1 §13 L2 — year-memorization probe.

The 90 preregistered D4/D4t states (30 eligible sessions per calendar year
2023/2024/2025 within D-fit and D-eval, one drawn slot each; A2-1, A2-2) are
each sent once as an ordinary cached request on the sealed `l2_year` template
(Template 4). Every state passes the L1 fence (stage L2) and the request audit
(features rebuilt from the store) before the ledger entry and any send.

Decision rule (§13, config probes): success = Jev's answer equals the state's
true calendar year; one-sided exact binomial test against chance 1/3,
H1: p > 1/3 (scipy.stats.binomtest, alternative="greater"); FAIL if p < 0.01.
"Answer" is evaluated as both the `choice` field and the arg-max probability;
if the two readings differ on any state, or any response is invalid, the rule
needs a ruling and the gate result is withheld.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from scipy.stats import binomtest

from scripts.jev_nms_1.eligibility import load_seal
from scripts.jev_nms_1.features import load_window_bars, raw_features, rounded, slot_index
from scripts.jev_nms_1.fence import Fence
from scripts.jev_nms_1.s0 import CACHE, _append, cached_keys
from scripts.jev_nms_1.transport import (
    MODEL, SUM_TOLERANCE, Transport, cache_key, canonical_request, transport_id,
    validate_response,
)

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "jev_market_state"
ARTIFACT_NAME = "l2_step4.json"
HASHES = {
    "eligibility_step1.json": "b5d1cd48b11667c15a3d744ebea81db7d0a11c7aa03a7e4420e2e9dc98344c77",
    "draws_step2.json": "e4c1f3c957b49ebfcfb0915ff0f5675467a953e58a9b82546a9ba4e007733de8",
    "features_step2.json": "29997617dba1888c4f66ff28da85e4ad42f3866b8b5bcd59d2b43e0404049eb3",
    "l1_step3.json": "502070d8148a73f1c94a63a334e2ce73da3ccd59a200e5d25e4a0838407ca11f",
}


def _artifact(name: str) -> dict:
    raw = (OUT / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASHES[name]:
        raise RuntimeError(f"{name} does not match its accepted SHA-256")
    return json.loads(raw.decode("utf-8"))


def prepare(store: Path) -> tuple[list[dict], dict, dict]:
    config, _ = load_seal()
    ref = config["templates"]["l2_year"]
    raw = (REPO / ref["file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise RuntimeError("l2_year template does not match its sealed SHA-256")
    template = json.loads(raw.decode("utf-8"))
    elig, draws, feats, l1 = (_artifact(n) for n in HASHES)
    if not l1["passed"]:
        raise RuntimeError("L1 did not pass")
    fence = Fence(elig, store)
    recs = {r["date"]: r for n in ("d_fit", "d_eval") for r in elig["sessions"][n]}
    planned = []
    for key in draws["draws"]["d4t_l2_timestamps"]["output"]:
        fence.check("L2", key)
        d, slot = key.split("|")
        rec, t = recs[d], slot_index(slot)
        bars = load_window_bars(store, d, rec["file_sha256"])
        rebuilt = rounded(raw_features(bars[:t], t, rec["prev_1529_close"]))
        sealed = {k: v for k, v in feats["states"][key].items() if k != "set"}
        if rebuilt != sealed:
            raise RuntimeError(f"request audit failed for {key}")
        body = canonical_request(template, sealed)
        planned.append({"state": key, "true_year": d[:4], "body": body, "key": cache_key(body)})
    if len(planned) != 90 or len({p["key"] for p in planned}) != 90:
        raise RuntimeError("L2 must be exactly 90 distinct requests")
    if sorted(p["true_year"] for p in planned) != ["2023"] * 30 + ["2024"] * 30 + ["2025"] * 30:
        raise RuntimeError("L2 sample is not 30 sessions per year")
    return planned, template, config


def run(store: Path, transport: Transport | None = None) -> dict:
    if (OUT / ARTIFACT_NAME).exists():
        raise SystemExit("L2 artifact exists; L2 is never re-run")
    planned, template, config = prepare(store)
    classes = tuple(template["question"]["criteria"])
    run_id = "L2-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tid = transport_id(config["transport"])
    already = cached_keys()
    _append(OUT / "ledger.jsonl", {"event": "l2_started", "run_id": run_id, "stage": "L2",
                                   "template": "l2_year", "model": MODEL, "transport_id": tid,
                                   "planned": [{"state": p["state"], "key": p["key"]} for p in planned],
                                   "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    transport = transport or Transport()
    records = []
    try:
        for p in planned:
            if p["key"] in already:
                raise RuntimeError(f"{p['key']} already cached; a cached key is never re-sent")
            h, m = map(int, p["state"][11:].split(":"))
            as_of = {"last_bar": f"{p['state'][:10]} {(h * 60 + m - 1) // 60:02d}:{(h * 60 + m - 1) % 60:02d}",
                     "payload_built_at": datetime.now(timezone.utc).isoformat(
                         timespec="milliseconds").replace("+00:00", "Z")}
            attempts = transport.send_historical(p["body"])
            final = attempts[-1]
            validity = (validate_response(final["raw"].encode("utf-8"), template["question_id"], classes)
                        if final.get("status") == 200 else
                        {"valid": False, "reason": f"no HTTP 200 ({final.get('outcome')} {final.get('status')})"})
            rec = {"key": p["key"], "run_id": run_id, "stage": "L2", "state": p["state"],
                   "true_year": p["true_year"], "template": "l2_year",
                   "question_id": template["question_id"], "model_requested": MODEL,
                   "transport_id": tid, "request_bytes": p["body"].decode("utf-8"),
                   "request_sha256": p["key"], "state_as_of": as_of,
                   "attempts": [{k: v for k, v in a.items() if k != "raw"} for a in attempts],
                   "retries": len(attempts) - 1, "response_raw": final.get("raw"),
                   "validity": validity, "cache": "miss_sent", "authoritative": True}
            _append(CACHE, rec)
            records.append(rec)
    finally:
        transport.close()
    return {"run_id": run_id, "transport_id": tid, "classes": list(classes), "records": records}


def decide(records: list[dict], chance: float, fail_p: float) -> dict:
    invalid = [r["state"] for r in records if not r["validity"]["valid"]]
    out = {"n_scheduled": 90, "n_sent": len(records), "n_valid": len(records) - len(invalid),
           "invalid_states": invalid, "chance": chance, "fail_if_p_below": fail_p}
    valid = [r for r in records if r["validity"]["valid"]]
    readings = {}
    for name, answer in (("choice", lambda v: v["choice"]),
                         ("argmax", lambda v: max(v["probabilities"], key=v["probabilities"].get))):
        k = sum(answer(r["validity"]) == r["true_year"] for r in valid)
        readings[name] = {"successes": k, "n": len(valid),
                          "p_value": binomtest(k, len(valid), chance, alternative="greater").pvalue}
    ties = [r["state"] for r in valid
            if list(r["validity"]["probabilities"].values()).count(max(r["validity"]["probabilities"].values())) > 1]
    disagree = [r["state"] for r in valid
                if r["validity"]["choice"] != max(r["validity"]["probabilities"],
                                                  key=r["validity"]["probabilities"].get)]
    out.update({"readings": readings, "argmax_ties": ties, "choice_argmax_disagree": disagree,
                "per_year": {y: {"n": sum(r["true_year"] == y for r in valid),
                                 "correct": sum(r["true_year"] == y and r["validity"]["choice"] == y
                                                for r in valid)} for y in ("2023", "2024", "2025")},
                "confusion": {y: {c: sum(r["true_year"] == y and r["validity"]["choice"] == c for r in valid)
                                  for c in ("2023", "2024", "2025")} for y in ("2023", "2024", "2025")}})
    needs_ruling = bool(invalid or ties or disagree)
    out["needs_ruling"] = needs_ruling
    if not needs_ruling:
        p = readings["choice"]["p_value"]
        out.update({"successes": readings["choice"]["successes"], "p_value": p,
                    "result": "FAIL" if p < fail_p else "PASS"})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, required=True)
    ap.add_argument("--audit-only", action="store_true")
    args = ap.parse_args()
    if args.audit_only:
        planned, _, _ = prepare(args.store)
        print(len(planned), "planned; first", planned[0]["state"], planned[0]["key"])
        return
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY is not set")
    config, _ = load_seal()
    result = run(args.store)
    recs = result["records"]
    sums = [r["validity"]["probability_sum"] for r in recs if r["validity"]["valid"]]
    result["summary"] = {
        "scheduled": 90, "sent": len(recs), "valid": sum(r["validity"]["valid"] for r in recs),
        "retries": sum(r["retries"] for r in recs),
        "models": sorted({r["validity"].get("model") for r in recs if r["validity"].get("model")}),
        "probability_sums_within_1e-6": all(abs(s - 1.0) <= SUM_TOLERANCE for s in sums),
        "max_abs_sum_deviation": max((abs(s - 1.0) for s in sums), default=None),
        "request_ids_captured": sum(1 for r in recs if r["attempts"][-1].get("request_id"))}
    result["decision"] = decide(recs, config["probes"]["l2_chance"], config["probes"]["l2_fail_p"])
    result["built_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    target = OUT / ARTIFACT_NAME
    with open(target, "x", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(result, indent=1, sort_keys=True))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    d = result["decision"]
    _append(OUT / "ledger.jsonl", {"event": "l2_completed", "run_id": result["run_id"],
                                   "artifact": ARTIFACT_NAME, "sha256": digest,
                                   "result": d.get("result", "NEEDS_RULING"),
                                   "successes": d.get("successes"), "p_value": d.get("p_value"),
                                   "at": result["built_at"]})
    print(json.dumps({"summary": result["summary"], "decision": d}, indent=1))
    print(f"{target}  sha256={digest}")


if __name__ == "__main__":
    main()
