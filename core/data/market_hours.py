"""
Legacy Market Hours - Backward Compatibility Shim
-------------------------------------------------
DEPRECATED: Use core.database.utils instead.

This module re-exports MarketHours from core.database.utils
to maintain backward compatibility with existing code.

Migration guide:
    # Old import (deprecated)
    from core.data.market_hours import MarketHours

    # New import (preferred)
    from core.database.utils import MarketHours
"""

# Re-export from the new location
from core.database.utils.market_hours import MarketHours

__all__ = ["MarketHours"]
