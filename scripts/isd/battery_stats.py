"""ISD battery — frozen statistics: rank IC, NW/AC1, matched nulls, cost gate.

Implements ISD_PHASE0_PRE_REGISTRATION §6-§8:
  - per-cell rank IC (Spearman), NW t, AC1, empirical one-sided p from the
    random-entry null (1,000 iterations);
  - family-level IC = equal-weighted mean of qualifying cells' per-session ICs;
    empirical p from the circular-shift null (month-block rotations);
  - BH per-cell alpha = 0.05/4 = 0.0125; >=2 of 4 qualifying cells;
  - net-spread gate: gross - 2 x slippage (G6 p90 by decile) - round-trip fees
    (era-accurate module), at measured tau (EOD-flat => structural tau = 2).
"""
from __future__ import annotations

import math
import warnings

import numpy as np
from scipy.stats import spearmanr, t as student_t

from scripts.isd.battery_features import MIN_NAMES

NW_LAG = None                 # computed per series: floor(4*(n/100)^(2/9))


def nw_lag(n: int) -> int:
    return max(1, int(4 * (n / 100.0) ** (2 / 9.0)))


def _ac1(x):
    x = np.asarray(x, float)
    if len(x) < 3:
        return 0.0
    xm = x - x.mean()
    denom = float(xm @ xm)
    return float(xm[:-1] @ xm[1:] / denom) if denom > 0 else 0.0


def _nw_se(x, lag):
    x = np.asarray(x, float)
    n = len(x)
    xm = x - x.mean()
    g0 = float(xm @ xm) / n
    lrv = g0
    for k in range(1, lag + 1):
        gk = float(xm[:-k] @ xm[k:]) / n
        lrv += 2 * (1 - k / (lag + 1)) * gk
    lrv = max(lrv, 1e-18)
    return math.sqrt(lrv / n)


def series_stats(ic: np.ndarray) -> dict:
    ic = np.asarray(ic, float)
    ic = ic[~np.isnan(ic)]
    n = len(ic)
    if n == 0:
        return {"n": 0, "mean_ic": float("nan"), "sd_ic": float("nan"),
                "t_plain": 0.0, "t_nw": 0.0, "p_nw_one_sided": 1.0,
                "ac1": 0.0, "lag": 0}
    mean = float(ic.mean())
    sd = float(ic.std(ddof=1)) if n > 1 else 0.0
    lag = nw_lag(n)
    se0 = sd / math.sqrt(n) if n > 1 else 0.0
    se_nw = _nw_se(ic, lag)
    t_plain = mean / se0 if se0 > 0 else 0.0
    t_nw = mean / se_nw if se_nw > 0 else 0.0
    p_nw = float(student_t.sf(t_nw, df=n - 1)) if n > 1 else 1.0
    return {"n": n, "mean_ic": mean, "sd_ic": sd, "t_plain": t_plain,
            "t_nw": t_nw, "p_nw_one_sided": p_nw, "ac1": _ac1(ic), "lag": lag}


def _row_ranks(mask_feat, feat_perm):
    """Per-row ranks of feat_perm (1 = worst) as float array, NaN where masked."""
    n_s, n_c = feat_perm.shape
    ranks = np.empty_like(feat_perm, dtype=float)
    for i in range(n_s):
        row = feat_perm[i]
        order = np.argsort(row, kind="mergesort")
        r = np.empty(n_c, dtype=float)
        r[order] = np.arange(1, n_c + 1)
        r[~mask_feat[i]] = np.nan
        ranks[i] = r
    return ranks


def per_session_ic(feat: np.ndarray, label: np.ndarray) -> np.ndarray:
    """Spearman IC per session; NaN where < MIN_NAMES valid pairs."""
    n_s, n_c = feat.shape
    valid = ~np.isnan(feat) & ~np.isnan(label)
    out = np.full(n_s, np.nan)
    for i in range(n_s):
        m = valid[i]
        if m.sum() < MIN_NAMES:
            continue
        rho, _ = spearmanr(feat[i][m], label[i][m])
        out[i] = rho
    return out


def random_entry_null(feat: np.ndarray, label: np.ndarray, rng,
                      iters: int = 1000) -> np.ndarray:
    """Null distribution of mean IC: features permuted within each session.

    Spearman-equivalent: per-row ranks of the permuted feature matrix,
    standardized, dotted with standardized labels (masked, NaN-safe).
    """
    n_s, n_c = feat.shape
    valid_l = ~np.isnan(label)
    nulls = np.empty(iters)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        label_std = np.where(valid_l, (label - np.nanmean(label, axis=1,
                                                          keepdims=True))
                             / np.nanstd(label, axis=1, keepdims=True), np.nan)
        for it in range(iters):
            perm = np.argsort(rng.standard_normal((n_s, n_c)), axis=1)
            feat_perm = np.take_along_axis(feat, perm, axis=1)
            ranks = np.argsort(np.argsort(feat_perm, axis=1, kind="mergesort"),
                               axis=1, kind="mergesort").astype(float)
            ranks[np.isnan(feat_perm)] = np.nan
            m = ~np.isnan(ranks) & valid_l
            counts = m.sum(axis=1)
            r_std = np.where(m, (ranks - np.nanmean(np.where(m, ranks, np.nan),
                                                    axis=1, keepdims=True))
                             / np.nanstd(np.where(m, ranks, np.nan), axis=1,
                                         keepdims=True), np.nan)
            ic_row = np.nansum(r_std * label_std, axis=1) / counts.clip(min=1)
            ok = counts >= MIN_NAMES
            nulls[it] = float(np.nanmean(ic_row[ok])) if ok.any() else np.nan
    return nulls


def circular_shift_null(feat: np.ndarray, label: np.ndarray,
                        month_starts: list, rng, iters: int = 1000):
    """Null: rotate month-blocks of the feature matrix; return mean-IC sample."""
    bounds = [b for b in month_starts if b < feat.shape[0]] + [feat.shape[0]]
    blocks = list(zip(bounds[:-1], bounds[1:]))
    n_blocks = len(blocks)
    nulls = np.empty(iters)
    for it in range(iters):
        k = rng.integers(1, n_blocks)
        shifted = np.full_like(feat, np.nan)
        for j, (a, b) in enumerate(blocks):
            src = blocks[(j - k) % n_blocks]
            shifted[a:b] = feat[src[0]:src[1]]
        ic = per_session_ic(shifted, label)
        nulls[it] = float(np.nanmean(ic))
    return nulls


def empirical_p(observed: float, nulls: np.ndarray, direction: int) -> float:
    """One-sided empirical p in `direction` (+1: p(null >= observed), -1: p(null <= observed))."""
    if direction > 0:
        return float((nulls >= observed).mean())
    return float((nulls <= observed).mean())


def net_spread_series(gross_bp: np.ndarray, slip_bp: np.ndarray,
                      fee_bp: np.ndarray) -> np.ndarray:
    """Per-session net spread in bp: gross - 2 x slippage - fees."""
    g = np.asarray(gross_bp, float)
    return g - 2.0 * np.asarray(slip_bp, float) - np.asarray(fee_bp, float)
