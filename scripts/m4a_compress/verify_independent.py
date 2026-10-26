"""M4a-CE independent verification. Nothing here imports the engine's state / cohort / outcome logic.

  VP1  pure-SQL re-derivation (DuckDB window functions) of the calendar, membership, daily range / return, fast and slow
       means, the trailing percentile, both tails, the onset rule, the three cohorts, forward status and every outcome,
       compared with the event ledger row by row.
  VP2  raw as-traded re-derivation (plain Python loops over `equity_bhavcopy`) of a seeded event sample: the percentile,
       the cohort membership and the range / vol outcomes are all scale-free, so they must equal the ledger.
  VP3  the statistics: cohort means from the ledger by dict arithmetic; Newey-West by a pure-Python path and by
       statsmodels' S_hac_simple kernel; Holm by hand; compared with the cell table.
  VP4  the accounting identities, uniqueness and cohort exclusivity.
  VP5  price basis: adjusted OHLC equals raw on names with no corporate action; on names with one, adjusted is rebuilt
       from `adjustment_factors` (entity level) and compared.

Any disagreement beyond the stated tolerance sets `stop=True`: the protocol says STOP, investigate, do not choose a number.
"""
from __future__ import annotations

import json
import math
import statistics
import sys

import duckdb
import numpy as np
import pandas as pd

from scripts.breakout_vol.common import P as BKV_P
from scripts.breakout_vol.verify_independent import _manual_nw, entity_symbols      # helpers only (hashed, unchanged)
from scripts.m4a_compress import common as C
from scripts.m4a_compress.common import P

TOL = 1e-9
CHUNK = 40


def _res():
    return C.OUT_DIR / "results"


# ------------------------------------------------------------------ SQL base
def _sql_base(p) -> tuple[duckdb.DuckDBPyConnection, int]:
    con = duckdb.connect()
    con.execute("PRAGMA memory_limit='2GB'")
    pan, cal, mem = (str(C.SNAPSHOT_DIR / f"{n}_dev.parquet").replace("\\", "/") for n in ("panel", "calendar", "membership"))
    con.execute(f"""
      CREATE TABLE cal0 AS SELECT CAST(trade_date AS DATE) d, COALESCE(n_symbols,0) n, tot_turnover_eq tt FROM read_parquet('{cal}');
      CREATE TABLE cal1 AS SELECT d, tt, median(tt) OVER (ORDER BY d ROWS BETWEEN 10 PRECEDING AND 10 FOLLOWING) med
                           FROM cal0 WHERE n >= {BKV_P.calendar_min_symbols} AND dayofweek(d) BETWEEN 1 AND 5;
      CREATE TABLE cal AS SELECT d, row_number() OVER (ORDER BY d) - 1 AS sidx FROM cal1 WHERE tt / med >= {BKV_P.short_session_ratio};
      CREATE TABLE p AS SELECT pa.entity, c.sidx, c.d, pa.open o, pa.high h, pa.low l, pa.close c_, pa.volume v
                        FROM read_parquet('{pan}') pa JOIN cal c ON CAST(pa.trade_date AS DATE) = c.d
                        WHERE pa.open > 0 AND pa.high > 0 AND pa.low > 0 AND pa.close > 0 AND pa.volume > 0;
      CREATE TABLE rb AS SELECT DISTINCT CAST(rebalance_date AS DATE) r FROM read_parquet('{mem}');
      CREATE TABLE dr AS SELECT c.sidx, c.d, (SELECT max(r) FROM rb WHERE r < c.d) AS r FROM cal c;
      CREATE TABLE mem AS SELECT dr.sidx, m.entity FROM dr JOIN read_parquet('{mem}') m ON CAST(m.rebalance_date AS DATE) = dr.r;
      CREATE TABLE q AS SELECT a.entity, a.sidx, (a.h - a.l) / b.c_ AS rng, ln(a.c_ / b.c_) AS ret
                        FROM p a LEFT JOIN p b ON b.entity = a.entity AND b.sidx = a.sidx - 1;
    """)
    return con, con.execute("SELECT max(sidx) + 1 FROM cal").fetchone()[0]


