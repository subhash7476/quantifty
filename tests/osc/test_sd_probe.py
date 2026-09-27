"""Tests for OSC SD/Breadth Probe — Black-76, parity forward, and fence."""
import math

import numpy as np
import pytest
from scipy import stats

from scripts.osc.sd_probe import (
    black76_delta,
    black76_price,
    black76_vega,
    implied_vol,
    _parity_forward,
    _assert_fence,
)


class TestBlack76:
    """Hand-computed values verified against online BSM calculators (switching to Black-76)."""

    def test_call_price_atm(self):
        F, K, sigma, T = 100.0, 100.0, 0.20, 1.0
        price = black76_price(F, K, sigma, T, "CE")
        assert price > 0
        expected = math.exp(-0.065) * 100 * (stats.norm.cdf(0.10) - stats.norm.cdf(-0.10))
        assert abs(price - expected) < 1e-8

    def test_put_price_atm(self):
        F, K, sigma, T = 100.0, 100.0, 0.20, 1.0
        price = black76_price(F, K, sigma, T, "PE")
        # put = call on futures (put-call parity: C = P when K=F in Black-76)
        expected = math.exp(-0.065) * 100 * (stats.norm.cdf(0.10) - stats.norm.cdf(-0.10))
        assert abs(price - expected) < 1e-8

    def test_call_delta_atm(self):
        F, K, sigma, T = 100.0, 100.0, 0.20, 1.0
        delta = black76_delta(F, K, sigma, T, "CE")
        assert 0.45 < delta < 0.55

    def test_call_delta_deep_itm(self):
        F, K, sigma, T = 100.0, 60.0, 0.20, 1.0
        delta = black76_delta(F, K, sigma, T, "CE")
        assert delta > 0.90

    def test_put_delta_deep_otm(self):
        F, K, sigma, T = 100.0, 50.0, 0.20, 1.0
        delta = black76_delta(F, K, sigma, T, "PE")
        assert delta < 0 and abs(delta) < 0.10

    def test_vega_positive(self):
        F, K, sigma, T = 100.0, 100.0, 0.20, 1.0
        vega = black76_vega(F, K, sigma, T)
        assert vega > 0

    def test_vega_scales_with_T(self):
        vega_short = black76_vega(100.0, 100.0, 0.20, 0.25)
        vega_long = black76_vega(100.0, 100.0, 0.20, 1.0)
        assert vega_short < vega_long

    def test_iv_roundtrip_call(self):
        F, K, sigma, T = 100.0, 105.0, 0.25, 0.5
        price = black76_price(F, K, sigma, T, "CE")
        iv = implied_vol(price, F, K, T, "CE")
        assert abs(iv - sigma) < 1e-4

    def test_iv_roundtrip_put(self):
        F, K, sigma, T = 100.0, 95.0, 0.30, 0.75
        price = black76_price(F, K, sigma, T, "PE")
        iv = implied_vol(price, F, K, T, "PE")
        assert abs(iv - sigma) < 1e-4

    def test_iv_nan_on_zero_price(self):
        iv = implied_vol(0.0, 100.0, 100.0, 0.5, "CE")
        assert np.isnan(iv)

    def test_iv_nan_on_negative_T(self):
        iv = implied_vol(5.0, 100.0, 100.0, -0.1, "CE")
        assert np.isnan(iv)


class TestParityForward:
    def test_exact_parity(self):
        import pandas as pd
        F_true = 100.0
        r = 0.065
        T = 30 / 365
        K = 100.0
        from scripts.osc.sd_probe import black76_price as b76
        from scripts.osc.sd_probe import R
        # Forward-known pricing: C-P = exp(-rT)*(F-K)
        call_px = b76(F_true, K, 0.20, T, "CE")
        put_px = b76(F_true, K, 0.20, T, "PE")
        diff = call_px - put_px
        assert abs(diff - math.exp(-R * T) * (F_true - K)) < 1e-6

    def test_parity_forward_no_common(self):
        import pandas as pd
        td = pd.Timestamp("2024-06-14")
        ed = pd.Timestamp("2024-07-25")
        calls = pd.DataFrame({"strike": [100.0], "settle": [5.0]})
        puts = pd.DataFrame({"strike": [105.0], "settle": [6.0]})
        F = _parity_forward(calls, puts, ed, td)
        assert np.isnan(F)


class TestFence:
    def test_fence_pass(self, monkeypatch):
        import pandas as pd
        df = pd.DataFrame({"trade_date": [pd.Timestamp("2024-06-15")]})
        _assert_fence(df)  # should not raise

    def test_fence_fail_early(self, monkeypatch):
        import pandas as pd
        df = pd.DataFrame({"trade_date": [pd.Timestamp("2022-12-31")]})
        with pytest.raises(AssertionError, match="FENCE VIOLATION"):
            _assert_fence(df)

    def test_fence_fail_late(self, monkeypatch):
        import pandas as pd
        df = pd.DataFrame({"trade_date": [pd.Timestamp("2026-01-01")]})
        with pytest.raises(AssertionError, match="FENCE VIOLATION"):
            _assert_fence(df)
