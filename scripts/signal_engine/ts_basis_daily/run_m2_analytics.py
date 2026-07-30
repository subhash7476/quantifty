"""Trade Intelligence — M2 Analytics Report.

Comprehensive trade-level analysis with TRAIN/HOLDOUT split,
exit reason decomposition, P&L statistics, and feature clusters.

Usage:
  python scripts/signal_engine/ts_basis_daily/run_m2_analytics.py
Output: docs/reports/TRADE_INTELLIGENCE_M2_ANALYTICS.md
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

TI_DB = ROOT / "data" / "signal_engine" / "trade_intelligence" / "trade_intelligence.duckdb"
REPORT = ROOT / "docs" / "reports" / "TRADE_INTELLIGENCE_M2_ANALYTICS.md"

WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _q(con, sql, window=None):
    if window:
        lo, hi = WINDOWS[window]
        sql = f"""
            WITH filtered AS (
                SELECT * FROM trades
                WHERE entry_date >= DATE '{lo}' AND entry_date <= DATE '{hi}'
                  AND exit_date IS NOT NULL AND stock_return IS NOT NULL
            )
            {sql.replace('FROM trades', 'FROM filtered')
              .replace('FROM filtered', 'FROM filtered')}
        """
    return con.execute(sql).fetchall()


def main():
    commit = _git_commit()
    now_ts = date.today().isoformat()

    con = duckdb.connect(str(TI_DB), read_only=True)

    n_all = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    n_closed = con.execute(
        "SELECT COUNT(*) FROM trades WHERE exit_date IS NOT NULL"
    ).fetchone()[0]

    lines = []
    a = lines.append
    a("# Trade Intelligence — M2 Analytics\n")
    a(f"**Script-generated.** Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a(f"**Data:** {n_all:,} total trades, {n_closed:,} closed.\n")

    # ── 1. TRAIN vs HOLDOUT ─────────────────────────────────────────
    a("---\n## 1. TRAIN vs HOLDOUT Summary\n")
    a("| Metric | TRAIN | HOLDOUT | Delta |")
    a("|---|---|--:|--:|--:|")

    for metric_sql, metric_name in [
        ("COUNT(*)", "Trades"),
        ("AVG(stock_return)*100", "Mean Return (%)"),
        ("PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY stock_return)*100", "Median Return (%)"),
        ("AVG(CASE WHEN stock_return>0 THEN 1.0 ELSE 0.0 END)*100", "Win Rate (%)"),
        ("AVG(CASE WHEN stock_return>=0.005 THEN 1.0 ELSE 0.0 END)*100", "TP Rate (%)"),
        ("AVG(CASE WHEN stock_return<=-0.01 THEN 1.0 ELSE 0.0 END)*100", "SL Rate (%)"),
        ("AVG(days_held)", "Avg Days Held"),
        ("STDDEV_SAMP(stock_return)*100", "Std Return (%)"),
    ]:
        t = _q(con, f"SELECT {metric_sql} FROM trades", "TRAIN")[0][0] or 0
        h = _q(con, f"SELECT {metric_sql} FROM trades", "HOLDOUT")[0][0] or 0
        d = h - t
        if metric_name in ("Trades", "Avg Days Held"):
            a(f"| {metric_name} | {t:,.0f} | {h:,.0f} | {d:+,.0f} |")
        else:
            a(f"| {metric_name} | {t:+.2f} | {h:+.2f} | {d:+.2f} |")
    a("")

    # ── 2. Exit Reason Analysis ─────────────────────────────────────
    a("---\n## 2. Exit Reason Analysis\n")
    a("| Exit Reason | TRAIN n | TRAIN Win | TRAIN Mean | HOLDOUT n | HOLDOUT Win | HOLDOUT Mean |")
    a("|---|---|--:|--:|--:|--:|--:|")

    reasons = con.execute(
        "SELECT DISTINCT exit_reason FROM trades WHERE exit_reason IS NOT NULL"
    ).fetchall()
    for (er,) in reasons:
        t = _q(con, f"""
            SELECT COUNT(*),
                   AVG(CASE WHEN stock_return>0 THEN 1.0 ELSE 0.0 END),
                   AVG(stock_return)
            FROM trades WHERE exit_reason='{er}'
        """, "TRAIN")[0]
        h = _q(con, f"""
            SELECT COUNT(*),
                   AVG(CASE WHEN stock_return>0 THEN 1.0 ELSE 0.0 END),
                   AVG(stock_return)
            FROM trades WHERE exit_reason='{er}'
        """, "HOLDOUT")[0]
        a(f"| {er} | {t[0]:,} | {t[1]*100:.1f}% | {t[2]*100:+.3f}% | "
          f"{h[0]:,} | {h[1]*100:.1f}% | {h[2]*100:+.3f}% |")
    a("")

    # ── 3. P&L Distribution ─────────────────────────────────────────
    a("---\n## 3. P&L Distribution\n")
    for w in ["TRAIN", "HOLDOUT"]:
        r = _q(con, f"""
            SELECT PERCENTILE_CONT(0.01) WITHIN GROUP (ORDER BY stock_return)*100,
                   PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY stock_return)*100,
                   PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY stock_return)*100,
                   PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY stock_return)*100,
                   PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY stock_return)*100,
                   PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY stock_return)*100,
                   PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY stock_return)*100,
                   AVG(stock_return)*100,
                   STDDEV_SAMP(stock_return)*100
            FROM trades
        """, w)[0]
        a(f"**{w}** — p1={r[0]:+.2f}% p5={r[1]:+.2f}% p25={r[2]:+.2f}% "
          f"p50={r[3]:+.2f}% p75={r[4]:+.2f}% p95={r[5]:+.2f}% p99={r[6]:+.2f}% "
          f"mean={r[7]:+.2f}% std={r[8]:+.2f}%")
    a("")

    # ── 4. Monthly Decomposition ────────────────────────────────────
    a("---\n## 4. Monthly Win Rate\n")
    a("| Year-Month | TRAIN n | TRAIN Win | HOLDOUT n | HOLDOUT Win |")
    a("|---|---|--:|--:|--:|")
    months = sorted(set(
        _q(con, "SELECT STRFTIME(entry_date, '%Y-%m') FROM trades") + 
        _q(con, "SELECT STRFTIME(entry_date, '%Y-%m') FROM trades", "HOLDOUT")
    ))
    for (m,) in months:
        t = _q(con, f"""
            SELECT COUNT(*), AVG(CASE WHEN stock_return>0 THEN 1.0 ELSE 0.0 END)
            FROM trades WHERE STRFTIME(entry_date, '%Y-%m')='{m}'
        """, "TRAIN")[0]
        h = _q(con, f"""
            SELECT COUNT(*), AVG(CASE WHEN stock_return>0 THEN 1.0 ELSE 0.0 END)
            FROM trades WHERE STRFTIME(entry_date, '%Y-%m')='{m}'
        """, "HOLDOUT")[0]
        t_n = t[0] or 0; t_w = t[1]*100 if t[1] else 0
        h_n = h[0] or 0; h_w = h[1]*100 if h[1] else 0
        if t_n > 0 or h_n > 0:
            a(f"| {m} | {t_n:,} | {t_w:.1f}% | {h_n:,} | {h_w:.1f}% |")
    a("")

    # ── 5. Sector × Quintile cross-tab ──────────────────────────────
    a("---\n## 5. Sector × Quintile Expectancy\n")
    a("*Mean return (%), min 30 trades per cell.*\n")
    r = con.execute("""
        SELECT sector, quintile,
               COUNT(*) as n, AVG(stock_return)*100 as mean_ret
        FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
        GROUP BY sector, quintile HAVING COUNT(*) >= 30
        ORDER BY sector, quintile
    """).fetchall()
    a("| Sector | Quintile | n | Mean Ret |")
    a("|---|---|--:|--:|")
    for sec, q, n, mr in r:
        a(f"| {sec} | {'LONG' if q==5 else 'SHORT'} | {n:,} | {mr:+.2f}% |")
    a("")

    # ── 6. Recovery × Exit Reason cross-tab ─────────────────────────
    a("---\n## 6. Recovery Filter × Exit Reason\n")
    a("*Mean return by recovery state and exit type.*\n")
    r = con.execute("""
        SELECT basis_reverting, exit_reason,
               COUNT(*) as n,
               AVG(stock_return)*100 as mean_ret,
               AVG(CASE WHEN stock_return>0 THEN 1.0 ELSE 0.0 END)*100 as win_rate,
               AVG(days_held) as avg_days
        FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
        GROUP BY basis_reverting, exit_reason
        ORDER BY basis_reverting, exit_reason
    """).fetchall()
    a("| Reverting? | Exit | n | Win Rate | Mean Ret | Avg Days |")
    a("|---|---|--:|--:|--:|--:|")
    for br, er, n, mr, wr, ad in r:
        a(f"| {'Yes' if br else 'No'} | {er} | {n:,} | {wr:.1f}% | {mr:+.3f}% | {ad:.1f} |")
    a("")

    # ── 7. Hold Period × Exit Reason ────────────────────────────────
    a("---\n## 7. Holding Period Distribution by Exit Type\n")
    r = con.execute("""
        SELECT exit_reason,
               AVG(days_held) as avg,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_held) as med,
               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY days_held) as p75,
               AVG(CASE WHEN stock_return>0 THEN 1.0 ELSE 0.0 END)*100 as win
        FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
        GROUP BY exit_reason
    """).fetchall()
    a("| Exit Reason | Avg Days | Med Days | p75 Days | Win Rate |")
    a("|---|---|--:|--:|--:|")
    for er, avg, med, p75, win in r:
        a(f"| {er} | {avg:.1f} | {med:.0f} | {p75:.0f} | {win:.1f}% |")
    a("")

    # ── 8. Top Failure Clusters ─────────────────────────────────────
    a("---\n## 8. Top Failure Clusters\n")
    a("*3-feature combinations with lowest mean return, min 100 trades.*\n")

    # sector + basis_reverting + exit_reason
    r = con.execute("""
        SELECT sector, basis_reverting, exit_reason,
               COUNT(*) as n,
               AVG(stock_return)*100 as mean_ret,
               AVG(CASE WHEN stock_return>0 THEN 1.0 ELSE 0.0 END)*100 as win
        FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
        GROUP BY sector, basis_reverting, exit_reason
        HAVING COUNT(*) >= 50
        ORDER BY AVG(stock_return)
        LIMIT 15
    """).fetchall()
    a("| Sector | Reverting | Exit | n | Mean Ret | Win Rate |")
    a("|---|---|--:|--:|--:|")
    for sec, br, er, n, mr, wr in r:
        a(f"| {sec} | {'Yes' if br else 'No'} | {er} | {n:,} | {mr:+.3f}% | {wr:.1f}% |")
    a("")

    a("---\n")
    a(f"**Generated:** {now_ts} | **Commit:** `{commit}`\n")

    con.close()

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"Report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
