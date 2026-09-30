import math

import numpy as np
import pandas as pd
import pytest

from scripts.breakout_vol import classify as K
from scripts.breakout_vol import stats as S


def manual_nw(vals, pos, lag):
    """Pure-python NW on an irregular calendar, written independently of stats.nw_gap_test."""
    n = len(vals)
    mean = sum(vals) / n
    z = {p: v - mean for p, v in zip(pos, vals)}
    g0 = sum(v * v for v in z.values()) / n
    lrv = g0
    for k in range(1, lag + 1):
        gk = sum(z[p] * z[p + k] for p in z if (p + k) in z) / n
        lrv += 2 * (1 - k / (lag + 1)) * gk
    se = math.sqrt(lrv / n)
    return mean, se, mean / se


def test_nw_gap_matches_manual_with_gaps():
    rng = np.random.default_rng(0)
    pos = np.sort(rng.choice(np.arange(400), size=150, replace=False))
    x = rng.normal(0.4, 1.0, 150) + 0.5 * np.sin(pos / 7.0)
    r = S.nw_gap_test(x, pos, 5)
    mean, se, t = manual_nw(list(x), list(pos), 5)
    assert (r["mean"], r["se"], r["t"]) == pytest.approx((mean, se, t), rel=1e-12)


def test_nw_gap_reduces_to_contiguous_formula():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, 300)
    r = S.nw_gap_test(x, np.arange(300), 4)
    xm = x - x.mean()
    lrv = xm @ xm / 300 + 2 * sum((1 - k / 5) * (xm[:-k] @ xm[k:]) / 300 for k in range(1, 5))
    assert r["se"] == pytest.approx(math.sqrt(lrv / 300))


def test_nw_matches_statsmodels_hac_kernel():
    from statsmodels.stats.sandwich_covariance import S_hac_simple
    rng = np.random.default_rng(2)
    pos = np.sort(rng.choice(np.arange(500), size=200, replace=False))
    x = rng.normal(0.2, 1.0, 200)
    r = S.nw_gap_test(x, pos, 6)
    dense = np.zeros(pos[-1] - pos[0] + 1)
    dense[pos - pos[0]] = x - x.mean()
    Sm = float(S_hac_simple(dense.reshape(-1, 1), nlags=6)[0, 0])
    assert r["se"] == pytest.approx(math.sqrt(Sm) / 200, rel=1e-9)


def test_event_contrast_equals_difference_in_means():
    rng = np.random.default_rng(3)
    y = rng.normal(0, 50, 400)
    b = rng.random(400) < 0.3
    g1 = rng.integers(0, 40, 400)
    g2 = rng.integers(0, 120, 400)
    r = S.event_contrast_cluster(y, b, g1, g2)
    assert r["b"] == pytest.approx(y[b].mean() - y[~b].mean(), rel=1e-12)


def test_permutation_is_roughly_uniform_under_the_null_and_detects_a_shift():
    rng = np.random.default_rng(4)
    n_dates, per = 80, 6
    did = np.repeat(np.arange(n_dates), per)
    isb = np.tile([True, True, False, False, False, False], n_dates)
    f_null = rng.normal(0, 10, len(did))
    p_null = S.paired_permutation(f_null, isb, did, 1500, 1)["p_one"]
    assert 0.02 < p_null < 0.98
    f_shift = f_null + 8 * isb
    assert S.paired_permutation(f_shift, isb, did, 1500, 1)["p_one"] < 0.01


def _cell(N, H, side, p, d, bound_p=None, bound_d=1.0):
    return dict(N=N, H=H, side=side, d_p_one=p, d_mean=d, bound_d_mean=bound_d,
                bound_d_p_one=p if bound_p is None else bound_p)


def _tab(ps, ds=None):
    keys = [(20, 5, "up"), (20, 5, "dn"), (20, 20, "up"), (20, 20, "dn"),
            (63, 5, "up"), (63, 5, "dn"), (63, 20, "up"), (63, 20, "dn")]
    ds = ds or [1.0] * 8
    return pd.DataFrame([_cell(*k, p, d) for k, p, d in zip(keys, ps, ds)])


NULL = [0.5, 0.6, 0.4, 0.7, 0.8, 0.3, 0.9, 0.55]


def test_tree_C5_when_nothing_confirms_in_val():
    r = K.classify(_tab(NULL), None)
    assert r["label"] == "C5" and not r["val_confirmed"]


def test_tree_C6_when_val_confirms_and_holdout_unread():
    ps = [0.001] + NULL[1:]
    r = K.classify(_tab(ps), None)
    assert r["label"] == "C6" and len(r["val_confirmed"]) == 1


def test_tree_C5_when_holdout_read_and_fails():
    r = K.classify(_tab([0.001] + NULL[1:]), _tab(NULL))
    assert r["label"] == "C5" and r["holdout_read"] and not r["holdout_confirmed"]


def test_tree_C7_vs_C8_by_economic_gate():
    v = _tab([0.001] + NULL[1:])
    h = _tab([0.002] + NULL[1:])
    assert K.classify(v, h, econ_pass={(20, 5, "up"): False})["label"] == "C7"
    assert K.classify(v, h, econ_pass={(20, 5, "up"): True})["label"] == "C8"


def test_tree_wrong_sign_and_fragility_do_not_confirm():
    ps = [0.001] + NULL[1:]
    assert K.classify(_tab(ps, ds=[-1.0] + [1.0] * 7), None)["label"] == "C5"
    v = _tab(ps)
    v.loc[0, "bound_d_mean"] = -0.1
    assert K.classify(v, None)["label"] == "C5"


def test_tree_defect_precedence_and_holm_uses_all_eight_cells():
    assert K.classify(_tab([0.001] + NULL[1:]), None, defects=["hash mismatch"])["label"] == "C4"
    # p = 0.01 alone passes at Holm-8? 8*0.01 = 0.08 > 0.05 -> not confirmed
    assert K.classify(_tab([0.01] + NULL[1:]), None)["label"] == "C5"
