"""Carry quintile persistence — hold vs rotate.

At each weekly formation, identifies Q5 (LONG) and Q1 (SHORT) names.
Tracks across subsequent weekly formations: what fraction of names stay
in their quintile? If >80% persist weekly, hold-to-month-end saves fees.
If <50% persist, weekly rotation captures the edge better.

Runs on weekly signals (weekly_signals.duckdb, partially neutralized).
Output: docs/reports/CARRY_PERSISTENCE_REPORT.md
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "weekly_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "CARRY_PERSISTENCE_REPORT.md"

QUINTILE_FRAC = 0.20


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
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute("SET threads=4")

    # ── Load weekly signals with z_carry_neut ──
    sig_rows = con.execute("""
        SELECT s.formation_date, s.underlying, s.z_carry_neut,
               f.fwd_formation_date
        FROM sig.signals s
        JOIN sig.formations f ON s.formation_date = f.formation_date
        WHERE s.z_carry_neut IS NOT NULL AND s.liquid = TRUE
          AND s.formation_date >= DATE '2016-03-01'
        ORDER BY s.formation_date, s.underlying
    """).fetchall()

    by_date = defaultdict(list)
    fwd_dates = {}
    for fdate, u, zn, nxt in sig_rows:
        by_date[fdate].append((u, float(zn)))
        if fdate not in fwd_dates and nxt:
            fwd_dates[fdate] = nxt

    formation_dates = sorted(by_date.keys())
    print(f"Loaded {len(formation_dates)} weekly formations, "
          f"{sum(len(v) for v in by_date.values()):,} signals")

    if not formation_dates:
        print("No data. Aborting.")
        return 1

    # ── Per-formation quintile assignment ──
    # {fdate: {underlying: quintile (1=bottom, 5=top)}}
    formation_quintiles = {}
    for fdate in formation_dates:
        rows = by_date[fdate]
        n = len(rows)
        nq = max(1, round(QUINTILE_FRAC * n))
        sorted_by_z = sorted(rows, key=lambda r: r[1])
        u_to_q = {}
        for i, (u, _) in enumerate(sorted_by_z):
            if i < nq:
                u_to_q[u] = 1  # short
            elif i >= n - nq:
                u_to_q[u] = 5  # long
            else:
                u_to_q[u] = 3  # middle
        formation_quintiles[fdate] = u_to_q

    # ── Persistence analysis: track Q5/Q1 names across subsequent weeks ──
    # For each formation, find the next 1, 2, 3, 4 weekly formations
    persistence = {"1w": {"long_persist": [], "short_persist": [], "n_pairs": 0},
                   "2w": {"long_persist": [], "short_persist": [], "n_pairs": 0},
                   "3w": {"long_persist": [], "short_persist": [], "n_pairs": 0},
                   "4w": {"long_persist": [], "short_persist": [], "n_pairs": 0}}

    for i, fdate in enumerate(formation_dates):
        q_now = formation_quintiles[fdate]
        longs = {u for u, q in q_now.items() if q == 5}
        shorts = {u for u, q in q_now.items() if q == 1}
        if not longs or not shorts:
            continue

        for horizon_idx, horizon_label in enumerate(["1w", "2w", "3w", "4w"], start=1):
            next_idx = i + horizon_idx
            if next_idx >= len(formation_dates):
                break
            next_date = formation_dates[next_idx]
            if next_date not in formation_quintiles:
                continue
            q_next = formation_quintiles[next_date]

            # What fraction of CURRENT longs remain long at NEXT?
            long_today = longs & set(q_next)
            long_still_long = {u for u in long_today if q_next.get(u) == 5}
            short_today = shorts & set(q_next)
            short_still_short = {u for u in short_today if q_next.get(u) == 1}

            if long_today:
                persistence[horizon_label]["long_persist"].append(
                    len(long_still_long) / len(long_today))
            if short_today:
                persistence[horizon_label]["short_persist"].append(
                    len(short_still_short) / len(short_today))
            persistence[horizon_label]["n_pairs"] += 1

    # ── Weekly rebalance vs hold simulation ──
    # Track: if we enter Q5/Q1 at week 0, hold for 1w / 2w / 3w / 4w,
    # what is the forward return?
    weekly_spreads = {"1w": [], "2w": [], "3w": [], "4w": []}

    for i, fdate in enumerate(formation_dates):
        q_now = formation_quintiles[fdate]
        longs = [u for u, q in q_now.items() if q == 5]
        shorts = [u for u, q in q_now.items() if q == 1]
        if not longs or not shorts:
            continue

        for horizon_idx, horizon_label in enumerate(["1w", "2w", "3w", "4w"], start=1):
            target_idx = i + horizon_idx
            if target_idx >= len(formation_dates):
                break
            target_date = formation_dates[target_idx]

            # Forward return: from fdate to target_date
            # Use fwd_ret in signals table (cumulative to next formation)
            # For multi-week, we need cumulative from fdate to target_date
            # Use daily prices from equity_bhavcopy
            pass  # need price data

    con.close()

    # ── Report ──
    lines = []
    a = lines.append

    a("# Carry — Quintile Persistence: Hold vs Rotate\n")
    a(f"**Script-generated** — `scripts/signal_engine/carry/persistence.py`. "
      f"Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a(f"**Data:** {len(formation_dates)} weekly formations with z_carry_neut "
      f"(TRAIN window only — neutralize incomplete for HOLDOUT).\n")
    a("")

    a("---\n")
    a("## 1. Quintile Persistence (% of Q5/Q1 names still in same quintile next week)\n")
    a("If high → monthly hold justified (same names, save fees). "
      "If low → weekly rotation justified (names churn, need to re-rank).\n")
    a("")
    a("| Horizon | Long Persist | Short Persist | N pairs |")
    a("|---|--:|--:|--:|")
    for h_label in ["1w", "2w", "3w", "4w"]:
        lp = np.mean(persistence[h_label]["long_persist"]) * 100 if persistence[h_label]["long_persist"] else 0
        sp = np.mean(persistence[h_label]["short_persist"]) * 100 if persistence[h_label]["short_persist"] else 0
        n = persistence[h_label]["n_pairs"]
        a(f"| {h_label} | {lp:.0f}% | {sp:.0f}% | {n} |")
    a("")

    # ── At month-end (4w): what fraction of original names are still Q5/Q1? ──
    a("---\n")
    a("## 2. Month-End Survival\n")
    a("Of names in Q5/Q1 at week 0, what fraction remain Q5/Q1 at week 4 "
      "(roughly one month later)?\n")
    a("")

    month_end = {"long": [], "short": []}
    for i, fdate in enumerate(formation_dates):
        q_now = formation_quintiles[fdate]
        longs = {u for u, q in q_now.items() if q == 5}
        shorts = {u for u, q in q_now.items() if q == 1}
        if not longs or not shorts:
            continue
        next_idx = i + 4
        if next_idx >= len(formation_dates):
            break
        next_date = formation_dates[next_idx]
        if next_date not in formation_quintiles:
            continue
        q_next = formation_quintiles[next_date]
        long_today = longs & set(q_next)
        short_today = shorts & set(q_next)
        if long_today:
            month_end["long"].append(
                sum(1 for u in long_today if q_next.get(u) == 5) / len(long_today))
        if short_today:
            month_end["short"].append(
                sum(1 for u in short_today if q_next.get(u) == 1) / len(short_today))

    a(f"- **Long persistence at month-end:** "
      f"{np.mean(month_end['long'])*100:.0f}% "
      f"(median {np.median(month_end['long'])*100:.0f}%, "
      f"range {np.min(month_end['long'])*100:.0f}–{np.max(month_end['long'])*100:.0f}%)\n")
    a(f"- **Short persistence at month-end:** "
      f"{np.mean(month_end['short'])*100:.0f}% "
      f"(median {np.median(month_end['short'])*100:.0f}%, "
      f"range {np.min(month_end['short'])*100:.0f}–{np.max(month_end['short'])*100:.0f}%)\n")
    a("")

    a("---\n")
    a("## 3. Interpretation\n")
    a("")
    lp1w = np.mean(persistence["1w"]["long_persist"]) * 100 if persistence["1w"]["long_persist"] else 0
    sp1w = np.mean(persistence["1w"]["short_persist"]) * 100 if persistence["1w"]["short_persist"] else 0
    lp4w = np.mean(persistence["4w"]["long_persist"]) * 100 if persistence["4w"]["long_persist"] else 0

    a(f"- **Week-to-week persistence:** {lp1w:.0f}% (long) / {sp1w:.0f}% (short) of names "
      f"stay in their quintile from one week to the next.\n")
    a(f"- **Month-end persistence:** {lp4w:.0f}% of original Q5 names are still Q5 "
      f"after 4 weeks.\n")
    a("")

    if lp1w > 70 and lp4w > 50:
        a("**Recommendation: HOLD to month-end.** Quintile membership is sticky — "
          "most names stay in their quintile throughout the month. Weekly rotation "
          "would generate ~4x turnover for largely the same book, increasing fees "
          "without capturing new edge. Monthly rebalance is correct.\n")
    elif lp1w < 50:
        a("**Recommendation: ROTATE weekly.** Quintile membership churns rapidly — "
          "fewer than half of Q5/Q1 names stay there week to week. Weekly rebalancing "
          "captures fresher signals and avoids holding names that have rotated out. "
          "The higher fee drag must be weighed against the fresher book.\n")
    else:
        a("**Recommendation: MIXED — depends on fee tolerance.** Week-to-week "
          "persistence is moderate. Weekly rotation would produce a somewhat different "
          "book each week and the net benefit depends on whether the incremental "
          "spread exceeds the ~4x higher fee drag. A fee-inclusive simulation is "
          "recommended.\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")

    print(f"\nReport: {REPORT}")
    print(f"1w pers: long={lp1w:.0f}% short={sp1w:.0f}%")
    print(f"4w pers: long={lp4w:.0f}% short={np.mean(persistence['4w']['short_persist'])*100 if persistence['4w']['short_persist'] else 0:.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
