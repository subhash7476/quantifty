"""Download all NSE bhavcopy data required for strategies.

Fetches from NSE public archives. Idempotent — each ingest script
skips dates already present. First run downloads full history;
subsequent runs only fetch new dates.

Usage:
  python scripts/download_all_data.py               # download + build + refresh
  python scripts/download_all_data.py --download-only  # download only
  python scripts/download_all_data.py --build-only     # build + refresh only

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
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


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


def download_data():
    """Download all bhavcopy. No date args → each script uses its own
    default full-range, skipping already-present dates."""
    all_ok = True

    # 1. Equity bhavcopy (defaults: 2010-01-01 → yesterday)
    if not _run(SCRIPTS / "csmp" / "ingest_equity_bhavcopy.py",
                label="equity-bhavcopy", timeout=1200):
        all_ok = False

    # 2. Futures bhavcopy (defaults: 2016-02-11 → yesterday)
    if not _run(SCRIPTS / "sfb" / "ingest_futures_bhavcopy_v2.py",
                label="futures-bhavcopy", timeout=1200):
        all_ok = False

    # 3. Index history for Nifty 50 (defaults: 2012-02-21 → yesterday, skips existing)
    if not _run(SCRIPTS / "ingest_index_history.py",
                label="index-history", timeout=1200):
        all_ok = False

    # 4. Corporate actions (eq bhavcopy → adjusted view)
    if not _run(SCRIPTS / "csmp" / "ingest_corporate_actions.py",
                label="corp-actions", timeout=600):
        all_ok = False

    # 5. Stock options bhavcopy (defaults: 2016-02-11 → yesterday)
    if not _run(SCRIPTS / "sfb" / "ingest_stock_options_bhavcopy.py",
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

    print(f"Download all data — {date.today().isoformat()}")
    print(f"  Download: {'yes' if not build_only else 'no'}")
    print(f"  Build:    {'yes' if not download_only else 'no'}")
    print()

    all_ok = True

    if not build_only:
        print("=" * 60)
        print("  STEP 1: Download bhavcopy from NSE archives")
        print("=" * 60)
        if not download_data():
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
