from datetime import datetime

from core.database.utils.market_hours import MarketHours


def test_pre_cas_behaviour_is_unchanged():
    # 2026-07-31 is a Friday, not an NSE holiday.
    assert MarketHours.is_market_open(datetime(2026, 7, 31, 15, 25))
    assert not MarketHours.is_market_open(datetime(2026, 7, 31, 15, 31))


def test_post_cas_cat1_cash_shuts_at_1515():
    # 2026-08-03 is a Monday, not an NSE holiday.
    assert MarketHours.is_market_open(datetime(2026, 8, 3, 15, 14))
    assert not MarketHours.is_market_open(datetime(2026, 8, 3, 15, 20))


def test_post_cas_derivatives_open_until_1540():
    assert MarketHours.is_derivatives_open(datetime(2026, 8, 3, 15, 38))
    assert not MarketHours.is_derivatives_open(datetime(2026, 8, 3, 15, 41))


def test_is_any_open_spans_the_derivatives_tail():
    assert MarketHours.is_any_open(datetime(2026, 8, 3, 15, 38))


def test_holidays_and_weekends_still_shut_every_segment():
    # 2026-08-15 is a Saturday.
    assert not MarketHours.is_market_open(datetime(2026, 8, 15, 11, 0))
    assert not MarketHours.is_derivatives_open(datetime(2026, 8, 15, 11, 0))
    assert not MarketHours.is_any_open(datetime(2026, 8, 15, 11, 0))
    # 2026-10-02 is Mahatma Gandhi Jayanti (in NSE_HOLIDAYS).
    assert not MarketHours.is_derivatives_open(datetime(2026, 10, 2, 11, 0))
