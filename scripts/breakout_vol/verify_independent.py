"""BKV-1 independent verification. Nothing here imports the engine's detection/outcome logic.

  VP1  pure-SQL re-derivation (DuckDB window functions) of the calendar, membership, flags, arms, entry/exit,
       benchmark and f for EVERY event, compared with the event ledger one-to-one.
  VP2  raw as-traded re-derivation (plain Python loops over `equity_bhavcopy`) of a seeded event sample.
  VP3  the statistics: cohort means from the ledger with dict arithmetic; Newey-West by a pure-Python path and
       by statsmodels' S_hac_simple kernel; compared with the cell table.
  VP4  the accounting identities and the benchmark identity.
  VP5  volume checks (adjusted vs raw identity; turnover-based agreement).
  VP6  the fee arithmetic for one trade written out by hand.

Any disagreement beyond the stated tolerance sets `stop=True` in the output: the protocol says STOP, investigate,
do not choose a number.
"""
from __future__ import annotations

import json
import math
import sys

import duckdb
import numpy as np
import pandas as pd

from scripts.breakout_vol import common as C
from scripts.breakout_vol.common import P



def _res():
    return C.OUT_DIR / "results"
TOL = 1e-9


# ------------------------------------------------------------------ VP1
def _sql_events(tag: str) -> tuple[duckdb.DuckDBPyConnection, int]:
    con = duckdb.connect()
    pan, cal, mem = (str(C.OUT_DIR / f"{n}_{tag}.parquet").replace("\\", "/") for n in ("panel", "calendar", "membership"))
    con.execute(f"""
      CREATE TABLE cal0 AS SELECT CAST(trade_date AS DATE) d, COALESCE(n_symbols,0) n, tot_turnover_eq tt FROM read_parquet('{cal}');
      CREATE TABLE cal1 AS SELECT d, tt, median(tt) OVER (ORDER BY d ROWS BETWEEN 10 PRECEDING AND 10 FOLLOWING) med
                           FROM cal0 WHERE n >= {P.calendar_min_symbols} AND dayofweek(d) BETWEEN 1 AND 5;
      CREATE TABLE cal AS SELECT d, row_number() OVER (ORDER BY d) - 1 AS sidx FROM cal1 WHERE tt / med >= {P.short_session_ratio};
      CREATE TABLE p AS SELECT pa.entity, c.sidx, c.d, pa.open o, pa.high h, pa.low l, pa.close c_, pa.volume v, pa.turnover tv
                        FROM read_parquet('{pan}') pa JOIN cal c ON CAST(pa.trade_date AS DATE) = c.d
                        WHERE pa.open > 0 AND pa.high > 0 AND pa.low > 0 AND pa.close > 0 AND pa.volume > 0;
      CREATE TABLE rb AS SELECT DISTINCT CAST(rebalance_date AS DATE) r FROM read_parquet('{mem}');
      CREATE TABLE dr AS SELECT c.sidx, c.d, (SELECT max(r) FROM rb WHERE r < c.d) AS r FROM cal c;
      CREATE TABLE mem AS SELECT dr.sidx, m.entity FROM dr JOIN read_parquet('{mem}') m ON CAST(m.rebalance_date AS DATE) = dr.r;
    """)
    T = con.execute("SELECT max(sidx) + 1 FROM cal").fetchone()[0]
    return con, T


