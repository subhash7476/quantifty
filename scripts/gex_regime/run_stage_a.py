"""GEX regime Stage A runner — EOD NIFTY gamma regime vs next-day RV / implied variance.

Spec: docs/superpowers/specs/2026-09-23-gex-regime-stage-a-design.md
Usage: python scripts/gex_regime/run_stage_a.py --window train|holdout [--checks-only]
Refuses any date >= 2023-01-01 (unread window).
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.analytics.gex_history import (  # noqa: E402
    MAX_DTE, MAX_FWD_DEV, MIN_STRIKES, day_regime, parity_forward, select_strikes,
)

SEALED_START = date(2023, 1, 1)
WINDOWS = {"train": (date(2016, 2, 11), date(2019, 12, 31)),
           "holdout": (date(2020, 1, 1), date(2022, 12, 31))}
OPTIONS_DB = ROOT / "data/market_data/options_bhavcopy.duckdb"
DAILY_DIR = ROOT / "data/market_data/nse/candles/1d"
REPORT_DIR = ROOT / "docs/reports"
NIFTY, VIX = "NSE_INDEX|Nifty 50", "NSE_INDEX|India VIX"
WARMUP_DAYS = 45
HAC_LAGS = 5
CONTROLS = ["ln_vix", "ln_rv5", "ln_rv20", "exp_next"]


def check_window(start: date, end: date) -> None:
    if end >= SEALED_START or start >= SEALED_START:
        raise ValueError(f"window {start}..{end} touches the unread window (>= {SEALED_START})")


def load_daily(start: date, end: date) -> pd.DataFrame:
    rows = []
    for path in sorted(DAILY_DIR.glob("*.duckdb")):
        d = date.fromisoformat(path.stem)
        if not start <= d <= end:
            continue
        con = duckdb.connect(str(path), read_only=True)
        got = dict((s, (h, lo, c)) for s, h, lo, c in con.execute(
            "SELECT symbol, high, low, close FROM candles WHERE symbol IN (?, ?)", [NIFTY, VIX]).fetchall())
        con.close()
        if NIFTY in got and VIX in got:
            h, lo, c = got[NIFTY]
            rows.append({"date": d, "high": h, "low": lo, "close": c, "vix": got[VIX][2]})
    return pd.DataFrame(rows)


def load_options(start: date, end: date) -> tuple[pd.DataFrame, set]:
    con = duckdb.connect(str(OPTIONS_DB), read_only=True)
    df = con.execute(
        """SELECT trade_date, expiry_dt, strike, option_type, close, contracts, open_int
           FROM option_bhavcopy
           WHERE symbol = 'NIFTY' AND trade_date BETWEEN ? AND ?
             AND expiry_dt > trade_date AND date_diff('day', trade_date, expiry_dt) <= ?""",
        [start, end, MAX_DTE]).df()
    expiries = {r[0] for r in con.execute(
        "SELECT DISTINCT expiry_dt FROM option_bhavcopy WHERE symbol = 'NIFTY' AND expiry_dt < ?",
        [SEALED_START]).fetchall()}
    con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df["expiry_dt"] = pd.to_datetime(df["expiry_dt"]).dt.date
    return df, expiries


def build_regimes(options: pd.DataFrame, close_by_date: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, drops = [], []
    for t, day in options.groupby("trade_date"):
        spot = close_by_date.get(t)
        if spot is None:
            drops.append({"date": t, "reason": "no_index_bar"})
            continue
        expiries, fwd_ratios = [], []
        for exp, chain in day.groupby("expiry_dt"):
            t_years = (exp - t).days / 365
            fwd = parity_forward(chain, t_years)
            if fwd is None:
                drops.append({"date": t, "reason": "expiry_no_pair"})
                continue
            if abs(fwd / spot - 1) > MAX_FWD_DEV:
                drops.append({"date": t, "reason": "expiry_fwd_dev"})
                continue
            fwd_ratios.append(fwd / spot)
            es = select_strikes(chain, fwd, t_years)
            if len(es.strikes):
                expiries.append(es)
        n = sum(len(e.strikes) for e in expiries)
        if n < MIN_STRIKES:
            drops.append({"date": t, "reason": "few_strikes"})
            continue
        r = day_regime(expiries)
        rows.append({"date": t, "n_strikes": r.n_strikes, "n_expiries": len(expiries),
                     "net_norm": r.net_norm, "sign": r.sign, "flip_x": r.flip_x,
                     "censored": r.censored, "fwd_ratio": float(np.median(fwd_ratios))})
    return pd.DataFrame(rows), pd.DataFrame(drops, columns=["date", "reason"])


def build_outcomes(daily: pd.DataFrame, expiry_dates: set, window_start: date, window_end: date) -> pd.DataFrame:
    d = daily.sort_values("date").reset_index(drop=True).copy()
    d["rv"] = np.log(d["high"] / d["low"]) ** 2 / (4 * math.log(2))
    d["rv"] = d["rv"].where(d["rv"] > 0)
    d["ivd"] = (d["vix"] / 100) ** 2 / 252
    d["ln_vix"] = np.log(d["vix"])
    d["ln_rv5"] = np.log(d["rv"].rolling(5).mean())
    d["ln_rv20"] = np.log(d["rv"].rolling(20).mean())
    d["next_date"] = d["date"].shift(-1)
    d["rv_next"] = d["rv"].shift(-1)
    r2 = np.log(d["close"].shift(-1) / d["close"]) ** 2
    d["y"] = np.log(d["rv_next"] / d["ivd"])
    d["y_cc"] = np.log(r2.where(r2 > 0) / d["ivd"])
    d["exp_next"] = d["next_date"].isin(expiry_dates).astype(int)
    keep = (d["date"] >= window_start) & d["next_date"].notna()
    keep &= d["next_date"].apply(lambda x: pd.notna(x) and x <= window_end)
    return d[keep].reset_index(drop=True)


def fit(panel: pd.DataFrame, regressor: str, outcome: str = "y"):
    d = panel.dropna(subset=[outcome, regressor] + CONTROLS)
    X = sm.add_constant(d[[regressor] + CONTROLS].astype(float))
    return sm.OLS(d[outcome].astype(float), X).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})


def _fmt(x, p=4):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{p}f}"


def checks_section(regimes: pd.DataFrame, drops: pd.DataFrame, n_days: int) -> list[str]:
    out = ["## §8 Pre-run checks (no outcome read)", "",
           f"Trading days in window (index store): {n_days}", "",
           "| year | days computed | kept strikes / day (median) | expiries / day (median) | "
           "fwd/close p1 · median · p99 | flip censored | N p10 · median · p90 |",
           "|---|--:|--:|--:|---|--:|---|"]
    reg = regimes.assign(year=[d.year for d in regimes["date"]])
    for y, g in reg.groupby("year"):
        fr, nn = g["fwd_ratio"], g["net_norm"]
        out.append(f"| {y} | {len(g)} | {g['n_strikes'].median():.0f} | {g['n_expiries'].median():.0f} | "
                   f"{fr.quantile(.01):.4f} · {fr.median():.4f} · {fr.quantile(.99):.4f} | "
                   f"{g['censored'].mean():.1%} | {nn.quantile(.1):+.3f} · {nn.median():+.3f} · "
                   f"{nn.quantile(.9):+.3f} |")
    out += ["", "**Drops by reason** (expiry-level reasons count expiries, not days):", ""]
    if drops.empty:
        out.append("none")
    else:
        dr = drops.assign(year=[d.year for d in drops["date"]])
        tab = dr.pivot_table(index="year", columns="reason", values="date", aggfunc="count", fill_value=0)
        out.append("| year | " + " | ".join(tab.columns) + " |")
        out.append("|---|" + "--:|" * len(tab.columns))
        for y, row in tab.iterrows():
            out.append(f"| {y} | " + " | ".join(str(int(v)) for v in row) + " |")
    return out + [""]


def fit_section(panel: pd.DataFrame, window: str) -> tuple[list[str], bool]:
    m = fit(panel, "net_norm")
    b, t, p = m.params["net_norm"], m.tvalues["net_norm"], m.pvalues["net_norm"]
    p_one = p / 2 if b < 0 else 1 - p / 2
    passed = (b < 0 and t <= -2.0) if window == "train" else (b < 0 and p_one < 0.05)
    q10, q90 = panel["net_norm"].quantile(.1), panel["net_norm"].quantile(.9)
    effect = math.exp(b * (q90 - q10)) - 1
    rho = panel[["net_norm", "ln_vix"]].corr().iloc[0, 1]
    out = ["## §6 Primary fit — y = ln(RV_{t+1} / IVd_t) on N_t + controls (NW HAC lag 5)", "",
           f"n = {int(m.nobs)} · R² = {m.rsquared:.4f}", "",
           "| term | coef | NW t | p (two-sided) |", "|---|--:|--:|--:|"]
    for k in m.params.index:
        out.append(f"| {k} | {m.params[k]:+.4f} | {m.tvalues[k]:+.2f} | {m.pvalues[k]:.4g} |")
    out += ["", f"- **b (net_norm) = {b:+.4f}, NW t = {t:+.2f}, one-sided p (b<0) = {p_one:.4g}**",
            f"- Effect of N p10→p90 ({q10:+.3f}→{q90:+.3f}): {effect:+.1%} in RV_{{t+1}}/IVd_t",
            f"- corr(N, ln VIX) = {rho:+.3f}", ""]
    out += ["## Descriptive (not part of the pass rule)", "",
            "| model | coef | NW t | n |", "|---|--:|--:|--:|"]
    panel = panel.assign(dist=-np.log1p(panel["flip_x"]) / (panel["vix"] / 100 / math.sqrt(252)))
    for label, reg, outc, sub in [
        ("S_t (sign), Parkinson", "sign", "y", panel),
        ("D_t (flip distance, σ units), Parkinson", "dist", "y", panel),
        ("N_t, close-to-close outcome", "net_norm", "y_cc", panel),
    ] + ([("N_t, Parkinson, 2016–2018", "net_norm", "y", panel[[d.year <= 2018 for d in panel["date"]]]),
          ("N_t, Parkinson, 2019", "net_norm", "y", panel[[d.year == 2019 for d in panel["date"]]])]
         if window == "train" else []):
        mm = fit(sub, reg, outc)
        out.append(f"| {label} | {mm.params[reg]:+.4f} | {mm.tvalues[reg]:+.2f} | {int(mm.nobs)} |")
    rule = "b < 0 and NW t ≤ −2.0" if window == "train" else "b < 0 and one-sided p < 0.05"
    out += ["", f"## Verdict", "", f"Rule: {rule}.", "",
            f"**{window.upper()} verdict: {'PASS' if passed else 'FAIL'}**", ""]
    return out, passed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", choices=list(WINDOWS), required=True)
    ap.add_argument("--checks-only", action="store_true")
    args = ap.parse_args()
    start, end = WINDOWS[args.window]
    check_window(start, end)
    if args.window == "holdout":
        train_report = REPORT_DIR / "GEX_REGIME_STAGE_A_TRAIN.md"
        if not train_report.exists() or "**TRAIN verdict: PASS**" not in train_report.read_text(encoding="utf-8"):
            raise SystemExit("HOLDOUT refused: TRAIN report missing or not PASS (spec §7)")

    daily = load_daily(start - timedelta(days=WARMUP_DAYS), end)
    options, expiry_dates = load_options(start, end)
    close_by_date = dict(zip(daily["date"], daily["close"]))
    regimes, drops = build_regimes(options, close_by_date)
    n_days = int(((daily["date"] >= start) & (daily["date"] <= end)).sum())

    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip()
    lines = [f"# GEX Regime Stage A — {args.window.upper()} ({start} → {end})", "",
             "Script-generated by `scripts/gex_regime/run_stage_a.py` — do not hand-edit.",
             f"Spec: `docs/superpowers/specs/2026-09-23-gex-regime-stage-a-design.md` · code rev `{rev}`", "",
             "Sign convention (assumption): dealers long calls, short puts. "
             "N = Σ signed / Σ gross gamma exposure.", ""]
    lines += checks_section(regimes, drops, n_days)
    if not args.checks_only:
        outcomes = build_outcomes(daily, expiry_dates, start, end)
        panel = outcomes.merge(regimes, on="date", how="inner")
        body, _ = fit_section(panel, args.window)
        lines += body
    suffix = "_CHECKS" if args.checks_only else ""
    path = REPORT_DIR / f"GEX_REGIME_STAGE_A_{args.window.upper()}{suffix}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
