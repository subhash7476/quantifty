"""
Broker mapping interface (CANONICAL_INSTRUMENT_ARCHITECTURE.md §D6).

The seam that keeps broker identity out of the canonical model. One
implementation per broker; the platform depends only on this interface, so it
stays portable across Upstox / Zerodha / Fyers / IB without redesigning internal
models.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from core.instruments.canonical import CanonicalInstrument


@dataclass(frozen=True)
class BrokerRef:
    """The broker-specific identity bundle for a canonical instrument (§D5)."""
    instrument_key: str
    tradingsymbol: str
    exchange_token: Optional[str] = None
    product_code: Optional[str] = None


class BrokerMapping(ABC):
    @abstractmethod
    def to_broker(self, instrument: CanonicalInstrument) -> BrokerRef:
        """Canonical instrument -> broker identity. Raises if unmapped."""

    @abstractmethod
    def from_broker_position(self, raw: dict) -> Optional[CanonicalInstrument]:
        """Broker position payload -> canonical instrument (None if unmappable)."""

    @abstractmethod
    def from_broker_order(self, raw: dict) -> Optional[CanonicalInstrument]:
        """Broker order payload -> canonical instrument (None if unmappable)."""
