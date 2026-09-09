"""Reclaim DuckDB storage bloat in the live trading stores.

Why this exists
---------------
Every write on these stores opens a connection and closes it, because a held
read-write DuckDB connection blocks other processes from opening the file even
read-only (verified on DuckDB 1.4.3 / Windows). Each close checkpoints the whole
table *including its indexes*, and the superseded blocks are not reused. Measured
on an isolated harness:

    indexed   + close-per-batch   1,000 checkpoints -> 265.56 MB
    indexed   + one held conn     1,000 checkpoints ->   1.32 MB
    unindexed + close-per-batch   1,000 checkpoints ->   1.32 MB

Both arms are needed to bloat. The code fixes remove the indexes from the hot
tables and cut the live-buffer flush rate, so new sessions stay flat. This script
reclaims what earlier sessions already wrote.

Method: build a fresh file with the current schema, INSERT ... SELECT every row,
verify the per-table counts match, then atomically swap. The original is renamed
aside as `<name>.pre_compact_<ts>.duckdb` rather than copied — a rename is
instant and needs no extra disk, and it is the copy-first baseline. Nothing is
deleted unless --discard-baseline is passed.

Usage:
    python scripts/ops/compact_duckdb_stores.py                  # report only
    python scripts/ops/compact_duckdb_stores.py --apply
    python scripts/ops/compact_duckdb_stores.py --apply --discard-baseline
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402

LIVE_BUFFER = ROOT / "data" / "live_buffer"
OPTIONS = ROOT / "data" / "options"
WALL_SNAPSHOTS = OPTIONS / "wall_chain_snapshots"

# PID files whose owning process must be dead before we touch anything. The
# stores are single-writer; compacting under a live writer would lose its writes.
PID_FILES = (OPTIONS / "wall_poller.pid", OPTIONS / "chain_poller.pid")


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if k32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return code.value == STILL_ACTIVE
            return False
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def live_writers() -> List[str]:
    """Names of writers still running. Checked immediately before every swap."""
    alive = []
    for pid_path in PID_FILES:
        if not pid_path.exists():
            continue
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            continue
        if _pid_alive(pid):
            alive.append(f"{pid_path.name} (pid {pid})")
    # the ingestor owns the live buffer but writes no pid file — look for it
    if os.name == "nt":
        import subprocess

        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" "
                 "| Select-Object -ExpandProperty CommandLine"],
                capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.SubprocessError):
            out = ""
        for marker in ("market_ingestor.py", "options_wall_poller.py",
                       "chain_poller.py", "orchestrator.py"):
            if marker in out:
                alive.append(f"running process: {marker}")
    return alive


def targets() -> List[Path]:
    found = [
        LIVE_BUFFER / "ticks_today.duckdb",
        LIVE_BUFFER / "candles_today.duckdb",
        OPTIONS / "wall_scan_results.duckdb",
    ]
    if WALL_SNAPSHOTS.is_dir():
        found.extend(sorted(WALL_SNAPSHOTS.glob("*.duckdb")))
    # never re-compact a baseline this script wrote — the glob would otherwise
    # pick up its own <name>.pre_compact_<ts>.duckdb on a second run
    return [p for p in found if p.exists() and ".pre_compact_" not in p.name]


def _tables(conn: duckdb.DuckDBPyConnection) -> List[str]:
    return [r[0] for r in conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' ORDER BY table_name").fetchall()]


def _apply_current_schema(conn: duckdb.DuckDBPyConnection, path: Path) -> bool:
    """Create the destination with the code's *current* schema where we own one.

    This is what drops the indexes the fix removed. Returns True when a schema
    was applied; False means fall back to CREATE TABLE AS SELECT (which carries
    no indexes either, just no constraints).
    """
    name = path.name
    if name == "ticks_today.duckdb":
        from core.database.schema import MARKET_TICKS_SCHEMA
        conn.execute(MARKET_TICKS_SCHEMA)
        return True
    if name == "candles_today.duckdb":
        from core.database.schema import MARKET_CANDLES_SCHEMA
        conn.execute(MARKET_CANDLES_SCHEMA)
        return True
    if name == "wall_scan_results.duckdb":
        from core.options_wall import persistence
        persistence.init_schema(conn)
        return True
    if path.parent == WALL_SNAPSHOTS:
        from core.data import options_wall_store
        options_wall_store.init_schema(conn)
        return True
    return False


def compact(path: Path, *, apply: bool, discard_baseline: bool) -> dict:
    before = path.stat().st_size
    src = duckdb.connect(str(path), read_only=True)
    try:
        tabs = _tables(src)
        counts = {t: src.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tabs}
    finally:
        src.close()

    tmp = path.with_suffix(".compact.tmp")
    for stale in (tmp, Path(str(tmp) + ".wal")):
        if stale.exists():
            stale.unlink()

    dst = duckdb.connect(str(tmp))
    try:
        seeded = _apply_current_schema(dst, path)
        # Column lists must be read before the ATTACH: the attached database
        # also exposes a schema called 'main', so information_schema would
        # return each column twice once both are visible.
        local_cols = {}
        if seeded:
            for t in _tables(dst):
                local_cols[t] = [r[1] for r in dst.execute(
                    f'PRAGMA table_info("{t}")').fetchall()]
        dst.execute(f"ATTACH '{path}' AS src (READ_ONLY)")
        for t in tabs:
            if t in local_cols:
                # A store written before a column existed (e.g. ticks.seq) is
                # narrower than the current schema; copy the intersection and
                # let the new column take its default.
                src_cols = {r[1] for r in dst.execute(f'PRAGMA table_info("src.{t}")').fetchall()}
                shared = [c for c in local_cols[t] if c in src_cols]
                sel = ", ".join(f'"{c}"' for c in shared)
                dst.execute(f'INSERT INTO "{t}" ({sel}) SELECT {sel} FROM src."{t}"')
            else:
                dst.execute(f'CREATE TABLE IF NOT EXISTS "{t}" AS SELECT * FROM src."{t}"')
        dst.execute("DETACH src")
        got = {t: dst.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tabs}
    finally:
        dst.close()

    mismatch = {t: (counts[t], got.get(t)) for t in tabs if counts[t] != got.get(t)}
    after = tmp.stat().st_size
    result = {"path": path, "before": before, "after": after,
              "rows": sum(counts.values()), "mismatch": mismatch, "applied": False}

    if mismatch or not apply:
        tmp.unlink(missing_ok=True)
        return result

    still = live_writers()
    if still:
        tmp.unlink(missing_ok=True)
        raise SystemExit("ABORT: a writer started mid-run — " + "; ".join(still))

    baseline = path.with_name(f"{path.stem}.pre_compact_{datetime.now():%Y%m%d_%H%M%S}.duckdb")
    os.replace(path, baseline)
    os.replace(tmp, path)
    result["applied"] = True
    result["baseline"] = baseline
    if discard_baseline:
        baseline.unlink()
        result["baseline"] = None
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="perform the swap (without this it only reports)")
    ap.add_argument("--discard-baseline", action="store_true",
                    help="delete the pre_compact baseline after a verified swap")
    args = ap.parse_args()

    alive = live_writers()
    if alive:
        print("ABORT: these stores are single-writer and a writer is running:")
        for a in alive:
            print(f"  - {a}")
        print("Stop the orchestrator/pollers first (PowerShell Stop-Process), then re-run.")
        return 1

    tot_before = tot_after = 0
    failures = 0
    for path in targets():
        r = compact(path, apply=args.apply, discard_baseline=args.discard_baseline)
        tot_before += r["before"]
        tot_after += r["after"]
        rel = r["path"].relative_to(ROOT)
        if r["mismatch"]:
            failures += 1
            print(f"SKIPPED {rel}: row-count mismatch {r['mismatch']} — left untouched")
            continue
        verb = "compacted" if r["applied"] else "would compact"
        print(f"{verb} {rel}: {r['before']/1e6:,.1f} MB -> {r['after']/1e6:,.1f} MB "
              f"({r['rows']:,} rows verified)")
        if r.get("baseline"):
            print(f"    baseline kept: {r['baseline'].name}")

    print(f"\nTotal: {tot_before/1e9:,.2f} GB -> {tot_after/1e9:,.2f} GB "
          f"(reclaims {(tot_before-tot_after)/1e9:,.2f} GB)")
    if not args.apply:
        print("Dry run — nothing changed. Re-run with --apply.")
    elif not args.discard_baseline:
        print("Baselines kept alongside each store; delete them once you are satisfied.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
