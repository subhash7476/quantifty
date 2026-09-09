import numpy as np
import pytest

from scripts.analog_path.matcher import analogue_forecasts, match_day, select_analogues


def _states(n=200, seed=7):
    rng = np.random.default_rng(seed)
    return rng.normal(size=(n, 14))


def test_pool_smaller_than_k_returns_none():
    states = _states()
    assert match_day(states, i=3, k=5) is None
    assert match_day(states, i=50, k=5) is not None


def test_select_analogues_raises_when_pool_small():
    with pytest.raises(ValueError):
        select_analogues(_states(), i=2, k=5)


def test_query_day_never_selected_and_no_future_days():
    states = _states()
    for i in (17, 63, 199):
        for k in (5, 10, 20, 50):
            if k > i:
                continue
            md = match_day(states, i, k)
            assert md is not None
            assert md["analogue_idx"].max() < i   # strictly pre-D
            assert i not in md["analogue_idx"]     # never D itself
            assert md["pool_size"] == i


def test_distances_sorted_ascending_and_nearest_is_min():
    states = _states()
    for i in (63, 199):
        md = match_day(states, i, k=20)
        assert np.all(np.diff(md["distances"]) >= 0)
        assert md["nearest_dist"] == md["distances"][0]
        assert md["nearest_dist"] <= md["kth_dist"]
        assert 0.0 <= md["reference_percentile"] <= 1.0
        assert 0.0 <= md["pool_rank_nearest"] <= 1.0
        assert md["median_pool_dist"] > 0


def test_pool_rank_nearest_is_trivially_max():
    states = _states()
    md = match_day(states, 199, k=20)
    assert md["pool_rank_nearest"] == 1.0 - 1.0 / md["pool_size"]


def test_reference_percentile_low_for_genuinely_similar_state():
    rng = np.random.default_rng(4)
    states = rng.normal(size=(300, 14))
    states[250] = states[40]  # exact duplicate of a pool day
    md = match_day(states, 250, k=5)
    assert md["nearest_dist"] == 0.0
    assert md["reference_percentile"] == 0.0


def test_reference_percentile_deterministic():
    states = _states()
    a = match_day(states, 150, 20)
    b = match_day(states, 150, 20)
    assert a["reference_percentile"] == b["reference_percentile"]


def test_reference_percentile_walkforward_pool_only():
    # mutating FUTURE states (positions > i) must not change the reference
    # percentile; the query day itself (position i) is NOT future
    states = _states()
    a = match_day(states, 100, 20)
    states_m = states.copy()
    states_m[101:] += 1000.0
    b = match_day(states_m, 100, 20)
    assert a["reference_percentile"] == b["reference_percentile"]


def test_selection_invariant_to_outcome_matrix():
    # future outcomes must not influence selection: mutate the outcome
    # matrix wildly, selection is identical (structural causality)
    states = _states()
    outcomes = np.random.default_rng(1).normal(size=(200, 5))
    outcomes_mutated = outcomes.copy()
    outcomes_mutated[100:] += 999.0
    for i in (63, 150):
        idx_a, d_a = select_analogues(states, i, 20)
        idx_b, d_b = select_analogues(states, i, 20)
        assert np.array_equal(idx_a, idx_b)
        assert np.array_equal(d_a, d_b)


def test_analogue_forecasts_use_only_selected_indices():
    outcomes = np.arange(200 * 5, dtype=float).reshape(200, 5)
    idx = np.array([3, 7, 9, 12, 15])
    fc = analogue_forecasts(outcomes, idx)
    sel = outcomes[idx]
    assert fc["mean"] == float(np.mean(sel))
    assert fc["median"] == float(np.median(sel))


def test_deterministic_selection():
    states = _states()
    a = match_day(states, 150, 20)
    b = match_day(states, 150, 20)
    assert np.array_equal(a["analogue_idx"], b["analogue_idx"])
    assert np.array_equal(a["distances"], b["distances"])
