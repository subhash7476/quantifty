"""
Backward Compatibility Shim
---------------------------
This module re-exports from core.database.ingestors for backward compatibility.

DEPRECATED: Use `from core.database.ingestors import WebSocketIngestor` instead.
"""

import warnings

warnings.warn(
    "Importing from core.data.websocket_ingestor is deprecated. "
    "Use 'from core.database.ingestors import WebSocketIngestor' instead.",
    DeprecationWarning,
    stacklevel=2
)

from core.database.ingestors import WebSocketIngestor

__all__ = ["WebSocketIngestor"]
