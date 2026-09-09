"""Transient vs structural: only a known-recoverable fault may be transient."""
import duckdb
import pytest
import requests

from core.options_wall.health import STRUCTURAL, TRANSIENT, classify


def _lock_error():
    return duckdb.IOException(
        'IO Error: Cannot open file "wall_scan_results.duckdb": '
        "The process cannot access the file because it is being used by another process."
    )


@pytest.mark.parametrize("exc, expected", [
    (_lock_error(), TRANSIENT),
    (duckdb.ConnectionException("different configuration than existing connections"), TRANSIENT),
    (requests.ConnectionError("upstox unreachable"), TRANSIENT),
    (duckdb.ConstraintException('Duplicate key "trade_id: 1" violates primary key constraint'), STRUCTURAL),
    (duckdb.CatalogException("Table with name trades does not exist!"), STRUCTURAL),
    (ZeroDivisionError("float division by zero"), STRUCTURAL),
    (TypeError("<lambda>() takes 5 positional arguments but 6 were given"), STRUCTURAL),
    (KeyError("max_loss"), STRUCTURAL),
])
def test_classify(exc, expected):
    assert classify(exc) == expected


def test_unknown_exception_is_structural():
    class Weird(Exception):
        pass
    assert classify(Weird("never seen before")) == STRUCTURAL


def test_io_error_that_is_not_the_lock_is_structural():
    assert classify(duckdb.IOException("IO Error: disk full")) == STRUCTURAL


from datetime import datetime

from core.options_wall.health import StepHealth


def _at(minute):
    return datetime(2026, 9, 7, 10, minute, 0)


def test_structural_alerts_once_and_only_once():
    h = StepHealth()
    exc = duckdb.ConstraintException("Duplicate key")
    verdicts = [h.record("executor", "NIFTY", exc, now=_at(i % 60)) for i in range(101)]
    assert sum(1 for v in verdicts if v.alert) == 1
    assert verdicts[0].alert is True
    assert verdicts[0].level == "error"
    assert verdicts[-1].record["consecutive"] == 101


def test_success_clears_and_rearms():
    h = StepHealth()
    exc = duckdb.ConstraintException("Duplicate key")
    assert h.record("executor", "NIFTY", exc, now=_at(0)).alert is True
    assert h.record("executor", "NIFTY", exc, now=_at(1)).alert is False
    assert h.record("executor", "NIFTY", None, now=_at(2)).ok is True
    assert h.record("executor", "NIFTY", exc, now=_at(3)).alert is True


def test_since_pins_to_the_first_failure():
    h = StepHealth()
    exc = duckdb.ConstraintException("Duplicate key")
    h.record("executor", "NIFTY", exc, now=_at(10))
    v = h.record("executor", "NIFTY", exc, now=_at(30))
    assert v.record["since"] == "2026-09-07T10:10:00"


def test_transient_waits_for_the_tenth_cycle():
    h = StepHealth()
    exc = duckdb.ConnectionException("lock")
    verdicts = [h.record("scan_persist", "NIFTY", exc, now=_at(i)) for i in range(12)]
    assert [i for i, v in enumerate(verdicts) if v.alert] == [9]
    assert verdicts[0].level == "warning"


def test_close_request_alerts_on_the_first_transient_failure():
    h = StepHealth()
    v = h.record("close_request", "NIFTY", duckdb.ConnectionException("lock"), now=_at(0))
    assert v.alert is True
    assert v.kind == "transient"


def test_steps_and_underlyings_are_tracked_independently():
    h = StepHealth()
    h.record("executor", "NIFTY", duckdb.ConstraintException("x"), now=_at(0))
    h.record("executor", "SENSEX", None, now=_at(0))
    snap = h.snapshot()
    assert snap["NIFTY"]["executor"]["ok"] is False
    assert snap["SENSEX"]["executor"]["ok"] is True
    assert h.any_failing() is True


def test_any_failing_false_when_everything_succeeded():
    h = StepHealth()
    h.record("executor", "NIFTY", None, now=_at(0))
    assert h.any_failing() is False
