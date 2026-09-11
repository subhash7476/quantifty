"""Pre-specified signal slate for the RELIANCE daily Long/Flat research.

Every signal is causal: the signal at day t uses only data through the
close of day t; it decides the position held for the t -> t+1 return.

Slate (frozen before any evaluation; drawn from the regime literature):

  S0  always_long        unconditional benchmark (buy and hold)
  S1  ts_mom_{63,126,252}  time-series momentum: long iff trailing N-day
                           return (skipping the most recent day, the
                           Moskowitz-Ooi-Pedersen convention) is positive
  S2  sma_{50,100,200}   trend: long iff close above its N-day moving average
  S3  donchian_{63,252}  breakout: long iff close exceeds the prior N-day
                           high (excluding today)
  S4  reversal_5         short-term contrarian: long iff the 5-day return
                           (including today) is negative
  S5  vol_calm           volatility-state gate (Moreira-Muir in Long/Flat
                           form): long only while trailing 20d realized
                           volatility sits at or below the 70th percentile
                           of its trailing 252d window
  S6  idx_trend          market-regime filter: long only while Nifty closes
                           above its 200-day SMA
  S7  combined           the regime-conditioned trend construct:
                           ts_mom_252 AND vol_calm AND idx_trend
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _ts_return(close: pd.Series, n: int) -> pd.Series:
    return close / close.shift(n) - 1.0


def always_long(panel: pd.DataFrame) -> pd.Series:
    return pd.Series(1, index=panel.index, dtype=float)


def ts_mom(panel: pd.DataFrame, n: int) -> pd.Series:
    r = _ts_return(panel["close"], n).shift(1)  # skip the most recent day
    return (r > 0).astype(float)


def sma_trend(panel: pd.DataFrame, n: int) -> pd.Series:
    s = panel["close"].rolling(n).mean()
    return (panel["close"] > s).astype(float)


def donchian(panel: pd.DataFrame, n: int) -> pd.Series:
    prior_high = panel["high"].shift(1).rolling(n).max()
    return (panel["close"] > prior_high).astype(float)


def reversal(panel: pd.DataFrame, n: int = 5) -> pd.Series:
    r = _ts_return(panel["close"], n)
    return (r < 0).astype(float)


def vol_calm(panel: pd.DataFrame, rv_window: int = 20,
             pct_window: int = 252, threshold: float = 0.70) -> pd.Series:
    rv = panel["ret"].rolling(rv_window).std()
    pct = rv.rolling(pct_window).apply(
        lambda w: (w[:-1] < w[-1]).mean(), raw=True)
    return (pct <= threshold).astype(float)


def idx_trend(panel: pd.DataFrame, n: int = 200) -> pd.Series:
    s = panel["nifty"].rolling(n).mean()
    return (panel["nifty"] > s).astype(float)


def combined(panel: pd.DataFrame) -> pd.Series:
    return ts_mom(panel, 252) * vol_calm(panel) * idx_trend(panel)


SIGNALS = {
    "always_long": always_long,
    "ts_mom_63": lambda p: ts_mom(p, 63),
    "ts_mom_126": lambda p: ts_mom(p, 126),
    "ts_mom_252": lambda p: ts_mom(p, 252),
    "sma_50": lambda p: sma_trend(p, 50),
    "sma_100": lambda p: sma_trend(p, 100),
    "sma_200": lambda p: sma_trend(p, 200),
    "donchian_63": lambda p: donchian(p, 63),
    "donchian_252": lambda p: donchian(p, 252),
    "reversal_5": reversal,
    "vol_calm": vol_calm,
    "idx_trend": idx_trend,
    "combined": combined,
}


def build_signals(panel: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=panel.index)
    for name, fn in SIGNALS.items():
        out[name] = fn(panel)
    return out
