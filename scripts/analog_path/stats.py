"""Minimal statistical machinery for the analog-path research.

Reproduces the repository's established conventions (A-track / ISD):
Newey-West t with lag 5, AC1, and a moving-block bootstrap for CIs of the
mean (blocks of 5 sessions) — self-contained so this track carries no import
dependency on another track's frozen module.
"""
from __future__ import annotations

import numpy as np
from scipy import stats as sps

from scripts.analog_path import config


def nw_t(x: np.ndarray, lag: int = config.NW_LAG) -> float:
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 3 or not np.all(np.isfinite(x)):
        return 0.0
    m = float(np.mean(x))
    e = x - m
    nw_var = float(np.mean(e * e))
    for k in range(1, min(lag, n - 1) + 1):
        ck = float(np.mean(e[k:] * e[:-k]))
        nw_var += 2.0 * (1.0 - k / (lag + 1.0)) * ck
    if nw_var <= 0:
        return 0.0
    return m / np.sqrt(nw_var / n)


def ac1(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 4 or not np.all(np.isfinite(x)):
        return 0.0
    m = float(np.mean(x))
    num = float(np.sum((x[1:] - m) * (x[:-1] - m)))
    den = float(np.sum((x - m) ** 2))
    return num / den if den > 0 else 0.0


def block_bootstrap_ci(x: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    """Moving-block bootstrap 95% CI for the mean (blocks of BOOT_BLOCKS)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 4 or not np.all(np.isfinite(x)):
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(config.BOOT_SEED)
    b = config.BOOT_BLOCKS
    means = np.empty(config.BOOT_ITERS)
    for i in range(config.BOOT_ITERS):
        starts = rng.integers(0, max(n - b, 1), size=(n + b - 1) // b + 1)
        sample = np.concatenate([x[s:s + b] for s in starts])
        means[i] = sample.mean()
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def summary(x: np.ndarray) -> dict:
    """Frozen summary block: n, mean, median, sd, hit rate, skew, quantiles,
    NW t, block-bootstrap CI."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    out = {
        "n": n,
        "mean": None, "median": None, "sd": None, "hit_rate": None,
        "skew": None, "quantiles": None, "nw_t": None, "ci95_lo": None,
        "ci95_hi": None, "ac1": None,
    }
    if n == 0:
        return out
    out.update({
        "n": int(n),
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "sd": float(np.std(x, ddof=1)) if n > 1 else 0.0,
        "hit_rate": float(np.mean(x > 0)),
        "skew": float(sps.skew(x)) if n > 2 else None,
        "quantiles": {f"q{q:.2f}": float(np.quantile(x, q)) for q in config.QUANTILES},
        "nw_t": float(nw_t(x)),
        "ac1": float(ac1(x)),
    })
    lo, hi = block_bootstrap_ci(x)
    out["ci95_lo"], out["ci95_hi"] = lo, hi
    return out


def ols_nw_multi(y: np.ndarray, X: np.ndarray) -> dict:
    """OLS of y on X (with intercept) with Newey-West standard errors.

    Returns per-regressor beta, NW se, t, p plus overall R2.
    """
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    m = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    y, X = y[m], X[m]
    n = len(y)
    out = {"n": int(n), "beta": None, "se": None, "t": None, "p": None, "r2": None}
    if n < X.shape[1] + 5:
        return out
    if np.any(np.std(X, axis=0) == 0):
        return out  # degenerate regressor column (e.g. constant forecast)
    Xd = np.column_stack([np.ones(n), X])
    beta, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    resid = y - Xd @ beta
    e = Xd * resid[:, None]
    lag = config.NW_LAG
    nw = e.T @ e / n
    for k in range(1, min(lag, n - 1) + 1):
        w = 1.0 - k / (lag + 1.0)
        g = (e[k:].T @ e[:-k]) / n
        nw += w * (g + g.T)
    xx = Xd.T @ Xd / n
    cov = np.linalg.inv(xx) @ nw @ np.linalg.inv(xx) / n
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    t = np.where(se > 0, beta / se, 0.0)
    out["beta"] = [float(b) for b in beta]
    out["se"] = [float(s) for s in se]
    out["t"] = [float(v) for v in t]
    out["p"] = [float(2 * sps.norm.sf(abs(v))) for v in t]
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    out["r2"] = 1.0 - float(np.sum(resid ** 2)) / ss_tot if ss_tot > 0 else None
    return out


def ols_nw(y: np.ndarray, x: np.ndarray) -> dict:
    """OLS of y on x (with intercept) using Newey-West standard errors."""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = len(x)
    out = {"n": int(n), "slope": None, "nw_t": None, "p": None, "r2": None}
    if n < 10:
        return out
    X = np.column_stack([np.ones(n), x])
    beta, res, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    e = X * resid[:, None]
    lag = config.NW_LAG
    nw = e.T @ e / n
    for k in range(1, min(lag, n - 1) + 1):
        w = 1.0 - k / (lag + 1.0)
        g = (e[k:].T @ e[:-k]) / n
        nw += w * (g + g.T)
    xx = X.T @ X / n
    cov = np.linalg.inv(xx) @ nw @ np.linalg.inv(xx) / n
    se = np.sqrt(np.diag(cov))
    t = float(beta[1] / se[1]) if se[1] > 0 else 0.0
    out["slope"] = float(beta[1])
    out["nw_t"] = t
    out["p"] = float(2 * sps.norm.sf(abs(t)))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    out["r2"] = 1.0 - float(np.sum(resid ** 2)) / ss_tot if ss_tot > 0 else None
    return out
