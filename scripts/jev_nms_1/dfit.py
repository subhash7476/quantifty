"""JEV-NMS-1 §28 step 2 (D-fit constants) — §9 scales, §8 thresholds and labels,
the h = 15 base-rate gate, the §4 R-1 report, and the B0/B1 baselines (§14).

Everything here is computed from raw 1m closes of ELIGIBLE D-fit sessions only;
no rounded §6 feature is used. Returns are natural logs (scale-free for z, v
and ER_f). Every quantile/median is numpy.quantile(method="linear") (A2-5).
Each store file is read read-only and must match the SHA-256 the accepted
step-1 artifact recorded for it.

If the base-rate gate fails, the constants are persisted with the failing gate
and B0/B1 are NOT fitted (§8, §24 rule 1).
"""
from __future__ import annotations

import os

if os.environ.get("OMP_NUM_THREADS") != "1":
    raise SystemExit("OMP_NUM_THREADS=1 must be set in the environment before launch (§14)")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

import duckdb  # noqa: E402
import numpy as np  # noqa: E402

from scripts.jev_nms_1.draws import ELIGIBILITY_SHA256, SLOTS, load_eligibility  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "jev_market_state"
DRAWS_SHA256 = "e4c1f3c957b49ebfcfb0915ff0f5675467a953e58a9b82546a9ba4e007733de8"
ARTIFACT_NAME = "dfit_constants_step2.json"
SYMBOL = "NSE_INDEX|Nifty 50"
HORIZONS = (5, 15, 30)
CLASSES = ("trending_up", "trending_down", "range_bound", "disorderly")
BASE_RATE_FLOOR = 0.05
QUANTILE = {"E_star": 0.5, "Z_star": 0.7, "V_star": 0.75}


def slot_index(slot: str) -> int:
    h, m = map(int, slot.split(":"))
    return (h - 9) * 60 + m - 15


def load_closes(store: Path, d: str, expected_sha: str) -> list[float]:
    """Closes of the 345 bars stamped 09:15..14:59, chronological (index 0 = 09:15)."""
    path = store / f"{d}.duckdb"
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        raise RuntimeError(f"{path} changed since the step-1 eligibility artifact")
    con = duckdb.connect(str(path), read_only=True)
    try:
        rows = con.execute(
            "SELECT timestamp, close FROM candles WHERE symbol = ? AND "
            "strftime(timestamp, '%H:%M') BETWEEN '09:15' AND '14:59' ORDER BY timestamp",
            [SYMBOL]).fetchall()
    finally:
        con.close()
    if len(rows) != 345:
        raise RuntimeError(f"{d}: expected 345 window bars, got {len(rows)}")
    return [r[1] for r in rows]


def window_stats(closes: list[float], first: int, last: int) -> tuple[float, float, float]:
    """(R, ER, RV) over the returns of bars first..last; R = ln(C_last / C_{first-1})."""
    rets = [math.log(closes[j] / closes[j - 1]) for j in range(first, last + 1)]
    r = math.log(closes[last] / closes[first - 1])
    denom = sum(abs(x) for x in rets)
    er = abs(r) / denom if denom != 0 else 0.0
    rv = math.sqrt(sum(x * x for x in rets))
    return r, er, rv


def state_windows(closes: list[float], slot: str, h: int) -> dict:
    t = slot_index(slot)
    fwd = window_stats(closes, t, t + h - 1)          # bars t .. t+h-1
    trail = window_stats(closes, t - h, t - 1)         # bars t-h .. t-1
    return {"fwd": fwd, "trail": trail}


def q(values, p: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=np.float64), p, method="linear"))


def classify(r: float, er: float, z: float, v: float, c: dict) -> str:
    if v >= c["V_star"] and er < c["E_star"]:
        return "disorderly"
    if abs(z) >= c["Z_star"] and er >= c["E_star"]:
        return "trending_up" if r > 0 else "trending_down"
    return "range_bound"


def laplace(counts: dict) -> dict:
    n = sum(counts.values())
    return {k: (counts[k] + 1) / (n + len(CLASSES)) for k in CLASSES}


