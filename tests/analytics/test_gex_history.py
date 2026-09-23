import math

import numpy as np
import pandas as pd
import pytest

from core.analytics.gex_history import (
    FLIP_EDGE, RATE, ExpiryStrikes, bs_gamma, day_regime, implied_vol,
    parity_forward, select_strikes,
)
from core.execution.options.nifty_shield_pricing import bs_price


def _chain(forward, t, iv, strikes, oi_ce=1000, oi_pe=1000, contracts=10):
    spot = forward * math.exp(-RATE * t)
    rows = []
    for k in strikes:
        for opt, oi in (("CE", oi_ce), ("PE", oi_pe)):
            rows.append({"strike": float(k), "option_type": opt,
                         "close": bs_price(spot, k, t, RATE, iv, opt),
                         "contracts": contracts, "open_int": oi})
    return pd.DataFrame(rows)


def test_bs_gamma_matches_hand_value():
    # d1 = 0.1, phi(0.1) = 0.3969525, gamma = phi / (S * sigma * sqrt(T))
    assert bs_gamma(100.0, 100.0, 1.0, 0.0, 0.2) == pytest.approx(0.01984763, rel=1e-6)


def test_implied_vol_round_trips_bs_price():
    price = bs_price(100.0, 105.0, 0.1, RATE, 0.18, "CE")
    assert implied_vol(price, 100.0, 105.0, 0.1, RATE, "CE") == pytest.approx(0.18, abs=1e-5)


def test_implied_vol_rejects_price_below_intrinsic():
    assert implied_vol(1.0, 100.0, 90.0, 0.1, RATE, "CE") is None


def test_parity_forward_recovers_known_forward():
    chain = _chain(20000.0, 20 / 365, 0.15, range(19500, 20501, 50))
    assert parity_forward(chain, 20 / 365) == pytest.approx(20000.0, abs=0.01)


def test_parity_forward_none_without_traded_pair():
    chain = _chain(20000.0, 20 / 365, 0.15, [20000])
    chain.loc[chain.option_type == "PE", "contracts"] = 0
    assert parity_forward(chain, 20 / 365) is None


def test_select_strikes_keeps_only_traded_otm_legs_in_band():
    t = 20 / 365
    chain = _chain(20000.0, t, 0.15, [17000, 19500, 19900, 20100, 20500, 23000])
    chain.loc[(chain.strike == 19900.0) & (chain.option_type == "PE"), "contracts"] = 0
    es = select_strikes(chain, 20000.0, t)
    # 17000 and 23000 are outside |ln(K/F)| <= 0.10; 19900's OTM put is untraded
    assert list(es.strikes) == [19500.0, 20100.0, 20500.0]
    assert np.allclose(es.iv, 0.15, atol=1e-4)
    assert list(es.oi_ce) == [1000, 1000, 1000]


def _es(strikes, oi_ce, oi_pe, forward=100.0, t=20 / 365, iv=0.2):
    n = len(strikes)
    return ExpiryStrikes(forward, t, np.array(strikes, float), np.full(n, iv),
                         np.array(oi_ce, float), np.array(oi_pe, float))


def test_sign_convention_call_only_is_plus_one_put_only_is_minus_one():
    calls = day_regime([_es([95, 100, 105], [10, 10, 10], [0, 0, 0])])
    puts = day_regime([_es([95, 100, 105], [0, 0, 0], [10, 10, 10])])
    assert calls.net_norm == pytest.approx(1.0) and calls.sign == 1
    assert puts.net_norm == pytest.approx(-1.0) and puts.sign == -1


def test_flip_found_between_put_and_call_mass():
    e = _es([97, 103], [0, 10], [10, 0])
    r = day_regime([e])
    assert not r.censored
    assert -0.03 < r.flip_x < 0.03

    def net(x):
        s = e.forward * math.exp(-RATE * e.t_years) * (1 + x)
        g = bs_gamma(s, e.strikes, e.t_years, RATE, e.iv)
        return float((g * (e.oi_ce - e.oi_pe)).sum())

    assert net(r.flip_x - 0.001) * net(r.flip_x + 0.001) < 0


def test_no_crossing_is_censored_at_grid_edge_below_spot_when_positive():
    r = day_regime([_es([95, 100, 105], [10, 10, 10], [0, 0, 0])])
    assert r.censored and r.flip_x == pytest.approx(-FLIP_EDGE)
