from datetime import date, datetime

import pytest

from core.scheduler.eod_chain import StepResult
from core.scheduler.eod_job import Deps, run_attempt
from core.scheduler.eod_store import EodStore

TODAY = date(2026, 7, 31)
YESTERDAY = date(2026, 7, 30)


@pytest.fixture
def store(tmp_path):
    return EodStore(tmp_path / "eod.sqlite")


def make_deps(feed_map, chain_results=None, sent=None):
    sent = sent if sent is not None else []
    return Deps(
        download=lambda: StepResult("download", True, "", ""),
        probe=lambda: feed_map,
        chain=lambda: chain_results if chain_results is not None
        else [StepResult(lbl, True, "", "") for lbl in ("a", "b", "c")],
        send=lambda text: (sent.append(text), True)[1],
        book=lambda: (TODAY, []),
    )


def feeds(**kw):
    base = {"equity": YESTERDAY, "futures": YESTERDAY,
            "stock_options": YESTERDAY, "index": YESTERDAY}
    base.update(kw)
    return base


def test_successful_run_records_success_and_sends_two_messages(store):
    sent = []
    outcome = run_attempt(store, TODAY, 1, datetime(2026, 7, 31, 20, 0),
                          make_deps(feeds(futures=TODAY), sent=sent))
    assert outcome == "success"
    assert store.is_date_terminal(TODAY) is True
    assert len(sent) == 2  # download success + options book


def test_retry_records_retry_and_sends_nothing(store):
    sent = []
    outcome = run_attempt(store, TODAY, 1, datetime(2026, 7, 31, 20, 0),
                          make_deps(feeds(equity=TODAY), sent=sent))
    assert outcome == "retry"
    assert store.is_date_terminal(TODAY) is False
    assert sent == []


def test_holiday_records_holiday_and_notifies(store):
    sent = []
    outcome = run_attempt(store, TODAY, 3, datetime(2026, 7, 31, 21, 0),
                          make_deps(feeds(), sent=sent))
    assert outcome == "holiday"
    assert store.is_date_terminal(TODAY) is True
    assert len(sent) == 1


def test_chain_failure_records_chain_failed_and_alerts(store):
    sent = []
    deps = make_deps(
        feeds(futures=TODAY),
        chain_results=[StepResult("refresh_all_strategies.py", False, "", "BoomError")],
        sent=sent,
    )
    outcome = run_attempt(store, TODAY, 1, datetime(2026, 7, 31, 20, 0), deps)
    assert outcome == "chain_failed"
    assert store.is_date_terminal(TODAY) is True
    assert any("BoomError" in m for m in sent)


def test_exhausted_on_final_attempt(store):
    sent = []
    outcome = run_attempt(store, TODAY, 8, datetime(2026, 7, 31, 23, 30),
                          make_deps(feeds(equity=TODAY), sent=sent))
    assert outcome == "exhausted"
    assert store.is_date_terminal(TODAY) is True
    assert len(sent) == 1


def test_options_book_message_is_sent_after_chain(store):
    sent = []
    run_attempt(store, TODAY, 1, datetime(2026, 7, 31, 20, 0),
                make_deps(feeds(futures=TODAY), sent=sent))
    assert "ATM OPTIONS" in sent[-1]
