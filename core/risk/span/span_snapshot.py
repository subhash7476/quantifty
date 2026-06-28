"""
SPAN Data Model — Immutable DTOs (MM9.4-S2).

SpanSnapshot represents one exchange-published SPAN parameter snapshot.
SpanRiskArray captures per-contract risk metrics within a snapshot.

Both are frozen, deterministic, and carry no business logic.
"""

from datetime import date
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class SpanRiskArray:
    """Per-contract risk metrics from a SPAN parameter file.

    Fields:
      symbol:      The contract's trading symbol (e.g. "NIFTY", "BANKNIFTY").
      risk_metrics: Dict of named risk values (e.g. scan_risk, extreme_loss,
                    intra_month_spread, inter_month_spread). Keys and their
                    interpretation are schema-version-specific.
    """
    symbol: str
    risk_metrics: Dict[str, float]


@dataclass(frozen=True)
class SpanSnapshot:
    """Immutable value object for one exchange-published SPAN parameter snapshot.

    Fields:
      snapshot_date:  The NSE trading date this snapshot was published for.
      schema_version: Parser version identifier (e.g. "v1").
      exchange:       Source exchange code (e.g. "NSE").
      segment:        Market segment (e.g. "FO").
      file_hash:      SHA-256 hex digest of the original downloaded ZIP file.
      risk_arrays:    Per-contract risk metrics keyed by symbol.
      metadata:       Auxiliary information (download timestamp, source URL,
                      exchange metadata). Schema is free-form.
    """
    snapshot_date: date
    schema_version: str
    exchange: str
    segment: str
    file_hash: str
    risk_arrays: Dict[str, SpanRiskArray]
    metadata: Dict[str, Any]
