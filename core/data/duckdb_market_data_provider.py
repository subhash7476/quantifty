"""
Legacy DuckDB Market Data Provider - Backward Compatibility Shim
----------------------------------------------------------------
DEPRECATED: Use core.database.providers instead.

This module re-exports DuckDBMarketDataProvider from core.database.providers
to maintain backward compatibility with existing code.

Migration guide:
    # Old import (deprecated)
    from core.data.duckdb_market_data_provider import DuckDBMarketDataProvider

    # New import (preferred)
    from core.database.providers import DuckDBMarketDataProvider
"""

# Re-export from the new location
from core.database.providers.market_data import DuckDBMarketDataProvider

__all__ = ["DuckDBMarketDataProvider"]
