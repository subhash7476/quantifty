"""Purge synthetic spot=100 rows from the Options-Wall results DB.

A test-isolation defect (fixed) let `WallPoller._poll_cycle` write a synthetic
spot=100 chain into the live `session_regime` when the suite ran. These rows show
on the dashboard as "spot 100.00 / Neutral / everything --". This removes them.

Safety:
  * Refuses to run while the poller holds the store (single-writer discipline) —
    checks the PID lock and aborts if a poller is alive. Stop the poller first.
  * Copy-first: snapshots the DB file next to itself before any DELETE.
  * Only deletes rows with underlying_ltp = 100.0 (the unambiguous synthetic
    marker — no real index prints 100).

    python scripts/options_wall/purge_synthetic_rows.py [--yes]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import duckdb  # noqa: E402

from core.options_wall import persistence as pers  # noqa: E402
from core.options_wall.poller import _pid_alive  # noqa: E402

PID_PATH = Path("data/options/wall_poller.pid")


def _poller_alive() -> bool:
    if not PID_PATH.exists():
        return False
    try:
        return _pid_alive(int(PID_PATH.read_text(encoding="utf-8").strip()))
    except (ValueError, OSError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = ap.parse_args()
    db = pers.WALL_RESULTS_DB

    if not db.exists():
        print(f"no results DB at {db}")
        return 0
    if _poller_alive():
        print("ABORT: the wall poller is running (PID lock alive). Stop it first — "
              "the poller is the results DB's sole writer.")
        return 1

    conn = duckdb.connect(str(db), read_only=True)
    n = conn.execute("SELECT count(*) FROM session_regime "
                     "WHERE underlying_ltp = 100.0").fetchone()[0]
    conn.close()
    if not n:
        print("no synthetic spot=100 rows found — nothing to purge")
        return 0
    print(f"found {n} synthetic spot=100 row(s) in session_regime")
    if not args.yes and input("delete them? [y/N] ").strip().lower() != "y":
        print("aborted")
        return 1

    backup = db.with_name(f"{db.stem}.pre_purge_{datetime.now():%Y%m%d_%H%M%S}.duckdb")
    shutil.copy2(db, backup)
    print(f"copy-first snapshot: {backup}")

    conn = duckdb.connect(str(db))
    try:
        conn.execute("DELETE FROM session_regime WHERE underlying_ltp = 100.0")
        conn.commit()
    finally:
        conn.close()
    print(f"deleted {n} synthetic row(s). Restart the poller to resume writing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
