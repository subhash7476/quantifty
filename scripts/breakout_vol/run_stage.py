"""BKV-1 stage runner: TRAIN, VAL, and (one-shot, authorised) HOLDOUT.

    python -m scripts.breakout_vol.run_stage TRAIN|VAL|HOLDOUT
    python -m scripts.breakout_vol.run_stage CLASSIFY

Refuses to run unless the freeze hashes match. Writes, per stage, into OUT_DIR/results/:
  events_{stage}.parquet/.csv.gz   the event ledger (one row per event, every input to its f)
  cohort_{stage}.csv               the session-cohort ledger (per cell: date, n_B, n_C, m_B, m_C, d)
  cells_{stage}.csv                the cell table (16 = 2N x 2H x 2 sides per stage)
  costs_{stage}.csv                cost scenarios
  accounting_{stage}.json          the sample-count reconciliation
"""
from __future__ import annotations

import itertools
import json
import sys

import numpy as np
import pandas as pd

from scripts.breakout_vol import analyze as A
from scripts.breakout_vol import classify as K
from scripts.breakout_vol import common as C
from scripts.breakout_vol import engine as G
from scripts.breakout_vol import freeze as F
from scripts.breakout_vol import stats as S
from scripts.breakout_vol.common import P



def _res():
    return C.OUT_DIR / "results"


def _accounting(ev: pd.DataFrame, sessions, stage: str) -> dict:
    lo, hi = G.stage_bounds(sessions, stage)
    out = {}
    for N, H, side in itertools.product(P.range_n, P.horizons, ("up", "dn")):
        sf = A.side_frame(ev, N, side)
        formed = sf[(sf["t"] >= lo) & (sf["t"] <= hi)]
        inst = G.in_stage(formed, sessions, stage, H)
        drop = G.dropped_in_stage(formed, sessions, stage, H)
        beyond = (formed["t"] + H > hi) & ~inst
        nobench = formed[f"status{H}"].isin([G.ST_NORMAL, G.ST_TERMINAL]) & formed[f"f{H}"].isna() & (formed["t"] + H <= hi)
        assert int(inst.sum() + drop.sum() + beyond.sum() + nobench.sum()) == len(formed), "accounting identity broken"
        row = {"formed": len(formed), "resolved_in_stage": int(inst.sum()), "dropped": int(drop.sum()),
               "excluded_by_containment": int(beyond.sum()), "excluded_no_benchmark": int(nobench.sum()),
               "terminal_within_resolved": int((formed.loc[inst, f"status{H}"] == G.ST_TERMINAL).sum())}
        for arm in ("B", "C", "D"):
            m = formed["arm"] == arm
            row[f"formed_{arm}"] = int(m.sum())
            row[f"resolved_{arm}"] = int((inst & m).sum())
        row["A_equals_B_plus_C"] = bool(((inst & formed["arm"].isin(["B", "C"])).sum()) ==
                                        ((inst & (formed["arm"] == "B")).sum() + (inst & (formed["arm"] == "C")).sum()))
        out[f"N{N}_H{H}_{side}"] = row
    return out


def econ_gate(ev: pd.DataFrame, sessions, stage: str, cell: tuple, m_cells: int, p=P) -> dict:
    """HOLDOUT economic gate for one confirmed cell: B-arm event-weighted net > 0 at the base kappa AND the
    cohort-by-date block-bootstrap one-sided lower bound at level alpha/m > 0."""
    N, H, side = cell
    sf = A.side_frame(ev, N, side)
    b = sf[G.in_stage(sf, sessions, stage, H) & (sf["arm"] == "B")]
    fee = A.event_fee_bp(b, H, p.notional)
    net = b[f"raw{H}"].to_numpy() - fee - 2 * p.base_kappa_bp
    coh = pd.DataFrame({"t": b["t"].to_numpy(), "net": net}).groupby("t")["net"].mean()
    bb = S.block_bootstrap_mean(coh.to_numpy(), block=H + 1, n_boot=p.n_boot, seed=p.boot_seed, lb_alpha=p.alpha / m_cells)
    return {"net_evt_bp": float(net.mean()), "lb_bp": bb["lb"], "pass": bool(net.mean() > 0 and bb["lb"] > 0)}


