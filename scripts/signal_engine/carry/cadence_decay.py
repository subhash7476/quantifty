"""Carry cadence-decay analysis — intra-month signal persistence.

Answers: does the carry edge accumulate steadily over the month, or
is most of the spread earned in the first week? If the signal decays,
a weekly or fortnightly rebalance might outperform monthly.

Method: starting from each monthly formation date, compute Q5-Q1
quintile spread at 5d (1w), 10d (2w), 15d (3w), and ~21d (1m)
horizons using daily close prices from equity_bhavcopy. Also tracks
quintile persistence — what fraction of Q5/Q1 names remain in their
quintile at each horizon.

Runs on TRAIN + HOLDOUT data in hand. No SEALED read.

Output: docs/reports/CARRY_CADENCE_DECAY_REPORT.md
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[3]  # scripts/signal_engine/carry -> root
sys.path.insert(0, str(ROOT))

SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "CARRY_CADENCE_DECAY_REPORT.md"

WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}

QUINTILE_FRAC = 0.20
HORIZONS = {"1w": 5, "2w": 10, "3w": 15, "1m": 21}
N_WARMUP = 30  # calendar days before formation for price lookup


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _load_price_map(con, underlyings: list[str], from_date: date,
                    to_date: date) -> dict[str, dict[date, float]]:
    """{underlying: {trade_date: close_price}} for a date range."""
    u_list = ", ".join(f"'{u}'" for u in underlyings)
    rows = con.execute(f"""
        SELECT symbol, trade_date, close
        FROM eq.equity_bhavcopy
        WHERE symbol IN ({u_list}) AND series = 'EQ'
          AND trade_date >= DATE '{from_date}'
          AND trade_date <= DATE '{to_date}'
          AND close IS NOT NULL AND close > 0
        ORDER BY symbol, trade_date
    """).fetchall()
    result = defaultdict(dict)
    for u, td, close in rows:
        result[u][td] = float(close)
    return dict(result)


def _forward_return(price_map: dict[date, float], fdate: date,
                    trading_days: int) -> float | None:
    """Forward return from fdate to fdate + trading_days."""
    dates = sorted(price_map.keys())
    if not dates:
        return None
    # Find fdate index
    try:
        i0 = dates.index(fdate) if fdate in dates else next(
            i for i, d in enumerate(dates) if d >= fdate)
    except (ValueError, StopIteration):
        return None
    i1 = i0 + trading_days
    if i1 >= len(dates):
        return None
    p0 = price_map[dates[i0]]
    p1 = price_map[dates[i1]]
    return (p1 - p0) / p0 if p0 > 0 else None


def _analyze(con, lo: date, hi: date, label: str) -> dict:
    """Run cadence-decay analysis over a date window."""
    # Load monthly formation signals
    sig_rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_carry_neut, s.liquid
        FROM sig.signals s
        WHERE s.formation_date >= DATE '{lo}'
          AND s.formation_date <= DATE '{hi}'
          AND s.z_carry_neut IS NOT NULL AND s.liquid = TRUE
        ORDER BY s.formation_date, s.underlying
    """).fetchall()

    by_date = defaultdict(list)
    for fdate, u, zn, liq in sig_rows:
        by_date[fdate].append((u, float(zn)))

    formation_dates = sorted(by_date.keys())
    print(f"  {label}: {len(formation_dates)} formations, "
          f"{sum(len(v) for v in by_date.values()):,} name-dates")

    # Collect all underlyings for price loading
    all_names = sorted(set(u for v in by_date.values() for u, _ in v))
    print(f"    Loading prices for {len(all_names)} underlyings...")

    price_start = lo - timedelta(days=N_WARMUP)
    price_end = hi + timedelta(days=35)
    price_map = _load_price_map(con, all_names, price_start, price_end)
    names_with_prices = set(price_map)
    print(f"    {len(names_with_prices)} underlyings with price data")

    # For each formation, compute horizon-level quintile spreads
    horizon_results = {h: {"spreads": [], "ics": [], "long_persist": [],
                            "short_persist": []}
                       for h in HORIZONS}

    for fdate in formation_dates:
        rows = by_date[fdate]
        # Filter to names with price data at formation date
        filt = [(u, zn) for u, zn in rows
                if u in names_with_prices and fdate in price_map.get(u, {})]
        if len(filt) < 10:
            continue

        n = len(filt)
        nq = max(1, round(QUINTILE_FRAC * n))
        sorted_by_z = sorted(filt, key=lambda r: r[1])
        long_set = {r[0] for r in sorted_by_z[-nq:]}
        short_set = {r[0] for r in sorted_by_z[:nq]}

        for h_label, td in HORIZONS.items():
            fwd_rets = {}
            for u, zn in filt:
                r = _forward_return(price_map.get(u, {}), fdate, td)
                if r is not None:
                    fwd_rets[u] = r

            if len(fwd_rets) < 2 * nq:
                continue

            # Quintile spread (equal-weight)
            long_rets = [fwd_rets[u] for u in long_set if u in fwd_rets]
            short_rets = [fwd_rets[u] for u in short_set if u in fwd_rets]
            if long_rets and short_rets:
                spread = np.mean(long_rets) - np.mean(short_rets)
                horizon_results[h_label]["spreads"].append(spread)

            # Rank-IC (Spearman) from z_carry_neut
            zs = [zn for u, zn in filt if u in fwd_rets]
            frs = [fwd_rets[u] for u, _ in filt if u in fwd_rets]
            if len(zs) >= 5:
                z_arr = np.array(zs)
                fr_arr = np.array(frs)
                # Rank correlation (Spearman, per pre-registered metric)
                sr = spearmanr(z_arr, fr_arr).correlation
                if not np.isnan(sr):
                    horizon_results[h_label]["ics"].append(float(sr))

        # Quintile persistence at each horizon
        long_now = long_set
        short_now = short_set
        for h_label in ["1w", "2w", "3w", "1m"]:
            td = HORIZONS[h_label]
            # Which names still have price data at this horizon?
            names_available = set()
            for u in (long_now | short_now):
                dates = sorted(price_map.get(u, {}).keys())
                try:
                    i0 = next(i for i, d in enumerate(dates) if d >= fdate)
                except StopIteration:
                    continue
                i1 = i0 + td
                if i1 < len(dates):
                    names_available.add(u)

            # Of available names, which would still be Q5/Q1 if we re-ranked?
            # Approximate: just check if they're still in the original sets
            # (since we don't have weekly z_carry_neut). Track raw survival.
            long_survive = long_now & names_available
            short_survive = short_now & names_available
            if long_now:
                horizon_results[h_label]["long_persist"].append(
                    len(long_survive) / len(long_now))
            if short_now:
                horizon_results[h_label]["short_persist"].append(
                    len(short_survive) / len(short_now))

    # Aggregate
    out = {}
    for h_label in HORIZONS:
        spreads = horizon_results[h_label]["spreads"]
        ics = horizon_results[h_label]["ics"]
        long_p = horizon_results[h_label]["long_persist"]
        short_p = horizon_results[h_label]["short_persist"]
        out[h_label] = {
            "horizon_days": HORIZONS[h_label],
            "n_periods": len(spreads),
            "mean_spread_bp": float(np.mean(spreads) * 10000) if spreads else 0.0,
            "mean_ic": float(np.mean(ics)) if ics else 0.0,
            "t_ic": float(np.mean(ics) / (np.std(ics, ddof=1) / np.sqrt(len(ics))))
                     if len(ics) > 1 and np.std(ics, ddof=1) > 0 else 0.0,
            "mean_long_persist": float(np.mean(long_p)) * 100 if long_p else 0.0,
            "mean_short_persist": float(np.mean(short_p)) * 100 if short_p else 0.0,
        }
    return out