def vp1_sql_reconcile(stage: str, tag: str) -> dict:
    ledger = pd.read_parquet(_res() / f"events_{stage}.parquet")
    con, T = _sql_events(tag)
    lo, hi = int(ledger["t"].min()), int(ledger["t"].max())
    from scripts.breakout_vol import engine as G
    pn_dates = con.execute("SELECT d FROM cal ORDER BY sidx").df()["d"].to_numpy().astype("datetime64[D]")
    lo, hi = G.stage_bounds(pn_dates, stage)
    out = {"stage": stage, "tables": {}}
    sql_events = []
    for N in P.range_n:
        con.execute(f"""
          CREATE OR REPLACE TABLE f{N} AS
          SELECT *, coalesce(up::int,0) AS upi, coalesce(dn::int,0) AS dni, coalesce(abn::int,0) AS abni FROM (
            SELECT entity, sidx, d, o, c_, v, cprev, med, mx, mn, cnt84, c_ > mx AS up, c_ < mn AS dn, v >= {P.av_threshold} * med AS abn FROM (
              SELECT entity, sidx, d, o, c_, v, count(*) OVER w84 AS cnt84, lag(c_) OVER wl AS cprev,
                     median(v) OVER wv AS med, max(c_) OVER wn AS mx, min(c_) OVER wn AS mn
              FROM p
              WINDOW w84 AS (PARTITION BY entity ORDER BY sidx RANGE BETWEEN {P.lookback_required - 1} PRECEDING AND CURRENT ROW),
                     wl AS (PARTITION BY entity ORDER BY sidx),
                     wv AS (PARTITION BY entity ORDER BY sidx RANGE BETWEEN {P.vol_window} PRECEDING AND 1 PRECEDING),
                     wn AS (PARTITION BY entity ORDER BY sidx RANGE BETWEEN {N} PRECEDING AND 1 PRECEDING)));
          CREATE OR REPLACE TABLE q{N} AS
          SELECT *, sum(upi) OVER wq AS qup, sum(dni) OVER wq AS qdn, sum(abni) OVER wq AS qabn FROM f{N}
          WINDOW wq AS (PARTITION BY entity ORDER BY sidx RANGE BETWEEN {P.onset_quiet} PRECEDING AND 1 PRECEDING);
          CREATE OR REPLACE TABLE e{N} AS
          SELECT q{N}.entity, q{N}.sidx AS t, {N} AS N,
                 CASE WHEN up AND coalesce(qup,0)=0 THEN 'up'
                      WHEN dn AND coalesce(qdn,0)=0 THEN 'dn'
                      WHEN abn AND NOT up AND NOT dn AND coalesce(qabn,0)=0 AND c_ > cprev THEN 'dup'
                      WHEN abn AND NOT up AND NOT dn AND coalesce(qabn,0)=0 AND c_ < cprev THEN 'ddn' END AS kind,
                 abn, c_ AS close, v AS vol, med AS med_vol, v/med AS av
          FROM q{N} JOIN mem USING (entity, sidx)
          WHERE cnt84 = {P.lookback_required};
        """)
        # an event can be BOTH an 'up' onset and (impossible) a D: kinds are exclusive by construction; up and dn cannot coexist.
        sql_events.append(con.execute(f"SELECT * FROM e{N} WHERE kind IS NOT NULL AND t BETWEEN {lo} AND {hi}").df())
    sev = pd.concat(sql_events, ignore_index=True)
    for H in P.horizons:
        con.execute(f"""
          CREATE OR REPLACE TABLE w{H} AS
          SELECT entity, sidx, c, mn, mx, lastv,
                 CASE WHEN sidx + {H} > {T - 1} THEN 3 WHEN c = {H} THEN 0
                      WHEN c BETWEEN 1 AND {H - 1} AND mn = sidx + 1 AND mx = sidx + c AND lastv = sidx + c
                           AND {T - 1} - (sidx + c + 1) >= {P.terminal_guard} THEN 1 ELSE 2 END AS status
          FROM (SELECT entity, sidx, count(*) OVER wf AS c, min(sidx) OVER wf AS mn, max(sidx) OVER wf AS mx,
                       max(sidx) OVER (PARTITION BY entity) AS lastv
                FROM p WINDOW wf AS (PARTITION BY entity ORDER BY sidx RANGE BETWEEN 1 FOLLOWING AND {H} FOLLOWING));
          CREATE OR REPLACE TABLE r{H} AS
          SELECT w.entity, w.sidx, w.status, x.c_ / e1.o - 1 AS R
          FROM w{H} w JOIN p e1 ON e1.entity = w.entity AND e1.sidx = w.sidx + 1
                      JOIN p x ON x.entity = w.entity AND x.sidx = w.sidx + CASE WHEN w.status = 0 THEN {H} ELSE w.c END
          WHERE w.status IN (0, 1);
          CREATE OR REPLACE TABLE m{H} AS
          SELECT r.sidx, avg(R) AS Rm, count(*) AS nb FROM r{H} r JOIN mem USING (entity, sidx) GROUP BY 1 HAVING count(*) >= {P.min_bench_names};
        """)
        st = con.execute(f"SELECT entity, sidx AS t, status, R FROM r{H} UNION ALL SELECT entity, sidx, status, NULL FROM w{H} WHERE status IN (2,3)").df()
        st = st.rename(columns={"status": f"sql_status{H}", "R": f"sql_R{H}"})
        sev = sev.merge(st, on=["entity", "t"], how="left")
        rm = con.execute(f"SELECT sidx AS t, Rm AS sql_Rm{H}, nb AS sql_nb{H} FROM m{H}").df()
        sev = sev.merge(rm, on="t", how="left")
    sign = sev["kind"].map({"up": 1, "dn": -1, "dup": 1, "ddn": -1})
    for H in P.horizons:
        sev[f"sql_f{H}"] = 1e4 * sign * (sev[f"sql_R{H}"] - sev[f"sql_Rm{H}"])
    sev["sql_arm"] = np.where(sev["kind"].isin(["up", "dn"]), np.where(sev["abn"], "B", "C"), "D")
    key = ["entity", "t", "N", "kind"]
    m = ledger.merge(sev, on=key, how="outer", suffixes=("", "_sql"), indicator=True)
    out["ledger_events"], out["sql_events"] = int(len(ledger)), int(len(sev))
    out["only_in_ledger"] = int((m["_merge"] == "left_only").sum())
    out["only_in_sql"] = int((m["_merge"] == "right_only").sum())
    both = m[m["_merge"] == "both"]
    out["arm_mismatch"] = int((both["arm"] != both["sql_arm"]).sum())
    out["av_max_abs_diff"] = float((both["av"] - both["av_sql"]).abs().max())
    for H in P.horizons:
        stat_l, stat_s = both[f"status{H}"], both[f"sql_status{H}"]
        out[f"status_mismatch_H{H}"] = int((stat_l != stat_s).sum())
        res = both[both[f"status{H}"].isin([0, 1]) & both[f"sql_status{H}"].isin([0, 1])]
        out[f"R_max_abs_diff_H{H}"] = float((res[f"R{H}"] - res[f"sql_R{H}"]).abs().max())
        out[f"Rm_max_abs_diff_H{H}"] = float((res[f"Rm{H}"] - res[f"sql_Rm{H}"]).abs().max())
        out[f"f_max_abs_diff_bp_H{H}"] = float((res[f"f{H}"] - res[f"sql_f{H}"]).abs().max())
        out[f"n_compared_H{H}"] = int(len(res))
    ok = (out["only_in_ledger"] == 0 and out["only_in_sql"] == 0 and out["arm_mismatch"] == 0 and
          all(out[f"status_mismatch_H{H}"] == 0 for H in P.horizons) and out["av_max_abs_diff"] < 1e-9 and
          all(out[f"f_max_abs_diff_bp_H{H}"] < 1e-6 for H in P.horizons))
    out["pass"] = bool(ok)
    # calendar reconciliation
    out["sql_sessions"] = int(T)
    return out


