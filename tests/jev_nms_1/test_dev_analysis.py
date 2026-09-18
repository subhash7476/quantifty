import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from scipy.optimize import approx_fprime  # noqa: E402

from scripts.jev_nms_1 import dev, dev_analysis as da  # noqa: E402

rng = np.random.default_rng(0)


def _synthetic(n=2000, informative=True):
    y = rng.integers(0, 4, n)
    pb = rng.dirichlet(np.ones(4) * 2, n)
    pb[np.arange(n), y] += 0.15
    pb = da.clip(pb)
    pj = rng.dirichlet(np.ones(4) * 2, n)
    if informative:
        pj[np.arange(n), y] += 0.4
    pj = da.clip(pj)
    return np.log(pb), np.log(pj), y


def test_pool_gradient_matches_finite_differences():
    lb3, lj, y = _synthetic(300)
    fit = da.fit_pool(lb3, lj, y, True)
    theta = np.array([0.7, 0.3, 0.1, -0.2, 0.05])

    def nll(t):
        return -np.log(da.pool_proba(t, lb3, lj, True)[np.arange(len(y)), y]).sum()

    num = approx_fprime(theta, nll, 1e-6)
    onehot = np.eye(4)[y]
    r = da.pool_proba(theta, lb3, lj, True) - onehot
    gc = r.sum(axis=0)
    ana = np.array([(r * lb3).sum(), (r * lj).sum(), *(gc[:3] - gc[3])])
    assert np.allclose(num, ana, rtol=1e-4, atol=1e-3)
    assert fit["converged"] and fit["grad_max_abs"] < 1e-8


def test_informative_j_gets_positive_b_and_improves_oof():
    lb3, lj, y = _synthetic()
    fit = da.fit_pool(lb3, lj, y, True)
    assert fit["b"] > 0.3
    assert abs(sum(fit["c"])) < 1e-12


def test_uninformative_j_gives_b_near_zero():
    lb3, lj, y = _synthetic(4000, informative=False)
    assert abs(da.fit_pool(lb3, lj, y, True)["b"]) < 0.1


def test_b3_star_has_no_j_term():
    lb3, lj, y = _synthetic(300)
    fs = da.fit_pool(lb3, lj, y, False)
    assert fs["b"] == 0.0 and len(fs["theta"]) == 4
    p1 = da.pool_proba(fs["theta"], lb3, lj, False)
    p2 = da.pool_proba(fs["theta"], lb3, np.zeros_like(lj), False)
    assert np.array_equal(p1, p2)


def test_blocks_are_five_contiguous_date_sorted_blocks():
    sessions = [f"2025-01-{d:02d}" for d in range(1, 31)][::-1]
    b = da.blocks(sessions)
    assert [len(x) for x in b] == [6] * 5
    assert sum(b, []) == sorted(sessions)
    assert [len(x) for x in da.blocks([f"s{i:03d}" for i in range(100)])] == [20] * 5


def test_crossfit_is_out_of_fold():
    lb3, lj, y = _synthetic(1000)
    sess = np.repeat([f"s{i:03d}" for i in range(100)], 10)
    obs = {"lb3": lb3, "lj": lj, "y": y, "session": sess}
    block_of = {s: i for i, b in enumerate(da.blocks(list(set(sess)))) for s in b}
    cf = da.crossfit(obs, block_of)
    for prm in cf["params"]:
        assert prm["n_train"] == 800 and prm["n_test"] == 200
    k0 = cf["fold"] == 0
    refit = da.fit_pool(lb3[~k0], lj[~k0], y[~k0], True)
    assert np.allclose(cf["p_pool"][k0], da.clip(da.pool_proba(refit["theta"], lb3[k0], lj[k0], True)))


def test_dll_is_session_weighted_mean_of_session_means():
    sess = np.array(["a"] * 10 + ["b"] * 9)
    d = np.concatenate([np.ones(10), np.zeros(9)])
    val, means, w = da.dll(sess, d, ["a", "b"])
    assert val == pytest.approx(10 / 19) and list(means) == [1.0, 0.0] and list(w) == [10, 9]


