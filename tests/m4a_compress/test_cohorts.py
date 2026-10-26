"""Cohort construction (state-only) and forward availability status. No forward VALUE is read."""
import dataclasses

import numpy as np
import pandas as pd
import pytest

from scripts.breakout_vol.common import P as BKV_P
from scripts.breakout_vol.engine import build_panel
from scripts.m4a_compress import cohorts as K
from scripts.m4a_compress.common import P
from tests.m4a_compress.synth import make_frames

PS = dataclasses.replace(P, fast=2, slow=4, pct_window=8, quiet=3, base_window=8, horizons=(3,))


def b(*s):
    return np.array([[c == "T" for c in s]])


def test_onset_needs_state_now_and_a_clean_valid_quiet_period():
    valid = b(*"TTTTTTTTTTT"); member = b(*"TTTTTTTTTTT")
    low = b(*"FFFFTTFFFFT"); high = np.zeros_like(low)
    m = K.cohort_masks(low, high, valid, member, quiet=3)
    assert list(np.nonzero(m["comp"][0])[0]) == [4, 10]          # 5 is inside the run, 6.. not in state
    assert list(np.nonzero(m["norm"][0])[0]) == [0, 1, 2, 3, 6, 7, 8, 9]   # literal complement: evaluable member, not low at t


def test_unknown_prior_state_is_not_treated_as_no_compression():
    valid = b(*"TTFTTTTTTTT"); member = b(*"TTTTTTTTTTT")
    low = b(*"FFFFTTFFFFT"); high = np.zeros_like(low)
    m = K.cohort_masks(low, high, valid, member, quiet=3)
    assert not m["comp"][0, 4]                                    # t-3..t-1 contains an unevaluable session
    assert m["comp"][0, 10]


def test_non_members_and_unevaluable_sessions_are_in_no_cohort():
    valid = b(*"TTTTTTTTTTT"); member = b(*"TTTTTTFFFFF")
    low = b(*"FFFFTTFFFFT"); high = np.zeros_like(low)
    m = K.cohort_masks(low, high, valid, member, quiet=3)
    assert not m["comp"][0, 10] and not m["norm"][0, 9] and not m["norm"][0, 8]
    m2 = K.cohort_masks(low, high, b(*"TTTTTTTTTTF"), np.ones_like(member), quiet=3)
    assert not m2["comp"][0, 10]


def test_persistence_comparator_mirrors_onset_on_the_high_tail():
    valid = b(*"TTTTTTTTTTT"); member = b(*"TTTTTTTTTTT")
    high = b(*"FFFFTTFFFFT"); low = np.zeros_like(high)
    m = K.cohort_masks(low, high, valid, member, quiet=3)
    assert list(np.nonzero(m["pers"][0])[0]) == [4, 10]


def test_comp_norm_pers_are_mutually_exclusive_on_real_shaped_data():
    panel, cal, memb, dates = make_frames(E=30, T=400, seed=3)
    pn = build_panel(panel, cal, memb, BKV_P)
    f = K.cohort_flags(pn, "D2", PS)
    assert f["comp"].sum() > 20 and f["norm"].sum() > 1000 and f["pers"].sum() > 20
    assert not (f["comp"] & f["norm"]).any() and not (f["comp"] & f["pers"]).any()
    assert not (f["low"] & f["high"]).any()
    assert (f["comp"] <= f["low"]).all() and not (f["norm"] & f["low"]).any()
    assert (f["comp"] <= pn.member).all() and (f["norm"] <= pn.member).all()


def test_cohort_flags_are_causal():
    panel, cal, memb, dates = make_frames(E=20, T=300, seed=4)
    f = K.cohort_flags(build_panel(panel, cal, memb, BKV_P), "D2", PS)
    t0 = 200
    p2 = panel.copy()
    late = p2["trade_date"] > dates[t0]
    rng = np.random.default_rng(1)
    for col in ("open", "high", "low", "close", "volume", "turnover"):
        p2.loc[late, col] = p2.loc[late, col] * np.exp(rng.normal(0, 0.5, late.sum()))
    g = K.cohort_flags(build_panel(p2, cal, memb, BKV_P), "D2", PS)
    for k in ("comp", "norm", "pers", "low", "high"):
        np.testing.assert_array_equal(f[k][:, :t0 + 1], g[k][:, :t0 + 1])
    np.testing.assert_array_equal(f["pct"][:, :t0 + 1], g["pct"][:, :t0 + 1])


def test_eligibility_needs_the_full_window_history_no_partial_windows():
    panel, cal, memb, dates = make_frames(E=3, T=120, seed=5, holes={1: [60]})
    pn = build_panel(panel, cal, memb, BKV_P)
    f = K.cohort_flags(pn, "D2", PS)
    e0, e1 = pn.entities.index("E00"), pn.entities.index("E01")
    # E01 has no row at session 60: the ratio needs slow+1 rows and the percentile pct_window ratios
    lookback = PS.slow + PS.pct_window - 1                        # sessions of ratio history -> +1 for the prior close
    assert np.isfinite(f["pct"][e0, lookback:]).all()
    assert np.isnan(f["pct"][e1, 60:60 + lookback]).all()
    assert np.isfinite(f["pct"][e1, 60 + lookback + 1:]).all()


def test_forward_status_normal_dropped_beyond():
    valid = b(*"TTTTTTFTTTTTTT")
    st = K.forward_status(valid, 3)
    assert st[0, 0] == K.ST_NORMAL and st[0, 1] == K.ST_NORMAL      # t..t+3 valid
    assert st[0, 3] == K.ST_DROPPED and st[0, 6] == K.ST_DROPPED    # hole inside the window / t itself missing
    assert st[0, 7] == K.ST_NORMAL
    assert st[0, 11] == K.ST_BEYOND and st[0, 13] == K.ST_BEYOND    # window runs past the panel


def test_stage_containment_needs_whole_window_inside_stage():
    sessions = pd.bdate_range("2017-12-20", "2018-01-15").to_numpy(dtype="datetime64[D]")
    lo, hi = K.stage_bounds(sessions, "TRAIN")
    assert sessions[hi] == np.datetime64("2017-12-29")
    lo2, hi2 = K.stage_bounds(sessions, "VAL")
    assert sessions[lo2] == np.datetime64("2018-01-01")
    t = np.array([hi - 5, hi - 3, hi])
    ok = K.in_stage(t, 5, lo, hi)
    assert list(ok) == [True, False, False]                         # exit t+5 must be <= hi
