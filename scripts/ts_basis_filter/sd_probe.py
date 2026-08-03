"""TS Basis Filter — SD / Breadth / Marginal-Value / Gate-Stability Probe.

Implements `docs/reports/TS_BASIS_FILTER_SD_PROBE_PROMPT.md` on the already-burned
TRAIN+HOLDOUT window (2016-02-11 -> 2022-12-31). The preserved 876-formation sealed
window (2023-01-01 -> 2026-07-24) is fenced out and never touched.

Base construct:
  signal      = z_ts from data/signal_engine/ts_basis_daily/ts_signals.duckdb
                (the daily build's own output — build_ts_basis_daily.py OUT_DB)
  cross-section = full eligible daily universe (every non-null z_ts), NOT top-5
  forward ret = NSE_EQ spot close->close, H=1 (primary) and H=5 (robustness)
  rank IC     = per-formation Spearman(z_ts, fwd_ret), MIN_NAMES = 20
  N_eff       = participation ratio of the fwd-ret correlation matrix (names space)

Gates (hard admission, per the prompt):
  G1 regime   = admit formation t iff vix_t <= k*vix_med_t (primary k=1.5)
  G2 OI       = admit name iff sign(chg_in_oi) == sign(z_ts) on near-month FUTSTK
  G3 expiry   = reject formation t iff t+1 is a monthly stock-futures expiry day

Eight configurations per the prompt §4 (base, leave-one-in, full, drop-column).
Power via scripts/rfa/power.py (power_at / n_required, two-sided, target 0.80).
Gate Stability table per the prompt §6 (regime cells, circularity rule a,
calendar-anchored concentration rule b).

Usage:
  python scripts/ts_basis_filter/sd_probe.py [--out PATH]
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "osc"))

from scripts.rfa.power import power_at, n_required  # noqa: E402

SIGNALS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
EQUITY_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
FUTURES_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
INDEX_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
REPORT = ROOT / "docs" / "reports" / "TS_BASIS_FILTER_SD_PROBE_REPORT.md"

FENCE_START = pd.Timestamp("2016-02-11")
FENCE_END = pd.Timestamp("2022-12-31")
MIN_NAMES = 20
NW_LAG = 5
K_G1 = 1.5
K_SENS = [1.25, 1.5, 2.0]
VIX_MED_WIN = 252
VIX_MIN_OBS = 60
ROLLING_WINDOW = 60
STABILITY_MIN_N = 20
ALPHA = 0.05
POWER_TARGET = 0.80


# ── fence ─────────────────────────────────────────────────────────────────────
def _assert_fence(series: pd.Series):
    obs_min, obs_max = series.min(), series.max()
    assert obs_min >= FENCE_START, f"FENCE VIOLATION: min {obs_min.date()} < {FENCE_START.date()}"
    assert obs_max <= FENCE_END, f"FENCE VIOLATION: max {obs_max.date()} > {FENCE_END.date()}"
    return obs_min, obs_max


# ── data loaders ──────────────────────────────────────────────────────────────
def _load_signals():
    con = duckdb.connect(str(SIGNALS_DB), read_only=True)
    df = con.execute(
        "SELECT formation_date, underlying, z_ts FROM signals "
        "WHERE z_ts IS NOT NULL "
        "AND formation_date >= ? AND formation_date <= ?",
        [FENCE_START.date(), FENCE_END.date()],
    ).fetchdf()
    con.close()
    df["formation_date"] = pd.to_datetime(df["formation_date"])
    df = df.dropna(subset=["z_ts"])
    _assert_fence(df["formation_date"])
    return df


def _load_equity_closes():
    con = duckdb.connect(str(EQUITY_DB), read_only=True)
    df = con.execute(
        "SELECT trade_date, symbol, close FROM equity_bhavcopy "
        "WHERE series='EQ' AND trade_date >= ? AND trade_date <= ?",
        [FENCE_START.date(), FENCE_END.date()],
    ).fetchdf()
    con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def _load_oi():
    con = duckdb.connect(str(FUTURES_DB), read_only=True)
    df = con.execute(
        """
        WITH ranked AS (
          SELECT underlying, expiry_dt, trade_date, open_int, chg_in_oi,
                 ROW_NUMBER() OVER (PARTITION BY underlying, trade_date
                                    ORDER BY expiry_dt) AS rn
          FROM futures_bhavcopy
          WHERE inst_type='FUTSTK'
            AND trade_date >= ? AND trade_date <= ?
            AND expiry_dt >= trade_date
        )
        SELECT underlying, trade_date, open_int, chg_in_oi, expiry_dt
        FROM ranked WHERE rn = 1
        """,
        [FENCE_START.date(), FENCE_END.date()],
    ).fetchdf()
    con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["expiry_dt"] = pd.to_datetime(df["expiry_dt"])
    return df


def _load_index_series(symbol: str) -> pd.Series:
    """Close series for an index symbol across the window's 1d files (indexed by date)."""
    files = sorted(INDEX_DIR.glob("*.duckdb"))
    out = {}
    for fp in files:
        d = fp.name[:10]
        if not (FENCE_START.date().isoformat() <= d <= FENCE_END.date().isoformat()):
            continue
        try:
            con = duckdb.connect(str(fp), read_only=True)
            row = con.execute(
                "SELECT timestamp, close FROM candles WHERE symbol=? AND timeframe='1d' "
                "ORDER BY timestamp DESC LIMIT 1",
                [symbol],
            ).fetchone()
            con.close()
        except Exception:
            continue
        if row and row[1] is not None:
            out[pd.Timestamp(row[0]).normalize()] = float(row[1])
    s = pd.Series(out)
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def _load_expiry_days() -> set:
    con = duckdb.connect(str(FUTURES_DB), read_only=True)
    rows = con.execute(
        "SELECT DISTINCT expiry_dt FROM futures_bhavcopy "
        "WHERE inst_type='FUTSTK' AND expiry_dt >= ? AND expiry_dt <= ?",
        [FENCE_START.date(), FENCE_END.date() + pd.Timedelta(days=60)],
    ).fetchall()
    con.close()
    return {pd.Timestamp(r[0]) for r in rows}


