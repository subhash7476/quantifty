"""VWAP-XREV primary run for ONE stage (freeze-gated). Usage: run_primary.py TRAIN|VAL|HOLDOUT [variant]

Variants (post-primary robustness) are named Params overrides defined in robustness.py; the
default variant is the frozen primary."""
from __future__ import annotations

import json
import sys

import pandas as pd

from scripts.vwap_rev import analyze as A
from scripts.vwap_rev import common as C
from scripts.vwap_rev import engine as E
from scripts.vwap_rev import freeze as F

RESULT_DIR = C.REPO / "docs" / "reports" / "research" / "results"


def primary_params() -> E.Params:
    proto = json.loads(C.PROTOCOL_PATH.read_text())
    return E.Params(q=float(proto["extreme_threshold"]["q_frozen"]))


def run(stage: str, params: E.Params, tag: str, horizons=A.HORIZONS) -> dict:
    F.assert_frozen()
    ev, sess = E.run_sessions(params, stages=(stage,), with_outcomes=True, progress=True)
    ev.to_parquet(C.OUT_DIR / f"events_{tag}_{stage}.parquet")
    sess.to_parquet(C.OUT_DIR / f"sessions_{tag}_{stage}.parquet")
    tab = A.stage_table(ev, stage, horizons)
    cost = A.cost_table(ev, stage, horizons)
    conc = {f"h{H}": A.concentration(ev[ev["stage"] == stage], H) for H in horizons}
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    tab.to_csv(RESULT_DIR / f"{tag}_{stage}_cells.csv", index=False)
    cost.to_csv(RESULT_DIR / f"{tag}_{stage}_costs.csv", index=False)
    (RESULT_DIR / f"{tag}_{stage}_concentration.json").write_text(json.dumps(conc, indent=1))
    return {"tab": tab, "cost": cost, "conc": conc, "n_events": len(ev)}


def main() -> None:
    stage = sys.argv[1]
    assert stage in ("TRAIN", "VAL", "HOLDOUT")
    tag = "primary"
    r = run(stage, primary_params(), tag)
    pd.set_option("display.width", 250, "display.max_columns", 40)
    cols = ["side", "H", "n_events", "n_names", "n_sessions", "session_mean_bp", "nw_t", "p_one_nw",
            "p_holm", "ci_lo", "ci_hi", "mean_bp_event", "median_bp_event", "frac_pos"]
    print(r["tab"][cols].round(4).to_string())


if __name__ == "__main__":
    sys.exit(main())
