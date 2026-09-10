"""The daily bar's nominal close stamp must follow the era, not a constant.

CAS register C4: `daily_bhavcopy` stamped every daily bar at 15:30. Pre-CAS that
was the cash close; post-CAS the Category I official close is struck in the
auction, which ends 15:35. The VALUE was always correct — only the label was wrong
— but a bare constant is exactly what the register exists to eliminate.
"""
from datetime import date, time

from core.database.providers.daily_bhavcopy import session_close_stamp


def test_pre_cas_stamps_the_cash_close():
    assert session_close_stamp(date(2026, 7, 31)).time() == time(15, 30)


def test_post_cas_stamps_the_auction_close():
    assert session_close_stamp(date(2026, 8, 3)).time() == time(15, 35)
    assert session_close_stamp(date(2026, 9, 10)).time() == time(15, 35)


def test_the_stamp_keeps_the_session_date():
    d = date(2026, 9, 10)
    assert session_close_stamp(d).date() == d
