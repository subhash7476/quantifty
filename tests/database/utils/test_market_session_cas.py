from datetime import date, datetime

import pytest

from core.database.utils.market_session import MarketSession
from core.market.session_schedule import is_open


def test_pre_cas_session_ends_1530():
    assert MarketSession(date(2026, 7, 31)).end.strftime("%H:%M") == "15:30"


def test_post_cas_session_ends_1515_for_cat1_cash():
    assert MarketSession(date(2026, 8, 3)).end.strftime("%H:%M") == "15:15"


def test_contains_respects_the_post_cas_end():
    session = MarketSession(date(2026, 8, 3))
    assert session.contains(datetime(2026, 8, 3, 15, 14))
    assert not session.contains(datetime(2026, 8, 3, 15, 20))


def test_progress_reaches_one_at_the_new_close():
    session = MarketSession(date(2026, 8, 3))
    assert session.get_progress(datetime(2026, 8, 3, 15, 15)) == 1.0


@pytest.mark.parametrize("on,start,end", [
    (date(2024, 3, 2), "09:15", "12:30"),
    (date(2024, 5, 18), "09:15", "12:30"),
    (date(2024, 11, 1), "18:00", "19:00"),
    (date(2025, 10, 21), "13:45", "14:45"),
])
def test_special_session_outer_bounds(on, start, end):
    session = MarketSession(on)
    assert session.start.strftime("%H:%M") == start
    assert session.end.strftime("%H:%M") == end


def test_contains_spans_the_dr_recess_unlike_is_open():
    # Intentional divergence (ruling G-1): MarketSession is outer-bound only,
    # so it contains the recess that session_schedule.is_open reports shut.
    ts = datetime(2024, 3, 2, 10, 30)
    assert MarketSession(date(2024, 3, 2)).contains(ts)
    assert not is_open("cash_cat1", ts)