# ------------------------------------------------------------------ VP2
def vp2_raw_sample(stage: str, tag: str, n_per_cell: int = 3, seed: int = 20260930) -> dict:
    """Plain-Python re-derivation of seeded events from the RAW as-traded table (no adjusted view, no numpy).
    Events with any adjustment_factors row (bonus/split/special dividend) in the span are skipped: for them the
    as-traded and adjusted series differ by construction (counted and reported)."""
    from scripts.breakout_vol import engine as G
    led = pd.read_parquet(_res() / f"events_{stage}.parquet")
    led = led[led["status5"].isin([0]) & led["status20"].isin([0])]
    cal = pd.read_parquet(C.OUT_DIR / f"calendar_{tag}.parquet")
    sessions, _ = G.regular_calendar(cal)
    sess = [pd.Timestamp(x).date() for x in sessions]
    panel = pd.read_parquet(C.OUT_DIR / f"panel_{tag}.parquet", columns=["entity", "trade_date", "symbol"])
    con = duckdb.connect(str(C.EQUITY_DB), read_only=True)
    rng = np.random.default_rng(seed)
    picks = []
    for (N, kind, arm), g in led.groupby(["N", "kind", "arm"]):
        picks.append(g.sample(min(n_per_cell, len(g)), random_state=int(rng.integers(1 << 30))))
    picks = pd.concat(picks)
    rows, skipped_ca, skipped_sym = [], 0, 0
    for r in picks.itertuples():
        t, N = int(r.t), int(r.N)
        d0, d1 = sess[t - 83], sess[int(r.exit_t20)]
        syms = panel[(panel["entity"] == r.entity) & (pd.to_datetime(panel["trade_date"]).dt.date >= d0) &
                     (pd.to_datetime(panel["trade_date"]).dt.date <= d1)]["symbol"].unique()
        if len(syms) != 1:
            skipped_sym += 1
            continue
        sym = syms[0]
        ca = con.execute("SELECT count(*) FROM adjustment_factors WHERE symbol = ? AND ex_date BETWEEN ? AND ?",
                         [sym, d0, d1]).fetchone()[0]
        if ca:
            skipped_ca += 1
            continue
        raw = con.execute("""SELECT trade_date, open, close, volume, turnover FROM equity_bhavcopy
                             WHERE symbol = ? AND series IN ('EQ','BE') AND trade_date BETWEEN ? AND ?
                             ORDER BY trade_date, turnover DESC""", [sym, d0, d1]).fetchall()
        by = {}
        for td, o, c, v, tv in raw:
            by.setdefault(td, (o, c, v, tv))
        closes = [by[sess[t - k]][1] for k in range(N, 0, -1)]                 # t-N .. t-1
        vols = sorted(by[sess[t - k]][2] for k in range(1, 21))               # t-20 .. t-1
        med = (vols[9] + vols[10]) / 2
        av = by[sess[t]][2] / med
        ref = max(closes) if r.kind in ("up",) else min(closes) if r.kind in ("dn",) else float("nan")
        entry, exit5, exit20 = by[sess[t + 1]][0], by[sess[t + 5]][1], by[sess[t + 20]][1]
        rows.append({"entity": r.entity, "date": str(sess[t]), "N": N, "kind": r.kind, "arm": r.arm,
                     "close_t": by[sess[t]][1], "ref_level": ref, "ledger_ref": r.ref_level,
                     "vol_t": by[sess[t]][2], "median_prior20": med, "av_raw": av, "av_ledger": r.av,
                     "entry_open": entry, "exit_close_h5": exit5, "exit_close_h20": exit20,
                     "R5_raw": exit5 / entry - 1, "R5_ledger": r.R5, "R20_raw": exit20 / entry - 1, "R20_ledger": r.R20})
    con.close()
    d = pd.DataFrame(rows)
    out = {"stage": stage, "sampled": int(len(picks)), "verified": int(len(d)), "skipped_ca": skipped_ca,
           "skipped_multi_symbol": skipped_sym}
    if len(d):
        out["av_max_rel_diff"] = float(((d["av_raw"] - d["av_ledger"]).abs() / d["av_ledger"]).max())
        out["R5_max_abs_diff"] = float((d["R5_raw"] - d["R5_ledger"]).abs().max())
        out["R20_max_abs_diff"] = float((d["R20_raw"] - d["R20_ledger"]).abs().max())
        brk = d[d["kind"].isin(["up", "dn"])]
        out["ref_max_abs_diff"] = float((brk["ref_level"] - brk["ledger_ref"]).abs().max()) if len(brk) else 0.0
        out["pass"] = bool(out["av_max_rel_diff"] < 1e-9 and out["R5_max_abs_diff"] < 1e-9 and
                           out["R20_max_abs_diff"] < 1e-9 and out["ref_max_abs_diff"] < 1e-9)
    else:
        out["pass"] = False
    d.to_csv(_res() / f"vp2_raw_sample_{stage}.csv", index=False)
    return out


