"""
Phase 0 hygiene — UpstoxAdapter.get_positions() Position-constructor mismatch.

Discovery finding (PORTFOLIO_STATE_DISCOVERY.md §4.5): get_positions() built
Position(symbol=..., quantity=..., avg_entry_price=..., last_update=...) but the
Position model accepts avg_price / last_updated (position_models.py) -> TypeError at
runtime, making the only broker-position read unusable. These tests prove valid
Position objects are produced, that a net-short broker line is normalized to
side=SHORT with a positive absolute quantity, and that the error/non-success paths
still return {} (existing behavior unchanged).

The broker HTTP boundary (_make_request) is the one unavoidable seam; it is replaced
with a stub returning canned net-positions payloads. No network.
"""

from datetime import datetime

from core.brokers.upstox_adapter import UpstoxAdapter
from core.execution.position_models import Position, PositionSide
from core.clock import ReplayClock


def _adapter(payload):
    adapter = UpstoxAdapter("key", "secret", "token",
                            ReplayClock(datetime(2026, 1, 1, 9, 15)))
    adapter._make_request = lambda *args, **kwargs: payload
    return adapter


def test_get_positions_builds_valid_long_position():
    adapter = _adapter({
        "status": "success",
        "data": [
            {"trading_symbol": "RELIANCE", "quantity": "10",
             "average_price": "2500.5"},
        ],
    })

    positions = adapter.get_positions()

    assert "RELIANCE" in positions
    pos = positions["RELIANCE"]
    assert isinstance(pos, Position)
    assert pos.quantity == 10.0
    assert pos.avg_price == 2500.5
    assert pos.side == PositionSide.LONG


def test_get_positions_normalizes_short_to_abs_quantity():
    """A net-short broker line (negative quantity) becomes side=SHORT with a
    positive absolute quantity — a valid Position per the model contract."""
    adapter = _adapter({
        "status": "success",
        "data": [
            {"trading_symbol": "TCS", "quantity": "-5",
             "average_price": "3500.0"},
        ],
    })

    pos = adapter.get_positions()["TCS"]

    assert pos.side == PositionSide.SHORT
    assert pos.quantity == 5.0
    assert pos.avg_price == 3500.0


def test_get_positions_returns_empty_on_non_success():
    adapter = _adapter({"status": "error", "data": []})

    assert adapter.get_positions() == {}


def test_get_positions_returns_empty_on_exception():
    adapter = UpstoxAdapter("key", "secret", "token",
                            ReplayClock(datetime(2026, 1, 1, 9, 15)))

    def _boom(*args, **kwargs):
        raise RuntimeError("broker transport down")

    adapter._make_request = _boom

    assert adapter.get_positions() == {}
