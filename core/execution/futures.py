"""
Future resolution — G1 Wave 2 Migration #1.

Routes a futures-style signal symbol through the canonical instrument master
(`InstrumentResolver.resolve_future`) and derives the legacy `Future` identity
from the returned `CanonicalInstrument`, keeping the broker-facing `symbol`
byte-identical.

G1 / 4C.7 boundary: the `CanonicalInstrument` is the identity *source* but stays
internal — only its economic facts (expiry, lot_size, underlying) are read to
build the legacy `Future`. The canonical object never reaches persistence, the
broker payload, or `NormalizedOrder`.

Determinism (ADR-003): the FUTURE *type* is decided by the symbol shape, not by
master presence. When the master is absent (`resolve_future` -> None) a `Future`
is still derived from the symbol-parsed fields, so the order type never flips on
DB presence.
"""
import re
from datetime import date, datetime
from typing import Optional, Union

from core.instruments.future import Future
from core.instruments.resolver import InstrumentResolver

# NSE monthly future symbol: {UNDERLYING}{YY}{MON}FUT  e.g. NIFTY26JUNFUT
_FUTURE_REGEX = re.compile(r"^([A-Z]+)(\d{2})([A-Z]{3})FUT$")


def resolve_future(
    symbol: str,
    timestamp: Union[datetime, date],
    resolver: Optional[InstrumentResolver] = None,
) -> Optional[Future]:
    """Derive a legacy `Future` for a futures-style symbol, else None (not a future)."""
    match = _FUTURE_REGEX.match(symbol)
    if not match:
        return None

    underlying, yy, mon = match.groups()
    as_of = timestamp.date() if isinstance(timestamp, datetime) else timestamp

    ci = (resolver or InstrumentResolver()).resolve_future(underlying, as_of=as_of)
    if ci is not None:
        return Future(
            symbol=symbol,
            underlying=ci.underlying or underlying,
            expiry=ci.expiry,
            multiplier=float(ci.lot_size),
        )

    # Master absent: keep the FUTURE type (ADR-003) with symbol-parsed expiry.
    expiry = datetime.strptime(f"01{mon}{yy}", "%d%b%y").date()
    return Future(symbol=symbol, underlying=underlying, expiry=expiry, multiplier=1.0)
