"""NiftyShield — execution group assembly (Decomposition Spec §3.3, D5).

Assembles the per-leg SignalEvents that share a `group_id` into one OrderGroup
so execution owns the structure as a unit (STRADDLE/STRANGLE/SPREAD/
IRON_CONDOR/CUSTOM). Leg instruments are resolved at the execution boundary
from the source-named strike/expiry/option_type — the source never builds a
tradable instrument (ADR-016); this service does, against the instrument layer.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from core.events import SignalEvent, SignalType
from core.execution.groups.order_group import OrderGroup, OrderGroupType
from core.execution.order_models import NormalizedOrder, OrderMetadata, OrderSide, OrderType
from core.instruments.instrument_base import InstrumentType
from core.instruments.option import Option, OptionType
from core.instruments.resolver import InstrumentResolver

STRUCTURE_TO_GROUP_TYPE = {
    "short_straddle": OrderGroupType.STRADDLE,
    "short_strangle": OrderGroupType.STRANGLE,
    "bull_put_spread": OrderGroupType.SPREAD,
    "bear_call_spread": OrderGroupType.SPREAD,
    "iron_fly": OrderGroupType.IRON_CONDOR,
}


def group_type_for(structure: str) -> OrderGroupType:
    return STRUCTURE_TO_GROUP_TYPE.get(structure, OrderGroupType.CUSTOM)


def _resolve_option(signal: SignalEvent, underlying: str,
                    default_lot_size: int,
                    resolver: Optional[InstrumentResolver],
                    as_of: Optional[date]) -> Option:
    md = signal.metadata
    expiry = date.fromisoformat(md["expiry"])
    strike = float(md["strike"])
    option_type = OptionType(md["option_type"])
    lot_size = default_lot_size
    if resolver is not None:
        ci = resolver.resolve_option(underlying, expiry, strike, option_type,
                                     as_of=as_of)
        if ci is not None:
            lot_size = ci.lot_size
    return Option(
        symbol=signal.symbol,
        underlying=underlying,
        expiry=expiry,
        strike=strike,
        option_type=option_type,
        lot_size=lot_size,
        multiplier=1.0,
    )


def build_leg_order(signal: SignalEvent, underlying: str, lots: int,
                    lot_size: int, *,
                    resolver: Optional[InstrumentResolver] = None,
                    as_of: Optional[date] = None) -> NormalizedOrder:
    """Turn one leg SignalEvent into a NormalizedOrder inside the group."""
    instrument = _resolve_option(signal, underlying, lot_size, resolver, as_of)
    side = OrderSide.SELL if signal.signal_type is SignalType.SELL else OrderSide.BUY
    group_id = UUID(signal.metadata["group_id"])
    return NormalizedOrder(
        instrument=instrument,
        side=side,
        quantity=lots * instrument.lot_size,
        order_type=OrderType.MARKET,
        strategy_id=signal.strategy_id,
        signal_id=signal.strategy_id,   # journaling key; per-leg via metadata below
        timestamp=signal.timestamp,
        group_id=group_id,
        metadata=OrderMetadata(
            original_confidence=signal.confidence,
            strategy_metadata=dict(signal.metadata),
        ),
    )


def assemble_group(signals: List[SignalEvent], underlying: str, lots: int,
                   lot_size: int, *,
                   resolver: Optional[InstrumentResolver] = None,
                   as_of: Optional[date] = None) -> OrderGroup:
    """Assemble the legs sharing a group_id into one OrderGroup.

    Raises ValueError if the signals do not share a single group_id or
    structure (a malformed leg set must fail loudly at the execution boundary).
    """
    if not signals:
        raise ValueError("assemble_group: no leg signals")
    group_ids = {s.metadata["group_id"] for s in signals}
    structures = {s.metadata["structure"] for s in signals}
    if len(group_ids) != 1:
        raise ValueError(f"assemble_group: legs span {len(group_ids)} group_ids")
    if len(structures) != 1:
        raise ValueError(f"assemble_group: legs span {len(structures)} structures")

    group_id = UUID(next(iter(group_ids)))
    structure = next(iter(structures))
    legs = [build_leg_order(s, underlying, lots, lot_size,
                            resolver=resolver, as_of=as_of) for s in signals]
    group = OrderGroup(group_type=group_type_for(structure), legs=legs)
    group.group_id = group_id
    return group
