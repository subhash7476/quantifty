"""BKV-1 cell tables: arms A/B/C/D, cohort-by-formation-date series, the paired B-C contrast, costs.

Units: every return here is in basis points (bp) of the entry-open notional, direction-signed so that
CONTINUATION of the breakout is positive. f = sign * (R_i - R_m) [market-excess]; raw = sign * R_i.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.execution.equity.delivery_fees import delivery_equity_fees
from scripts.breakout_vol import engine as G
from scripts.breakout_vol import stats as S
from scripts.breakout_vol.common import P, Params

SIDES = {"up": ("up", "dup"), "dn": ("dn", "ddn")}


def side_frame(ev: pd.DataFrame, N: int, side: str) -> pd.DataFrame:
    return ev[(ev["N"] == N) & ev["kind"].isin(SIDES[side])]


def cohort(df: pd.DataFrame, col: str) -> pd.DataFrame:
    g = df.groupby("t")[col].agg(["mean", "size"])
    return g.rename(columns={"mean": "m", "size": "n"})


def paired_series(cb: pd.DataFrame, cc: pd.DataFrame) -> pd.DataFrame:
    j = cb.join(cc, lsuffix="_B", rsuffix="_C", how="inner")
    j["d"] = j["m_B"] - j["m_C"]
    return j


def _arm_test(series: pd.DataFrame, lag: int) -> dict:
    if len(series) == 0:
        return {"n": 0, "mean": np.nan, "t": np.nan, "p_one": np.nan}
    r = S.nw_gap_test(series["m"].to_numpy(), series.index.to_numpy(), lag)
    return {"n": r["n"], "mean": r["mean"], "t": r["t"], "p_one": r["p_one"]}


def cell_row(ev: pd.DataFrame, sessions: np.ndarray, stage: str, N: int, H: int, side: str,
             p: Params = P, extras: bool = True) -> tuple[dict, dict]:
    """One (stage, N, H, side) cell. Returns (row, series-dict for the arithmetic ledger)."""
    f = f"f{H}"
    sf = side_frame(ev, N, side)
    inst = sf[G.in_stage(sf, sessions, stage, H)]
    dropped = sf[G.dropped_in_stage(sf, sessions, stage, H)]
    arms = {"A": inst[inst["arm"].isin(["B", "C"])], "B": inst[inst["arm"] == "B"],
            "C": inst[inst["arm"] == "C"], "D": inst[inst["arm"] == "D"]}
    coh = {k: cohort(v, f) for k, v in arms.items()}
    pair = paired_series(coh["B"], coh["C"])
    row = {"stage": stage, "N": N, "H": H, "side": side}
    for k, v in arms.items():
        row[f"n_{k}"] = len(v)
        row[f"dates_{k}"] = len(coh[k])
        row[f"mean_{k}_evt"] = float(v[f].mean()) if len(v) else np.nan
        row[f"mean_{k}_raw_evt"] = float(v[f"raw{H}"].mean()) if len(v) else np.nan
        tst = _arm_test(coh[k], H)
        row[f"mean_{k}_coh"], row[f"t_{k}"], row[f"p_{k}"] = tst["mean"], tst["t"], tst["p_one"]
    row["n_pair_dates"] = len(pair)
    row["n_terminal_B"] = int((arms["B"][f"status{H}"] == G.ST_TERMINAL).sum())
    row["n_terminal_C"] = int((arms["C"][f"status{H}"] == G.ST_TERMINAL).sum())
    row["n_dropped_B"] = int((dropped["arm"] == "B").sum())
    row["n_dropped_C"] = int((dropped["arm"] == "C").sum())
    if len(pair) >= 3:
        c = S.nw_gap_test(pair["d"].to_numpy(), pair.index.to_numpy(), H)
        row.update({"d_mean": c["mean"], "d_se": c["se"], "d_t": c["t"], "d_p_one": c["p_one"], "d_lag": H,
                    "d_mde80": S.mde_one_sided(c["se"], p.alpha)})
        wsum = (pair["n_B"] + pair["n_C"])
        row["d_mean_evtwt"] = float((pair["d"] * wsum).sum() / wsum.sum())
    else:
        row.update({"d_mean": np.nan, "d_se": np.nan, "d_t": np.nan, "d_p_one": np.nan, "d_lag": H,
                    "d_mde80": np.nan, "d_mean_evtwt": np.nan})
    if extras and len(pair) >= 3:
        bb = S.block_bootstrap_mean(pair["d"].to_numpy(), block=H + 1, n_boot=p.n_boot, seed=p.boot_seed)
        row["d_ci_lo"], row["d_ci_hi"] = bb["ci_lo"], bb["ci_hi"]
        both = pd.concat([arms["B"].assign(isb=True), arms["C"].assign(isb=False)])
        ec = S.event_contrast_cluster(both[f].to_numpy(), both["isb"].to_numpy(), both["entity"].to_numpy(), both["t"].to_numpy())
        row.update({"evt_b": ec["b"], "evt_se": ec["se"], "evt_t": ec["t"], "evt_p_one": ec["p_one"]})
        both_pair = both[both["t"].isin(pair.index)]
        pm = S.paired_permutation(both_pair[f].to_numpy(), both_pair["isb"].to_numpy(), both_pair["t"].to_numpy(),
                                  p.n_perm, p.perm_seed)
        row["perm_p_one"], row["perm_null_sd"] = pm["p_one"], pm["null_sd"]
        row.update(_attrition_bound(arms, dropped, coh, H, f, p))
    return row, {"B": coh["B"], "C": coh["C"], "pair": pair, "D": coh["D"], "A": coh["A"]}


def _attrition_bound(arms: dict, dropped: pd.DataFrame, coh: dict, H: int, f: str, p: Params) -> dict:
    """Worst-case bound for the claim B > C: dropped B events -> the smallest retained B value, dropped C
    events -> the largest retained C value, both landing on their own formation date. Terminal windows are
    replaced only if the replacement is worse for the claim than the observed value (M1c v1.3 F-1 rule)."""
    b, c = arms["B"], arms["C"]
    if len(b) == 0 or len(c) == 0:
        return {"bound_d_mean": np.nan, "bound_d_p_one": np.nan}
    m_b, M_c = float(b[f].min()), float(c[f].max())
    term_b = b[b[f"status{H}"] == G.ST_TERMINAL]
    term_c = c[c[f"status{H}"] == G.ST_TERMINAL]
    b2 = b[["t", f]].copy()
    b2.loc[term_b.index, f] = np.minimum(term_b[f], m_b)
    c2 = c[["t", f]].copy()
    c2.loc[term_c.index, f] = np.maximum(term_c[f], M_c)
    b2 = pd.concat([b2, pd.DataFrame({"t": dropped.loc[dropped["arm"] == "B", "t"], f: m_b})])
    c2 = pd.concat([c2, pd.DataFrame({"t": dropped.loc[dropped["arm"] == "C", "t"], f: M_c})])
    pr = paired_series(cohort(b2, f), cohort(c2, f))
    if len(pr) < 3:
        return {"bound_d_mean": np.nan, "bound_d_p_one": np.nan}
    r = S.nw_gap_test(pr["d"].to_numpy(), pr.index.to_numpy(), H)
    return {"bound_d_mean": r["mean"], "bound_d_p_one": r["p_one"]}


# ---------------------------------------------------------------- costs
_fee_cache: dict = {}


def fee_bp(date, side: str, notional: float) -> float:
    key = (pd.Timestamp(date).date(), side, notional)
    if key not in _fee_cache:
        _fee_cache[key] = 1e4 * delivery_equity_fees(side=side, trade_value=notional, trade_date=key[0]).total / notional
    return _fee_cache[key]


def event_fee_bp(df: pd.DataFrame, H: int, notional: float) -> np.ndarray:
    """Statutory + DP round-trip fee in bp of notional for each event: BUY on the entry date, SELL on the exit date."""
    ent = pd.to_datetime(df["entry_date"]).dt.date.to_numpy()
    ext = pd.to_datetime(df[f"exit_date{H}"]).dt.date.to_numpy()
    return np.array([fee_bp(a, "BUY", notional) + fee_bp(b, "SELL", notional) for a, b in zip(ent, ext)])


def cost_rows(ev: pd.DataFrame, sessions: np.ndarray, stage: str, N: int, H: int, side: str, arm: str,
              p: Params = P) -> list[dict]:
    sf = side_frame(ev, N, side)
    inst = sf[G.in_stage(sf, sessions, stage, H)]
    arr = inst[inst["arm"].isin(["B", "C"])] if arm == "A" else inst[inst["arm"] == arm]
    out = []
    if len(arr) == 0:
        return out
    fee = event_fee_bp(arr, H, p.notional)
    raw = arr[f"raw{H}"].to_numpy()
    for k in p.kappas_bp:
        net = raw - fee - 2 * k
        coh = pd.DataFrame({"t": arr["t"].to_numpy(), "net": net}).groupby("t")["net"].mean()
        out.append({"stage": stage, "N": N, "H": H, "side": side, "arm": arm, "kappa_bp": k, "n": len(arr),
                    "gross_raw_evt_bp": float(raw.mean()), "fee_bp": float(fee.mean()),
                    "net_evt_bp": float(net.mean()), "net_coh_bp": float(coh.mean()),
                    "breakeven_kappa_bp": float((raw.mean() - fee.mean()) / 2)})
    return out
