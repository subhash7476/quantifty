import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from core.market.nse_holidays import NSE_HOLIDAYS
from core.market.session_schedule import SPECIAL_SESSIONS
from core.market.trading_calendar import (
    ADDITIONAL_SESSIONS, COVERAGE_FIRST, COVERAGE_LAST, MAX_LOOKBACK_DAYS, SPECIAL_CLOSURES,
    OutsideCoverage, is_session, previous_session,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CSMP_DB = REPO_ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"

# Session-calendar architecture audit, section B (1m store + CSMP trading_calendar).
CHRONOLOGY = [
    (date(2023, 11, 12), True),   # Sun Muhurat
    (date(2023, 11, 13), True),
    (date(2024, 1, 20), True),    # Sat
    (date(2024, 1, 21), False),   # Sun
    (date(2024, 1, 22), False),   # special closure
    (date(2024, 1, 23), True),
    (date(2024, 3, 2), True),     # Sat DR
    (date(2024, 3, 3), False),
    (date(2024, 3, 4), True),
    (date(2024, 5, 18), True),    # Sat DR
    (date(2024, 5, 19), False),
    (date(2024, 5, 20), False),   # special closure
    (date(2024, 5, 21), True),
    (date(2024, 11, 1), True),    # Fri Muhurat
    (date(2024, 11, 2), False),
    (date(2024, 11, 3), False),
    (date(2024, 11, 4), True),
    (date(2024, 11, 20), False),  # special closure
    (date(2025, 2, 1), True),     # Sat Budget
    (date(2025, 2, 2), False),
    (date(2025, 2, 3), True),
    (date(2025, 10, 20), True),
    (date(2025, 10, 21), True),   # Tue Muhurat
    (date(2025, 10, 22), False),  # NSE_HOLIDAYS
    (date(2025, 10, 23), True),
    (date(2026, 2, 1), True),     # Sun Budget; Nifty 1m not captured
    (date(2026, 2, 2), True),
]


@pytest.mark.parametrize("d,expected", CHRONOLOGY)
def test_chronology_rows(d, expected):
    assert is_session(d) is expected


@pytest.mark.parametrize("d,expected", [
    (date(2024, 1, 23), date(2024, 1, 20)),
    (date(2024, 3, 4), date(2024, 3, 2)),
    (date(2024, 5, 21), date(2024, 5, 18)),
    (date(2024, 11, 4), date(2024, 11, 1)),
    (date(2025, 2, 3), date(2025, 2, 1)),
    (date(2025, 10, 23), date(2025, 10, 21)),
    (date(2026, 2, 2), date(2026, 2, 1)),
    (date(2024, 11, 21), date(2024, 11, 19)),
    (date(2023, 11, 13), date(2023, 11, 12)),
    (date(2024, 1, 22), date(2024, 1, 20)),   # a closed date still has a predecessor
])
def test_previous_session(d, expected):
    assert previous_session(d) == expected


def test_previous_session_is_strictly_earlier():
    assert previous_session(date(2024, 1, 20)) == date(2024, 1, 19)


def test_weekend_sessions_are_sessions():
    assert is_session(date(2024, 1, 20))
    assert is_session(date(2025, 2, 1))


def test_every_special_session_key_is_a_session():
    assert all(is_session(d) for d in SPECIAL_SESSIONS)


@pytest.mark.parametrize("d", sorted(SPECIAL_CLOSURES))
def test_special_closures_are_not_sessions_and_not_ordinary_holidays(d):
    assert not is_session(d)
    assert d not in NSE_HOLIDAYS


def test_required_members():
    assert ADDITIONAL_SESSIONS == {
        date(2023, 11, 12), date(2024, 1, 20), date(2024, 3, 2),
        date(2024, 5, 18), date(2025, 2, 1), date(2026, 2, 1)}
    assert SPECIAL_CLOSURES == {date(2024, 1, 22), date(2024, 5, 20), date(2024, 11, 20)}


def test_additional_sessions_and_closures_are_disjoint_from_holidays():
    assert not ADDITIONAL_SESSIONS & NSE_HOLIDAYS
    assert not ADDITIONAL_SESSIONS & SPECIAL_CLOSURES


def test_declared_coverage_is_2023_through_2026():
    assert COVERAGE_FIRST == date(2023, 1, 1)
    assert COVERAGE_LAST == date(2026, 12, 31)


@pytest.mark.parametrize("d", [date(2022, 12, 30), date(2027, 1, 4)])
def test_is_session_refuses_dates_outside_coverage(d):
    with pytest.raises(OutsideCoverage):
        is_session(d)


def test_previous_session_hard_stops_at_the_coverage_start():
    # 2023-01-02 is the first covered session; its predecessor lies in 2022.
    with pytest.raises(OutsideCoverage):
        previous_session(date(2023, 1, 2))


def test_previous_session_hard_stops_far_outside_coverage():
    with pytest.raises(OutsideCoverage):
        previous_session(date(2030, 6, 3))


def test_lookback_bound_never_trips_inside_coverage():
    d = COVERAGE_FIRST + timedelta(days=MAX_LOOKBACK_DAYS)
    while d <= COVERAGE_LAST:
        s = previous_session(d)
        assert s < d and is_session(s)
        d += timedelta(days=1)


def test_no_other_core_market_module_imports_trading_calendar():
    pattern = re.compile(r"^\s*(from|import)\s+[\w.]*trading_calendar", re.MULTILINE)
    offenders = [
        p.name for p in (REPO_ROOT / "core" / "market").glob("*.py")
        if p.name != "trading_calendar.py" and pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == []


@pytest.mark.skipif(not CSMP_DB.exists(), reason="CSMP equity_bhavcopy store not present")
def test_conforms_to_the_empirical_csmp_trading_calendar():
    # Read-only validation only; the CSMP table is not the runtime source of truth.
    import duckdb
    con = duckdb.connect(str(CSMP_DB), read_only=True)
    try:
        rows = con.execute(
            "SELECT trade_date FROM trading_calendar WHERE trade_date BETWEEN ? AND ?",
            [COVERAGE_FIRST, COVERAGE_LAST]).fetchall()
    finally:
        con.close()
    observed = {r[0] for r in rows}
    last = max(observed)
    span = [COVERAGE_FIRST + timedelta(days=i) for i in range((last - COVERAGE_FIRST).days + 1)]
    assert {d for d in span if is_session(d)} == observed
