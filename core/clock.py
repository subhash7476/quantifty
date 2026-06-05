"""
Clock - Single Source of Truth for Time
---------------------------------------
Abstracts time to support both live trading and historical replay.
"""
from abc import ABC
from datetime import datetime, timedelta
import pytz

class Clock(ABC):
    """
    Abstract base class for all clocks.
    """
    
    def now(self) -> datetime:
        """Returns the current 'system' time."""
        return datetime.now(pytz.UTC)

    def sleep(self, seconds: float):
        """Simulates or performs an actual sleep."""
        pass

    def set_time(self, dt: datetime) -> None:
        """
        Set the clock's current time. No-op by default.

        The deterministic loop driver calls this uniformly on every tick with
        the current bar's timestamp (DRIVER_SPECIFICATION.md §6), without
        branching on clock type. Replay clocks override this to advance
        deterministic time; wall-clock clocks (e.g. RealTimeClock) inherit this
        no-op and safely ignore external time ownership — live time is
        authoritative and owned by the wall clock, not the data feed.
        """
        pass


class RealTimeClock(Clock):
    """
    Clock implementation for live trading.
    """
    
    def __init__(self, timezone: str = 'Asia/Kolkata'):
        self.tz = pytz.timezone(timezone)

    def now(self) -> datetime:
        return datetime.now(self.tz)

    def sleep(self, seconds: float):
        import time
        time.sleep(seconds)


class ReplayClock(Clock):
    """
    Clock implementation for historical backtesting.
    Time only advances when manually stepped or when data is consumed.
    """
    
    def __init__(self, start_time: datetime):
        self._current_time = start_time

    def now(self) -> datetime:
        return self._current_time

    def set_time(self, dt: datetime):
        """Manually advance the clock."""
        self._current_time = dt

    def advance(self, delta: timedelta):
        """Advance the clock by a duration."""
        self._current_time += delta
