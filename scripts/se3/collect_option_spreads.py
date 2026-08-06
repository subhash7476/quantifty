"""SE-3 forward spread collection — the only route to an honest Indian
single-stock option spread distribution.

PRE-REG section 5.3 / section 9.2 (operator decision 2026-08-05: YES, starts
independently). Costs CANNOT be measured historically: stock_options_bhavcopy
carries no bid and no ask, and Cao & Han's cost result is a fraction of the
quoted spread. This collector accumulates LIVE bid/ask over time so the eventual
SE-3 cost gate has a real distribution to reference.

Properties:
  - Costs NO historical window. It reads only live quotes via Upstox.
  - NOT a dependency of the confirmatory run (Phase 1 / Phase 2). The D1 ladder
    remains an assumption regardless of when collection starts.
  - Value is a function of how long it has been running — run it on a schedule.
  - Append-only store: data/se3/spread_collection.duckdb
      spread_observations(trade_date, observed_at, underlying, expiry_dt,
                          option_type, strike, instrument_key, best_bid,
                          best_ask, ltp, oi, volume, spread_pct, screen,
                          screen_reason)
    PK (observed_at, instrument_key) — append-only per observation timestamp,
    never overwrite. A repeated run gets a fresh observed_at and INSERTS new
    rows, over-sampling that market moment into the distribution rather than
    deduping it — an accidental double-run is not harmless; run once per sweep.

Usage:
    python scripts/se3/collect_option_spreads.py --once         # one sweep, exit
    python scripts/se3/collect_option_spreads.py --sweeps 12    # 12 sweeps
    python scripts/se3/collect_option_spreads.py --minutes 10   # loop 10 min

The contract set comes from core/analytics/options_selection.py so the screen
rules cannot drift from the platform's live options path.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
STORE = ROOT / "data" / "se3" / "spread_collection.duckdb"

DEFAULT_UNIVERSE = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT",
    "AXISBANK", "ITC", "KOTAKBANK", "BHARTIARTL", "TATAMOTORS", "TATASTEEL",
    "HINDUNILVR", "MARUTI", "SUNPHARMA", "BAJFINANCE", "BAJAJFINSV", "NTPC",
    "ADANIENT",
]
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS spread_observations (
    trade_date    DATE    NOT NULL,
    observed_at   TIMESTAMP NOT NULL,
    underlying    VARCHAR NOT NULL,
    expiry_dt     DATE    NOT NULL,
    option_type   VARCHAR NOT NULL,
    strike        DOUBLE  NOT NULL,
    instrument_key VARCHAR NOT NULL,
    best_bid      DOUBLE,
    best_ask      DOUBLE,
    ltp           DOUBLE,
    oi            BIGINT,
    volume        BIGINT,
    spread_pct    DOUBLE,
    screen        VARCHAR,
    screen_reason VARCHAR,
    PRIMARY KEY (observed_at, instrument_key)
);
"""


def _init_store(store_path=None):
    store_path = store_path or STORE
    store_path = Path(store_path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(store_path))
    con.execute(SCHEMA_SQL)
    return con


def _pick_contracts():
    """Return [(ticker, direction, {contract row})...] via the shared options
    selection path so the collection screen cannot drift from the platform's
    live path. Direction is irrelevant to a spread measurement (both CE and PE
    quote); we collect LONG (CE) for each name to keep one quote per name."""
    from core.analytics.options_selection import select_book_options
    book = [(t, "LONG") for t in DEFAULT_UNIVERSE]
    return select_book_options(book)


def _collect_once(con, market_data):
    """One sweep: resolve contracts, fetch live quotes, append observations.
    Returns (n_observed, n_skipped, errors)."""
    from core.analytics.options_selection import screen_candidate

    rows = _pick_contracts()
    observed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    trade_date = date.today()

    n_obs = 0
    n_skip = 0
    errors = 0
    for row in rows:
        key = row.get("instrument_key")
        if not key:
            n_skip += 1
            continue
        result = market_data.fetch_quotes_batch([key])
        if result.get("error"):
            errors += 1
            continue
        q = result.get("quotes", {}).get(key)
        if not q or q.get("best_bid") is None or q.get("best_ask") is None:
            n_skip += 1
            continue
        bid, ask = q["best_bid"], q["best_ask"]
        oi = q.get("oi")
        vol = q.get("volume")
        ok, spread_pct, reason = screen_candidate(
            bid, ask, oi, vol, min_oi=100, min_volume=1, max_spread_pct=0.05)
        try:
            con.execute(
                """
                INSERT INTO spread_observations
                    (trade_date, observed_at, underlying, expiry_dt, option_type,
                     strike, instrument_key, best_bid, best_ask, ltp, oi, volume,
                     spread_pct, screen, screen_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [trade_date, observed_at, row["ticker"], row["expiry"], row["opt_type"],
                 row["strike"], key, bid, ask, q.get("ltp"), oi, vol, spread_pct,
                 "pass" if ok else "skip", reason],
            )
            n_obs += 1
        except duckdb.Error:
            errors += 1
    return n_obs, n_skip, errors


def run(sweeps: int | None, minutes: int | None, once: bool):
    from core.brokers.upstox_market_data import UpstoxMarketData

    market_data = UpstoxMarketData()
    con = _init_store()
    try:
        if once:
            n_obs, n_skip, err = _collect_once(con, market_data)
            print(f"once: {n_obs} observed, {n_skip} skipped, {err} errors")
            return _exit_code(n_obs, err)
        if sweeps is not None:
            total_obs, total_err = 0, 0
            for i in range(sweeps):
                n_obs, n_skip, err = _collect_once(con, market_data)
                print(f"sweep {i+1}/{sweeps}: {n_obs} observed, {n_skip} skipped, {err} errors")
                total_obs += n_obs
                total_err += err
                if i < sweeps - 1:
                    time.sleep(5)
            return _exit_code(total_obs, total_err)
        if minutes is not None:
            deadline = time.time() + minutes * 60
            i = 0
            total_obs, total_err = 0, 0
            while time.time() < deadline:
                i += 1
                n_obs, n_skip, err = _collect_once(con, market_data)
                print(f"sweep {i}: {n_obs} observed, {n_skip} skipped, {err} errors")
                total_obs += n_obs
                total_err += err
                time.sleep(5)
            return _exit_code(total_obs, total_err)
        print("No mode selected. Use --once, --sweeps N, or --minutes N.")
        return 0
    finally:
        con.close()


def _exit_code(n_obs: int, errors: int) -> int:
    """Freshness assertion — the collector must FAIL, not merely log, when it
    goes quiet. Lives here so every invocation (manual, OS-scheduled) surfaces
    the same non-zero signal:

      0  sweep recorded observations (or market is closed — nothing expected)
      1  fetch errors — a failed download must never be recorded as a skip
      2  market was open but the sweep recorded zero observations — expired
         token, silent auth failure, or a screen collapsing every name
    """
    if errors > 0:
        return 1
    from core.database.utils.market_hours import MarketHours
    if MarketHours.is_market_open() and n_obs == 0:
        return 2
    return 0


def main():
    parser = argparse.ArgumentParser(description="SE-3 forward spread collection")
    parser.add_argument("--once", action="store_true", help="one sweep then exit")
    parser.add_argument("--sweeps", type=int, default=None, help="run N sweeps")
    parser.add_argument("--minutes", type=int, default=None, help="loop for N minutes")
    args = parser.parse_args()
    return run(args.sweeps, args.minutes, args.once)


if __name__ == "__main__":
    raise SystemExit(main())
