"""JEV-NMS-1 §13 L3 — repeatability probe and canary baseline.

The 50 preregistered D5 states (A2-1: all eligible D-fit and D-eval states,
excluding every S0, L2/D4t and development state; random.sample(pop, 50)) are
each sent twice on the sealed h15 template (A2-4). Every state passes the L1
fence (stage L3) and the request audit before the ledger entry and any send.

Replicates (§12, A2-4): replicate 0 is the authoritative, ordinary cache
record keyed by the canonical request hash. Replicate 1 is the deliberate,
non-authoritative cache-bypass record keyed by
`canonical_request_hash + run_id + replicate_index`. Send order (not fixed by
the protocol; disclosed): all 50 replicate-0 requests in seed order, then all
50 replicate-1 requests in seed order.

§13 prescribes reporting only: argmax agreement and maximum absolute
probability difference; "L3 agreement is the canary baseline". The halt rule
belongs to L5 (at P) and has no L3 counterpart, so none is evaluated here.
Both the 50-state agreement and the D6 (first 20) canary-subset agreement are
recorded. If any response is invalid or any argmax ties, the figures are still
recorded but flagged for a ruling.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from scripts.jev_nms_1.draws import SLOTS, population_hash
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
ARTIFACT_NAME = "l3_step5.json"
HASHES = {
    "eligibility_step1.json": "b5d1cd48b11667c15a3d744ebea81db7d0a11c7aa03a7e4420e2e9dc98344c77",
    "draws_step2.json": "e4c1f3c957b49ebfcfb0915ff0f5675467a953e58a9b82546a9ba4e007733de8",
    "features_step2.json": "29997617dba1888c4f66ff28da85e4ad42f3866b8b5bcd59d2b43e0404049eb3",
    "l1_step3.json": "502070d8148a73f1c94a63a334e2ce73da3ccd59a200e5d25e4a0838407ca11f",
    "l2_step4.json": "c27b65eba39c76052e5e94271ee33bea60e917d643140eedaa880dfc0143be92",
}
N_STATES, N_CANARY = 50, 20


def _artifact(name: str) -> dict:
    raw = (OUT / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASHES[name]:
        raise RuntimeError(f"{name} does not match its accepted SHA-256")
    return json.loads(raw.decode("utf-8"))


def record_id(key: str, run_id: str, replicate: int) -> str:
    return key if replicate == 0 else f"{key}+{run_id}+{replicate}"


def verify_pool(elig: dict, draws: dict) -> dict:
    """Check the frozen D5 manifest against its A2-1 population; never redraws."""
    d = draws["draws"]
    pool_dates = sorted(r["date"] for n in ("d_fit", "d_eval") for r in elig["sessions"][n] if r["eligible"])
    all_states = [f"{x}|{s}" for x in pool_dates for s in SLOTS]
    s0 = set(d["d3_s0"]["states"])
    l2 = set(d["d4t_l2_timestamps"]["output"])
    dev = {f"{x}|{s}" for x in d["d1_dev"]["output"] for s in SLOTS}
    excluded = s0 | l2 | dev
    pop = [st for st in all_states if st not in excluded]
    m = d["d5_l3"]
    out = m["output"]
    checks = {
        "all_states": len(all_states), "s0": len(s0), "l2": len(l2), "dev": len(dev),
        "s0_and_l2": len(s0 & l2), "s0_and_dev": len(s0 & dev), "l2_and_dev": len(l2 & dev),
        "excluded": len(excluded), "population": len(pop),
        "population_sha256_matches": population_hash(pop) == m["population_sha256"],
        "manifest_counts_match": (len(all_states), len(excluded), len(pop))
        == (m["all_states_before_exclusion"], m["excluded_states"], m["population_size"]),
        "output_distinct_50": len(set(out)) == N_STATES == len(out),
        "output_in_population": set(out) <= set(pop),
        "output_disjoint_s0_l2_dev": not (set(out) & excluded),
        "d6_is_first_20": d["d6_canaries"]["output"] == out[:N_CANARY],
    }
    if not all(v for k, v in checks.items() if isinstance(v, bool)):
        raise RuntimeError(f"D5 pool verification failed: {checks}")
    return checks


def prepare(store: Path) -> tuple[list[dict], dict, dict, dict]:
    config, _ = load_seal()
    ref = config["templates"]["h15"]
    raw = (REPO / ref["file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise RuntimeError("h15 template does not match its sealed SHA-256")
    template = json.loads(raw.decode("utf-8"))
    elig, draws, feats, l1, l2 = (_artifact(n) for n in HASHES)
    if not l1["passed"]:
        raise RuntimeError("L1 did not pass")
    if l2["decision"].get("result") != "PASS":
        raise RuntimeError("L2 did not pass")
    pool = verify_pool(elig, draws)
    fence = Fence(elig, store)
    recs = {r["date"]: r for n in ("d_fit", "d_eval") for r in elig["sessions"][n]}
    planned = []
    for key in draws["draws"]["d5_l3"]["output"]:
        fence.check("L3", key)
        d, slot = key.split("|")
        rec, t = recs[d], slot_index(slot)
        bars = load_window_bars(store, d, rec["file_sha256"])
        rebuilt = rounded(raw_features(bars[:t], t, rec["prev_1529_close"]))
        sealed = {k: v for k, v in feats["states"][key].items() if k != "set"}
        if rebuilt != sealed:
            raise RuntimeError(f"request audit failed for {key}")
        body = canonical_request(template, sealed)
        planned.append({"state": key, "body": body, "key": cache_key(body)})
    if len(planned) != N_STATES or len({p["key"] for p in planned}) != N_STATES:
        raise RuntimeError("L3 must be exactly 50 distinct requests")
    return planned, template, config, pool


def _as_of(state: str) -> dict:
    h, m = map(int, state[11:].split(":"))
    last = h * 60 + m - 1
    return {"last_bar": f"{state[:10]} {last // 60:02d}:{last % 60:02d}",
            "payload_built_at": datetime.now(timezone.utc).isoformat(
                timespec="milliseconds").replace("+00:00", "Z")}


def run(store: Path, transport: Transport | None = None) -> dict:
    if (OUT / ARTIFACT_NAME).exists():
        raise SystemExit("L3 artifact exists; L3 is never re-run")
    planned, template, config, pool = prepare(store)
    classes = tuple(template["question"]["criteria"])
    run_id = "L3-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tid = transport_id(config["transport"])
    already = cached_keys()
    ids = [(r, p, record_id(p["key"], run_id, r)) for r in (0, 1) for p in planned]
    clash = [rid for _, _, rid in ids if rid in already]
    if clash:
        raise RuntimeError(f"{len(clash)} L3 record ids already cached; a cached key is never re-sent")
    _append(OUT / "ledger.jsonl", {"event": "l3_started", "run_id": run_id, "stage": "L3",
                                   "template": "h15", "model": MODEL, "transport_id": tid,
                                   "send_order": "all replicate 0 in seed order, then all replicate 1",
                                   "planned": [{"state": p["state"], "replicate": r, "record_id": rid}
                                               for r, p, rid in ids],
                                   "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    transport = transport or Transport()
    records = []
    try:
        for r, p, rid in ids:
            as_of = _as_of(p["state"])
            attempts = transport.send_historical(p["body"])
            final = attempts[-1]
            validity = (validate_response(final["raw"].encode("utf-8"), template["question_id"], classes)
                        if final.get("status") == 200 else
                        {"valid": False, "reason": f"no HTTP 200 ({final.get('outcome')} {final.get('status')})"})
            rec = {"key": rid, "request_sha256": p["key"], "run_id": run_id, "replicate": r,
                   "stage": "L3", "state": p["state"], "template": "h15",
                   "question_id": template["question_id"], "model_requested": MODEL,
                   "transport_id": tid, "request_bytes": p["body"].decode("utf-8"),
                   "state_as_of": as_of,
                   "attempts": [{k: v for k, v in a.items() if k != "raw"} for a in attempts],
                   "retries": len(attempts) - 1, "response_raw": final.get("raw"),
                   "validity": validity, "cache": "miss_sent" if r == 0 else "bypass",
                   "authoritative": r == 0}
            _append(CACHE, rec)
            records.append(rec)
    finally:
        transport.close()
    return {"run_id": run_id, "transport_id": tid, "classes": list(classes), "pool": pool,
            "records": records}


def _argmax(probs: dict) -> str:
    return max(probs, key=probs.get)


def _is_tie(probs: dict) -> bool:
    return list(probs.values()).count(max(probs.values())) > 1


def decide(records: list[dict]) -> dict:
    """§13 L3 figures. Report only: there is no L3 pass/fail threshold."""
    by = {(r["state"], r["replicate"]): r for r in records}
    states = list(dict.fromkeys(r["state"] for r in records if r["replicate"] == 0))
    invalid = [f"{s}#{k}" for (s, k), r in by.items() if not r["validity"]["valid"]]
    pairs = []
    for s in states:
        v0, v1 = by[(s, 0)]["validity"], by[(s, 1)]["validity"]
        if not (v0["valid"] and v1["valid"]):
            continue
        p0, p1 = v0["probabilities"], v1["probabilities"]
        pairs.append({"state": s, "argmax_0": _argmax(p0), "argmax_1": _argmax(p1),
                      "choice_0": v0["choice"], "choice_1": v1["choice"],
                      "agree": _argmax(p0) == _argmax(p1),
                      "max_abs_diff": max(abs(p0[c] - p1[c]) for c in p0),
                      "tie": _is_tie(p0) or _is_tie(p1)})

    def summary(sub: list[dict]) -> dict:
        n = len(sub)
        k = sum(p["agree"] for p in sub)
        return {"n_pairs": n, "argmax_agreements": k, "argmax_agreement": k / n if n else None,
                "max_abs_probability_difference": max((p["max_abs_diff"] for p in sub), default=None)}

    canary_states = states[:N_CANARY]
    ties = [p["state"] for p in pairs if p["tie"]]
    choice_argmax_disagree = [f"{s}#{k}" for (s, k), r in by.items() if r["validity"]["valid"]
                              and r["validity"]["choice"] != _argmax(r["validity"]["probabilities"])]
    return {
        "n_states": len(states), "n_sent": len(records),
        "n_valid": len(records) - len(invalid), "invalid": invalid,
        "all_50": summary(pairs),
        "canary_d6_first_20": summary([p for p in pairs if p["state"] in canary_states]),
        "canary_baseline_rep0": [{"state": s, "argmax": _argmax(by[(s, 0)]["validity"]["probabilities"]),
                                  "probabilities": by[(s, 0)]["validity"]["probabilities"],
                                  "record_id": by[(s, 0)]["key"]}
                                 for s in canary_states if by[(s, 0)]["validity"]["valid"]],
        "pairs": pairs, "argmax_ties": ties, "choice_argmax_disagree": choice_argmax_disagree,
        "needs_ruling": bool(invalid or ties),
        "halt_rule": "none at L3: the §13 halt rule is L5's, evaluated at P against this baseline",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, required=True)
    ap.add_argument("--audit-only", action="store_true")
    args = ap.parse_args()
    if args.audit_only:
        planned, _, _, pool = prepare(args.store)
        print(len(planned), "planned; first", planned[0]["state"], planned[0]["key"])
        print(json.dumps(pool, indent=1))
        return
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY is not set")
    result = run(args.store)
    recs = result["records"]
    sums = [r["validity"]["probability_sum"] for r in recs if r["validity"]["valid"]]
    result["summary"] = {
        "scheduled": 2 * N_STATES, "sent": len(recs), "valid": sum(r["validity"]["valid"] for r in recs),
        "retries": sum(r["retries"] for r in recs),
        "models": sorted({r["validity"].get("model") for r in recs if r["validity"].get("model")}),
        "probability_sums_within_1e-6": all(abs(s - 1.0) <= SUM_TOLERANCE for s in sums),
        "max_abs_sum_deviation": max((abs(s - 1.0) for s in sums), default=None),
        "request_ids_captured": sum(1 for r in recs if r["attempts"][-1].get("request_id")),
        "request_ids_distinct": len({r["attempts"][-1].get("request_id") for r in recs})}
    result["decision"] = decide(recs)
    result["built_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    target = OUT / ARTIFACT_NAME
    with open(target, "x", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(result, indent=1, sort_keys=True))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    d = result["decision"]
    _append(OUT / "ledger.jsonl", {"event": "l3_completed", "run_id": result["run_id"],
                                   "artifact": ARTIFACT_NAME, "sha256": digest,
                                   "n_valid": d["n_valid"], "needs_ruling": d["needs_ruling"],
                                   "agreement_50": d["all_50"]["argmax_agreement"],
                                   "agreement_canary_20": d["canary_d6_first_20"]["argmax_agreement"],
                                   "max_abs_diff_50": d["all_50"]["max_abs_probability_difference"],
                                   "at": result["built_at"]})
    print(json.dumps({"summary": result["summary"],
                      "decision": {k: v for k, v in d.items() if k not in ("pairs", "canary_baseline_rep0")}},
                     indent=1))
    print(f"{target}  sha256={digest}")


if __name__ == "__main__":
    main()
