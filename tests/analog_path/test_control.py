from datetime import date

import numpy as np

from scripts.analog_path.control import TOL, run_control


def _data(n=400, seed=11):
    rng = np.random.default_rng(seed)
    R = rng.normal(0, 0.004, n)
    # outcomes depend on shape: two regimes keyed on a shape feature
    shape = rng.normal(0, 1, n)
    y = 0.002 * shape + 0.3 * R + rng.normal(0, 0.003, n)
    outcomes = np.column_stack([y, rng.normal(0, 0.003, n)])
    # states: C rows where distance correlates with shape
    C = np.column_stack([shape[:, None] * np.ones((1, 13)),
                         np.zeros(n)])  # 14 cols, last = 0
    return C, R, outcomes


def test_tolerance_is_frozen_10bp():
    assert TOL == 0.001


def test_control_runs_and_reports_structure():
    C, R, O = _data()
    out = run_control(C, R, O, [date(2015, 1, 1)] * len(R),
                      horizon_keys=("h0", "h1"))
    assert out["n_groups"] > 0
    assert out["n_groups"] == len(out["group_sizes"])
    for key, v in out["horizons"].items():
        assert v["n"] == out["n_groups"]
        assert v["mean_diff"] is not None
        assert v["null"] is not None and v["null"]["n"] > 0
        assert len(v["null"]["sample"]) == v["null"]["n"]


def test_control_matched_sets_are_causal():
    # matched sets come strictly from the past: build outcome arrays where
    # future rows are poisoned; early-query differences must not change
    C, R, O = _data()
    out = run_control(C, R, O, [date(2015, 1, 1)] * len(R),
                      horizon_keys=("h0", "h1"))
    O2 = O.copy()
    O2[300:, :] += 999.0
    out2 = run_control(C, R, O2, [date(2015, 1, 1)] * len(R),
                       horizon_keys=("h0", "h1"))
    # groups built from query days i < 300 should be identical in size
    sizes = np.asarray(out["group_sizes"])
    sizes2 = np.asarray(out2["group_sizes"])
    assert out["n_groups"] >= out2["n_groups"]
    # every group in out2 is a prefix subset of out's groups
    assert np.array_equal(sizes[:len(sizes2)], sizes2)


def test_control_deterministic():
    C, R, O = _data()
    a = run_control(C, R, O, [date(2015, 1, 1)] * len(R),
                    horizon_keys=("h0", "h1"))
    b = run_control(C, R, O, [date(2015, 1, 1)] * len(R),
                    horizon_keys=("h0", "h1"))
    assert a["horizons"]["h0"]["mean_diff"] == b["horizons"]["h0"]["mean_diff"]
    assert a["horizons"]["h0"]["null"]["sample"] == b["horizons"]["h0"]["null"]["sample"]


def test_control_effect_recoverable_on_strong_shape_signal():
    # outcome is convex in shape around a fixed regime point: days whose
    # shape is close to the query (near-half) must systematically differ
    # from the far half -> the machinery must recover a large negative d
    rng = np.random.default_rng(42)
    n = 600
    R = rng.normal(0, 0.004, n)
    shape = rng.normal(0, 1, n)
    y = 0.004 * (shape - 0.3) ** 2 + 0.3 * R + rng.normal(0, 0.003, n)
    O = np.column_stack([y])
    C = np.column_stack([np.outer(shape, np.ones(13)), np.zeros(n)])
    out = run_control(C, R, O, [date(2015, 1, 1)] * n, horizon_keys=("close",))
    v = out["horizons"]["close"]
    assert v["n"] > 100
    assert v["nw_t"] < -2.0
    assert v["mean_diff"] < 0
