"""Minimal statistics for the RELIANCE regime research.

Same conventions as the platform's research tracks: Newey-West t (lag 5)
and moving-block bootstrap CIs (blocks of 5 sessions, 10,000 iterations,
seed 42).
"""
from __future__ import annotations

import numpy as np

NW_LAG = 5
BOOT_BLOCKS = 5
BOOT_ITERS = 10_000
BOOT_SEED = 42


def nw_t(x: np.ndarray, lag: int = NW_LAG) -> float:
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


def block_bootstrap_ci(x: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 4 or not np.all(np.isfinite(x)):
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(BOOT_SEED)
    b = BOOT_BLOCKS
    means = np.empty(BOOT_ITERS)
    for i in range(BOOT_ITERS):
        starts = rng.integers(0, max(n - b, 1), size=(n + b - 1) // b + 1)
        sample = np.concatenate([x[s:s + b] for s in starts])
        means[i] = sample.mean()
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)
