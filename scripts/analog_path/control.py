"""Same-return / different-path control (frozen tolerance +/-10 bp).

For each query day i: matched set M_i = {j < i : |R_j - R_i| <= 10bp}.
If |M_i| >= CONTROL_MIN_GROUP: split M_i at the median State-C distance into
near-shape and far-shape halves; d_i = mean(outcome | near) - mean(outcome | far)
per horizon. The aggregate test is mean(d_i) vs 0 (NW t, block-bootstrap CI,
within-group sign-permutation null). This is the direct test of "same
endpoint, different path -> different outcome".
"""
from __future__ import annotations

from datetime import date

import numpy as np

from scripts.analog_path import config
from scripts.analog_path.stats import block_bootstrap_ci, nw_t
from scripts.analog_path.nulls import _null_summary

TOL = config.TOLERANCE_PCT / 100.0


def run_control(states_C: np.ndarray, r_1230: np.ndarray,
                outcomes: np.ndarray, dates: list[date],
                horizon_keys: tuple[str, ...] | None = None) -> dict:
    if horizon_keys is None:
        horizon_keys = tuple(config.HORIZONS)
    assert outcomes.shape[1] == len(horizon_keys)
    n = len(r_1230)
    result = {
        "tolerance_bp": config.TOLERANCE_PCT,
        "min_group": config.CONTROL_MIN_GROUP,
        "state": "C (linear detrend)",
        "group_sizes": [],
        "n_groups": 0,
        "horizons": {},
    }
    group_sizes = []
    matched_sets = []
    ds = {k: [] for k in horizon_keys}
    for i in range(n):
        m_idx = np.flatnonzero(np.abs(r_1230[:i] - r_1230[i]) <= TOL)
        if len(m_idx) < config.CONTROL_MIN_GROUP:
            continue
        matched_sets.append((i, m_idx))
        dC = np.sqrt(np.sum((states_C[m_idx] - states_C[i]) ** 2, axis=1))
        order = np.argsort(dC, kind="stable")
        half = len(order) // 2
        near, far = order[:half], order[half:]
        for h, key in enumerate(horizon_keys):
            y = outcomes[:, h]
            ds[key].append(float(np.mean(y[m_idx[near]]) - np.mean(y[m_idx[far]])))
        group_sizes.append(len(m_idx))
    result["n_groups"] = len(group_sizes)
    result["group_sizes"] = group_sizes
    for key in horizon_keys:
        d = np.asarray(ds[key])
        lo, hi = block_bootstrap_ci(d) if len(d) >= 4 else (np.nan, np.nan)
        result["horizons"][key] = {
            "n": int(len(d)),
            "mean_diff": float(np.mean(d)) if len(d) else None,
            "sd_diff": float(np.std(d, ddof=1)) if len(d) > 1 else None,
            "nw_t": float(nw_t(d)),
            "ci95_lo": lo,
            "ci95_hi": hi,
            "null": within_group_permutation_null(outcomes, h, matched_sets)
            if len(d) >= 4 else None,
        }
    return result


def within_group_permutation_null(outcomes: np.ndarray, horizon_col: int,
                                  matched_sets: list,
                                  n_iters: int = config.NULL_ITERS) -> dict:
    """Permute the near/far assignment within each matched set (sets are
    precomputed by run_control and fixed; only the labels permute)."""
    rng = np.random.default_rng(config.NULL_SEED)
    y = outcomes[:, horizon_col]
    sizes = np.asarray([len(m) for _, m in matched_sets])
    halves = sizes // 2
    means = np.empty(n_iters)
    for it in range(n_iters):
        ds = []
        for (i, m_idx), half in zip(matched_sets, halves):
            perm = rng.permutation(len(m_idx))
            near, far = m_idx[perm[:half]], m_idx[perm[half:]]
            ds.append(float(np.mean(y[near]) - np.mean(y[far])))
        means[it] = float(np.mean(ds)) if ds else np.nan
    return _null_summary(means)