def run(stage: str) -> None:
    rec = F.assert_frozen()
    if stage == "HOLDOUT":
        F.holdout_guard(_res() / "cells_VAL.csv")
    execute(stage, "full" if stage == "HOLDOUT" else "dev", rec["git_head_at_freeze"])
    if stage == "HOLDOUT":
        F.mark_holdout_read("BKV-1 HOLDOUT read")


def execute(stage: str, tag: str, freeze_head: str = "dry-run") -> pd.DataFrame:
    _res().mkdir(parents=True, exist_ok=True)
    pn = G.load_panel(tag)
    ev = G.detect_events(pn)
    ev, bench = G.attach_outcomes(pn, ev)
    lo, hi = G.stage_bounds(pn.sessions, stage)
    ev = ev[(ev["t"] >= lo) & (ev["t"] <= hi)].reset_index(drop=True)      # formations in this stage only
    ev.to_parquet(_res() / f"events_{stage}.parquet", index=False)
    ev.to_csv(_res() / f"events_{stage}.csv.gz", index=False, compression="gzip")
    bench[(bench["t"] >= lo) & (bench["t"] <= hi + max(P.horizons))].to_csv(_res() / f"bench_{stage}.csv", index=False)
    rows, cohorts, costs = [], [], []
    for N, H, side in itertools.product(P.range_n, P.horizons, ("up", "dn")):
        row, ser = A.cell_row(ev, pn.sessions, stage, N, H, side)
        rows.append(row)
        pair = ser["pair"].reset_index()
        pair["date"] = pn.sessions[pair["t"].to_numpy()]
        pair.insert(0, "stage", stage); pair.insert(1, "N", N); pair.insert(2, "H", H); pair.insert(3, "side", side)
        cohorts.append(pair)
        for arm in ("A", "B", "C"):
            costs.extend(A.cost_rows(ev, pn.sessions, stage, N, H, side, arm))
    cells = pd.DataFrame(rows)
    cells.to_csv(_res() / f"cells_{stage}.csv", index=False)
    pd.concat(cohorts).to_csv(_res() / f"cohort_{stage}.csv", index=False)
    pd.DataFrame(costs).to_csv(_res() / f"costs_{stage}.csv", index=False)
    (_res() / f"accounting_{stage}.json").write_text(json.dumps(_accounting(ev, pn.sessions, stage), indent=2))
    (_res() / f"run_{stage}.json").write_text(json.dumps({"stage": stage, "panel_tag": tag, "freeze_head": freeze_head,
                                                       "events": len(ev)}, indent=2))
    print(cells[["stage", "N", "H", "side", "n_B", "n_C", "n_pair_dates", "d_mean", "d_t", "d_p_one"]].to_string())
    return cells


def classify_final() -> dict:
    F.assert_frozen()
    val = pd.read_csv(_res() / "cells_VAL.csv")
    hold_path = _res() / "cells_HOLDOUT.csv"
    hold = pd.read_csv(hold_path) if hold_path.exists() else None
    econ = {}
    if hold is not None:
        v, _ = K.val_confirmed(val)
        h, _ = K.holdout_confirmed(v, hold)
        pn = G.load_panel("full")
        ev = pd.read_parquet(_res() / "events_HOLDOUT.parquet")
        for c in h:
            econ[c] = econ_gate(ev, pn.sessions, "HOLDOUT", c, len(h))["pass"]
    res = K.classify(val, hold, econ_pass=econ)
    def _keys(o):
        if isinstance(o, dict):
            return {(",".join(map(str, k)) if isinstance(k, tuple) else k): _keys(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_keys(x) for x in o]
        return o
    out = _keys(res)
    (_res() / "classification.json").write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "CLASSIFY":
        print(json.dumps(classify_final(), indent=2, default=str))
    else:
        run(sys.argv[1])
