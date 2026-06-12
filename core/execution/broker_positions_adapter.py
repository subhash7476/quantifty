"""
Broker-position shape adapter (MM7H #6b.1).

The reconciliation engine consumes `List[Dict]` with `{symbol, quantity, side}`
where `side` is a STRING ('LONG'/'SHORT'/'FLAT') and `quantity` is unsigned —
reconcile() re-derives the sign from `side` (reconciliation.py:42-51). Every
`BrokerAdapter.get_positions()` returns `Dict[str, Position]` with `side` a
`PositionSide` ENUM and `quantity` already absolute (base.py:27). The two ends do
not share a type — a naive pass-through raises inside reconcile() (the enum has no
.upper()).

`to_reconcile_positions` is the SHAPE bridge between them, and only that:
dict -> list, `pos.side.value` -> string, `pos.quantity` carried through (already
absolute). The symbol KEY is passed through UNCHANGED — this function performs NO
symbol-namespace translation (broker `trading_symbol` vs the internal ledger key
is #6b.2 / MM7G). Keep it a pure function so the composition root (#6b.3) can wire
it as `broker_positions=lambda: to_reconcile_positions(broker.get_positions())`.
"""
from typing import Any, Dict, List

from core.execution.position_models import Position


def to_reconcile_positions(positions: Dict[str, Position]) -> List[Dict[str, Any]]:
    """Map a broker's `Dict[str, Position]` to reconcile()'s `List[Dict]` shape.

    Shape-only: the dict key becomes `symbol` verbatim (no namespace mapping),
    `side` is stringified via the enum value, `quantity` is left absolute.
    """
    return [
        {"symbol": symbol, "quantity": pos.quantity, "side": pos.side.value}
        for symbol, pos in positions.items()
    ]
