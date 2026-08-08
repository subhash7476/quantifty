"""NiftyShield — execution sizing (Decomposition Spec D4).

Final lots from the source's declared base_lots / regime_mult / vix_reduce,
clamped to the margin ceiling by the margin engine (the sole sizing authority,
ADR-011/013). Pure + injectable: the margin-query callable lets unit tests use
a fake engine while production passes NseMarginEngine.get_incremental_margin.

Rules (datasheet §5a):
  lots = max(1, round(base_lots × regime_mult))
  then −1 if vix_reduce (non-strangle)
  then reduce further while the structure's margin exceeds the ceiling.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

NON_REDUCIBLE_STRUCTURES = ("short_strangle",)


def declared_lots(metadata: Dict[str, Any]) -> int:
    """Lots from the source's declarations, before the margin clamp."""
    base_lots = int(metadata.get("base_lots", 2))
    regime_mult = float(metadata.get("regime_mult", 0.5))
    vix_reduce = bool(metadata.get("vix_reduce", False))
    structure = metadata.get("structure", "")
    lots = max(1, round(base_lots * regime_mult))
    if vix_reduce and structure not in NON_REDUCIBLE_STRUCTURES:
        lots = max(1, lots - 1)
    return lots


def margin_clamped_lots(
    lots: int,
    structure_margin: Callable[[int], float],
    margin_budget: float,
    *,
    min_lots: int = 1,
) -> int:
    """Reduce lots until structure_margin(lots) fits margin_budget.

    structure_margin(lots) returns the structure's total margin (SPAN+ELM) at
    that lot count — the NseMarginEngine is the authority; production wraps
    get_incremental_margin over the structure's legs. Monotone non-decreasing.
    """
    if margin_budget is None or margin_budget <= 0:
        return lots
    while lots > min_lots and structure_margin(lots) > margin_budget:
        lots -= 1
    return lots


def final_lots(
    metadata: Dict[str, Any],
    structure_margin: Callable[[int], float],
    margin_budget: float,
    *,
    min_lots: int = 1,
) -> int:
    """End-to-end: declared lots, then the margin-ceiling clamp."""
    lots = declared_lots(metadata)
    return margin_clamped_lots(lots, structure_margin, margin_budget,
                               min_lots=min_lots)


def structure_margin_over_engine(
    legs: List[Dict[str, Any]],
    margin_engine: Any,
    current_prices: Dict[str, float],
    lot_size: int,
) -> Callable[[int], float]:
    """Build the structure_margin callable from a NseMarginEngine-like object.

    legs: leg descriptors with 'symbol', 'side' ('BUY'/'SELL'), 'option_type'.
    margin_engine: exposes get_incremental_margin(symbol, quantity, price,
        lot_size) -> Rs (NseMarginEngine's signature; tests may fake it).
    current_prices: per-symbol mark the engine prices the short leg against.
    """
    def margin_at(lots: int) -> float:
        total = 0.0
        for leg in legs:
            price = current_prices.get(leg["symbol"])
            if price is None:
                continue
            qty = lots * lot_size
            total += margin_engine.get_incremental_margin(
                leg["symbol"], qty, price, lot_size=lot_size)
        return total

    return margin_at
