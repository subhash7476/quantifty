"""Backfill 1m bars for Nifty 100 constituents missing from the per-day files.

Each per-day 1m file holds whatever universe its writer used, not a universe
(CLAUDE.md). Measured against PIT Nifty 100 membership rather than the F&O list,
a mean of 11 constituents per session are absent across 2023-2026 — DLF,
BRITANNIA, KOTAKBANK and BAJAJFINSV on 868 of 918 sessions — so a Nifty-100
cross-sectional study silently runs on ~89 names, the absences being large-cap
and systematic. This is the sibling of backfill_fo_1m.py, which asks the same
question of the F&O universe and therefore never sees these names.

Membership comes from data/isd/n100_membership.duckdb (NSE press releases gated
monthly against the MCWB archives), so the universe is independent of the candle
store it is used to audit.

Additive only: a name is fetched only over runs of consecutive sessions on which
the file has no row for it at all, so no existing bar is ever re-fetched.
Presence is tested against EVERY ISIN the repo knows for a symbol — a face-value
change re-issues the security under a new ISIN serial, and the store keeps bars
under whichever one was current — while the fetch uses instrument_master's
current ISIN, the key the ingest itself writes.

Copy-first: each file is copied to data/_baselines/1m_pre_n100_backfill/ before
the fetch, and an existing baseline is never overwritten.

The fetcher resets is_synthetic, so the CAS carry-forward marker is re-run on
every touched post-CAS session. A session whose Category I list is missing is
REFUSED rather than marked, because mark_file() returns 0 for an empty list and
an unmarked session is indistinguishable from a marked one — data/cas/
cas_category.duckdb currently ends 2026-08-28, so sessions after that are out of
reach until it is extended (PTMS gate C3).

  python scripts/cas/backfill_n100_1m.py            # plan only
  python scripts/cas/backfill_n100_1m.py --apply
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.market.session_schedule import CAS_EFFECTIVE  # noqa: E402
from scripts.cas.backfill_fo_1m import plan_runs  # noqa: E402
from scripts.cas.fo_1m_coverage import CANDLES_1M_DIR  # noqa: E402
from scripts.cas.mark_synthetic_bars import cat1_isin_symbols, mark_file  # noqa: E402

EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
N100_DB = ROOT / "data" / "isd" / "n100_membership.duckdb"
BASELINE_DIR = ROOT / "data" / "_baselines" / "1m_pre_n100_backfill"
FETCHER = ROOT / "scripts" / "fetch_upstox_historical.py"

# The per-day equity 1m store begins here; earlier files hold index series only.
DEFAULT_FROM = date(2023, 1, 2)


def load_isins() -> tuple[dict[str, set[str]], dict[str, str]]:
    """({symbol: every ISIN across its rename chain}, {symbol: the key to fetch}).

    An entity is not one symbol for all time and the 1m store keys a whole
    series under the ticker's *current* ISIN, so the era-correct label in the
    membership table does not resolve on its own: MCDOWELL-N's bars sit under
    UNITDSPR's INE854D01024 from 2023 on, and looking up only INE854D01016
    reports 354 sessions absent that were never missing. Walk symbol_changes
    (NSE's own record) to the terminal ticker, take every ISIN on the way for
    the presence test, and fetch under the terminal ticker's current ISIN.
    """
    con = duckdb.connect(str(EQ_DB), read_only=True)
    try:
        renames = dict(con.execute(
            "SELECT old_symbol, new_symbol FROM symbol_changes").fetchall())
        by_symbol: dict[str, set[str]] = defaultdict(set)
        for s, i in con.execute(
                "SELECT symbol, isin FROM instrument_master WHERE isin IS NOT NULL").fetchall():
            by_symbol[s].add(i)
        live = {s: i for s, i in con.execute(
            "SELECT symbol, isin FROM instrument_master "
            "WHERE isin IS NOT NULL AND series = 'EQ'").fetchall()}
        for s, i in con.execute(
                "SELECT symbol, isin FROM symbol_isin WHERE isin IS NOT NULL").fetchall():
            by_symbol[s].add(i)
    finally:
        con.close()

    def chain(sym: str) -> list[str]:
        out, seen = [sym], {sym}
        while sym in renames and renames[sym] not in seen:
            sym = renames[sym]
            seen.add(sym)
            out.append(sym)
        return out

    known: dict[str, set[str]] = {}
    current: dict[str, str] = {}
    for sym in set(by_symbol) | set(renames):
        era = chain(sym)
        isins = set().union(*(by_symbol.get(e, set()) for e in era))
        if isins:
            known[sym] = isins
        for terminal in reversed(era):
            if terminal in live:
                current[sym] = live[terminal]
                break
    return known, current


def load_membership() -> list[tuple[str, str, str | None]]:
    con = duckdb.connect(str(N100_DB), read_only=True)
    try:
        return [(s, str(vf), None if vt is None else str(vt)) for s, vf, vt in
                con.execute("SELECT symbol, valid_from, valid_to FROM n100_membership").fetchall()]
    finally:
        con.close()


def members_on(intervals, day: str) -> list[str]:
    return [s for s, vf, vt in intervals if vf <= day and (vt is None or vt > day)]


def coverage(sessions: list[date], intervals, known, current):
    """(absent keys per session, names with rows but no traded bar, unmapped names)."""
    absent: dict[date, set[str]] = {}
    untraded: dict[date, list[str]] = {}
    unmapped: set[str] = set()
    for d in sessions:
        path = CANDLES_1M_DIR / f"{d}.duckdb"
        if not path.exists():
            continue
        con = duckdb.connect(str(path), read_only=True)
        try:
            rows = con.execute(
                "SELECT symbol, sum(CASE WHEN volume > 0 THEN 1 ELSE 0 END) "
                "FROM candles WHERE symbol LIKE 'NSE_EQ|%' GROUP BY 1").fetchall()
        finally:
            con.close()
        traded = {k.split("|")[-1]: n for k, n in rows}
        gone, dead = set(), []
        for sym in members_on(intervals, str(d)):
            hit = known.get(sym, set()) & traded.keys()
            if not hit:
                key = current.get(sym)
                if key is None:
                    unmapped.add(sym)
                else:
                    gone.add(f"NSE_EQ|{key}")
            elif not any(traded[i] for i in hit):
                dead.append(sym)
        if gone:
            absent[d] = gone
        if dead:
            untraded[d] = sorted(dead)
    return absent, untraded, sorted(unmapped)


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
    parser.add_argument("--apply", action="store_true",
                        help="fetch, mark and verify (baselines first)")
    parser.add_argument("--from", dest="from_date", default=DEFAULT_FROM.isoformat())
    parser.add_argument("--to", dest="to_date", default=None)
    args = parser.parse_args()

    # A per-day file is not a session: 2026-03-03 is a holiday whose file holds
    # 197 rows stamped 2026-03-02 15:29-15:59, misfiled from the previous
    # close. Scanning files alone reports its members absent forever, with
    # nothing to fetch. The calendar is the authority on what a session is.
    files = {date.fromisoformat(p.stem) for p in CANDLES_1M_DIR.glob("*.duckdb")}
    con = duckdb.connect(str(EQ_DB), read_only=True)
    try:
        calendar = {r[0] for r in con.execute("SELECT trade_date FROM trading_calendar").fetchall()}
    finally:
        con.close()
    lo = date.fromisoformat(args.from_date)
    hi = date.fromisoformat(args.to_date) if args.to_date else max(files)
    sessions = sorted(d for d in files & calendar if lo <= d <= hi)
    orphans = sorted(d for d in files - calendar if lo <= d <= hi)
    if orphans:
        print(f"{len(orphans)} per-day files with no calendar session (skipped): {orphans}")

    # Post-CAS sessions with no Category I list cannot be marked, so their
    # backfilled carry-forward bars would read as real trades. Drop them here
    # rather than fetching and then failing.
    blocked = [d for d in sessions if d >= CAS_EFFECTIVE and not cat1_isin_symbols(d)]
    if blocked:
        sessions = [d for d in sessions if d not in set(blocked)]
        print(f"REFUSED {len(blocked)} post-CAS sessions with no Category I list "
              f"({blocked[0]} -> {blocked[-1]}): extend data/cas/cas_category.duckdb "
              f"(scripts/cas/build_cas_category.py) first - PTMS gate C3")

    intervals = load_membership()
    known, current = load_isins()
    absent, untraded, unmapped = coverage(sessions, intervals, known, current)
    runs = plan_runs(absent, sessions)
    cells = sum(len(v) for v in absent.values())
    print(f"{len(sessions)} sessions {sessions[0]} -> {sessions[-1]}; "
          f"{cells} absent (session, name) cells in {len(runs)} fetch runs")
    for (start, end), keys in list(runs.items())[:20]:
        print(f"  {start} -> {end}: {len(keys)} keys")
    if len(runs) > 20:
        print(f"  ... {len(runs) - 20} more runs")
    if untraded:
        print(f"  present but no traded bar on {len(untraded)} sessions "
              f"(reported, never fetched)")
    if unmapped:
        print(f"  no ISIN anywhere (cannot fetch): {unmapped}")
    if not args.apply:
        return 0

    touched = sorted(absent)
    for d in touched:
        _baseline(d)
    for (start, end), keys in runs.items():
        cmd = [sys.executable, str(FETCHER), "--instrument_key", ",".join(keys),
               "--unit", "minutes", "--interval", "1",
               "--from", start.isoformat(), "--to", end.isoformat(), "--no-intraday"]
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            raise RuntimeError(f"fetch failed for {start} -> {end}")

    post_cas = [d for d in touched if d >= CAS_EFFECTIVE]
    flagged = sum(mark_file(CANDLES_1M_DIR / f"{d}.duckdb", d, cat1_isin_symbols(d))
                  for d in post_cas if (CANDLES_1M_DIR / f"{d}.duckdb").exists())
    print(f"CAS marker: {flagged:,} carry-forward bars flagged on {len(post_cas)} post-CAS files")

    absent, untraded, unmapped = coverage(sessions, intervals, known, current)
    still = sum(len(v) for v in absent.values())
    print(f"after backfill: {still} absent cells on {len(absent)} sessions")
    for d in sorted(absent)[:20]:
        print(f"  STILL ABSENT {d}: {sorted(absent[d])}")
    return 1 if absent or unmapped else 0


if __name__ == "__main__":
    raise SystemExit(main())