def _stage_idx(con, stage: str) -> tuple[int, int]:
    d0, d1 = C.STAGES[stage]
    lo = con.execute(f"SELECT min(sidx) FROM cal WHERE d >= DATE '{d0}'").fetchone()[0]
    hi = con.execute(f"SELECT max(sidx) FROM cal WHERE d <= DATE '{d1}'").fetchone()[0]
    return int(lo), int(hi)


def _chunk_sql(variant: str, ents: list, p, T: int, lo: int, hi: int) -> str:
    inlist = ",".join("'" + e.replace("'", "''") + "'" for e in ents)
    if variant == "D2":
        f_expr, s_expr = "avg(rng)", "avg(rng)"
        n_f, n_s = "count(rng)", "count(rng)"
    else:
        f_expr, s_expr = "stddev_samp(ret)", "stddev_samp(ret)"
        n_f, n_s = "count(ret)", "count(ret)"
    wins = []
    for h in p.horizons:
        wins.append(f"""
          count(*) OVER wf{h} AS nrows{h}, avg(rng) OVER wf{h} AS frng{h}, avg(ret * ret) OVER wf{h} AS fmsq{h},
          sum(ret) OVER wf{h} AS fsum{h}""")
    wdefs = ",\n".join(f"wf{h} AS (PARTITION BY entity ORDER BY sidx RANGE BETWEEN 1 FOLLOWING AND {h} FOLLOWING)" for h in p.horizons)
    stat_cols = []
    for h in p.horizons:
        stat_cols.append(f"""
          CASE WHEN sidx + {h} > {T - 1} THEN 3 WHEN nrows{h} = {h} THEN 0 ELSE 2 END AS status{h},
          CASE WHEN sidx + {h} <= {T - 1} AND nrows{h} = {h} AND nb = {p.base_window} AND medb > 0 THEN frng{h} / medb END AS E_range{h},
          CASE WHEN sidx + {h} <= {T - 1} AND nrows{h} = {h} AND nrb = {p.base_window} AND msb > 0 THEN sqrt(fmsq{h}) / sqrt(msb) END AS E_vol{h},
          CASE WHEN sidx + {h} <= {T - 1} AND nrows{h} = {h} AND nrb = {p.base_window} AND msb > 0 THEN abs(fsum{h}) / (sqrt({h}) * sqrt(msb)) END AS E_abs{h},
          CASE WHEN sidx + {h} <= {T - 1} AND nrows{h} = {h} AND nrb = {p.base_window} AND msb > 0 THEN fsum{h} / (sqrt({h}) * sqrt(msb)) END AS E_sgn{h}""")
    return f"""
      WITH r AS (
        SELECT entity, sidx,
               CASE WHEN nf = {p.fast} AND ns = {p.slow} AND sl > 0 THEN fa / sl END AS ratio
        FROM (SELECT entity, sidx, {n_f} OVER wfast AS nf, {f_expr} OVER wfast AS fa,
                     {n_s} OVER wslow AS ns, {s_expr} OVER wslow AS sl
              FROM q WHERE entity IN ({inlist})
              WINDOW wfast AS (PARTITION BY entity ORDER BY sidx RANGE BETWEEN {p.fast - 1} PRECEDING AND CURRENT ROW),
                     wslow AS (PARTITION BY entity ORDER BY sidx RANGE BETWEEN {p.slow - 1} PRECEDING AND CURRENT ROW))),
      s AS (
        SELECT entity, sidx, ratio,
               CASE WHEN np_ = {p.pct_window} THEN len(list_filter(lst, x -> x <= ratio))::DOUBLE / {p.pct_window} END AS pct,
               CASE WHEN np_ = {p.pct_window} THEN len(list_filter(lst, x -> abs(x - ratio) <= 1e-12 * ratio)) - 1 END AS ties
        FROM (SELECT entity, sidx, ratio, count(ratio) OVER wp AS np_, list(ratio) OVER wp AS lst FROM r
              WINDOW wp AS (PARTITION BY entity ORDER BY sidx RANGE BETWEEN {p.pct_window - 1} PRECEDING AND CURRENT ROW))),
      f AS (
        SELECT entity, sidx, pct, ties, pct <= {p.q_low} + 1e-12 AS low, pct >= {p.q_high} - 1e-12 AS high FROM s),
      g AS (
        SELECT f.entity, f.sidx, pct, ties, low, high,
               sum(CASE WHEN pct IS NOT NULL AND NOT low THEN 1 ELSE 0 END) OVER wq AS cl,
               sum(CASE WHEN pct IS NOT NULL AND NOT high THEN 1 ELSE 0 END) OVER wq AS ch
        FROM f WINDOW wq AS (PARTITION BY entity ORDER BY sidx RANGE BETWEEN {p.quiet} PRECEDING AND 1 PRECEDING)),
      c AS (
        SELECT g.entity, g.sidx AS t, pct, ties,
               coalesce(low AND cl = {p.quiet}, false) AS is_C,
               coalesce(NOT low, false) AS is_N,
               coalesce(high AND ch = {p.quiet}, false) AS is_P
        FROM g JOIN mem ON mem.entity = g.entity AND mem.sidx = g.sidx
        WHERE pct IS NOT NULL AND g.sidx BETWEEN {lo} AND {hi}),
      o AS (
        SELECT entity, sidx, count(rng) OVER wb AS nb, median(rng) OVER wb AS medb,
               count(ret) OVER wb AS nrb, avg(ret * ret) OVER wb AS msb, {",".join(wins)}
        FROM q WHERE entity IN ({inlist})
        WINDOW wb AS (PARTITION BY entity ORDER BY sidx RANGE BETWEEN {p.base_window - 1} PRECEDING AND CURRENT ROW),
               {wdefs}),
      oo AS (SELECT entity, sidx, {",".join(stat_cols)} FROM o)
      SELECT c.entity, c.t, c.pct, c.ties, c.is_C, c.is_N, c.is_P, oo.* EXCLUDE (entity, sidx)
      FROM c JOIN oo ON oo.entity = c.entity AND oo.sidx = c.t
      WHERE c.is_C OR c.is_N OR c.is_P"""


