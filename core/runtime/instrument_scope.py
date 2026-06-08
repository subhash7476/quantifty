"""
F&O scope detection for the MM.4 startup-readiness gate.

`has_derivatives` answers "does this universe trade a tradable derivative?" from
the broker-segment prefix of each instrument key. Master-independent by design:
master absence is itself a BLOCK condition (MASTER_MATERIALIZATION_POLICY.md §4),
so the scope decision cannot depend on resolving the master — it reads only the
raw key string (MM.4_DESIGN_REVIEW.md §2).

Pure: no DB, no resolver, no I/O. Runtime-owned — the driver already holds the
configured symbol list and must not reach into InstrumentResolver for this.
"""
from typing import Iterable

# Broker segments whose instruments are tradable derivatives (futures/options).
_DERIVATIVE_SEGMENTS = frozenset({"NSE_FO", "MCX_FO"})


def has_derivatives(symbols: Iterable[str]) -> bool:
    """True if any instrument key's segment prefix is a tradable-derivative segment."""
    return any(s.split("|", 1)[0] in _DERIVATIVE_SEGMENTS for s in symbols)