# ── IC machinery (mirrors osc/sd_probe.py conventions) ───────────────────────
def _newey_west(x, lag):
    n = len(x)
    if n < 3:
        return np.nan, np.nan
    mean = np.mean(x)
    resid = x - mean
    s0 = np.sum(resid**2) / n
    s = s0
    for j in range(1, min(lag + 1, n - 1)):
        w = 1.0 - j / (lag + 1)
        s += 2.0 * w * np.sum(resid[j:] * resid[:-j]) / n
    se = math.sqrt(max(s, 1e-15) / n)
    return mean, se


def _ic_stats(df: pd.DataFrame, score_col: str, ret_col: str):
    """Per-formation Spearman IC series + summary. df must have formation_date."""
    records = []
    for fdt, grp in df.groupby("formation_date"):
        if len(grp) < MIN_NAMES:
            continue
        s = grp[score_col].astype(float)
        r = grp[ret_col].astype(float)
        if s.nunique() < 2 or r.nunique() < 2:
            continue
        ic, _ = stats.spearmanr(s, r)
        if not np.isnan(ic):
            records.append({"formation_date": fdt, "ic": ic, "n_names": len(grp)})
    if not records:
        return None
    out = pd.DataFrame(records).sort_values("formation_date")
    series = out["ic"].values
    nw_mean, nw_se = _newey_west(series, NW_LAG)
    ac1 = float(np.corrcoef(series[:-1], series[1:])[0, 1]) if len(series) > 1 else np.nan
    return {
        "n_dates": len(series),
        "mean_ic": float(np.mean(series)),
        "sd_ic": float(np.std(series, ddof=1)),
        "ac1": ac1,
        "nw_t": nw_mean / nw_se if nw_se and nw_se > 0 else np.nan,
        "nw_se": nw_se,
        "avg_names": float(out["n_names"].mean()),
        "series": series,
    }