def classify_pct_diffs(diff: np.ndarray, ties: np.ndarray, w: int) -> tuple[np.ndarray, np.ndarray]:
    """Amendment A1. A percentile difference beyond 1e-12 is EXPLAINED only if the window holds an exact mathematical tie
    (a ratio equal to the current one within 1e-12 relative, counted by the SQL path) and the difference is at most one
    count per tied value - the two float paths then break the tie differently. Anything else is unexplained."""
    diff, ties = np.asarray(diff, float), np.asarray(ties, float)
    off = diff > 1e-12
    k = np.rint(diff * w)
    explained = off & (np.abs(diff * w - k) < 1e-6) & (k >= 1) & (k <= ties)
    return explained, off & ~explained


def vp1_sql_reconcile(stage: str, p=P, variants=("D2", "D1")) -> dict:
    con, T = _sql_base(p)
    lo, hi = _stage_idx(con, stage)
    ents = [r[0] for r in con.execute("SELECT DISTINCT entity FROM p ORDER BY 1").fetchall()]
    out = {}
    for variant in variants:
        ledger = pd.read_parquet(_res() / f"events_{variant}_{stage}.parquet")
        parts = []
        for i in range(0, len(ents), CHUNK):
            parts.append(con.execute(_chunk_sql(variant, ents[i:i + CHUNK], p, T, lo, hi)).df())
        sq = pd.concat(parts, ignore_index=True)
        m = ledger.merge(sq, on=["entity", "t"], how="outer", suffixes=("", "_sql"), indicator=True)
        both = m[m["_merge"] == "both"]
        x = {"ledger_rows": int(len(ledger)), "sql_rows": int(len(sq)),
             "only_in_ledger": int((m["_merge"] == "left_only").sum()), "only_in_sql": int((m["_merge"] == "right_only").sum())}
        x["flag_mismatch"] = int(sum((both[k].astype(bool) != both[f"{k}_sql"].astype(bool)).sum() for k in ("is_C", "is_N", "is_P")))
        pdiff = (both["pct"] - both["pct_sql"]).abs()
        x["pct_max_abs_diff"] = float(pdiff.max()) if len(both) else float("nan")
        expl, unexpl = classify_pct_diffs(pdiff.to_numpy(), both["ties"].fillna(0).to_numpy(), p.pct_window)
        x["pct_tie_explained"], x["pct_unexplained"] = int(expl.sum()), int(unexpl.sum())
        x["status_mismatch"] = int(sum((both[f"status{h}"] != both[f"status{h}_sql"]).sum() for h in p.horizons))
        worst, ncmp, nullmis = 0.0, 0, 0
        for h in p.horizons:
            for nm in ("E_range", "E_vol", "E_abs", "E_sgn"):
                a, b = both[f"{nm}{h}"], both[f"{nm}{h}_sql"]
                nullmis += int((a.isna() != b.isna()).sum())
                ok = a.notna() & b.notna()
                ncmp += int(ok.sum())
                if ok.any():
                    worst = max(worst, float((a[ok] - b[ok]).abs().max()))
        x.update({"E_max_abs_diff": worst, "n_compared_values": ncmp, "null_mismatch": nullmis})
        x["pass"] = bool(x["only_in_ledger"] == 0 and x["only_in_sql"] == 0 and x["flag_mismatch"] == 0 and
                         x["status_mismatch"] == 0 and x["null_mismatch"] == 0 and x["pct_unexplained"] == 0 and worst < TOL)
        out[variant] = x
    out["sql_sessions"] = int(T)
    out["pass"] = all(out[v]["pass"] for v in variants)
    return out


