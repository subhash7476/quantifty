"""
Backward Compatibility Shim
---------------------------
This module re-exports from core.database.ingestors for backward compatibility.

DEPRECATED: Use `from core.database.ingestors import DBTickAggregator` instead.
"""

import warnings

warnings.warn(
    "Importing from core.data.db_tick_aggregator is deprecated. "
    "Use 'from core.database.ingestors import DBTickAggregator' instead.",
    DeprecationWarning,
    stacklevel=2
)

from core.database.ingestors import DBTickAggregator

__all__ = ["DBTickAggregator"]
