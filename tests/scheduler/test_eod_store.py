from datetime import date, datetime

import pytest

from core.scheduler.eod_store import EodStore, TERMINAL_OUTCOMES


@pytest.fixture
def store(tmp_path):
    return EodStore(tmp_path / "eod.sqlite")


def test_enabled_defaults_false_and_round_trips(store):
    assert store.is_enabled() is False
    store.set_enabled(True)
    assert store.is_enabled() is True
    store.set_enabled(False)
    assert store.is_enabled() is False


def test_heartbeat_records_timestamp_and_pid(store):
    assert store.get_heartbeat() == (None, None)
    store.heartbeat(4321)
    ts, pid = store.get_heartbeat()
    assert pid == 4321
    assert datetime.fromisoformat(ts)


def test_run_now_is_consumed_exactly_once(store):
    assert store.consume_run_now() is False
    store.request_run_now()
    assert store.consume_run_now() is True
    assert store.consume_run_now() is False


def test_attempts_today_excludes_manual_runs(store):
    d = date(2026, 7, 31)
    store.record(d, 0, "download", "success", "manual")
    store.record(d, 1, "download", "retry", "futures stale")
    attempts = store.attempts_today(d)
    assert [a["attempt"] for a in attempts] == [1]


def test_manual_run_does_not_make_date_terminal(store):
    d = date(2026, 7, 31)
    store.record(d, 0, "done", "success", "manual")
    assert store.is_date_terminal(d) is False


def test_scheduled_success_makes_date_terminal(store):
    d = date(2026, 7, 31)
    store.record(d, 1, "done", "success", "")
    assert store.is_date_terminal(d) is True


@pytest.mark.parametrize("outcome", sorted(TERMINAL_OUTCOMES))
def test_all_terminal_outcomes_stop_the_day(store, outcome):
    d = date(2026, 7, 31)
    store.record(d, 1, "download", outcome, "")
    assert store.is_date_terminal(d) is True


def test_retry_outcome_is_not_terminal(store):
    d = date(2026, 7, 31)
    store.record(d, 1, "download", "retry", "")
    assert store.is_date_terminal(d) is False


def test_last_attempt_started_returns_latest_scheduled(store):
    d = date(2026, 7, 31)
    store.record(d, 1, "download", "retry", "")
    store.record(d, 2, "download", "retry", "")
    assert store.last_attempt_started(d).date() == d
    assert len(store.attempts_today(d)) == 2


def test_record_is_idempotent_on_same_attempt(store):
    d = date(2026, 7, 31)
    store.record(d, 1, "download", "retry", "first")
    store.record(d, 1, "download", "success", "second")
    attempts = store.attempts_today(d)
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "success"
