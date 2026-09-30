"""BKV-1 post-primary disclosure analyses R1-R9 (protocol section 13). NOT frozen, NOT classifying.

Every table is a description of where the frozen primary result lives; none can change the label, and none is
promoted. Variants reuse the frozen engine/analysis code; only the declared knob differs.
"""
from __future__ import annotations

import dataclasses
import json

import duckdb
import numpy as np
import pandas as pd

from scripts.breakout_vol import analyze as A
from scripts.breakout_vol import common as C
from scripts.breakout_vol import engine as G
from scripts.breakout_vol import stats as S
from scripts.breakout_vol.common import P

OUT = C.OUT_DIR / "results"
STAGES = ("TRAIN", "VAL")


def events_variant(pn: G.Panel, p=P, hl: bool = False, declust: bool = True) -> pd.DataFrame:
    """detect_events with declared knobs: hl=True -> range from highs/lows (R1); declust=False -> every flag (R3)."""
    if declust and not hl:
        return G.detect_events(pn, p)
    rows = []
    for n in p.range_n:
        m = G.detect_masks(pn, n, p)
        if hl:
            Hd, Ld = G._df(pn.H), G._df(pn.L)
            mx = Hd.rolling(n).max().shift(1).to_numpy().T
            mn = Ld.rolling(n).min().shift(1).to_numpy().T
            with np.errstate(invalid="ignore"):
                up, dn = pn.C > mx, pn.C < mn
            q = p.onset_quiet
            up_on = up & (G._prior_sum(up, q) == 0) if declust else up
            dn_on = dn & (G._prior_sum(dn, q) == 0) if declust else dn
            quiet_vol = G._prior_sum(m["abn"], q) == 0
            cprev = G._df(pn.C).shift(1).to_numpy().T
            d_evt = m["abn"] & ~up & ~dn & quiet_vol
            with np.errstate(invalid="ignore"):
                m.update({"up_on": up_on & m["elig"], "dn_on": dn_on & m["elig"], "mx": mx, "mn": mn,
                          "dup": d_evt & (pn.C > cprev) & m["elig"], "ddn": d_evt & (pn.C < cprev) & m["elig"]})
        else:
            m["up_on"], m["dn_on"] = m["up"] & m["elig"], m["dn"] & m["elig"]
        for kind, key in (("up", "up_on"), ("dn", "dn_on"), ("dup", "dup"), ("ddn", "ddn")):
            ei, ti = np.nonzero(m[key])
            ref = m["mx"] if kind in ("up", "dup") else m["mn"]
            rows.append(pd.DataFrame({"entity": np.asarray(pn.entities, dtype=object)[ei], "e": ei, "t": ti,
                                      "date": pn.sessions[ti], "N": n, "kind": kind, "close": pn.C[ei, ti],
                                      "prev_close": pn.C[ei, ti - 1], "ref_level": ref[ei, ti] if kind in ("up", "dn") else np.nan,
                                      "vol": pn.V[ei, ti], "med_vol": m["med"][ei, ti], "av": m["av"][ei, ti],
                                      "abn": m["abn"][ei, ti]}))
    ev = pd.concat(rows, ignore_index=True)
    ev["arm"] = np.where(ev["kind"].isin(["up", "dn"]), np.where(ev["abn"], "B", "C"), "D")
    return ev


def primary_table(ev: pd.DataFrame, sessions, stage: str, p=P, tag: str = "") -> pd.DataFrame:
    rows = []
    for N in p.range_n:
        for H in p.horizons:
            for side in ("up", "dn"):
                r, _ = A.cell_row(ev, sessions, stage, N, H, side, p, extras=False)
                rows.append({"variant": tag, "stage": stage, "N": N, "H": H, "side": side, "n_B": r["n_B"], "n_C": r["n_C"],
                             "pair_dates": r["n_pair_dates"], "d_mean": r["d_mean"], "d_t": r["d_t"], "d_p_one": r["d_p_one"],
                             "mean_B_evt": r["mean_B_evt"], "mean_C_evt": r["mean_C_evt"]})
    return pd.DataFrame(rows)


def run_variant(pn, tag, p=P, **kw):
    ev = events_variant(pn, p, **kw)
    ev, _ = G.attach_outcomes(pn, ev, p)
    return ev, pd.concat([primary_table(ev, pn.sessions, st, p, tag) for st in STAGES])