# ------------------------------------------------------------------ VP3
def _manual_nw(vals: list, pos: list, lag: int) -> tuple:
    n = len(vals)
    mean = sum(vals) / n
    z = {p: v - mean for p, v in zip(pos, vals)}
    g0 = sum(v * v for v in z.values()) / n
    lrv = g0
    for k in range(1, lag + 1):
        gk = sum(z[p] * z[p + k] for p in z if (p + k) in z) / n
        lrv += 2 * (1 - k / (lag + 1)) * gk
    se = math.sqrt(lrv / n)
    return mean, se, mean / se


def vp3_stats(stage: str) -> dict:
    """Cohort ledger -> mean/SE/t by (a) dict arithmetic, (b) statsmodels kernel; and events -> cohorts by dict arithmetic."""
    from statsmodels.stats.sandwich_covariance import S_hac_simple
    from scipy import stats as sst
    cells = pd.read_csv(_res() / f"cells_{stage}.csv")
    coh = pd.read_csv(_res() / f"cohort_{stage}.csv")
    led = pd.read_parquet(_res() / f"events_{stage}.parquet")
    out = {"stage": stage, "cells": [], "max_abs_diff": {}}
    worst = {"d_mean": 0.0, "d_se": 0.0, "d_t": 0.0, "d_p": 0.0, "kernel_se": 0.0, "cohort_m": 0.0}
    for c in cells.itertuples():
        g = coh[(coh["N"] == c.N) & (coh["H"] == c.H) & (coh["side"] == c.side)].sort_values("t")
        if len(g) < 3:
            continue
        vals, pos = list(g["d"]), list(g["t"])
        mean, se, t = _manual_nw(vals, pos, int(c.H))
        p_one = float(sst.t.sf(t, len(vals) - 1))
        dense = np.zeros(pos[-1] - pos[0] + 1)
        dense[np.array(pos) - pos[0]] = np.array(vals) - mean
        se_kernel = math.sqrt(float(S_hac_simple(dense.reshape(-1, 1), nlags=int(c.H))[0, 0])) / len(vals)
        # cohort means rebuilt from the event ledger by dict arithmetic (no groupby)
        kinds = ("up", "dup") if c.side == "up" else ("dn", "ddn")
        lo, hi = None, None
        bucket = {"B": {}, "C": {}}
        for e in led.itertuples():
            if e.N != c.N or e.kind not in kinds or e.arm not in ("B", "C"):
                continue
            fH = getattr(e, f"f{int(c.H)}")
            stt = getattr(e, f"status{int(c.H)}")
            xt = getattr(e, f"exit_t{int(c.H)}")
            if stt not in (0, 1) or not (fH == fH):
                continue
            bucket[e.arm].setdefault(int(e.t), []).append(fH)
        # stage containment: keep cohorts whose (t, exit) are inside the stage - reuse the cohort file's t set
        dmax = 0.0
        for t_, dv in zip(pos, vals):
            if t_ in bucket["B"] and t_ in bucket["C"]:
                mb = sum(bucket["B"][t_]) / len(bucket["B"][t_])
                mc = sum(bucket["C"][t_]) / len(bucket["C"][t_])
                dmax = max(dmax, abs((mb - mc) - dv))
        worst["cohort_m"] = max(worst["cohort_m"], dmax)
        worst["d_mean"] = max(worst["d_mean"], abs(mean - c.d_mean))
        worst["d_se"] = max(worst["d_se"], abs(se - c.d_se))
        worst["d_t"] = max(worst["d_t"], abs(t - c.d_t))
        worst["d_p"] = max(worst["d_p"], abs(p_one - c.d_p_one))
        worst["kernel_se"] = max(worst["kernel_se"], abs(se_kernel - c.d_se))
        out["cells"].append({"N": int(c.N), "H": int(c.H), "side": c.side, "n_pair_dates": len(vals),
                             "d_mean_table": c.d_mean, "d_mean_manual": mean, "d_se_table": c.d_se,
                             "d_se_manual": se, "d_se_statsmodels_kernel": se_kernel, "t_table": c.d_t,
                             "t_manual": t, "p_table": c.d_p_one, "p_manual": p_one, "perm_p": getattr(c, "perm_p_one", np.nan),
                             "evt_p": getattr(c, "evt_p_one", np.nan)})
    out["max_abs_diff"] = worst
    out["pass"] = bool(all(v < 1e-6 for v in worst.values()))
    return out


