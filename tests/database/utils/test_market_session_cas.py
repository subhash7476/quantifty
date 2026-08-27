from datetime import date, datetime

from core.database.utils.market_session import MarketSession


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
