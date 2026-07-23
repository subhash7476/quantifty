"""CarryRebalancerHook end-to-end integration verification.

Drives the full production chain through a real formation date:
  __call__ -> _execute -> margin check -> compute_target_book ->
  _execute_deltas -> position_tracker.update_from_fill()

Verifies: fills land, positions open, gross matches target, dedup works.
Run manually: python scripts/carry_integration_check.py
"""
from __future__ import annotations

import sys
from datetime import date, datetime, time
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import duckdb

from core.brokers.paper_broker import PaperBroker
from core.clock import RealTimeClock
from core.database.manager import DatabaseManager
from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
from core.execution.portfolio.carry_rebalancer import (
    CarryRebalancerHook, paper_gross_exposure_policy, PAPER_GROSS,
)
from core.execution.position_models import PositionSide

FACTS_DB = ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
BHAVCOPY_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "CARRY_INTEGRATION_SMOKE_REPORT.md"


def _git_commit() -> str:
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

    # ── Pick 3 formation dates from facts DB (early, mid, recent) ──
    con = duckdb.connect(str(FACTS_DB), read_only=True)
    all_dates = [r[0] for r in con.execute(
        "SELECT DISTINCT formation_date FROM carry_facts ORDER BY formation_date"
    ).fetchall()]
    con.close()

    test_dates = [all_dates[3], all_dates[len(all_dates) // 2], all_dates[-1]]
    print(f"Testing {len(test_dates)} formation dates: {test_dates}")

    results: List[dict] = []

    for fdate in test_dates:
        fdate_clean = fdate if isinstance(fdate, date) else date.fromisoformat(str(fdate))

        # ── Fresh handler per date (clean state) ──
        clock = RealTimeClock()
        db = DatabaseManager()
        handler = ExecutionHandler(
            db_manager=db,
            clock=clock,
            broker=PaperBroker(clock),
            config=ExecutionConfig(mode=ExecutionMode.PAPER),
            load_db_state=False,
            initial_capital=10_000_000.0,
        )

        init_pos = len(handler.position_tracker.get_all_positions())

        # ── Build hook and drive __call__() ──
        hook = CarryRebalancerHook(
            facts_db_path=str(FACTS_DB),
            execution_handler=handler,
            gross_exposure_policy=paper_gross_exposure_policy,
            bhavcopy_db_path=str(BHAVCOPY_DB),
        )

        ts = datetime.combine(fdate_clean, time(15, 30))
        fired = hook(ts, handler)

        # ── Collect results ──
        positions = handler.position_tracker.get_all_positions()
        longs = {s: p for s, p in positions.items() if p.side == PositionSide.LONG}
        shorts = {s: p for s, p in positions.items() if p.side == PositionSide.SHORT}
        long_cap = sum(p.quantity * p.avg_price for p in longs.values())
        short_cap = sum(p.quantity * p.avg_price for p in shorts.values())
        n_pos = len(positions)

        # Dedup check
        fired2 = hook(ts, handler)
        positions2 = handler.position_tracker.get_all_positions()
        dedup_ok = not fired2 and len(positions2) == n_pos

        results.append({
            "fdate": str(fdate_clean),
            "fired": fired,
            "fired2": fired2,
            "n_long": len(longs),
            "n_short": len(shorts),
            "long_cap": long_cap,
            "short_cap": short_cap,
            "gross": long_cap + short_cap,
            "target_gross": PAPER_GROSS,
            "init_pos": init_pos,
            "final_pos": n_pos,
            "dedup_ok": dedup_ok,
            "longs_sample": sorted(longs)[:3],
            "shorts_sample": sorted(shorts)[:3],
        })
        print(f"  {fdate_clean}: {n_pos} positions ({len(longs)}L/{len(shorts)}S) "
              f"gross=Rs {long_cap+short_cap:,.0f}  dedup={'OK' if dedup_ok else 'FAIL'}")

    # ── Generate report ──
    lines = []
    a = lines.append

    a("# Carry — Integration Smoke Test Report\n")
    a(f"**Script-generated** — `scripts/carry_integration_check.py`. "
      f"Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a("**Purpose:** verify that `CarryRebalancerHook.__call__()` drives the full "
      "production chain end-to-end — margin check, target-book construction, "
      "delta execution, fill placement — against real `facts.duckdb` data.\n")
    a("")

    a("---\n")
    a("## 1. Setup\n")
    a(f"- **Facts DB:** `{FACTS_DB}`\n")
    a(f"- **Bhavcopy DB:** `{BHAVCOPY_DB}`\n")
    a(f"- **Handler mode:** `ExecutionMode.PAPER`, `PaperBroker`\n")
    a(f"- **Initial capital:** Rs 1 Cr (`initial_capital=10_000_000.0`)\n")
    a(f"- **Gross-exposure policy:** `paper_gross_exposure_policy` → Rs 1 Cr fixed\n")
    a(f"- **ADV capping:** enabled (`bhavcopy_db_path` provided)\n")
    a(f"- **Margin check:** active (flat-rate 20%, 80% utilisation cap)\n")
    a(f"- **Slippage:** 5bp/side injected via `_build_fill`\n")
    a("")

    a("---\n")
    a("## 2. Per-Date Results\n")
    a("")
    a("| Formation Date | Fired | Longs | Shorts | Gross (Rs Cr) | Target | "
      "Dedup |")
    a("|---|:--:|--:|--:|--:|--:|:--:|")
    for r in results:
        a(f"| {r['fdate']} | {'PASS' if r['fired'] else 'FAIL'} | "
          f"{r['n_long']} | {r['n_short']} | "
          f"{r['gross']/1e7:.2f} | {r['target_gross']/1e7:.2f} | "
          f"{'PASS' if r['dedup_ok'] else 'FAIL'} |")
    a("")

    a("---\n")
    a("## 3. Detail (per-formation samples)\n")
    a("")
    for r in results:
        a(f"### {r['fdate']}\n")
        a(f"- **Fired:** {r['fired']}\n")
        a(f"- **Positions:** {r['n_long']} long + {r['n_short']} short = "
          f"{r['final_pos']} total (from {r['init_pos']} initially)\n")
        a(f"- **Gross exposure:** Rs {r['gross']:,.0f} "
          f"(target: Rs {r['target_gross']:,.0f})\n")
        a(f"- **Dedup:** second call returned `{r['fired2']}` "
          f"({'positions unchanged' if r['dedup_ok'] else 'BUG: positions modified'})\n")
        a(f"- **Longs (sample):** {', '.join(r['longs_sample'][:5])}\n")
        a(f"- **Shorts (sample):** {', '.join(r['shorts_sample'][:5])}\n")
        a("")

    # ── Gate ──
    all_ok = all(
        r['fired'] and r['n_long'] > 0 and r['n_short'] > 0
        and abs(r['gross'] - r['target_gross']) / r['target_gross'] < 0.05
        and r['dedup_ok']
        for r in results
    )

    a("---\n")
    a("## 4. Verdict\n")
    if all_ok:
        a("**PASS** — `CarryRebalancerHook` fires on formation dates, margin "
          "check clears, target book constructed, fills placed in "
          "`position_tracker`, gross exposure matches target. Dedup prevents "
          "double-execution on same date. Full production chain verified "
          "end-to-end.\n")
    else:
        a("**FAIL** — one or more checks did not pass. See per-date detail "
          "above.\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")

    print(f"\nReport: {REPORT}")
    print(f"Verdict: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
