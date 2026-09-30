import numpy as np
import pytest

from scripts.vwap_rev import stats as S


def test_nw_matches_naive_when_iid():
    rng = np.random.default_rng(0)
    x = rng.normal(0.3, 1.0, 4000)
    r = S.nw_mean_test(x)
    naive_se = x.std(ddof=1) / np.sqrt(len(x))
    assert r["se"] == pytest.approx(naive_se, rel=0.15)
    assert 0.0 < r["p_one"] < 1e-6


def test_nw_inflates_se_under_positive_autocorrelation():
    rng = np.random.default_rng(1)
    e = rng.normal(size=3000)
    x = np.zeros(3000)
    for i in range(1, 3000):
        x[i] = 0.8 * x[i - 1] + e[i]
    naive = x.std(ddof=1) / np.sqrt(len(x))
    assert S.nw_mean_test(x)["se"] > 1.5 * naive


def test_null_series_not_rejected_and_bootstrap_agrees():
    rng = np.random.default_rng(2)
    x = rng.normal(0, 1, 500)
    nw = S.nw_mean_test(x)
    bb = S.block_bootstrap_mean(x, n_boot=2000)
    assert nw["p_one"] > 0.01
    assert bb["ci_lo"] < 0 < bb["ci_hi"] or abs(x.mean()) < 0.1
    assert abs(nw["p_one"] - bb["p_one"]) < 0.15


def test_bootstrap_detects_true_effect():
    rng = np.random.default_rng(3)
    x = rng.normal(0.5, 1, 400)
    bb = S.block_bootstrap_mean(x, n_boot=2000)
    assert bb["p_one"] < 0.01 and bb["ci_lo"] > 0


def test_twoway_cluster_wider_than_naive_with_common_shocks():
    rng = np.random.default_rng(4)
    dates = np.repeat(np.arange(200), 20)
    stocks = np.tile(np.arange(20), 200)
    shock = rng.normal(0, 1, 200)[dates]
    y = shock + rng.normal(0, 0.3, 4000)
    r = S.twoway_cluster_mean(y, stocks, dates)
    naive = y.std(ddof=1) / np.sqrt(len(y))
    assert r["se"] > 3 * naive


def test_holm_monotone_and_bounded():
    adj = S.holm({"a": 0.001, "b": 0.02, "c": 0.04, "d": 0.5})
    assert adj["a"] == pytest.approx(0.004) and adj["b"] == pytest.approx(0.06)
    assert adj["c"] == pytest.approx(0.08) and adj["d"] == pytest.approx(0.5)
    assert all(0 <= v <= 1 for v in adj.values())


def test_mde_scales_with_sqrt_n():
    assert S.mde_session(10, 100) == pytest.approx(2 * S.mde_session(10, 400))
