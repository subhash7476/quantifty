"""
NseMarginEngine (MM10.4) — Calendar Spread Credits + Extreme Loss Margin.

Composition layer wrapping SpanMarginCalculator with spread credit reduction
and ELM. Satisfies MarginCalculator Protocol v2 structurally.
"""

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional

from core.instruments.instrument_base import InstrumentType
from core.risk.span.span_calculator import SpanMarginCalculator
from core.risk.span.span_snapshot import SpanSnapshot

# Intentionally duplicated from span_calculator.py.
#
# Calculator is feature-frozen.
# Engine must not depend on calculator internal helpers.
_SCENARIO_WEIGHTS = (1.0,) * 14 + (0.3, 0.3)


def _derive_contract_scan_risk(ra: tuple) -> float:
    return max(0.0, max(v * w for v, w in zip(ra, _SCENARIO_WEIGHTS)))


def _get_scan_risk(underlying: str, expiry: date, snapshot: SpanSnapshot) -> float:
    contracts = snapshot.futures.get(underlying, ())
    for c in contracts:
        if c.expiry == expiry:
            return _derive_contract_scan_risk(c.ra)
    ra = snapshot.risk_arrays.get(underlying)
    if ra is not None:
        return ra.risk_metrics.get("scan_risk", 0.0)
    return 0.0


class NseMarginEngine:
    """NSE margin engine: SpanMarginCalculator + spread credits + ELM.

    Args:
        span_calc:    Feature-frozen SpanMarginCalculator instance.
        span_snapshot: Immutable SpanSnapshot (same instance passed to span_calc).
        elm_rates:    Dict mapping underlying -> ELM rate fraction (required).
    """

    def __init__(
        self,
        span_calc: SpanMarginCalculator,
        span_snapshot: SpanSnapshot,
        elm_rates: Dict[str, float],
    ):
        self._span_calc = span_calc
        self._snapshot = span_snapshot
        self._elm_rates = dict(elm_rates)

    @property
    def margin_rate(self) -> float:
        return self._span_calc.margin_rate

    @margin_rate.setter
    def margin_rate(self, value: float) -> None:
        self._span_calc.margin_rate = value

    def get_exposure(
        self,
        current_prices: Dict[str, float],
        symbol: Optional[str] = None,
    ) -> float:
        return self._span_calc.get_exposure(current_prices, symbol=symbol)

    def get_used_margin(self, current_prices: Dict[str, float]) -> float:
        span_margin = self._span_calc.get_used_margin(current_prices)
        credit = self._spread_credit(current_prices)
        elm = self._elm_margin(current_prices)
        return max(0.0, span_margin - credit) + elm

    def get_incremental_margin(
        self,
        symbol: str,
        quantity: float,
        price: float,
        lot_size: float = 1.0,
    ) -> float:
        span_incr = self._span_calc.get_incremental_margin(
            symbol, quantity, price, lot_size=lot_size,
        )
        elm_rate = self._resolve_elm_rate(symbol)
        elm_incr = elm_rate * lot_size * abs(quantity) * price
        return span_incr + elm_incr

    def _resolve_elm_rate(self, symbol: str) -> float:
        for underlying, rate in self._elm_rates.items():
            if symbol.startswith(underlying):
                return rate
        return 0.0

    def _elm_margin(self, current_prices: Dict[str, float]) -> float:
        pt = self._span_calc.position_tracker

        underlying_prices: Dict[str, float] = {}
        for sym, pos in pt._positions.items():
            if pos.instrument.type == InstrumentType.FUTURE:
                price = current_prices.get(sym, 0.0)
                if price > 0.0:
                    underlying = pos.instrument.underlying
                    underlying_prices.setdefault(underlying, price)

        total = 0.0
        for sym, pos in pt._positions.items():
            inst = pos.instrument
            itype = inst.type
            if itype not in (InstrumentType.FUTURE, InstrumentType.OPTION):
                continue
            underlying = inst.underlying
            elm_rate = self._elm_rates.get(underlying, 0.0)
            if elm_rate == 0.0:
                continue
            is_option = itype == InstrumentType.OPTION
            is_short = pos.side.name == "SHORT"
            if is_option and not is_short:
                continue

            if itype == InstrumentType.FUTURE:
                price = current_prices.get(sym, 0.0)
            else:
                price = underlying_prices.get(underlying, 0.0)

            if price == 0.0:
                continue

            lot_size = getattr(inst, "lot_size", None) or inst.multiplier
            qty = pos.quantity
            total += elm_rate * lot_size * qty * price
        return total

    def _spread_credit(self, current_prices: Dict[str, float]) -> float:
        total_credit = 0.0
        pt = self._span_calc.position_tracker

        futures_by_underlying: Dict[str, Dict[date, float]] = defaultdict(
            lambda: defaultdict(float))

        lot_sizes: Dict[str, float] = {}

        for sym, pos in pt._positions.items():
            inst = pos.instrument
            if inst.type != InstrumentType.FUTURE:
                continue
            underlying = inst.underlying
            expiry = inst.expiry
            signed_qty = pos.quantity if pos.side.name == "LONG" else -pos.quantity
            futures_by_underlying[underlying][expiry] += signed_qty
            if underlying not in lot_sizes:
                lot_sizes[underlying] = (
                    getattr(inst, "lot_size", None) or inst.multiplier)

        for underlying, expiry_map in futures_by_underlying.items():
            expiries = sorted(expiry_map.keys())
            if len(expiries) < 2:
                continue

            ra = self._snapshot.risk_arrays.get(underlying)
            if ra is None:
                continue
            charge = ra.risk_metrics.get("intra_spread_charge_rs", 0.0)
            if charge == 0.0:
                continue

            lot_size = lot_sizes.get(underlying, 1.0)
            remaining = {e: expiry_map[e] for e in expiries}

            for i in range(len(expiries)):
                e_i = expiries[i]
                q_i = remaining[e_i]
                if q_i == 0.0:
                    continue
                for j in range(i + 1, len(expiries)):
                    e_j = expiries[j]
                    q_j = remaining[e_j]
                    if q_j == 0.0:
                        continue
                    if (q_i > 0 and q_j > 0) or (q_i < 0 and q_j < 0):
                        continue

                    n_matched = min(abs(q_i), abs(q_j))
                    if n_matched == 0.0:
                        continue

                    near_exp = min(e_i, e_j, key=lambda e: e)
                    far_exp = max(e_i, e_j, key=lambda e: e)
                    scan_near = _get_scan_risk(underlying, near_exp, self._snapshot)
                    scan_far = _get_scan_risk(underlying, far_exp, self._snapshot)
                    pair_credit = max(
                        0.0, (scan_near + scan_far - charge) * lot_size * n_matched)
                    total_credit += pair_credit

                    sign_i = 1 if q_i > 0 else -1
                    sign_j = 1 if q_j > 0 else -1
                    remaining[e_i] -= n_matched * sign_i
                    remaining[e_j] -= n_matched * sign_j

                    q_i = remaining[e_i]
                    if q_i == 0.0:
                        break

        return total_credit
