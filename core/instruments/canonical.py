"""
CanonicalInstrument — the platform-owned instrument value object
(CANONICAL_INSTRUMENT_ARCHITECTURE.md §D2/§D3).

One immutable value object discriminated by `asset_class` (not a subclass tree).
It carries the platform-owned economic facts (lot_size, tick_size, isin) and a
deterministic `canonical_id`; broker identifiers live in the mapping layer
(§D6), never here. The `multiplier == lot_size` invariant (§D3.1) is enforced by
making multiplier a derived view of lot_size.

Pure module: no broker, no strategy, no I/O.
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from core.instruments.identity import canonical_id
from core.instruments.option import OptionType


class AssetClass(Enum):
    EQUITY = "EQUITY"
    INDEX = "INDEX"
    FUTURE = "FUTURE"
    OPTION = "OPTION"


@dataclass(frozen=True)
class CanonicalInstrument:
    asset_class: AssetClass
    exchange: str
    underlying: Optional[str] = None
    expiry: Optional[date] = None
    strike: Optional[float] = None
    option_type: Optional[OptionType] = None
    lot_size: int = 1
    tick_size: float = 0.0
    isin: Optional[str] = None
    segment: Optional[str] = None
    product: Optional[str] = None
    freeze_qty: Optional[int] = None
    display_symbol: Optional[str] = None
    canonical_id: str = field(init=False, default="")

    def __post_init__(self):
        self._validate()
        object.__setattr__(
            self,
            "canonical_id",
            canonical_id(
                self.asset_class,
                exchange=self.exchange,
                underlying=self.underlying,
                isin=self.isin,
                expiry=self.expiry,
                strike=self.strike,
                option_type=self.option_type,
            ),
        )

    def _validate(self):
        ac = self.asset_class
        if ac == AssetClass.OPTION:
            missing = [
                n for n, v in (
                    ("underlying", self.underlying),
                    ("expiry", self.expiry),
                    ("strike", self.strike),
                    ("option_type", self.option_type),
                ) if v is None
            ]
            if missing:
                raise ValueError(f"OPTION requires {missing}")
        elif ac == AssetClass.FUTURE:
            if self.underlying is None or self.expiry is None:
                raise ValueError("FUTURE requires underlying and expiry")
        elif ac == AssetClass.EQUITY:
            if not self.isin:
                raise ValueError("EQUITY requires isin")
        elif ac == AssetClass.INDEX:
            if not self.underlying:
                raise ValueError("INDEX requires underlying")

    @property
    def multiplier(self) -> float:
        """The one size convention (§D3.1): notional = qty_lots * multiplier * price."""
        return float(self.lot_size)

    @property
    def tradable(self) -> bool:
        """INDEX is a reference underlying, never an order target (§D2.2)."""
        return self.asset_class != AssetClass.INDEX

    @property
    def symbol(self) -> str:
        """Human/back-compat handle: the display symbol, else the canonical_id."""
        return self.display_symbol or self.canonical_id
