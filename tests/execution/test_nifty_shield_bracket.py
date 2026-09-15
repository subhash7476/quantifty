"""NiftyShield sigma bracket — take-profit and stop sized as the structure's P&L at
spot +/-1 sigma over the hold (docs/superpowers/specs/2026-09-15-nifty-shield-sigma-bracket-design.md).
"""
from __future__ import annotations

import pytest

from core.execution.options.nifty_shield_pricing import (
    bs_price, implied_vol, sigma_bracket,
)

RATE = 0.065


@pytest.mark.parametrize("option_type", ["CE", "PE"])
@pytest.mark.parametrize("strike", [22800.0, 23300.0, 23800.0])
def test_implied_vol_round_trips_bs_price(option_type, strike):
    price = bs_price(23334.5, strike, 7 / 365, RATE, 0.15, option_type)
    assert implied_vol(price, 23334.5, strike, 7 / 365, RATE, option_type) == pytest.approx(0.15, abs=1e-4)


def test_implied_vol_is_none_below_intrinsic():
    assert implied_vol(100.0, 23334.5, 23000.0, 7 / 365, RATE, "CE") is None


def _bear_call_2026_09_15():
    return [
        {"side": "SELL", "strike": 23300.0, "option_type": "CE", "price": 174.50, "qty": 65},
        {"side": "BUY", "strike": 23500.0, "option_type": "CE", "price": 83.25, "qty": 65},
    ]


def _bracket(legs, fee_floor_rs=402.0, **over):
    kw = dict(spot=23334.5, dte_days=7, rate=RATE, sigma_mult=1.0,
              hold_hours=2.5, session_hours=6.25, fee_floor_rs=fee_floor_rs)
    kw.update(over)
    return sigma_bracket(legs, **kw)


def test_bear_call_spread_reproduces_the_2026_09_15_bracket():
    """Rs 121 take-profit / Rs 3,534 stop under the old rules; symmetric here."""
    b = _bracket(_bear_call_2026_09_15())
    assert b.sigma_pts == pytest.approx(101.4, rel=0.01)
    assert b.tp_rs == pytest.approx(1_424.0, rel=0.01)
    assert b.sl_rs == pytest.approx(1_462.0, rel=0.01)
    assert b.leg_ivs == pytest.approx((0.1091, 0.1091), abs=5e-4)
    assert b.fee_floor_rs == 402.0
    assert b.tp_enabled is True


def test_short_straddle_has_no_take_profit_side():
    """Loses on both sides of the move, so the clock and the stop manage it."""
    legs = [{"side": "SELL", "strike": 18150.0, "option_type": "CE", "price": 60.0, "qty": 130},
            {"side": "SELL", "strike": 18150.0, "option_type": "PE", "price": 58.0, "qty": 130}]
    b = _bracket(legs, spot=18150.0, dte_days=6)
    assert b.tp_rs == 0.0
    assert b.tp_enabled is False
    assert b.sl_rs > 0.0


def test_take_profit_below_the_fee_floor_is_disabled():
    b = _bracket(_bear_call_2026_09_15(), fee_floor_rs=10_000.0)
    assert b.tp_rs == pytest.approx(1_424.0, rel=0.01)
    assert b.tp_enabled is False
    assert b.sl_rs == pytest.approx(1_462.0, rel=0.01)


def test_wider_sigma_multiple_widens_both_sides():
    one = _bracket(_bear_call_2026_09_15())
    two = _bracket(_bear_call_2026_09_15(), sigma_mult=2.0)
    assert two.tp_rs > one.tp_rs and two.sl_rs > one.sl_rs


def test_structure_that_gains_on_both_sides_is_unavailable():
    """Credit above the wing width (an arbitrage-priced fly, e.g. off a stale
    quote) has no loss side, so a stop of Rs 0 would fire at flat marks."""
    legs = [{"side": "SELL", "strike": 18150.0, "option_type": "CE", "price": 100.0, "qty": 130},
            {"side": "SELL", "strike": 18150.0, "option_type": "PE", "price": 100.0, "qty": 130},
            {"side": "BUY", "strike": 18250.0, "option_type": "CE", "price": 20.0, "qty": 130},
            {"side": "BUY", "strike": 18050.0, "option_type": "PE", "price": 20.0, "qty": 130}]
    assert _bracket(legs, spot=18150.0, dte_days=6) is None


def test_unsolvable_leg_makes_the_bracket_unavailable():
    legs = _bear_call_2026_09_15()
    legs[0] = {**legs[0], "strike": 23000.0, "price": 100.0}     # below intrinsic
    assert _bracket(legs) is None


@pytest.mark.parametrize("over", [{"spot": 0.0}, {"dte_days": 0}])
def test_missing_inputs_make_the_bracket_unavailable(over):
    assert _bracket(_bear_call_2026_09_15(), **over) is None
