"""
SpanMarginCalculator (MM9.4-S3)
-------------------------------
First concrete MarginCalculator implementation consuming SpanSnapshot.

Conservative SPAN margin model:
  - get_exposure: gross notional (same algorithm as MarginTracker)
  - get_used_margin: per-position SPAN risk = notional * max(scan_risk, short_option_min)
  - get_incremental_margin: SPAN risk for a proposed order

Deterministic: zero filesystem, network, broker, or clock I/O.
Repository-independent: imports only SpanSnapshot from the SPAN package.
"""

from typing import Dict, Optional

from core.execution.position_tracker import PositionTracker
from core.risk.span.span_snapshot import SpanSnapshot


# --------------------------------------------------------------------------- #
# Metric constants — implementation-time confirmed against NSE SPAN schema.
# These are the named risk metric keys inside SpanRiskArray.risk_metrics.
# --------------------------------------------------------------------------- #
SPAN_METRIC_SCAN_RISK = "scan_risk"
SPAN_METRIC_SHORT_OPTION_MIN = "short_option_minimum"


# --------------------------------------------------------------------------- #
# Exception hierarchy
# --------------------------------------------------------------------------- #

class SpanMarginError(Exception):
    """Base exception for SPAN margin computation errors."""


class UnsupportedInstrument(SpanMarginError):
    """Instrument type not supported by the SPAN calculator."""


class MissingRiskArray(SpanMarginError):
    """No SPAN risk array found for a position's symbol."""


class MissingRiskMetric(SpanMarginError):
    """Required risk metric absent from the risk array."""


# --------------------------------------------------------------------------- #
# Calculator
# --------------------------------------------------------------------------- #

class SpanMarginCalculator:
    """SPAN-based margin calculator satisfying MarginCalculator structurally.

    Computes exposure and margin from immutable SpanSnapshot risk arrays.
    Owns no mutable portfolio state — reads PositionTracker and prices on
    every call.

    Args:
        position_tracker: The live PositionTracker.
        span_snapshot:    Immutable SpanSnapshot with per-symbol risk arrays.
        margin_rate:      Additional haircut multiplier (default 1.0 = no
                          additional buffer beyond SPAN scan risk).
    """

    def __init__(
        self,
        position_tracker: PositionTracker,
        span_snapshot: SpanSnapshot,
        margin_rate: float = 1.0,
    ):
        self.position_tracker = position_tracker
        self._snapshot = span_snapshot
        self.margin_rate = margin_rate

    # -- MarginCalculator protocol surface -------------------------------- #

    def get_exposure(
        self,
        current_prices: Dict[str, float],
        symbol: Optional[str] = None,
    ) -> float:
        """Gross notional exposure across the portfolio, or for one symbol."""
        if symbol is not None:
            return self._single_exposure(symbol, current_prices.get(symbol))

        total = 0.0
        for sym in self.position_tracker._positions:
            price = current_prices.get(sym)
            if price is not None:
                total += self._single_exposure(sym, price)
        return total

    def get_used_margin(self, current_prices: Dict[str, float]) -> float:
        """Total SPAN margin for all held positions.

        For each position: margin = notional * max(scan_risk, short_option_min)
        * margin_rate.
        """
        total = 0.0
        for sym in self.position_tracker._positions:
            price = current_prices.get(sym)
            if price is None:
                continue
            total += self._single_span_margin(sym, price)
        return total * self.margin_rate

    # -- Calculator-only extension --------------------------------------- #

    def get_incremental_margin(
        self,
        symbol: str,
        quantity: float,
        price: float,
        lot_size: float = 1.0,
    ) -> float:
        """SPAN margin for a proposed order.

        Args:
            symbol:   The contract symbol (must have a risk array).
            quantity: Proposed order quantity.
            price:    Current price.
            lot_size: Contract lot size (default 1.0 for equity).

        Returns:
            Margin in rupees for the proposed position.

        Raises:
            MissingRiskArray: No risk array for symbol.
            MissingRiskMetric: scan_risk or short_option_min absent.
        """
        risk_pct = self._risk_percentage(symbol)
        notional = quantity * price * lot_size
        return notional * risk_pct * self.margin_rate

    # -- Internal helpers ------------------------------------------------ #

    def _single_exposure(self, symbol: str, current_price: Optional[float]) -> float:
        """Gross notional for one position."""
        if current_price is None:
            return 0.0
        pos = self.position_tracker.get_position(symbol)
        lot_size = getattr(pos.instrument, "lot_size", None) or pos.instrument.multiplier
        return pos.quantity * current_price * lot_size

    def _single_span_margin(self, symbol: str, current_price: float) -> float:
        """SPAN margin for one held position (before margin_rate haircut)."""
        pos = self.position_tracker.get_position(symbol)
        lot_size = getattr(pos.instrument, "lot_size", None) or pos.instrument.multiplier
        notional = pos.quantity * current_price * lot_size
        risk_pct = self._risk_percentage(symbol)
        return notional * risk_pct

    def _risk_percentage(self, symbol: str) -> float:
        """Look up the SPAN risk percentage for a symbol.

        Returns max(scan_risk, short_option_min).

        Raises:
            MissingRiskArray: No risk array for symbol.
            MissingRiskMetric: scan_risk or short_option_min absent.
        """
        risk_array = self._snapshot.risk_arrays.get(symbol)
        if risk_array is None:
            raise MissingRiskArray(
                f"No SPAN risk array for symbol {symbol!r}"
            )
        scan_risk = risk_array.risk_metrics.get(SPAN_METRIC_SCAN_RISK)
        if scan_risk is None:
            raise MissingRiskMetric(
                f"Missing {SPAN_METRIC_SCAN_RISK!r} for symbol {symbol!r}"
            )
        short_opt_min = risk_array.risk_metrics.get(SPAN_METRIC_SHORT_OPTION_MIN)
        if short_opt_min is None:
            raise MissingRiskMetric(
                f"Missing {SPAN_METRIC_SHORT_OPTION_MIN!r} for symbol {symbol!r}"
            )
        return max(scan_risk, short_opt_min)
