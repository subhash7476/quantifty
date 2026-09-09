from datetime import date

import numpy as np

from scripts.analog_path.forecasts import (expanding_baseline,
                                           expanding_return_only, quality,
                                           return_controlled)
from scripts.analog_path.nulls import (block_shift_null,
                                       randomized_matching_null,
                                       sign_permutation_null)


def _data(n=300, seed=3):
    rng = np.random.default_rng(seed)
    r = rng.normal(0, 0.004, n)
    y = rng.normal(0, 0.003, n)
    outcomes = np.column_stack([y + 0.1 * r, y - 0.2 * r])
    return outcomes, r


def _fcast(n=300, seed=5):
    return np.random.default_rng(seed).normal(0, 0.001, n)


def test_expanding_baseline_uses_only_past():
    outcomes, _ = _data()
    f = expanding_baseline(outcomes, 0)
    assert np.isnan(f[0])
    assert f[5] == float(np.mean(outcomes[:5, 0]))
    # mutating future outcomes does not change earlier forecasts
    outcomes_m = outcomes.copy()
    outcomes_m[200:, 0] += 100.0
    f2 = expanding_baseline(outcomes_m, 0)
    assert np.allclose(f[:200], f2[:200], equal_nan=True)
    assert not np.isclose(f2[250], f[250])


def test_expanding_return_only_uses_only_past():
    outcomes, r = _data()
    f = expanding_return_only(outcomes, 0, r)
    assert np.isnan(f[0]) and np.isnan(f[2])
    outcomes_m = outcomes.copy()
    outcomes_m[200:, 0] += 100.0
    f2 = expanding_return_only(outcomes_m, 0, r)
    assert np.allclose(f[:200], f2[:200], equal_nan=True)


def test_quality_metrics_shape():
    outcomes, _ = _data()
    q = quality(_fcast(), outcomes[:, 0])
    assert q["n"] == 300
    assert q["mae"] >= 0 and q["rmse"] >= 0
    assert -1.0 <= q["corr"] <= 1.0
    assert 0.0 <= q["dir_acc"] <= 1.0


def test_quality_constant_forecast_corr_none():
    outcomes, _ = _data()
    q = quality(np.zeros(300), outcomes[:, 0])
    assert q["corr"] is None
    assert q["mae"] >= 0


def test_return_controlled_shape():
    outcomes, r = _data()
    rc = return_controlled(outcomes[:, 0], _fcast(), r)
    assert rc["n"] == 300
    assert rc["beta_analogue"] is not None and rc["beta_R"] is not None
    assert rc["r2_full"] is not None and rc["r2_return_only"] is not None


def test_return_controlled_degenerate_forecast():
    outcomes, r = _data()
    rc = return_controlled(outcomes[:, 0], np.zeros(300), r)
    assert rc["beta_analogue"] is None


def test_randomized_matching_null_causal_and_reproducible():
    outcomes, _ = _data()
    realized = outcomes[:, 0]
    n1 = randomized_matching_null(outcomes, 0, k=10, realized=realized, n_iters=50)
    n2 = randomized_matching_null(outcomes, 0, k=10, realized=realized, n_iters=50)
    assert n1["sample"] == n2["sample"]
    assert len(n1["sample"]) == 50
    assert abs(n1["null_mean"]) < 0.3


def test_block_shift_null_reproducible():
    outcomes, _ = _data()
    dates = [date(2015, 1, 1) + np.timedelta64(i, "D") for i in range(300)]
    f = _fcast()
    n1 = block_shift_null(outcomes[:, 0], f, dates, n_iters=50)
    n2 = block_shift_null(outcomes[:, 0], f, dates, n_iters=50)
    assert n1["sample"] == n2["sample"]
    assert n1["n"] == 50


def test_sign_permutation_null_directional_accuracy_centered():
    outcomes, _ = _data()
    f = _fcast()
    n = sign_permutation_null(outcomes[:, 0], f, n_iters=200)
    assert abs(n["null_mean"] - 0.5) < 0.1
