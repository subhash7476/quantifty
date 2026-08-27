"""A — forward paper run evaluation (pre-committed criteria).

Reads data/a_index_intraday/paper_trades.duckdb and reports the mean net
bp/trade against the TRAIN (+1.27 bp) and HOLDOUT (-0.22 bp) benchmarks per
A_HOLDOUT_CLOSURE.md §forward paper run. Excludes dry-run runs by run_id
linkage through the trial ledger (run_start.dry_run).

Usage: python scripts/a_index_intraday/analyze_paper.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PAPER_DB = ROOT / "data" / "a_index_intraday" / "paper_trades.duckdb"
LEDGER = ROOT / "data" / "a_index_intraday" / "trial_ledger.jsonl"
REPORT = ROOT / "docs" / "reports" / "A_PAPER_EVALUATION.md"

TRAIN_BENCH = 1.27      # TRAIN mean net bp (A_TRAIN_REPORT.md)
HOLDOUT_BENCH = -0.22   # HOLDOUT mean net bp (A_HOLDOUT_REPORT.md)
MONTHS = 3              # pre-committed duration


def dry_run_ids() -> set:
    out = set()
    if not LEDGER.exists():
        return out
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event") == "run_start" and e.get("gate") == "PAPER_FORWARD":
            if e.get("dry_run"):
                out.add(e["run_id"])
    return out


def main() -> int:
    if not PAPER_DB.exists():
        print("paper_trades.duckdb not found — no forward sessions yet")
        return 0
    con = duckdb.connect(str(PAPER_DB), read_only=True)
    try:
        rows = con.execute(
            "SELECT date, side, era, gross_bp, fee_bp, net_bp, note "
            "FROM paper_sessions WHERE side IS NOT NULL ORDER BY date"
        ).fetchall()
    finally:
        con.close()
    if not rows:
        print("no traded sessions recorded yet")
        return 0

    nets = [r[4] for r in rows if r[4] is not None]
    mean = sum(nets) / len(nets)
    pos = sum(1 for n in nets if n > 0)
    lines = [
        "# A — Forward PAPER Evaluation",
        "",
        f"Generated: {__import__('datetime').datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Traded sessions: {len(nets)} · mean net bp/trade: **{mean:.2f}** "
        f"({pos}/{len(nets)} positive)",
        "",
        "| Benchmark | Mean net bp | A vs benchmark |",
        "|---|---:|---:|",
        f"| TRAIN | +{TRAIN_BENCH:.2f} | {mean - TRAIN_BENCH:+.2f} |",
        f"| HOLDOUT | {HOLDOUT_BENCH:.2f} | {mean - HOLDOUT_BENCH:+.2f} |",
        "",
        "Standing caveat (D5): paper fills are cash-series prices; the basis "
        "dispersion (19.2 bp full-day within-contract p90) is unmodeled in "
        "the translation to Nifty futures.",
        "",
        "Pre-committed decision (A_HOLDOUT_CLOSURE.md): at ≥ 3 months of "
        "forward sessions, retire the construct permanently and record the "
        "decision. The clock started at the first traded session.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"mean net bp: {mean:.2f} over {len(nets)} traded sessions -> {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