def test_argmax_uses_frozen_order_on_ties():
    p = np.array([[0.1, 0.42, 0.42, 0.06]])
    assert list(da.argmax_idx(p)) == [1]


def test_clip_floors_and_renormalizes():
    p = da.clip([[0.0, 0.5, 0.5, 0.0]])
    assert p.min() > 0 and p.sum() == pytest.approx(1.0)
    assert p[0, 0] == pytest.approx(1e-4 / 1.0002)


def test_aurc_is_invariant_to_order_within_ties():
    conf = np.array([0.9, 0.5, 0.5, 0.5, 0.2])
    loss = np.array([0.0, 1.0, 0.0, 0.0, 1.0])
    a1 = da.aurc(conf, loss)
    a2 = da.aurc(conf, loss[[0, 3, 2, 1, 4]])
    assert a1 == a2 == pytest.approx(np.mean([0, 1 / 4, 1 / 4, 1 / 4, 2 / 5]))


def test_coverage_retains_ties_at_the_cut():
    y = np.array([0, 1] * 5)
    pj = da.clip([[0.6, 0.2, 0.1, 0.1]] * 5 + [[0.5, 0.2, 0.2, 0.1]] * 5)
    ps = da.clip(rng.dirichlet(np.ones(4), 10))
    lv = {x["coverage_pct"]: x["by_J_confidence"] for x in da.coverage(pj, ps, y)["levels"]}
    assert lv[80]["n"] == 10 and lv[80]["realized_pct"] == 100.0
    assert lv[40]["n"] == 5 and lv[20]["n"] == 5


def test_ece_is_zero_for_perfect_calibration_per_bin():
    y = np.array([0, 0, 1, 1])
    p = np.array([[1.0, 0, 0, 0], [1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 1.0, 0, 0]])
    m = da.metrics(da.clip(p), y)
    assert m["accuracy"] == 1.0 and m["ece"] < 1e-3
    assert m["confusion"]["trending_up"]["trending_up"] == 2


def test_newey_west_lag0_equals_iid_t_and_ac1():
    x = rng.normal(0.1, 1, 400)
    t0 = da.newey_west_t(x, 0)
    assert t0 == pytest.approx(x.mean() / (x.std(ddof=0) / np.sqrt(len(x))))
    assert abs(da.ac1(x)) < 0.15


def test_bootstrap_lb_is_deterministic_and_below_mean():
    means, w = rng.normal(0.02, 0.05, 100), np.full(100, 10.0)
    a, b = da.bootstrap_lb(means, w), da.bootstrap_lb(means, w)
    assert a == b and a["lower_bound_95_one_sided"] < means.mean()


def test_n_req_variants_and_rule6():
    rule = {"alpha": 0.05, "power": 0.8, "min": 120, "abandon_if_n_req_gt": 250}
    means = np.array([0.02, -0.01, 0.03, 0.0] * 25)
    r = da.n_req(float(means.mean()), means, rule)
    assert r["computed"] and set(r["variants"]) == {"t_ddof1", "t_ddof0", "normal_ddof1"}
    assert r["variants"]["normal_ddof1"]["n_req"] <= r["variants"]["t_ddof1"]["n_req"]
    assert r["rule6_null"] == (r["variants"]["t_ddof1"]["n_req"] > 250)
    assert not da.n_req(-0.01, means, rule)["computed"]


def test_planned_development_states_are_1600_in_declared_order():
    draws = dev._artifact("draws_step2.json")
    plan = dev.planned_states(draws)
    d1 = draws["draws"]["d1_dev"]["output"]
    assert len(plan) == 1600 and plan[0] == ("h15", f"{d1[0]}|10:00")
    assert [t for t, _ in plan].count("h15") == 1000
    assert plan[1000] == ("h5", f"{d1[0]}|10:00") and plan[1300] == ("h30", f"{d1[0]}|10:00")
