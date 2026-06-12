"""
Phase 0 hygiene — reconciliation consumes broker positions without model errors.

Discovery finding (PORTFOLIO_STATE_DISCOVERY.md §4.5): broker reconciliation was
impossible because the only broker-position read crashed at Position construction.
With that defect fixed, the broker's reported positions can be normalized to the
reconcile() dict contract (symbol/quantity/side) and diffed against the internal
ledger. These tests prove the end-to-end flow runs without a model error and detects
a known divergence.

The bridge from the adapter's Dict[str, Position] to reconcile()'s List[Dict] shape
is performed here in test glue — wiring a live broker-reconciliation feed is a
separate planned item (PROJECT_STATE.md Planned #6), out of scope for Phase 0.
"""

from datetime import datetime

from core.brokers.upstox_adapter import UpstoxAdapter
from core.clock import ReplayClock
from core.execution.broker_positions_adapter import to_reconcile_positions
from core.execution.position_tracker import PositionTracker
from core.execution.position_models import Position, PositionSide
from core.execution.reconciliation import ReconciliationEngine
from core.instruments.equity import Equity


def _broker_positions_as_dicts(adapter):
    """MM7H #6b.1: repointed to the production `to_reconcile_positions` (the shape
    transform now has a single home — adapter's Dict[str, Position] -> reconcile()'s
    List[Dict])."""
    return to_reconcile_positions(adapter.get_positions())


def _adapter(payload):
    adapter = UpstoxAdapter("key", "secret", "token",
                            ReplayClock(datetime(2026, 1, 1, 9, 15)))
    adapter._make_request = lambda *args, **kwargs: payload
    return adapter


def test_reconcile_consumes_broker_positions_consistent():
    """Internal long 10 == broker long 10 -> no alerts, no model error."""
    internal = PositionTracker()
    internal._positions["RELIANCE"] = Position(
        instrument=Equity("RELIANCE"), side=PositionSide.LONG,
        quantity=10, avg_price=2500.0)
    engine = ReconciliationEngine(internal)

    adapter = _adapter({
        "status": "success",
        "data": [{"trading_symbol": "RELIANCE", "quantity": "10",
                  "average_price": "2500.5"}],
    })

    alerts = engine.reconcile(_broker_positions_as_dicts(adapter))

    assert alerts == []


def test_reconcile_detects_quantity_mismatch_from_broker():
    """Internal long 10 vs broker long 5 -> one QUANTITY_MISMATCH alert."""
    internal = PositionTracker()
    internal._positions["RELIANCE"] = Position(
        instrument=Equity("RELIANCE"), side=PositionSide.LONG,
        quantity=10, avg_price=2500.0)
    engine = ReconciliationEngine(internal)

    adapter = _adapter({
        "status": "success",
        "data": [{"trading_symbol": "RELIANCE", "quantity": "5",
                  "average_price": "2500.5"}],
    })

    alerts = engine.reconcile(_broker_positions_as_dicts(adapter))

    assert len(alerts) == 1
    assert alerts[0].issue == "QUANTITY_MISMATCH"
    assert alerts[0].internal_value == 10.0
    assert alerts[0].broker_value == 5.0


def test_reconcile_flags_orphaned_short_broker_position():
    """A net-short broker position with no internal counterpart is flagged,
    proving short normalization survives end-to-end into reconcile()."""
    engine = ReconciliationEngine(PositionTracker())  # empty internal book

    adapter = _adapter({
        "status": "success",
        "data": [{"trading_symbol": "TCS", "quantity": "-5",
                  "average_price": "3500.0"}],
    })

    alerts = engine.reconcile(_broker_positions_as_dicts(adapter))

    assert len(alerts) == 1
    assert alerts[0].issue == "ORPHANED_BROKER_POSITION"
    assert alerts[0].broker_value == -5.0
