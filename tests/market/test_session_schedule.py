from datetime import date, datetime, time

import pytest

from core.market.session_schedule import (
    CAS_EFFECTIVE, any_open, is_open, session_window,
)


def test_cas_effective_date_is_2026_08_03():
    assert CAS_EFFECTIVE == date(2026, 8, 3)


def test_pre_cas_cash_closes_at_1530():
    assert session_window("cash_cat1", date(2026, 7, 31)) == (time(9, 15), time(15, 30))


def test_pre_cas_has_no_auction():
    assert session_window("cash_auction", date(2026, 7, 31)) is None


def test_pre_cas_derivatives_close_at_1530():
    assert session_window("derivatives", date(2026, 7, 31)) == (time(9, 15), time(15, 30))


def test_post_cas_cat1_continuous_ends_1515():
    assert session_window("cash_cat1", date(2026, 8, 3)) == (time(9, 15), time(15, 15))


def test_post_cas_cat2_continuous_still_ends_1530():
    assert session_window("cash_cat2", date(2026, 8, 3)) == (time(9, 15), time(15, 30))


def test_post_cas_auction_window():
    assert session_window("cash_auction", date(2026, 8, 3)) == (time(15, 15), time(15, 35))


def test_post_cas_derivatives_extend_to_1540():
    assert session_window("derivatives", date(2026, 8, 3)) == (time(9, 15), time(15, 40))


def test_is_open_excludes_end_boundary():
    assert is_open("cash_cat1", datetime(2026, 8, 3, 15, 14))
    assert not is_open("cash_cat1", datetime(2026, 8, 3, 15, 15))


def test_derivatives_open_while_cat1_cash_is_shut():
    dt = datetime(2026, 8, 3, 15, 35)
    assert not is_open("cash_cat1", dt)
    assert is_open("derivatives", dt)


def test_any_open_true_during_derivatives_only_window():
    assert any_open(datetime(2026, 8, 3, 15, 38))
    assert not any_open(datetime(2026, 8, 3, 15, 41))


def test_unknown_segment_raises():
    with pytest.raises(KeyError):
        session_window("equities", date(2026, 8, 3))
