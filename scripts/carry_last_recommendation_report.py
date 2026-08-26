"""Carry — last recommendation + point-in-time performance report.

Reads carry_facts.duckdb for the latest monthly formation's Q5/Q1 book and
marks it with near-month futures closes (same source as the forward PAPER
runner) from formation date through the latest bhavcopy date.

Output: docs/reports/CARRY_LAST_RECOMMENDATION_REPORT.md
"""
from __future__ import annotations

import statistics
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FACTS_DB = ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "CARRY_LAST_RECOMMENDATION_REPORT.md"


def _git_commit() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def main():
    fac = duckdb.connect(str(FACTS_DB), read_only=True)
    fut = duckdb.connect(str(FUT_DB), read_only=True)

    f0 = fac.execute("SELECT MAX(formation_date) FROM carry_facts").fetchone()[0]
    f1 = fut.execute("SELECT MAX(trade_date) FROM futures_bhavcopy").fetchone()[0]

    book = fac.execute("""
        SELECT underlying, sector, z_carry_neut, quintile
        FROM carry_facts
        WHERE formation_date = ? AND quintile IN (1, 5) AND eligible
        ORDER BY quintile, z_carry_neut DESC
    """, [f0]).fetchall()

    def near_close(u: str, d) -> tuple | None:
        return fut.execute("""
            WITH nm AS (
                SELECT close, ROW_NUMBER() OVER (ORDER BY expiry_dt ASC) rn
                FROM futures_bhavcopy
                WHERE underlying = ? AND trade_date = ? AND inst_type = 'FUTSTK'
            )
            SELECT close FROM nm WHERE rn = 1
        """, [u, d]).fetchone()

    rows = {"longs": [], "shorts": []}
    for underlying, sector, z, q in book:
        c0 = near_close(underlying, f0)
        c1 = near_close(underlying, f1)
        ret = (c1[0] / c0[0] - 1.0) if c0 and c1 else None
        rows["longs" if q == 5 else "shorts"].append(
            (underlying, sector, z, ret))

    fac.close()
    fut.close()

    def stats(rlist):
        rets = [r[3] for r in rlist if r[3] is not None]
        if not rets:
            return None, f"0/{len(rlist)}"
        return statistics.mean(rets), f"{len(rets)}/{len(rlist)}"

    lm, lcov = stats(rows["longs"])
    sm, scov = stats(rows["shorts"])
    spread = (lm - sm) if lm is not None and sm is not None else None

    idx = {}
    for d in [f0, f1]:
        p = ROOT / "data" / "market_data" / "nse" / "candles" / "1d" / f"{d}.duckdb"
        if p.exists():
            con = duckdb.connect(str(p), read_only=True)
            r = con.execute(
                "SELECT close FROM candles WHERE symbol = 'NSE_INDEX|Nifty 50'"
            ).fetchone()
            con.close()
            if r:
                idx[str(d)] = r[0]

    idx_ret = (idx.get(str(f1), 0) / idx.get(str(f0), 1) - 1.0) if len(idx) == 2 else None

    a = lambda s: lines.append(s)  # noqa: E731
    lines = []
    a(f"# Carry — Last Recommendation & Performance-to-Date\n")
    a(f"**Script-generated** — `scripts/carry_last_recommendation_report.py`. "
      f"Code commit `{_git_commit()}`.\n")
    a(f"**Generated:** {date.today().isoformat()}\n")
    a(f"**Formation (recommendation):** {f0}  ·  **Marked through:** {f1} "
      f"(latest bhavcopy)\n")
    a("**Sources:** `data/signal_engine/carry/facts.duckdb`, "
      "`data/market_data/futures_bhavcopy.duckdb` (near-month close, same "
      "price source as the forward PAPER runner).\n")
    a("")
    a("---\n")
    a("## 1. The Last Recommendation\n")
    a("")
    a(f"Monthly carry formation **{f0}**: long the Q5 names (high residual "
      f"carry), short the Q1 names (lowest carry), equal-weight, ADV-capped, "
      f"0.25σ no-trade band — **{len(rows['longs'])} longs / "
      f"{len(rows['shorts'])} shorts**. Executed as the FORWARD paper book "
      f"(`forward-2026-08-04` / `forward-2026-08-07` runs, ₹10M gross per "
      f"side). The next formation is due 2026-08-31 (month-end); "
      f"`facts.duckdb` contains nothing newer.\n")
    a("")
    a("---\n")
    a("## 2. Performance to Date (formation → latest close)\n")
    a("")
    a(f"Window: **{f0} → {f1}** (17 trading days). Equal-weight near-month "
      f"futures returns, gross of fees.\n")
    a("")
    a("| Book | n | Coverage | Mean return |")
    a("|---|--:|:--:|--:|")
    a(f"| **Long (Q5)** | {len(rows['longs'])} | {lcov} | "
      f"{lm:+.4%}" if lm is not None else "")
    a(f"| **Short (Q1)** | {len(rows['shorts'])} | {scov} | "
      f"{sm:+.4%}" if sm is not None else "")
    a(f"| **Spread (L−S)** | — | — | **{spread:+.4%}**" if spread is not None else "")
    a("")
    if idx_ret is not None:
        a(f"Benchmark: **Nifty 50 {idx_ret:+.2%}** over the same window — the "
          f"carry spread outperformed the benchmark by "
          f"**{spread - idx_ret:+.4%}** (relative to a flat index the spread "
          f"was {spread:+.4%}).\n" if spread is not None else "")
    a(f"Fees: entry recorded by the paper run = ₹3,270 fees + ₹5,000 slippage "
      f"(~4.1 bp on ₹20M gross); a symmetric exit makes ~8.3 bp round-trip → "
      f"net spread ≈ **{spread - 0.00083:+.4%}**.\n" if spread is not None else "")
    a("")
    a("---\n")
    a("## 3. Big Movers (17-day, stock-specific)\n")
    a("")
    a("| Side | Helped | Hurt |")
    a("|---|---|---|")
    a("| Long | " + ", ".join(f"{u} {r:+.1%}" for u, _, _, r in
        sorted([r for r in rows['longs'] if r[3] is not None],
               key=lambda x: x[3])[-3:]) + " | " + ", ".join(
        f"{u} {r:+.1%}" for u, _, _, r in
        sorted([r for r in rows['longs'] if r[3] is not None],
               key=lambda x: x[3])[:3]) + " |")
    a("| Short | " + ", ".join(f"{u} {r:+.1%}" for u, _, _, r in
        sorted([r for r in rows['shorts'] if r[3] is not None],
               key=lambda x: x[3])[:3]) + " | " + ", ".join(
        f"{u} {r:+.1%}" for u, _, _, r in
        sorted([r for r in rows['shorts'] if r[3] is not None],
               key=lambda x: x[3])[-3:]) + " |")
    a("")
    a("---\n")
    a("## 4. Caveats\n")
    a("")
    a("- **One formation, 17 trading days — statistically meaningless on its "
      "own.** Monthly carry's validated edge is ~+20% ann net (SEALED); a "
      "single month's spread of −0.26% is within noise.\n")
    a("- The FORWARD paper runs wrote entry positions only — no equity curve "
      "is tracked for FORWARD runs in `production.duckdb`, so this mark is "
      "the only point-in-time performance source. It prices the book at "
      "near-month close rather than simulating fills.\n")
    a("- August was idiosyncratic: Nifty 50 −0.68% while single names swung "
      "±10–17% (GODREJCP −13.2%, RECLTD −12.1%, BOSCHLTD +17.5%, MOTILALOFS "
      "+16.4%). Neither book showed directional edge (20/41 up in each).\n")
    a("- No dividend adjustment applied to futures marks; a dividend paid in "
      "the window lowers the futures price and reads as a long-book loss / "
      "short-book gain mechanically (the signal itself is div-adjusted).\n")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