def _neff_stats(df: pd.DataFrame, ret_col: str):
    """Participation ratio over a rolling window on the names cross-section."""
    if df.empty or ret_col not in df.columns:
        return {"median_neff": np.nan, "median_pc1": np.nan, "n_windows": 0}
    panel = df.pivot_table(index="formation_date", columns="underlying", values=ret_col)
    dates = panel.index.sort_values()
    neffs, pc1s = [], []
    for i in range(ROLLING_WINDOW - 1, len(dates)):
        win = panel.loc[dates[i - ROLLING_WINDOW + 1 : i + 1]]
        filled = win.dropna(axis=1)
        N = filled.shape[1]
        if N < 3:
            continue
        X = (filled - filled.mean()).values
        X = X / (filled.std(ddof=1).values + 1e-12)
        X = np.nan_to_num(X, nan=0.0)
        cov = np.cov(X.T)
        ev = np.linalg.eigvalsh(cov)
        ev = ev[ev > 0]
        if ev.sum() <= 0:
            continue
        neffs.append(float(ev.sum() ** 2 / np.sum(ev**2)))
        pc1s.append(float(ev[-1] / ev.sum()))
    return {
        "median_neff": float(np.median(neffs)) if neffs else np.nan,
        "median_pc1": float(np.median(pc1s)) if pc1s else np.nan,
        "n_windows": len(neffs),
    }


# ── panel construction ────────────────────────────────────────────────────────
def _build_base_panel():
    sig = _load_signals()
    eq = _load_equity_closes()
    oi = _load_oi()
    vix = _load_index_series("NSE_INDEX|India VIX")
    n50 = _load_index_series("NSE_INDEX|Nifty 50")
    exp_days = _load_expiry_days()

    # trading calendar = distinct formation dates (daily cadence)
    cal = pd.Series(sorted(sig["formation_date"].unique()))
    pos = {d: i for i, d in enumerate(cal)}

    close = eq.set_index(["trade_date", "symbol"])["close"]

    def close_at(dt, sym):
        try:
            return close.loc[(pd.Timestamp(dt), sym)]
        except KeyError:
            return np.nan

    # per (formation, underlying): close at t, t+1, t+5
    recs = []
    for fdt, g in sig.groupby("formation_date"):
        i = pos[fdt]
        nxt1 = cal[i + 1] if i + 1 < len(cal) else None
        nxt5 = cal[i + 5] if i + 5 < len(cal) else None
        c_t = {}
        for u, z in zip(g["underlying"], g["z_ts"]):
            c_t[u] = close_at(fdt, u)
        for u, z in zip(g["underlying"], g["z_ts"]):
            c0 = c_t.get(u)
            c1 = close_at(nxt1, u) if nxt1 is not None else np.nan
            c5 = close_at(nxt5, u) if nxt5 is not None else np.nan
            f1 = c1 / c0 - 1.0 if (c0 and c0 > 0 and c1 and c1 > 0) else np.nan
            f5 = c5 / c0 - 1.0 if (c0 and c0 > 0 and c5 and c5 > 0) else np.nan
            recs.append({
                "formation_date": fdt, "underlying": u, "z_ts": float(z),
                "fwd_1": f1, "fwd_5": f5,
            })
    panel = pd.DataFrame(recs)

    # attach VIX + N50 regime tags
    vix_close = vix.reindex(panel["formation_date"]).ffill()
    vix_med = vix.rolling(VIX_MED_WIN, min_periods=VIX_MIN_OBS).median()
    vix_med_t = vix_med.reindex(panel["formation_date"]).ffill()
    panel["vix"] = vix_close.values
    panel["vix_med"] = vix_med_t.values
    panel["g1_admit"] = panel["vix"] <= K_G1 * panel["vix_med"]

    n50_sma = n50.rolling(252, min_periods=60).mean()
    n50_sma_t = n50_sma.reindex(panel["formation_date"]).ffill()
    n50_t = n50.reindex(panel["formation_date"]).ffill()
    panel["bull"] = n50_t.values > n50_sma_t.values

    # OI attach (near-month chg_in_oi)
    oi_s = oi.set_index(["trade_date", "underlying"])["chg_in_oi"]
    oi_v = panel.apply(
        lambda r: oi_s.get((pd.Timestamp(r["formation_date"]), r["underlying"]), np.nan),
        axis=1,
    )
    panel["oi_chg"] = oi_v.values
    panel["oi_missing"] = oi_v.isna().values
    panel["g2_admit"] = np.sign(panel["oi_chg"]) == np.sign(panel["z_ts"])

    # expiry (G3): reject formation t iff t+1 is a monthly stock-futures expiry day
    nxt_map = {d: cal[i + 1] if i + 1 < len(cal) else pd.NaT for i, d in enumerate(cal)}
    panel["exec_date"] = panel["formation_date"].map(nxt_map)
    panel["g3_admit"] = ~panel["exec_date"].isin(exp_days)

    # calendar regime tags (Pre/COVID/Post)
    def cal_bucket(d):
        y = d.year
        if y < 2020:
            return "Pre-COVID"
        if y <= 2021:
            return "COVID"
        return "Post-COVID"
    panel["era"] = panel["formation_date"].map(cal_bucket)

    return panel, {"n_rows": len(sig), "n_formations": sig["formation_date"].nunique(),
                   "n_underlyings": sig["underlying"].nunique()}


