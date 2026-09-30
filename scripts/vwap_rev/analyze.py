"""VWAP-XREV analysis: per-(stage, side, horizon) cell statistics from an events table.

Everything here is a pure function of the events DataFrame (plus the fee model), so
robustness variants reuse it verbatim.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.vwap_rev import stats as S

HORIZONS = (5, 10, 15, 30, 60)
KAPPA_SCENARIOS = (0.0, 1.0, 2.75, 5.0)
BASE_KAPPA = 2.75
TICKET_RS = 500_000.0


def fee_bps(date) -> float:
    """Era-accurate intraday round-trip statutory cost in bp of notional (entry == exit value)."""
    from core.execution.equity.intraday_fees import round_trip_fees

    f = round_trip_fees(entry_value=TICKET_RS, exit_value=TICKET_RS, entry_date=date)
    return 1e4 * f.total / TICKET_RS


def add_costs(ev: pd.DataFrame, horizons=HORIZONS) -> pd.DataFrame:
    ev = ev.copy()
    fb = {d: fee_bps(d) for d in ev["date"].unique()}
    ev["fee_bp"] = ev["date"].map(fb)
    for H in horizons:
        for k in KAPPA_SCENARIOS:
            ev[f"N_h{H}_k{k}"] = ev[f"R_h{H}"] - ev["fee_bp"] - 2 * k
    return ev


def session_series(ev: pd.DataFrame, col: str) -> pd.Series:
    """One number per session: equal weight per event within the session."""
    return ev.dropna(subset=[col]).groupby("date")[col].mean()


def cell_stats(ev: pd.DataFrame, H: int, col: str | None = None) -> dict:
    col = col or f"R_h{H}"
    sub = ev.dropna(subset=[col])
    if len(sub) == 0:
        return {"n_events": 0}
    ss = session_series(sub, col)
    nw = S.nw_mean_test(ss.to_numpy())
    bb = S.block_bootstrap_mean(ss.to_numpy())
    tw = S.twoway_cluster_mean(sub[col].to_numpy(), sub["symbol"].to_numpy(), sub["date"].to_numpy())
    d = S.describe(sub[col].to_numpy())
    sd_s = float(ss.std(ddof=1)) if len(ss) > 1 else np.nan
    return {
        "n_events": int(len(sub)), "n_names": int(sub["symbol"].nunique()),
        "n_sessions": int(len(ss)),
        "mean_bp_event": d["mean"], "median_bp_event": d["median"], "sd_event": d["sd"],
        "skew": d["skew"], "kurt": d["kurt"], "frac_pos": d["frac_pos"],
        **{k: d[k] for k in d if k.startswith("q")},
        "session_mean_bp": nw["mean"], "session_sd_bp": sd_s, "nw_se": nw["se"], "nw_t": nw["t"],
        "p_one_nw": nw["p_one"], "p_two_nw": nw["p_two"], "nw_lag": nw["lag"], "ac1_sessions": nw["ac1"],
        "ci_lo": bb["ci_lo"], "ci_hi": bb["ci_hi"], "p_one_boot": bb["p_one"],
        "cluster_t": tw["t"], "cluster_p_one": tw["p_one"], "cluster_se": tw["se"],
        "cohen_d_session": nw["mean"] / sd_s if sd_s and np.isfinite(sd_s) else np.nan,
        "mde_bp_80": S.mde_session(sd_s, len(ss)),
    }


def side_extras(ev: pd.DataFrame, H: int) -> dict:
    """Outcome measures that are not the primary statistic (per event)."""
    sub = ev.dropna(subset=[f"R_h{H}"])
    if len(sub) == 0:
        return {}
    return {
        "mfe_mean": float(sub[f"MFE_h{H}"].mean()), "mfe_median": float(sub[f"MFE_h{H}"].median()),
        "mae_mean": float(sub[f"MAE_h{H}"].mean()), "mae_median": float(sub[f"MAE_h{H}"].median()),
        "frac_toward_vwap_static": float((sub[f"dstat_h{H}"] < 0).mean()),
        "frac_toward_vwap_moving": float((sub[f"dmov_h{H}"] < 0).mean()),
        "dstat_mean_bp": float(sub[f"dstat_h{H}"].mean()), "dstat_median_bp": float(sub[f"dstat_h{H}"].median()),
        "dmov_mean_bp": float(sub[f"dmov_h{H}"].mean()), "dmov_median_bp": float(sub[f"dmov_h{H}"].median()),
        "excess_mean_bp": float(sub[f"R_ex_h{H}"].mean()) if f"R_ex_h{H}" in sub else np.nan,
    }


def stage_table(ev: pd.DataFrame, stage: str, horizons=HORIZONS, with_holm: bool = True) -> pd.DataFrame:
    """All 10 primary cells (side x horizon) plus pooled-side secondary rows."""
    rows = []
    sub = ev[ev["stage"] == stage]
    for label, side_sel in (("up_disp_short", +1), ("down_disp_long", -1), ("pooled", 0)):
        e = sub if side_sel == 0 else sub[sub["side"] == side_sel]
        for H in horizons:
            r = {"stage": stage, "side": label, "H": H, **cell_stats(e, H), **side_extras(e, H)}
            rows.append(r)
    tab = pd.DataFrame(rows)
    if with_holm:
        prim = tab[tab["side"] != "pooled"]
        adj = S.holm({(r.side, r.H): r.p_one_nw for r in prim.itertuples()})
        tab["p_holm"] = [adj.get((r.side, r.H), np.nan) for r in tab.itertuples()]
    return tab


def cost_table(ev: pd.DataFrame, stage: str, horizons=HORIZONS) -> pd.DataFrame:
    ev = add_costs(ev[ev["stage"] == stage], horizons)
    rows = []
    for label, side_sel in (("up_disp_short", +1), ("down_disp_long", -1), ("pooled", 0)):
        e = ev if side_sel == 0 else ev[ev["side"] == side_sel]
        for H in horizons:
            for k in KAPPA_SCENARIOS:
                col = f"N_h{H}_k{k}"
                c = cell_stats(e, H, col)
                rows.append({"stage": stage, "side": label, "H": H, "kappa_bp_side": k,
                             "fee_bp_mean": float(e["fee_bp"].mean()) if len(e) else np.nan,
                             "gross_session_mean": cell_stats(e, H).get("session_mean_bp", np.nan),
                             "net_session_mean": c.get("session_mean_bp", np.nan),
                             "net_ci_lo": c.get("ci_lo", np.nan), "net_ci_hi": c.get("ci_hi", np.nan),
                             "net_p_one_nw": c.get("p_one_nw", np.nan),
                             "net_event_mean": c.get("mean_bp_event", np.nan),
                             "n_events": c.get("n_events", 0)})
    return pd.DataFrame(rows)


def concentration(ev: pd.DataFrame, H: int, top_ks=(1, 5, 10, 20)) -> dict:
    sub = ev.dropna(subset=[f"R_h{H}"])
    if len(sub) == 0:
        return {}
    ss = session_series(sub, f"R_h{H}")
    n_by_day = sub.groupby("date").size().sort_values(ascending=False)
    out = {"top10_event_days_share": float(n_by_day.head(10).sum() / n_by_day.sum()),
           "top10_names_share": float(sub["symbol"].value_counts().head(10).sum() / len(sub)),
           "max_events_one_session": int(n_by_day.iloc[0])}
    dev = ss.sort_values(ascending=False)          # drop the k MOST FAVOURABLE sessions
    for k in top_ks:
        drop = set(dev.head(k).index)
        rest = ss[~ss.index.isin(drop)]
        out[f"mean_ex_top{k}_sessions"] = float(rest.mean())
    return out
