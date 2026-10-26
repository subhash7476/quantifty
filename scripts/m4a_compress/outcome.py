"""M4a-CE forward outcomes - the ONLY module that reads sessions after t. Called only after the freeze.

For a formation at session t and horizon h, everything forward uses sessions t+1..t+h; every baseline uses
sessions <= t (window ending at t). Missing input anywhere in a window -> NaN (strict windows, no imputation).

  E_range  primary : mean_{t+1..t+h}((H-L)/C[s-1]) / median_{t-base+1..t}((H-L)/C[s-1])
  E_vol    report  : sqrt(mean r^2 over t+1..t+h) / sqrt(mean r^2 over t-base+1..t)
  E_abs    report  : |sum r over t+1..t+h| / (sqrt(h) * sqrt(mean r^2 over t-base+1..t))
  E_sgn    descr.  : (sum r over t+1..t+h) / (sqrt(h) * same baseline)   - signed, never tested
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.m4a_compress import cohorts as K
from scripts.m4a_compress import state as S
from scripts.m4a_compress.common import P, Params


def _shift_back(a: np.ndarray, h: int) -> np.ndarray:
    """out[t] = a[t+h] (NaN where t+h is past the panel)."""
    out = np.full_like(a, np.nan)
    if h < a.shape[1]:
        out[:, : a.shape[1] - h] = a[:, h:]
    return out


def _safe_div(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        r = num / den
    return np.where(np.isfinite(r) & (den > 0), r, np.nan)


def forward_mean(a: np.ndarray, h: int) -> np.ndarray:
    return _shift_back(S.rolling_mean(a, h), h)                         # mean of a[t+1..t+h]


def forward_sum(a: np.ndarray, h: int) -> np.ndarray:
    return _shift_back(pd.DataFrame(a.T).rolling(h, min_periods=h).sum().to_numpy().T, h)


def range_expansion(rng: np.ndarray, h: int, base: int) -> np.ndarray:
    return _safe_div(forward_mean(rng, h), S.rolling_median(rng, base))


def _base_rms(ret: np.ndarray, base: int) -> np.ndarray:
    return np.sqrt(S.rolling_mean(ret ** 2, base))


def vol_expansion(ret: np.ndarray, h: int, base: int) -> np.ndarray:
    return _safe_div(np.sqrt(forward_mean(ret ** 2, h)), _base_rms(ret, base))


def abs_expansion(ret: np.ndarray, h: int, base: int) -> np.ndarray:
    return _safe_div(np.abs(forward_sum(ret, h)), np.sqrt(h) * _base_rms(ret, base))


def signed_move(ret: np.ndarray, h: int, base: int) -> np.ndarray:
    den = np.sqrt(h) * _base_rms(ret, base)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = forward_sum(ret, h) / den
    return np.where(np.isfinite(r) & (den > 0), r, np.nan)


def attach(pn, ev: pd.DataFrame, p: Params = P) -> pd.DataFrame:
    """Adds, per horizon h: status{h} (availability), E_range{h}, E_vol{h}, E_abs{h}, E_sgn{h}. A value is kept only
    for a `normal` window; the event set itself is fixed by the state and never depends on these values."""
    ev = ev.copy()
    rng = S.daily_range(pn.H, pn.L, pn.C)
    ret = S.log_return(pn.C)
    ei, ti = ev["e"].to_numpy(), ev["t"].to_numpy()
    for h in p.horizons:
        st = K.forward_status(pn.valid, h)[ei, ti]
        ev[f"status{h}"] = st
        ok = st == K.ST_NORMAL
        for name, arr in (("E_range", range_expansion(rng, h, p.base_window)),
                          ("E_vol", vol_expansion(ret, h, p.base_window)),
                          ("E_abs", abs_expansion(ret, h, p.base_window)),
                          ("E_sgn", signed_move(ret, h, p.base_window))):
            ev[f"{name}{h}"] = np.where(ok, arr[ei, ti], np.nan)
    return ev
