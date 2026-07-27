"""TS Basis Daily — Drawdown / Regime Profile.

Mirror of TS Basis run_drawdown.py for daily cadence.
Annualization: 252 trading days/year.

Output: docs/reports/TS_BASIS_DAILY_DRAWDOWN_REPORT.md
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

from core.execution.futures.futures_fees import futures_fees as _calc_fees

SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "TS_BASIS_DAILY_DRAWDOWN_REPORT.md"

WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}

GROSS = 10_000_000.0; HALF = GROSS / 2.0
QF = 0.20; ADV_CAP_FRAC = 0.10; BAND = 0.25; SLIP = 5
PPY = 252.0


def main():
    from scripts.signal_engine.ts_basis_daily.run_net_spread import _simulate
    commit = __import__('subprocess').check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()

    con = duckdb.connect()
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute("SET threads=4")

    lines = []
    a = lines.append
    a("# TS Basis Daily — Drawdown / Regime Profile\n")
    a(f"**Script-generated.** Code commit `{commit}`.\n")
    a(f"**Cadence:** daily ({PPY:.0f} formations/year).\n")
    a(f"**Generated:** {date.today().isoformat()}\n")
    a("")

    for label, (lo, hi) in WINDOWS.items():
        print(f"  {label}...")
        r = _simulate(label, lo, hi, con)

        net = r.get("net_spreads", [])
        if not net or "error" in r:
            a(f"## {label}: ERROR\n")
            continue

        nets = np.array(net)
        eq = np.cumprod(1 + nets)
        peak = np.maximum.accumulate(eq)
        dd = (eq - peak) / peak
        max_dd = float(np.min(dd))
        worst = float(np.min(nets))
        best = float(np.max(nets))
        sharpe = float(np.mean(nets) / np.std(nets, ddof=1) * np.sqrt(PPY)) if len(nets) > 1 and np.std(nets, ddof=1) > 0 else 0
        pos_pct = float(np.mean(nets > 0)) * 100

        a(f"## {label} ({len(nets)} days)\n")
        a(f"| Metric | Value |")
        a(f"|---|--:|")
        a(f"| Annualized net | {r['ann_net']*100:+.2f}% |")
        a(f"| Worst day | {worst*100:+.2f}% |")
        a(f"| Best day | {best*100:+.2f}% |")
        a(f"| Max drawdown | {max_dd*100:+.2f}% |")
        a(f"| Daily std | {np.std(nets, ddof=1)*100:.2f}% |")
        a(f"| Sharpe (ann) | {sharpe:.2f} |")
        a(f"| % positive | {pos_pct:.0f}% |")
        a(f"| Avg turnover | {r['avg_turnover']:.3f} |")
        a(f"| Fee drag | {r['fee_drag_bp']:.0f} bp |")
        a("")

        pcts = [10, 25, 50, 75, 90]
        vals = np.percentile(nets, pcts) * 100
        a(f"**Percentiles:** p10={vals[0]:+.2f}% p25={vals[1]:+.2f}% p50={vals[2]:+.2f}% p75={vals[3]:+.2f}% p90={vals[4]:+.2f}%\n")
        a("")

    con.close()

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"Report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
