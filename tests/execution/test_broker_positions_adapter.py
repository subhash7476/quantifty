"""
MM.7A — W2 characterization: the broker-positions shape contract the future
reconciliation adapter (PROJECT_STATE.md Planned #6) must satisfy.

The driver's `broker_positions` callable and the reconciliation engine expect
`List[Dict]` with `{symbol, quantity, side}` where `side` is a STRING
('LONG'/'SHORT'); the broker adapter returns `Dict[str, Position]` with `side` a
`PositionSide` ENUM and `quantity` already absolute (upstox_adapter.py:126-152;
reconciliation.py:24,46-52). So `broker.get_positions` CANNOT be injected
directly — an adapter must (1) listify, (2) stringify `side`, (3) preserve the
sign convention reconcile re-derives from `side`.

This file pins that CONTRACT — it implements no production adapter. It documents
the two-ended mismatch, proves the naive pass-through (enum `side`) breaks
reconcile, and proves a correct bridge preserves LONG / SHORT / FLAT semantics.
(`tests/execution/test_reconciliation_broker.py` covers the Phase-0 end-to-end
flow with the same test glue; this file pins the shape/type contract itself,
including the enum-vs-string trap and the FLAT case that file does not.)
"""

from datetime import datetime

import pytest

from core.brokers.upstox_adapter import UpstoxAdapter
from core.clock import ReplayClock
from core.execution.broker_positions_adapter import to_reconcile_positions
from core.execution.position_models import Position, PositionSide
from core.execution.position_tracker import PositionTracker
from core.execution.reconciliation import ReconciliationEngine
from core.instruments.equity import Equity


def _adapter(payload):
    a = UpstoxAdapter("key", "secret", "token",
                      ReplayClock(datetime(2026, 1, 1, 9, 15)))
    a._make_request = lambda *args, **kwargs: payload
    return a


def _payload(rows):
    return {"status": "success", "data": rows}


def _bridge(adapter):
    """MM7H #6b.1: the production shape adapter now owns this transform. Repointed
    from local glue to `to_reconcile_positions` so this net exercises the real
    function end-to-end through the UpstoxAdapter shape."""
    return to_reconcile_positions(adapter.get_positions())


# --------------------------------------------------------------------------- #
# The two-ended shape mismatch (W2): the broker yields a dict; reconcile needs a
# list — they cannot be the same object.
# --------------------------------------------------------------------------- #
def test_adapter_returns_dict_reconcile_needs_list():
    adapter = _adapter(_payload([
        {"trading_symbol": "RELIANCE", "quantity": "10", "average_price": "2500.5"},
    ]))
    positions = adapter.get_positions()
    assert isinstance(positions, dict)                 # broker shape
    assert all(isinstance(v, Position) for v in positions.values())
    # The bridge turns it into reconcile()'s shape.
    bridged = _bridge(adapter)
    assert isinstance(bridged, list)
    assert set(bridged[0].keys()) == {"symbol", "quantity", "side"}


# --------------------------------------------------------------------------- #
# The field-type mismatch (W2): broker `side` is a PositionSide enum, reconcile
# wants a string. The naive pass-through (enum side) breaks reconcile, proving an
# adapter is required, not optional.
# --------------------------------------------------------------------------- #
def test_position_side_is_enum_not_string():
    adapter = _adapter(_payload([
        {"trading_symbol": "TCS", "quantity": "-5", "average_price": "3500.0"},
    ]))
    pos = adapter.get_positions()["TCS"]
    assert isinstance(pos.side, PositionSide)          # NOT a str
    assert pos.side.value == "SHORT"                   # the string the bridge must emit


def test_naive_passthrough_with_enum_side_breaks_reconcile():
    engine = ReconciliationEngine(PositionTracker())
    # Naive pass-through: side left as the enum object (what NOT to inject).
    naive = [{"symbol": "TCS", "quantity": 5.0, "side": PositionSide.SHORT}]
    with pytest.raises(AttributeError):
        engine.reconcile(naive)                        # enum has no .upper()


# --------------------------------------------------------------------------- #
# A correct bridge preserves reconciliation semantics: LONG / SHORT / FLAT.
# --------------------------------------------------------------------------- #
def test_bridge_long_matches_internal_no_alert():
    internal = PositionTracker()
    internal._positions["RELIANCE"] = Position(
        instrument=Equity("RELIANCE"), side=PositionSide.LONG,
        quantity=10, avg_price=2500.0)
    engine = ReconciliationEngine(internal)

    adapter = _adapter(_payload([
        {"trading_symbol": "RELIANCE", "quantity": "10", "average_price": "2500.5"},
    ]))
    assert engine.reconcile(_bridge(adapter)) == []


def test_bridge_short_orphan_detected_with_signed_value():
    engine = ReconciliationEngine(PositionTracker())   # empty internal book
    adapter = _adapter(_payload([
        {"trading_symbol": "TCS", "quantity": "-5", "average_price": "3500.0"},
    ]))
    alerts = engine.reconcile(_bridge(adapter))
    assert len(alerts) == 1
    assert alerts[0].issue == "ORPHANED_BROKER_POSITION"
    # SHORT survived the string round-trip and was re-signed negative.
    assert alerts[0].broker_value == -5.0


def test_bridge_flat_zero_quantity_produces_no_alert():
    engine = ReconciliationEngine(PositionTracker())   # empty internal book
    adapter = _adapter(_payload([
        {"trading_symbol": "INFY", "quantity": "0", "average_price": "1500.0"},
    ]))
    bridged = _bridge(adapter)
    assert bridged[0]["side"] == "FLAT"
    # A flat broker position is not an orphan (abs(qty) == 0).
    assert engine.reconcile(bridged) == []