# ------------------------------------------------------------------ VP4 / VP5 / VP6
def vp4_accounting(stage: str) -> dict:
    acc = json.loads((_res() / f"accounting_{stage}.json").read_text())
    led = pd.read_parquet(_res() / f"events_{stage}.parquet")
    out = {"stage": stage, "duplicate_event_keys": int(led.duplicated(["entity", "t", "N", "kind"]).sum()),
           "identity_ok": all(v["resolved_in_stage"] + v["dropped"] + v["excluded_by_containment"] + v["excluded_no_benchmark"] == v["formed"]
                              for v in acc.values()),
           "A_eq_B_plus_C": all(v["A_equals_B_plus_C"] for v in acc.values())}
    bench = pd.read_csv(_res() / f"bench_{stage}.csv")
    out["bench_dates_below_floor"] = int(bench["Rm"].isna().sum())
    # excess identity: sum over the benchmark set of (R - Rm) is 0 by construction; check the ledger's Rm is the
    # cohort-independent date value (one Rm per (t,H))
    ok = True
    for H in P.horizons:
        g = led.groupby("t")[f"Rm{H}"].nunique()
        ok &= bool((g <= 1).all())
    out["one_Rm_per_date"] = bool(ok)
    out["pass"] = bool(out["duplicate_event_keys"] == 0 and out["identity_ok"] and out["A_eq_B_plus_C"] and ok)
    return out


