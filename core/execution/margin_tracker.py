"""
Margin Tracker
--------------
Tracks estimated margin usage based on gross exposure.
"""
from typing import Dict, Optional
from core.execution.position_tracker import PositionTracker


class MarginTracker:
    def __init__(self, position_tracker: PositionTracker, margin_rate: float = 0.2):
        """
        Args:
            margin_rate: Default margin requirement (e.g., 0.2 for 5x leverage)
        """
        self.position_tracker = position_tracker
        self.margin_rate = margin_rate

    def get_exposure(self, current_prices: Dict[str, float], symbol: Optional[str] = None) -> float:
        """Calculate Gross Exposure (Value of all positions)."""
        if symbol:
            return self._calculate_single_exposure(symbol, current_prices.get(symbol))

        total_exposure = 0.0
        for sym in self.position_tracker._positions:
            price = current_prices.get(sym)
            # MM9.2-S2: 'is not None' instead of truthy — a zero-priced leg
            # (deep OTM near expiry) must remain in the sum, contributing 0.
            if price is not None:
                total_exposure += self._calculate_single_exposure(sym, price)
        return total_exposure

    def _calculate_single_exposure(self, symbol: str, current_price: Optional[float]) -> float:
        if current_price is None:
            return 0.0
        pos = self.position_tracker.get_position(symbol)
        # MM9.2-S2: prefer lot_size — canonical_restore._resolve_option sets
        # lot_size=ci.lot_size but multiplier=1.0 on restored Option positions,
        # so pos.instrument.multiplier under-counts NIFTY ~75x / BANKNIFTY ~30x.
        # Option carries lot_size; Future already folds lot_size into multiplier
        # (core/execution/futures.py:49); Equity has neither (defaults to 1.0).
        lot_size = getattr(pos.instrument, 'lot_size', None) or pos.instrument.multiplier
        return pos.quantity * current_price * lot_size

    def get_used_margin(self, current_prices: Dict[str, float]) -> float:
        """Estimate used margin based on gross exposure."""
        return self.get_exposure(current_prices) * self.margin_rate
