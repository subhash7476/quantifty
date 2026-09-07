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
