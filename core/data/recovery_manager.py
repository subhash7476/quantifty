"""
Backward Compatibility Shim
---------------------------
This module re-exports from core.database.ingestors for backward compatibility.

DEPRECATED: Use `from core.database.ingestors import RecoveryManager` instead.
"""

import warnings

warnings.warn(
    "Importing from core.data.recovery_manager is deprecated. "
    "Use 'from core.database.ingestors import RecoveryManager' instead.",
    DeprecationWarning,
    stacklevel=2
)

from core.database.ingestors import RecoveryManager

__all__ = ["RecoveryManager"]
