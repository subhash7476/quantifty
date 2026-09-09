"""Experiment 1 — return-only baseline (TRAIN only).

Condition only on R = P(12:30)/P(open) - 1, binned by the frozen edges
(<=-2%, (-2,-1], (-1,-0.5], (-0.5,0], (0,0.5], (0.5,1], (1,2], >2%).
Per bin per frozen horizon: the full summary block. Continuous confirmation:
OLS of outcome on R with Newey-West SE, per horizon (pre-specified).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.analog_path import config
from scripts.analog_path.data_layer import load_session
from scripts.analog_path.eligibility import load_eligible_dates
from scripts.analog_path.ledger import record
from scripts.analog_path.stats import ols_nw, summary

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "analog_path" / "exp1_return_bins.json"

BIN_EDGES = np.asarray(config.BIN_EDGES_PCT) / 100.0  # frozen edges, fractions


def _bin_index(r: float) -> int:
    return int(np.searchsorted(BIN_EDGES[1:-1], r, side="right"))


def run(fence: str = "train") -> dict:
    dates = load_eligible_dates(fence)
    for d in dates:
        config.require_fence(d, fence)
    sessions = []
    skipped = 0
    for d in dates:
        s = load_session(d)
        if s is None or not s.valid:
            skipped += 1
            continue
        sessions.append(s)

    rs = np.asarray([s.open_to_1230 for s in sessions], dtype=float)
    result = {
        "experiment": "exp1_return_bins",
        "fence": fence,
        "config_sha256": config.CONFIG_SHA256,
        "n_sessions": len(sessions),
        "skipped_invalid": skipped,
        "bin_edges_pct": config.BIN_EDGES_PCT,
        "bins": {},
        "continuous": {},
        "overall_r_summary": summary(rs),
    }
    for b in range(len(BIN_EDGES) - 1):
        mask = np.searchsorted(BIN_EDGES[1:-1], rs, side="right") == b
        result["bins"][str(b)] = {
            "label": f"bin_{b}",
            "n": int(mask.sum()),
            "horizons": {},
        }
        for key in config.HORIZONS:
            y = np.asarray([s.outcomes[key] for s in sessions], dtype=float)
            result["bins"][str(b)]["horizons"][key] = summary(y[mask])

    for key in config.HORIZONS:
        y = np.asarray([s.outcomes[key] for s in sessions], dtype=float)
        result["continuous"][key] = ols_nw(y, rs)

    record("exp1_return_bins", fence=fence, representation=None, distance=None,
           k=None, horizon="all", sample="eligible TRAIN sessions",
           metric="return-conditioned outcome distribution + NW OLS",
           result={"n_sessions": len(sessions)},
           used_for_methodology_decision=False)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as fh:
        json.dump(result, fh, indent=1, default=str)
    return result


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--fence", choices=["train", "holdout"], default="train")
    args = p.parse_args()
    out = run(args.fence)
    print(f"exp1 {args.fence}: n={out['n_sessions']} skipped={out['skipped_invalid']}")
    print("continuous OLS (outcome on R, NW SE):")
    for k, v in out["continuous"].items():
        print(f"  {k:6s} n={v['n']:5d} slope={v['slope']:+.4f} nw_t={v['nw_t']:+.2f} "
              f"p={v['p']:.4f} r2={v['r2']:.4f}")
    for b, v in out["bins"].items():
        h = v["horizons"]["close"]
        print(f"  {v['label']} n={v['n']:4d} close: mean={h['mean']:+.5f} "
              f"median={h['median']:+.5f} hit={h['hit_rate']:.3f}")
