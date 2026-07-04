from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from .estimate import Estimate


@dataclass(frozen=True)
class MarketState:
    """MarketState DTO (MSI-002 §4.8).

    Multidimensional collection of Estimates of Latent Variables.
    Never a single scalar per MSI-OD-001.
    """

    evaluation_timestamp: datetime
    estimates: Tuple[Estimate, ...]