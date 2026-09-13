"""Remove 1m rows stamped for a different session than the file they sit in.

A per-day file is addressed by its date: every reader takes `2026-02-25.duckdb`
to be the 2026-02-25 session. Three files break that — 2026-02-25 carries
12,221 rows stamped 2026-02-24, 2026-03-02 carries 11,436 stamped 2026-02-27,
2026-03-04 carries 13 stamped 2026-03-02 — so a reader that does not filter on
the date (and none should have to) mixes two sessions. It is the same ingest
misfiling that produced the 2026-03-03 orphan file and the post-close print
tails: a flush landing after the file rotated.

Deleting them loses nothing, and the script proves that per row before it
deletes. A misfiled row is removed only when EITHER

  - the correct file already carries that (symbol, timestamp) — every such row
    here is a second, poorer copy: of the 23,670 duplicated rows only 12,541
    agree with the good copy on close and volume, the rest being partial
    aggregates from a recovery pass; or
  - its stamp lies outside the correct session's own trading window, so it is
    a post-close print that would be junk in the right file too.

Anything else is REFUSED and reported, never deleted.

Copy-first: each file is copied to data/_baselines/1m_pre_misdated_prune/
before the delete, and an existing baseline is never overwritten.

  python scripts/cas/prune_misdated_bars.py            # plan only
  python scripts/cas/prune_misdated_bars.py --apply
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

from core.market.session_schedule import session_windows  # noqa: E402
from scripts.cas.fo_1m_coverage import CANDLES_1M_DIR  # noqa: E402

BASELINE_DIR = ROOT / "data" / "_baselines" / "1m_pre_misdated_prune"

# The widest cash window; a stamp outside it on the owning date is a print the
# session never had.
SEGMENT = "cash_cat2"


def _in_session(on: date) -> str:
    """SQL predicate: the stamp falls inside one of `on`'s trading windows."""
    windows = session_windows(SEGMENT, on)
    if not windows:
        return "FALSE"
    return " OR ".join(
        f"(CAST(timestamp AS TIME) >= TIME '{s}' AND CAST(timestamp AS TIME) < TIME '{e}')"
        for s, e in windows)


def survey(paths: list[Path]) -> list[dict]:
    out = []
    for path in paths:
        on = date.fromisoformat(path.stem)
        con = duckdb.connect(str(path), read_only=True)
        try:
            foreign = [r[0] for r in con.execute(
                "SELECT DISTINCT CAST(timestamp AS DATE) FROM candles "
                "WHERE CAST(timestamp AS DATE) <> ? ORDER BY 1", [on]).fetchall()]
            for owner in foreign:
                owner_path = CANDLES_1M_DIR / f"{owner}.duckdb"
                if not owner_path.exists():
                    out.append({"file": on, "owner": owner, "rows": 0, "removable": 0,
                                "note": "owning file does not exist"})
                    continue
                con.execute(f"ATTACH '{owner_path}' AS owner (READ_ONLY)")
                try:
                    rows, dup, outside = con.execute(f"""
                        SELECT count(*),
                               count(*) FILTER (WHERE EXISTS (
                                   SELECT 1 FROM owner.candles t
                                   WHERE t.symbol = m.symbol AND t.timestamp = m.timestamp)),
                               count(*) FILTER (WHERE NOT ({_in_session(owner)}))
                        FROM candles m WHERE CAST(m.timestamp AS DATE) = ?""",
                        [owner]).fetchone()
                    removable = con.execute(f"""
                        SELECT count(*) FROM candles m
                        WHERE CAST(m.timestamp AS DATE) = ?
                          AND (EXISTS (SELECT 1 FROM owner.candles t
                                       WHERE t.symbol = m.symbol AND t.timestamp = m.timestamp)
                               OR NOT ({_in_session(owner)}))""", [owner]).fetchone()[0]
                finally:
                    con.execute("DETACH owner")
                out.append({"file": on, "owner": owner, "rows": rows, "duplicate": dup,
                            "outside_window": outside, "removable": removable,
                            "refused": rows - removable})
        finally:
            con.close()
    return out


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
    parser.add_argument("--apply", action="store_true", help="delete (baselines first)")
    parser.add_argument("--from", dest="from_date", default="2023-01-02")
    args = parser.parse_args()

    lo = date.fromisoformat(args.from_date)
    paths = []
    for path in sorted(CANDLES_1M_DIR.glob("*.duckdb")):
        on = date.fromisoformat(path.stem)
        if on < lo:
            continue
        con = duckdb.connect(str(path), read_only=True)
        try:
            n = con.execute("SELECT count(*) FROM candles WHERE CAST(timestamp AS DATE) <> ?",
                            [on]).fetchone()[0]
        finally:
            con.close()
        if n:
            paths.append(path)

    plan = survey(paths)
    print(f"{len(paths)} files carry rows stamped for another date")
    for row in plan:
        print(f"  {row['file']}: {row['rows']:,} rows stamped {row['owner']}: "
              f"{row.get('duplicate', 0):,} already in that file, "
              f"{row.get('outside_window', 0):,} outside its session window, "
              f"REMOVABLE {row['removable']:,}, REFUSED {row.get('refused', 0):,}")
    if not args.apply or not plan:
        return 0

    total = 0
    for row in plan:
        if not row["removable"]:
            continue
        path = CANDLES_1M_DIR / f"{row['file']}.duckdb"
        owner_path = CANDLES_1M_DIR / f"{row['owner']}.duckdb"
        _baseline(path)
        con = duckdb.connect(str(path))
        try:
            con.execute(f"ATTACH '{owner_path}' AS owner (READ_ONLY)")
            con.execute(f"""
                DELETE FROM candles m
                WHERE CAST(m.timestamp AS DATE) = ?
                  AND (EXISTS (SELECT 1 FROM owner.candles t
                               WHERE t.symbol = m.symbol AND t.timestamp = m.timestamp)
                       OR NOT ({_in_session(row['owner'])}))""", [row["owner"]])
            left = con.execute("SELECT count(*) FROM candles WHERE CAST(timestamp AS DATE) = ?",
                               [row["owner"]]).fetchone()[0]
            con.execute("DETACH owner")
        finally:
            con.close()
        if left != row.get("refused", 0):
            raise RuntimeError(f"{row['file']}: {left} rows left, expected {row.get('refused', 0)}")
        total += row["removable"]
    print(f"pruned {total:,} misfiled rows")

    after = survey([p for p in paths])
    still = sum(r["rows"] for r in after)
    print(f"after: {still:,} misfiled rows remain across {len(after)} (file, owner) pairs")
    for row in after:
        print(f"  REMAINING {row['file']}: {row['rows']:,} stamped {row['owner']}")
    return 1 if still else 0


if __name__ == "__main__":
    raise SystemExit(main())
