"""
MM.7H #6b.1 — unit acceptance for the broker-position SHAPE adapter,
`core.execution.broker_positions_adapter.to_reconcile_positions`.

The adapter performs ONLY the shape transform the reconciliation engine requires
(MM7F F1 / MM7G §0): `Dict[str, Position]` -> `List[Dict]`, enum `side` ->
string `side`, with `quantity` (already absolute) and the symbol KEY passed
through UNCHANGED. It does NOT translate the symbol namespace (that is #6b.2) and
touches no reconciliation/broker code.

These tests pin the function's contract directly. The MM7A net
(`test_broker_positions_adapter.py`), the Phase-0 net
(`test_reconciliation_broker.py`), and the MM7G namespace net
(`test_reconcile_symbol_namespace.py`) additionally exercise it end-to-end
through the real `UpstoxAdapter` shape once their glue is repointed at it.
"""

from core.execution.broker_positions_adapter import to_reconcile_positions
from core.execution.position_models import Position, PositionSide
from core.instruments.equity import Equity


def _pos(symbol, side, quantity):
    return Position(instrument=Equity(symbol), side=side, quantity=quantity,
                    avg_price=100.0)


# --------------------------------------------------------------------------- #
# Shape: dict-keyed-by-symbol -> list; each row is exactly {symbol, quantity, side}.
# --------------------------------------------------------------------------- #
def test_listifies_dict_keyed_positions():
    out = to_reconcile_positions({"RELIANCE": _pos("RELIANCE", PositionSide.LONG, 10)})
    assert isinstance(out, list)
    assert len(out) == 1
    assert set(out[0].keys()) == {"symbol", "quantity", "side"}
    assert out[0]["symbol"] == "RELIANCE"


# --------------------------------------------------------------------------- #
# side: PositionSide enum -> its string value (what reconcile().upper()s).
# --------------------------------------------------------------------------- #
def test_side_enum_becomes_string():
    out = to_reconcile_positions({"TCS": _pos("TCS", PositionSide.SHORT, 5)})
    assert out[0]["side"] == "SHORT"
    assert isinstance(out[0]["side"], str)


# --------------------------------------------------------------------------- #
# quantity: passed through unchanged (already absolute; reconcile re-signs).
# --------------------------------------------------------------------------- #
def test_quantity_stays_absolute():
    out = to_reconcile_positions({"TCS": _pos("TCS", PositionSide.SHORT, 5)})
    assert out[0]["quantity"] == 5          # NOT -5 — sign is reconcile's job
    long_out = to_reconcile_positions({"INFY": _pos("INFY", PositionSide.LONG, 7)})
    assert long_out[0]["quantity"] == 7


# --------------------------------------------------------------------------- #
# FLAT / zero qty round-trips to the "FLAT" string with quantity 0.
# --------------------------------------------------------------------------- #
def test_flat_zero_qty_round_trips():
    out = to_reconcile_positions({"INFY": _pos("INFY", PositionSide.FLAT, 0.0)})
    assert out[0]["side"] == "FLAT"
    assert out[0]["quantity"] == 0.0


# --------------------------------------------------------------------------- #
# Empty book -> empty list (vacuous reconcile input, not an error).
# --------------------------------------------------------------------------- #
def test_empty_book_yields_empty_list():
    assert to_reconcile_positions({}) == []


# --------------------------------------------------------------------------- #
# The symbol KEY is carried through verbatim — NO namespace mapping (#6b.2).
# A broker trading_symbol stays a broker trading_symbol.
# --------------------------------------------------------------------------- #
def test_symbol_key_passes_through_unchanged():
    out = to_reconcile_positions(
        {"NIFTY26JAN2623500CE": _pos("NIFTY26JAN2623500CE", PositionSide.LONG, 50)})
    assert out[0]["symbol"] == "NIFTY26JAN2623500CE"


# --------------------------------------------------------------------------- #
# Multiple positions all transform; order follows dict iteration.
# --------------------------------------------------------------------------- #
def test_multiple_positions_all_transform():
    out = to_reconcile_positions({
        "RELIANCE": _pos("RELIANCE", PositionSide.LONG, 10),
        "TCS": _pos("TCS", PositionSide.SHORT, 5),
    })
    by_symbol = {r["symbol"]: r for r in out}
    assert by_symbol["RELIANCE"]["side"] == "LONG"
    assert by_symbol["RELIANCE"]["quantity"] == 10
    assert by_symbol["TCS"]["side"] == "SHORT"
    assert by_symbol["TCS"]["quantity"] == 5