def ca_flags(ev: pd.DataFrame, pn: G.Panel) -> pd.Series:
    """True if any bonus/split/special-dividend factor of any symbol of the entity has ex_date in [t-83, exit_t20+1]."""
    con = duckdb.connect(str(C.EQUITY_DB), read_only=True)
    sy = con.execute("SELECT entity, symbol FROM symbol_entity_intervals").df()
    fac = con.execute("SELECT symbol, ex_date FROM adjustment_factors WHERE action_type IN ('BONUS','SPLIT','SPECIAL_DIVIDEND')").df()
    con.close()
    j = sy.merge(fac, on="symbol")
    j["ex_date"] = pd.to_datetime(j["ex_date"])
    by = {e: np.sort(g["ex_date"].to_numpy()) for e, g in j.groupby("entity")}
    sess = pd.to_datetime(pn.sessions)
    lo = sess[np.maximum(ev["t"].to_numpy() - 83, 0)].to_numpy()
    hi = sess[np.minimum(np.where(ev["exit_t20"].to_numpy() >= 0, ev["exit_t20"].to_numpy() + 1, ev["t"].to_numpy() + 21), len(sess) - 1)].to_numpy()
    out = np.zeros(len(ev), bool)
    for i, (e, a, b) in enumerate(zip(ev["entity"].to_numpy(), lo, hi)):
        x = by.get(e)
        if x is not None:
            k = np.searchsorted(x, a, side="left")
            out[i] = k < len(x) and x[k] <= b
    return pd.Series(out, index=ev.index)


