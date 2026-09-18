from datetime import date, time

import pytest

from core.market.bar_labeling import (
    NATIVE, VENDOR, UnknownLabeling, covered_interval, labeling_of,
)


def test_native_era_first_bar_is_the_open():
    assert labeling_of(time(9, 15), date(2023, 6, 15)) == NATIVE


def test_vendor_era_first_bar_is_one_minute_after_the_open():
    assert labeling_of(time(9, 16), date(2022, 6, 15)) == VENDOR


def test_era_follows_the_observed_stamp_not_the_calendar():
    """2023-01-31 sits in the native era by date but is labelled the vendor way."""
    assert labeling_of(time(9, 16), date(2023, 1, 31)) == VENDOR
    assert labeling_of(time(9, 15), date(2022, 6, 15)) == NATIVE


def test_muhurat_session_resolves_against_its_own_open():
    assert labeling_of(time(13, 45), date(2025, 10, 21)) == NATIVE
    assert labeling_of(time(18, 15), date(2023, 11, 12)) == NATIVE
    assert labeling_of(time(18, 16), date(2023, 11, 12)) == VENDOR


def test_an_unrecognised_stamp_is_refused_not_guessed():
    with pytest.raises(UnknownLabeling):
        labeling_of(time(9, 17), date(2023, 6, 15))
    with pytest.raises(UnknownLabeling):
        labeling_of(time(18, 15), date(2023, 6, 15))


def test_covered_interval_is_half_open_around_the_stamp():
    assert covered_interval(time(9, 15), NATIVE) == (time(9, 15), time(9, 16))
    assert covered_interval(time(9, 16), VENDOR) == (time(9, 15), time(9, 16))
    assert covered_interval(time(15, 29), NATIVE) == (time(15, 29), time(15, 30))
    assert covered_interval(time(15, 30), VENDOR) == (time(15, 29), time(15, 30))


def test_the_two_conventions_name_the_same_minute_differently():
    """The seam in one line: 15:29 native and 15:30 vendor are the same minute."""
    assert covered_interval(time(15, 29), NATIVE) == covered_interval(time(15, 30), VENDOR)
