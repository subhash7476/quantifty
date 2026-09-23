from datetime import date, datetime, time

import pytest

from core.execution.equity.cas_rules import (
    MIS_SQUAREOFF, is_order_type_permitted, latest_intraday_exit,
)


def test_stop_loss_rejected_during_the_auction():
    assert not is_order_type_permitted("SL", datetime(2026, 8, 24, 15, 20))


def test_stop_loss_permitted_during_continuous_trading():
    assert is_order_type_permitted("SL", datetime(2026, 8, 24, 14, 0))


def test_market_orders_rejected_after_1525():
    assert is_order_type_permitted("MARKET", datetime(2026, 8, 24, 15, 22))
    assert not is_order_type_permitted("MARKET", datetime(2026, 8, 24, 15, 26))


def test_limit_orders_permitted_throughout_the_auction():
    assert is_order_type_permitted("LIMIT", datetime(2026, 8, 24, 15, 26))


def test_pre_cas_imposes_no_restriction():
    assert is_order_type_permitted("SL", datetime(2026, 7, 29, 15, 20))


def test_latest_intraday_exit_is_the_broker_squareoff_post_cas():
    assert latest_intraday_exit(date(2026, 8, 24)) == MIS_SQUAREOFF
    assert latest_intraday_exit(date(2026, 7, 29)) == time(15, 30)


@pytest.mark.parametrize("on,expected", [
    (date(2024, 3, 2), time(12, 30)),
    (date(2024, 5, 18), time(12, 30)),
    (date(2024, 11, 1), time(19, 0)),
    (date(2025, 10, 21), time(14, 45)),
    (date(2024, 3, 4), time(15, 30)),
    (date(2024, 5, 21), time(15, 30)),
    (date(2024, 11, 4), time(15, 30)),
    (date(2025, 10, 23), time(15, 30)),
])
def test_pre_cas_exit_is_the_cash_session_end_on_special_and_adjacent_dates(on, expected):
    assert latest_intraday_exit(on) == expected
