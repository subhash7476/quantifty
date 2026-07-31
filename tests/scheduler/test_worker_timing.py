from datetime import datetime

from scripts.schedule_worker import is_due

MON_2000 = datetime(2026, 7, 27, 20, 0)     # Monday
MON_1959 = datetime(2026, 7, 27, 19, 59)
MON_2330 = datetime(2026, 7, 27, 23, 30)
MON_2331 = datetime(2026, 7, 27, 23, 31)
SAT_2000 = datetime(2026, 8, 1, 20, 0)      # Saturday


def test_not_due_before_fire_hour():
    assert is_due(MON_1959, None, 0) is False


def test_due_at_fire_hour_with_no_prior_attempt():
    assert is_due(MON_2000, None, 0) is True


def test_not_due_on_weekend():
    assert is_due(SAT_2000, None, 0) is False


def test_not_due_after_stop_time():
    assert is_due(MON_2331, None, 0) is False


def test_due_exactly_at_stop_time():
    assert is_due(MON_2330, datetime(2026, 7, 27, 23, 0), 7) is True


def test_not_due_before_retry_interval_elapses():
    assert is_due(datetime(2026, 7, 27, 20, 20), MON_2000, 1) is False


def test_due_once_retry_interval_elapses():
    assert is_due(datetime(2026, 7, 27, 20, 30), MON_2000, 1) is True


def test_not_due_once_attempt_cap_reached():
    assert is_due(datetime(2026, 7, 27, 23, 0), datetime(2026, 7, 27, 22, 0), 8) is False
