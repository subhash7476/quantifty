"""M4a state module: hand-computed toy cases, strict windows, causality. No forward information anywhere."""
import dataclasses

import numpy as np
import pytest

from scripts.m4a_compress import state as S
from scripts.m4a_compress.common import P

PS = dataclasses.replace(P, fast=2, slow=4, pct_window=5, quiet=3, base_window=5)


def test_daily_range_uses_each_days_own_prior_close():
    H = np.array([[11.0, 12.0, 13.0]])
    L = np.array([[9.0, 10.0, 12.0]])
    C = np.array([[10.0, 11.0, 12.5]])
    rng = S.daily_range(H, L, C)
    assert np.isnan(rng[0, 0])                                  # no prior close on the first session
    assert rng[0, 1] == pytest.approx((12 - 10) / 10.0)
    assert rng[0, 2] == pytest.approx((13 - 12) / 11.0)


def test_daily_range_is_nan_when_prior_row_missing():
    H = np.array([[11.0, 12.0, 13.0]]); L = np.array([[9.0, 10.0, 12.0]])
    C = np.array([[10.0, np.nan, 12.5]])
    H[0, 1] = L[0, 1] = np.nan
    rng = S.daily_range(H, L, C)
    assert np.isnan(rng[0, 1]) and np.isnan(rng[0, 2])          # t=2 needs C[1], which is missing


def test_rolling_windows_are_strict_no_partial_windows():
    x = np.array([[1.0, 2.0, 3.0, np.nan, 5.0, 6.0, 7.0]])
    m = S.rolling_mean(x, 3)
    assert m[0, 2] == pytest.approx(2.0)
    assert np.isnan(m[0, 3]) and np.isnan(m[0, 4]) and np.isnan(m[0, 5])   # any NaN in window -> NaN
    assert m[0, 6] == pytest.approx(6.0)
    assert np.isnan(m[0, 0]) and np.isnan(m[0, 1])


def test_rolling_std_is_sample_std_ddof1():
    x = np.array([[1.0, 4.0, 9.0, 16.0]])
    s = S.rolling_std(x, 3)
    assert s[0, 2] == pytest.approx(np.std([1, 4, 9], ddof=1))
    assert s[0, 3] == pytest.approx(np.std([4, 9, 16], ddof=1))


def test_atr_ratio_is_fast_over_slow_mean_of_daily_range():
    rng = np.array([[np.nan, 1.0, 2.0, 3.0, 4.0, 5.0]])
    r = S.atr_ratio(rng, fast=2, slow=4)
    assert r[0, 4] == pytest.approx(((3 + 4) / 2) / ((1 + 2 + 3 + 4) / 4))
    assert r[0, 5] == pytest.approx(((4 + 5) / 2) / ((2 + 3 + 4 + 5) / 4))
    assert np.isnan(r[0, 3])                                    # slow window incomplete


def test_rv_ratio_is_std_of_log_returns_fast_over_slow():
    C = np.array([[100.0, 101.0, 99.0, 102.0, 100.0, 103.0, 101.0]])
    ret = S.log_return(C)
    r = S.rv_ratio(ret, fast=2, slow=4)
    assert r[0, 5] == pytest.approx(np.std(ret[0, 4:6], ddof=1) / np.std(ret[0, 2:6], ddof=1))


def test_trailing_pct_rank_counts_window_values_le_current_including_self():
    x = np.array([[5.0, 3.0, 4.0, 1.0, 2.0, 9.0]])
    p = S.trailing_pct_rank(x, 5)
    assert np.isnan(p[0, :4]).all()
    assert p[0, 4] == pytest.approx(2 / 5)                      # window [5,3,4,1,2]: {1,2} <= 2
    assert p[0, 5] == pytest.approx(5 / 5)                      # window [3,4,1,2,9]: all <= 9
    assert S.trailing_pct_rank(np.array([[7.0, 7.0, 7.0]]), 3)[0, 2] == pytest.approx(1.0)   # ties count as <=


def test_trailing_pct_rank_is_nan_if_any_window_value_missing():
    x = np.array([[5.0, 3.0, np.nan, 1.0, 2.0, 9.0]])
    p = S.trailing_pct_rank(x, 3)
    assert np.isnan(p[0, 2]) and np.isnan(p[0, 3]) and np.isnan(p[0, 4])
    assert np.isfinite(p[0, 5])


def test_thresholds_low_at_most_q_high_at_least_one_minus_q():
    pct = np.array([[50 / 252, 51 / 252, 201 / 252, 202 / 252]])
    low, high = S.tail_flags(pct, q_low=0.20, q_high=0.80)
    assert list(low[0]) == [True, False, False, False]          # 50/252 = .198 <= .20 ; 51/252 = .2024 is not
    assert list(high[0]) == [False, False, False, True]         # 201/252 = .7976 < .80 ; 202/252 = .8016 >= .80


def test_state_at_t_is_causal_and_window_includes_t():
    rng_ = np.random.default_rng(0)
    E, T = 4, 40
    C = 100 * np.exp(np.cumsum(rng_.normal(0, 0.01, (E, T)), axis=1))
    H, L = C * 1.01, C * 0.99
    a = S.compression_ratio(H, L, C, "D2", PS)
    pa = S.trailing_pct_rank(a, PS.pct_window)
    t0 = 25
    H2, L2, C2 = H.copy(), L.copy(), C.copy()
    for arr in (H2, L2, C2):
        arr[:, t0 + 1:] *= np.exp(rng_.normal(0, 0.5, (E, T - t0 - 1)))
    b = S.compression_ratio(H2, L2, C2, "D2", PS)
    pb = S.trailing_pct_rank(b, PS.pct_window)
    np.testing.assert_array_equal(pa[:, :t0 + 1], pb[:, :t0 + 1])          # nothing after t0 touches state up to t0
    H3, L3, C3 = H.copy(), L.copy(), C.copy()
    for arr in (H3, L3, C3):
        arr[:, t0] *= 1.3                                                    # perturb t0 itself
    c = S.trailing_pct_rank(S.compression_ratio(H3, L3, C3, "D2", PS), PS.pct_window)
    assert not np.array_equal(pa[:, t0], c[:, t0])                           # the window does include t


def test_compression_ratio_rejects_unknown_variant():
    with pytest.raises(ValueError):
        S.compression_ratio(np.ones((1, 10)), np.ones((1, 10)), np.ones((1, 10)), "D9", PS)


def test_ratio_is_nan_not_inf_when_slow_atr_is_zero():
    C = np.full((1, 12), 100.0)
    r = S.compression_ratio(C.copy(), C.copy(), C, "D2", PS)                 # H == L == C: zero range
    assert np.isnan(r).all()
