"""VWAP-XREV engine tests: VWAP correctness, causality (no look-ahead), strict-bar rules."""
import copy
import datetime as dt

import numpy as np
import pytest

from scripts.vwap_rev import common as C
from scripts.vwap_rev import engine as E


def _session(nsym=3, seed=0):
    rng = np.random.default_rng(seed)
    n = C.N_SLOTS
    base = 100 + 10 * np.arange(nsym)[:, None]
    ret = rng.normal(0, 0.0005, (nsym, n))
    Cc = base * np.exp(np.cumsum(ret, axis=1))
    Oo = np.concatenate([base, Cc[:, :-1]], axis=1)
    Hh = np.maximum(Oo, Cc) * 1.0002
    Ll = np.minimum(Oo, Cc) * 0.9998
    V = rng.integers(100, 1000, (nsym, n)).astype(float)
    return {"symbols": np.array([f"NSE_EQ|S{i}" for i in range(nsym)]),
            "O": Oo.astype(np.float32), "H": Hh.astype(np.float32), "L": Ll.astype(np.float32),
            "C": Cc.astype(np.float32), "V": V.astype(np.float32)}


def test_vwap_matches_bruteforce_typical_and_close():
    s = _session()
    for mode in ("typical", "close"):
        vw, ok = E.session_vwap(s, mode)
        for k in (0, 10, 100, 374):
            for i in range(3):
                tp = ((s["H"][i, :k + 1].astype(float) + s["L"][i, :k + 1] + s["C"][i, :k + 1]) / 3
                      if mode == "typical" else s["C"][i, :k + 1].astype(float))
                v = s["V"][i, :k + 1].astype(float)
                assert vw[i, k] == pytest.approx((tp * v).sum() / v.sum(), rel=1e-9)


def test_vwap_ignores_invalid_bars_and_does_not_impute():
    s = _session()
    for a in ("O", "H", "L", "C", "V"):
        s[a][0, 50:60] = np.nan
    vw, ok = E.session_vwap(s, "typical")
    assert not ok[0, 55]
    keep = np.r_[0:50, 60:101]
    tp = (s["H"][0, keep].astype(float) + s["L"][0, keep] + s["C"][0, keep]) / 3
    v = s["V"][0, keep].astype(float)
    assert vw[0, 100] == pytest.approx((tp * v).sum() / v.sum(), rel=1e-9)


def test_vwap_at_k_is_unchanged_by_future_bars():
    s = _session()
    vw1, _ = E.session_vwap(s, "typical")
    s2 = copy.deepcopy(s)
    for a in ("O", "H", "L", "C", "V"):
        s2[a][:, 200:] = s2[a][:, 200:] * 3.0
    vw2, _ = E.session_vwap(s2, "typical")
    assert np.allclose(vw1[:, :200], vw2[:, :200], equal_nan=True)


def test_z_at_k_is_unchanged_by_future_bars():
    s = _session()
    scale = np.array([0.0005, 0.0006, 0.0007])
    vw, ok = E.session_vwap(s, "typical")
    z1 = E.displacement_z(s, vw, ok, scale, "rms1m")
    s2 = copy.deepcopy(s)
    for a in ("O", "H", "L", "C", "V"):
        s2[a][:, 200:] = s2[a][:, 200:] * 2.0
    vw2, ok2 = E.session_vwap(s2, "typical")
    z2 = E.displacement_z(s2, vw2, ok2, scale, "rms1m")
    kcut = 200 - (E.K_LO - 1)
    assert np.allclose(z1[:, :kcut], z2[:, :kcut], equal_nan=True)


def test_prior_scale_excludes_current_session():
    st = E._State()
    p = E.Params()
    for t in range(20):
        st.hist["A"] = st.hist.get("A", []) + [(t, 0.001, 0.02, 1e6)]
    st.hist["A"].append((20, 0.5, 9.9, 9e9))          # "today"'s own stats appended AFTER use
    sig, rng, adv = E._prior(st, "A", 20, p)          # session 20 must not see row 20
    assert sig == pytest.approx(0.001) and rng == pytest.approx(0.02)


def test_prior_needs_min_sessions():
    st = E._State()
    st.hist["A"] = [(t, 0.001, 0.02, 1e6) for t in range(10)]
    sig, _, _ = E._prior(st, "A", 10, E.Params())
    assert np.isnan(sig)


def test_thresholds_use_only_prior_sessions():
    p = E.Params(pool_sessions=60)
    rng = np.random.default_rng(1)
    pool = [[rng.random(6000).astype(np.float32) for _ in range(E.N_BUCKETS)] for _ in range(100)]
    c1 = E.thresholds(pool, 70, p)
    pool2 = copy.deepcopy(pool)
    pool2[70] = [np.full(6000, 1e6, np.float32) for _ in range(E.N_BUCKETS)]   # session t itself
    pool2[75] = [np.full(6000, 1e6, np.float32) for _ in range(E.N_BUCKETS)]   # the future
    c2 = E.thresholds(pool2, 70, p)
    assert np.allclose(c1, c2)
    assert c1 is not None and np.all(c1 > 0.95) and np.all(c1 < 1.0)


def test_thresholds_none_when_pool_thin():
    p = E.Params()
    pool = [[np.zeros(6000, np.float32) for _ in range(E.N_BUCKETS)] for _ in range(10)]
    assert E.thresholds(pool, 10, p) is None


def test_outcome_direction_and_entry_exit_bars():
    s = _session(nsym=1)
    n = C.N_SLOTS
    # deterministic path: open == previous close, closes fall 1bp/bar after slot 100
    Cc = np.full(n, 100.0)
    Cc[101:] = 100.0 * (1 - 1e-4 * np.arange(1, n - 100))
    s["C"][0] = Cc
    s["O"][0] = np.r_[Cc[0], Cc[:-1]]
    s["H"][0] = np.maximum(s["O"][0], Cc)
    s["L"][0] = np.minimum(s["O"][0], Cc)
    vw, ok = E.session_vwap(s, "close")
    p = E.Params(vwap_mode="close")
    k = 100
    # up-displacement (side=+1) -> short; falling price -> positive reversion return
    out = E._outcomes(s, 0, k, +1, vw, ok, p)
    entry = float(s["O"][0, 101])
    exitp = float(s["C"][0, 105])
    assert out["R_h5"] == pytest.approx(-(exitp / entry - 1) * 1e4, rel=1e-4)
    assert out["R_h5"] > 0
    # down-displacement (side=-1) -> long; same falling path -> negative
    out2 = E._outcomes(s, 0, k, -1, vw, ok, p)
    assert out2["R_h5"] == pytest.approx(-out["R_h5"], rel=1e-9)


def test_outcome_nan_when_exit_bar_missing_no_imputation():
    s = _session(nsym=1)
    for a in ("O", "H", "L", "C", "V"):
        s[a][0, 105] = np.nan
    vw, ok = E.session_vwap(s, "typical")
    out = E._outcomes(s, 0, 100, +1, vw, ok, E.Params())
    assert np.isnan(out["R_h5"]) and np.isfinite(out["R_h10"])


def test_stage_boundaries_are_chronological_and_disjoint():
    prev_hi = None
    for name, lo, hi in E.STAGES:
        assert lo <= hi
        if prev_hi:
            assert lo > prev_hi
        prev_hi = hi
    assert E.stage_of(dt.date(2025, 4, 1)) == "HOLDOUT"
    assert E.stage_of(dt.date(2024, 6, 30)) == "TRAIN"
