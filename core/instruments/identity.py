"""
Canonical instrument identity (CANONICAL_INSTRUMENT_ARCHITECTURE.md §D4).

`canonical_id` is the platform-owned, broker-independent primary key (Option B):
a deterministic structured key minted from immutable contract attributes. Its
determinism depends on `normalize_underlying` (§D4.3) — the sole authority that
collapses the repo's three underlying spellings into one token.

Pure module: no broker, no strategy, no I/O.
"""
from datetime import date
from typing import Optional, Union

from core.instruments.option import OptionType

# The single source of truth for underlying spelling (§D4.3).
_UNDERLYING_ALIASES = {
    "NSE_INDEX|NIFTY 50": "NIFTY",
    "NSE_INDEX|NIFTY BANK": "BANKNIFTY",
    "NIFTY 50": "NIFTY",
    "NIFTY BANK": "BANKNIFTY",
}


def normalize_underlying(raw: str) -> str:
    """Collapse any spelling of an underlying to its canonical token."""
    key = raw.strip().upper()
    if key in _UNDERLYING_ALIASES:
        return _UNDERLYING_ALIASES[key]
    if "|" in key:
        key = key.split("|", 1)[1]
        if key in _UNDERLYING_ALIASES:
            return _UNDERLYING_ALIASES[key]
    return key.replace(" ", "")


def _fmt_strike(strike: float) -> str:
    return str(int(strike)) if float(strike).is_integer() else str(strike)


def _fmt_option_type(ot: Union[OptionType, str]) -> str:
    return ot.value if isinstance(ot, OptionType) else str(ot).upper()


def canonical_id(
    asset_class,
    *,
    exchange: str,
    underlying: Optional[str] = None,
    isin: Optional[str] = None,
    expiry: Optional[date] = None,
    strike: Optional[float] = None,
    option_type: Optional[Union[OptionType, str]] = None,
) -> str:
    """Mint the canonical_id for a contract (§D4.1)."""
    # Local import avoids an import cycle (canonical imports this module).
    from core.instruments.canonical import AssetClass

    if asset_class == AssetClass.EQUITY:
        return f"{exchange}:EQ:{isin}"
    if asset_class == AssetClass.INDEX:
        return f"{exchange}:IDX:{normalize_underlying(underlying)}"
    if asset_class == AssetClass.FUTURE:
        return f"{exchange}:FUT:{normalize_underlying(underlying)}:{expiry.isoformat()}"
    if asset_class == AssetClass.OPTION:
        return (
            f"{exchange}:OPT:{normalize_underlying(underlying)}:"
            f"{expiry.isoformat()}:{_fmt_strike(strike)}:{_fmt_option_type(option_type)}"
        )
    raise ValueError(f"unknown asset_class: {asset_class!r}")