def build(store: Path) -> dict:
    elig = load_eligibility()
    if hashlib.sha256((OUT / "draws_step2.json").read_bytes()).hexdigest() != DRAWS_SHA256:
        raise RuntimeError("draws_step2.json does not match its recorded SHA-256")
    sessions = [r for r in elig["sessions"]["d_fit"] if r["eligible"]]
    raw = {}
    for rec in sessions:
        closes = load_closes(store, rec["date"], rec["file_sha256"])
        raw[rec["date"]] = {(s, h): state_windows(closes, s, h) for s in SLOTS for h in HORIZONS}
    dates = sorted(raw)

    scales = {h: {s: q([raw[d][(s, h)]["fwd"][2] for d in dates], 0.5) for s in SLOTS}
              for h in HORIZONS}
    trail_scales = {h: {s: q([raw[d][(s, h)]["trail"][2] for d in dates], 0.5) for s in SLOTS}
                    for h in HORIZONS}

    thresholds, states, base_rates = {}, {}, {}
    for h in HORIZONS:
        er = [raw[d][(s, h)]["fwd"][1] for d in dates for s in SLOTS]
        az = [abs(raw[d][(s, h)]["fwd"][0] / scales[h][s]) for d in dates for s in SLOTS]
        v = [raw[d][(s, h)]["fwd"][2] / scales[h][s] for d in dates for s in SLOTS]
        c = {"E_star": q(er, QUANTILE["E_star"]), "Z_star": q(az, QUANTILE["Z_star"]),
             "V_star": q(v, QUANTILE["V_star"])}
        thresholds[h] = c
        rows = []
        for d in dates:
            for s in SLOTS:
                r, e, rv = raw[d][(s, h)]["fwd"]
                tr, te, trv = raw[d][(s, h)]["trail"]
                rows.append({
                    "date": d, "slot": s, "R": r, "ER_f": e, "RV_f": rv,
                    "z": r / scales[h][s], "v": rv / scales[h][s],
                    "label": classify(r, e, r / scales[h][s], rv / scales[h][s], c),
                    "trailing_label": classify(tr, te, tr / trail_scales[h][s],
                                               trv / trail_scales[h][s], c)})
        states[h] = rows
        n = len(rows)
        base_rates[h] = {k: sum(x["label"] == k for x in rows) / n for k in CLASSES}

    gate_rates = base_rates[15]
    gate = {"horizon": 15, "floor": BASE_RATE_FLOOR, "base_rates": gate_rates,
            "passed": all(p >= BASE_RATE_FLOOR for p in gate_rates.values())}

    out = {
        "protocol_id": "JEV-NMS-1",
        "step": "section 28 step 2 - D-fit scales, thresholds, labels, base-rate gate, R-1, B0/B1",
        "eligibility_sha256": ELIGIBILITY_SHA256,
        "draws_sha256": DRAWS_SHA256,
        "quantile": "numpy.quantile(method='linear'), numpy " + np.__version__,
        "units": "natural-log returns (bp = x 1e4)",
        "d_fit_eligible_sessions": len(dates),
        "scales_forward": {str(h): v for h, v in scales.items()},
        "scales_trailing": {str(h): v for h, v in trail_scales.items()},
        "thresholds": {str(h): v for h, v in thresholds.items()},
        "base_rates": {str(h): v for h, v in base_rates.items()},
        "base_rate_gate": gate,
        "r1_report": r1_report(elig),
        "states": {str(h): v for h, v in states.items()},
    }
    if gate["passed"]:
        out["B0"] = {str(h): fit_b0(states[h]) for h in HORIZONS}
        out["B1"] = {str(h): fit_b1(states[h]) for h in HORIZONS}
    return out


def fit_b0(rows: list[dict]) -> dict:
    return {s: laplace({k: sum(1 for x in rows if x["slot"] == s and x["label"] == k)
                        for k in CLASSES}) for s in SLOTS}


def fit_b1(rows: list[dict]) -> dict:
    return {s: {tl: laplace({k: sum(1 for x in rows if x["slot"] == s and x["trailing_label"] == tl
                                    and x["label"] == k) for k in CLASSES})
                for tl in CLASSES} for s in SLOTS}


def r1_report(elig: dict) -> dict:
    """§4 R-1 statistics per set (item 7 materiality), from the step-1 artifact."""
    draws = json.loads((OUT / "draws_step2.json").read_text(encoding="utf-8"))["draws"]
    dev = set(draws["d1_dev"]["output"])
    report = {}
    for name in ("d_fit", "d_eval"):
        recs = elig["sessions"][name]
        oe = [r for r in recs if r["otherwise_eligible"]]
        ex7 = [r for r in oe if not r["items"]["7"]]
        report[name] = {
            "otherwise_eligible": len(oe), "item7_excluded": len(ex7),
            "item7_excluded_pct": 100.0 * len(ex7) / len(oe),
            "excluded": [{"date": r["date"], **(r["item7_longest_run"] or {})} for r in ex7],
            "overlap_with_dev_sample": sorted(r["date"] for r in ex7 if r["date"] in dev)}
    report["stop"] = any(v["item7_excluded_pct"] > 2.0 or v["overlap_with_dev_sample"]
                         for v in report.values())
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    target = OUT / ARTIFACT_NAME
    if target.exists():
        raise SystemExit(f"{target} exists; D-fit constants are never refit")
    art = build(args.store)
    art["omp_num_threads"] = os.environ["OMP_NUM_THREADS"]
    art["built_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(json.dumps({k: art[k] for k in ("thresholds", "base_rates", "base_rate_gate")}, indent=1))
    print("R-1:", json.dumps(art["r1_report"]))
    if args.dry_run:
        return
    with open(target, "x", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(art, indent=1, sort_keys=True))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with open(OUT / "ledger.jsonl", "a", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"event": "r1_report", "at": art["built_at"],
                             "stop": art["r1_report"]["stop"], "artifact": ARTIFACT_NAME}) + "\n")
        fh.write(json.dumps({"event": "dfit_constants", "at": art["built_at"],
                             "base_rate_gate_passed": art["base_rate_gate"]["passed"],
                             "artifact": ARTIFACT_NAME, "sha256": digest}) + "\n")
    print(f"{target}  sha256={digest}")


if __name__ == "__main__":
    main()
