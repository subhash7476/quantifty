import math
from dataclasses import dataclass
from typing import Optional

from governance.rfa.declaration import validate
from scripts.rfa.power import n_required, power_at

METHODOLOGY_VERSION = "2.0.0"
POWER_HURDLE = 0.80


@dataclass(frozen=True)
class Verdict:
    decision: str
    max_power: float
    n_available: int
    n_required_corner: int
    n_required_central: int
    n_required_pessimistic: int
    methodology_version: str
    corner_delta: Optional[float] = None
    corner_sd: Optional[float] = None
    corner_sharpe: Optional[float] = None


def evaluate(decl):
    if decl.methodology_version != METHODOLOGY_VERSION:
        raise ValueError(
            f"methodology_version mismatch: declaration targets "
            f"{decl.methodology_version}, gate is {METHODOLOGY_VERSION}. "
            f"A frozen declaration was defended against a specific ruleset; "
            f"re-approve it against the current version before re-running."
        )
    validate(decl)

    two_sided = decl.test_type == "two_sided"

    if decl.metric == "per_trade_pnl":
        return _evaluate_per_trade_pnl(decl, two_sided)
    return _evaluate_rank_ic(decl, two_sided)


def _evaluate_rank_ic(decl, two_sided):
    corner_delta, corner_sd = decl.delta_hi, decl.sd_lo
    mid_delta = (decl.delta_lo + decl.delta_hi) / 2
    mid_sd = (decl.sd_lo + decl.sd_hi) / 2

    max_power = power_at(corner_delta, corner_sd, decl.n_available, two_sided)

    return Verdict(
        decision="ABANDON" if max_power < POWER_HURDLE else "PROCEED",
        max_power=max_power,
        n_available=decl.n_available,
        n_required_corner=n_required(corner_delta, corner_sd, POWER_HURDLE, two_sided),
        n_required_central=n_required(mid_delta, mid_sd, POWER_HURDLE, two_sided),
        n_required_pessimistic=n_required(decl.delta_lo, decl.sd_hi, POWER_HURDLE, two_sided),
        methodology_version=METHODOLOGY_VERSION,
        corner_delta=corner_delta,
        corner_sd=corner_sd,
    )


def _evaluate_per_trade_pnl(decl, two_sided):
    # ncp = (delta/sd) * sqrt(n); for fixed Sharpe S, delta/sd = S/sqrt(c),
    # so ncp = (S/sqrt(c)) * sqrt(c*T) = S*sqrt(T) -- cadence cancels.
    # We pass delta = per_formation_sharpe and sd = 1.0 to power_at().
    c = decl.cadence_per_year
    sqrt_c = math.sqrt(c)

    def _per_formation(annualized_sharpe):
        return annualized_sharpe / sqrt_c

    corner_sharpe = decl.sharpe_hi
    central_sharpe = (decl.sharpe_lo + decl.sharpe_hi) / 2

    max_power = power_at(
        _per_formation(corner_sharpe), 1.0, decl.n_available, two_sided
    )

    return Verdict(
        decision="ABANDON" if max_power < POWER_HURDLE else "PROCEED",
        max_power=max_power,
        n_available=decl.n_available,
        n_required_corner=n_required(
            _per_formation(corner_sharpe), 1.0, POWER_HURDLE, two_sided
        ),
        n_required_central=n_required(
            _per_formation(central_sharpe), 1.0, POWER_HURDLE, two_sided
        ),
        n_required_pessimistic=n_required(
            _per_formation(decl.sharpe_lo), 1.0, POWER_HURDLE, two_sided
        ),
        methodology_version=METHODOLOGY_VERSION,
        corner_sharpe=corner_sharpe,
    )
