import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from core.analytics.gex_history import RATE
from core.analytics.iron_fly import (
    Leg, conservative_mark, exit_reason, leg_costs, position_value, select_legs,
    trade_return, zone_thresholds,
)
from core.execution.options.fees import option_order_fees
from core.execution.options.nifty_shield_pricing import bs_price

F, T, IV = 20000.0, 7 / 365, 0.15


def _chain():
    spot = F * math.exp(-RATE * T)
    return pd.DataFrame([{"strike": float(k), "option_type": o,
                          "close": bs_price(spot, k, T, RATE, IV, o), "contracts": 10}
                         for k in range(19000, 21001, 50) for o in ("CE", "PE")])


def test_zone_thresholds_are_causal():
    n = pd.Series(np.linspace(-0.1, 0.1, 300))
    spiked = n.copy()
    spiked.iloc[-1] = 5.0
    a, b = zone_thresholds(n), zone_thresholds(spiked)
    assert a.iloc[:-1].equals(b.iloc[:-1])
    assert a["p67"].iloc[198] != a["p67"].iloc[198]  # NaN below 200 observations
    assert a["p67"].iloc[-1] > a["p50"].iloc[-1]


def test_select_legs_fly_uses_sigma_wings():
    legs, width = select_legs(_chain(), F, T, "fly")
    w = IV * math.sqrt(T) * F  # ~415.5
    assert legs == (Leg(20000.0, "CE", -1), Leg(20000.0, "PE", -1),
                    Leg(20450.0, "CE", 1), Leg(19550.0, "PE", 1))
    assert 20450.0 >= 20000 + w and 19550.0 <= 20000 - w
    assert width == 450.0


def test_select_legs_condor_and_straddle():
    legs, width = select_legs(_chain(), F, T, "condor")
    assert legs == (Leg(20200.0, "CE", -1), Leg(19800.0, "PE", -1),
                    Leg(20600.0, "CE", 1), Leg(19400.0, "PE", 1))
    assert width == 400.0
    legs, width = select_legs(_chain(), F, T, "straddle")
    assert legs == (Leg(20000.0, "CE", -1), Leg(20000.0, "PE", -1)) and width == 450.0


def test_select_legs_reports_missing_wing():
    chain = _chain()
    assert select_legs(chain[chain.strike.between(19700, 20300)], F, T, "fly") == "no_wing"


def test_conservative_mark():
    assert conservative_mark(10.0, 12.0, 5, -1) == 10.0
    assert conservative_mark(10.0, 12.0, 0, -1) == 12.0
    assert conservative_mark(10.0, 12.0, 0, 1) == 10.0
    assert conservative_mark(10.0, float("nan"), 0, 1) == 10.0


def test_exit_precedence():
    assert exit_reason(-100.0, 100.0, True, True) == "stop"
    assert exit_reason(50.0, 100.0, True, True) == "profit"
    assert exit_reason(0.0, 100.0, True, True) == "regime"
    assert exit_reason(0.0, 100.0, False, True) == "time"
    assert exit_reason(0.0, 100.0, False, False) is None


def test_position_value_and_costs():
    legs = (Leg(100.0, "CE", -1), Leg(120.0, "CE", 1))
    assert position_value(legs, [10.0, 4.0]) == -6.0
    d = date(2020, 6, 1)
    fees, prem = leg_costs(legs, [10.0, 4.0], d, 75, opening=True)
    expected = (option_order_fees(premium=10.0, quantity=75, side="SELL", trade_date=d).total
                + option_order_fees(premium=4.0, quantity=75, side="BUY", trade_date=d).total) / 75
    assert fees == pytest.approx(expected) and prem == 14.0
    close_fees, _ = leg_costs(legs, [10.0, 4.0], d, 75, opening=False)
    assert close_fees != fees  # sides flip on close (STT is sell-side only)


def test_trade_return_hand_built():
    # credit 100, width 400 -> risk 300; gross +50, fees 6, premium turnover 800 @ 2% spread -> 8
    assert trade_return(50.0, 6.0, 800.0, 300.0, 0.02) == pytest.approx((50 - 6 - 8) / 300)