def main() -> None:
    pn = G.load_panel("dev")
    base = pd.read_parquet(OUT / "events_TRAIN.parquet"), pd.read_parquet(OUT / "events_VAL.parquet")
    ev_all = pd.concat(base, ignore_index=True)
    tabs = {}
    prim = pd.concat([primary_table(ev_all, pn.sessions, st, P, "PRIMARY") for st in STAGES])
    tabs["PRIMARY"] = prim
    # R1 high/low range; R3 non-declustered; R2 AV thresholds
    for tag, kw, p in (("R1_highlow_range", dict(hl=True), P), ("R3_non_declustered", dict(declust=False), P),
                       ("R2_av1.5", {}, dataclasses.replace(P, av_threshold=1.5)),
                       ("R2_av3.0", {}, dataclasses.replace(P, av_threshold=3.0))):
        _, t = run_variant(pn, tag, p, **kw)
        tabs[tag] = t
    # R6 turnover-based abnormal volume
    pn_to = dataclasses.replace(pn, V=pn.TO.copy())
    _, t = run_variant(pn_to, "R6_turnover_AV")
    tabs["R6_turnover_AV"] = t
    # R4 exclude events with a corporate-action factor in the span
    flags = ca_flags(ev_all, pn)
    ev_ca = ev_all[~flags.to_numpy()]
    tabs["R4_no_CA_in_span"] = pd.concat([primary_table(ev_ca, pn.sessions, st, P, "R4_no_CA_in_span") for st in STAGES])
    share_ca = float(flags.mean())
    # R8 exclude terminal windows
    ev_nt = ev_all.copy()
    for h in P.horizons:
        ev_nt.loc[ev_nt[f"status{h}"] == G.ST_TERMINAL, f"f{h}"] = np.nan
    tabs["R8_no_terminal"] = pd.concat([primary_table(ev_nt, pn.sessions, st, P, "R8_no_terminal") for st in STAGES])
    allv = pd.concat(tabs.values(), ignore_index=True)
    allv.to_csv(OUT / "post_primary_variants.csv", index=False)

    # R5 decomposition (VAL/TRAIN, raw direction-signed means, bp): R starts at the t+1 OPEN, so the overnight gap
    # G = O[t+1]/C[t]-1 is NOT inside R. From the day-t close the move is (1+G)(1+R)-1 = gap + post-open (+ cross term).
    gap_rows = []
    for st in STAGES:
        lo, hi = G.stage_bounds(pn.sessions, st)
        for N in P.range_n:
            for side, kinds, sg in (("up", ("up",), 1), ("dn", ("dn",), -1)):
                e = ev_all[(ev_all["N"] == N) & ev_all["kind"].isin(kinds) & (ev_all["t"] >= lo) & (ev_all["t"] <= hi) & ev_all["gap"].notna()]
                e = e.assign(gap_bp=1e4 * sg * e["gap"], post_open5=e["raw5"], post_open20=e["raw20"],
                             from_close5=1e4 * sg * ((1 + e["gap"]) * (1 + e["R5"]) - 1),
                             from_close20=1e4 * sg * ((1 + e["gap"]) * (1 + e["R20"]) - 1))
                for col in ("gap_bp", "post_open5", "from_close5", "post_open20", "from_close20"):
                    b, c = e[e["arm"] == "B"], e[e["arm"] == "C"]
                    gap_rows.append({"stage": st, "N": N, "side": side, "quantity": col, "n_B": len(b), "n_C": len(c),
                                     "mean_B": b[col].mean(), "mean_C": c[col].mean(), "diff_B_minus_C": b[col].mean() - c[col].mean()})
    pd.DataFrame(gap_rows).to_csv(OUT / "post_primary_gap_decomposition.csv", index=False)

    # R7 by calendar year, paired contrast, VAL+TRAIN
    yr_rows = []
    for st in STAGES:
        for N in P.range_n:
            for H in P.horizons:
                for side in ("up", "dn"):
                    sf = A.side_frame(ev_all, N, side)
                    inst = sf[G.in_stage(sf, pn.sessions, st, H)]
                    inst = inst.assign(year=pd.to_datetime(inst["date"]).dt.year)
                    for y, g in inst.groupby("year"):
                        cb = A.cohort(g[g["arm"] == "B"], f"f{H}"); cc = A.cohort(g[g["arm"] == "C"], f"f{H}")
                        pr = A.paired_series(cb, cc)
                        yr_rows.append({"stage": st, "N": N, "H": H, "side": side, "year": int(y), "n_pair_dates": len(pr),
                                        "d_mean": pr["d"].mean() if len(pr) else np.nan})
    pd.DataFrame(yr_rows).to_csv(OUT / "post_primary_by_year.csv", index=False)

    # R9 penetration-depth terciles: cuts fixed once per (N, side) from pooled TRAIN u VAL A-arm events
    t_rows = []
    for N in P.range_n:
        for side, kinds in (("up", ("up",)), ("dn", ("dn",))):
            ea = ev_all[(ev_all["N"] == N) & ev_all["kind"].isin(kinds)].copy()
            ea["depth"] = (ea["close"] / ea["ref_level"] - 1).abs() * 1e4
            for H in P.horizons:
                res = pd.concat([ea[G.in_stage(ea, pn.sessions, st, H)] for st in STAGES])
                cuts = np.quantile(res["depth"], [1 / 3, 2 / 3])
                for st in STAGES:
                    s_ = ea[G.in_stage(ea, pn.sessions, st, H)]
                    tier = np.digitize(s_["depth"].to_numpy(), cuts)
                    for k in range(3):
                        g = s_[tier == k]
                        cb = A.cohort(g[g["arm"] == "B"], f"f{H}"); cc = A.cohort(g[g["arm"] == "C"], f"f{H}")
                        pr = A.paired_series(cb, cc)
                        r = S.nw_gap_test(pr["d"].to_numpy(), pr.index.to_numpy(), H) if len(pr) >= 3 else {"mean": np.nan, "t": np.nan, "p_one": np.nan}
                        t_rows.append({"stage": st, "N": N, "H": H, "side": side, "tercile": k + 1,
                                       "depth_lo_bp": float(cuts[k - 1]) if k else 0.0, "depth_hi_bp": float(cuts[k]) if k < 2 else np.inf,
                                       "share_B": float((g["arm"] == "B").mean()) if len(g) else np.nan, "n_B": int((g["arm"] == "B").sum()),
                                       "n_C": int((g["arm"] == "C").sum()), "pair_dates": len(pr), "d_mean": r["mean"], "d_t": r["t"], "d_p_one": r["p_one"]})
    pd.DataFrame(t_rows).to_csv(OUT / "post_primary_depth_terciles.csv", index=False)
    (OUT / "post_primary_meta.json").write_text(json.dumps({"share_events_with_CA_in_span": share_ca}, indent=2))
    print("done; CA-in-span share", round(share_ca, 4))


if __name__ == "__main__":
    main()
