from datetime import date, datetime, time

import pytest

from core.market.session_schedule import (
    CAS_EFFECTIVE, SEGMENTS, SPECIAL_SESSIONS, any_open, is_open, session_window,
    session_windows,
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


# --- special sessions (Muhurat) --------------------------------------------

MUHURAT = {
    date(2023, 11, 12): (time(18, 15), time(19, 15)),
    date(2024, 11, 1): (time(18, 0), time(19, 0)),
    date(2025, 10, 21): (time(13, 45), time(14, 45)),
}


@pytest.mark.parametrize("on,window", sorted(MUHURAT.items()))
def test_special_session_window_overrides_the_era_schedule(on, window):
    for segment in ("cash_cat1", "cash_cat2", "derivatives"):
        assert session_window(segment, on) == window


@pytest.mark.parametrize("on,window", sorted(MUHURAT.items()))
def test_special_session_lasts_sixty_minutes(on, window):
    start, end = window
    minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    assert minutes == 60


@pytest.mark.parametrize("on", sorted(MUHURAT))
def test_special_session_has_no_auction(on):
    assert session_window("cash_auction", on) is None


def test_evening_muhurat_is_open_during_real_trading():
    assert any_open(datetime(2023, 11, 12, 18, 30))
    assert is_open("cash_cat1", datetime(2024, 11, 1, 18, 30))


def test_afternoon_muhurat_is_shut_outside_its_own_window():
    """The fail-open case: the era schedule called 09:30 and 15:00 open."""
    assert not any_open(datetime(2025, 10, 21, 9, 30))
    assert not any_open(datetime(2025, 10, 21, 15, 0))
    assert any_open(datetime(2025, 10, 21, 14, 0))
    assert not any_open(datetime(2025, 10, 21, 14, 45))


def test_dates_adjacent_to_a_special_session_are_ordinary():
    for on in (date(2025, 10, 20), date(2025, 10, 22), date(2023, 11, 13)):
        assert session_window("cash_cat1", on) == (time(9, 15), time(15, 30))


def test_every_special_session_maps_every_segment():
    """A partial map would silently inherit era values for the missing segment."""
    for on, windows in SPECIAL_SESSIONS.items():
        assert set(windows) == set(SEGMENTS), on


# --- split sessions (NSE special Saturdays, two blocks) ---------------------

SPLIT = (date(2024, 3, 2), date(2024, 5, 18))


@pytest.mark.parametrize("on", SPLIT)
def test_split_session_outer_bounds(on):
    assert session_window("cash_cat1", on) == (time(9, 15), time(12, 30))


@pytest.mark.parametrize("on", SPLIT)
def test_split_session_is_shut_during_the_recess(on):
    assert any_open(datetime.combine(on, time(9, 30)))
    assert not any_open(datetime.combine(on, time(10, 30)))
    assert any_open(datetime.combine(on, time(12, 0)))
    assert not any_open(datetime.combine(on, time(12, 30)))


def test_session_windows_exposes_both_blocks_of_a_split_session():
    assert session_windows("cash_cat1", date(2024, 3, 2)) == (
        (time(9, 15), time(10, 0)), (time(11, 30), time(12, 30)))
    assert session_windows("cash_cat1", date(2025, 10, 20)) == (
        (time(9, 15), time(15, 30)),)
    assert session_windows("cash_auction", date(2026, 7, 31)) == ()
