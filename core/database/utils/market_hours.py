"""
Market Hours Utility
--------------------
Utilities for checking market hours and trading sessions.

Indian market hours (IST). Segment-dependent since SEBI's Closing Auction
Session (2026-08-03) — see core/market/session_schedule.py, which is the
authority. The constants below are the pre-CAS cash session, retained because
callers still reference them for display.
"""

from datetime import datetime, time, date, timedelta
from typing import Tuple, Optional, Set
import pytz
import logging

from core.market.session_schedule import any_open as _any_open
from core.market.session_schedule import is_open as _is_open
from core.market.session_schedule import session_window

_logger = logging.getLogger(__name__)


class MarketHours:
    """
    Utility class for Indian market hours.

    All times are in IST (Indian Standard Time).

    Usage:
        from core.database.utils import MarketHours

        # Check if market is open
        if MarketHours.is_market_open():
            print("Market is open")

        # Get current IST time
        now = MarketHours.get_ist_now()

        # Get today's session times
        open_time, close_time = MarketHours.get_session_times()
    """

    # Indian Standard Time timezone
    IST = pytz.timezone("Asia/Kolkata")

    # Market hours (IST)
    MARKET_OPEN = time(9, 15)  # 9:15 AM
    MARKET_CLOSE = time(15, 30)  # 3:30 PM
    PRE_MARKET_OPEN = time(9, 0)  # 9:00 AM
    POST_MARKET_CLOSE = time(16, 0)  # 4:00 PM

    # Trading days (Monday = 0, Sunday = 6)
    TRADING_DAYS = {0, 1, 2, 3, 4}  # Monday to Friday

    # NSE Trading Holidays 2026 (official NSE calendar)
    # Source: https://www.nseindia.com/resources/exchange-communication-holidays
    # Update this set at the start of each calendar year.
    NSE_HOLIDAYS: Set[date] = {
        date(2026, 1, 15),   # Municipal Corporation Election - Maharashtra
        date(2026, 1, 26),   # Republic Day
        date(2026, 3, 3),    # Holi
        date(2026, 3, 26),   # Shri Ram Navami
        date(2026, 3, 31),   # Shri Mahavir Jayanti
        date(2026, 4, 3),    # Good Friday
        date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
        date(2026, 5, 1),    # Maharashtra Day
        date(2026, 5, 28),   # Bakri Id
        date(2026, 6, 26),   # Muharram
        date(2026, 9, 14),   # Ganesh Chaturthi
        date(2026, 10, 2),   # Mahatma Gandhi Jayanti
        date(2026, 10, 20),  # Dussehra
        date(2026, 11, 10),  # Diwali-Balipratipada
        date(2026, 11, 24),  # Prakash Gurpurb Sri Guru Nanak Dev
        date(2026, 12, 25),  # Christmas
    }

    @classmethod
    def is_holiday(cls, dt: Optional[datetime] = None) -> bool:
        """Check if a date is an NSE trading holiday."""
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)
        return dt.date() in cls.NSE_HOLIDAYS

    @classmethod
    def get_ist_now(cls) -> datetime:
        """
        Get current time in IST.

        Returns:
            Current datetime in IST timezone.
        """
        return datetime.now(cls.IST)

    @classmethod
    def to_ist(cls, dt: datetime) -> datetime:
        """
        Convert a datetime to IST.

        Args:
            dt: Datetime to convert (can be naive or aware).

        Returns:
            Datetime in IST timezone.
        """
        if dt.tzinfo is None:
            # Assume naive datetime is already IST
            return cls.IST.localize(dt)
        return dt.astimezone(cls.IST)

    @classmethod
    def is_trading_day(cls, dt: Optional[datetime] = None) -> bool:
        """
        Check if a date is a trading day (weekday, not a holiday).

        Args:
            dt: Datetime to check. Defaults to current IST time.

        Returns:
            True if it's a trading day (Mon-Fri and not an NSE holiday).
        """
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)

        if dt.weekday() not in cls.TRADING_DAYS:
            return False
        if dt.date() in cls.NSE_HOLIDAYS:
            return False
        return True

    @classmethod
    def is_market_open(cls, dt: Optional[datetime] = None, segment: str = "cash_cat1") -> bool:
        """
        Check whether `segment` is currently open.

        Default segment is cash Category I (F&O-eligible stocks) — the historical
        meaning of this method. Post-CAS that session ends at 15:15, not 15:30.

        Args:
            dt: Datetime to check. Defaults to current IST time.
            segment: One of core.market.session_schedule.SEGMENTS.

        Returns:
            True if the segment is open at `dt` on a trading day.
        """
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)

        # Check if it's a trading day
        if not cls.is_trading_day(dt):
            return False

        return _is_open(segment, dt.replace(tzinfo=None))

    @classmethod
    def is_derivatives_open(cls, dt: Optional[datetime] = None) -> bool:
        """Check whether the F&O segment is open — 15:40 close since CAS."""
        return cls.is_market_open(dt, segment="derivatives")

    @classmethod
    def is_any_open(cls, dt: Optional[datetime] = None) -> bool:
        """Check whether any segment (cash, auction, or derivatives) is open."""
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)

        if not cls.is_trading_day(dt):
            return False

        return _any_open(dt.replace(tzinfo=None))

    @classmethod
    def is_pre_market(cls, dt: Optional[datetime] = None) -> bool:
        """
        Check if we're in pre-market hours.

        Args:
            dt: Datetime to check. Defaults to current IST time.

        Returns:
            True if in pre-market (9:00 AM - 9:15 AM IST).
        """
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)

        if not cls.is_trading_day(dt):
            return False

        current_time = dt.time()
        return cls.PRE_MARKET_OPEN <= current_time < cls.MARKET_OPEN

    @classmethod
    def is_post_market(cls, dt: Optional[datetime] = None) -> bool:
        """
        Check if we're in post-market hours.

        Args:
            dt: Datetime to check. Defaults to current IST time.

        Returns:
            True if after the derivatives close and before 4:00 PM IST.
        """
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)

        if not cls.is_trading_day(dt):
            return False

        current_time = dt.time()
        window = session_window("derivatives", dt.date())
        return bool(window) and window[1] <= current_time < cls.POST_MARKET_CLOSE

    @classmethod
    def get_session_times(
        cls, dt: Optional[datetime] = None
    ) -> Tuple[datetime, datetime]:
        """
        Get today's market open and close times.

        Args:
            dt: Date to get session for. Defaults to today.

        Returns:
            Tuple of (open_datetime, close_datetime) in IST.
        """
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)

        date = dt.date()
        open_dt = cls.IST.localize(datetime.combine(date, cls.MARKET_OPEN))
        close_dt = cls.IST.localize(datetime.combine(date, cls.MARKET_CLOSE))

        return (open_dt, close_dt)

    @classmethod
    def get_next_market_open(cls, dt: Optional[datetime] = None) -> datetime:
        """
        Get the next market open time.

        Args:
            dt: Starting datetime. Defaults to current IST time.

        Returns:
            Datetime of next market open in IST.
        """
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)

        # Start checking from today's open
        check_date = dt.date()
        check_dt = cls.IST.localize(datetime.combine(check_date, cls.MARKET_OPEN))

        # If today's open has passed, start from tomorrow
        if dt >= check_dt:
            check_date += timedelta(days=1)
            check_dt = cls.IST.localize(datetime.combine(check_date, cls.MARKET_OPEN))

        # Find next trading day (skip weekends AND holidays)
        while check_date.weekday() not in cls.TRADING_DAYS or check_date in cls.NSE_HOLIDAYS:
            check_date += timedelta(days=1)
        check_dt = cls.IST.localize(datetime.combine(check_date, cls.MARKET_OPEN))

        return check_dt

    @classmethod
    def time_until_market_open(cls, dt: Optional[datetime] = None) -> timedelta:
        """
        Get time remaining until market opens.

        Args:
            dt: Starting datetime. Defaults to current IST time.

        Returns:
            Timedelta until next market open.
        """
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)

        next_open = cls.get_next_market_open(dt)
        return next_open - dt

    @classmethod
    def time_until_market_close(cls, dt: Optional[datetime] = None) -> Optional[timedelta]:
        """
        Get time remaining until market closes.

        Args:
            dt: Starting datetime. Defaults to current IST time.

        Returns:
            Timedelta until market close, or None if market is not open.
        """
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)

        if not cls.is_market_open(dt):
            return None

        _, close_dt = cls.get_session_times(dt)
        return close_dt - dt
