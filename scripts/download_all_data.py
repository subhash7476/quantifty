"""Download all NSE bhavcopy data required for strategies.

Fetches from NSE public archives. By default runs INCREMENTALLY: each bhavcopy
ingest is started at (latest date already stored − LOOKBACK_DAYS), so a daily
run only visits the last few sessions instead of walking every date since 2016.
The lookback re-checks a small trailing window so a late-published or revised
bhavcopy, or a previously failed partial run, self-heals.

Use --full to force full-history ingest (first-time bootstrap, or to re-probe
stale trading-calendar days — see the unresolved-days notice below).

Usage:
  python scripts/download_all_data.py               # incremental download + build + refresh
  python scripts/download_all_data.py --full        # full-history download (bootstrap / repair)
  python scripts/download_all_data.py --download-only
  python scripts/download_all_data.py --build-only
  python scripts/download_all_data.py --lookback 3  # override trailing re-check window

Pipeline:
  1. Equity bhavcopy     → data/market_data/equity_bhavcopy.duckdb
  2. Futures bhavcopy    → data/market_data/futures_bhavcopy.duckdb
  3. Index history (1d)  → data/market_data/nse/candles/1d/{date}.duckdb
  4. Corporate actions   → equity_bhavcopy.duckdb (adds adjusted view)
  5. Stock options       → data/market_data/stock_options_bhavcopy.duckdb
  6. Build Nifty 50 DB   → data/signal_engine/carry/nifty50.duckdb
  7. Build continuous    → data/signal_engine/trend/continuous.duckdb
  8. Refresh strategies  → carry + ts_basis + ts_basis_daily signals
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data" / "market_data"

LOOKBACK_DAYS = 7  # trailing window re-checked each incremental run (self-heals gaps)

EQUITY_DB = DATA / "equity_bhavcopy.duckdb"
FUTURES_DB = DATA / "futures_bhavcopy.duckdb"
STOCK_OPT_DB = DATA / "stock_options_bhavcopy.duckdb"
INDEX_1D_DIR = DATA / "nse" / "candles" / "1d"


def _max_trade_date(db_path: Path, table: str):
    """Latest trade_date stored, or None if the DB/table is absent or empty."""
    if not db_path.exists():
        return None
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        names = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if table not in names:
            return None
        return con.execute(f"SELECT MAX(trade_date) FROM {table}").fetchone()[0]
    finally:
        con.close()


def _incremental_start(db_path: Path, table: str, lookback: int):
    """(start_date, is_incremental). None start → let the ingest script use its
    own full-history default (empty/absent store → bootstrap)."""
    latest = _max_trade_date(db_path, table)
    if latest is None:
        return None, False
    return latest - timedelta(days=lookback), True


def _max_index_date():
    """Latest 1d index file date (from filenames), or None."""
    if not INDEX_1D_DIR.exists():
        return None
    stems = [f.stem for f in INDEX_1D_DIR.glob("*.duckdb")]
    return max((date.fromisoformat(s) for s in stems), default=None)


def _warn_unresolved_calendar(start):
    """Non-silent notice: trading-calendar days marked 'unresolved' that fall
    before the incremental window will not be re-probed this run. --full does."""
    if not EQUITY_DB.exists():
        return
    con = duckdb.connect(str(EQUITY_DB), read_only=True)
    try:
        names = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if "trading_calendar" not in names:
            return
        n, mn = con.execute(
            "SELECT COUNT(*), MIN(trade_date) FROM trading_calendar "
            "WHERE source='unresolved' AND trade_date < ?", [start]).fetchone()
    finally:
        con.close()
    if n:
        print(f"  NOTE: {n} unresolved trading-calendar day(s) before {start} "
              f"(earliest {mn}) are outside the incremental window and will NOT be "
              f"re-probed. Run with --full to re-adjudicate them.")


def _run(script_path, args=None, label="", timeout=None):
    name = script_path.name
    print(f"\n  [{label}] {name}...")
    t0 = time.time()
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend([str(a) for a in args])
    try:
        result = subprocess.run(cmd, cwd=str(ROOT), timeout=timeout)
        elapsed = time.time() - t0
        ok = result.returncode == 0
        status = "OK" if ok else f"FAILED (exit {result.returncode})"
        print(f"  [{label}] {status} ({elapsed:.0f}s)")
        return ok
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        print(f"  [{label}] TIMEOUT after {elapsed:.0f}s")
        return False


def download_data(full: bool, lookback: int):
    """Download bhavcopy. Incremental by default — each ingest is started at
    (latest stored date − lookback). --full lets each script use its own
    full-history default (skipping already-present dates)."""
    all_ok = True
    # End at TODAY, not the ingest scripts' today-1 default, so the current
    # session's EOD bhavcopy (published after market close) is fetched. If run
    # before publication, today simply 404s / is absent — handled gracefully.
    end_iso = date.today().isoformat()

    def _start(db, table):
        if full:
            return None
        start, incr = _incremental_start(db, table, lookback)
        return start if incr else None

    # 1. Equity bhavcopy (argparse: --start / --end; default full start: 2010-01-01)
    eq_start = _start(EQUITY_DB, "equity_bhavcopy")
    if eq_start is not None:
        _warn_unresolved_calendar(eq_start)
    eq_args = ["--start", eq_start.isoformat()] if eq_start else []
    eq_args += ["--end", end_iso]
    if not _run(SCRIPTS / "csmp" / "ingest_equity_bhavcopy.py", args=eq_args,
                label="equity-bhavcopy", timeout=1200):
        all_ok = False

    # 2. Futures bhavcopy (positional: start end; default full start: 2016-02-11)
    fut_start = _start(FUTURES_DB, "futures_bhavcopy")
    fut_args = [fut_start.isoformat(), end_iso] if fut_start else None
    if not _run(SCRIPTS / "sfb" / "ingest_futures_bhavcopy_v2.py", args=fut_args,
                label="futures-bhavcopy", timeout=1200):
        all_ok = False

    # 3. Index history for Nifty 50 (--since narrows the floor→today file scan)
    idx_max = None if full else _max_index_date()
    idx_args = ["--since", (idx_max - timedelta(days=lookback)).isoformat()] if idx_max else None
    if not _run(SCRIPTS / "ingest_index_history.py", args=idx_args,
                label="index-history", timeout=1200):
        all_ok = False

    # 4. Corporate actions (eq bhavcopy → adjusted view; view is whole-panel, always full)
    if not _run(SCRIPTS / "csmp" / "ingest_corporate_actions.py",
                label="corp-actions", timeout=600):
        all_ok = False

    # 5. Stock options bhavcopy (positional: start end; default full start: 2016-02-11)
    opt_start = _start(STOCK_OPT_DB, "stock_options_bhavcopy")
    opt_args = [opt_start.isoformat(), end_iso] if opt_start else None
    if not _run(SCRIPTS / "sfb" / "ingest_stock_options_bhavcopy.py", args=opt_args,
                label="stock-options", timeout=1200):
        all_ok = False

    return all_ok


def build_derived():
    """Build derived datasets."""
    all_ok = True

    if not _run(SCRIPTS / "signal_engine" / "carry" / "build_index_db.py",
                label="build-nifty50", timeout=300):
        all_ok = False

    if not _run(SCRIPTS / "signal_engine" / "trend" / "build_continuous.py",
                label="build-continuous", timeout=600):
        all_ok = False

    return all_ok


def refresh_strategies():
    return _run(SCRIPTS / "refresh_all_strategies.py",
                label="refresh-strategies", timeout=3600)


def main():
    download_only = "--download-only" in sys.argv
    build_only = "--build-only" in sys.argv
    full = "--full" in sys.argv
    lookback = LOOKBACK_DAYS
    for i, a in enumerate(sys.argv):
        if a == "--lookback" and i + 1 < len(sys.argv):
            lookback = int(sys.argv[i + 1])

    print(f"Download all data — {date.today().isoformat()}")
    print(f"  Mode:     {'FULL history' if full else f'incremental (lookback {lookback}d)'}")
    print(f"  Download: {'yes' if not build_only else 'no'}")
    print(f"  Build:    {'yes' if not download_only else 'no'}")
    print()

    all_ok = True

    if not build_only:
        print("=" * 60)
        print("  STEP 1: Download bhavcopy from NSE archives")
        print("=" * 60)
        if not download_data(full, lookback):
            all_ok = False
            print("\n  WARNING: Some downloads failed. Continuing...")

    if not download_only:
        print("\n" + "=" * 60)
        print("  STEP 2: Build derived datasets")
        print("=" * 60)
        if not build_derived():
            all_ok = False

        print("\n" + "=" * 60)
        print("  STEP 3: Refresh strategy signals")
        print("=" * 60)
        if not refresh_strategies():
            all_ok = False

    print(f"\n{'='*60}")
    print(f"  {'ALL DONE' if all_ok else 'DONE WITH ERRORS'}")
    print(f"{'='*60}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