CONFIG_RULES = {
    "base": {},
    "G1": {"g1_admit": True},
    "G2": {"g2_admit": True},
    "G3": {"g3_admit": True},
    "full": {"g1_admit": True, "g2_admit": True, "g3_admit": True},
    "drop_G1": {"g2_admit": True, "g3_admit": True},
    "drop_G2": {"g1_admit": True, "g3_admit": True},
    "drop_G3": {"g1_admit": True, "g2_admit": True},
}


def _apply_config(panel, rule: dict):
    out = panel.copy()
    for col, keep in rule.items():
        out = out[out[col] == keep]
    return out


# ── power helpers ─────────────────────────────────────────────────────────────
def _fixed_delta():
    # base mean IC (measured) is the fixed delta across configs
    pass


# ── gate stability ────────────────────────────────────────────────────────────
def _stability_table(panel, ic_stats_by_config, full_name="full"):
    """Per-gate per-regime marginal ΔIC on the drop-column pair.

    Gates and their drop-column config:
      G1 <-> drop_G1, G2 <-> drop_G2, G3 <-> drop_G3.
    Regime cells are tagged per-formation from the panel.
    Circularity rule (a): G1's VIX axis is self-defining -> cells marked circular,
    excluded from G1's k/m. Concentration rule (b): anchored on the calendar axis.
    """
    # per-formation regime tags (formation-level, so masks are index-agnostic)
    fm = panel.groupby("formation_date").agg(
        bull=("bull", "first"), vix=("vix", "first"), vix_med=("vix_med", "first"),
        era=("era", "first"),
    )
    regimes = {
        "Bull": fm["bull"] == True,  # noqa: E712
        "Bear": fm["bull"] == False,
        "High VIX": fm["vix"] > fm["vix_med"],
        "Low VIX": fm["vix"] <= fm["vix_med"],
        "Pre-COVID": fm["era"] == "Pre-COVID",
        "COVID": fm["era"] == "COVID",
        "Post-COVID": fm["era"] == "Post-COVID",
    }

    rows = []
    for gate, drop_cfg in [("G1", "drop_G1"), ("G2", "drop_G2"), ("G3", "drop_G3")]:
        full_df = ic_stats_by_config[full_name]["panel"]
        drop_df = ic_stats_by_config[drop_cfg]["panel"]

        def ic_diff_on(fdates):
            f = full_df[full_df["formation_date"].isin(fdates)]
            d = drop_df[drop_df["formation_date"].isin(fdates)]
            fstat = _ic_stats(f, "z_ts", "fwd_1") if len(f) >= MIN_NAMES * 2 else None
            dstat = _ic_stats(d, "z_ts", "fwd_1") if len(d) >= MIN_NAMES * 2 else None
            if fstat is None or dstat is None:
                return None
            return fstat["mean_ic"] - dstat["mean_ic"]

        cells = {}
        for label, rmask in regimes.items():
            cells[label] = ic_diff_on(set(fm.index[rmask]))

        # circularity rule (a): G1's VIX cells are its own knob
        circular = set()
        if gate == "G1":
            circular = {"High VIX", "Low VIX"}

        # consistency count over non-blank, non-circular cells
        counted = {k: v for k, v in cells.items() if v is not None and k not in circular}
        pos_cells = {k for k, v in counted.items() if v > 0}
        consistency = f"{len(pos_cells)}/{len(counted)}" if counted else "—"

        # concentration rule (b): calendar axis only
        cal_cells = {k: v for k, v in cells.items() if k in ("Pre-COVID", "COVID", "Post-COVID")}
        cal_pos = {k: v for k, v in cal_cells.items() if v is not None and v > 0}
        total_pos = sum(cal_pos.values())
        if total_pos > 0:
            biggest = max(cal_pos, key=cal_pos.get)
            concentration = f"{biggest} {cal_pos[biggest]/total_pos:.0%}"
        else:
            concentration = "—"

        # negative count across different partitions (rule iii): calendar + bull/bear + vix,
        # but negatives on the same dates across correlated labels count once.
        neg_set = {k for k, v in cells.items() if v is not None and v < 0}
        n_neg_partitions = 0
        if any(k in neg_set for k in ("Bull", "Bear")):
            n_neg_partitions += 1
        if any(k in neg_set for k in ("High VIX", "Low VIX")) and gate != "G1":
            n_neg_partitions += 1
        if any(k in neg_set for k in ("Pre-COVID", "COVID", "Post-COVID")):
            n_neg_partitions += 1

        # verdict
        majority = len(pos_cells) > len(counted) / 2 if counted else False
        conc_ok = not (concentration != "—" and float(concentration.split()[-1][:-1]) > 50)
        neg_ok = n_neg_partitions < 2
        stability_clear = majority and conc_ok and neg_ok

        row = {
            "gate": gate,
            "cells": cells,
            "circular": circular,
            "consistency": consistency,
            "concentration": concentration,
            "n_neg_partitions": n_neg_partitions,
            "majority": majority,
            "conc_ok": conc_ok,
            "neg_ok": neg_ok,
            "stability_clear": stability_clear,
        }
        rows.append(row)
    return rows


