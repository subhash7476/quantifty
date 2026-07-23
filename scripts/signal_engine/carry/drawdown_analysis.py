"""Carry drawdown / regime profile — §6.3 of the go-live gate.

Measures worst month, max drawdown, and return distribution over TRAIN
and HOLDOUT using the validated production construction (re-uses the
same simulation harness as parity_check.py). No SEALED read — runs on
data already in hand.

The report characterizes the risk profile so sizing can be calibrated
to the conservative net, not the regime-flattered SEALED +20.5%.

Optional: Trend sleeve's −0.246 correlation evaluated as a drawdown-
reduction overlay on TRAIN/HOLDOUT data (same windows, no SEALED spend).

Output: docs/reports/CARRY_DRAWDOWN_REPORT.md
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))

# ── Paths ──
FACTS_DB = ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "CARRY_DRAWDOWN_REPORT.md"

WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}

# Use the parity check's simulation — it exercises the real production module
from scripts.signal_engine.carry.parity_check import _simulate_production


def _equity_curve(monthly: list[float]) -> np.ndarray:
    """Cumulative return from monthly net return series. Start at 1.0."""
    return np.cumprod(1.0 + np.array(monthly))


def _max_drawdown(monthly: list[float]) -> tuple[float, int, int]:
    """Peak-to-trough max drawdown from monthly returns.
    Returns (max_dd_pct, peak_month_idx, trough_month_idx)."""
    eq = _equity_curve(monthly)
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    trough_idx = int(np.argmin(dd))
    peak_idx = int(np.argmax(eq[:trough_idx + 1])) if trough_idx > 0 else 0
    return float(dd[trough_idx]), peak_idx, trough_idx


def _worst_month(monthly: list[float]) -> float:
    return float(np.min(monthly))


def _best_month(monthly: list[float]) -> float:
    return float(np.max(monthly))


def _sharpe(monthly: list[float], ann_factor: int = 12) -> float:
    arr = np.array(monthly)
    if len(arr) < 2 or np.std(arr, ddof=1) == 0:
        return 0.0
    return float(np.mean(arr) / np.std(arr, ddof=1) * np.sqrt(ann_factor))


def _sortino(monthly: list[float], ann_factor: int = 12) -> float:
    arr = np.array(monthly)
    downside = arr[arr < 0]
    if len(downside) < 2 or np.std(downside, ddof=1) == 0:
        return 0.0
    return float(np.mean(arr) / np.std(downside, ddof=1) * np.sqrt(ann_factor))


def _calmar(monthly: list[float], ann_ret: float) -> float:
    dd, _, _ = _max_drawdown(monthly)
    return ann_ret / abs(dd) if dd < 0 else float('inf')


def _ulcer_index(monthly: list[float]) -> float:
    eq = _equity_curve(monthly)
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    return float(np.sqrt(np.mean(dd ** 2)))


def _positive_months_pct(monthly: list[float]) -> float:
    return float(np.mean(np.array(monthly) > 0) * 100)


def _concentration(monthly: list[float], top_n: int = 5) -> float:
    """Fraction of total return from the top-N months."""
    arr = np.array(monthly)
    total = np.sum(arr)
    if abs(total) < 1e-12:
        return 0.0
    top = np.sort(arr)[-top_n:]
    return float(np.sum(top) / total)


def _rolling_12m(monthly: list[float]) -> tuple[float, float, float]:
    """Min, mean, max of rolling 12-month returns (annualized)."""
    arr = np.array(monthly)
    if len(arr) < 12:
        return 0.0, 0.0, 0.0
    rolling = np.array([np.prod(1 + arr[i:i+12]) - 1 for i in range(len(arr) - 11)])
    return float(np.min(rolling)), float(np.mean(rolling)), float(np.max(rolling))


def _analyze(label: str, result: dict) -> dict:
    """Extract drawdown/regime metrics from a simulation result dict."""
    net = result.get("net_spreads", [])
    gross = result.get("gross_spreads", [])
    if not net or "error" in result:
        return {"error": result.get("error", "no data")}

    ann_net = result["ann_net"]
    worst = _worst_month(net)
    best = _best_month(net)
    dd, peak_i, trough_i = _max_drawdown(net)
    sharpe = _sharpe(net)
    sortino = _sortino(net)
    calmar = _calmar(net, ann_net)
    ulcer = _ulcer_index(net)
    pos_pct = _positive_months_pct(net)
    conc5 = _concentration(net, 5)
    conc3 = _concentration(net, 3)
    r12 = _rolling_12m(net)
    std_m = float(np.std(net, ddof=1)) if len(net) > 1 else 0.0
    skew = float(_skew(net))

    return {
        "label": label,
        "n_months": len(net),
        "ann_net": ann_net,
        "ann_gross": result.get("ann_gross", 0.0),
        "avg_turnover": result.get("avg_turnover", 0.0),
        "worst_month": worst,
        "best_month": best,
        "max_dd": dd,
        "monthly_std": std_m,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "ulcer": ulcer,
        "positive_pct": pos_pct,
        "top5_concentration": conc5,
        "top3_concentration": conc3,
        "rolling_12m_min": r12[0],
        "rolling_12m_mean": r12[1],
        "rolling_12m_max": r12[2],
        "skew": skew,
        "monthly_returns": net,
    }


def _skew(arr: list[float]) -> float:
    a = np.array(arr)
    if len(a) < 3 or np.std(a, ddof=1) == 0:
        return 0.0
    n = len(a)
    m3 = np.sum((a - np.mean(a)) ** 3) / n
    s3 = (np.std(a, ddof=1)) ** 3
    return float(m3 / s3) if s3 > 0 else 0.0


def _sub_periods(label: str, lo: date, hi: date, metrics: dict) -> dict:
    """Split window into halves for sub-period comparison."""
    mid = lo + (hi - lo) / 2
    # We'll mark: if someone wants sub-periods, the monthly returns need dates.
    # For now skip — the rolling 12m already covers regime variation.
    return {}


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def main():
    commit = _git_commit()
    now_ts = date.today().isoformat()

    con = duckdb.connect()
    con.execute(f"ATTACH '{FACTS_DB}' AS fct (READ_ONLY)")
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute("SET threads=4")

    metrics = {}
    for label, (lo, hi) in WINDOWS.items():
        print(f"  Simulating {label}: {lo} -> {hi}")
        result = _simulate_production(label, lo, hi, con)
        if "error" not in result:
            print(f"    ann_net={result['ann_net']*100:.2f}%  months={result['return_periods']}")
        metrics[label] = _analyze(label, result)

    con.close()

    # ── Generate report ──
    lines = []
    a = lines.append

    a("# Carry — Drawdown / Regime Profile\n")
    a(f"**Script-generated** — `scripts/signal_engine/carry/drawdown_analysis.py`. "
      f"Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a("**Protocol:** `CARRY_IMPLEMENTATION_BRIDGE.md` §6.3 — characterize risk before "
      "sizing. Size on the conservative net, not the SEALED +20.5%.\n")
    a("**SEALED:** NOT read — TRAIN and HOLDOUT only. SEALED (2023–26) is likely a "
      "carry-favorable regime; sizing on that headline number would understate risk.\n")
    a("")

    # ── Summary table ──
    a("---\n")
    a("## 1. Risk Summary\n")
    a("")
    a("| Metric | TRAIN | HOLDOUT | Conservative |")
    a("|---|--:|--:|--:|")

    train = metrics.get("TRAIN", {})
    holdout = metrics.get("HOLDOUT", {})

    def _row(name, key, fmt=".2f", pct=True, worse_is_lower=True):
        tv = train.get(key, 0) if isinstance(train, dict) else 0
        hv = holdout.get(key, 0) if isinstance(holdout, dict) else 0
        if worse_is_lower:
            ch = min(tv, hv) if isinstance(tv, (int, float)) else 0
        else:
            ch = max(tv, hv) if isinstance(tv, (int, float)) else 0
        sfx = "%" if pct else ""
        a(f"| {name} | {tv*100:{fmt}}% | {hv*100:{fmt}}% | {ch*100:{fmt}}% |")

    _row("Annualized net", "ann_net")           # lower is worse
    _row("Worst month", "worst_month")           # lower is worse
    _row("Max drawdown", "max_dd")               # lower is worse
    _row("Monthly std dev", "monthly_std", worse_is_lower=False)  # higher is worse
    a("")

    # ── Risk ratios ──
    a("---\n")
    a("## 2. Risk-Adjusted Metrics\n")
    a("")
    a("| Metric | TRAIN | HOLDOUT |")
    a("|---|--:|--:|")
    for name, key in [("Sharpe (ann)", "sharpe"), ("Sortino (ann)", "sortino"),
                       ("Calmar (ret/|DD|)", "calmar"), ("Ulcer Index", "ulcer"),
                       ("% positive months", "positive_pct"),
                       ("Return skew", "skew")]:
        tv = train.get(key, 0) if isinstance(train, dict) else 0
        hv = holdout.get(key, 0) if isinstance(holdout, dict) else 0
        sfx = "%" if key in ("positive_pct",) else ""
        fmt = ".1f" if key in ("positive_pct",) else ".2f"
        if key == "skew":
            a(f"| {name} | {tv:{fmt}} | {hv:{fmt}} |")
        elif key in ("positive_pct",):
            a(f"| {name} | {tv:.1f}% | {hv:.1f}% |")
        else:
            a(f"| {name} | {tv:.2f} | {hv:.2f} |")
    a("")

    # ── Return concentration ──
    a("---\n")
    a("## 3. Return Concentration\n")
    a("What fraction of total return comes from the top N months? "
      "High concentration → returns are lumpy, not steady.\n")
    a("")
    a("| Window | Top 3 months | Top 5 months |")
    a("|---|--:|--:|")
    for label in ["TRAIN", "HOLDOUT"]:
        m = metrics.get(label, {})
        a(f"| {label} | {m.get('top3_concentration', 0)*100:.0f}% | "
          f"{m.get('top5_concentration', 0)*100:.0f}% |")
    a("")

    # ── Rolling 12-month returns ──
    a("---\n")
    a("## 4. Rolling 12-Month Returns (Annualized)\n")
    a("Shows the range of annual returns an investor would have experienced "
      "at any entry point.\n")
    a("")
    a("| Window | Worst 12m | Mean 12m | Best 12m |")
    a("|---|--:|--:|--:|")
    for label in ["TRAIN", "HOLDOUT"]:
        m = metrics.get(label, {})
        a(f"| {label} | {m.get('rolling_12m_min', 0)*100:+.1f}% | "
          f"{m.get('rolling_12m_mean', 0)*100:+.1f}% | "
          f"{m.get('rolling_12m_max', 0)*100:+.1f}% |")
    a("")

    # ── Monthly return distribution ──
    a("---\n")
    a("## 5. Monthly Return Distribution\n")
    a("")
    for label in ["TRAIN", "HOLDOUT"]:
        m = metrics.get(label, {})
        rets = m.get("monthly_returns", [])
        if not rets:
            continue
        arr = np.array(rets)
        a(f"### {label} ({len(rets)} months)\n")
        pcts = [10, 25, 50, 75, 90]
        vals = np.percentile(arr, pcts)
        a("| Percentile | Return |")
        a("|---|--:|")
        for p, v in zip(pcts, vals):
            a(f"| p{p} | {v*100:+.2f}% |")
        a("")
        a(f"- Mean: {np.mean(arr)*100:+.2f}% · Std: {np.std(arr, ddof=1)*100:.2f}% "
          f"· Skew: {_skew(rets):+.2f}\n")
        a(f"- Positive: {_positive_months_pct(rets):.0f}% · Best: {np.max(arr)*100:+.2f}% "
          f"· Worst: {np.min(arr)*100:+.2f}%\n")
        a("")

    # ── Sizing recommendation ──
    a("---\n")
    a("## 6. Sizing Guidance\n")
    a("")
    dd_train = train.get("max_dd", 0) if isinstance(train, dict) else 0
    dd_holdout = holdout.get("max_dd", 0) if isinstance(holdout, dict) else 0
    worst_dd = min(dd_train, dd_holdout)  # more negative = worse
    sharpe_conservative = min(
        train.get("sharpe", 0) if isinstance(train, dict) else 0,
        holdout.get("sharpe", 0) if isinstance(holdout, dict) else 0,
    )

    a(f"- **Worst drawdown (TRAIN + HOLDOUT): {worst_dd*100:+.1f}%** — size so this "
      f"is tolerable at the chosen risk budget.\n")
    a(f"- **Conservative Sharpe:** {sharpe_conservative:.2f} (the lower of the two windows).\n")
    a(f"- **Monthly std dev (conservative): {max(train.get('monthly_std',0) if isinstance(train, dict) else 0, holdout.get('monthly_std',0) if isinstance(holdout, dict) else 0)*100:.1f}%** "
      f"— the expected monthly swing.\n")
    a(f"- **SEALED is NOT used for sizing.** The +20.52% SEALED return is likely "
      f"carry-favorable regime performance. Size on the conservative HOLDOUT-class "
      f"net and worst-case drawdown, not the headline.\n")
    a("")

    # ── Trend overlay note ──
    a("---\n")
    a("## 7. Trend Overlay (Optional — Not Evaluated)\n")
    a("The Trend sleeve's −0.246 correlation with Carry was identified in the "
      "pre-registration as a potential drawdown-reduction overlay. If evaluated, "
      "it would run on the same TRAIN/HOLDOUT data (no SEALED spend). "
      "This analysis is deferred — the report above provides the standalone "
      "Carry risk profile for sizing decisions.\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")

    print(f"\nReport: {REPORT}")
    for label in ["TRAIN", "HOLDOUT"]:
        m = metrics.get(label, {})
        if isinstance(m, dict) and "error" not in m:
            print(f"  {label}: ann_net={m['ann_net']*100:+.2f}%  worst_month={m['worst_month']*100:+.2f}%  max_dd={m['max_dd']*100:+.2f}%  sharpe={m['sharpe']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
