"""
Legacy DuckDB Client - Backward Compatibility Shim
--------------------------------------------------
DEPRECATED: Use core.database instead.

This module re-exports functions from core.database.legacy_adapter
to maintain backward compatibility with existing code.

Migration guide:
    # Old import (deprecated)
    from core.data.duckdb_client import db_cursor

    # New import (preferred)
    from core.database import db_cursor

    # Or better, use the new abstraction
    from core.database import DatabaseManager, DatabaseDomain

    db = DatabaseManager()
    with db.read() as conn:
        ...
"""

# Re-export everything from the new location
from core.database.legacy_adapter import (
    db_cursor,
    get_connection,
    get_db,
)

__all__ = [
    "db_cursor",
    "get_connection",
    "get_db",
]
