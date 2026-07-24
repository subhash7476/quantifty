"""Regression test for calendar-driven DailyBhavcopyProvider.

Enforces the acceptance test from CARRY_REPLAY_INFRA_TEST_REPORT.md §5:
- Within-tick bar-date spread must be exactly 0 for 100% of ticks
- Tick count must equal the number of trading dates in the window

This test would have caught the per-symbol cursor defect documented in that
report (median spread 463 days, 10.6% aligned).

Runs on TRAIN-era data only; no SEALED read.
"""
from datetime import date as Date, datetime, time
from pathlib import Path
from typing import List, Optional

import duckdb

from core.database.providers.daily_bhavcopy import DailyBhavcopyProvider
from core.events import OHLCVBar


def test_calendar_alignment():
    """Provider delivers aligned cross-sections — all symbols same date per tick."""
    bhavcopy_db = "data/market_data/futures_bhavcopy.duckdb"

    con = duckdb.connect(bhavcopy_db, read_only=True)
    con.execute("SET threads=4")

    TRAIN_SYMBOLS_SQL = """
        SELECT DISTINCT underlying
        FROM futures_bhavcopy
        WHERE trade_date BETWEEN '2016-03-31' AND '2020-12-31'
          AND inst_type = 'FUTSTK'
        ORDER BY underlying
    """
    symbols = [row[0] for row in con.execute(TRAIN_SYMBOLS_SQL).fetchall()]
    con.close()

    provider = DailyBhavcopyProvider(
        underlyings=symbols,
        bhavcopy_db=bhavcopy_db,
        start_date=Date(2016, 3, 31),
        end_date=Date(2020, 12, 31),
    )

    tick_count = 0
    misaligned_ticks = 0
    max_spread_days = 0

    while provider.is_data_available(symbols[0]):
        bars_this_tick = {}
        for sym in symbols:
            bar = provider.get_next_bar(sym)
            if bar is not None:
                bars_this_tick[sym] = bar.timestamp.date()

        provider.advance_tick()

        if len(bars_this_tick) > 1:
            dates_in_tick = list(bars_this_tick.values())
            min_date = min(dates_in_tick)
            max_date = max(dates_in_tick)
            spread = (max_date - min_date).days

            if spread > 0:
                misaligned_ticks += 1
                max_spread_days = max(max_spread_days, spread)

        tick_count += 1

    assert misaligned_ticks == 0, f"{misaligned_ticks} ticks had non-zero spread; max spread: {max_spread_days} days"
    assert max_spread_days == 0, f"Max within-tick spread: {max_spread_days} days"

    expected_trading_days = len(provider._calendar)
    assert tick_count == expected_trading_days, f"Expected {expected_trading_days} ticks, got {tick_count}"


if __name__ == "__main__":
    test_calendar_alignment()
    print("PASS: Calendar alignment test — 100% ticks aligned, correct tick count")