"""Experiment 0 — unconditional baseline of post-12:30 outcomes (TRAIN only).

Frozen horizons: 12:30 -> 13:00 / 13:30 / 14:00 / 15:00 / close, plus MFE and
MAE over the remainder of the session. No analogue matching. Refuses SEALED.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np

from scripts.analog_path import config
from scripts.analog_path.data_layer import load_session
from scripts.analog_path.eligibility import load_eligible_dates
from scripts.analog_path.ledger import record
from scripts.analog_path.stats import summary

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "analog_path" / "exp0_unconditional.json"


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

    result = {
        "experiment": "exp0_unconditional",
        "fence": fence,
        "config_sha256": config.CONFIG_SHA256,
        "n_sessions": len(sessions),
        "skipped_invalid": skipped,
        "horizons": {},
        "excursions": {},
    }
    for key in config.HORIZONS:
        x = np.asarray([s.outcomes[key] for s in sessions], dtype=float)
        result["horizons"][key] = summary(x)
    for name, arr in (("mfe", np.asarray([s.mfe for s in sessions])),
                      ("mae", np.asarray([s.mae for s in sessions]))):
        result["excursions"][name] = summary(arr)

    record("exp0_unconditional", fence=fence, representation=None, distance=None,
           k=None, horizon="all", sample="eligible TRAIN sessions",
           metric="unconditional outcome distribution",
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
    print(f"exp0 {args.fence}: n={out['n_sessions']} skipped={out['skipped_invalid']}")
    for k, v in out["horizons"].items():
        print(f"  {k:6s} n={v['n']:5d} mean={v['mean']:+.5f} median={v['median']:+.5f} "
              f"sd={v['sd']:.5f} hit={v['hit_rate']:.3f} nw_t={v['nw_t']:+.2f}")
    for k, v in out["excursions"].items():
        print(f"  {k:6s} n={v['n']:5d} mean={v['mean']:+.5f} median={v['median']:+.5f}")
