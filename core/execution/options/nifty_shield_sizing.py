"""NiftyShield — execution sizing (Decomposition Spec D4).

Final lots from the source's declared base_lots / regime_mult / vix_reduce,
clamped to the margin ceiling. Pure + injectable: the margin-query callable
lets unit tests use a fake while production passes a real one.

Rules (datasheet §5a):
  lots = max(1, round(base_lots × regime_mult))
  then −1 if vix_reduce (non-strangle)
  then reduce further while the structure's margin exceeds the ceiling.

Two margin sources are available for the clamp:

- `structure_margin_over_upstox_basket` — the broker's own basket margin for the
  whole structure (`POST /v2/charges/margin`), which is what production uses.
- `structure_margin_over_engine` — per-leg NseMarginEngine, kept for the
  offline/replay paths that have no broker session.

The broker basket is the live sizing input by operator decision (2026-09-08).
This departs from ADR-011/013, which make NseMarginEngine the sole sizing
authority in every mode, and the reason is empirical: with no SPAN snapshot
present the engine degrades to the flat-rate MarginTracker, which priced the
2026-09-07 bear call spread at Rs 4,619 against the broker's Rs 79,902. A
sizing clamp that understates margin 17x is not a conservative approximation of
a broker RMS, it is a gate that cannot fire. The basket call is also the only
figure that carries the spread benefit a hedged structure actually earns —
summing per-leg margins cannot express it.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


class UpstoxMarginUnavailable(RuntimeError):
    """The broker could not price the basket — no token, HTTP error, bad JSON.

    Raised rather than degraded: falling back to the flat-rate engine here would
    reproduce the exact 17x understatement this path exists to remove, and
    would do it silently.
    """

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


def structure_margin_over_upstox_basket(
    legs: List[Dict[str, Any]],
    instrument_keys: Dict[str, str],
    lot_size: int,
    *,
    product: str = "D",
    fetch: Optional[Callable[..., Dict]] = None,
) -> Callable[[int], float]:
    """Build the structure_margin callable from the Upstox basket-margin API.

    One HTTP call per distinct lot count — the whole structure at once, so the
    figure carries the hedge's spread benefit. `margin_clamped_lots` walks lots
    downward and can revisit a count, so results are memoized.

    legs: leg descriptors with 'symbol' and 'side' ('BUY'/'SELL').
    instrument_keys: symbol -> broker instrument_key, from the marks source.
    fetch: injection seam for tests; defaults to the real Upstox call.

    Raises UpstoxMarginUnavailable if a leg has no instrument key or the broker
    cannot price the basket.
    """
    from core.brokers.upstox_margin import fetch_basket_margin
    fetch = fetch or fetch_basket_margin

    missing = [leg["symbol"] for leg in legs
               if not instrument_keys.get(leg["symbol"])]
    if missing:
        raise UpstoxMarginUnavailable(
            f"no broker instrument_key for {', '.join(missing)}")

    cache: Dict[int, float] = {}

    def margin_at(lots: int) -> float:
        if lots not in cache:
            basket = [{"instrument_key": instrument_keys[leg["symbol"]],
                       "quantity": lots * lot_size,
                       "transaction_type": leg["side"]} for leg in legs]
            result = fetch(basket, product=product)
            if result.get("error") or result.get("final") is None:
                raise UpstoxMarginUnavailable(
                    result.get("error") or "broker returned no final margin")
            cache[lots] = float(result["final"])
        return cache[lots]

    return margin_at