# ------------------------------------------------------------------ VP2
def _pct_py(ratios: list, w: int) -> float | None:
    if len(ratios) < w or any(r is None for r in ratios[-w:]):
        return None
    win = ratios[-w:]
    return sum(1 for r in win if r <= win[-1]) / w


def vp2_raw_sample(stage: str, p=P, n_per_cohort: int = 4, seed: int = 20260930, variant: str = "D2") -> dict:
    """Plain-Python re-derivation of seeded events from the RAW as-traded table. Events with any adjustment_factors row of
    any symbol of the entity in the span are skipped (raw and adjusted series differ there by construction); counted."""
    con0, _ = _sql_base(p)
    sess = [pd.Timestamp(x).date() for x in con0.execute("SELECT d FROM cal ORDER BY sidx").df()["d"]]
    led = pd.read_parquet(_res() / f"events_{variant}_{stage}.parquet")
    led = led[(led[[f"status{h}" for h in p.horizons]] == 0).all(axis=1)]
    panel = pd.read_parquet(C.SNAPSHOT_DIR / "panel_dev.parquet", columns=["entity", "trade_date", "symbol"])
    panel["td"] = pd.to_datetime(panel["trade_date"]).dt.date
    con = duckdb.connect(str(C.EQUITY_DB), read_only=True)
    ent_syms = entity_symbols(con)
    rng_ = np.random.default_rng(seed)
    picks = []
    for col in ("is_C", "is_N", "is_P"):
        g = led[led[col]]
        picks.append(g.sample(min(n_per_cohort, len(g)), random_state=int(rng_.integers(1 << 30))))
    picks = pd.concat(picks).drop_duplicates(["entity", "t"])
    back = p.quiet + p.pct_window + p.slow
    rows, skipped_ca, skipped_sym, skipped_short = [], 0, 0, 0
    for r in picks.itertuples():
        t = int(r.t)
        if t - back < 0 or t + max(p.horizons) >= len(sess):
            skipped_short += 1
            continue
        d0, d1 = sess[t - back], sess[t + max(p.horizons)]
        syms = panel[(panel["entity"] == r.entity) & (panel["td"] >= d0) & (panel["td"] <= d1)]["symbol"].unique()
        if len(syms) != 1:
            skipped_sym += 1
            continue
        all_syms = sorted(ent_syms.get(r.entity, {syms[0]}) | {syms[0]})
        ca = con.execute("SELECT count(*) FROM adjustment_factors WHERE symbol IN (" + ",".join(["?"] * len(all_syms)) +
                         ") AND ex_date BETWEEN ? AND ?", all_syms + [d0, d1]).fetchone()[0]
        if ca:
            skipped_ca += 1
            continue
        raw = con.execute("""SELECT trade_date, open, high, low, close, volume FROM equity_bhavcopy
                             WHERE symbol = ? AND series IN ('EQ','BE') AND trade_date BETWEEN ? AND ?
                             ORDER BY trade_date, turnover DESC""", [syms[0], d0, d1]).fetchall()
        by = {}
        for td, o, h_, l_, c_, v in raw:
            if min(o, h_, l_, c_, v) > 0:
                by.setdefault(td, (o, h_, l_, c_, v))

        def row(i):
            return by.get(sess[i])

        def rng_at(s):
            a, b = row(s), row(s - 1)
            return None if a is None or b is None else (a[1] - a[2]) / b[3]

        def ret_at(s):
            a, b = row(s), row(s - 1)
            return None if a is None or b is None else math.log(a[3] / b[3])

        def ratio_at(s):
            if variant == "D2":
                xs = [rng_at(k) for k in range(s - p.slow + 1, s + 1)]
                if any(v is None for v in xs):
                    return None
                den = sum(xs) / p.slow
                num = sum(xs[-p.fast:]) / p.fast
            else:
                xs = [ret_at(k) for k in range(s - p.slow + 1, s + 1)]
                if any(v is None for v in xs):
                    return None
                den = statistics.stdev(xs)
                num = statistics.stdev(xs[-p.fast:])
            return num / den if den > 0 else None

        pcts = {}
        for s in range(t - p.quiet, t + 1):
            win = [ratio_at(k) for k in range(s - p.pct_window + 1, s + 1)]
            pcts[s] = None if any(v is None for v in win) else sum(1 for v in win if v <= win[-1]) / p.pct_window
        low = {s: (v is not None and v <= p.q_low + 1e-12) for s, v in pcts.items()}
        high = {s: (v is not None and v >= p.q_high - 1e-12) for s, v in pcts.items()}
        prior = range(t - p.quiet, t)
        is_c = bool(low[t] and all(pcts[s] is not None and not low[s] for s in prior))
        is_p = bool(high[t] and all(pcts[s] is not None and not high[s] for s in prior))
        is_n = bool(pcts[t] is not None and not low[t])
        rec = {"entity": r.entity, "t": t, "pct_raw": pcts[t], "pct_ledger": r.pct,
               "flags_raw": (is_c, is_n, is_p), "flags_ledger": (bool(r.is_C), bool(r.is_N), bool(r.is_P))}
        base_r = [rng_at(k) for k in range(t - p.base_window + 1, t + 1)]
        base_e = [ret_at(k) for k in range(t - p.base_window + 1, t + 1)]
        for h in p.horizons:
            fr = [rng_at(k) for k in range(t + 1, t + h + 1)]
            fe = [ret_at(k) for k in range(t + 1, t + h + 1)]
            rec[f"E_range{h}_raw"] = (sum(fr) / h) / statistics.median(base_r)
            rec[f"E_range{h}_ledger"] = getattr(r, f"E_range{h}")
            rec[f"E_vol{h}_raw"] = math.sqrt(sum(x * x for x in fe) / h) / math.sqrt(sum(x * x for x in base_e) / len(base_e))
            rec[f"E_vol{h}_ledger"] = getattr(r, f"E_vol{h}")
        rows.append(rec)
    con.close()
    d = pd.DataFrame(rows)
    out = {"stage": stage, "variant": variant, "sampled": int(len(picks)), "verified": int(len(d)),
           "skipped_ca": skipped_ca, "skipped_multi_symbol": skipped_sym, "skipped_short": skipped_short}
    if len(d):
        out["pct_max_abs_diff"] = float((d["pct_raw"] - d["pct_ledger"]).abs().max())
        out["flag_mismatch"] = int((d["flags_raw"] != d["flags_ledger"]).sum())
        worst = 0.0
        for h in p.horizons:
            for nm in ("E_range", "E_vol"):
                worst = max(worst, float((d[f"{nm}{h}_raw"] - d[f"{nm}{h}_ledger"]).abs().max()))
        out["E_max_abs_diff"] = worst
        out["pass"] = bool(out["pct_max_abs_diff"] < 1e-12 and out["flag_mismatch"] == 0 and worst < TOL)
    else:
        out["pass"] = False
    d.to_csv(_res() / f"vp2_raw_sample_{stage}.csv", index=False)
    return out


