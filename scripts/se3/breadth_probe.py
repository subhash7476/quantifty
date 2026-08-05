"""SE-3 Breadth / SD Probe — measure sd_IC and effective breadth of the Nifty 50
constituent option cross-section.

Reads the already-burned 2023-01-02 -> 2025-12-31 window on the STOCK leg and the
index leg. The 2016-02-11 -> 2022-12-31 (1,701 dates) and 2021-2022 stock windows
are fenced out and never touched. Produces a single script-generated report.

Public entry-points (importable):
  build_panel()  -> {panel, stats, attrit, ...}
  run()          -> writes report, calls build_panel internally
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import zipfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

from scripts.osc.sd_probe import (
    black76_delta,
    black76_vega,
    implied_vol,
    _parity_forward,
)
from scripts.rfa.power import n_required

# ── pinned constants ─────────────────────────────────────────────────────────
DTE_LO = 7
DTE_HI = 60
SETTLE_FLOOR = 0.50
MONEYNESS_BAND = 0.10
MIN_NAMES_A = 20
MIN_NAMES_IC = 20
MIN_PAIRED_B = 40
RV_WINDOW = 21
RV_MIN_OBS = 18
BETA_WINDOW = 60
NW_LAG = 5
ROLLING_WINDOW = 60
POWER_TARGET = 0.80

FENCE_START = pd.Timestamp("2023-01-02")
FENCE_END = pd.Timestamp("2025-12-31")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STOCK_OPTIONS_DB = PROJECT_ROOT / "data" / "market_data" / "stock_options_bhavcopy.duckdb"
OPTIONS_DB = PROJECT_ROOT / "data" / "market_data" / "options_bhavcopy.duckdb"
FUTURES_DB = PROJECT_ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REF_DIR = PROJECT_ROOT / "data" / "reference"
MANIFEST_PATH = REF_DIR / "mcwb_manifest.json"

DUMMY_SYMBOLS = {"DUMMYREL", "DUMMYTATAM", "DUMMYHDLVR"}


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


def _assert_fence(df):
    obs_min = df["trade_date"].min()
    obs_max = df["trade_date"].max()
    print(f"Fence: observed range [{obs_min.date()}, {obs_max.date()}]")
    assert obs_min >= FENCE_START, f"FENCE VIOLATION: min trade_date {obs_min.date()} < {FENCE_START.date()}"
    assert obs_max <= FENCE_END, f"FENCE VIOLATION: max trade_date {obs_max.date()} > {FENCE_END.date()}"
    return obs_min, obs_max


# ── data loaders ─────────────────────────────────────────────────────────────
def _load_stock_options(member_syms):
    ph = ",".join(f"'{s}'" for s in sorted(member_syms))
    con = duckdb.connect(str(STOCK_OPTIONS_DB), read_only=True)
    df = con.execute(
        f"""
        SELECT underlying, expiry_dt, strike, option_type, settle, contracts, open_int, trade_date
        FROM stock_options_bhavcopy
        WHERE underlying IN ({ph})
          AND trade_date >= '2023-01-02'
          AND trade_date <= '2025-12-31'
        ORDER BY trade_date, underlying, expiry_dt
        """
    ).fetchdf()
    con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["expiry_dt"] = pd.to_datetime(df["expiry_dt"])
    return df


def _load_index_options():
    con = duckdb.connect(str(OPTIONS_DB), read_only=True)
    df = con.execute(
        """
        SELECT symbol, expiry_dt, strike, option_type, settle, contracts, open_int, trade_date
        FROM option_bhavcopy
        WHERE symbol = 'NIFTY'
          AND trade_date >= '2023-01-02'
          AND trade_date <= '2025-12-31'
        ORDER BY trade_date, expiry_dt, strike, option_type
        """
    ).fetchdf()
    con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["expiry_dt"] = pd.to_datetime(df["expiry_dt"])
    return df


def _load_futures(member_syms):
    ph = ",".join(f"'{s}'" for s in sorted(member_syms) + ["NIFTY"])
    con = duckdb.connect(str(FUTURES_DB), read_only=True)
    df = con.execute(
        f"""
        SELECT underlying, expiry_dt, trade_date, inst_type, settle
        FROM futures_bhavcopy
        WHERE underlying IN ({ph})
          AND trade_date >= '2023-01-02'
          AND trade_date <= '2025-12-31'
        """
    ).fetchdf()
    con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["expiry_dt"] = pd.to_datetime(df["expiry_dt"])
    return df


def _mcwb_rows(raw, filename):
    """Yield {symbol, weight} from an MCWB CSV. Uses the header line to locate
    columns by name so layout drift across archives does not matter."""
    textio = io.StringIO(raw)
    reader = csv.reader(textio)
    header = None
    rows = []
    for line in reader:
        if not line or not line[0].strip():
            continue
        joined = ",".join(line)
        if "Security Symbol" in joined:
            header = line
            continue
        if header is not None:
            rows.append(line)
    if header is None:
        sys.exit(f"FATAL: header not found in {filename}")
    try:
        sym_idx = header.index("Security Symbol")
    except ValueError:
        sys.exit(f"FATAL: Security Symbol column not found in {filename}")
    w_idx = None
    for i, col in enumerate(header):
        if col.strip() in ("Weightage (%)", "Weightage", "Weightage%", "Index Weightage (%)"):
            w_idx = i
            break
    out = []
    for r in rows:
        if len(r) <= sym_idx:
            continue
        sym = r[sym_idx].strip().upper()
        if not sym:
            continue
        w = None
        if w_idx is not None and len(r) > w_idx:
            wstr = r[w_idx].strip()
            if wstr not in ("", "-"):
                try:
                    w = float(wstr.replace("%", ""))
                except ValueError:
                    sys.exit(f"FATAL: unparseable weight {wstr!r} in {filename}")
        out.append({"symbol": sym, "weight": w})
    return out


def _load_mcwb():
    """Parse MCWB snapshots -> {month_str: {symbol: weight_pct}}.

    Also returns pollution findings (symbols matching DUMMY*/TMPV* seen in any
    valid snapshot), which the caller must NOT treat as members.
    """
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    valid = [r for r in manifest["records"] if r["status"] == "valid"]
    snapshots = {}
    findings = {}
    for rec in sorted(valid, key=lambda r: r["month"]):
        month = rec["month"]
        with zipfile.ZipFile(REF_DIR / rec["filename"]) as zf:
            names = zf.namelist()
            if "nifty50_mcwb.csv" not in names:
                sys.exit(f"FATAL: nifty50_mcwb.csv missing from {rec['filename']}")
            raw = zf.read("nifty50_mcwb.csv").decode("utf-8", errors="replace")
        members = {}
        for row in _mcwb_rows(raw, rec["filename"]):
            sym = row["symbol"]
            if sym in DUMMY_SYMBOLS or sym.startswith("DUMMY") or sym.startswith("TMPV"):
                findings[sym] = month
                continue
            if row["weight"] is None:
                sys.exit(
                    f"FATAL: weight column not located in {rec['filename']} layout; "
                    "stopping per §3.1 (do not substitute equal weights)."
                )
            members[sym] = row["weight"]
        snapshots[month] = members
    return snapshots, findings


def _membership_for_date(snapshots, td):
    """Month M's membership applies to trading dates in month M+1 only.

    Returns the snapshot dict for the calendar month immediately before td's
    month.  Raises SystemExit if the required snapshot is missing (never apply
    an older snapshot to a newer month — that is lookahead).
    """
    if td.month == 1:
        key = f"{td.year - 1:04d}-12-01"
    else:
        key = f"{td.year:04d}-{td.month - 1:02d}-01"
    if key not in snapshots:
        sys.exit(f"FATAL: no MCWB snapshot for month {key} (needed for trade date {td.date()})")
    return snapshots[key]


# ── core helpers ─────────────────────────────────────────────────────────────
def _dte(expiry, trade_date):
    return (expiry - trade_date).days


def _pick_expiry(expiries, trade_date, lo=DTE_LO, hi=DTE_HI):
    """Nearest expiry with lo <= DTE <= hi. Returns expiry or None."""
    best = None
    best_dte = None
    for exp in expiries:
        d = _dte(exp, trade_date)
        if lo <= d <= hi:
            if best is None or d < best_dte:
                best, best_dte = exp, d
    return best


def _ic_series(records, min_cells):
    recs = []
    for td, grp in records.groupby("trade_date"):
        if len(grp) < min_cells:
            continue
        ic, _ = stats.spearmanr(grp["richness"], grp["dh_return_scaled"])
        if not np.isnan(ic):
            recs.append({"trade_date": td, "ic": ic, "n": len(grp)})
    if not recs:
        return None, None
    df = pd.DataFrame(recs).sort_values("trade_date")
    series = df["ic"].values
    mean_ic = float(np.mean(series))
    sd_ic = float(np.std(series, ddof=1))
    ac1 = float(np.corrcoef(series[:-1], series[1:])[0, 1]) if len(series) > 1 else np.nan
    nw_mean, nw_se = _newey_west(series, NW_LAG)
    nw_t = nw_mean / nw_se if nw_se > 0 else np.nan
    return series, {"mean_ic": mean_ic, "sd_ic": sd_ic, "ac1": ac1, "nw_t": nw_t, "nw_se": nw_se, "n_dates": len(series)}


def _corr_matrix_stats(panel):
    """panel: DataFrame rows=dates, cols=names, values=dh_return_scaled.
    Returns rho_bar, N_eff, pc1_share, N (cols populated throughout)."""
    filled = panel.dropna(axis=1)
    N = filled.shape[1]
    if N < 3:
        return None
    corr = filled.corr().values
    idx_upper = np.triu_indices(N, k=1)
    pairwise = corr[idx_upper]
    rho_bar = float(np.mean(pairwise))
    neff = N / (1 + (N - 1) * rho_bar) if N > 1 else N
    X_std = (filled - filled.mean()) / filled.std(ddof=1)
    cov = np.cov(X_std.values.T)
    eig = np.linalg.eigvalsh(cov)
    pc1 = float(eig[-1] / eig.sum()) if eig.sum() > 0 else np.nan
    return {"rho_bar": rho_bar, "neff": neff, "pc1": pc1, "N": N}


def _rolling_breadth(panel):
    rho_list, neff_list, pc1_list, n_list = [], [], [], []
    dates = panel.index.sort_values()
    for i in range(ROLLING_WINDOW - 1, len(dates)):
        window = panel.loc[dates[i - ROLLING_WINDOW + 1 : i + 1]]
        s = _corr_matrix_stats(window)
        if s:
            rho_list.append(s["rho_bar"])
            neff_list.append(s["neff"])
            pc1_list.append(s["pc1"])
            n_list.append(s["N"])
    return rho_list, neff_list, pc1_list, n_list


# ── panel builder ────────────────────────────────────────────────────────────
def _front_month_rv(g):
    """Given a per-underlying FUTSTK frame (trade_date, expiry_dt, settle),
    build the front-month (nearest expiry with DTE >= 7) series, compute log
    returns, drop returns computed across a roll, and return a frame with the
    trailing 21-day annualized RV (>=18 observations required)."""
    g = g.sort_values("trade_date")
    fronts = []
    for td, gg in g.groupby("trade_date"):
        best = _pick_expiry(gg["expiry_dt"].unique(), td, lo=DTE_LO, hi=10_000)
        if best is None:
            continue
        row = gg[gg["expiry_dt"] == best].iloc[0]
        fronts.append({"trade_date": td, "expiry_dt": best, "settle": row["settle"]})
    if not fronts:
        return None
    fdf = pd.DataFrame(fronts).sort_values("trade_date").reset_index(drop=True)
    fdf["prev_exp"] = fdf["expiry_dt"].shift(1)
    fdf["prev_settle"] = fdf["settle"].shift(1)
    fdf["ret"] = np.log(fdf["settle"] / fdf["prev_settle"])
    fdf.loc[fdf["expiry_dt"] != fdf["prev_exp"], "ret"] = np.nan
    fdf["rv"] = fdf["ret"].rolling(RV_WINDOW, min_periods=RV_MIN_OBS).std(ddof=1) * math.sqrt(252)
    fdf["n_obs"] = fdf["ret"].rolling(RV_WINDOW, min_periods=RV_MIN_OBS).count()
    fdf.loc[fdf["n_obs"] < RV_MIN_OBS, "rv"] = np.nan
    return fdf


def build_panel():
    snapshots, findings = _load_mcwb()
    print(f"MCWB snapshots: {len(snapshots)} valid; pollution findings: {findings}")

    # Only snapshots that feed the fence (month M applies to month M+1; the
    # fence spans 2023-01..2025-12, so snapshots 2022-12..2025-11 are used).
    fence_snap_months = set()
    for td in pd.date_range(FENCE_START, FENCE_END, freq="MS"):
        if td.month == 1:
            fence_snap_months.add(f"{td.year - 1:04d}-12-01")
        else:
            fence_snap_months.add(f"{td.year:04d}-{td.month - 1:02d}-01")
    member_syms = set()
    for month, m in snapshots.items():
        if month in fence_snap_months:
            member_syms |= set(m.keys())
    member_syms.difference_update(DUMMY_SYMBOLS)
    print(f"Union of member symbols across fence window: {len(member_syms)}")

    raw_stock = _load_stock_options(member_syms)
    raw_idx = _load_index_options()
    raw_fut = _load_futures(member_syms)

    obs = {
        "stock": _assert_fence(raw_stock),
        "idx": _assert_fence(raw_idx),
        "fut": _assert_fence(raw_fut),
    }

    # --- futures: FUTSTK settle lookup + front-month series per name ---
    fut_stk = raw_fut[raw_fut["inst_type"] == "FUTSTK"].copy()
    fut_stk["dte"] = (fut_stk["expiry_dt"] - fut_stk["trade_date"]).dt.days
    fut_stk_settle = fut_stk.set_index(["underlying", "expiry_dt", "trade_date"])["settle"]
    fut_idx = raw_fut[(raw_fut["inst_type"] == "FUTIDX") & (raw_fut["underlying"] == "NIFTY")]
    fut_idx_settle = fut_idx.set_index(["expiry_dt", "trade_date"])["settle"]

    # --- PIT membership per date (month M applies to month M+1) ---
    all_dates = sorted(raw_idx["trade_date"].unique())
    membership = {}
    for td in all_dates:
        membership[td] = set(_membership_for_date(snapshots, td).keys())

    # --- apply membership + F&O eligibility to stock options ---
    fo_live = set(zip(fut_stk["underlying"], fut_stk["trade_date"]))
    stock_rows_loaded = len(raw_stock)
    member_lookup = {}
    for td, syms in membership.items():
        for s in syms:
            if (s, td) in fo_live:
                member_lookup[(s, td)] = True
    raw_stock["_key"] = list(zip(raw_stock["underlying"], raw_stock["trade_date"]))
    is_member = raw_stock["_key"].map(lambda k: k in member_lookup).astype(bool)
    raw_stock = raw_stock[is_member].drop(columns=["_key"]).reset_index(drop=True)
    stock_after_membership = len(raw_stock)

    attrit = {
        "stock_rows_loaded": stock_rows_loaded,
        "idx_rows_loaded": len(raw_idx),
        "stock_after_membership": stock_after_membership,
        "stock_traded": 0,
        "idx_traded": 0,
        "stock_after_expiry": 0,
        "idx_after_expiry": 0,
        "stock_after_forward": 0,
        "idx_after_forward": 0,
        "stock_after_settle": 0,
        "idx_after_settle": 0,
        "stock_after_moneyness": 0,
        "idx_after_moneyness": 0,
        "stock_after_iv": 0,
        "idx_after_iv": 0,
        "dropped_no_expiry": {"stock": 0, "idx": 0},
        "dropped_no_forward": {"stock": 0, "idx": 0},
        "dropped_no_atm": {"stock": 0, "idx": 0},
        "iv_discard": {"stock": 0, "idx": 0},
        "iv_attempted": {"stock": 0, "idx": 0},
        "pairing_dropped": 0,
    }

    # ── stock options pipeline ───────────────────────────────────────────────
    stock_traded = raw_stock[(raw_stock["contracts"] > 0) & (raw_stock["open_int"] > 0)]
    attrit["stock_traded"] = len(stock_traded)

    # Group traded cells for fast per-(date, underlying) access.
    stock_grouped = {key: grp for key, grp in stock_traded.groupby(["trade_date", "underlying"])}

    def _stock_forward(td, underlying, expiry):
        """FUTSTK settle preferred; parity fallback on that (date, underlying,
        expiry)'s traded cells. Returns float or NaN."""
        try:
            f = fut_stk_settle.loc[(underlying, expiry, td)]
            if np.isfinite(f) and f > 0:
                return float(f)
        except KeyError:
            pass
        cells = stock_grouped.get((td, underlying))
        if cells is None:
            return np.nan
        g = cells[cells["expiry_dt"] == expiry]
        calls = g[g["option_type"] == "CE"][["strike", "settle"]]
        puts = g[g["option_type"] == "PE"][["strike", "settle"]]
        return _parity_forward(calls, puts, expiry, td)

    stock_records = []
    for (td, underlying), grp in stock_grouped.items():
        expiries = sorted(grp["expiry_dt"].unique())
        expiry = _pick_expiry(expiries, td)
        if expiry is None:
            attrit["dropped_no_expiry"]["stock"] += 1
            continue
        g = grp[grp["expiry_dt"] == expiry]
        attrit["stock_after_expiry"] += len(g)

        F = _stock_forward(td, underlying, expiry)
        if not np.isfinite(F) or F <= 0:
            attrit["dropped_no_forward"]["stock"] += 1
            continue
        attrit["stock_after_forward"] += len(g)

        gs = g[g["settle"] >= SETTLE_FLOOR]
        attrit["stock_after_settle"] += len(gs)
        gm = gs[np.abs(np.log(gs["strike"] / F)) <= MONEYNESS_BAND]
        attrit["stock_after_moneyness"] += len(gm)

        calls = gm[gm["option_type"] == "CE"]
        puts = gm[gm["option_type"] == "PE"]
        iv_call_cell = iv_put_cell = None
        T = _dte(expiry, td) / 365.0
        if len(calls):
            c = calls[calls["strike"] >= F]
            if len(c):
                c = c.loc[c["strike"].idxmin()]
                attrit["iv_attempted"]["stock"] += 1
                iv = implied_vol(c["settle"], F, c["strike"], T, "CE")
                if np.isnan(iv):
                    attrit["iv_discard"]["stock"] += 1
                else:
                    iv_call_cell = (c["strike"], "CE", iv, c["settle"])
        if len(puts):
            p = puts[puts["strike"] < F]
            if len(p):
                p = p.loc[p["strike"].idxmax()]
                attrit["iv_attempted"]["stock"] += 1
                iv = implied_vol(p["settle"], F, p["strike"], T, "PE")
                if np.isnan(iv):
                    attrit["iv_discard"]["stock"] += 1
                else:
                    iv_put_cell = (p["strike"], "PE", iv, p["settle"])
        if iv_call_cell is None and iv_put_cell is None:
            attrit["dropped_no_atm"]["stock"] += 1
            continue

        sigmas = [c[2] for c in (iv_call_cell, iv_put_cell) if c]
        stock_records.append(
            {
                "trade_date": td,
                "underlying": underlying,
                "expiry_dt": expiry,
                "F_t": F,
                "sigma": float(np.mean(sigmas)),
                "iv_call": iv_call_cell,
                "iv_put": iv_put_cell,
            }
        )

    stock_df = pd.DataFrame(stock_records) if stock_records else pd.DataFrame(
        columns=["trade_date", "underlying", "expiry_dt", "F_t", "sigma", "iv_call", "iv_put"]
    )
    attrit["stock_after_iv"] = len(stock_df)

    # ── index (NIFTY) options pipeline ───────────────────────────────────────
    idx_traded = raw_idx[(raw_idx["contracts"] > 0) & (raw_idx["open_int"] > 0)]
    attrit["idx_traded"] = len(idx_traded)
    idx_grouped = {key: grp for key, grp in idx_traded.groupby("trade_date")}

    idx_records = []
    for td, grp in idx_grouped.items():
        expiries = sorted(grp["expiry_dt"].unique())
        expiry = _pick_expiry(expiries, td)
        if expiry is None:
            attrit["dropped_no_expiry"]["idx"] += 1
            continue
        g = grp[grp["expiry_dt"] == expiry]
        attrit["idx_after_expiry"] += len(g)

        calls = g[g["option_type"] == "CE"][["strike", "settle"]]
        puts = g[g["option_type"] == "PE"][["strike", "settle"]]
        F = _parity_forward(calls, puts, expiry, td)
        if not np.isfinite(F) or F <= 0:
            try:
                F = float(fut_idx_settle.loc[(expiry, td)])
            except KeyError:
                F = np.nan
        if not np.isfinite(F) or F <= 0:
            attrit["dropped_no_forward"]["idx"] += 1
            continue
        attrit["idx_after_forward"] += len(g)

        gs = g[g["settle"] >= SETTLE_FLOOR]
        attrit["idx_after_settle"] += len(gs)
        gm = gs[np.abs(np.log(gs["strike"] / F)) <= MONEYNESS_BAND]
        attrit["idx_after_moneyness"] += len(gm)

        calls = gm[gm["option_type"] == "CE"]
        puts = gm[gm["option_type"] == "PE"]
        iv_call_cell = iv_put_cell = None
        T = _dte(expiry, td) / 365.0
        if len(calls):
            c = calls[calls["strike"] >= F]
            if len(c):
                c = c.loc[c["strike"].idxmin()]
                attrit["iv_attempted"]["idx"] += 1
                iv = implied_vol(c["settle"], F, c["strike"], T, "CE")
                if np.isnan(iv):
                    attrit["iv_discard"]["idx"] += 1
                else:
                    iv_call_cell = (c["strike"], "CE", iv, c["settle"])
        if len(puts):
            p = puts[puts["strike"] < F]
            if len(p):
                p = p.loc[p["strike"].idxmax()]
                attrit["iv_attempted"]["idx"] += 1
                iv = implied_vol(p["settle"], F, p["strike"], T, "PE")
                if np.isnan(iv):
                    attrit["iv_discard"]["idx"] += 1
                else:
                    iv_put_cell = (p["strike"], "PE", iv, p["settle"])
        if iv_call_cell is None and iv_put_cell is None:
            attrit["dropped_no_atm"]["idx"] += 1
            continue

        sigmas = [c[2] for c in (iv_call_cell, iv_put_cell) if c]
        idx_records.append({"trade_date": td, "expiry_dt": expiry, "F_t": F, "sigma_I": float(np.mean(sigmas))})
    idx_df = pd.DataFrame(idx_records) if idx_records else pd.DataFrame(
        columns=["trade_date", "expiry_dt", "F_t", "sigma_I"]
    )
    attrit["idx_after_iv"] = len(idx_df)
    sigma_I = idx_df.set_index("trade_date")["sigma_I"]

    # ── §3.5 realized vol (front-month FUTSTK, trailing 21d) ─────────────────
    print("Computing realized vol per underlying ...")
    rv_map = {}
    for underlying, g in fut_stk.groupby("underlying"):
        fdf = _front_month_rv(g)
        if fdf is None or fdf.empty:
            continue
        rv_map[underlying] = fdf[["trade_date", "rv"]].dropna(subset=["rv"]).set_index("trade_date")["rv"]

    rv_series = pd.Series(np.nan, index=stock_df.index)
    for i, (u, td) in enumerate(zip(stock_df["underlying"], stock_df["trade_date"])):
        m = rv_map.get(u)
        if m is not None and td in m.index:
            rv_series.iloc[i] = m.loc[td]
    stock_df["rv"] = rv_series.values

    # ── §3.6 richness ────────────────────────────────────────────────────────
    print("Computing variant A richness ...")
    richA = pd.Series(np.nan, index=stock_df.index)
    for td, grp in stock_df.groupby("trade_date"):
        gg = grp.dropna(subset=["sigma", "rv"])
        if len(gg) < MIN_NAMES_A:
            continue
        X = np.column_stack([np.ones(len(gg)), gg["rv"].values])
        y = gg["sigma"].values
        try:
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        except np.linalg.LinAlgError:
            continue
        richA.loc[gg.index] = y - (X @ beta)
    stock_df["richA"] = richA

    print("Computing variant B richness ...")
    richB = pd.Series(np.nan, index=stock_df.index)
    all_dates_arr = np.array(sorted(stock_df["trade_date"].unique()))
    pos_map = {d: j for j, d in enumerate(all_dates_arr)}
    sigmaI_arr = np.array([sigma_I.get(d, np.nan) for d in all_dates_arr])
    for underlying, grp in stock_df.groupby("underlying"):
        sig_map = grp.set_index("trade_date")["sigma"].to_dict()
        for j, d in enumerate(all_dates_arr):
            sig_j = sig_map.get(d)
            if sig_j is None or np.isnan(sigmaI_arr[j]):
                continue
            lo = max(0, j - BETA_WINDOW + 1)
            xs = sigmaI_arr[lo : j + 1]
            ys = np.array([sig_map.get(dd, np.nan) for dd in all_dates_arr[lo : j + 1]])
            m = ~(np.isnan(xs) | np.isnan(ys))
            if m.sum() < MIN_PAIRED_B:
                continue
            if np.std(xs[m]) == 0:
                continue
            slope, intercept = np.polyfit(xs[m], ys[m], 1)
            pred = intercept + slope * sigmaI_arr[j]
            idx = pos_map[d]
            row_mask = (stock_df["underlying"] == underlying) & (stock_df["trade_date"] == d)
            stock_pos = stock_df.index[row_mask]
            if len(stock_pos):
                richB.loc[stock_pos[0]] = sig_j - pred
    stock_df["richB"] = richB

    # ── §3.7 delta-hedged returns (t -> t+1) ─────────────────────────────────
    print("Computing delta-hedged returns ...")
    date_list = sorted(stock_df["trade_date"].unique())
    dh_records = []
    stock_by_dt = {key: grp for key, grp in stock_df.groupby("trade_date")}
    # Pre-build a per-(t1, underlying, expiry) settle lookup for fast cell pairing.
    traded_settle = stock_traded.set_index(
        ["trade_date", "underlying", "expiry_dt", "strike", "option_type"]
    )["settle"]
    for i, td in enumerate(date_list[:-1]):
        t1 = date_list[i + 1]
        td_data = stock_by_dt[td]
        for _, r in td_data.iterrows():
            u = r["underlying"]
            exp = r["expiry_dt"]
            F_t = r["F_t"]
            F_t1 = _stock_forward(t1, u, exp)
            if not np.isfinite(F_t1) or F_t1 <= 0:
                attrit["pairing_dropped"] += 1
                continue
            T = _dte(exp, td) / 365.0
            scaled = []
            for cell in (r["iv_call"], r["iv_put"]):
                if cell is None:
                    continue
                strike, ot, iv, V_t = cell
                try:
                    V_t1 = float(traded_settle.loc[(t1, u, exp, strike, ot)])
                except KeyError:
                    continue
                delta_t = black76_delta(F_t, strike, iv, T, ot)
                vega_t = black76_vega(F_t, strike, iv, T)
                dh = (V_t1 - V_t) - delta_t * (F_t1 - F_t)
                scaled.append(dh / max(vega_t, 1e-6))
            if not scaled:
                attrit["pairing_dropped"] += 1
                continue
            dh_records.append({"trade_date": td, "underlying": u, "dh_return_scaled": float(np.mean(scaled))})
    dh_df = pd.DataFrame(dh_records) if dh_records else pd.DataFrame(
        columns=["trade_date", "underlying", "dh_return_scaled"]
    )
    attrit["stock_after_pairing"] = len(dh_df)

    panel = stock_df.merge(dh_df, on=["trade_date", "underlying"], how="inner")

    # ── §3.9 IC series ───────────────────────────────────────────────────────
    icA = panel[["trade_date", "richA", "dh_return_scaled"]].rename(columns={"richA": "richness"})
    icB = panel[["trade_date", "richB", "dh_return_scaled"]].rename(columns={"richB": "richness"})
    seriesA, statsA = _ic_series(icA, MIN_NAMES_IC)
    seriesB, statsB = _ic_series(icB, MIN_NAMES_IC)

    # ── §3.10 effective breadth ──────────────────────────────────────────────
    print("Computing effective breadth ...")
    dh_panel = panel.pivot_table(index="trade_date", columns="underlying", values="dh_return_scaled")
    rho_raw, neff_raw, pc1_raw, n_raw = _rolling_breadth(dh_panel)
    demeaned = dh_panel.sub(dh_panel.mean(axis=1), axis=0)
    rho_dm, neff_dm, pc1_dm, n_dm = _rolling_breadth(demeaned)

    # ── §3.8 implied correlation (diagnostic) ────────────────────────────────
    print("Computing implied correlation diagnostic ...")
    rho_imp_list, mass_list = [], []
    for td, grp in panel.groupby("trade_date"):
        sI = sigma_I.get(td, np.nan)
        if not np.isfinite(sI):
            continue
        gg = grp.dropna(subset=["sigma"])
        if len(gg) < 2:
            continue
        snap = _membership_for_date(snapshots, td)
        w = {}
        for _, r in gg.iterrows():
            u = r["underlying"]
            if u in snap:
                w[u] = snap[u]
        if len(w) < 2:
            continue
        total = sum(snap.values())
        if total <= 0:
            continue
        ws = np.array([w[u] for u in w]) / total
        sigs = np.array([gg[gg["underlying"] == u]["sigma"].iloc[0] for u in w])
        mass = float(sum(w.values()) / total)
        num = sI**2 - np.sum((ws**2) * (sigs**2))
        denom = 0.0
        for i in range(len(ws)):
            for j in range(len(ws)):
                if i != j:
                    denom += ws[i] * ws[j] * sigs[i] * sigs[j]
        if denom == 0:
            continue
        rho_imp_list.append(float(num / denom))
        mass_list.append(mass)

    rho_imp_diag = {}
    if rho_imp_list:
        rho_imp = np.array(rho_imp_list)
        rho_imp_diag = {
            "n_dates": len(rho_imp),
            "median": float(np.median(rho_imp)),
            "p10": float(np.percentile(rho_imp, 10)),
            "p90": float(np.percentile(rho_imp, 90)),
            "outside": float(np.mean((rho_imp < 0) | (rho_imp > 1))),
            "median_mass": float(np.median(mass_list)),
        }

    # ── §5 decision ladder ───────────────────────────────────────────────────
    def _rung(sd_ic, n):
        if n_required(0.015, sd_ic, POWER_TARGET, True) is not None and n_required(0.015, sd_ic, POWER_TARGET, True) <= n:
            return "Green"
        if n_required(0.020, sd_ic, POWER_TARGET, True) <= n:
            return "Amber"
        if n_required(0.029, sd_ic, POWER_TARGET, True) <= n:
            return "Red-amber"
        return "ABANDON"

    n_permissive, n_strict = 1701, 495
    ladder = {}
    for v, st in (("A", statsA), ("B", statsB)):
        if st is None:
            ladder[v] = None
            continue
        sd = st["sd_ic"]
        ladder[v] = {
            "sd_ic": sd,
            "permissive": _rung(sd, n_permissive),
            "strict": _rung(sd, n_strict),
            "n_req": {d: n_required(d, sd, POWER_TARGET, True) for d in (0.015, 0.020, 0.029)},
        }

    # ── names-per-day and first-usable-date ──────────────────────────────────
    namesA = panel[panel["richA"].notna()].groupby("trade_date").size()
    namesB = panel[panel["richB"].notna()].groupby("trade_date").size()

    def _by_year(s):
        if len(s) == 0:
            return pd.DataFrame()
        g = s.groupby(s.index.year)
        df = pd.DataFrame({"median": g.median(), "p10": g.quantile(0.1), "p90": g.quantile(0.9)})
        return df

    names_per_day_A = _by_year(namesA)
    names_per_day_B = _by_year(namesB)

    all_dates_arr_f = np.array(sorted(all_dates))
    if len(all_dates_arr_f) >= BETA_WINDOW:
        first_usable = all_dates_arr_f[BETA_WINDOW - 1]
    else:
        first_usable = None

    return {
        "snapshots": snapshots,
        "findings": findings,
        "member_syms": member_syms,
        "obs": obs,
        "attrit": attrit,
        "stock_df": stock_df,
        "idx_df": idx_df,
        "sigma_I": sigma_I,
        "panel": panel,
        "statsA": statsA,
        "statsB": statsB,
        "rho_raw": rho_raw,
        "neff_raw": neff_raw,
        "pc1_raw": pc1_raw,
        "n_raw": n_raw,
        "rho_dm": rho_dm,
        "neff_dm": neff_dm,
        "pc1_dm": pc1_dm,
        "n_dm": n_dm,
        "rho_imp_diag": rho_imp_diag,
        "ladder": ladder,
        "names_per_day_A": names_per_day_A,
        "names_per_day_B": names_per_day_B,
        "first_usable": first_usable,
        "n_permissive": n_permissive,
        "n_strict": n_strict,
    }


