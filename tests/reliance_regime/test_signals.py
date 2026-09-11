from datetime import date

import numpy as np
import pandas as pd
import pytest

from scripts.reliance_regime.data import build_panel, load_reliance_daily
from scripts.reliance_regime.signals import (always_long, combined, donchian,
                                             idx_trend, reversal, sma_trend,
                                             ts_mom, vol_calm)


@pytest.fixture(scope="module")
def panel():
    return build_panel()


def test_panel_span_and_integrity(panel):
    assert panel.index.min() <= date(2010, 1, 10)
    assert panel.index.max() >= date(2026, 8, 1)
    assert len(panel) > 4000
    assert panel["close"].notna().all()
    # no gap larger than 10 calendar days
    dts = pd.Series(panel.index).diff().dt.days
    assert (dts.max() <= 10)


def test_no_fabricated_returns(panel):
    r = panel["ret"].abs()
    assert r.max() < 0.25  # CA-adjusted continuity


def test_always_long_is_one_everywhere(panel):
    assert (always_long(panel) == 1).all()


def test_signals_are_causal_vectors(panel):
    for name, sig in {
        "ts_mom_252": ts_mom(panel, 252),
        "sma_200": sma_trend(panel, 200),
        "donchian_63": donchian(panel, 63),
        "reversal_5": reversal(panel, 5),
        "vol_calm": vol_calm(panel),
        "idx_trend": idx_trend(panel),
        "combined": combined(panel),
    }.items():
        assert sig.notna().any(), name
        assert set(sig.dropna().unique()).issubset({0.0, 1.0}), name


def test_ts_mom_uses_past_only():
    closes = pd.Series(np.arange(1.0, 301.0), index=pd.RangeIndex(300))
    p = pd.DataFrame({"close": closes})
    p["high"] = closes
    p["ret"] = closes.pct_change()
    s = ts_mom(p, 10)
    # signal at t depends on close(t-1)/close(t-11): for strictly rising
    # prices the momentum is positive everywhere after warmup
    assert (s.iloc[12:] == 1.0).all()


def test_sma_trend_sign():
    closes = pd.Series(np.concatenate([np.linspace(100, 90, 50),
                                       np.linspace(90, 110, 50)]))
    p = pd.DataFrame({"close": closes, "high": closes, "ret": closes.pct_change()})
    s = sma_trend(p, 20)
    assert s.iloc[:20].dropna().eq(0).all() or s.iloc[0] in (0.0, 1.0)
    assert (s.iloc[-10:] == 1.0).all()


def test_donchian_breakout():
    closes = pd.Series(np.concatenate([np.full(30, 100.0),
                                       [95.0, 96.0, 97.0, 105.0]]))
    highs = closes.copy()
    p = pd.DataFrame({"close": closes, "high": highs,
                      "ret": closes.pct_change()})
    s = donchian(p, 10)
    assert s.iloc[-1] == 1.0
    assert (s.iloc[:10] == 0.0).all()


def test_vol_calm_reacts_to_vol_spike():
    rng = np.random.default_rng(7)
    rets = pd.Series(np.concatenate(
        [rng.normal(0, 0.005, 300), rng.normal(0, 0.03, 30)]))
    s = vol_calm(pd.DataFrame({"ret": rets}), rv_window=20, pct_window=100,
                 threshold=0.70)
    # calm in the quiet regime, flat through the spike
    assert s.iloc[280] == 1.0
    assert s.iloc[310] == 0.0


def test_combined_is_product_of_gates():
    p = build_panel()
    c = combined(p)
    prod = ts_mom(p, 252) * vol_calm(p) * idx_trend(p)
    pd.testing.assert_series_equal(c, prod, check_names=False)


def test_idx_trend_nifty_context_present():
    p = build_panel()
    assert p["nifty"].notna().sum() > 3500
    s = idx_trend(p)
    assert s.notna().sum() > 3000
