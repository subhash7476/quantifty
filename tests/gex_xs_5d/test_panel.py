from datetime import date, datetime

import numpy as np
import pytest

from core.analytics.gex_history import ExpiryStrikes
from scripts.gex_xs_5d import panel as P


def test_session_grid_drops_weekends_specials_and_out_of_range():
    dates = [date(2017, 10, 18), date(2017, 10, 19), date(2017, 10, 20), date(2017, 10, 21),
             date(2017, 10, 23), date(2017, 10, 24)]
    assert P.session_grid(dates, date(2017, 10, 18), date(2017, 10, 23)) == [
        date(2017, 10, 18), date(2017, 10, 20), date(2017, 10, 23)]


def test_formation_indices_every_fifth_with_target_inside():
    assert P.formation_indices(16, phase=0) == [0, 5, 10]
    assert P.formation_indices(16, phase=1) == [1, 6]
    assert P.formation_indices(5, phase=0) == []


def _es(fwd, strikes, ivs):
    k = np.array(strikes, float)
    return ExpiryStrikes(fwd, 0.05, k, np.array(ivs, float), np.ones_like(k), np.ones_like(k))


def test_name_valid_needs_six_kept_and_two_each_side_across_expiries():
    near = _es(100, [96, 98, 100, 102], [0.3] * 4)
    far = _es(101, [97, 103], [0.3] * 2)
    assert P.name_valid([near, far])
    assert not P.name_valid([near])                                       # 4 kept
    assert not P.name_valid([_es(100, [90, 100, 101, 102, 103, 104], [0.3] * 6)])  # 1 below


def test_atm_iv_interpolates_in_log_moneyness():
    e = _es(100, [95, 98, 103], [0.40, 0.30, 0.20])
    w = np.log(100 / 98) / np.log(103 / 98)
    assert P.atm_iv(e) == pytest.approx(0.30 + w * (0.20 - 0.30))


def test_atm_iv_none_when_one_side_missing():
    assert P.atm_iv(_es(100, [101, 103], [0.3, 0.3])) is None
    assert P.atm_iv(_es(100, [95, 99], [0.3, 0.3])) is None


def test_atm_iv_exact_strike_at_forward():
    assert P.atm_iv(_es(100, [98, 100, 102], [0.31, 0.25, 0.22])) == pytest.approx(0.25)


def test_iv_expiry_is_nearest_expiring_after_window():
    exps = [date(2024, 3, 28), date(2024, 4, 25), date(2024, 5, 30)]
    assert P.iv_expiry(exps, window_end=date(2024, 3, 28)) == date(2024, 4, 25)
    assert P.iv_expiry(exps, window_end=date(2024, 3, 27)) == date(2024, 3, 28)
    assert P.iv_expiry([], window_end=date(2024, 3, 27)) is None


def test_parkinson():
    assert P.parkinson(110.0, 100.0) == pytest.approx(np.log(1.1) ** 2 / (4 * np.log(2)))
    assert P.parkinson(100.0, 100.0) == 0.0


def _m(bm_date, known, pref="INE123A01", sym="ABC"):
    return {"isin_prefix": pref, "symbol": sym, "bm_date": bm_date, "known_ts": known}


T, T5 = date(2024, 2, 5), date(2024, 2, 12)          # Monday; session t+5 the next Monday
CLOSE = datetime(2024, 2, 5, 15, 30)


@pytest.mark.parametrize("meeting,known,excluded", [
    (date(2024, 2, 8), datetime(2024, 2, 5, 15, 29), True),
    (date(2024, 2, 8), datetime(2024, 2, 5, 15, 31), False),
    (date(2024, 2, 5), datetime(2024, 1, 25, 18, 0), True),     # meeting on t
    (date(2024, 2, 10), datetime(2024, 1, 25, 18, 0), True),    # Saturday inside the span
    (date(2024, 2, 12), datetime(2024, 1, 25, 18, 0), True),    # date of session t+5
    (date(2024, 2, 13), datetime(2024, 1, 25, 18, 0), False),   # day after session t+5
    (date(2024, 2, 2), datetime(2024, 1, 25, 18, 0), False),    # before t
])
def test_results_excluded(meeting, known, excluded):
    idx = P.index_meetings([_m(meeting, known)])
    assert P.results_excluded(idx, "INE123A01", "ABC", T, T5, CLOSE) is excluded


def test_results_excluded_matches_by_symbol_when_prefix_differs():
    idx = P.index_meetings([_m(date(2024, 2, 8), datetime(2024, 2, 1, 10, 0), pref=None)])
    assert P.results_excluded(idx, "INE999Z01", "ABC", T, T5, CLOSE)
    assert not P.results_excluded(idx, "INE999Z01", "XYZ", T, T5, CLOSE)


def test_results_excluded_posthoc_ignores_known_time():
    idx = P.index_meetings([_m(date(2024, 2, 8), datetime(2024, 2, 7, 10, 0))])
    assert not P.results_excluded(idx, "INE123A01", "ABC", T, T5, CLOSE)
    assert P.results_excluded(idx, "INE123A01", "ABC", T, T5, CLOSE, posthoc=True)


def test_winsorize_clips_at_percentiles():
    x = np.arange(1.0, 101.0)
    w = P.winsorize(x)
    assert w.min() == pytest.approx(np.percentile(x, 1))
    assert w.max() == pytest.approx(np.percentile(x, 99))


def test_residual_ic_invariant_to_linear_function_of_controls():
    rng = np.random.default_rng(0)
    n = 200
    C = rng.normal(size=(n, 5))
    N = rng.uniform(-1, 1, n)
    y = -0.3 * N + C @ rng.normal(size=5) + rng.normal(size=n)
    a = P.residual_ic(N, y, C)
    b = P.residual_ic(np.clip(N + 0.05 * C[:, 0], -5, 5), y, C)   # N plus a control: same residual
    assert a == pytest.approx(b, abs=1e-9)
    assert a < 0


def test_nw_test_lag0_equals_iid_t():
    x = np.array([-0.05, 0.01, -0.03, -0.02, 0.0, -0.04, 0.02, -0.01])
    r = P.nw_mean_test(x, lag=0)
    se = np.sqrt(np.mean((x - x.mean()) ** 2) / len(x))
    assert r["t"] == pytest.approx(x.mean() / se)
    assert 0 < r["p_one_sided"] < 0.5


def test_nw_test_positive_autocorrelation_widens_se():
    x = np.repeat([-0.04, 0.02, -0.03, 0.01, -0.02, 0.0], 4).astype(float)
    assert abs(P.nw_mean_test(x, lag=4)["t"]) < abs(P.nw_mean_test(x, lag=0)["t"])


def test_ac1():
    assert P.ac1(np.array([1.0, -1.0, 1.0, -1.0, 1.0, -1.0])) < -0.8
