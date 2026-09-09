"""Null machinery for the analogue engine (A-track conventions: 1,000
iterations, seed 42; empirical p-values reported, never parametric-only).

  1. randomized-matching null — for query day i, its K selected analogues
     are replaced by K random pool days (uniform over [0, i), sampled
     causally). This destroys the state-outcome pairing while keeping the
     pool structure; answers "does the actual matching beat random
     historical matching?" Statistic: correlation(realized, forecast).
     The null distribution depends on (K, horizon) only, not on the state
     representation, so it is computed once per (K, horizon) and compared
     against each representation's observed correlation.
  2. block-shift null — the realized outcome series is shifted by a random
     number of calendar-month blocks against the fixed forecasts; preserves
     the realized series' autocorrelation structure (A-track convention).
  3. sign-permutation null — realized outcomes are sign-flipped with p=0.5;
     used for the directional-accuracy statistic.
"""
from __future__ import annotations

from datetime import date

import numpy as np

from scripts.analog_path import config


def randomized_matching_null(outcomes: np.ndarray, horizon_col: int, k: int,
                             realized: np.ndarray,
                             n_iters: int = config.NULL_ITERS) -> dict:
    rng = np.random.default_rng(config.NULL_SEED)
    n = len(outcomes)
    i = np.arange(n)
    positions = i[:, None]
    null_corrs = np.empty(n_iters)
    for it in range(n_iters):
        u = rng.random((n, k))
        idx = (u * positions).astype(int)
        forecasts = np.mean(outcomes[idx, horizon_col], axis=1)
        m = np.isfinite(forecasts) & np.isfinite(realized)
        if m.sum() < 10:
            null_corrs[it] = np.nan
        else:
            null_corrs[it] = np.corrcoef(forecasts[m], realized[m])[0, 1]
    return _null_summary(null_corrs)


def block_shift_null(realized: np.ndarray, forecast: np.ndarray,
                     dates: list[date], n_iters: int = config.NULL_ITERS) -> dict:
    rng = np.random.default_rng(config.NULL_SEED)
    y = np.asarray(realized, dtype=float)
    f = np.asarray(forecast, dtype=float)
    # month boundaries in the (chronological) date list
    months = [d.year * 12 + d.month for d in dates]
    bounds = [0] + [i for i in range(1, len(months)) if months[i] != months[i - 1]] + [len(months)]
    n_blocks = len(bounds) - 1
    null_corrs = np.empty(n_iters)
    for it in range(n_iters):
        shift = rng.integers(0, n_blocks)
        if shift == 0:
            y_shift = y.copy()
        else:
            y_shift = np.concatenate([y[bounds[shift]:], y[:bounds[shift]]])
        m = np.isfinite(f) & np.isfinite(y_shift)
        null_corrs[it] = np.corrcoef(f[m], y_shift[m])[0, 1] if m.sum() >= 10 else np.nan
    return _null_summary(null_corrs)


def sign_permutation_null(realized: np.ndarray, forecast: np.ndarray,
                          n_iters: int = config.NULL_ITERS) -> dict:
    """Null for directional accuracy: sign-flip realized with p=0.5."""
    rng = np.random.default_rng(config.NULL_SEED)
    y = np.asarray(realized, dtype=float)
    f = np.asarray(forecast, dtype=float)
    m = np.isfinite(f) & np.isfinite(y)
    yv, fv = y[m], f[m]
    null_da = np.empty(n_iters)
    for it in range(n_iters):
        flips = rng.choice([-1.0, 1.0], size=len(yv))
        null_da[it] = np.mean(np.sign(fv) == np.sign(yv * flips))
    return _null_summary(null_da)


def _null_summary(sample: np.ndarray) -> dict:
    sample = sample[np.isfinite(sample)]
    if len(sample) == 0:
        return {"n": 0, "null_mean": None, "null_sd": None,
                "null_p5": None, "null_p95": None, "sample": []}
    return {
        "n": int(len(sample)),
        "null_mean": float(np.mean(sample)),
        "null_sd": float(np.std(sample, ddof=1)) if len(sample) > 1 else 0.0,
        "null_p5": float(np.quantile(sample, 0.05)),
        "null_p95": float(np.quantile(sample, 0.95)),
        "sample": [float(v) for v in sample],
    }


def empirical_p_two_sided(observed: float, null: np.ndarray) -> float:
    """Fraction of null draws at least as extreme (two-sided on |x - mean|)."""
    null = null[np.isfinite(null)]
    if len(null) == 0:
        return float("nan")
    center = np.mean(null)
    obs_dev = abs(observed - center)
    null_dev = np.abs(null - center)
    p = (np.sum(null_dev >= obs_dev) + 1) / (len(null) + 1)
    return float(p)
