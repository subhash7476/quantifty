"""
Legacy Market Data Provider - Backward Compatibility Shim
---------------------------------------------------------
DEPRECATED: Use core.database.providers instead.

This module re-exports MarketDataProvider from core.database.providers
to maintain backward compatibility with existing code.

Migration guide:
    # Old import (deprecated)
    from core.data.market_data_provider import MarketDataProvider

    # New import (preferred)
    from core.database.providers import MarketDataProvider
"""

# Re-export from the new location
from core.database.providers.base import MarketDataProvider

__all__ = ["MarketDataProvider"]
