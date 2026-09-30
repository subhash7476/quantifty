"""VWAP-XREV POST-PRIMARY robustness grid (non-classifying; not part of the frozen hash set).

Every variant is a Params override defined in protocol `robustness`. Results are disclosure only and
can never enter the classification. Usage: robustness.py variant [variant ...]"""
from __future__ import annotations

import sys
from dataclasses import replace

import pandas as pd

from scripts.vwap_rev import analyze as A
from scripts.vwap_rev import common as C
from scripts.vwap_rev import engine as E
from scripts.vwap_rev.run_primary import RESULT_DIR, primary_params

VARIANTS = {
    "q995": dict(q=0.995), "q999": dict(q=0.999),
    "norm_range": dict(norm_mode="range"), "norm_raw_bp": dict(norm_mode="raw_bp"),
    "vwap_close": dict(vwap_mode="close"), "delay2": dict(entry_delay=2),
    "dedup_all": dict(dedup="all"), "universe_all": dict(universe="all"),
    "universe_core": dict(universe="core"), "exit_last_valid": dict(exit_fill="last_valid"),
    "extra_h": dict(horizons=(20, 45)),
}


def run_variant(name: str) -> None:
    p = replace(primary_params(), **VARIANTS[name])
    ev, _ = E.run_sessions(p, with_outcomes=True)
    ev.to_parquet(C.OUT_DIR / f"events_robust_{name}.parquet")
    for stage in ("TRAIN", "VAL", "HOLDOUT"):
        tab = A.stage_table(ev, stage, p.horizons)
        tab.to_csv(RESULT_DIR / f"robust_{name}_{stage}_cells.csv", index=False)
    print("done", name, len(ev), flush=True)


if __name__ == "__main__":
    for v in sys.argv[1:]:
        run_variant(v)