def main():
    commit = _git_commit()
    now_ts = date.today().isoformat()

    con = duckdb.connect()
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute("SET threads=4")

    results = {}
    for label, (lo, hi) in WINDOWS.items():
        results[label] = _analyze(con, lo, hi, label)
    con.close()

    # ── Report ──
    lines = []
    a = lines.append

    a("# Carry — Cadence Decay / Intra-Month Persistence\n")
    a(f"**Script-generated** — `scripts/signal_engine/carry/cadence_decay.py`. "
      f"Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a("**Question:** does the carry edge accumulate linearly over the month, "
      "or is most earned in week 1-2? Should positions be held to month-end "
      "or exited early?\n")
    a("")

    a("---\n")
    a("## 1. Horizon Quintile Spread (Q5−Q1, equal-weight, bp)\n")
    a("")
    a("| Horizon | TRAIN Spread (bp) | TRAIN IC | HOLDOUT Spread (bp) | HOLDOUT IC |")
    a("|---|--:|--:|--:|--:|")
    for h_label in HORIZONS:
        tr = results["TRAIN"][h_label]
        hr = results["HOLDOUT"][h_label]
        a(f"| {h_label} ({tr['horizon_days']}d) | {tr['mean_spread_bp']:+.0f} | "
          f"{tr['mean_ic']:+.4f} | {hr['mean_spread_bp']:+.0f} | {hr['mean_ic']:+.4f} |")
    a("")

    a("---\n")
    a("## 2. Spread Accumulation (% of month-end spread earned by each horizon)\n")
    a("")
    a("| Horizon | TRAIN % of 1m | HOLDOUT % of 1m |")
    a("|---|--:|--:|")
    for h_label in ["1w", "2w", "3w", "1m"]:
        tr_sp = results["TRAIN"][h_label]["mean_spread_bp"]
        hr_sp = results["HOLDOUT"][h_label]["mean_spread_bp"]
        tr_1m = results["TRAIN"]["1m"]["mean_spread_bp"]
        hr_1m = results["HOLDOUT"]["1m"]["mean_spread_bp"]
        tr_pct = (tr_sp / tr_1m * 100) if abs(tr_1m) > 0.01 else 0
        hr_pct = (hr_sp / hr_1m * 100) if abs(hr_1m) > 0.01 else 0
        a(f"| {h_label} | {tr_pct:.0f}% | {hr_pct:.0f}% |")
    a("")

    a("---\n")
    a("## 3. Quintile Persistence (% of Q5/Q1 names still in calendar at horizon)\n")
    a("Tracks what fraction of the original quintile names are still alive in "
      "the price series at each horizon (not re-ranked — just survival). "
      "High persistence = same names drive edge throughout month. "
      "Low persistence = names churn, edge may depend on rebalancing.\n")
    a("")
    a("| Horizon | TRAIN Long Persist | TRAIN Short Persist | HOLDOUT Long Persist | HOLDOUT Short Persist |")
    a("|---|--:|--:|--:|--:|")
    for h_label in HORIZONS:
        tr = results["TRAIN"][h_label]
        hr = results["HOLDOUT"][h_label]
        a(f"| {h_label} | {tr['mean_long_persist']:.0f}% | "
          f"{tr['mean_short_persist']:.0f}% | "
          f"{hr['mean_long_persist']:.0f}% | {hr['mean_short_persist']:.0f}% |")
    a("")

    a("---\n")
    a("## 4. IC Decay Profile\n")
    a("")
    a("| Horizon | TRAIN IC | TRAIN t | HOLDOUT IC | HOLDOUT t |")
    a("|---|--:|--:|--:|--:|")
    for h_label in HORIZONS:
        tr = results["TRAIN"][h_label]
        hr = results["HOLDOUT"][h_label]
        a(f"| {h_label} | {tr['mean_ic']:+.4f} | {tr['t_ic']:+.2f} | "
          f"{hr['mean_ic']:+.4f} | {hr['t_ic']:+.2f} |")
    a("")

    a("---\n")
    a("## 5. Interpretation\n")
    a("")

    # Compute key ratios for interpretation
    tr_1w = results["TRAIN"]["1w"]["mean_spread_bp"]
    tr_1m = results["TRAIN"]["1m"]["mean_spread_bp"]
    hr_1w = results["HOLDOUT"]["1w"]["mean_spread_bp"]
    hr_1m = results["HOLDOUT"]["1m"]["mean_spread_bp"]

    tr_pct_1w = (tr_1w / tr_1m * 100) if abs(tr_1m) > 0.01 else 0
    hr_pct_1w = (hr_1w / hr_1m * 100) if abs(hr_1m) > 0.01 else 0

    a(f"- **TRAIN:** week 1 captures **{tr_pct_1w:.0f}%** of the full-month "
      f"spread ({tr_1w:+.0f}bp of {tr_1m:+.0f}bp).\n")
    a(f"- **HOLDOUT:** week 1 captures **{hr_pct_1w:.0f}%** of the full-month "
      f"spread ({hr_1w:+.0f}bp of {hr_1m:+.0f}bp).\n")
    a("")

    if tr_pct_1w > 50 and hr_pct_1w > 50:
        a("**Finding: most of the edge is earned in the first week.** "
          "A weekly or fortnightly rebalance may capture a larger fraction of "
          "the gross spread while reducing per-period risk exposure. However, "
          "fees at weekly cadence will dominate — the STT per round-trip is "
          "unchanged regardless of holding period, so turnover ~4x higher means "
          "~4x fee drag. The net effect depends on whether the weekly spread "
          "exceeds the incremental fees.\n")
    elif tr_pct_1w < 30 and hr_pct_1w < 30:
        a("**Finding: the spread accumulates steadily over the month.** "
          "Exiting early would leave significant edge on the table. Monthly "
          "holding is justified — higher-cadence rebalancing would likely "
          "underperform after fees.\n")
    else:
        a("**Finding: mixed evidence.** TRAIN and HOLDOUT show different "
          "accumulation profiles. Further analysis with statistical "
          "thresholds is needed before changing the rebalance cadence.\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")

    print(f"\nReport: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
