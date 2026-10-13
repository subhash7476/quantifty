"""nifty_shield_v1 expiry selection is holiday-aware.

2026-10-12 / 10-13: 2026-10-20 (Dussehra) is an NSE holiday, so that week's Nifty
weekly expired Monday 10-19. The pure-weekday rule struck legs on 20-OCT symbols
that do not exist, and both 13:00 entries skipped as "missing option marks".
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from core.market.nse_holidays import NSE_HOLIDAYS
from strategies.nifty_shield_v1 import exchange_holidays, structures
from strategies.nifty_shield_v1.config import DEFAULT_CONFIG

UNDERLYING = "NSE_INDEX|Nifty 50"


def _legacy_nearest_expiry(from_date: date, min_days: int) -> date:
    target = from_date + timedelta(days=min_days)
    return target + timedelta(days=(1 - target.weekday()) % 7)


def test_strategy_calendar_copy_equals_exchange_calendar():
    # The strategy package may not import core.market (conformance import
    # surface), so it carries a copy. Adding a year to one and not the other
    # must fail here, not at 13:00 on a holiday-shifted Monday.
    assert exchange_holidays.EXCHANGE_HOLIDAYS == NSE_HOLIDAYS


@pytest.mark.parametrize("session, expected", [
    (date(2026, 10, 9), date(2026, 10, 13)),     # ordinary Tuesday expiry
    (date(2026, 10, 12), date(2026, 10, 19)),    # Dussehra week, Mon
    (date(2026, 10, 13), date(2026, 10, 19)),    # Dussehra week, Tue
    (date(2026, 10, 14), date(2026, 10, 19)),
    (date(2026, 10, 16), date(2026, 10, 19)),    # Fri: Sun target -> shifted expiry
    (date(2026, 10, 19), date(2026, 10, 27)),    # expiry day itself rolls on
    (date(2026, 11, 2), date(2026, 11, 9)),      # Diwali-Balipratipada week
    (date(2026, 11, 3), date(2026, 11, 9)),
    (date(2026, 11, 16), date(2026, 11, 23)),    # Guru Nanak week
    (date(2026, 11, 17), date(2026, 11, 23)),
])
def test_nearest_expiry_follows_the_exchange_calendar(session, expected):
    assert structures.nearest_expiry(session, 2, UNDERLYING) == expected


def test_without_holidays_it_is_the_legacy_weekday_rule():
    d = date(2026, 1, 1)
    while d <= date(2026, 12, 31):
        for min_days in (0, 1, 2, 3):
            assert structures.nearest_expiry(
                d, min_days, UNDERLYING, holidays=frozenset()
            ) == _legacy_nearest_expiry(d, min_days)
        d += timedelta(days=1)


def test_every_session_gets_a_tradable_weekly_at_least_min_days_out():
    d = date(2026, 10, 14)
    while d <= date(2026, 12, 31):
        expiry = structures.nearest_expiry(d, 2, UNDERLYING)
        assert expiry.weekday() < 5 and expiry not in NSE_HOLIDAYS, (d, expiry)
        assert (expiry - d).days >= 2, (d, expiry)
        d += timedelta(days=1)


def test_a_shifted_expiry_closer_than_min_days_rolls_to_the_next_week():
    # Tue and Mon both closed: the weekly moves back to Fri 10-16. From Thu
    # 10-15 that is 1 day away, so it must roll rather than strike a 1 DTE leg.
    closed = frozenset({date(2026, 10, 19), date(2026, 10, 20)})
    assert structures.nearest_expiry(date(2026, 10, 14), 2, UNDERLYING,
                                     holidays=closed) == date(2026, 10, 16)
    assert structures.nearest_expiry(date(2026, 10, 15), 2, UNDERLYING,
                                     holidays=closed) == date(2026, 10, 27)


def test_compute_legs_strikes_the_real_expiry_symbols():
    legs = structures.compute_legs("bear_call_spread", 22382.95,
                                   DEFAULT_CONFIG, date(2026, 10, 12), 0.154)
    assert {leg["expiry"] for leg in legs} == {"2026-10-19"}
    assert all(leg["symbol"].startswith("NIFTY19OCT26") for leg in legs)
