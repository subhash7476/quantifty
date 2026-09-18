from datetime import date

import pytest

from core.market.nse_holidays import NSE_HOLIDAYS, sessions_after

SUPPLIED_2023 = [
    date(2023, 1, 26), date(2023, 3, 7), date(2023, 3, 30), date(2023, 4, 4), date(2023, 4, 7),
    date(2023, 4, 14), date(2023, 5, 1), date(2023, 6, 29), date(2023, 8, 15), date(2023, 9, 19),
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


def test_bakri_id_2023_is_observed_on_06_29_not_06_28():
    # Reconciliation 2026-09-18: the extraction keyed Bakri Id to Wed 06-28, but
    # four stores agree 06-28 traded (1m: full 375-bar Nifty session;
    # trading_calendar: 1999 symbols; equity_bhavcopy: 1999 rows; futures: 570
    # rows; options: 1354 rows) while Thu 06-29 is absent from all of them.
    # Pre-existing repo artifacts agree 06-29 is non-trading
    # (TS_BASIS_DAILY_SIGNAL_AUDIT §F11; PTMS_G_INDEX_OPTIONS_CERTIFICATION;
    # PTMS_FAMILY_G_INDEX_OPTIONS_SUBSTRATE_CERTIFICATION). Swap, not add.
    assert date(2023, 6, 28) not in NSE_HOLIDAYS
    assert date(2023, 6, 29) in NSE_HOLIDAYS


def test_sessions_after_skips_bakri_id_2023():
    assert sessions_after(date(2023, 6, 27), date(2023, 6, 30)) == [
        date(2023, 6, 28), date(2023, 6, 30)]


@pytest.mark.parametrize("year,expected", [(2023, 15), (2024, 13), (2025, 13)])
def test_year_counts_are_ordinary_holidays_only(year, expected):
    # 2024/2025 NSE summaries count 14 weekday holidays: 13 ordinary dates here
    # plus the Diwali-Laxmi Pujan Muhurat session day (2024-11-01 Fri,
    # 2025-10-21 Tue — both traded, so excluded by design, never added back).
    # 2023 needs no such reconciliation (Muhurat 2023-11-12 fell on a Sunday).
    assert len([d for d in NSE_HOLIDAYS if d.year == year]) == expected


@pytest.mark.parametrize("d", [
    date(2024, 5, 20),    # market-wide closure, reason not in annual-circular evidence
    date(2024, 11, 20),   # special NSE closure, Maharashtra Assembly Elections
])
def test_known_special_closures_stay_out_of_the_ordinary_list(d):
    # Same class as 2024-01-22: separate special-closure/calendar mechanism,
    # not ordinary NSE_HOLIDAYS entries. Pinned so a store-matching "fix"
    # cannot silently absorb them here.
    assert d not in NSE_HOLIDAYS
