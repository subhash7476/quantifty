"""M4a-CE outcome-free diagnostics: substrate reconciliation, state incidence, cohort sizes, availability.

Imports neither `outcome` nor any price beyond t: a governance test asserts that. Its numbers describe sample size
and incidence and cannot select any parameter (all are pinned in the protocol).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from scripts.m4a_compress import cohorts as K
from scripts.m4a_compress import common as C
from scripts.m4a_compress import panel as PL
from scripts.m4a_compress.common import P


def _runs(low: np.ndarray, valid: np.ndarray) -> float:
    lens = []
    for e in range(low.shape[0]):
        cur = 0
        for x in low[e]:
            if x:
                cur += 1
            elif cur:
                lens.append(cur); cur = 0
        if cur:
            lens.append(cur)
    return float(np.mean(lens)) if lens else float("nan")


def variant_block(pn, variant: str) -> dict:
    f = K.cohort_flags(pn, variant, P)
    sess = pd.to_datetime(pn.sessions)
    out = {"variant": variant, "state_valid_name_days": int(f["state_valid"].sum()),
           "member_state_valid_name_days": int((f["state_valid"] & pn.member).sum()),
           "low_name_days": int((f["low"] & f["state_valid"]).sum()),
           "low_share_of_state_valid": float((f["low"] & f["state_valid"]).sum() / max(f["state_valid"].sum(), 1)),
           "high_share_of_state_valid": float((f["high"] & f["state_valid"]).sum() / max(f["state_valid"].sum(), 1)),
           "mean_low_run_length": _runs(f["low"] & f["state_valid"], f["state_valid"]), "stages": {}}
    inlow = (f["low"] & f["state_valid"] & pn.member).sum(axis=0)
    for st in C.STAGES:
        lo, hi = K.stage_bounds(pn.sessions, st)
        blk = {"sessions": hi - lo + 1}
        for k in ("comp", "norm", "pers"):
            blk[f"{k}_events"] = int(f[k][:, lo:hi + 1].sum())
        blk["names_in_low_state_per_date"] = {q: float(np.quantile(inlow[lo:hi + 1], v)) for q, v in
                                             (("median", .5), ("p90", .9), ("max", 1.0))}
        nC, nN, nP = (f[k][:, lo:hi + 1].sum(axis=0) for k in ("comp", "norm", "pers"))
        blk["dates_with_comp"] = int((nC > 0).sum())
        blk["dates_comp_and_norm_ge_floor"] = int(((nC > 0) & (nN >= P.min_normal_names)).sum())
        blk["dates_comp_and_pers"] = int(((nC > 0) & (nP > 0)).sum())
        blk["dates_norm_below_floor_with_comp"] = int(((nC > 0) & (nN < P.min_normal_names)).sum())
        blk["median_norm_names_per_date"] = float(np.median(nN))
        avail = {}
        for h in P.horizons:
            st_h = K.forward_status(pn.valid, h)
            for k in ("comp", "norm", "pers"):
                m = f[k][:, lo:hi + 1] & (np.arange(lo, hi + 1)[None, :] + h <= hi)
                tot = int(m.sum())
                normal = int((m & (st_h[:, lo:hi + 1] == K.ST_NORMAL)).sum())
                avail[f"{k}_h{h}"] = {"formed_with_window_in_stage": tot, "window_available": normal,
                                      "dropped": tot - normal, "dropped_share": (tot - normal) / max(tot, 1)}
        blk["forward_availability_only"] = avail
        out["stages"][st] = blk
    yrs = {}
    for y in range(2012, 2023):
        idx = np.where(sess.year == y)[0]
        yrs[str(y)] = {k: int(f[k][:, idx].sum()) for k in ("comp", "norm", "pers")}
    out["events_by_year"] = yrs
    return out


def run() -> dict:
    pn = PL.load_panel()
    E, T = pn.valid.shape
    out = {"entities": E, "regular_sessions": T, "panel_sha256": PL.sha256_file(C.SNAPSHOT_DIR / "panel_dev.parquet"),
           "panel_max_date": str(pd.Timestamp(pn.sessions[-1]).date()),
           "membership_name_days": int(pn.member.sum()),
           "lookback_sessions_required_for_onset": P.slow + P.pct_window + P.quiet,
           "variants": {v: variant_block(pn, v) for v in ("D2", "D1")}}
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    (C.OUT_DIR / "diagnostics_outcome_free.json").write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, default=str))
