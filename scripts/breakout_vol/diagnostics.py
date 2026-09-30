"""BKV-1 outcome-free diagnostics: substrate reconciliation and event counts by formation date only.

Reads NO forward price. Run before the freeze; its numbers describe sample size and incidence, and
cannot select any parameter (all parameters are pinned in the protocol).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from scripts.breakout_vol import common as C
from scripts.breakout_vol import engine as G


def run() -> dict:
    pn = G.load_panel("dev")
    E, T = pn.valid.shape
    ev = G.detect_events(pn)
    d = pd.to_datetime(ev["date"])
    stage = np.select([(d >= pd.Timestamp(C.STAGES["TRAIN"][0])) & (d <= pd.Timestamp(C.STAGES["TRAIN"][1])),
                       (d >= pd.Timestamp(C.STAGES["VAL"][0])) & (d <= pd.Timestamp(C.STAGES["VAL"][1]))],
                      ["TRAIN", "VAL"], "other")
    ev = ev.assign(stage=stage)
    elig = G.eligibility(pn)
    sess_dt = pd.to_datetime(pn.sessions)
    out = {"entities": E, "regular_sessions": T,
           "dropped_calendar_dates": pn.dropped_sessions.assign(trade_date=lambda x: x.trade_date.astype(str)).to_dict("records"),
           "membership_name_days": int(pn.member.sum()), "eligible_name_days": int(elig.sum()),
           "sessions_by_stage": {k: int(((sess_dt >= pd.Timestamp(a)) & (sess_dt <= pd.Timestamp(b))).sum()) for k, (a, b) in C.STAGES.items() if k != "HOLDOUT"},
           "events": {}}
    for st in ("TRAIN", "VAL"):
        lo, hi = G.stage_bounds(pn.sessions, st)
        out.setdefault("eligible_name_days_by_stage", {})[st] = int(elig[:, lo:hi + 1].sum())
        out.setdefault("members_name_days_by_stage", {})[st] = int(pn.member[:, lo:hi + 1].sum())
    g = ev[ev["stage"].isin(["TRAIN", "VAL"])].groupby(["stage", "N", "kind", "arm"]).size()
    for (st, n, kind, arm), c in g.items():
        out["events"].setdefault(st, {}).setdefault(f"N{n}", {})[f"{kind}:{arm}"] = int(c)
    # breakout flags before the onset/quiet filter (how much the onset rule removes)
    for n in C.P.range_n:
        m = G.detect_masks(pn, n)
        for st in ("TRAIN", "VAL"):
            lo, hi = G.stage_bounds(pn.sessions, st)
            for key in ("up", "dn"):
                raw = (m[key] & m["elig"])[:, lo:hi + 1].sum()
                out.setdefault("breakout_flags_before_onset", {}).setdefault(st, {})[f"N{n}:{key}"] = int(raw)
    (C.OUT_DIR / "diagnostics_outcome_free.json").write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, default=str))
