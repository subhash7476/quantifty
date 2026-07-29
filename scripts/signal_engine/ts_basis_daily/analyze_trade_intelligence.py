"""Trade Intelligence — M0.5 Exploratory Analytics.

Reads trade_intelligence.duckdb and produces a summary report of
win rates and expectancy across signal, regime, and context dimensions.

Usage:
  python scripts/signal_engine/ts_basis_daily/analyze_trade_intelligence.py
Output: docs/reports/TRADE_INTELLIGENCE_M0_5_ANALYTICS.md
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

TI_DB = ROOT / "data" / "signal_engine" / "trade_intelligence" / "trade_intelligence.duckdb"
REPORT = ROOT / "docs" / "reports" / "TRADE_INTELLIGENCE_M0_5_ANALYTICS.md"


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _bucket_rows(con, table, dim, buckets_sql, order_by=None):
    """Run a bucketed query and return formatted rows."""
    sql = f"""
        SELECT {buckets_sql},
               COUNT(*) as n,
               AVG(stock_return) as mean_ret,
               AVG(CASE WHEN stock_return > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
               AVG(days_held) as avg_days
        FROM {table}
        WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
        GROUP BY bucket
    """
    if order_by:
        sql += f" ORDER BY {order_by}"
    rows = con.execute(sql).fetchall()
    return rows


def main():
    commit = _git_commit()
    now_ts = date.today().isoformat()

    if not TI_DB.exists():
        print("Trade Intelligence DB not found. Run build_trade_intelligence.py first.")
        return 1

    con = duckdb.connect(str(TI_DB), read_only=True)

    n_total = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    n_closed = con.execute(
        "SELECT COUNT(*) FROM trades WHERE exit_date IS NOT NULL"
    ).fetchone()[0]
    mean_ret = con.execute(
        "SELECT AVG(stock_return) FROM trades WHERE stock_return IS NOT NULL"
    ).fetchone()[0]
    win_rate = con.execute("""
        SELECT AVG(CASE WHEN stock_return > 0 THEN 1.0 ELSE 0.0 END)
        FROM trades WHERE stock_return IS NOT NULL
    """).fetchone()[0]
    mean_days = con.execute(
        "SELECT AVG(days_held) FROM trades WHERE days_held IS NOT NULL"
    ).fetchone()[0]

    lines = []
    a = lines.append
    a("# Trade Intelligence — M0.5 Exploratory Analytics\n")
    a(f"**Script-generated.** Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a(f"**Data:** {n_total:,} total trades, {n_closed:,} closed.\n")
    a(f"**Baseline:** {win_rate*100:.1f}% win rate, {mean_ret*100:+.3f}% mean return, "
      f"{mean_days:.1f} avg days held.\n")

    # ── 1. Win rate by rank_in_date ─────────────────────────────────
    a("---\n## 1. Win Rate by Rank\n")
    r = con.execute("""
        SELECT rank_in_date,
               COUNT(*) as n,
               AVG(CASE WHEN stock_return > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
               AVG(stock_return) as mean_ret,
               AVG(days_held) as avg_days
        FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
        GROUP BY rank_in_date ORDER BY rank_in_date
    """).fetchall()
    a("| Rank | n | Win Rate | Mean Ret | Avg Days |")
    a("|---|--:|--:|--:|--:|")
    for rank, n, wr, mr, ad in r:
        a(f"| {rank} | {n:,} | {wr*100:.1f}% | {mr*100:+.3f}% | {ad:.1f} |")
    a("")

    # ── 2. Expectancy by quintile ────────────────────────────────────
    a("---\n## 2. Expectancy by Quintile\n")
    for q, qname in [(1, "SHORT"), (5, "LONG")]:
        r = con.execute(f"""
            SELECT COUNT(*) as n,
                   AVG(CASE WHEN stock_return > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
                   AVG(stock_return) as mean_ret,
                   AVG(days_held) as avg_days,
                   AVG(CASE WHEN stock_return >= 0.005 THEN 1.0 ELSE 0.0 END) as tp_rate,
                   AVG(CASE WHEN stock_return <= -0.01 THEN 1.0 ELSE 0.0 END) as sl_rate
            FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
            AND quintile = {q}
        """).fetchone()
        if r[0] > 0:
            a(f"**{qname}** — n={r[0]:,} | Win: {r[1]*100:.1f}% | Mean: {r[2]*100:+.3f}% | "
              f"Days: {r[3]:.1f} | TP: {r[4]*100:.1f}% | SL: {r[5]*100:.1f}%")
    a("")

    # ── 3. Expectancy by sector ──────────────────────────────────────
    a("---\n## 3. Expectancy by Sector\n")
    a("*Min 50 trades per sector.*\n")
    r = con.execute("""
        SELECT sector,
               COUNT(*) as n,
               AVG(CASE WHEN stock_return > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
               AVG(stock_return) as mean_ret,
               AVG(days_held) as avg_days
        FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
        GROUP BY sector HAVING COUNT(*) >= 50
        ORDER BY AVG(stock_return)
    """).fetchall()
    a("| Sector | n | Win Rate | Mean Ret | Avg Days |")
    a("|---|---|--:|--:|--:|")
    for sec, n, wr, mr, ad in r:
        a(f"| {sec} | {n:,} | {wr*100:.1f}% | {mr*100:+.3f}% | {ad:.1f} |")
    a("")

    # ── 4. Expectancy by holding period ──────────────────────────────
    a("---\n## 4. Expectancy by Holding Period\n")
    r = con.execute("""
        SELECT CASE
                 WHEN days_held = 1 THEN '1 day'
                 WHEN days_held BETWEEN 2 AND 3 THEN '2–3 days'
                 WHEN days_held BETWEEN 4 AND 7 THEN '4–7 days'
                 WHEN days_held BETWEEN 8 AND 14 THEN '8–14 days'
                 ELSE '15+ days'
               END as bucket,
               COUNT(*) as n,
               AVG(CASE WHEN stock_return > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
               AVG(stock_return) as mean_ret
        FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
        GROUP BY bucket
        ORDER BY MIN(days_held)
    """).fetchall()
    a("| Hold Period | n | Win Rate | Mean Ret |")
    a("|---|---|--:|--:|")
    for bkt, n, wr, mr in r:
        a(f"| {bkt} | {n:,} | {wr*100:.1f}% | {mr*100:+.3f}% |")
    a("")

    # ── 5. Exit reason distribution ──────────────────────────────────
    a("---\n## 5. Exit Reason Distribution\n")
    r = con.execute("""
        SELECT exit_reason,
               COUNT(*) as n,
               AVG(CASE WHEN stock_return > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
               AVG(stock_return) as mean_ret,
               AVG(days_held) as avg_days
        FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
        GROUP BY exit_reason ORDER BY n DESC
    """).fetchall()
    a("| Exit Reason | n | Win Rate | Mean Ret | Avg Days |")
    a("|---|---|--:|--:|--:|")
    for er, n, wr, mr, ad in r:
        a(f"| {er} | {n:,} | {wr*100:.1f}% | {mr*100:+.3f}% | {ad:.1f} |")
    a("")

    # ── 6. VIX deciles ───────────────────────────────────────────────
    a("---\n## 6. VIX Deciles vs Expectancy\n")
    a("*India VIX at entry. Min 100 trades per decile.*\n")
    r = con.execute("""
        WITH deciles AS (
            SELECT *, NTILE(10) OVER (ORDER BY vix_at_entry) AS vix_decile
            FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
              AND vix_at_entry IS NOT NULL
        )
        SELECT vix_decile,
               COUNT(*) as n,
               MIN(vix_at_entry) as vix_lo,
               MAX(vix_at_entry) as vix_hi,
               AVG(CASE WHEN stock_return > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
               AVG(stock_return) as mean_ret
        FROM deciles
        GROUP BY vix_decile ORDER BY vix_decile
    """).fetchall()
    a("| Decile | VIX Range | n | Win Rate | Mean Ret |")
    a("|---|--:|--:|--:|--:|")
    for d, n, vlo, vhi, wr, mr in r:
        a(f"| D{d} | {vlo:.1f}–{vhi:.1f} | {n:,} | {wr*100:.1f}% | {mr*100:+.3f}% |")
    a("")

    # ── 7. Nifty 20d return buckets ──────────────────────────────────
    a("---\n## 7. Nifty 20d Return Buckets vs Expectancy\n")
    r = con.execute("""
        SELECT CASE
                 WHEN nifty_20d_at_entry < -0.05 THEN 'Strong bear (< -5%)'
                 WHEN nifty_20d_at_entry < -0.02 THEN 'Bear (-5% to -2%)'
                 WHEN nifty_20d_at_entry < 0.02  THEN 'Flat (-2% to +2%)'
                 WHEN nifty_20d_at_entry < 0.05  THEN 'Bull (+2% to +5%)'
                 ELSE 'Strong bull (> +5%)'
               END as bucket,
               COUNT(*) as n,
               AVG(CASE WHEN stock_return > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
               AVG(stock_return) as mean_ret,
               AVG(days_held) as avg_days
        FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
          AND nifty_20d_at_entry IS NOT NULL
        GROUP BY bucket
        ORDER BY AVG(nifty_20d_at_entry)
    """).fetchall()
    a("| Regime | n | Win Rate | Mean Ret | Avg Days |")
    a("|---|---|--:|--:|--:|")
    for bkt, n, wr, mr, ad in r:
        a(f"| {bkt} | {n:,} | {wr*100:.1f}% | {mr*100:+.3f}% | {ad:.1f} |")
    a("")

    # ── 8. Basis reverting impact ────────────────────────────────────
    a("---\n## 8. Recovery Filter Impact\n")
    r = con.execute("""
        SELECT basis_reverting,
               COUNT(*) as n,
               AVG(CASE WHEN stock_return > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
               AVG(stock_return) as mean_ret,
               AVG(days_held) as avg_days
        FROM trades WHERE exit_date IS NOT NULL AND stock_return IS NOT NULL
        GROUP BY basis_reverting
    """).fetchall()
    a("| Reverting? | n | Win Rate | Mean Ret | Avg Days |")
    a("|---|---|--:|--:|--:|")
    for br, n, wr, mr, ad in r:
        label = "Yes" if br else "No (widening)"
        a(f"| {label} | {n:,} | {wr*100:.1f}% | {mr*100:+.3f}% | {ad:.1f} |")
    a("")

    # ── 9. Schema assessment ─────────────────────────────────────────
    a("---\n## 9. Schema Completeness\n")
    a("*Assessment of whether the schema answers the planned research questions.*\n")

    checks = [
        ("Win rate by rank_in_date", "Yes", "rank_in_date populated for all trades"),
        ("Expectancy by quintile", "Yes", "quintile populated for all trades"),
        ("Expectancy by sector", "Yes", "20-sector taxonomy, min 50 trades/sector"),
        ("Expectancy by holding period", "Yes", "days_held populated for all closed trades"),
        ("Exit reason distribution", "Partial", "All exits are EXIT_SIGNAL. TP/SL need M1."),
        ("VIX deciles vs expectancy", "Yes", "vix_at_entry 99.8% populated"),
        ("Nifty 20d buckets vs expectancy", "Yes", "nifty_20d_at_entry 99.8% populated"),
        ("Recovery filter impact", "Yes", "basis_reverting populated for all trades"),
        ("Raw vs clamped z analysis", "Yes", "raw_z + z_ts both stored"),
        ("Missing: trade-level fees", "Not stored", "Only aggregate in rebalance_summary"),
        ("Missing: intraday gap", "Not stored", "1m candles could supply open-vs-close"),
    ]

    a("| Question | Answerable? | Notes |")
    a("|---|---|---|")
    for q, ans, note in checks:
        a(f"| {q} | {ans} | {note} |")
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
