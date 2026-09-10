from datetime import date

import numpy as np
import pandas as pd

from scripts.reliance_regime.evaluate import backtest, regime_buckets
from scripts.reliance_regime.signals import always_long, ts_mom


def _panel(n=600, seed=5):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0003, 0.01, n)
    close = 1000.0 * np.cumprod(1 + rets)
    dates = pd.date_range("2015-01-01", periods=n)
    df = pd.DataFrame({"close": close, "ret": rets}, index=dates)
    df["high"] = close * 1.01
    df["nifty"] = 10000.0 * np.cumprod(1 + rng.normal(0.0002, 0.008, n))
    df.index = df.index.date
    return df


def test_backtest_always_long_matches_buy_and_hold():
    p = _panel()
    b = backtest(p, always_long(p))
    # gross over the same valid window (first day position is NaN)
    ann = float(p["ret"].iloc[1:].mean()) * 252
    assert b["ann_net_return"] < ann
    assert b["ann_net_return"] > ann - 0.10
    assert b["in_market_fraction"] > 0.99


def test_backtest_flat_signal_no_returns():
    p = _panel()
    b = backtest(p, pd.Series(0.0, index=p.index))
    assert abs(b["net_mean_daily"]) < 1e-10
    assert b["round_trips"] == 0


def test_backtest_fees_only_on_trades():
    p = _panel()
    sig = pd.Series(np.where(np.arange(len(p)) % 100 == 0, 1.0, 0.0),
                    index=p.index)
    b = backtest(p, sig)
    assert b["round_trips"] > 0
    assert b["fees_paid_fraction"] > 0
    # one signal day per 100 days => ~6 buys + 6 sells over 600 days
    assert 2.0 < b["trades_per_year"] < 7.0


def test_regime_buckets_structure():
    p = _panel()
    rb = regime_buckets(p, always_long(p))
    assert set(rb) == {"vol_bucket_0", "vol_bucket_1", "vol_bucket_2"}
    assert all(v["n"] > 0 for v in rb.values())


def test_backtest_ci_contains_mean():
    p = _panel()
    b = backtest(p, always_long(p))
    assert b["ci95_lo"] <= b["net_mean_daily"] <= b["ci95_hi"]


def test_backtest_deterministic():
    p = _panel()
    a = backtest(p, ts_mom(p, 63))
    b = backtest(p, ts_mom(p, 63))
    assert a == b
