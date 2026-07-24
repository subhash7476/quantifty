"""Driver-level test for calendar-driven replay alignment.

This test guards the driver-side half of the calendar-driven fix.
See CARRY_REPLAY_FIX_REVIEW.md §2.2.

The test constructs a real LoopDriver(Mode.REPLAY) with DailyBhavcopyProvider
and verifies that within-tick bar-date spread is exactly 0 for 100% of ticks.

This would have caught the isinstance guard deletion case, which the provider-only
test would not.
"""
from datetime import date as Date, datetime, time

import pytest

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver
from core.clock import ReplayClock
from core.database.providers.daily_bhavcopy import DailyBhavcopyProvider
from core.events import TradeEvent, OHLCVBar


class ClockTickObserver:
    """Observer that records bar timestamps grouped by clock time (tick boundaries)."""

    def __init__(self):
        self.ticks = []
        self.current_tick_bars = None
        self.last_clock_time = None

    def on_bar(self, bar: OHLCVBar, clock_time):
        """Called when a bar is processed with the current clock time."""
        if self.last_clock_time is None:
            self.last_clock_time = clock_time
            self.current_tick_bars = []
        elif clock_time != self.last_clock_time:
            self.ticks.append(self.current_tick_bars.copy())
            self.current_tick_bars = []
            self.last_clock_time = clock_time

        self.current_tick_bars.append((bar.symbol, bar.timestamp.date()))


class ObservingSource:
    """Signal source that observes bars without generating signals."""
    def __init__(self, observer, clock):
        self.observer = observer
        self.clock = clock

    def on_start(self):
        pass

    def on_bar(self, bar):
        self.observer.on_bar(bar, self.clock.now())
        return []

    def on_stop(self):
        pass


def test_driver_calendar_alignment():
    """LoopDriver with DailyBhavcopyProvider delivers aligned cross-sections."""
    bhavcopy_db = "data/market_data/futures_bhavcopy.duckdb"

    import duckdb
    con = duckdb.connect(bhavcopy_db, read_only=True)
    con.execute("SET threads=4")

    # Use a small subset for faster test
    TRAIN_SYMBOLS_SQL = """
        SELECT DISTINCT underlying
        FROM futures_bhavcopy
        WHERE trade_date BETWEEN '2016-03-31' AND '2016-12-31'
          AND inst_type = 'FUTSTK'
        ORDER BY underlying
        LIMIT 50
    """
    symbols = [row[0] for row in con.execute(TRAIN_SYMBOLS_SQL).fetchall()]
    con.close()

    # Derive expected trading days (not hardcoded, per review §2.4)
    con = duckdb.connect(bhavcopy_db, read_only=True)
    expected_days_query = f"""
        SELECT COUNT(DISTINCT trade_date)
        FROM futures_bhavcopy
        WHERE trade_date BETWEEN '2016-03-31' AND '2016-12-31'
          AND inst_type = 'FUTSTK'
          AND underlying IN ({', '.join(f"'{s}'" for s in symbols)})
    """
    expected_trading_days = con.execute(expected_days_query).fetchone()[0]
    con.close()

    # Create provider
    provider = DailyBhavcopyProvider(
        underlyings=symbols,
        bhavcopy_db=bhavcopy_db,
        start_date=Date(2016, 3, 31),
        end_date=Date(2016, 12, 31),
    )

    # Create a signal source that acts as our tick observer
    clock = ReplayClock(start_time=datetime(2016, 3, 31, 9, 15, 0))
    observer = ClockTickObserver()
    source = ObservingSource(observer, clock)

    # Create config and driver
    # max_bars bound ensures test fails cleanly (tick-count mismatch) rather than
    # hanging if advance_tick() is disabled. See CARRY_REPLAY_FIX_FOLLOWUP_SUMMARY.md
    config = DriverConfig(
        mode=Mode.REPLAY,
        symbols=symbols,
        max_bars=10000,  # Sufficient to cover all dates in test window
    )

    driver = LoopDriver(
        config=config,
        clock=clock,
        provider=provider,
        source=source,
        execution=None,
        rebalance_hook=None,
    )

    # Run the driver
    driver.run()

    # Flush the last tick
    if observer.current_tick_bars:
        observer.ticks.append(observer.current_tick_bars)

    # Validate alignment
    misaligned_ticks = 0
    max_spread_days = 0

    for tick_idx, bars in enumerate(observer.ticks):
        if len(bars) > 1:
            dates = [d for _, d in bars]
            min_date = min(dates)
            max_date = max(dates)
            spread = (max_date - min_date).days

            if spread > 0:
                misaligned_ticks += 1
                max_spread_days = max(max_spread_days, spread)

    # Enforce the acceptance test from CARRY_REPLAY_INFRA_TEST_REPORT.md §5
    assert misaligned_ticks == 0, f"{misaligned_ticks} ticks had non-zero spread; max spread: {max_spread_days} days"
    assert max_spread_days == 0, f"Max within-tick spread: {max_spread_days} days"

    # Tick count should match expected trading days
    assert len(observer.ticks) == expected_trading_days, f"Expected {expected_trading_days} ticks, got {len(observer.ticks)}"

    # Verify tick dates are strictly increasing
    for i in range(1, len(observer.ticks)):
        tick_dates = set(d for _, d in observer.ticks[i])
        prev_tick_dates = set(d for _, d in observer.ticks[i-1])
        # All dates in current tick should be after all dates in previous tick
        for curr_date in tick_dates:
            for prev_date in prev_tick_dates:
                assert curr_date > prev_date, f"Tick dates not strictly increasing at tick {i}"


if __name__ == "__main__":
    test_driver_calendar_alignment()
    print("PASS: Driver-level calendar alignment test")