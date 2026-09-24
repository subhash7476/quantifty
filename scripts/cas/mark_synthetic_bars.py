"""Populate `is_synthetic` for CAS auction-window carry-forward bars.

Since 2026-08-03 the Upstox feed keeps broadcasting a stale LTP (with
last-traded-quantity 0) through the 15:15-15:30 cash halt for Category I stocks.
DBTickAggregator faithfully bars those ticks, producing O=H=L=C, volume=0 rows
that look exactly like real data. The `is_synthetic` column already exists in
the per-day store and was uniformly FALSE — the flag was lying, not missing.

A bar is synthetic when, on a post-CAS session for a Category I symbol, it sits
in the auction window with zero volume, zero range, and a close identical to the
15:14 close. The auction print itself carries the whole auction volume and is
never marked.

EQUITIES ONLY. The predicate discriminates on volume == 0, and NSE_INDEX symbols
carry volume 0 on every bar of every session — applying it to an index would mark
that index's real closing value as fabricated (Nifty 50's 24614.90 on 2026-08-04
sits at 15:29 as a flat, zero-volume bar).

Copy-first: --apply snapshots each file before mutating it.
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

from core.market.session_schedule import CAS_EFFECTIVE, session_window  # noqa: E402
NATIVE_1M_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
CATEGORY_DB = ROOT / "data" / "cas" / "cas_category.duckdb"
MASTER_DB = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"

CAS_MARKABLE_PREFIX = "NSE_EQ|"

# The 15:14 close per symbol is materialised into a temp table first. A
# correlated subquery against the UPDATE's own target table is ambiguous in
# DuckDB; a join against a precomputed anchor is unambiguous and faster.
_ANCHOR_SQL = """
CREATE TEMP TABLE anchor AS
SELECT symbol, close AS anchor_close FROM candles
WHERE hour(timestamp) * 60 + minute(timestamp) = ?
"""

_MARK_SQL = """
UPDATE candles SET is_synthetic = TRUE
WHERE symbol IN (SELECT symbol FROM cat1)
  AND volume = 0
  AND open = high AND high = low AND low = close
  AND (hour(timestamp) * 60 + minute(timestamp)) >= ?
  AND (hour(timestamp) * 60 + minute(timestamp)) < ?
  AND close IN (
      SELECT anchor_close FROM anchor WHERE anchor.symbol = candles.symbol
  )
"""


def mark_file(path: Path, session: date, cat1_symbols: set) -> int:
    """Flag carry-forward bars in one per-day file. Returns rows flagged.

    EQUITIES ONLY — index symbols are filtered out here even if a caller
    passes them in.
    """
    if session < CAS_EFFECTIVE:
        return 0
    cat1_symbols = {s for s in cat1_symbols if s.startswith(CAS_MARKABLE_PREFIX)}
    auction = session_window("cash_auction", session)
    if auction is None or not cat1_symbols:
        return 0

    start_min = auction[0].hour * 60 + auction[0].minute
    end_min = auction[1].hour * 60 + auction[1].minute
    last_continuous_min = start_min - 1

    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE TEMP TABLE cat1 (symbol VARCHAR)")
        con.executemany("INSERT INTO cat1 VALUES (?)", [(s,) for s in cat1_symbols])
        con.execute(_ANCHOR_SQL, [last_continuous_min])
        before = con.execute(
            "SELECT count(*) FROM candles WHERE is_synthetic"
        ).fetchone()[0]
        con.execute(_MARK_SQL, [start_min, end_min])
        after = con.execute(
            "SELECT count(*) FROM candles WHERE is_synthetic"
        ).fetchone()[0]
    finally:
        con.close()
    return after - before


def cat1_isin_symbols(session: date) -> set:
    """Category I membership on `session`, as NSE_EQ|<isin> store symbols."""
    master = duckdb.connect(str(MASTER_DB), read_only=True)
    try:
        ticker_to_isin = dict(
            master.execute(
                "SELECT DISTINCT tradingsymbol, isin FROM instruments "
                "WHERE isin IS NOT NULL AND isin <> ''"
            ).fetchall()
        )
    finally:
        master.close()

    cat = duckdb.connect(str(CATEGORY_DB), read_only=True)
    try:
        tickers = {
            r[0]
            for r in cat.execute(
                "SELECT symbol FROM cas_category "
                "WHERE effective_from <= ? AND effective_to >= ?",
                [session, session],
            ).fetchall()
        }
    finally:
        cat.close()

    isins = {
        isin
        for ticker, isin in ticker_to_isin.items()
        if ticker.replace("-EQ", "") in tickers
    }
    return {f"{CAS_MARKABLE_PREFIX}{i}" for i in isins}


def run(apply: bool, since: date | None = None) -> dict:
    """Mark every post-CAS session, or only those on/after `since`.

    `since` exists so a newly-ingested tail can be marked without re-entering
    files that were marked in an earlier run.
    """
    floor = CAS_EFFECTIVE if since is None else max(CAS_EFFECTIVE, since)
    total = 0
    touched = 0
    for path in sorted(NATIVE_1M_DIR.glob("*.duckdb")):
        session = date.fromisoformat(path.stem)
        if session < floor:
            continue
        symbols = cat1_isin_symbols(session)
        if not symbols:
            raise RuntimeError(
                f"no Cat-I symbols resolved for {session} — build the category "
                f"table first (scripts/cas/build_cas_category.py)")
        if apply:
            # An existing snapshot is never overwritten: its whole value is
            # that it predates the FIRST mark. A re-run (after a backfill
            # re-ingests a marked session, say) would otherwise replace the
            # pre-mark baseline with an already-marked copy, and the original
            # state would be unrecoverable.
            snapshot = path.with_suffix(".duckdb.pre_cas_mark")
            if not snapshot.exists():
                shutil.copy2(path, snapshot)
            total += mark_file(path, session, symbols)
        touched += 1
    return {"sessions": touched, "bars_flagged": total}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="mutate the store (snapshots each file first)")
    parser.add_argument("--since", type=date.fromisoformat, default=None,
                        help="only sessions on/after this date (default: all post-CAS)")
    args = parser.parse_args()
    print(run(args.apply, args.since))
