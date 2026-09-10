from datetime import date

import numpy as np
import pandas as pd
import pytest

from scripts.reliance_regime.intraday import (VENDOR_FIRST, VENDOR_LAST,
                                              dip_fill, load_day, profile)
from scripts.reliance_regime.timing_study import _trades, run
from scripts.reliance_regime.signals import sma_trend


@pytest.fixture(scope="module")
def panel():
    from scripts.reliance_regime.data import build_panel
    return build_panel()


def test_vendor_window_bounds():
    assert VENDOR_FIRST == date(2015, 2, 2)
    assert VENDOR_LAST == date(2025, 8, 6)
    assert load_day(date(2014, 12, 31)) is None
    assert load_day(date(2025, 8, 7)) is None
    df = load_day(date(2020, 6, 15))
    assert df is not None and len(df) >= 350


def test_profile_vendor_and_fallback():
    df = load_day(date(2020, 6, 15))
    p = profile(date(2020, 6, 15), None)
    assert p.sourced_from == "vendor_1m"
    assert p.low <= p.open and p.low <= p.close
    assert p.high >= p.open and p.high >= p.close
    assert p.low <= p.vwap <= p.high
    # outside vendor span: fallback must use the daily row
    fb = profile(date(2012, 6, 4), {"open": 100.0, "high": 102.0,
                                    "low": 99.0, "close": 101.0})
    assert fb.sourced_from == "daily_fallback"
    assert fb.open == 100.0


def test_dip_fill_logic():
    from scripts.reliance_regime.data import load_reliance_daily
    daily = load_reliance_daily()
    d = date(2020, 6, 15)
    row = daily.loc[d].to_dict()
    p = profile(d, row)
    mid = (p.low + p.close) / 2.0
    # limit between low and close -> touched -> fill at limit
    assert dip_fill(d, mid, row) == mid
    # limit far below the low -> fill at close
    assert dip_fill(d, p.low - 100.0, row) == p.close


def test_trades_reconstruction_causal(panel):
    trades = _trades(panel)
    assert len(trades) > 10
    sig = sma_trend(panel, 200).fillna(0.0)
    # every entry day has signal on; every exit day has signal off
    for t in trades:
        assert sig.loc[t["entry"]] > 0.5
        assert sig.loc[t["exit"]] <= 0.5
        assert t["entry"] < t["exit"]


def test_timing_study_runs_and_baseline_positive(panel):
    r = run()
    v = r["variants"]["close_E / close_X (baseline)"]
    assert v["n"] > 5
    assert v["n"] == r["n_trades_study"]
    assert v["ann_net"] is not None
    # the infeasible low-entry bound must dominate the baseline
    lb = r["variants"]["low_E1 / close_X (infeasible bound)"]
    assert lb["mean_gross_per_trade"] > v["mean_gross_per_trade"]


def test_timing_study_deterministic():
    a = run()
    b = run()
    assert a == b


def test_vendor_profile_rescaled_to_daily_close(panel):
    from scripts.reliance_regime.data import load_reliance_daily
    daily = load_reliance_daily()
    d = date(2020, 6, 15)
    p = profile(d, daily.loc[d].to_dict())
    assert p.sourced_from == "vendor_1m"
    # rescaling by the same-day close ratio aligns the level exactly
    assert abs(p.close - float(daily.loc[d, "close"])) < 1e-9
    assert p.low <= p.open and p.low <= p.close
    assert p.high >= p.open and p.high >= p.close
    assert p.low <= p.vwap <= p.high