def vp5_volume(stage: str, tag: str, n: int = 4000, seed: int = 7) -> dict:
    """(a) adjusted volume == raw volume for panel rows on names with no bonus/split anywhere in the panel span;
    (b) agreement of the abnormal-volume flag computed from turnover (CA-invariant) vs volume."""
    led = pd.read_parquet(_res() / f"events_{stage}.parquet")
    led = led[led["kind"].isin(["up", "dn"])]
    con = duckdb.connect(str(C.EQUITY_DB), read_only=True)
    panel = pd.read_parquet(C.OUT_DIR / f"panel_{tag}.parquet", columns=["entity", "trade_date", "symbol", "volume", "turnover", "close"])
    ca_syms = set(r[0] for r in con.execute(
        "SELECT DISTINCT symbol FROM adjustment_factors WHERE action_type IN ('BONUS','SPLIT')").fetchall())
    clean = panel[~panel["symbol"].isin(ca_syms)]
    samp = clean.sample(min(n, len(clean)), random_state=seed)
    dates = tuple(pd.to_datetime(samp["trade_date"]).dt.date.unique())
    raw = con.execute("SELECT symbol, trade_date, volume FROM equity_bhavcopy WHERE series IN ('EQ','BE') AND trade_date IN ("
                      + ",".join(["?"] * len(dates)) + ")", list(dates)).df()
    con.close()
    m = samp.assign(td=pd.to_datetime(samp["trade_date"])).merge(raw.assign(td=pd.to_datetime(raw["trade_date"])),
                                                                  on=["symbol", "td"], suffixes=("_adj", "_raw"))
    out = {"stage": stage, "names_with_bonus_or_split": len(ca_syms), "rows_checked": int(len(m)),
           "adj_vs_raw_max_abs_diff_no_CA_names": float((m["volume_adj"] - m["volume_raw"]).abs().max())}
    # turnover-based flag agreement on the event set
    pv = panel.copy()
    pv["td"] = pd.to_datetime(pv["trade_date"])
    pv = pv.sort_values(["entity", "td"])
    pv["med_to"] = pv.groupby("entity")["turnover"].transform(lambda s: s.rolling(20).median().shift(1))
    pv["av_to"] = pv["turnover"] / pv["med_to"]
    ev = led.assign(td=pd.to_datetime(led["date"])).merge(pv[["entity", "td", "av_to"]], on=["entity", "td"], how="left")
    ev["abn_to"] = ev["av_to"] >= P.av_threshold
    out["events"] = int(len(ev))
    out["turnover_flag_agreement"] = float((ev["abn_to"] == ev["abn"]).mean())
    out["pass"] = bool(out["adj_vs_raw_max_abs_diff_no_CA_names"] < 1e-6)
    return out


