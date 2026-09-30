"""BKV-1 statistics (pure functions, no market data).

The calendar-aware Newey-West test is written out step by step so that every intermediate quantity
(mean, g0, g_k, weights, long-run variance, SE, t) can be reproduced by hand; verify_independent.py
recomputes it by a separate pure-Python path and with statsmodels' S_hac_simple.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats as sst

from scripts.vwap_rev.stats import block_bootstrap_mean, describe, holm, twoway_cluster_mean  # noqa: F401  (reused, hashed)


def nw_gap_test(values, positions, lag: int) -> dict:
    """Mean of a series observed on integer session positions, Bartlett/Newey-West HAC SE with a fixed lag.

    x_i observed at session position pos_i. z_i = x_i - mean. g0 = sum z^2 / n.
    g_k = (sum over observation pairs exactly k sessions apart of z_i z_j) / n   (gaps contribute nothing).
    LRV = g0 + 2 * sum_{k=1..lag} (1 - k/(lag+1)) g_k ;  SE = sqrt(LRV / n) ;  t = mean / SE.
    One-sided p (H1: mean > 0) from Student-t with n-1 df.
    """
    x = np.asarray(values, float)
    pos = np.asarray(positions, np.int64)
    m = np.isfinite(x)
    x, pos = x[m], pos[m]
    n = len(x)
    if n < 3:
        return {"n": n, "mean": float(x.mean()) if n else np.nan, "se": np.nan, "t": np.nan,
                "p_one": np.nan, "p_two": np.nan, "lag": lag, "g0": np.nan, "lrv": np.nan}
    order = np.argsort(pos)
    x, pos = x[order], pos[order]
    mean = float(x.mean())
    z = x - mean
    dense = np.zeros(int(pos[-1] - pos[0]) + 1)
    dense[pos - pos[0]] = z
    g0 = float(z @ z) / n
    lrv = g0
    gks = []
    for k in range(1, lag + 1):
        gk = float(dense[:-k] @ dense[k:]) / n if k < len(dense) else 0.0
        gks.append(gk)
        lrv += 2.0 * (1.0 - k / (lag + 1.0)) * gk
    lrv = max(lrv, 1e-18)
    se = math.sqrt(lrv / n)
    t = mean / se
    return {"n": n, "mean": mean, "se": se, "t": t, "p_one": float(sst.t.sf(t, n - 1)),
            "p_two": float(2 * sst.t.sf(abs(t), n - 1)), "lag": lag, "g0": g0, "lrv": lrv, "gk": gks}


def event_contrast_cluster(y, is_b, g1, g2) -> dict:
    """OLS y = a + b*1[B] with two-way (g1, g2) cluster-robust variance (Cameron-Gelbach-Miller, intersection
    term subtracted); b equals mean_B - mean_C exactly. One-sided p for b > 0 with min(#g1,#g2)-1 df."""
    y = np.asarray(y, float)
    b = np.asarray(is_b, float)
    m = np.isfinite(y)
    y, b, g1, g2 = y[m], b[m], np.asarray(g1)[m], np.asarray(g2)[m]
    n = len(y)
    if n < 20 or b.sum() < 5 or (1 - b).sum() < 5:
        return {"n": n, "b": np.nan, "se": np.nan, "t": np.nan, "p_one": np.nan}
    X = np.column_stack([np.ones(n), b])
    XtXi = np.linalg.inv(X.T @ X)
    beta = XtXi @ (X.T @ y)
    e = y - X @ beta
    s = X * e[:, None]

    def meat(groups):
        df = pd.DataFrame(s).groupby(np.asarray(groups)).sum().to_numpy()
        return df.T @ df

    inter = pd.Series(list(zip(g1, g2))).astype(str).to_numpy()
    V = XtXi @ (meat(g1) + meat(g2) - meat(inter)) @ XtXi
    v = V[1, 1]
    if v <= 0:
        v = max((XtXi @ meat(g1) @ XtXi)[1, 1], (XtXi @ meat(g2) @ XtXi)[1, 1])
    se = math.sqrt(v)
    t = beta[1] / se
    df = max(min(pd.Series(g1).nunique(), pd.Series(g2).nunique()) - 1, 1)
    return {"n": n, "b": float(beta[1]), "se": se, "t": float(t), "p_one": float(sst.t.sf(t, df))}


def paired_permutation(f, is_b, date_id, n_perm: int, seed: int) -> dict:
    """Within-date permutation of the B/C label among the breakout events of the SAME date (event count per
    date and per arm fixed). Statistic = mean over dates with both arms of (mean_B - mean_C). Returns the
    observed statistic and the one-sided permutation p = (1 + #{perm >= obs}) / (1 + n_perm)."""
    f = np.asarray(f, float)
    b = np.asarray(is_b, bool)
    did = np.asarray(date_id)
    order = np.argsort(did, kind="stable")
    f, b, did = f[order], b[order], did[order]
    uniq, start, cnt = np.unique(did, return_index=True, return_counts=True)
    nb = np.add.reduceat(b.astype(int), start)
    keep = (nb >= 1) & (nb < cnt)
    if keep.sum() < 3:
        return {"obs": np.nan, "p_one": np.nan, "n_dates": int(keep.sum()), "null_sd": np.nan}
    lab = np.zeros(len(f), bool)
    for s, c, k in zip(start, cnt, nb):
        lab[s:s + k] = True                                   # canonical: first nb slots of each date are B
    def stat(labels):
        sb = np.add.reduceat(np.where(labels, f, 0.0), start)
        sc = np.add.reduceat(np.where(labels, 0.0, f), start)
        with np.errstate(invalid="ignore", divide="ignore"):
            d = sb / nb - sc / (cnt - nb)
        return float(np.mean(d[keep]))
    obs_d = np.add.reduceat(np.where(b, f, 0.0), start) / nb - np.add.reduceat(np.where(b, 0.0, f), start) / (cnt - nb)
    obs = float(np.mean(obs_d[keep]))
    rng = np.random.default_rng(seed)
    did_codes = np.repeat(np.arange(len(uniq)), cnt)
    null = np.empty(n_perm)
    for i in range(n_perm):
        o = np.lexsort((rng.random(len(f)), did_codes))       # shuffle within date
        null[i] = stat(lab[np.argsort(o, kind="stable")])
    return {"obs": obs, "p_one": float((1 + (null >= obs).sum()) / (1 + n_perm)), "n_dates": int(keep.sum()),
            "null_sd": float(null.std(ddof=1))}


def mde_one_sided(se: float, alpha: float = 0.05, power: float = 0.80) -> float:
    """Minimum detectable mean given the (HAC) standard error of the estimate."""
    return (sst.norm.ppf(1 - alpha) + sst.norm.ppf(power)) * se if np.isfinite(se) else float("nan")