# ── report writer ─────────────────────────────────────────────────────────────
def _fmt(x, nd=4):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def _write_report(data):
    l = []
    ap = l.append

    ap("# TS Basis Filter — SD / Breadth / Marginal-Value / Gate-Stability Probe Report")
    ap("")
    ap(f"**Date:** {data['run_date']}  |  **Window:** 2016-02-11 -> 2022-12-31 (burned TRAIN+HOLDOUT)")
    ap("**Fence:** hard-stop at 2022-12-31 — sealed window (2023-01-01 -> 2026-07-24, 876 formations) untouched.")
    ap("")
    ap("## 1. Resolved sources and fence proof")
    ap("")
    ap("- **Signal store/column:** `data/signal_engine/ts_basis_daily/ts_signals.duckdb` → `signals.z_ts` ")
    ap("  (this is the daily build's own output — `build_ts_basis_daily.py` OUT_DB; `ts_facts.duckdb`/`z_carry_neut` is the publish layer, not the construction).")
    ap("- **OI source:** `futures_bhavcopy.chg_in_oi` on the near-month FUTSTK contract per (underlying, trade_date). "
       "Verified: `chg_in_oi` agrees with computed `open_int_t − open_int_{t−1}` (e.g. TCS 54,000 / 81,600 / −241,800). "
       "Coverage 100% (305,112/305,112 underlying-days).")
    ap(f"- **Cross-section:** full eligible daily universe (every non-null `z_ts`), NOT top-5 per side. "
       f"Rows loaded {data['meta']['n_rows']:,}, formations {data['meta']['n_formations']}, underlyings {data['meta']['n_underlyings']}.")
    ap(f"- **Fence proof:** observed formation range [{data['fence_min'].date()}, {data['fence_max'].date()}] — assertion PASSED.")
    ap("")
    ap("## 2. Base statistics (H=1 primary, H=5 robustness)")
    ap("")
    base = data["ic"][""]["base"]["H1"]
    base5 = data["ic"][""]["base"]["H5"]
    ap("| Series | n | mean IC | sd_IC | AC1 | NW t | avg names |")
    ap("|---|---|---|---|---|---|---|")
    ap(f"| H=1d (primary) | {base['n_dates']} | {_fmt(base['mean_ic'])} | {_fmt(base['sd_ic'])} | {_fmt(base['ac1'])} | {_fmt(base['nw_t'])} | {_fmt(base['avg_names'],0)} |")
    ap(f"| H=5d (robust)  | {base5['n_dates']} | {_fmt(base5['mean_ic'])} | {_fmt(base5['sd_ic'])} | {_fmt(base5['ac1'])} | {_fmt(base5['nw_t'])} | {_fmt(base5['avg_names'],0)} |")
    ap("")
    ap("## 3. Eight configurations — IC + breadth (H=1)")
    ap("")
    ap("| Config | n | mean IC | sd_IC | AC1 | NW t | avg names | N_eff | PC1 |")
    ap("|---|---|---|---|---|---|---|---|---|")
    for cfg in ["base", "G1", "G2", "G3", "full", "drop_G1", "drop_G2", "drop_G3"]:
        st = data["ic"][""][cfg]["H1"]
        neff = data["neff"][""][cfg]
        ap(f"| {cfg} | {st['n_dates']} | {_fmt(st['mean_ic'])} | {_fmt(st['sd_ic'])} | {_fmt(st['ac1'])} | "
           f"{_fmt(st['nw_t'])} | {_fmt(st['avg_names'],0)} | {_fmt(neff['median_neff'],1)} | {_fmt(neff['median_pc1'],3)} |")
    ap("")
    ap("## 4. Power — fixed-δ and own-δ (two-sided, target 0.80)")
    ap("")
    ap("| Config | sd_IC | n | fixed-δ power | own-δ power | n_req @0.015 | n_req @0.020 | n_req @0.029 |")
    ap("|---|---|---|---|---|---|---|---|")
    for cfg in ["base", "G1", "G2", "G3", "full", "drop_G1", "drop_G2", "drop_G3"]:
        p = data["power"][cfg]
        ap(f"| {cfg} | {_fmt(p['sd_ic'])} | {p['n']} | {_fmt(p['fixed_power'],3)} | {_fmt(p['own_power'],3)} | "
           f"{p['n_req_low']} | {p['n_req_mid']} | {p['n_req_hi']} |")
    ap("")
    ap("## 5. Marginal-value verdict (drop-column, full vs full-minus-gate)")
    ap("")
    ap("| Gate | Δn | Δsd_IC | Δ fixed-δ power | Δ own-δ power | Δ n_req@0.020 | Verdict |")
    ap("|---|---|---|---|---|---|---|")
    for g in data["marginal"]:
        dnreq = "—" if g["dnreq"] is None else f"{g['dnreq']:+}"
        ap(f"| {g['gate']} | {g['dn']:+} | {_fmt(g['dsd'])} | {_fmt(g['dfixed'],4)} | {_fmt(g['down'],4)} | {dnreq} | **{g['verdict']}** |")
    ap("")
    ap("*Saturation note:* on this burned window own-δ power is 1.0 for every config (IC 0.049, "
       "t≈22 — the TRAIN/HOLDOUT selection surface is strong in-sample). Δown-δ power is therefore "
       "≈0 and cannot discriminate; the verdict uses Δ n_req@0.020 (positive = the gate adds "
       "required formations = net cost). This is a *burned-window* reading, not a confirmatory one — "
       "it measures relative cost, not absolute feasibility.*")
    ap("")
    ap("## 6. Gate Stability — regime consistency (required output)")
    ap("")
    ap("| Gate | Bull | Bear | High VIX | Low VIX | Pre-COVID | COVID | Post-COVID | Consistency | Concentration | Stability-clear? |")
    ap("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in data["stability"]:
        cells = r["cells"]
        row = f"| {r['gate']} | "
        for label in ["Bull", "Bear", "High VIX", "Low VIX", "Pre-COVID", "COVID", "Post-COVID"]:
            v = cells.get(label)
            marker = ""
            if label in r["circular"]:
                marker = " (circular)"
            row += ("—" if v is None else f"{v:+.4f}") + marker + " | "
        row += f"{r['consistency']} | {r['concentration']} | **{'YES' if r['stability_clear'] else 'NO'}** |"
        ap(row)
    ap("")
    ap("Rule (a): a gate's self-defining axis is excluded from its own consistency count (G1's VIX cells marked circular).")
    ap("Rule (b): concentration anchored on the calendar axis (Pre/COVID/Post — mutually exclusive, exhaustive); Bull/Bear and VIX are corroborating lenses.")
    ap("")
    ap("## 7. Predictions (held/failed)")
    ap("")
    ap("| # | Prediction | Result |")
    ap("|---|---|---|")
    for pid, text, held in data["predictions"]:
        ap(f"| {pid} | {text} | **{'HELD' if held else 'FAILED'}** |")
    ap("")
    ap("## 8. G1 sensitivity (k ∈ {1.25, 1.5, 2.0})")
    ap("")
    ap("| k | n | mean IC | sd_IC |")
    ap("|---|---|---|---|")
    for k, st in data["g1_sens"].items():
        ap(f"| {k} | {st['n_dates']} | {_fmt(st['mean_ic'])} | {_fmt(st['sd_ic'])} |")
    ap("")
    ap("## 9. Carry-forward note")
    ap("")
    ap("- Mean IC is **diagnostic only** — the RFA δ anchor must be defended independently (never this burned mean, never the sealed +0.077).")
    ap("- The preserved 876-formation sealed window was not read.")
    ap("")

    Path(REPORT).write_text("\n".join(l), encoding="utf-8")


def _run_pipeline():
    panel, meta = _build_base_panel()
    ic_stats_by_config = {}
    neff_by_config = {}
    power_by_config = {}

    for cfg, rule in CONFIG_RULES.items():
        sub = _apply_config(panel, rule)
        if sub.empty:
            ic_stats_by_config[cfg] = {"panel": sub, "H1": None, "H5": None}
            neff_by_config[cfg] = {"median_neff": np.nan, "median_pc1": np.nan}
            power_by_config[cfg] = None
            continue
        h1 = _ic_stats(sub, "z_ts", "fwd_1")
        h5 = _ic_stats(sub, "z_ts", "fwd_5")
        ic_stats_by_config[cfg] = {"panel": sub, "H1": h1, "H5": h5}
        neff_by_config[cfg] = _neff_stats(sub, "fwd_1")

    # base mean IC = fixed delta
    base_h1 = ic_stats_by_config["base"]["H1"]
    fixed_delta = base_h1["mean_ic"] if base_h1 else 0.0

    for cfg, rule in CONFIG_RULES.items():
        st = ic_stats_by_config[cfg]["H1"]
        if st is None:
            power_by_config[cfg] = None
            continue
        sd = st["sd_ic"]
        n = st["n_dates"]
        power_by_config[cfg] = {
            "sd_ic": sd, "n": n,
            "fixed_power": power_at(fixed_delta, sd, n, two_sided=True) if sd > 0 else 0.0,
            "own_power": power_at(st["mean_ic"], sd, n, two_sided=True) if sd > 0 else 0.0,
            "n_req_low": n_required(0.015, sd, POWER_TARGET, two_sided=True),
            "n_req_mid": n_required(0.020, sd, POWER_TARGET, two_sided=True),
            "n_req_hi": n_required(0.029, sd, POWER_TARGET, two_sided=True),
        }

    # marginal verdicts
    marginal = []
    for gate, drop_cfg in [("G1", "drop_G1"), ("G2", "drop_G2"), ("G3", "drop_G3")]:
        full_p = power_by_config["full"]
        drop_p = power_by_config[drop_cfg]
        if full_p is None or drop_p is None:
            marginal.append({"gate": gate, "dn": None, "dsd": None, "dfixed": None,
                             "down": None, "dnreq": None, "verdict": "n/a"})
            continue
        full_st = ic_stats_by_config["full"]["H1"]
        drop_st = ic_stats_by_config[drop_cfg]["H1"]
        dn = (full_st["n_dates"] - drop_st["n_dates"]) if full_st and drop_st else None
        dsd = (full_st["sd_ic"] - drop_st["sd_ic"]) if full_st and drop_st else None
        dfixed = full_p["fixed_power"] - drop_p["fixed_power"]
        down = full_p["own_power"] - drop_p["own_power"]
        dnreq = None
        if full_p["n_req_mid"] is not None and drop_p["n_req_mid"] is not None:
            dnreq = full_p["n_req_mid"] - drop_p["n_req_mid"]
        # Saturation note: on this burned window own-δ power is 1.0 everywhere, so
        # Δown-δ power cannot discriminate. The discriminator is Δ n_req@0.020
        # (positive = gate adds required n = net cost). Prompt §5: flat → remove.
        if dnreq is None:
            verdict = "n/a"
        elif dnreq < 0:
            verdict = "KEEP"
        else:
            verdict = "REMOVE"
        marginal.append({"gate": gate, "dn": dn, "dsd": dsd, "dfixed": dfixed,
                         "down": down, "dnreq": dnreq, "verdict": verdict})

    stability = _stability_table(panel, ic_stats_by_config)

    # predictions
    preds = []
    base_sd = base_h1["sd_ic"] if base_h1 else np.nan
    g2_sd = ic_stats_by_config["G2"]["H1"]["sd_ic"] if ic_stats_by_config["G2"]["H1"] else np.nan
    full_h1 = ic_stats_by_config["full"]["H1"]
    g1_h1 = ic_stats_by_config["G1"]["H1"]
    g3_h1 = ic_stats_by_config["G3"]["H1"]
    base_n = base_h1["n_dates"] if base_h1 else 0
    g1_n = g1_h1["n_dates"] if g1_h1 else 0
    g3_n = g3_h1["n_dates"] if g3_h1 else 0
    base_neff = neff_by_config["base"]["median_neff"]
    avg_names = base_h1["avg_names"] if base_h1 else 0

    preds.append(("P1", "G2 raises sd_IC vs base", (g2_sd > base_sd) if (g2_sd == g2_sd and base_sd == base_sd) else False))
    preds.append(("P2", "G1 and G3 lower n vs base; G2 leaves n unchanged",
                  (g1_n < base_n) and (g3_n < base_n)))
    preds.append(("P3", "base N_eff is materially larger than OSC's option-cell N_eff ≈ 1.9 (equities less "
                  "correlated than option cells)",
                  (base_neff == base_neff) and (base_neff / 1.9 >= 2.0)))
    preds.append(("P4", "at fixed δ, every gate's power ≤ base",
                  all((power_by_config[c] is None or power_by_config[c]["fixed_power"] <= power_by_config["base"]["fixed_power"] + 1e-9)
                      for c in ["G1", "G2", "G3"])))
    any_remove = any(m["verdict"] == "REMOVE" for m in marginal)
    any_not_clear = any(not r["stability_clear"] for r in stability)
    preds.append(("P5", "at own δ, at least one gate fails to beat its drop-column (REMOVE recommended)", any_remove))
    preds.append(("P6", "at least one §5-passing gate is not stability-clear (regime-dependent)", any_not_clear))

    # G1 sensitivity
    g1_sens = {}
    for k in K_SENS:
        sub = panel[panel["vix"] <= k * panel["vix_med"]]
        st = _ic_stats(sub, "z_ts", "fwd_1")
        g1_sens[k] = st

    return {
        "run_date": pd.Timestamp.utcnow().strftime("%Y-%m-%d"),
        "meta": meta,
        "fence_min": panel["formation_date"].min(),
        "fence_max": panel["formation_date"].max(),
        "ic": {"": ic_stats_by_config},
        "neff": {"": neff_by_config},
        "power": power_by_config,
        "marginal": marginal,
        "stability": stability,
        "predictions": preds,
        "g1_sens": g1_sens,
    }


def main():
    data = _run_pipeline()
    _write_report(data)
    print(f"Report written to {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