def run(output_path):
    d = build_panel()
    _write_report(output_path, d)
    print(f"Report written to {output_path}")


def _write_report(path, d):
    att = d["attrit"]
    statsA, statsB = d["statsA"], d["statsB"]
    med_neff_raw = float(np.median(d["neff_raw"])) if d["neff_raw"] else np.nan
    med_rho_raw = float(np.median(d["rho_raw"])) if d["rho_raw"] else np.nan
    med_pc1_raw = float(np.median(d["pc1_raw"])) if d["pc1_raw"] else np.nan
    med_n_raw = float(np.median(d["n_raw"])) if d["n_raw"] else np.nan
    med_neff_dm = float(np.median(d["neff_dm"])) if d["neff_dm"] else np.nan
    med_rho_dm = float(np.median(d["rho_dm"])) if d["rho_dm"] else np.nan
    med_pc1_dm = float(np.median(d["pc1_dm"])) if d["pc1_dm"] else np.nan
    names_per_day = d["panel"].groupby("trade_date").size()
    med_names_day = float(names_per_day.median()) if len(names_per_day) else np.nan
    rho_imp = d["rho_imp_diag"]

    lines = []
    l = lines.append
    l("# SE-3 — Index-versus-constituent dispersion: Breadth / SD Probe Report")
    l("")
    l("**Date:** 2026-08-05  |  **Window:** 2023-01-02 -> 2025-12-31 (index leg burned; stock leg **SPENT** by this probe)")
    l("**Unread windows preserved:** NIFTY index options 2016-02-11 -> 2022-12-31 (1,701 dates); stock options 2021-01-01 -> 2022-12-31; both legs 2026-01-01 -> 2026-07")
    l("")
    l("## 1. Fence proof")
    l("")
    for key, (mn, mx) in d["obs"].items():
        l(f"- **{key}**: observed `trade_date` range [{mn.date()}, {mx.date()}] — inside fence")
    l("- Hard assertion per source at top of pipeline: `assert FENCE_START <= min and max <= FENCE_END` — **PASSED** on all three legs")
    l(f"- First usable formation date (complete 60-trading-day warmup inside fence): **{d['first_usable'].date()}** — variant B's 60-day window is binding; variant A's 21-day RV warmup completes earlier.")
    l("")
    l("## 2. Window ledger (state entering vs after this probe)")
    l("")
    l("| Leg | Window | State entering this probe | State after |")
    l("|---|---|---|---|")
    l("| NIFTY index options | 2023-01-02 -> 2025-12-31 | **Already burned** — MSRP triage + OSC SD probe | Unchanged — costs nothing |")
    l("| OPTSTK stock options | 2023-01-02 -> 2025-12-31 | **Not previously read for research** | **SPENT by this probe** |")
    l("| NIFTY index options | 2016-02-11 -> 2022-12-31 | Unread, 1,701 dates | **Preserved — untouched** |")
    l("| OPTSTK stock options | 2016-07-31 -> 2020-12-31 | **Prior-exposed** — Skew sleeve TRAIN | Unchanged |")
    l("| OPTSTK stock options | 2021-01-01 -> 2022-12-31 | Unread | **Preserved — untouched** |")
    l("| Both legs | 2026-01-01 -> 2026-07 | Unread | **Preserved — untouched** |")
    l("")
    l("## 3. Attrition (absolute row counts)")
    l("")
    l("| Stage | Stocks | NIFTY |")
    l("|---|---|---|")
    l(f"| Option rows in fence (member universe) | {att['stock_rows_loaded']:,} | {att['idx_rows_loaded']:,} |")
    l(f"| After PIT membership + F&O-live | {att['stock_after_membership']:,} | — |")
    l(f"| Traded (contracts>0, OI>0) | {att['stock_traded']:,} | {att['idx_traded']:,} |")
    l(f"| On selected expiry (§3.2) | {att['stock_after_expiry']:,} | {att['idx_after_expiry']:,} |")
    l(f"| With forward (§3.3) | {att['stock_after_forward']:,} | {att['idx_after_forward']:,} |")
    l(f"| Settle >= {SETTLE_FLOOR} | {att['stock_after_settle']:,} | {att['idx_after_settle']:,} |")
    l(f"| |ln(strike/F)| <= {MONEYNESS_BAND} | {att['stock_after_moneyness']:,} | {att['idx_after_moneyness']:,} |")
    l(f"| ATM-IV (date-name cells) | {att['stock_after_iv']:,} | {att['idx_after_iv']:,} |")
    l(f"| After t+1 pairing (date-name cells) | {att['stock_after_pairing']:,} | — |")
    l("")
    l("Dropped (date, name) tallies:")
    l("")
    l("| Drop reason | Stocks | NIFTY |")
    l("|---|---|---|")
    l(f"| §3.2 no expiry in [7,60] | {att['dropped_no_expiry']['stock']} | {att['dropped_no_expiry']['idx']} |")
    l(f"| §3.3 no forward | {att['dropped_no_forward']['stock']} | {att['dropped_no_forward']['idx']} |")
    l(f"| §3.4 no ATM IV cell | {att['dropped_no_atm']['stock']} | {att['dropped_no_atm']['idx']} |")
    l(f"| IV inversion discard (attempted) | {att['iv_discard']['stock']}/{att['iv_attempted']['stock']} ({att['iv_discard']['stock']/max(att['iv_attempted']['stock'],1):.1%}) | {att['iv_discard']['idx']}/{att['iv_attempted']['idx']} ({att['iv_discard']['idx']/max(att['iv_attempted']['idx'],1):.1%}) |")
    l(f"| §3.7 pairing dropped (neither leg paired to t+1) | {att['pairing_dropped']} | — |")
    l("")
    l("## 4. Names per day (variant A and B universes)")
    l("")
    l("**Variant A** (>=20 names with sigma & rv on the date):")
    l("")
    l("| Year | median | p10 | p90 |")
    l("|---|---|---|---|")
    for yr in d["names_per_day_A"].index:
        row = d["names_per_day_A"].loc[yr]
        l(f"| {yr} | {row['median']:.0f} | {row['p10']:.0f} | {row['p90']:.0f} |")
    l("")
    l("**Variant B** (>=40 paired obs in trailing 60d):")
    l("")
    l("| Year | median | p10 | p90 |")
    l("|---|---|---|---|")
    for yr in d["names_per_day_B"].index:
        row = d["names_per_day_B"].loc[yr]
        l(f"| {yr} | {row['median']:.0f} | {row['p10']:.0f} | {row['p90']:.0f} |")
    l("")
    l("## 5. THE HEADLINE NUMBERS")
    l("")
    l("| Variant | n_dates | mean_IC | **sd_IC** | Newey-West t (lag 5) | AC1 |")
    l("|---|---|---|---|---|---|")
    def _row(label, st):
        return f"| {label} | {st['n_dates']} | {st['mean_ic']:.4f} | **{st['sd_ic']:.4f}** | {st['nw_t']:.4f} | {st['ac1']:.4f} |"
    if statsA:
        l(_row("A (pure cross-section)", statsA))
    else:
        l("| A (pure cross-section) | 0 | — | — | — | — |")
    if statsB:
        l(_row("B (index-anchored)", statsB))
    else:
        l("| B (index-anchored) | 0 | — | — | — | — |")
    l("")
    l("**Expected sign is NEGATIVE** (rich options subsequently underperform delta-hedged). Nothing is flipped.")
    l("")
    l("## 6. Breadth — raw panel (rolling 60-trading-day)")
    l("")
    l("| Statistic | Value |")
    l("|---|---|")
    l(f"| Median rho_bar (raw) | {med_rho_raw:.3f} |")
    l(f"| **Median N_eff (raw)** | **{med_neff_raw:.1f}** |")
    l(f"| Median PC1 share (raw) | {med_pc1_raw:.2%} |")
    l(f"| Median N (names populated through window) | {med_n_raw:.0f} |")
    l(f"| Median raw names/day | {med_names_day:.0f} |")
    l("")
    l("### Demeaned panel (SECONDARY — artifact warning)")
    l("")
    l("> **WARNING:** demeaning mechanically induces rho_bar ~ -1/(N-1), which drives N_eff toward N by construction. **The demeaned N_eff is an artifact and must never be quoted as the breadth of this cross-section.** It is reported only to show how much of the raw correlation is a common level vs genuine pairwise co-movement. The **raw N_eff is the headline**, comparable to OSC's 1.9 and the TS Basis filter probe's 10.1.")
    l("")
    l("| Statistic (demeaned) | Value |")
    l("|---|---|")
    l(f"| Median rho_bar | {med_rho_dm:.3f} |")
    l(f"| Median N_eff | {med_neff_dm:.1f} |")
    l(f"| Median PC1 share | {med_pc1_dm:.2%} |")
    l("")
    l("## 7. Implied-correlation diagnostics (§3.8, diagnostic only — NOT the signal)")
    l("")
    if rho_imp:
        l("| Quantity | Value |")
        l("|---|---|")
        l(f"| Dates with rho_imp computable | {rho_imp['n_dates']} |")
        l(f"| Median rho_imp | {rho_imp['median']:.3f} |")
        l(f"| 10th percentile | {rho_imp['p10']:.3f} |")
        l(f"| 90th percentile | {rho_imp['p90']:.3f} |")
        l(f"| Fraction outside [0,1] | {rho_imp['outside']:.1%} |")
        l(f"| Median renormalization mass | {rho_imp['median_mass']:.3f} |")
        l("")
        l("rho_imp is NOT clipped and NOT used as a per-name signal.")
        l("")
    else:
        l("No dates produced a computable rho_imp.")
        l("")
    l("## 8. Feasibility read-out (decision ladder, §5)")
    l("")
    l("Ladder applied mechanically via `power.n_required`, two-sided, power 0.80, at both confirmatory-n readings:")
    l("")
    l("| Variant | sd_IC | n=1,701 (permissive) | n≈495 (strict) |")
    l("|---|---|---|---|")
    for v in ("A", "B"):
        ld = d["ladder"].get(v)
        if ld is None:
            l(f"| {v} | — | — | — |")
        else:
            l(f"| {v} | {ld['sd_ic']:.4f} | **{ld['permissive']}** | **{ld['strict']}** |")
    l("")
    l("Rung semantics (identical to OSC's anchors, applied at both readings):")
    l("")
    l("| Rung | Meaning |")
    l("|---|---|")
    l("| **Green** | Feasible even at a pessimistic δ = 0.015 -> proceed to design |")
    l("| **Amber** | Feasible only if δ >= 0.020 can be **independently** defended |")
    l("| **Red-amber** | Feasible only at δ >= 0.029 — CB-N50's *stock* HOLDOUT IC; no claim on option cells |")
    l("| **ABANDON** | Infeasible at any defensible δ |")
    l("")
    l("**Do not editorialize beyond the rung.** The δ anchor is NOT an output of this probe (§8 of the prompt).")
    l("")
    l("## 9. Predictions (pre-registered, state-before-run)")
    l("")
    l("| # | Prediction | Actual | Held? |")
    l("|---|---|---|---|")
    preds = _predictions(d)
    for pid, text, held, actual in preds:
        l(f"| {pid} | {text} | {actual} | **{'HELD' if held else 'FAILED'}** |")
    l("")
    l("## 10. Implementation notes")
    l("")
    l("- All Black-76 functions imported from `scripts/osc/sd_probe.py` — no reimplementation.")
    l("- `_mcwb_rows` locates the `Security Symbol` and weight columns by header name, so archive layout drift is handled without touching the pinned spec.")
    l(f"- Source-pollution findings (DUMMY*/TMPV* excluded from membership): {d['findings'] or 'none'}")
    l("- Nothing under `data/` is written (read-only).")
    l("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _predictions(d):
    statsA, statsB = d["statsA"], d["statsB"]
    med_neff_raw = float(np.median(d["neff_raw"])) if d["neff_raw"] else np.nan
    med_rho_raw = float(np.median(d["rho_raw"])) if d["rho_raw"] else np.nan
    namesA = d["panel"][d["panel"]["richA"].notna()].groupby("trade_date").size()
    rho_imp = d["rho_imp_diag"]
    att = d["attrit"]
    pairing_attr = att["pairing_dropped"] / max(att["stock_after_iv"] + att["pairing_dropped"], 1)
    out = []

    def add(pid, text, held, actual):
        out.append((pid, text, held, actual))

    add("P1", "Median names/day (variant A) >= 35", bool(len(namesA) and namesA.median() >= 35),
        f"{namesA.median():.0f}" if len(namesA) else "n/a")
    add("P2", "Raw rho_bar >= 0.15", not np.isnan(med_rho_raw) and med_rho_raw >= 0.15, f"{med_rho_raw:.3f}")
    add("P3", "Raw median N_eff < 15", not np.isnan(med_neff_raw) and med_neff_raw < 15, f"{med_neff_raw:.1f}")
    add("P4", "Raw median N_eff > 1.9", not np.isnan(med_neff_raw) and med_neff_raw > 1.9, f"{med_neff_raw:.1f}")
    add("P5", "mean_IC (variant A) negative", statsA is not None and statsA["mean_ic"] < 0,
        f"{statsA['mean_ic']:.4f}" if statsA else "n/a")
    add("P6a", "sd_IC(A) <= 0.30", statsA is not None and statsA["sd_ic"] <= 0.30,
        f"{statsA['sd_ic']:.4f}" if statsA else "n/a")
    add("P6b", "sd_IC(A) >= 0.15", statsA is not None and statsA["sd_ic"] >= 0.15,
        f"{statsA['sd_ic']:.4f}" if statsA else "n/a")
    add("P7", "sd_IC(B) >= sd_IC(A)", statsA is not None and statsB is not None and statsB["sd_ic"] >= statsA["sd_ic"],
        f"{statsB['sd_ic']:.4f}" if statsB else "n/a")
    iv_rate = att["iv_discard"]["stock"] / max(att["iv_attempted"]["stock"], 1)
    add("P8", "IV inversion discard rate < 10% (stocks)", iv_rate < 0.10, f"{iv_rate:.1%}")
    add("P9", "t+1 pairing attrition < 25% of (date,name) cells", pairing_attr < 0.25, f"{pairing_attr:.1%}")
    if rho_imp:
        add("P10", "Median renormalization mass >= 0.85", rho_imp["median_mass"] >= 0.85, f"{rho_imp['median_mass']:.3f}")
    else:
        add("P10", "Median renormalization mass >= 0.85", False, "n/a")
    return out


def main():
    parser = argparse.ArgumentParser(description="SE-3 Breadth / SD Probe")
    parser.add_argument("--out", default=str(PROJECT_ROOT / "docs" / "reports" / "SE3_BREADTH_PROBE_REPORT.md"))
    args = parser.parse_args()
    run(args.out)


if __name__ == "__main__":
    main()