# ------------------------------------------------------------------ VP3
def _holm_py(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, run, out = len(items), 0.0, {}
    for i, (k, v) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v))
        out[k] = run
    return out


def vp3_stats(stage: str, p=P) -> dict:
    """Cell statistics rebuilt from the ledger with dict arithmetic (no groupby), NW by hand and by the statsmodels kernel."""
    from scipy import stats as sst
    from statsmodels.stats.sandwich_covariance import S_hac_simple
    con, _ = _sql_base(p)
    lo, hi = _stage_idx(con, stage)
    cells = pd.read_csv(_res() / f"cells_{stage}.csv")
    worst = {"d_mean": 0.0, "d_se": 0.0, "d_t": 0.0, "d_p": 0.0, "kernel_se": 0.0, "n_pair": 0}
    ledgers, out_cells = {}, []
    for c in cells.itertuples():
        led = ledgers.setdefault(c.variant, pd.read_parquet(_res() / f"events_{c.variant}_{stage}.parquet"))
        h, y = int(c.h), f"{c.outcome}{int(c.h)}"
        xcol = "is_N" if c.comparator == "normal" else "is_P"
        floor = p.min_normal_names if c.comparator == "normal" else 1
        bc, bx = {}, {}
        for e in led.itertuples():
            if not (e.t >= lo and e.t + h <= hi):
                continue
            v = getattr(e, y)
            if getattr(e, f"status{h}") != 0 or not (v == v):
                continue
            if e.is_C:
                bc.setdefault(int(e.t), []).append(v)
            if getattr(e, xcol):
                bx.setdefault(int(e.t), []).append(v)
        pos = sorted(t for t in bc if t in bx and len(bx[t]) >= floor)
        vals = [sum(bc[t]) / len(bc[t]) - sum(bx[t]) / len(bx[t]) for t in pos]
        if len(vals) < 3:
            continue
        mean, se, t_ = _manual_nw(vals, pos, h)
        p_one = float(sst.t.sf(t_, len(vals) - 1))
        dense = np.zeros(pos[-1] - pos[0] + 1)
        dense[np.array(pos) - pos[0]] = np.array(vals) - mean
        se_k = math.sqrt(float(S_hac_simple(dense.reshape(-1, 1), nlags=h)[0, 0])) / len(vals)
        worst["d_mean"] = max(worst["d_mean"], abs(mean - c.d_mean))
        worst["d_se"] = max(worst["d_se"], abs(se - c.d_se))
        worst["d_t"] = max(worst["d_t"], abs(t_ - c.d_t))
        worst["d_p"] = max(worst["d_p"], abs(p_one - c.d_p_one))
        worst["kernel_se"] = max(worst["kernel_se"], abs(se_k - c.d_se))
        worst["n_pair"] = max(worst["n_pair"], abs(len(vals) - int(c.n_pair_dates)))
        if c.variant == "D2" and c.outcome == "E_range":
            out_cells.append({"h": h, "comparator": c.comparator, "n_pair_dates": len(vals), "d_mean_table": c.d_mean,
                              "d_mean_manual": mean, "d_se_table": c.d_se, "d_se_manual": se, "d_se_kernel": se_k,
                              "p_table": c.d_p_one, "p_manual": p_one})
    prim = cells[(cells["variant"] == "D2") & (cells["outcome"] == "E_range")].dropna(subset=["d_p_one"])
    holm_manual = _holm_py({(int(r.h), r.comparator): r.d_p_one for r in prim.itertuples()})
    out = {"stage": stage, "cells": out_cells, "max_abs_diff": worst, "holm_manual": {f"{k[0]},{k[1]}": v for k, v in holm_manual.items()}}
    out["pass"] = bool(all(v < 1e-6 for v in worst.values()) and len(out_cells) == len(prim))
    return out


