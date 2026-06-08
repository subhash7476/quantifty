"""
Legacy Live Market Provider - Backward Compatibility Shim
---------------------------------------------------------
DEPRECATED: Use core.database.providers instead.

This module re-exports LiveDuckDBMarketDataProvider from core.database.providers
to maintain backward compatibility with existing code.

Migration guide:
    # Old import (deprecated)
    from core.data.live_market_provider import LiveDuckDBMarketDataProvider

    # New import (preferred)
    from core.database.providers import LiveDuckDBMarketDataProvider
"""

# Re-export from the new location
from core.database.providers.live_market import LiveDuckDBMarketDataProvider

__all__ = ["LiveDuckDBMarketDataProvider"]
