"""GATE C — Carry strategy fixture tests.

Verifies the strategy emits the correct formation-date intents from facts.
"""
import sys
from datetime import date, datetime
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.events import OHLCVBar
from core.strategies.carry_strategy import CarryStrategy


@pytest.fixture
def facts_db(tmp_path):
    """Create a mini facts DB with 2 formation dates."""
    db = tmp_path / "facts.duckdb"
    con = duckdb.connect(str(db))
    con.execute("""
        CREATE TABLE carry_facts (
            formation_date DATE, underlying VARCHAR, sector VARCHAR,
            z_carry DOUBLE, z_carry_neut DOUBLE, quintile TINYINT,
            eligible BOOLEAN,
            PRIMARY KEY (formation_date, underlying)
        )
    """)
    rows = [
        (date(2020, 1, 31), "ABC", None, 0.5, 0.48, 5, True),
        (date(2020, 1, 31), "DEF", None, -0.3, -0.31, 1, True),
        (date(2020, 1, 31), "GHI", None, 0.1, 0.11, 3, True),
        (date(2020, 2, 28), "ABC", None, 0.7, 0.68, 5, True),
        (date(2020, 2, 28), "DEF", None, -0.5, -0.51, 1, True),
    ]
    con.executemany(
        "INSERT INTO carry_facts VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(str(r[0]), *r[1:]) for r in rows],
    )
    con.close()
    yield db


def test_loads_formation_dates(facts_db):
    strategy = CarryStrategy(str(facts_db))
    strategy.on_start()
    assert date(2020, 1, 31) in strategy._formation_dates
    assert date(2020, 2, 28) in strategy._formation_dates
    assert len(strategy._formation_dates) == 2


def test_emits_on_formation_date(facts_db):
    strategy = CarryStrategy(str(facts_db))
    strategy.on_start()

    bar = OHLCVBar(
        symbol="NIFTY",
        timestamp=datetime(2020, 1, 31, 15, 30),
        open=100, high=101, low=99, close=100.5, volume=10000,
    )
    signals = strategy.on_bar(bar)
    assert len(signals) == 1
    assert signals[0].metadata["rebalance"] is True
    assert signals[0].metadata["formation_date"] == "2020-01-31"
    assert signals[0].strategy_id == "carry"


def test_no_emit_on_non_formation(facts_db):
    strategy = CarryStrategy(str(facts_db))
    strategy.on_start()

    bar = OHLCVBar(
        symbol="NIFTY",
        timestamp=datetime(2020, 1, 15, 15, 30),
        open=100, high=101, low=99, close=100.5, volume=10000,
    )
    signals = strategy.on_bar(bar)
    assert signals == []


def test_no_duplicate_emit_same_formation(facts_db):
    strategy = CarryStrategy(str(facts_db))
    strategy.on_start()

    dt = datetime(2020, 1, 31, 15, 30)
    bar = OHLCVBar(symbol="NIFTY", timestamp=dt,
                   open=100, high=101, low=99, close=100.5, volume=10000)
    s1 = strategy.on_bar(bar)
    assert len(s1) == 1
    s2 = strategy.on_bar(bar)
    assert s2 == []
