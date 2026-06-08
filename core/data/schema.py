"""
Legacy Schema Module - Backward Compatibility Shim
--------------------------------------------------
DEPRECATED: Use core.database.schema instead.

This module re-exports BOOTSTRAP_STATEMENTS from core.database.schema
to maintain backward compatibility with existing code.

Migration guide:
    # Old import (deprecated)
    from core.data.schema import BOOTSTRAP_STATEMENTS

    # New import (preferred)
    from core.database.schema import BOOTSTRAP_STATEMENTS

    # Or
    from core.database import BOOTSTRAP_STATEMENTS
"""

# Re-export from the new location
from core.database.schema import BOOTSTRAP_STATEMENTS, INDEX_STATEMENTS

__all__ = [
    "BOOTSTRAP_STATEMENTS",
    "INDEX_STATEMENTS",
]