# ------------------------------------------------------------------ VP4 / VP5
def vp4_accounting(stage: str, p=P) -> dict:
    acct = json.loads((_res() / f"accounting_{stage}.json").read_text())
    out = {"stage": stage, "variants": {}}
    ok = True
    for variant, blocks in acct.items():
        led = pd.read_parquet(_res() / f"events_{variant}_{stage}.parquet")
        v = {"duplicate_keys": int(led.duplicated(["entity", "t"]).sum()),
             "C_and_N": int((led["is_C"] & led["is_N"]).sum()), "C_and_P": int((led["is_C"] & led["is_P"]).sum()),
             "identity_ok": all(b["resolved"] + b["dropped"] + b["value_missing"] + b["excluded_by_containment"] == b["formed"]
                                for b in blocks.values()),
             "formed_matches_ledger": all(blocks[f"h{h}_{n}"]["formed"] == int(led[c].sum())
                                          for h in p.horizons for n, c in (("C", "is_C"), ("N", "is_N"), ("P", "is_P"))),
             "pct_in_unit_interval": bool(led["pct"].between(1.0 / p.pct_window - 1e-12, 1.0 + 1e-12).all())}
        v["pass"] = bool(v["duplicate_keys"] == 0 and v["C_and_N"] == 0 and v["C_and_P"] == 0 and v["identity_ok"]
                         and v["formed_matches_ledger"] and v["pct_in_unit_interval"])
        ok &= v["pass"]
        out["variants"][variant] = v
    out["pass"] = bool(ok)
    return out


