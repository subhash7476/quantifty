"""Backfill 1m bars for F&O stocks missing from post-CAS per-day files.

TS Basis Daily prices post-CAS spot off each F&O name's continuous-session 1m close
(TS_BASIS_DAILY_SIGNAL_AUDIT_2026-09-11 F10). Each per-day file holds whatever
universe its writer used, so 3-26 F&O names per session were never stored.

Additive only: a name is fetched only over runs of consecutive sessions on which the
file has no row for it at all. The fetcher upserts and resets is_synthetic, so no
existing bar is ever re-fetched. Copy-first: each file is copied to
data/_baselines/1m_pre_fo_backfill/ before the fetch, and an existing baseline is never
overwritten. The CAS carry-forward marker then runs on the touched files, and the
script exits 1 if any F&O name still lacks a continuous-session close.

  python scripts/cas/backfill_fo_1m.py            # plan only
  python scripts/cas/backfill_fo_1m.py --apply
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.market.session_schedule import CAS_EFFECTIVE  # noqa: E402
from scripts.cas.fo_1m_coverage import CANDLES_1M_DIR, fo_equity_keys, load_continuous_closes  # noqa: E402
from scripts.cas.mark_synthetic_bars import cat1_isin_symbols, mark_file  # noqa: E402

FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
BASELINE_DIR = ROOT / "data" / "_baselines" / "1m_pre_fo_backfill"
FETCHER = ROOT / "scripts" / "fetch_upstox_historical.py"


def plan_runs(absent: dict[date, set[str]], sessions: list[date]) -> dict[tuple[date, date], list[str]]:
    """Group each key's absent sessions into consecutive runs: {(from, to): keys}."""
    index = {d: i for i, d in enumerate(sessions)}
    by_key: dict[str, list[date]] = {}
    for d, keys in absent.items():
        for k in keys:
            by_key.setdefault(k, []).append(d)
    runs: dict[tuple[date, date], list[str]] = {}
    for key, days in by_key.items():
        days.sort()
        start = prev = days[0]
        for d in days[1:] + [None]:
            if d is not None and index[d] == index[prev] + 1:
                prev = d
                continue
            runs.setdefault((start, prev), []).append(key)
            if d is not None:
                start = prev = d
    return {r: sorted(keys) for r, keys in sorted(runs.items())}


def coverage(sessions: list[date]) -> tuple[dict[date, set[str]], dict[date, list[str]], list[str]]:
    """(keys with no 1m row, names with rows but no continuous close, unmapped names) per session."""
    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
        con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
        load_continuous_closes(con, sessions, CANDLES_1M_DIR)
        present = {}
        for d, u, close in con.execute("SELECT trade_date, underlying, close FROM cont_close").fetchall():
            present.setdefault(d, {})[u] = close
        absent, no_close, unmapped = {}, {}, set()
        for d in sessions:
            keys, missing_isin = fo_equity_keys(con, d)
            unmapped.update(missing_isin)
            day = present.get(d, {})
            gone = {k for u, k in keys.items() if u not in day}
            if gone:
                absent[d] = gone
            stale = sorted(u for u, close in day.items() if close is None)
            if stale:
                no_close[d] = stale
        return absent, no_close, sorted(unmapped)
    finally:
        con.close()


def _baseline(d: date) -> None:
    src = CANDLES_1M_DIR / f"{d}.duckdb"
    dst = BASELINE_DIR / f"{d}.duckdb"
    if not src.exists() or dst.exists():
        return
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if dst.stat().st_size != src.stat().st_size:
        raise RuntimeError(f"baseline {dst} does not match {src}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="fetch, mark and verify (baselines first)")
    args = parser.parse_args()

    con = duckdb.connect(str(FUT_DB), read_only=True)
    sessions = [r[0] for r in con.execute(
        "SELECT DISTINCT trade_date FROM futures_bhavcopy WHERE inst_type = 'FUTSTK' "
        "AND trade_date >= ? AND trade_date < ? ORDER BY 1", [CAS_EFFECTIVE, date.today()]).fetchall()]
    con.close()

    absent, no_close, unmapped = coverage(sessions)
    runs = plan_runs(absent, sessions)
    print(f"{len(sessions)} post-CAS sessions {sessions[0]} -> {sessions[-1]}; "
          f"{sum(len(k) for k in absent.values())} absent (session, name) cells in {len(runs)} fetch runs")
    for (start, end), keys in runs.items():
        print(f"  {start} -> {end}: {len(keys)} keys")
    if unmapped:
        print(f"  no EQ ISIN in instrument_master (cannot fetch): {unmapped}")
    if not args.apply:
        return 0

    touched = sorted(absent)
    cat1 = {d: cat1_isin_symbols(d) for d in touched}
    uncategorised = [str(d) for d, symbols in cat1.items() if not symbols]
    if uncategorised:
        raise RuntimeError(f"no Category I symbols for {uncategorised} — backfilled bars would land unmarked; "
                           f"extend data/cas/cas_category.duckdb (scripts/cas/build_cas_category.py) first")
    for d in touched:
        _baseline(d)
    for (start, end), keys in runs.items():
        cmd = [sys.executable, str(FETCHER), "--instrument_key", ",".join(keys), "--unit", "minutes",
               "--interval", "1", "--from", start.isoformat(), "--to", end.isoformat(), "--no-intraday"]
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            raise RuntimeError(f"fetch failed for {start} -> {end}")
    flagged = sum(mark_file(CANDLES_1M_DIR / f"{d}.duckdb", d, cat1[d])
                  for d in touched if (CANDLES_1M_DIR / f"{d}.duckdb").exists())
    print(f"CAS marker: {flagged:,} carry-forward bars flagged on {len(touched)} files")

    absent, no_close, unmapped = coverage(sessions)
    for d, keys in absent.items():
        print(f"  STILL ABSENT {d}: {sorted(keys)}")
    for d, names in no_close.items():
        print(f"  NO CONTINUOUS CLOSE {d}: {names}")
    if unmapped:
        print(f"  UNMAPPED: {unmapped}")
    return 1 if absent or no_close or unmapped else 0


if __name__ == "__main__":
    raise SystemExit(main())
