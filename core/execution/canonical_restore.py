"""
G1 Wave 3 — restore canonicalization primitive (Option B post-gate pass).

Given a restored ledger entry's display `symbol`, derive the canonical-sourced
legacy identity (`Future`/`Option`) by resolving through the `InstrumentResolver`
and reading only the economic facts (expiry / lot_size / underlying) — the
`CanonicalInstrument` stays internal (the G1 / 4C.7 boundary). Returns None for a
non-derivative (equity) or an unresolved symbol, so the caller leaves the legacy
identity in place (carve-out).

Futures detection + derivation is the same forward path Wave 2 #1 already uses
(`core/execution/futures.resolve_future`): a futures-shaped symbol always yields
a `Future` (master-absent still derives, ADR-003). Options are detected by the
NSE option symbol shape and resolved for their master lot; when the master does
not carry the contract the legacy identity is kept (None), so nothing flips on a
missing master.
"""
import re
from datetime import date, datetime
from typing import Optional, Union

from core.execution.futures import resolve_future
from core.instruments.instrument_base import Instrument
from core.instruments.option import Option, OptionType
from core.instruments.resolver import InstrumentResolver

# NSE option symbol: {UNDERLYING}{DD}{MON}{YY}{STRIKE}{CE|PE}  e.g. NIFTY16JUN2622500CE
_OPTION_REGEX = re.compile(r"^([A-Z]+)(\d{2})([A-Z]{3})(\d{2})(\d+)(CE|PE)$")


def canonicalize_symbol(
    symbol: str,
    timestamp: Union[datetime, date],
    resolver: Optional[InstrumentResolver] = None,
) -> Optional[Instrument]:
    """Canonical-derived legacy `Future`/`Option` for a derivative symbol, else None."""
    future = resolve_future(symbol, timestamp, resolver)
    if future is not None:
        return future
    return _resolve_option(symbol, timestamp, resolver)


def _resolve_option(
    symbol: str,
    timestamp: Union[datetime, date],
    resolver: Optional[InstrumentResolver],
) -> Optional[Option]:
    match = _OPTION_REGEX.match(symbol)
    if not match:
        return None
    underlying, day, mon, yy, strike, opt_type = match.groups()
    expiry = datetime.strptime(f"{day}{mon}{yy}", "%d%b%y").date()
    strike_price = float(strike)
    option_type = OptionType(opt_type)
    as_of = timestamp.date() if isinstance(timestamp, datetime) else timestamp

    ci = (resolver or InstrumentResolver()).resolve_option(
        underlying, expiry, strike_price, option_type, as_of=as_of)
    if ci is None:
        return None
    return Option(
        symbol=symbol,
        underlying=underlying,
        expiry=expiry,
        strike=strike_price,
        option_type=option_type,
        lot_size=ci.lot_size,
        multiplier=1.0,
    )
