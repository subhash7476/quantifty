from datetime import date

import pytest

from core.market.nse_holidays import NSE_HOLIDAYS, sessions_after

SUPPLIED_2023 = [
    date(2023, 1, 26), date(2023, 3, 7), date(2023, 3, 30), date(2023, 4, 4), date(2023, 4, 7),
    date(2023, 4, 14), date(2023, 5, 1), date(2023, 6, 28), date(2023, 8, 15), date(2023, 9, 19),
    date(2023, 10, 2), date(2023, 10, 24), date(2023, 11, 14), date(2023, 11, 27), date(2023, 12, 25),
]
SUPPLIED_2024 = [
    date(2024, 1, 26), date(2024, 3, 8), date(2024, 3, 25), date(2024, 3, 29), date(2024, 4, 11),
    date(2024, 4, 17), date(2024, 5, 1), date(2024, 6, 17), date(2024, 7, 17), date(2024, 8, 15),
    date(2024, 10, 2), date(2024, 11, 15), date(2024, 12, 25),
]
SUPPLIED_2025 = [
    date(2025, 2, 26), date(2025, 3, 14), date(2025, 3, 31), date(2025, 4, 10), date(2025, 4, 14),
    date(2025, 4, 18), date(2025, 5, 1), date(2025, 8, 15), date(2025, 8, 27), date(2025, 10, 2),
    date(2025, 10, 22), date(2025, 11, 5), date(2025, 12, 25),
]
EXISTING_2026 = {
    date(2026, 1, 15), date(2026, 1, 26), date(2026, 3, 3), date(2026, 3, 26), date(2026, 3, 31),
    date(2026, 4, 3), date(2026, 4, 14), date(2026, 5, 1), date(2026, 5, 28), date(2026, 6, 26),
    date(2026, 9, 14), date(2026, 10, 2), date(2026, 10, 20), date(2026, 11, 10), date(2026, 11, 24),
    date(2026, 12, 25),
}


@pytest.mark.parametrize("d", SUPPLIED_2023 + SUPPLIED_2024 + SUPPLIED_2025)
def test_supplied_2023_2025_holidays_are_listed(d):
    assert d in NSE_HOLIDAYS


def test_2023_2025_entries_are_exactly_the_supplied_dates():
    listed = {d for d in NSE_HOLIDAYS if 2023 <= d.year <= 2025}
    assert listed == set(SUPPLIED_2023 + SUPPLIED_2024 + SUPPLIED_2025)


def test_2026_entries_are_unchanged():
    assert {d for d in NSE_HOLIDAYS if d.year == 2026} == EXISTING_2026


def test_every_holiday_is_a_weekday():
    assert all(d.weekday() < 5 for d in NSE_HOLIDAYS)


@pytest.mark.parametrize("d", [
    date(2023, 11, 12),  # Muhurat - SPECIAL_SESSIONS territory, not this list
    date(2024, 11, 1),   # Muhurat
    date(2025, 10, 21),  # Muhurat
    date(2024, 1, 22),   # special trading holiday - kept out of the ordinary list
    date(2024, 1, 20),   # Saturday trading session
    date(2025, 2, 1),    # Saturday Budget trading session
])
def test_special_and_weekend_session_dates_are_not_ordinary_holidays(d):
    assert d not in NSE_HOLIDAYS


@pytest.mark.parametrize("d", [date(2023, 3, 8), date(2024, 3, 26), date(2025, 3, 17)])
def test_ordinary_weekdays_remain_trading_days(d):
    assert d not in NSE_HOLIDAYS


def test_sessions_after_skips_a_2025_holiday():
    # 2025-03-14 (Fri) is Holi; the next sessions are Mon 03-17 and Tue 03-18.
    assert sessions_after(date(2025, 3, 13), date(2025, 3, 18)) == [date(2025, 3, 17), date(2025, 3, 18)]
