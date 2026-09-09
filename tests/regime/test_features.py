"""Regime feature tests — §5 and §10.1 of the N200 design spec.

The load-bearing ones are the causality tests: every feature window is trailing,
and the gate's tercile cut is computed from data ending at t-1. Both are the kind
of defect that produces good-looking results and no error message.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.analytics.regime.features import (
    FEATURE_NAMES, build_features, fit_normalization, forward_realized_vol,
    garman_klass, gk_floor_value, trailing_tercile_cuts,
)


def make_frame(n: int = 400, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    open_ = close * np.exp(rng.normal(0, 0.004, n))
    span = np.abs(rng.normal(0, 0.008, n))
    high = np.maximum(open_, close) * np.exp(span)
    low = np.minimum(open_, close) * np.exp(-span)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close},
                        index=pd.RangeIndex(n))


def test_garman_klass_is_zero_on_a_zero_range_bar():
    gk = garman_klass(np.array([100.0]), np.array([100.0]),
                      np.array([100.0]), np.array([100.0]))
    assert gk[0] == pytest.approx(0.0)


def test_garman_klass_rises_with_range():
    narrow = garman_klass(np.array([100.0]), np.array([101.0]),
                          np.array([99.0]), np.array([100.0]))
    wide = garman_klass(np.array([100.0]), np.array([110.0]),
                        np.array([90.0]), np.array([100.0]))
    assert wide[0] > narrow[0] > 0


def test_gk_floor_uses_only_non_zero_values():
    gk = np.array([0.0, 0.0, 1e-6, 2e-6, 5e-6])
    assert gk_floor_value(gk, percentile=50.0) == pytest.approx(2e-6)


def test_features_are_nan_through_warmup_and_finite_after():
    f = build_features(make_frame(), gk_floor=1e-9)
    assert list(f.columns) == list(FEATURE_NAMES)
    assert f.iloc[:251].isna().any(axis=1).all()
    assert f.iloc[300:].notna().all(axis=1).all()


def test_features_are_trailing_only():
    """Appending future bars must not change any already-computed row."""
    frame = make_frame(500, seed=4)
    early = build_features(frame.iloc[:300], gk_floor=1e-9)
    full = build_features(frame, gk_floor=1e-9)
    pd.testing.assert_frame_equal(early.iloc[260:300], full.iloc[260:300])


def test_efficiency_ratio_is_one_on_a_pure_trend_and_low_on_chop():
    n = 100
    trend = pd.DataFrame({"open": np.arange(1, n + 1) * 1.0,
                          "high": np.arange(1, n + 1) * 1.0 + 0.5,
                          "low": np.arange(1, n + 1) * 1.0 - 0.5,
                          "close": np.arange(1, n + 1) * 1.0})
    ker_trend = build_features(trend, gk_floor=1e-9)["ker_20"].iloc[-1]
    assert ker_trend == pytest.approx(1.0, abs=1e-9)

    saw = 100 + np.tile([0.0, 1.0], n // 2)
    chop = pd.DataFrame({"open": saw, "high": saw + 0.5,
                         "low": saw - 0.5, "close": saw})
    assert build_features(chop, gk_floor=1e-9)["ker_20"].iloc[-1] < 0.1


def test_forward_realized_vol_looks_forward_and_truncates_the_tail():
    gk = np.array([1.0, 4.0, 4.0, 4.0, 4.0, 4.0, 9.0])
    out = forward_realized_vol(gk, horizon=5)
    assert out[0] == pytest.approx(np.sqrt(20.0))
    assert np.isnan(out[-5:]).all()


def test_tercile_cuts_exclude_the_row_they_label():
    """Changing a row must not move that row's own cut — but must move the next.

    An earlier version of this test asserted `hi[t] < values[t]` over a monotone
    series, which passes with or without the shift and so could not detect the
    leak it existed to catch. This version is a direct probe of the property.
    """
    rng = np.random.default_rng(0)
    base = rng.normal(size=300)
    spiked = base.copy()
    spiked[200] = 500.0

    _, hi_base = trailing_tercile_cuts(base, window=100, min_periods=10)
    _, hi_spiked = trailing_tercile_cuts(spiked, window=100, min_periods=10)

    assert hi_base[200] == pytest.approx(hi_spiked[200]), (
        "row 200 moved its own tercile cut — the cut is reading the row it labels"
    )
    assert hi_base[201] != pytest.approx(hi_spiked[201]), (
        "row 200 never entered a later window — the shift skipped it entirely"
    )


def test_tercile_cuts_are_trailing_only():
    rng = np.random.default_rng(2)
    values = rng.normal(size=300)
    _, hi_full = trailing_tercile_cuts(values, window=100, min_periods=10)
    _, hi_early = trailing_tercile_cuts(values[:200], window=100, min_periods=10)
    assert np.allclose(hi_full[150:200], hi_early[150:200], equal_nan=True)


def test_normalization_is_frozen_from_the_fit_window():
    fit = np.random.default_rng(0).normal(0, 1, (500, 4))
    norm = fit_normalization(fit)
    shifted = np.random.default_rng(1).normal(8, 5, (200, 4))
    out = norm.apply(shifted)
    # a filter year that is wilder than the fit window must not re-scale itself:
    # it gets clipped at the fit window's bounds and stays far from zero mean
    assert out.mean() > 1.0
    assert np.all(np.isfinite(out))