def vp6_fee_by_hand() -> dict:
    """One BUY on 2019-06-03 and one SELL on 2019-06-12, Rs 500,000 each, computed from the schedules by hand."""
    from core.execution.equity.delivery_fees import delivery_equity_fees
    import datetime as dt
    v = 500_000.0
    buy_d, sell_d = dt.date(2019, 6, 3), dt.date(2019, 6, 12)
    stt = 0.001 * v
    exch = 0.0000345 * v
    sebi = 0.000001 * v
    stamp = 0.0001 * v                                    # pre-2020-07-01 buyer stamp duty assumption
    gst = 0.18 * (exch + sebi)
    hand_buy = stt + exch + sebi + stamp + gst
    hand_sell = stt + exch + sebi + gst + 13.5 * 1.18
    lib_buy = delivery_equity_fees(side="BUY", trade_value=v, trade_date=buy_d).total
    lib_sell = delivery_equity_fees(side="SELL", trade_value=v, trade_date=sell_d).total
    return {"notional": v, "hand_buy_rs": hand_buy, "lib_buy_rs": lib_buy, "hand_sell_rs": hand_sell, "lib_sell_rs": lib_sell,
            "round_trip_bp": 1e4 * (hand_buy + hand_sell) / v,
            "components_buy_rs": {"stt": stt, "exchange": exch, "sebi": sebi, "stamp": stamp, "gst": gst},
            "pass": bool(abs(hand_buy - lib_buy) < 1e-9 and abs(hand_sell - lib_sell) < 1e-9)}


def run(stage: str) -> dict:
    tag = "full" if stage == "HOLDOUT" else "dev"
    res = {"stage": stage, "vp1_sql": vp1_sql_reconcile(stage, tag), "vp2_raw": vp2_raw_sample(stage, tag),
           "vp3_stats": vp3_stats(stage), "vp4_accounting": vp4_accounting(stage), "vp5_volume": vp5_volume(stage, tag),
           "vp6_fee": vp6_fee_by_hand()}
    res["stop"] = not all(v["pass"] for k, v in res.items() if isinstance(v, dict) and "pass" in v)
    (_res() / f"verification_{stage}.json").write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    r = run(sys.argv[1])
    print(json.dumps({k: (v["pass"] if isinstance(v, dict) and "pass" in v else v) for k, v in r.items()}, indent=2))
