"""
SpanMarginCalculator (MM9.5-S3)
-------------------------------
Consumes immutable SpanSnapshot from parser_v400.  The margin formula uses
absolute rupees per underlying unit (ADR-008): scan_risk is NOT a fraction.

  margin = qty_lots x lot_size x max(scan_risk_rs, som_rs) x margin_rate

This milestone migrates ONLY the scan-risk component of SPAN.  It does NOT
implement: spread credits, portfolio offsets, exposure margin, delivery
margin, or complete SPAN portfolio margin.

Deterministic: zero filesystem, network, broker, or clock I/O.
Repository-independent: imports only SpanSnapshot from the SPAN package.
"""

from typing import Dict, Optional

from core.execution.position_tracker import PositionTracker
from core.risk.span.span_snapshot import SpanSnapshot


# --------------------------------------------------------------------------- #
# Metric constants — keys inside SpanRiskArray.risk_metrics populated by
# parser_v400 (MM9.5-S2).  scan_risk is confirmed as Rs per underlying unit.
# --------------------------------------------------------------------------- #
SPAN_METRIC_SCAN_RISK            = "scan_risk"
SPAN_METRIC_SHORT_OPTION_MIN     = "short_option_minimum"
SPAN_METRIC_PRICE_SCAN_RANGE     = "price_scan_range"
SPAN_METRIC_VOL_SCAN_RANGE       = "vol_scan_range"
SPAN_METRIC_CVF                  = "cvf"
SPAN_METRIC_INTRA_SPREAD_CHARGE  = "intra_spread_charge_rs"
SPAN_METRIC_RISK_FREE_RATE       = "risk_free_rate"


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

        For each position: margin = qty x lot_size x max(scan_risk, som)
        x margin_rate.  Price does NOT appear in the scan margin path
        (ADR-008 — scan_risk is absolute Rs per underlying unit).
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
            quantity: Proposed order quantity (in lots).
            price:    Current price (used for exposure only, NOT scan margin).
            lot_size: Contract lot size (default 1.0 for equity).

        Returns:
            Margin in rupees for the proposed position.

        Raises:
            MissingRiskArray: No risk array for symbol.
            MissingRiskMetric: scan_risk absent.
        """
        risk = self._scan_margin_per_unit(symbol)
        return quantity * lot_size * risk * self.margin_rate

    def get_snapshot_param(self, symbol: str, metric: str) -> float:
        """Return any risk_metrics value from the snapshot for a given symbol.

        Raises MissingRiskArray  if symbol not in snapshot.
        Raises MissingRiskMetric if metric absent.
        """
        risk_array = self._snapshot.risk_arrays.get(symbol)
        if risk_array is None:
            raise MissingRiskArray(f"No SPAN risk array for symbol {symbol!r}")
        value = risk_array.risk_metrics.get(metric)
        if value is None:
            raise MissingRiskMetric(
                f"Missing metric {metric!r} for symbol {symbol!r}"
            )
        return value

    # -- Internal helpers ------------------------------------------------ #

    def _single_exposure(self, symbol: str, current_price: Optional[float]) -> float:
        """Gross notional for one position."""
        if current_price is None:
            return 0.0
        pos = self.position_tracker.get_position(symbol)
        lot_size = getattr(pos.instrument, "lot_size", None) or pos.instrument.multiplier
        return pos.quantity * current_price * lot_size

    def _single_span_margin(self, symbol: str, current_price: float) -> float:
        """SPAN margin for one held position (before margin_rate haircut).

        Formula: qty_lots x lot_size x scan_risk_rs (absolute rupees per
        underlying unit — price does NOT appear here).
        """
        pos = self.position_tracker.get_position(symbol)
        lot_size = getattr(pos.instrument, "lot_size", None) or pos.instrument.multiplier
        risk = self._scan_margin_per_unit(symbol)
        return pos.quantity * lot_size * risk

    def _scan_margin_per_unit(self, symbol: str) -> float:
        """Look up the SPAN margin per underlying unit for a symbol.

        Returns max(scan_risk, short_option_min) in absolute Rs per
        underlying unit.

        scan_risk is sourced from the v400 parser as Rs per underlying unit.
        short_option_minimum defaults to 0.0 if absent (index-instrument
        SOM is 0 for all underlyings in the reference file; non-zero SOM
        for equity underlyings requires unit confirmation before use).

        Raises:
            MissingRiskArray: No risk array for symbol.
            MissingRiskMetric: scan_risk absent.
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
        som = risk_array.risk_metrics.get(SPAN_METRIC_SHORT_OPTION_MIN, 0.0)
        return max(scan_risk, som)
