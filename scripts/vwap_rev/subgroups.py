"""VWAP-XREV POST-PRIMARY subgroup / weighting / quarterly disclosure tables (non-classifying).

Cuts of the PRIMARY events only. No subgroup result can be promoted to a finding: this file exists to
show where the primary result lives (or does not), per Opus Review B."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from scripts.vwap_rev import common as C
from scripts.vwap_rev import regime as R
from scripts.vwap_rev import stats as S
from scripts.vwap_rev.run_primary import RESULT_DIR

HS = (5, 10, 15, 30, 60)
CAS = dt.date(2026, 8, 3)


def load() -> pd.DataFrame:
    ev = pd.concat([pd.read_parquet(C.OUT_DIR / f"events_primary_{s}.parquet")
                    for s in ("TRAIN", "VAL", "HOLDOUT")], ignore_index=True)
    dates = sorted(ev["date"].unique())
    lab = R.labels(dates)
    ev = ev.merge(lab[["date", "vix_terc", "mkt_regime"]], on="date", how="left")
    ev["tod"] = pd.cut(ev["D"], [59, 134, 209, 295], labels=["10:15-11:29", "11:30-12:44", "12:45-14:10"])
    ev["liq"] = pd.cut(ev["adv_rank"], [0, 1 / 3, 2 / 3, 1.0001], labels=["low", "mid", "high"])
    ev["svol"] = pd.cut(ev["scale_rank"], [0, 1 / 3, 2 / 3, 1.0001], labels=["low", "mid", "high"])
    ev["era"] = np.where(ev["date"] >= CAS, "post-CAS", "pre-CAS")
    ev["bar"] = np.where(ev["k"] == 59, "first-bar k59", "later")
    ev["vix"] = ev["vix_terc"].map({0: "low", 1: "mid", 2: "high"})
    n_ss = ev.groupby(["date", "side"])["symbol"].transform("size")
    ev["n_in_session_side"] = n_ss
    ev["quarter"] = pd.PeriodIndex(pd.to_datetime(ev["date"]), freq="Q").astype(str)
    ev["side_lbl"] = np.where(ev["side"] == 1, "up_disp_short", "down_disp_long")
    return ev


def light(sub: pd.DataFrame, col: str) -> dict:
    s = sub.dropna(subset=[col])
    if len(s) < 5:
        return {"n_events": len(s), "n_sessions": s["date"].nunique(), "session_mean": np.nan,
                "t": np.nan, "p_one": np.nan, "event_mean": np.nan}
    ss = s.groupby("date")[col].mean()
    nw = S.nw_mean_test(ss.to_numpy())
    return {"n_events": len(s), "n_sessions": len(ss), "session_mean": nw["mean"], "t": nw["t"],
            "p_one": nw["p_one"], "event_mean": float(s[col].mean())}


def subgroup_table(ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in ("tod", "vix", "mkt_regime", "liq", "svol", "era", "bar"):
        for lvl, g in ev.groupby(col, observed=True):
            for stage, gs in g.groupby("stage"):
                for side, gd in gs.groupby("side_lbl"):
                    for H in HS:
                        rows.append({"cut": col, "level": str(lvl), "stage": stage, "side": side, "H": H,
                                     **{f"raw_{k}": v for k, v in light(gd, f"R_h{H}").items()},
                                     "ex_session_mean": light(gd, f"R_ex_h{H}")["session_mean"],
                                     "ex_p_one": light(gd, f"R_ex_h{H}")["p_one"]})
    return pd.DataFrame(rows)


def quarterly_table(ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (q, side), g in ev.groupby(["quarter", "side_lbl"]):
        for H in (10, 30):
            rows.append({"quarter": q, "side": side, "H": H, "stage": g["stage"].iloc[0],
                         "n_events": len(g), "n_sessions": g["date"].nunique(),
                         "raw_event_mean": g[f"R_h{H}"].mean(), "raw_session_mean": g.groupby("date")[f"R_h{H}"].mean().mean(),
                         "ex_event_mean": g[f"R_ex_h{H}"].mean(), "ex_session_mean": g.groupby("date")[f"R_ex_h{H}"].mean().mean()})
    return pd.DataFrame(rows)


def weighting_table(ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for stage, gs in ev.groupby("stage"):
        for side, g in gs.groupby("side_lbl"):
            multi = g[g["n_in_session_side"] > 1]
            for H in HS:
                a, b = light(g, f"R_h{H}"), light(multi, f"R_h{H}")
                ae, be = light(g, f"R_ex_h{H}"), light(multi, f"R_ex_h{H}")
                rows.append({"stage": stage, "side": side, "H": H,
                             "session_mean_raw": a["session_mean"], "event_mean_raw": a["event_mean"],
                             "session_mean_raw_ex_singletons": b["session_mean"], "t_ex_singletons": b["t"],
                             "session_mean_excess": ae["session_mean"], "event_mean_excess": ae["event_mean"],
                             "session_mean_excess_ex_singletons": be["session_mean"],
                             "singleton_session_share": float((g.groupby("date").size() == 1).mean())})
    return pd.DataFrame(rows)


def composition_table(ev: pd.DataFrame) -> pd.DataFrame:
    sess = []
    for st in ("TRAIN", "VAL", "HOLDOUT"):
        s = pd.read_parquet(C.OUT_DIR / f"sessions_primary_{st}.parquet")
        s = s[s["stage"] == st]
        g = ev[ev["stage"] == st]
        sess.append({"stage": st, "sessions": len(s), "first": str(s["date"].min()), "last": str(s["date"].max()),
                     "mean_member_names": s["n_member"].mean(), "mean_eligible_names": s["n_elig_names"].mean(),
                     "events": len(g), "events_up": int((g["side"] == 1).sum()), "events_down": int((g["side"] == -1).sum()),
                     "distinct_names": g["symbol"].nunique(), "events_per_session": len(g) / len(s),
                     "share_first_bar": float((g["k"] == 59).mean())})
    return pd.DataFrame(sess)


def main() -> None:
    ev = load()
    subgroup_table(ev).to_csv(RESULT_DIR / "subgroups_cells.csv", index=False)
    quarterly_table(ev).to_csv(RESULT_DIR / "quarterly_excess.csv", index=False)
    weighting_table(ev).to_csv(RESULT_DIR / "weighting_views.csv", index=False)
    composition_table(ev).to_csv(RESULT_DIR / "stage_composition.csv", index=False)
    print("subgroup tables written")


if __name__ == "__main__":
    main()
