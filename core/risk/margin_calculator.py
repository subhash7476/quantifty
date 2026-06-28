"""
MarginCalculator Protocol v1
-----------------------------
Abstract interface for margin computation. Implementations calculate margin
exposure and usage from current market prices and the position tracker.

Protocol contract:
  - margin_rate: float — the margin requirement fraction.
  - get_exposure(current_prices, symbol=None) -> float — gross notional exposure.
  - get_used_margin(current_prices) -> float — estimated margin consumed.

Implementations MUST be stateless with respect to portfolio state: positions,
margin, and equity must never be cached. Immutable configuration (e.g., SPAN
parameters loaded at construction) is permitted.

Implementations MUST NOT consult broker APIs at margin-calculation time.
Broker APIs are permitted only for offline reconciliation, diagnostics, and
research — never for execution-time margin.

Implementations MUST be deterministic given the same inputs. SPAN parameters
sourced from exchange data are immutable once loaded; no runtime I/O, no
runtime downloads, no runtime broker queries.

MarginCalculator computes margin. ExecutionHandler decides admission.
The calculator must never expose business-policy methods (can_trade, approve,
reject) — those belong to ExecutionHandler.
"""

from typing import Dict, Optional, Protocol


class MarginCalculator(Protocol):
    """Protocol v1: margin computation seam for flat-rate and future SPAN
    implementations. Satisfied structurally by MarginTracker."""

    margin_rate: float

    def get_exposure(self, current_prices: Dict[str, float],
                     symbol: Optional[str] = None) -> float:
        """Gross notional exposure across the portfolio, or for one symbol."""

    def get_used_margin(self, current_prices: Dict[str, float]) -> float:
        """Estimated margin consumed given current prices."""
