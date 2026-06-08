from typing import Optional
from core.instruments.instrument_base import Instrument
from core.instruments.canonical import AssetClass
from core.risk.greeks.greeks_model import Greeks
from core.risk.greeks.black76_engine import Black76Engine


def _asset_class(instrument) -> Optional[AssetClass]:
    """Asset class of either a CanonicalInstrument (`.asset_class`) or a legacy
    Instrument (normalised from `.type` — InstrumentType names align with AssetClass)."""
    ac = getattr(instrument, "asset_class", None)
    if ac is not None:
        return ac
    itype = getattr(instrument, "type", None)
    return AssetClass[itype.name] if itype is not None else None


class GreeksCalculator:
    """
    Calculates Greeks for various instrument types.
    """

    @staticmethod
    def calculate(instrument: Instrument,
                  quantity: float,
                  underlying_price: float,
                  volatility: float = 0.20,  # Default 20% if not provided
                  time_to_expiry: float = 0.0,  # Years
                  risk_free_rate: float = 0.05) -> Greeks:
        """
        Compute Greeks for a given instrument and quantity.
        """

        asset_class = _asset_class(instrument)

        # 1. Equity
        if asset_class == AssetClass.EQUITY:
            # Delta = 1 (per share), others 0
            return Greeks(
                delta=quantity,
                gamma=0.0,
                vega=0.0,
                theta=0.0,
                rho=0.0
            )

        # 2. Future
        elif asset_class == AssetClass.FUTURE:
            # Delta = 1 * multiplier (approx for futures close to expiry/spot)
            # Technically Delta of future wrt spot is e^(rT), but often treated as 1 for delta-one.
            # We will use quantity * multiplier.
            multiplier = getattr(instrument, 'multiplier', 1.0)
            return Greeks(
                delta=quantity * multiplier,
                gamma=0.0,
                vega=0.0,
                theta=0.0,
                rho=0.0
            )

        # 3. Option
        elif asset_class == AssetClass.OPTION:
            multiplier = getattr(instrument, 'multiplier', 1.0)

            # Calculate per-unit Greeks
            unit_greeks = Black76Engine.calculate_greeks(
                F=underlying_price,
                K=instrument.strike,
                T=time_to_expiry,
                r=risk_free_rate,
                sigma=volatility,
                option_type=instrument.option_type
            )

            # Scale by quantity and multiplier
            return unit_greeks * (quantity * multiplier)

        # Default / Unknown
        return Greeks(0.0, 0.0, 0.0, 0.0, 0.0)
