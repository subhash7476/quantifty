"""
Legacy Market Session - Backward Compatibility Shim
---------------------------------------------------
DEPRECATED: Use core.database.utils instead.

This module re-exports MarketSession from core.database.utils
to maintain backward compatibility with existing code.

Migration guide:
    # Old import (deprecated)
    from core.data.market_session import MarketSession

    # New import (preferred)
    from core.database.utils import MarketSession
"""

# Re-export from the new location
from core.database.utils.market_session import MarketSession

__all__ = ["MarketSession"]
