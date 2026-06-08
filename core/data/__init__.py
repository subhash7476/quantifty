"""
Legacy Data Package - Backward Compatibility Shim
-------------------------------------------------
This package redirects all imports to the new core.database module.

DEPRECATED: Use core.database instead.

All modules in this package are re-exports from core.database:
    - duckdb_client -> core.database.legacy_adapter
    - schema -> core.database.schema
    - analytics_persistence -> core.database.legacy_adapter
"""

# This package exists solely for backward compatibility.
# New code should import from core.database directly.
