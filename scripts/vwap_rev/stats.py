"""VWAP-XREV dependence-aware statistics (pure functions, no market data)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats as sst

QUANTILES = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
N_BOOT = 10_000
BOOT_SEED = 20260930


def nw_lag(n: int) -> int:
    return max(1, int(4 * (n / 100.0) ** (2 / 9.0)))


def nw_mean_test(x) -> dict:
    """Mean of a (session-indexed) series with a Bartlett/Newey-West HAC SE.
    One-sided p for H1: mean > 0 (Student-t, n-1 df); two-sided also returned."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return {"n": n, "mean": float(x.mean()) if n else np.nan, "se": np.nan, "t": np.nan,
                "p_one": np.nan, "p_two": np.nan, "lag": 0, "ac1": np.nan}
    lag = nw_lag(n)
    xm = x - x.mean()
    g0 = float(xm @ xm) / n
    lrv = g0
    for k in range(1, lag + 1):
        gk = float(xm[:-k] @ xm[k:]) / n
        lrv += 2 * (1 - k / (lag + 1)) * gk
    lrv = max(lrv, 1e-18)
    se = math.sqrt(lrv / n)
    t = float(x.mean()) / se
    ac1 = float(xm[:-1] @ xm[1:] / (xm @ xm)) if (xm @ xm) > 0 else 0.0
    return {"n": n, "mean": float(x.mean()), "se": se, "t": t,
            "p_one": float(sst.t.sf(t, n - 1)), "p_two": float(2 * sst.t.sf(abs(t), n - 1)),
            "lag": lag, "ac1": ac1}


def block_bootstrap_mean(x, block: int | None = None, n_boot: int = N_BOOT,
                         seed: int = BOOT_SEED, lb_alpha: float | None = None) -> dict:
    """Circular moving-block bootstrap of the mean over the session series.
    CI = percentile CI; p_one = share of RE-CENTRED bootstrap means >= observed mean."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 5:
        return {"ci_lo": np.nan, "ci_hi": np.nan, "p_one": np.nan, "block": 0, "lb": np.nan}
    b = block or max(2, nw_lag(n) + 1)
    rng = np.random.default_rng(seed)
    nblk = int(math.ceil(n / b))
    starts = rng.integers(0, n, (n_boot, nblk))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]) % n
    means = x[idx.reshape(n_boot, -1)[:, :n]].mean(axis=1)
    obs = x.mean()
    return {"ci_lo": float(np.percentile(means, 2.5)), "ci_hi": float(np.percentile(means, 97.5)),
            "p_one": float(((means - obs) >= obs).mean()), "block": b,
            "lb": float(np.percentile(means, 100 * lb_alpha)) if lb_alpha is not None else np.nan}


def twoway_cluster_mean(y, g1, g2) -> dict:
    """Mean of y with two-way clustered SE (Cameron-Gelbach-Miller; g1 x g2 intersection
    for the overlap term). Constant-only regression."""
    y = np.asarray(y, float)
    m = np.isfinite(y)
    y, g1, g2 = y[m], np.asarray(g1)[m], np.asarray(g2)[m]
    n = len(y)
    if n < 10:
        return {"n": n, "mean": np.nan, "se": np.nan, "t": np.nan, "p_one": np.nan}
    e = y - y.mean()

    def meat(g):
        s = pd.Series(e).groupby(g).sum().to_numpy()
        return float((s ** 2).sum())

    inter = pd.Series(list(zip(g1, g2)))
    v = (meat(g1) + meat(g2) - meat(inter.astype(str).to_numpy())) / n ** 2
    if v <= 0:
        v = max(meat(g1), meat(g2)) / n ** 2
    se = math.sqrt(v)
    t = y.mean() / se
    ng = min(pd.Series(g1).nunique(), pd.Series(g2).nunique())
    return {"n": n, "mean": float(y.mean()), "se": se, "t": float(t),
            "p_one": float(sst.t.sf(t, max(ng - 1, 1)))}


def holm(pvals: dict) -> dict:
    """Holm-Bonferroni adjusted p-values for a dict {key: p}. NaN stays NaN."""
    items = [(k, p) for k, p in pvals.items() if p is not None and np.isfinite(p)]
    items.sort(key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    for k, p in pvals.items():
        out.setdefault(k, np.nan)
    return out


def describe(y) -> dict:
    y = np.asarray(y, float)
    y = y[np.isfinite(y)]
    if len(y) == 0:
        return {"n": 0}
    d = {"n": int(len(y)), "mean": float(y.mean()), "median": float(np.median(y)),
         "sd": float(y.std(ddof=1)) if len(y) > 1 else np.nan,
         "skew": float(sst.skew(y)) if len(y) > 2 else np.nan,
         "kurt": float(sst.kurtosis(y)) if len(y) > 3 else np.nan,
         "frac_pos": float((y > 0).mean())}
    for q, v in zip(QUANTILES, np.quantile(y, QUANTILES)):
        d[f"q{int(q * 100):02d}"] = float(v)
    return d


def mde_session(sd_session: float, n_sessions: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """Minimum detectable mean (one-sided) for the session-level test."""
    if n_sessions < 2 or not np.isfinite(sd_session):
        return float("nan")
    return (sst.norm.ppf(1 - alpha) + sst.norm.ppf(power)) * sd_session / math.sqrt(n_sessions)