def vp5_prices(n: int = 3000, seed: int = 7) -> dict:
    """(a) adjusted OHLC == raw OHLC for panel rows of entities with no adjustment factor of any of their symbols;
    (b) for entities with one, adjusted is rebuilt as raw x product of LATER factors (reported, precedent: BKV-1 VP5(c))."""
    con = duckdb.connect(str(C.EQUITY_DB), read_only=True)
    panel = pd.read_parquet(C.SNAPSHOT_DIR / "panel_dev.parquet",
                            columns=["entity", "trade_date", "symbol", "series", "open", "high", "low", "close"])
    ent_syms = entity_symbols(con)
    fac = con.execute("SELECT symbol, ex_date, action_type, factor FROM adjustment_factors "
                      "WHERE action_type IN ('BONUS','SPLIT','SPECIAL_DIVIDEND')").df()
    fac["ex_date"] = pd.to_datetime(fac["ex_date"])
    ca_ents = {e for e, ss in ent_syms.items() if ss & set(fac["symbol"])}
    panel["td"] = pd.to_datetime(panel["trade_date"])

    def raw_for(sample):
        dates = tuple(sample["td"].dt.date.unique())
        raw = con.execute("SELECT symbol, series, trade_date, open r_open, high r_high, low r_low, close r_close "
                          "FROM equity_bhavcopy WHERE trade_date IN (" + ",".join(["?"] * len(dates)) + ")", list(dates)).df()
        raw["td"] = pd.to_datetime(raw["trade_date"])
        return sample.merge(raw.drop(columns=["trade_date"]), on=["symbol", "series", "td"])

    clean = panel[~panel["entity"].isin(ca_ents)]
    a = raw_for(clean.sample(min(n, len(clean)), random_state=seed))
    diffs = [((a[c] - a[f"r_{c}"]).abs() / a[c].abs()).max() for c in ("open", "high", "low", "close")]
    dirty = panel[panel["entity"].isin(ca_ents)]
    rec_ok = rec_n = 0
    if len(dirty):
        b = raw_for(dirty.sample(min(n, len(dirty)), random_state=seed))
        by_ent = {e: fac[fac["symbol"].isin(ent_syms.get(e, set()))] for e in set(b["entity"])}
        for r in b.itertuples():
            g = by_ent[r.entity]
            later = g[g["ex_date"] > r.td]
            pf = float(np.prod(later["factor"])) if len(later) else 1.0
            rec_n += 1
            rec_ok += int(all(abs(getattr(r, c) - getattr(r, f"r_{c}") * pf) <= 1e-6 * abs(getattr(r, c))
                              for c in ("open", "high", "low", "close")))
    con.close()
    out = {"entities_with_bonus_or_split": len(ca_ents), "rows_checked_clean": int(len(a)),
           "adj_vs_raw_max_rel_diff_no_CA_names": float(max(diffs)), "ca_rows_reconstructed": rec_n,
           "ca_rows_reconstruction_agree": rec_ok, "ca_reconstruction_rate": (rec_ok / rec_n) if rec_n else None}
    out["pass"] = bool(out["adj_vs_raw_max_rel_diff_no_CA_names"] < 1e-9 and len(a) > 0)
    return out


def run(stage: str, p=P) -> dict:
    res = {"stage": stage, "vp1_sql": vp1_sql_reconcile(stage, p), "vp2_raw": vp2_raw_sample(stage, p),
           "vp3_stats": vp3_stats(stage, p), "vp4_accounting": vp4_accounting(stage, p), "vp5_prices": vp5_prices()}
    res["stop"] = not all(v["pass"] for k, v in res.items() if isinstance(v, dict) and "pass" in v)
    (_res() / f"verification_{stage}.json").write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    r = run(sys.argv[1])
    print(json.dumps({k: (v["pass"] if isinstance(v, dict) and "pass" in v else v) for k, v in r.items()}, indent=2))
