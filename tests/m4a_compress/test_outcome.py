"""M4a outcome module (the ONLY module that reads t+1.. prices): hand-computed cases and timing."""
import dataclasses

import numpy as np
import pandas as pd
import pytest

from scripts.breakout_vol.common import P as BKV_P
from scripts.breakout_vol.engine import build_panel
from scripts.m4a_compress import cohorts as K
from scripts.m4a_compress import outcome as O
from scripts.m4a_compress import state as S
from scripts.m4a_compress.common import P
from tests.m4a_compress.synth import make_frames

PS = dataclasses.replace(P, fast=2, slow=4, pct_window=8, quiet=3, base_window=6, horizons=(3, 5))


def test_range_expansion_is_forward_mean_over_trailing_median_of_daily_range():
    rng = np.array([[np.nan, 1.0, 2.0, 9.0, 4.0, 6.0, 8.0, 3.0, 5.0, 7.0, 2.0, 4.0]])
    E = O.range_expansion(rng, h=3, base=4)
    # t=5: forward = mean(rng[6..8]) = (8+3+5)/3 ; baseline = median(rng[2..5]) = median(2,9,4,6) = 5
    assert E[0, 5] == pytest.approx(((8 + 3 + 5) / 3) / 5.0)
    assert E[0, 8] == pytest.approx(((7 + 2 + 4) / 3) / np.median([6, 8, 3, 5]))
    assert np.isnan(E[0, 2])                                      # baseline window (needs 4 finite values) incomplete
    assert np.isnan(E[0, 9]) and np.isnan(E[0, 11])               # forward window runs past the data


def test_baseline_never_uses_sessions_after_t_and_forward_never_uses_t_or_before():
    rng = np.array([np.linspace(1.0, 2.0, 30)])
    rng[0, 5:] = np.random.default_rng(0).uniform(0.5, 3, 25)
    E0 = O.range_expansion(rng, 3, 6)
    r2 = rng.copy(); r2[0, 18:] *= 7.0                            # everything from t0+1+h... changes; t0 = 12, h = 3 -> window 13..15
    E1 = O.range_expansion(r2, 3, 6)
    np.testing.assert_array_equal(E0[0, :15], E1[0, :15])          # E(t) for t <= 14 needs at most t+3 <= 17
    r3 = rng.copy(); r3[0, 12] *= 7.0                              # touch t0 itself: enters the baseline, not the forward mean
    E2 = O.range_expansion(r3, 3, 6)
    assert E2[0, 12] != E0[0, 12]
    fwd_only = rng.copy(); fwd_only[0, 14] *= 7.0                  # inside t0's forward window
    assert O.range_expansion(fwd_only, 3, 6)[0, 12] != E0[0, 12]


def test_zero_baseline_gives_nan_not_inf():
    rng = np.zeros((1, 12)); rng[0, 8:] = 1.0
    assert np.isnan(O.range_expansion(rng, 3, 4)[0, 6])


def test_vol_and_abs_expansion_use_trailing_rms_of_log_returns():
    C = np.array([[100.0, 101.0, 99.0, 102.0, 100.0, 103.0, 101.0, 104.0, 102.0, 105.0, 103.0, 99.0]])
    ret = S.log_return(C)
    ev = O.vol_expansion(ret, h=3, base=4)
    base_rms = np.sqrt(np.mean(ret[0, 4:8] ** 2))                 # t=7: r[4..7]
    fwd_rms = np.sqrt(np.mean(ret[0, 8:11] ** 2))
    assert ev[0, 7] == pytest.approx(fwd_rms / base_rms)
    ea = O.abs_expansion(ret, h=3, base=4)
    assert ea[0, 7] == pytest.approx(abs(np.log(C[0, 10] / C[0, 7])) / (np.sqrt(3) * base_rms))
    sg = O.signed_move(ret, h=3, base=4)
    assert sg[0, 7] == pytest.approx(np.log(C[0, 10] / C[0, 7]) / (np.sqrt(3) * base_rms))


def test_attach_reads_own_row_and_reports_forward_status():
    panel, cal, memb, dates = make_frames(E=14, T=200, seed=7, cut={2: 150}, holes={3: [120]})
    pn = build_panel(panel, cal, memb, BKV_P)
    f = K.cohort_flags(pn, "D2", PS)
    ev = K.events_frame(pn, f)
    out = O.attach(pn, ev, PS)
    for h in PS.horizons:
        for col in (f"E_range{h}", f"E_vol{h}", f"E_abs{h}", f"E_sgn{h}", f"status{h}"):
            assert col in out
    r = out[out["status3"] == K.ST_NORMAL].iloc[5]
    rng = S.daily_range(pn.H, pn.L, pn.C)
    e, t = int(r["e"]), int(r["t"])
    want = np.mean(rng[e, t + 1:t + 4]) / np.median(rng[e, t - PS.base_window + 1:t + 1])
    assert r["E_range3"] == pytest.approx(want)
    assert out.loc[out["status3"] != K.ST_NORMAL, "E_range3"].isna().all()   # unresolved windows carry no value
    assert (out["status3"] == K.ST_DROPPED).any() and (out["status3"] == K.ST_BEYOND).any()


def test_attach_does_not_depend_on_data_beyond_the_window():
    panel, cal, memb, dates = make_frames(E=14, T=200, seed=8)
    pn = build_panel(panel, cal, memb, BKV_P)
    ev = K.events_frame(pn, K.cohort_flags(pn, "D2", PS))
    a = O.attach(pn, ev, PS)
    p2 = panel.copy()
    late = p2["trade_date"] > dates[150]
    rng = np.random.default_rng(2)
    for col in ("open", "high", "low", "close"):
        p2.loc[late, col] = p2.loc[late, col] * np.exp(rng.normal(0, 0.3, late.sum()))
    pn2 = build_panel(p2, cal, memb, BKV_P)
    b = O.attach(pn2, ev, PS)
    early = a["t"] + 5 <= 150
    np.testing.assert_allclose(a.loc[early, "E_range5"], b.loc[early, "E_range5"], equal_nan=True)
