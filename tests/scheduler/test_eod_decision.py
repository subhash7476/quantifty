from datetime import date, datetime

from core.scheduler.eod_decision import MAX_ATTEMPTS, decide

TODAY = date(2026, 7, 31)
YESTERDAY = date(2026, 7, 30)


def feeds(equity=YESTERDAY, futures=YESTERDAY, stock_options=YESTERDAY, index=YESTERDAY):
    return {"equity": equity, "futures": futures, "stock_options": stock_options, "index": index}


def at(hour, minute=0):
    return datetime(2026, 7, 31, hour, minute)


def test_futures_today_runs_the_chain():
    d = decide(feeds(futures=TODAY), TODAY, at(20), attempt=1)
    assert d.action == "chain"


def test_partial_feeds_without_futures_retries():
    d = decide(feeds(equity=TODAY), TODAY, at(20), attempt=1)
    assert d.action == "retry"


def test_partial_feeds_retries_even_after_grace_hour():
    # A trading day is proven: some feed published. Grace must not apply.
    d = decide(feeds(index=TODAY), TODAY, at(22), attempt=3)
    assert d.action == "retry"


def test_all_feeds_stale_before_grace_hour_retries():
    d = decide(feeds(), TODAY, at(20, 30), attempt=2)
    assert d.action == "retry"


def test_all_feeds_stale_at_grace_hour_declares_holiday():
    d = decide(feeds(), TODAY, at(21), attempt=3)
    assert d.action == "holiday"


def test_all_feeds_stale_after_grace_hour_declares_holiday():
    d = decide(feeds(), TODAY, at(22, 30), attempt=6)
    assert d.action == "holiday"


def test_attempt_cap_exhausts_before_holiday_check():
    d = decide(feeds(equity=TODAY), TODAY, at(23, 30), attempt=MAX_ATTEMPTS)
    assert d.action == "exhausted"


def test_chain_wins_even_on_final_attempt():
    d = decide(feeds(futures=TODAY), TODAY, at(23, 30), attempt=MAX_ATTEMPTS)
    assert d.action == "chain"


def test_missing_store_is_treated_as_stale():
    d = decide(feeds(equity=None, futures=None, stock_options=None, index=None),
               TODAY, at(21), attempt=3)
    assert d.action == "holiday"


def test_decision_carries_a_reason():
    assert decide(feeds(futures=TODAY), TODAY, at(20), attempt=1).reason
    assert decide(feeds(), TODAY, at(21), attempt=3).reason
