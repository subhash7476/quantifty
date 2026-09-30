"""VWAP-XREV primary run for ONE stage (freeze-gated). Usage: run_primary.py TRAIN|VAL|HOLDOUT

TRAIN and VAL run the primary variant. HOLDOUT is ONE-SHOT and runs the primary variant plus
the pre-registered entry_delay=2 microstructure qualifier in the same invocation, only after
the VAL cells file exists. Post-primary robustness lives in robustness.py (non-classifying)."""
from __future__ import annotations

import json
import sys
from dataclasses import replace

import pandas as pd

from scripts.vwap_rev import analyze as A
from scripts.vwap_rev import common as C
from scripts.vwap_rev import engine as E
from scripts.vwap_rev import freeze as F

RESULT_DIR = C.REPO / "docs" / "reports" / "research" / "results"


def primary_params() -> E.Params:
    proto = json.loads(C.PROTOCOL_PATH.read_text())
    return E.Params(q=float(proto["extreme_threshold"]["q_frozen"]))


def cells_path(tag: str, stage: str):
    return RESULT_DIR / f"{tag}_{stage}_cells.csv"


def excess_view(ev: pd.DataFrame) -> pd.DataFrame:
    ex = ev.copy()
    for H in A.HORIZONS:
        ex[f"R_h{H}"] = ex[f"R_ex_h{H}"]
    return ex


def run(stage: str, params: E.Params, tag: str, full_outputs: bool = True) -> pd.DataFrame:
    F.assert_frozen()
    ev, sess = E.run_sessions(params, stages=(stage,), with_outcomes=True, progress=True)
    ev.to_parquet(C.OUT_DIR / f"events_{tag}_{stage}.parquet")
    sess.to_parquet(C.OUT_DIR / f"sessions_{tag}_{stage}.parquet")
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    tab = A.stage_table(ev, stage, params.horizons)
    tab.to_csv(cells_path(tag, stage), index=False)
    if full_outputs:
        A.cost_table(ev, stage, params.horizons).to_csv(RESULT_DIR / f"{tag}_{stage}_costs.csv", index=False)
        A.stage_table(excess_view(ev), stage, params.horizons).to_csv(
            RESULT_DIR / f"{tag}_{stage}_excess_cells.csv", index=False)
        sub = ev[ev["stage"] == stage]
        (RESULT_DIR / f"{tag}_{stage}_concentration.json").write_text(json.dumps(
            {f"h{H}": A.concentration(sub, H) for H in params.horizons}, indent=1))
        (RESULT_DIR / f"{tag}_{stage}_first_bar_split.json").write_text(json.dumps(
            {f"h{H}": A.first_bar_split(sub, H) for H in params.horizons}, indent=1, default=float))
    return tab


def show(tab: pd.DataFrame) -> None:
    pd.set_option("display.width", 250, "display.max_columns", 40)
    cols = ["side", "H", "n_events", "n_names", "n_sessions", "nan_share", "session_mean_bp", "nw_t",
            "p_one_nw", "p_holm_all10", "ci_lo", "ci_hi", "mean_bp_event", "median_bp_event", "frac_pos"]
    print(tab[cols].round(4).to_string())


def main() -> None:
    stage = sys.argv[1]
    assert stage in ("TRAIN", "VAL", "HOLDOUT")
    p = primary_params()
    if stage == "HOLDOUT":
        F.holdout_guard(cells_path("primary", "VAL"))
        tab = run(stage, p, "primary")
        run(stage, replace(p, entry_delay=2), "delay2", full_outputs=False)
        F.mark_holdout_read("primary + delay2 qualifier computed in one invocation")
    else:
        tab = run(stage, p, "primary")
    show(tab)


if __name__ == "__main__":
    sys.exit(main())
