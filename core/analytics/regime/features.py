"""Regime features — Garman-Klass, efficiency ratio, normalized drift.

Design: `docs/superpowers/specs/2026-09-09-n200-regime-hmm-design.md` §5.

Every window is trailing. Nothing here may read a bar at or after the row it
describes, and nothing may compute a threshold from a window containing the row
it is applied to — the fold barrier (§8) covers winsorization bounds and
standardization moments as well as model parameters, so both are fitted on the
fit window and passed in rather than recomputed per call.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

GK_BASELINE_WINDOW = 252
GK_SHORT_WINDOW = 5
GK_LONG_WINDOW = 60
KER_WINDOW = 20
DRIFT_WINDOW = 20
WINSOR_SIGMA = 3.0
GK_FLOOR_PERCENTILE = 1.0

FEATURE_NAMES = ("gk_vol_z", "gk_ratio_st", "ker_20", "drift_t")

_LN2_TERM = 2.0 * np.log(2.0) - 1.0


def garman_klass(open_: np.ndarray, high: np.ndarray, low: np.ndarray,
                 close: np.ndarray) -> np.ndarray:
    """Daily GK variance: 0.5·ln(H/L)² − (2ln2 − 1)·ln(C/O)².

    A zero-range row (H = L) forces O = C = H = L in this substrate, so GK is
    exactly zero there rather than negative — 2.63% of rows, per the preflight.
    Those zeros are what `gk_floor` exists to handle.
    """
    hl = np.log(np.asarray(high, float) / np.asarray(low, float))
    co = np.log(np.asarray(close, float) / np.asarray(open_, float))
    return 0.5 * hl * hl - _LN2_TERM * co * co


def gk_floor_value(gk: np.ndarray, percentile: float = GK_FLOOR_PERCENTILE) -> float:
    """Floor for one stock: the given percentile of its own non-zero GK.

    Fitted on the fit window only and frozen — a floor recomputed on the filter
    year would let that year's own distribution set its scale.
    """
    positive = gk[gk > 0]
    if positive.size == 0:
        return float(np.finfo(float).tiny)
    return float(np.percentile(positive, percentile))


@dataclass(frozen=True)
class Normalization:
    """Winsorization bounds and standardization moments, fitted on the fit window."""
    lower: np.ndarray
    upper: np.ndarray
    mean: np.ndarray
    std: np.ndarray

    def apply(self, x: np.ndarray) -> np.ndarray:
        clipped = np.clip(np.asarray(x, float), self.lower, self.upper)
        return (clipped - self.mean) / np.where(self.std > 0, self.std, 1.0)

    def to_dict(self) -> dict:
        return {"lower": self.lower.tolist(), "upper": self.upper.tolist(),
                "mean": self.mean.tolist(), "std": self.std.tolist()}


def fit_normalization(x: np.ndarray, n_sigma: float = WINSOR_SIGMA) -> Normalization:
    x = np.asarray(x, float)
    mu, sd = np.nanmean(x, axis=0), np.nanstd(x, axis=0)
    lower, upper = mu - n_sigma * sd, mu + n_sigma * sd
    clipped = np.clip(x, lower, upper)
    return Normalization(lower=lower, upper=upper,
                         mean=np.nanmean(clipped, axis=0),
                         std=np.nanstd(clipped, axis=0))


def build_features(frame: pd.DataFrame, gk_floor: float) -> pd.DataFrame:
    """Raw (un-normalized) features from OHLC, ordered by date."""
    gk = garman_klass(frame["open"].to_numpy(), frame["high"].to_numpy(),
                      frame["low"].to_numpy(), frame["close"].to_numpy())
    return features_from_gk(pd.Series(gk, index=frame.index),
                            frame["close"].astype(float), gk_floor)


def features_from_gk(gk_s: pd.Series, close: pd.Series,
                     gk_floor: float) -> pd.DataFrame:
    """Raw features from a precomputed GK series — the fold path.

    `build_panel.py` already stores GK per row, and the floor is a fit-window
    quantity that changes per fold, so folds re-floor a stored series rather
    than recomputing it from OHLC ten times.

    Rows inside the warmup carry NaN and are dropped by the caller — never
    filled, since a filled warmup row is a fabricated observation.
    """
    close = close.astype(float)
    gk_s = pd.Series(np.maximum(gk_s.astype(float).to_numpy(), gk_floor),
                     index=close.index)

    baseline = gk_s.rolling(GK_BASELINE_WINDOW, min_periods=GK_BASELINE_WINDOW).median()
    gk_vol_z = np.log(gk_s / baseline)

    short = gk_s.rolling(GK_SHORT_WINDOW, min_periods=GK_SHORT_WINDOW).mean()
    long = gk_s.rolling(GK_LONG_WINDOW, min_periods=GK_LONG_WINDOW).mean()
    gk_ratio_st = np.log(short / long)

    net = (close - close.shift(KER_WINDOW)).abs()
    path = close.diff().abs().rolling(KER_WINDOW, min_periods=KER_WINDOW).sum()
    ker = net / path.where(path > 0)

    ret = np.log(close / close.shift(DRIFT_WINDOW))
    daily_sd = np.log(close / close.shift(1)).rolling(
        DRIFT_WINDOW, min_periods=DRIFT_WINDOW).std()
    drift = ret / (daily_sd * np.sqrt(DRIFT_WINDOW)).where(daily_sd > 0)

    return pd.DataFrame({"gk_vol_z": gk_vol_z, "gk_ratio_st": gk_ratio_st,
                         "ker_20": ker, "drift_t": drift}, index=close.index)


def forward_realized_vol(gk: np.ndarray, horizon: int = 5) -> np.ndarray:
    """sqrt of summed GK variance over t+1 .. t+horizon — the gate's target (§10.1).

    Strictly forward and therefore an evaluation label only: it must never enter
    a feature. The last `horizon` rows are NaN because their window is unfinished.
    """
    gk = np.asarray(gk, float)
    out = np.full(gk.shape[0], np.nan)
    if gk.shape[0] > horizon:
        csum = np.concatenate([[0.0], np.cumsum(gk)])
        idx = np.arange(gk.shape[0] - horizon)
        out[idx] = np.sqrt(csum[idx + 1 + horizon] - csum[idx + 1])
    return out


def trailing_tercile_cuts(values: np.ndarray, window: int = GK_BASELINE_WINDOW,
                          min_periods: int = 60) -> tuple[np.ndarray, np.ndarray]:
    """Per-row 33rd/67th percentile of `values` over the trailing `window`,
    ending at t-1 (§10.1).

    The shift is the whole point: a quantile computed over a window containing
    the row it labels leaks the answer into the label.
    """
    s = pd.Series(np.asarray(values, float)).shift(1)
    lo = s.rolling(window, min_periods=min_periods).quantile(1 / 3)
    hi = s.rolling(window, min_periods=min_periods).quantile(2 / 3)
    return lo.to_numpy(), hi.to_numpy()
