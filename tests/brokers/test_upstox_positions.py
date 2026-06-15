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
with a stub returning canned positions payloads. No network.
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


# --------------------------------------------------------------------------- #
# MM7J.2 — instrument_token preservation (Route R1). Upstox documentation suggests
# the positions payload (GET /v2/portfolio/short-term-positions) carries
# instrument_token = NSE_FO|<token>, expected byte-identical to the ledger key — but
# live verification is still PENDING (no non-empty payload captured; see
# docs/reports/UPSTOX_CANONICAL_API_MAP.md). get_positions() must retain it on the
# returned position so downstream reconciliation can key on it — WITHOUT changing the
# dict key, any existing Position field, or any other observable behavior.
# --------------------------------------------------------------------------- #

def test_get_positions_preserves_instrument_token():
    """A derivative positions line carrying instrument_token surfaces it on
    the returned broker position (NSE_FO|<token>, the ledger namespace)."""
    adapter = _adapter({
        "status": "success",
        "data": [
            {"instrument_token": "NSE_FO|79381",
             "trading_symbol": "NIFTY26JAN2623500CE", "quantity": "75",
             "average_price": "120.5"},
        ],
    })

    positions = adapter.get_positions()

    # dict KEY is unchanged — still the trading_symbol (no re-key this slice)
    assert "NIFTY26JAN2623500CE" in positions
    pos = positions["NIFTY26JAN2623500CE"]
    # the token rides on the position, in the ledger namespace
    assert pos.instrument_token == "NSE_FO|79381"


def test_get_positions_with_token_leaves_existing_fields_unchanged():
    """Preserving instrument_token does not perturb side / quantity / avg_price /
    symbol, and the position is still a Position (base.py contract holds)."""
    adapter = _adapter({
        "status": "success",
        "data": [
            {"instrument_token": "NSE_FO|79381",
             "trading_symbol": "NIFTY26JAN2623500CE", "quantity": "-50",
             "average_price": "88.0"},
        ],
    })

    pos = adapter.get_positions()["NIFTY26JAN2623500CE"]

    assert isinstance(pos, Position)
    assert pos.symbol == "NIFTY26JAN2623500CE"
    assert pos.side == PositionSide.SHORT
    assert pos.quantity == 50.0
    assert pos.avg_price == 88.0


def test_get_positions_token_absent_is_none_no_behavior_change():
    """A line WITHOUT instrument_token (today's equity payload shape) behaves
    exactly as before — keyed on trading_symbol, valid Position — and the token
    attribute is simply None. Proves no runtime behavior change on the legacy path."""
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
    assert pos.instrument_token is None


def test_get_positions_with_token_still_shapes_for_reconcile():
    """The token-bearing position still passes cleanly through the production
    shape adapter (to_reconcile_positions reads .side/.quantity) — proving the DTO
    stays a drop-in for the existing reconcile path."""
    from core.execution.broker_positions_adapter import to_reconcile_positions

    adapter = _adapter({
        "status": "success",
        "data": [
            {"instrument_token": "NSE_FO|79381",
             "trading_symbol": "NIFTY26JAN2623500CE", "quantity": "75",
             "average_price": "120.5"},
        ],
    })

    out = to_reconcile_positions(adapter.get_positions())

    assert out == [{"symbol": "NIFTY26JAN2623500CE", "quantity": 75.0,
                    "side": "LONG"}]
