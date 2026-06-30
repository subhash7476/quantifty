"""ELM rate table for known underlyings.

Source: NSE Clearing equity derivatives margins page
    https://www.nseclearing.in/risk-management/equity-derivatives/margins

Category-level rates (single source of truth):
  INDEX: 2% — confirmed from NSE Clearing page
  STOCK: 3.5% — Phase 2; dynamic component out of scope

Index derivatives covered by Phase 1: NIFTY, BANKNIFTY.
Adding a new index underlying requires only one line in _INDEX_UNDERLYINGS.
"""

from typing import Dict, FrozenSet

ELM_RATES_BY_CATEGORY: Dict[str, float] = {
    "INDEX": 0.02,
    "STOCK": 0.035,
}

_INDEX_UNDERLYINGS: FrozenSet[str] = frozenset({"NIFTY", "BANKNIFTY"})

INDEX_ELM_RATES: Dict[str, float] = {
    u: ELM_RATES_BY_CATEGORY["INDEX"] for u in _INDEX_UNDERLYINGS
}
