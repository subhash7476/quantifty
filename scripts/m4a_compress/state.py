"""M4a-CE compression state: pure functions of information at or before t. No forward quantity exists here.

All arrays are (entities x sessions). A window that is not complete (any missing input) yields NaN - never a
partial window, never an imputed value. `daily_range` for session s uses that session's OWN prior-session
close C[s-1]; if session s-1 has no valid row the value is missing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from scripts.m4a_compress.common import P, Params

_TOL = 1e-12


def prior_close(C: np.ndarray) -> np.ndarray:
    out = np.full_like(C, np.nan)
    out[:, 1:] = C[:, :-1]
    return out


def daily_range(H: np.ndarray, L: np.ndarray, C: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return (H - L) / prior_close(C)


def log_return(C: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.log(C / prior_close(C))


def _roll(a: np.ndarray, n: int):
    return pd.DataFrame(a.T).rolling(n, min_periods=n)


def rolling_mean(a: np.ndarray, n: int) -> np.ndarray:
    return _roll(a, n).mean().to_numpy().T


def rolling_std(a: np.ndarray, n: int) -> np.ndarray:
    return _roll(a, n).std(ddof=1).to_numpy().T


def rolling_median(a: np.ndarray, n: int) -> np.ndarray:
    return _roll(a, n).median().to_numpy().T


def _ratio(fast: np.ndarray, slow: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        r = fast / slow
    return np.where(np.isfinite(r) & (slow > 0), r, np.nan)


def atr_ratio(rng: np.ndarray, fast: int, slow: int) -> np.ndarray:
    return _ratio(rolling_mean(rng, fast), rolling_mean(rng, slow))


def rv_ratio(ret: np.ndarray, fast: int, slow: int) -> np.ndarray:
    return _ratio(rolling_std(ret, fast), rolling_std(ret, slow))


def compression_ratio(H: np.ndarray, L: np.ndarray, C: np.ndarray, variant: str, p: Params = P) -> np.ndarray:
    """D2 = ATR_fast/ATR_slow of (H-L)/C[s-1] (primary); D1 = std(r, fast)/std(r, slow) of log returns (robustness)."""
    if variant == "D2":
        return atr_ratio(daily_range(H, L, C), p.fast, p.slow)
    if variant == "D1":
        return rv_ratio(log_return(C), p.fast, p.slow)
    raise ValueError(f"unknown variant {variant!r}")


def trailing_pct_rank(x: np.ndarray, w: int) -> np.ndarray:
    """pct[t] = #{s in t-w+1..t : x[s] <= x[t]} / w  (window ends at t and includes t; ties count as <=).
    NaN unless the whole w-window is present."""
    E, T = x.shape
    out = np.full((E, T), np.nan)
    if T < w:
        return out
    for e in range(E):
        win = sliding_window_view(x[e], w)                       # (T-w+1, w)
        ok = np.isfinite(win).all(axis=1)
        cnt = (win <= x[e, w - 1:, None]).sum(axis=1)
        out[e, w - 1:] = np.where(ok, cnt / w, np.nan)
    return out


def tail_flags(pct: np.ndarray, q_low: float, q_high: float) -> tuple[np.ndarray, np.ndarray]:
    """low = pct <= q_low (compression); high = pct >= q_high (persistence comparator). NaN -> False."""
    with np.errstate(invalid="ignore"):
        return pct <= q_low + _TOL, pct >= q_high - _TOL
