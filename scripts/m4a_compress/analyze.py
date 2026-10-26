"""M4a-CE cell tables: the cohort-by-formation-date contrast d(t) = mean_C(E) - mean_X(E), X in {normal, persistence}.

Units: E is dimensionless (forward statistic / the name's own trailing baseline ending at t). The observation for a
date is the equal-weighted mean over that cohort's events formed at t, so cross-sectional dependence on a date is
removed by construction. Inference: one-sided (H1: d-bar > 0) calendar-aware Newey-West, lag = h.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.m4a_compress import cohorts as K
from scripts.m4a_compress import stats as S
from scripts.m4a_compress.common import P, Params

COMPARATOR_COL = {"normal": "is_N", "persistence": "is_P"}


def cohort(df: pd.DataFrame, col: str) -> pd.DataFrame:
    return df.groupby("t")[col].agg(["mean", "size"]).rename(columns={"mean": "m", "size": "n"})


def _masks(ev: pd.DataFrame, sessions: np.ndarray, stage: str, h: int, outcome: str):
    """(resolved, dropped, value-missing) row masks for events whose formation and whole window lie in the stage."""
    lo, hi = K.stage_bounds(sessions, stage)
    inst = K.in_stage(ev["t"].to_numpy(), h, lo, hi)
    st = ev[f"status{h}"].to_numpy()
    val = ev[f"{outcome}{h}"].notna().to_numpy()
    return inst & (st == K.ST_NORMAL) & val, inst & (st == K.ST_DROPPED), inst & (st == K.ST_NORMAL) & ~val


def _pair(cC: pd.DataFrame, cX: pd.DataFrame, floor: int) -> tuple[pd.DataFrame, int]:
    j = cC.join(cX, lsuffix="_C", rsuffix="_X", how="inner")
    below = int((j["n_X"] < floor).sum())
    j = j[j["n_X"] >= floor].copy()
    j["d"] = j["m_C"] - j["m_X"]
    return j, below


def _attrition_bound(C: pd.DataFrame, X: pd.DataFrame, dC: pd.DataFrame, dX: pd.DataFrame, y: str, h: int,
                     floor: int) -> dict:
    """Worst case for the claim d > 0 (BKV-1 rule): dropped compression events take the smallest retained C value,
    dropped comparator events the largest retained X value, each on its own formation date."""
    if len(C) == 0 or len(X) == 0:
        return {"bound_d_mean": np.nan, "bound_d_p_one": np.nan}
    c2 = pd.concat([C[["t", y]], pd.DataFrame({"t": dC["t"].to_numpy(), y: float(C[y].min())})])
    x2 = pd.concat([X[["t", y]], pd.DataFrame({"t": dX["t"].to_numpy(), y: float(X[y].max())})])
    pr, _ = _pair(cohort(c2, y), cohort(x2, y), floor)
    if len(pr) < 3:
        return {"bound_d_mean": np.nan, "bound_d_p_one": np.nan}
    r = S.nw_gap_test(pr["d"].to_numpy(), pr.index.to_numpy(), h)
    return {"bound_d_mean": r["mean"], "bound_d_p_one": r["p_one"]}


def cell_row(ev: pd.DataFrame, sessions: np.ndarray, stage: str, h: int, comparator: str, outcome: str = "E_range",
             p: Params = P, extras: bool = True) -> tuple[dict, dict]:
    y = f"{outcome}{h}"
    xcol = COMPARATOR_COL[comparator]
    floor = p.min_normal_names if comparator == "normal" else 1
    res, drop, miss = _masks(ev, sessions, stage, h, outcome)
    isC, isX = ev["is_C"].to_numpy(), ev[xcol].to_numpy()
    C, X = ev[res & isC], ev[res & isX]
    dC, dX = ev[drop & isC], ev[drop & isX]
    cC, cX = cohort(C, y), cohort(X, y)
    pair, below = _pair(cC, cX, floor)
    row = {"stage": stage, "h": h, "comparator": comparator, "outcome": outcome,
           "n_C": len(C), "n_X": len(X), "dates_C": len(cC), "dates_X": len(cX),
           "mean_C_evt": float(C[y].mean()) if len(C) else np.nan, "mean_X_evt": float(X[y].mean()) if len(X) else np.nan,
           "mean_C_coh": float(cC["m"].mean()) if len(cC) else np.nan, "mean_X_coh": float(cX["m"].mean()) if len(cX) else np.nan,
           "n_pair_dates": len(pair), "n_dates_below_floor": below, "n_dropped_C": len(dC), "n_dropped_X": len(dX),
           "n_value_missing": int((miss & (isC | isX)).sum())}
    if len(pair) >= 3:
        r = S.nw_gap_test(pair["d"].to_numpy(), pair.index.to_numpy(), h)
        row.update({"d_mean": r["mean"], "d_se": r["se"], "d_t": r["t"], "d_p_one": r["p_one"],
                    "d_mde80": S.mde_one_sided(r["se"], p.alpha),
                    "d_mean_evtwt": float((pair["d"] * pair["n_C"]).sum() / pair["n_C"].sum())})
    else:
        row.update(dict.fromkeys(("d_mean", "d_se", "d_t", "d_p_one", "d_mde80", "d_mean_evtwt"), np.nan))
    row["d_lag"] = h
    if extras and len(pair) >= 3:
        bb = S.block_bootstrap_mean(pair["d"].to_numpy(), block=h + 1, n_boot=p.n_boot, seed=p.boot_seed)
        row["d_ci_lo"], row["d_ci_hi"] = bb["ci_lo"], bb["ci_hi"]
        both = pd.concat([C[C["t"].isin(pair.index)].assign(isc=True), X[X["t"].isin(pair.index)].assign(isc=False)])
        ec = S.event_contrast_cluster(both[y].to_numpy(), both["isc"].to_numpy(), both["entity"].to_numpy(), both["t"].to_numpy())
        row.update({"evt_b": ec["b"], "evt_se": ec["se"], "evt_t": ec["t"], "evt_p_one": ec["p_one"]})
        pm = S.paired_permutation(both[y].to_numpy(), both["isc"].to_numpy(), both["t"].to_numpy(), p.n_perm, p.perm_seed)
        row["perm_p_one"] = pm["p_one"]
        row.update(_attrition_bound(C, X, dC, dX, y, h, floor))
    return row, {"C": cC, "X": cX, "pair": pair}


def cohort_levels(ev: pd.DataFrame, sessions: np.ndarray, stage: str, h: int, outcome: str = "E_range") -> pd.DataFrame:
    y = f"{outcome}{h}"
    res, _, _ = _masks(ev, sessions, stage, h, outcome)
    out = []
    for name, col in (("C", "is_C"), ("N", "is_N"), ("P", "is_P")):
        d = ev[res & ev[col].to_numpy()]
        c = cohort(d, y)
        out.append({"stage": stage, "h": h, "outcome": outcome, "cohort": name, "n": len(d), "dates": len(c),
                    "mean_evt": float(d[y].mean()) if len(d) else np.nan,
                    "median_evt": float(d[y].median()) if len(d) else np.nan,
                    "mean_coh": float(c["m"].mean()) if len(c) else np.nan})
    return pd.DataFrame(out)


def signed_descriptive(ev: pd.DataFrame, sessions: np.ndarray, stage: str, h: int, p: Params = P) -> pd.DataFrame:
    """Signed forward move per cohort - DESCRIPTIVE ONLY: no test statistic, no p-value, never classifying."""
    y = f"E_sgn{h}"
    res, _, _ = _masks(ev, sessions, stage, h, "E_sgn")
    rows = []
    for name, col in (("C", "is_C"), ("N", "is_N"), ("P", "is_P")):
        d = ev[res & ev[col].to_numpy()]
        rows.append({"stage": stage, "h": h, "cohort": name, "n": len(d),
                     "mean_evt": float(d[y].mean()) if len(d) else np.nan,
                     "mean_coh": float(cohort(d, y)["m"].mean()) if len(d) else np.nan,
                     "frac_pos": float((d[y] > 0).mean()) if len(d) else np.nan})
    return pd.DataFrame(rows)


def by_year(d: pd.Series, sessions: np.ndarray) -> pd.DataFrame:
    yr = pd.DatetimeIndex(sessions[d.index.to_numpy()]).year
    g = d.groupby(yr)
    return pd.DataFrame({"n_dates": g.size(), "d_mean": g.mean(), "share_pos": g.apply(lambda s: float((s > 0).mean()))})


def concentration(d: pd.Series, sessions: np.ndarray, k: int = 10) -> dict:
    order = d.sort_values(ascending=False)
    top = order.iloc[:k]
    tot = float(d.sum())
    return {"n_dates": int(len(d)), "d_mean": float(d.mean()), "d_median": float(d.median()),
            "k": k, "d_mean_ex_top_k": float(order.iloc[k:].mean()) if len(d) > k else np.nan,
            "share_of_sum_top_k": float(top.sum() / tot) if tot != 0 else np.nan,
            "share_pos_dates": float((d > 0).mean()),
            "top_dates": [(str(sessions[int(t)])[:10], float(v)) for t, v in top.items()]}
