"""ISD Phase-1 store repair — remove zero-price NSE_EQ rows from the 1m tree.

G4 audit found exactly one row with o=h=l=c=0 (2023-11-12 19:01:00,
NSE_EQ|INE121A08PJ0, Diwali Muhurat session) — a placeholder/garbage print,
not a trade (no security trades at price zero). Phase-1 certification is
read-only, but the spec (§6) permits store mutation when the baseline copy is
taken FIRST and the mutation comes from committed, re-runnable code (the Gate-A
provenance lesson).

Discipline:
  1. dry-run by default; `--apply` mutates.
  2. baseline copy of every touched file to data/isd/baseline/ BEFORE deletion.
  3. deletion predicate = the G4 v2 predicate (any OHLC <= 0 or null); counts
     printed per file; a manifest jsonl records stem, baseline path, deleted.

Usage:
    python scripts/isd/repair_zero_rows.py            # dry-run census
    python scripts/isd/repair_zero_rows.py --apply    # baseline + delete
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.isd import (
    ISD_DATA_DIR, NATIVE_1M_DIR, SESSION_FIRST_MIN, connect_ro,
)

BASELINE_DIR = ISD_DATA_DIR / "baseline"
MANIFEST = ISD_DATA_DIR / "zero_row_repair_manifest.jsonl"

_PRED = ("open <= 0 or high <= 0 or low <= 0 or close <= 0 "
         "or open is null or high is null or low is null or close is null")


def _census() -> list:
    out = []
    for p in sorted(NATIVE_1M_DIR.glob("*.duckdb")):
        if p.stem < "2023-01-02":
            continue
        con = connect_ro(p)
        try:
            rows = con.execute(f"""
                select symbol, timestamp, open, high, low, close, volume
                from candles where symbol like 'NSE_EQ%' and ({_PRED})
                order by timestamp
            """).fetchall()
            n = len(rows)
        finally:
            con.close()
        if n:
            out.append({"file": p.name, "rows": rows, "count": n})
    return out


def run(apply: bool = False) -> dict:
    hits = _census()
    if not hits:
        return {"files_touched": 0, "rows_deleted": 0, "rows_flagged": 0,
                "baseline_dir": str(BASELINE_DIR), "rows": []}

    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = open(MANIFEST, "w", encoding="utf-8")
    total = 0
    files = []
    try:
        for hit in hits:
            src = NATIVE_1M_DIR / hit["file"]
            baseline = BASELINE_DIR / hit["file"]
            if not baseline.exists():
                shutil.copy2(src, baseline)
            if apply:
                import duckdb
                con = duckdb.connect(str(src))
                try:
                    con.execute(
                        f"delete from candles where symbol like 'NSE_EQ%' "
                        f"and ({_PRED})")
                finally:
                    con.close()
            total += hit["count"]
            files.append(hit["file"])
            manifest.write(json.dumps({
                "file": hit["file"], "baseline": str(baseline),
                "deleted": hit["count"] if apply else 0,
                "applied": bool(apply)}) + "\n")
    finally:
        manifest.close()

    return {
        "files_touched": len(files),
        "files": files,
        "rows_deleted": total if apply else 0,
        "rows_flagged": total,
        "baseline_dir": str(BASELINE_DIR),
        "rows": [r for hit in hits for r in hit["rows"]],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="take baselines and delete the flagged rows")
    args = parser.parse_args()
    res = run(apply=args.apply)
    print(json.dumps(res, indent=2, default=str))
    if not args.apply:
        print("\nDry-run: nothing mutated. Re-run with --apply to repair.")
