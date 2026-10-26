"""M4a-CE stage runner: TRAIN and VAL. There is no HOLDOUT stage in this package.

    python -m scripts.m4a_compress.run_stage TRAIN|VAL
    python -m scripts.m4a_compress.run_stage CLASSIFY

Refuses to run unless the freeze hashes match. Writes, per stage, into OUT_DIR/results/:
  events_{variant}_{stage}.parquet   the event ledger (one row per (entity, session) in any cohort, every input to E)
  cells_{stage}.csv                  the cell table (variant x horizon x comparator x outcome)
  cohort_{variant}_{stage}.csv       the date-cohort ledger of the primary outcome (per cell: date, n_C, m_C, n_X, m_X, d)
  levels_/signed_/byyear_{stage}.csv, concentration_{stage}.json, accounting_{stage}.json
"""
from __future__ import annotations

import itertools
import json
import sys

import numpy as np
import pandas as pd

from scripts.m4a_compress import analyze as A
from scripts.m4a_compress import classify as CL
from scripts.m4a_compress import cohorts as K
from scripts.m4a_compress import common as C
from scripts.m4a_compress import freeze as F
from scripts.m4a_compress import outcome as O
from scripts.m4a_compress import panel as PL
from scripts.m4a_compress.common import P

VARIANTS = ("D2", "D1")
COMPARATORS = ("normal", "persistence")
SECONDARY = ("E_vol", "E_abs")


def _res():
    return C.OUT_DIR / "results"


def _accounting(ev: pd.DataFrame, sessions, stage: str, p) -> dict:
    lo, hi = K.stage_bounds(sessions, stage)
    out = {}
    for h in p.horizons:
        formed = ev[(ev["t"] >= lo) & (ev["t"] <= hi)]
        inst = K.in_stage(formed["t"].to_numpy(), h, lo, hi)
        st = formed[f"status{h}"].to_numpy()
        val = formed[f"E_range{h}"].notna().to_numpy()
        for name, col in (("C", "is_C"), ("N", "is_N"), ("P", "is_P")):
            m = formed[col].to_numpy()
            row = {"formed": int(m.sum()), "resolved": int((m & inst & (st == K.ST_NORMAL) & val).sum()),
                   "dropped": int((m & inst & (st == K.ST_DROPPED)).sum()),
                   "value_missing": int((m & inst & (st == K.ST_NORMAL) & ~val).sum()),
                   "excluded_by_containment": int((m & ~inst).sum())}
            assert row["resolved"] + row["dropped"] + row["value_missing"] + row["excluded_by_containment"] == row["formed"], \
                "accounting identity broken"
            out[f"h{h}_{name}"] = row
    return out


def _series_rows(ser: dict, sessions, stage, variant, h, comparator) -> pd.DataFrame:
    pair = ser["pair"].reset_index()
    pair["date"] = sessions[pair["t"].to_numpy()]
    pair.insert(0, "stage", stage); pair.insert(1, "variant", variant); pair.insert(2, "h", h); pair.insert(3, "comparator", comparator)
    return pair


def execute(stage: str, p=P, pn=None) -> pd.DataFrame:
    if stage not in C.STAGES:
        raise ValueError(f"unknown stage {stage!r}; this package has only {sorted(C.STAGES)} (no HOLDOUT exists)")
    _res().mkdir(parents=True, exist_ok=True)
    pn = pn if pn is not None else PL.load_panel()
    lo, hi = K.stage_bounds(pn.sessions, stage)
    rows, cohorts, levels, signed, byyear, conc, acct = [], [], [], [], [], {}, {}
    for variant in VARIANTS:
        flags = K.cohort_flags(pn, variant, p)
        ev = O.attach(pn, K.events_frame(pn, flags), p)
        ev = ev[(ev["t"] >= lo) & (ev["t"] <= hi)].reset_index(drop=True)
        ev.to_parquet(_res() / f"events_{variant}_{stage}.parquet", index=False)
        acct[variant] = _accounting(ev, pn.sessions, stage, p)
        ser_all = []
        for h, comp in itertools.product(p.horizons, COMPARATORS):
            row, ser = A.cell_row(ev, pn.sessions, stage, h, comp, "E_range", p, extras=(variant == "D2"))
            rows.append({"variant": variant, **row})
            ser_all.append(_series_rows(ser, pn.sessions, stage, variant, h, comp))
            if variant == "D2":
                d = ser["pair"]["d"]
                if len(d):
                    yy = A.by_year(d, pn.sessions).reset_index().rename(columns={"index": "year"})
                    yy.insert(0, "stage", stage); yy.insert(1, "h", h); yy.insert(2, "comparator", comp)
                    byyear.append(yy)
                    conc[f"h{h}_{comp}"] = A.concentration(d, pn.sessions)
            for outc in SECONDARY:
                r2, _ = A.cell_row(ev, pn.sessions, stage, h, comp, outc, p, extras=False)
                rows.append({"variant": variant, **r2})
        pd.concat(ser_all).to_csv(_res() / f"cohort_{variant}_{stage}.csv", index=False)
        for h in p.horizons:
            levels.append(A.cohort_levels(ev, pn.sessions, stage, h).assign(variant=variant))
            signed.append(A.signed_descriptive(ev, pn.sessions, stage, h, p).assign(variant=variant))
    cells = pd.DataFrame(rows)
    cells.to_csv(_res() / f"cells_{stage}.csv", index=False)
    pd.concat(levels).to_csv(_res() / f"levels_{stage}.csv", index=False)
    pd.concat(signed).to_csv(_res() / f"signed_{stage}.csv", index=False)
    if byyear:
        pd.concat(byyear).to_csv(_res() / f"byyear_{stage}.csv", index=False)
    (_res() / f"concentration_{stage}.json").write_text(json.dumps(conc, indent=2))
    (_res() / f"accounting_{stage}.json").write_text(json.dumps(acct, indent=2))
    (_res() / f"run_{stage}.json").write_text(json.dumps({"stage": stage, "panel_sessions": int(len(pn.sessions))}, indent=2))
    print(cells[cells["outcome"] == "E_range"][["variant", "stage", "h", "comparator", "n_C", "n_X", "n_pair_dates",
                                                 "d_mean", "d_t", "d_p_one"]].to_string())
    return cells


def run(stage: str) -> None:
    F.assert_frozen()
    execute(stage)


def _keys(o):
    if isinstance(o, dict):
        return {(",".join(map(str, k)) if isinstance(k, tuple) else k): _keys(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_keys(x) for x in o]
    return o


def classify_final(p=P) -> dict:
    F.assert_frozen()
    val = pd.read_csv(_res() / "cells_VAL.csv")
    prim = val[(val["variant"] == "D2") & (val["outcome"] == "E_range")]
    res = CL.classify(prim, alpha=p.alpha)
    res["primary_family_size"] = int(len(prim))
    train = pd.read_csv(_res() / "cells_TRAIN.csv")
    tr = train[(train["variant"] == "D2") & (train["outcome"] == "E_range")]
    res["train_descriptive"] = _keys(CL.val_consistent(tr, p.alpha)[1])                    # TRAIN takes no decision
    d1 = val[(val["variant"] == "D1") & (val["outcome"] == "E_range")]
    res["d1_disclosure_holm"] = _keys({k: v for k, v in CL.val_consistent(d1.assign(bound_d_mean=np.nan,
                                                                                    bound_d_p_one=np.nan), p.alpha)[1].items()})
    out = _keys(res)
    (_res() / "classification.json").write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "CLASSIFY":
        print(json.dumps(classify_final(), indent=2, default=str))
    else:
        run(sys.argv[1])
