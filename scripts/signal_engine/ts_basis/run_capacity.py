"""TS Basis — Capacity Analysis.

Same method as carry capacity_analysis.py: sweep AUM from 1 Cr to 100 Cr,
measure ADV cap incidence.

Output: docs/reports/TS_BASIS_CAPACITY_REPORT.md
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

SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis" / "ts_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "TS_BASIS_CAPACITY_REPORT.md"

WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}

GROSS_BASE = 10_000_000.0; HALF = GROSS_BASE / 2.0
QF = 0.20; ADV_CAP_FRAC = 0.10
MULTIPLIERS = [1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 75, 100]
ADV_W = 20; ADV_MIN = 10


def _load_adva(con, fdate, ulist):
    if not ulist: return {}
    ul = ", ".join(f"'{u}'" for u in ulist)
    rows = con.execute(f"""
        SELECT underlying, AVG(val_in_lakh) * 100000.0
        FROM (SELECT underlying, val_in_lakh, ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
              FROM fut.futures_bhavcopy WHERE trade_date <= DATE '{fdate}'
              AND trade_date > DATE '{fdate}' - INTERVAL '{ADV_W+10} days'
              AND underlying IN ({ul}) AND inst_type = 'FUTSTK')
        WHERE rn <= {ADV_W} AND val_in_lakh IS NOT NULL
        GROUP BY underlying HAVING COUNT(*) >= {ADV_MIN}
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def main():
    commit = __import__('subprocess').check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()

    con = duckdb.connect()
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute("SET threads=4")

    lines = []
    a = lines.append
    a("# TS Basis — Capacity Analysis\n")
    a(f"**Script-generated.** Code commit `{commit}`.\n")
    a(f"**Generated:** {date.today().isoformat()}\n")
    a("")

    a("| AUM (Cr) | TRAIN Long % | TRAIN Short % | HOLDOUT Long % | HOLDOUT Short % |")
    a("|---:|--:|--:|--:|--:|")

    results = {}
    for label, (lo, hi) in WINDOWS.items():
        facts_rows = con.execute(f"""
            SELECT formation_date, underlying, z_ts FROM sig.signals
            WHERE formation_date >= DATE '{lo}' AND formation_date <= DATE '{hi}'
            AND z_ts IS NOT NULL AND fwd_ret_1m IS NOT NULL AND liquid = TRUE
            ORDER BY formation_date, underlying
        """).fetchall()
        by_date = defaultdict(list)
        for fd, u, z in facts_rows:
            by_date[fd].append((u, float(z)))
        dates = sorted(by_date.keys())

        for mult in MULTIPLIERS:
            gross = GROSS_BASE * mult; hg = gross / 2.0
            capped = {"L": 0, "S": 0, "n": 0}
            for fd in dates:
                rows = by_date[fd]
                ulist = [r[0] for r in rows]
                adva = _load_adva(con, fd, ulist)
                filt = [(u, z) for u, z in rows if u in adva]
                n = len(filt)
                if n < 5: continue
                nq = max(1, round(QF * n))
                srt = sorted(filt, key=lambda r: r[1])
                longs = {r[0] for r in srt[-nq:]}
                shorts = {r[0] for r in srt[:nq]}
                for in_set, leg in [(longs, "L"), (shorts, "S")]:
                    n_leg = len(in_set)
                    if n_leg == 0: continue
                    cap_each = hg / n_leg
                    for u in in_set:
                        max_pos = adva.get(u, float('inf')) * ADV_CAP_FRAC
                        if min(cap_each, max_pos if max_pos > 0 else cap_each) < cap_each - 1:
                            capped[leg] += 1
                    capped["n"] += n_leg
            pc_long = capped["L"] / max(capped["n"] / 2, 1) * 100
            pc_short = capped["S"] / max(capped["n"] / 2, 1) * 100
            results.setdefault(label, {})[mult] = (pc_long, pc_short)

    for mult in MULTIPLIERS:
        t = results.get("TRAIN", {}).get(mult, (0, 0))
        h = results.get("HOLDOUT", {}).get(mult, (0, 0))
        a(f"| {mult} | {t[0]:.1f}% | {t[1]:.1f}% | {h[0]:.1f}% | {h[1]:.1f}% |")
    a("")

    con.close()

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"Report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
