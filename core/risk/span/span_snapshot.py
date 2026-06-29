"""
SPAN Data Model — Immutable DTOs (MM9.5-S2).

SpanSnapshot represents one exchange-published SPAN parameter snapshot.
SpanRiskArray captures per-contract risk metrics within a snapshot.
SpanFutureContract, SpanOptionSeries, and SpanOptionContract capture
per-contract extracted data for futures and options positions.

All are frozen, deterministic, and carry no business logic.
"""

from datetime import date
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


class UnsupportedSpanSchema(ValueError):
    """Raised when a schema_version has no registered parser."""


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
class SpanFutureContract:
    """Per-expiry futures contract extracted from <futPf/fut>."""
    symbol: str
    expiry: date
    price: float
    delta: float
    time_to_expiry: float
    risk_free_rate: float
    price_scan_range: float
    vol_scan_range: float
    ra: Tuple[float, ...]


@dataclass(frozen=True)
class SpanOptionSeries:
    """Per-expiry option series extracted from <oopPf/series>."""
    symbol: str
    expiry: date
    vol: float
    price_scan_range: float
    vol_scan_range: float
    time_to_expiry: float
    risk_free_rate: float


@dataclass(frozen=True)
class SpanOptionContract:
    """Per-strike option contract extracted from <oopPf/series/opt>."""
    symbol: str
    expiry: date
    strike: float
    option_type: str
    price: float
    delta: float
    implied_vol: float
    ra: Tuple[float, ...]


@dataclass(frozen=True)
class SpanSnapshot:
    """Immutable value object for one exchange-published SPAN parameter snapshot.

    Fields:
      snapshot_date:  The NSE trading date this snapshot was published for.
      schema_version: Parser version identifier (e.g. "v1").
      exchange:       Source exchange code (e.g. "NSE").
      segment:        Market segment (e.g. "FO").
      file_hash:      SHA-256 hex digest of the original downloaded ZIP file.
      is_settlement:  Whether this is an EOD settlement file.
      risk_arrays:    Per-contract risk metrics keyed by symbol.
      metadata:       Auxiliary information (download timestamp, source URL,
                      exchange metadata). Schema is free-form.
      futures:        Per-symbol tuples of SpanFutureContract.
      option_series:  Per-symbol tuples of SpanOptionSeries.
      option_contracts: Per-symbol tuples of SpanOptionContract.
    """
    snapshot_date: date
    schema_version: str
    exchange: str
    segment: str
    file_hash: str
    is_settlement: bool
    risk_arrays: Dict[str, SpanRiskArray]
    metadata: Dict[str, Any]
    futures: Dict[str, Tuple[SpanFutureContract, ...]] = field(default_factory=dict)
    option_series: Dict[str, Tuple[SpanOptionSeries, ...]] = field(default_factory=dict)
    option_contracts: Dict[str, Tuple[SpanOptionContract, ...]] = field(default_factory=dict)
