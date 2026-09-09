"""Walk-forward forecasts and quality metrics.

All forecasts are causal: for query day i, only pool data (positions < i)
is used.

  - baseline    : expanding mean of pool outcomes
  - return_only : expanding OLS of outcome on open->12:30 return, evaluated
                  at the query day's R
  - analogue    : mean (and median) of the K selected analogues' outcomes
                  (selection itself is causal by construction of the matcher)
"""
from __future__ import annotations

import numpy as np

from scripts.analog_path import config
from scripts.analog_path.stats import nw_t, ols_nw_multi


def expanding_baseline(outcomes: np.ndarray, horizon_col: int) -> np.ndarray:
    n = len(outcomes)
    f = np.full(n, np.nan)
    for i in range(1, n):
        f[i] = np.mean(outcomes[:i, horizon_col])
    return f


def expanding_return_only(outcomes: np.ndarray, horizon_col: int,
                          r: np.ndarray) -> np.ndarray:
    n = len(outcomes)
    f = np.full(n, np.nan)
    y = outcomes[:, horizon_col]
    for i in range(3, n):
        X = np.column_stack([np.ones(i), r[:i]])
        beta, *_ = np.linalg.lstsq(X, y[:i], rcond=None)
        f[i] = beta[0] + beta[1] * r[i]
    return f


def quality(forecast: np.ndarray, realized: np.ndarray) -> dict:
    m = np.isfinite(forecast) & np.isfinite(realized)
    f, y = forecast[m], realized[m]
    n = len(f)
    out = {"n": int(n), "mae": None, "rmse": None, "corr": None,
           "dir_acc": None, "bias": None}
    if n < 5:
        return out
    err = f - y
    out["mae"] = float(np.mean(np.abs(err)))
    out["rmse"] = float(np.sqrt(np.mean(err ** 2)))
    out["bias"] = float(np.mean(err))
    sd_f, sd_y = np.std(f), np.std(y)
    out["corr"] = float(np.corrcoef(f, y)[0, 1]) if sd_f > 0 and sd_y > 0 else None
    out["dir_acc"] = float(np.mean(np.sign(f) == np.sign(y)))
    out["nw_t_bias"] = float(nw_t(err))
    return out


def calibration(forecast: np.ndarray, realized: np.ndarray, n_buckets: int = 5) -> list:
    m = np.isfinite(forecast) & np.isfinite(realized)
    f, y = forecast[m], realized[m]
    n = len(f)
    if n < n_buckets * 5:
        return []
    qs = np.quantile(f, np.linspace(0, 1, n_buckets + 1))
    out = []
    for b in range(n_buckets):
        lo, hi = qs[b], qs[b + 1]
        mask = (f >= lo) & (f <= hi if b == n_buckets - 1 else f < hi)
        out.append({
            "bucket": b,
            "n": int(mask.sum()),
            "mean_forecast": float(np.mean(f[mask])),
            "mean_realized": float(np.mean(y[mask])),
        })
    return out


def return_controlled(realized: np.ndarray, analogue_f: np.ndarray,
                      r: np.ndarray) -> dict:
    """realized ~ [1, analogue_f, R] with NW SEs; plus the R-only model for
    incremental R2 (does the analogue forecast add explanatory power
    conditional on the current return?)."""
    full = ols_nw_multi(realized, np.column_stack([analogue_f, r]))
    reduced = ols_nw_multi(realized, r)
    out = {
        "n": full["n"],
        "beta_analogue": full["beta"][1] if full["beta"] else None,
        "se_analogue": full["se"][1] if full["se"] else None,
        "t_analogue": full["t"][1] if full["t"] else None,
        "p_analogue": full["p"][1] if full["p"] else None,
        "beta_R": full["beta"][2] if full["beta"] else None,
        "se_R": full["se"][2] if full["se"] else None,
        "t_R": full["t"][2] if full["t"] else None,
        "p_R": full["p"][2] if full["p"] else None,
        "r2_full": full["r2"],
        "r2_return_only": reduced["r2"],
        "delta_r2": (full["r2"] - reduced["r2"]) if full["r2"] is not None
                    and reduced["r2"] is not None else None,
    }
    return out
