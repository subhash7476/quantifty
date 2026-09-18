"""JEV-NMS-1 §13 L1 — structural probe (§7 required tests + fence/store guards).

No Jev call is made: §13 defines L1 as structural tests and §23 budgets no L1
calls. Checks, over every eligible D-fit and D-eval state:

1. input/label disjointness - features are unchanged when every bar stamped
   >= t is poisoned; forward label statistics are unchanged when every bar
   stamped <= t-2 is poisoned (the label reads P(t) = C_{t-1} and bars
   t..t+h-1 only); the input bar set [0, t-1] and label window [t, t+h-1]
   are disjoint.
2. isolation - a directory containing only D and previous_session(D)
   reproduces every state exactly (C_prev read from D-1's 15:29 bar there).
3. request audit - every preregistered payload (S0, L2, L3, development
   incl. secondary horizons) is rebuilt and checked field by field against
   the isolated I_t recomputation, against the sealed template (hash and
   question object), for key order, model literal and fixed-decimal literals;
   the already-sent S0 bytes must be byte-identical.
4. fence and store guards - every planned state passes its stage's fence;
   preregistered out-of-set, H-exposed, buffer and beyond-store probes are
   refused.

Any failure means L1 failed (§26: INVALID); the artifact records it and the
run stops. Artifact create-only; ledger entries before and after.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

from scripts.jev_nms_1.dfit import window_stats
from scripts.jev_nms_1.eligibility import load_seal
from scripts.jev_nms_1.features import FIELDS, SLOTS, load_window_bars, raw_features, rounded, slot_index
from scripts.jev_nms_1.fence import Fence, FenceViolation
from scripts.jev_nms_1.transport import MODEL, _literal, canonical_request
from core.market.trading_calendar import previous_session

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "jev_market_state"
ARTIFACT_NAME = "l1_step3.json"
HASHES = {
    "eligibility_step1.json": "b5d1cd48b11667c15a3d744ebea81db7d0a11c7aa03a7e4420e2e9dc98344c77",
    "draws_step2.json": "e4c1f3c957b49ebfcfb0915ff0f5675467a953e58a9b82546a9ba4e007733de8",
    "dfit_constants_step2.json": "656ed4ddf3ee19d264c2dc8183844f329881bf14ca2e77c7dfb87e6d8bafe88d",
    "features_step2.json": "29997617dba1888c4f66ff28da85e4ad42f3866b8b5bcd59d2b43e0404049eb3",
    "s0_step3.json": "53113e5c0dc8805785963b01386e2b1c0628561a329ddba54480e35ae28cd308",
}
NEGATIVE_PROBES = [  # (stage, state) that the fence/store guard must refuse
    ("S0", "2023-02-28|10:00"),   # before D-fit, outside every set
    ("S0", "2023-03-01|10:00"),   # D-fit but ineligible (no Nifty bars)
    ("S0", "2025-06-02|10:00"),   # eligible, but D-eval is not S0's active set
    ("development", "2024-06-03|10:00"),  # D-fit is not development's active set
    ("L2", "2024-03-04|10:00"),   # ineligible (item 8)
    ("L3", "2026-01-05|10:00"),   # H-exposed: no Jev calls
    ("development", "2026-09-18|10:00"),  # H-exposed last session; file absent
    ("L2", "2026-09-21|10:00"),   # buffer date (> F1)
    ("P", "2025-06-02|10:00"),    # P has no active set before F2
    ("L3", "2027-01-04|10:00"),   # beyond the store
]


def _artifact(name: str) -> dict:
    raw = (OUT / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASHES[name]:
        raise RuntimeError(f"{name} does not match its accepted SHA-256")
    return json.loads(raw.decode("utf-8"))


def _prev_close_from_file(path: Path, d: str) -> float | None:
    con = duckdb.connect(str(path), read_only=True)
    try:
        rows = con.execute("SELECT close FROM candles WHERE symbol = 'NSE_INDEX|Nifty 50' AND "
                           "timestamp = ?", [f"{d} 15:29:00"]).fetchall()
    finally:
        con.close()
    return rows[0][0] if len(rows) == 1 else None


def _templates(config: dict) -> dict:
    out = {}
    for name, ref in config["templates"].items():
        raw = (REPO / ref["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
            raise RuntimeError(f"template {name} does not match its sealed SHA-256")
        out[name] = json.loads(raw.decode("utf-8"))
    return out


def isolation_and_disjointness(store: Path, elig: dict, feats: dict, dfit: dict) -> tuple[dict, dict]:
    """Returns (isolated I_t features per state, check results)."""
    labels = {(r["date"], r["slot"], h): r for h, rows in dfit["states"].items() for r in rows}
    isolated, fails = {}, {"isolation": [], "features_disjoint": [], "labels_disjoint": []}
    n_label_checks = 0
    for name in ("d_fit", "d_eval"):
        for rec in elig["sessions"][name]:
            if not rec["eligible"]:
                continue
            d, prev = rec["date"], previous_session(date.fromisoformat(rec["date"])).isoformat()
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                shutil.copy2(store / f"{d}.duckdb", tmp / f"{d}.duckdb")
                shutil.copy2(store / f"{prev}.duckdb", tmp / f"{prev}.duckdb")
                if sorted(p.name for p in tmp.iterdir()) != sorted([f"{d}.duckdb", f"{prev}.duckdb"]):
                    raise RuntimeError("isolation directory is not exactly {D, D-1}")
                if hashlib.sha256((tmp / f"{prev}.duckdb").read_bytes()).hexdigest() != rec["prev_file_sha256"]:
                    raise RuntimeError(f"{prev} changed since step 1")
                bars = load_window_bars(tmp, d, rec["file_sha256"])
                c_prev = _prev_close_from_file(tmp / f"{prev}.duckdb", prev)
            for s in SLOTS:
                key, t = f"{d}|{s}", slot_index(s)
                got = rounded(raw_features(bars[:t], t, c_prev))
                isolated[key] = got
                if got != {k: v for k, v in feats["states"][key].items() if k != "set"}:
                    fails["isolation"].append(key)
                poisoned = bars[:t] + [(math.nan,) * 4] * (345 - t)
                if rounded(raw_features(poisoned, t, c_prev)) != got:
                    fails["features_disjoint"].append(key)
                if name == "d_fit":
                    closes = [b[3] for b in bars]
                    early = [math.nan] * (t - 1) + closes[t - 1:]
                    for h in (5, 15, 30):
                        n_label_checks += 1
                        stored = labels[(d, s, str(h))]
                        again = window_stats(early, t, t + h - 1)
                        inputs, window = set(range(0, t)), set(range(t, t + h))
                        if (again != (stored["R"], stored["ER_f"], stored["RV_f"])
                                or inputs & window):
                            fails["labels_disjoint"].append(f"{key}|h{h}")
    return isolated, {"states": len(isolated), "label_checks": n_label_checks, "failures": fails}


def planned_requests(draws: dict) -> list[tuple[str, str, str]]:
    """(stage, template, state) for every preregistered Jev payload."""
    d = draws["draws"]
    out = [("S0", "h15", s) for s in d["d3_s0"]["states"]]
    out += [("L2", "l2_year", s) for s in d["d4t_l2_timestamps"]["output"]]
    out += [("L3", "h15", s) for s in d["d5_l3"]["output"]]
    dev = [f"{x}|{s}" for x in d["d1_dev"]["output"] for s in SLOTS]
    sec = [f"{x}|{s}" for x in d["d2_dev_secondary"]["output"] for s in SLOTS]
    out += [("development", "h15", s) for s in dev]
    out += [("development", tpl, s) for tpl in ("h5", "h30") for s in sec]
    return out


def request_audit(planned, templates, isolated, feats, s0) -> dict:
    fails, sent = [], {r["state"]: r for r in s0["records"]}
    for stage, tpl_name, key in planned:
        tpl = templates[tpl_name]
        state = isolated[key]
        body = canonical_request(tpl, state)
        pairs = json.loads(body, object_pairs_hook=lambda p: p, parse_float=str, parse_int=str)
        top = [k for k, _ in pairs]
        st, qs = dict(pairs)["state"], dict(pairs)["questions"]
        problems = []
        if top != ["model", "state", "questions"] or dict(pairs)["model"] != MODEL:
            problems.append("top-level order or model")
        if [k for k, _ in st] != list(tpl["state_field_order"]) or list(tpl["state_field_order"]) != list(FIELDS):
            problems.append("state field order")
        if any(v != _literal(k, state[k]) for k, v in st):
            problems.append("state literal differs from I_t")
        if state != {k: v for k, v in feats["states"][key].items() if k != "set"}:
            problems.append("I_t differs from sealed features")
        if len(qs) != 1 or qs[0][0] != tpl["question_id"]:
            problems.append("question id")
        q = json.loads(body)["questions"][tpl["question_id"]]
        if q != tpl["question"] or list(q) != ["type", "instructions", "criteria"] \
                or list(q["criteria"]) != list(tpl["question"]["criteria"]):
            problems.append("question object differs from the sealed template")
        if stage == "S0" and sent[key]["request_bytes"].encode("utf-8") != body:
            problems.append("S0 sent bytes differ")
        if problems:
            fails.append({"stage": stage, "template": tpl_name, "state": key, "problems": problems})
    return {"payloads": len(planned),
            "by_stage": {s: sum(1 for p in planned if p[0] == s) for s in ("S0", "L2", "L3", "development")},
            "distinct_payload_bytes": len({(t, k) for _, t, k in planned}), "failures": fails}


def fence_checks(fence: Fence, planned) -> dict:
    pos_fail = []
    for stage, _, key in planned:
        try:
            fence.check(stage, key)
        except FenceViolation as exc:
            pos_fail.append({"stage": stage, "state": key, "error": str(exc)})
    neg = []
    for stage, key in NEGATIVE_PROBES:
        try:
            fence.check(stage, key)
            neg.append({"stage": stage, "state": key, "refused": False})
        except FenceViolation as exc:
            neg.append({"stage": stage, "state": key, "refused": True, "reason": str(exc)})
    return {"planned_passed": len(planned) - len(pos_fail), "planned_refused": pos_fail,
            "negative_probes": neg, "negative_not_refused": [n for n in neg if not n["refused"]]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, required=True)
    args = ap.parse_args()
    target = OUT / ARTIFACT_NAME
    if target.exists():
        raise SystemExit(f"{target} exists; L1 is never re-run")
    config, _ = load_seal()
    templates = _templates(config)
    elig, draws, dfit, feats, s0 = (_artifact(n) for n in HASHES)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(OUT / "ledger.jsonl", "a", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"event": "l1_started", "at": started, "jev_calls": 0}) + "\n")
    isolated, iso = isolation_and_disjointness(args.store, elig, feats, dfit)
    planned = planned_requests(draws)
    audit = request_audit(planned, templates, isolated, feats, s0)
    fences = fence_checks(Fence(elig, args.store), planned)
    passed = (not any(iso["failures"].values()) and not audit["failures"]
              and not fences["planned_refused"] and not fences["negative_not_refused"])
    art = {"protocol_id": "JEV-NMS-1", "stage": "L1", "jev_calls": 0,
           "inputs": HASHES, "templates": {k: v["sha256"] for k, v in config["templates"].items()},
           "isolation_and_disjointness": iso, "request_audit": audit, "fence": fences,
           "passed": passed, "started_at": started,
           "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    with open(target, "x", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(art, indent=1, sort_keys=True))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with open(OUT / "ledger.jsonl", "a", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"event": "l1_completed", "at": art["built_at"], "passed": passed,
                             "jev_calls": 0, "artifact": ARTIFACT_NAME, "sha256": digest}) + "\n")
    print(json.dumps({"passed": passed, "states": iso["states"], "label_checks": iso["label_checks"],
                      "iso_failures": {k: len(v) for k, v in iso["failures"].items()},
                      "payloads": audit["payloads"], "by_stage": audit["by_stage"],
                      "audit_failures": len(audit["failures"]),
                      "fence_planned_passed": fences["planned_passed"],
                      "fence_negatives_refused": sum(n["refused"] for n in fences["negative_probes"])},
                     indent=1))
    print(f"{target}  sha256={digest}")


if __name__ == "__main__":
    main()
