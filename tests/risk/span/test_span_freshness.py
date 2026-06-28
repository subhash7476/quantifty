"""Block J — span_freshness date helpers (MM9.4-S2)."""

from datetime import date, datetime, timedelta

import pytz

from core.risk.span.span_freshness import expected_span_date


def test_expected_date_returns_today_on_trading_day():
    # Monday 2026-06-29 is a trading day
    dt = datetime(2026, 6, 29, 10, 0, tzinfo=pytz.UTC)
    result = expected_span_date(dt)
    # During market hours (before cutoff), expected date is today
    assert result == date(2026, 6, 29)


def test_expected_date_weekend_rolls_to_previous_trading_day():
    """Weekend returns the last trading day before the weekend."""
    dt = datetime(2026, 6, 27, 10, 0, tzinfo=pytz.UTC)
    result = expected_span_date(dt)
    # Should be a date before the weekend, not a weekend
    assert result < date(2026, 6, 27)
    assert result.weekday() < 5  # Must be a weekday


def test_expected_date_sunday_rolls_to_previous_trading_day():
    dt = datetime(2026, 6, 28, 10, 0, tzinfo=pytz.UTC)
    result = expected_span_date(dt)
    assert result < date(2026, 6, 28)
    assert result.weekday() < 5


def test_expected_date_before_cutoff_returns_previous():
    """Before 08:30 IST, the expected date is the previous trading day."""
    ist = pytz.timezone("Asia/Kolkata")
    dt = ist.localize(datetime(2026, 6, 29, 6, 0))
    result = expected_span_date(dt)
    # Should be a weekday before Monday
    assert result < date(2026, 6, 29)
    assert result.weekday() < 5


def test_expected_date_is_deterministic():
    dt = datetime(2026, 6, 29, 12, 0, tzinfo=pytz.UTC)
    assert expected_span_date(dt) == expected_span_date(dt)
