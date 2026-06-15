"""
Broker-position DTO (MM7J.2, Route R1).

A broker's positions line (`GET /v2/portfolio/short-term-positions`) is documented
to carry `instrument_token` (e.g. `NSE_FO|79381`), expected byte-identical to the
internal ledger key — but this is NOT yet live-verified: no non-empty position
payload has been captured (see `docs/reports/UPSTOX_CANONICAL_API_MAP.md`). The execution
`Position` model is deliberately broker-identity-free (the G1 boundary —
`instrument_key`/token handling must NOT live in `core/execution/`). `BrokerPosition`
is the broker-layer carrier: it IS-A `Position` (so it remains a drop-in for the
`BrokerAdapter.get_positions() -> Dict[str, Position]` contract and the reconcile
shape adapter) and adds the broker-only `instrument_token`, kept here in
`core/brokers/` where broker identity is legal.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.execution.position_models import Position, PositionSide
from core.instruments.instrument_base import Instrument


@dataclass(frozen=True, init=False)
class BrokerPosition(Position):
    """A `Position` annotated with the broker's `instrument_token` (ledger key)."""
    instrument_token: Optional[str] = None

    def __init__(
        self,
        instrument: Optional[Instrument] = None,
        *,
        symbol: Optional[str] = None,
        side: PositionSide = PositionSide.FLAT,
        quantity: float = 0.0,
        avg_price: float = 0.0,
        last_updated: Optional[datetime] = None,
        instrument_token: Optional[str] = None,
    ):
        super().__init__(
            instrument,
            symbol=symbol,
            side=side,
            quantity=quantity,
            avg_price=avg_price,
            last_updated=last_updated,
        )
        object.__setattr__(self, "instrument_token", instrument_token)
