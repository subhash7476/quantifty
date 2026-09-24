"""Clear `is_synthetic` on rows that cannot be CAS carry-forward bars.

`is_synthetic` has exactly one meaning in this store — a stale-LTP artifact of
the CAS cash halt — and exactly one definition of it:
`db_tick_aggregator.is_carry_forward()`. That predicate is **imported here, not
restated**, so this script cannot drift from the flag's meaning.

548 equity rows fail it: MOTHERSON and CHOLAFIN on 2026-03-02 (205) and
2026-03-04 (343), stamped 09:15 onward on **pre-CAS** sessions with **volume on
every one**. No writer in the repo can produce that — the aggregator refuses
pre-CAS dates and non-zero volume, the historical fetcher writes FALSE, and the
marker refuses pre-CAS sessions. The likeliest path is
`migrate_monolith_to_isolated.py`, which copies the column through from the
pre-migration store, which means the provenance is not recoverable.

Operator ruling 2026-09-13: clear them. The risk stated at the time and
accepted: if the flag was recording something true about those bars (that they
were reconstructed rather than tick-aggregated), clearing it loses that warning.
The baselines below are what makes the decision reversible.

Copy-first: each file is copied to data/_baselines/1m_pre_false_synthetic_clear/
before the update, and an existing baseline is never overwritten.

  python scripts/cas/clear_false_synthetic.py              # plan only
  python scripts/cas/clear_false_synthetic.py --apply
  python scripts/cas/clear_false_synthetic.py --symbols all    # include MCX_FO
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.database.ingestors.db_tick_aggregator import is_carry_forward  # noqa: E402
from scripts.cas.fo_1m_coverage import CANDLES_1M_DIR  # noqa: E402

BASELINE_DIR = ROOT / "data" / "_baselines" / "1m_pre_false_synthetic_clear"

SYMBOL_FILTERS = {"eq": "symbol LIKE 'NSE_EQ|%'", "all": "TRUE"}


def false_marks(path: Path, where: str) -> list[tuple[str, object]]:
    """(symbol, timestamp) of every marked row the definition rejects."""
    con = duckdb.connect(str(path), read_only=True)
    try:
        rows = con.execute(
            f"SELECT symbol, timestamp, open, high, low, close, volume "
            f"FROM candles WHERE is_synthetic AND {where}").fetchall()
    finally:
        con.close()
    return [(r[0], r[1]) for r in rows
            if not is_carry_forward(r[0], r[1], r[2], r[3], r[4], r[5], r[6])]


def _baseline(path: Path) -> None:
    dst = BASELINE_DIR / path.name
    if dst.exists():
        return
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)
    if dst.stat().st_size != path.stat().st_size:
        raise RuntimeError(f"baseline {dst} does not match {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="clear (baselines first)")
    parser.add_argument("--symbols", choices=sorted(SYMBOL_FILTERS), default="eq")
    parser.add_argument("--from", dest="from_date", default="2023-01-02")
    args = parser.parse_args()

    where = SYMBOL_FILTERS[args.symbols]
    lo = date.fromisoformat(args.from_date)
    plan = {}
    for path in sorted(CANDLES_1M_DIR.glob("*.duckdb")):
        if date.fromisoformat(path.stem) < lo:
            continue
        bad = false_marks(path, where)
        if bad:
            plan[path] = bad

    total = sum(len(v) for v in plan.values())
    print(f"{len(plan)} files carry {total:,} rows marked synthetic that "
          f"is_carry_forward() rejects")
    for path, bad in plan.items():
        symbols = sorted({s for s, _ in bad})
        print(f"  {path.stem}: {len(bad):,} rows, {len(symbols)} symbols "
              f"({', '.join(symbols[:4])}{'...' if len(symbols) > 4 else ''})")
    if not args.apply or not plan:
        return 0

    cleared = 0
    for path, bad in plan.items():
        _baseline(path)
        con = duckdb.connect(str(path))
        try:
            con.executemany(
                "UPDATE candles SET is_synthetic = FALSE WHERE symbol = ? AND timestamp = ?", bad)
        finally:
            con.close()
        # Verified only after the writer is closed: DuckDB refuses a read-only
        # connection to a file another connection already holds read-write.
        left = len(false_marks(path, where))
        if left:
            raise RuntimeError(f"{path.stem}: {left} false marks survived the update")
        cleared += len(bad)
    print(f"cleared {cleared:,} false synthetic marks across {len(plan)} files")

    remaining = sum(len(false_marks(p, where)) for p in plan)
    print(f"after: {remaining} false marks remain")
    return 1 if remaining else 0


if __name__ == "__main__":
    raise SystemExit(main())
