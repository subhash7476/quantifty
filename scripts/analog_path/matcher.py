"""Walk-forward analogue matcher with explicit causal ordering.

For query day D (position i in the chronological date list):
  1. construct D's state (precomputed — uses only D's own 09:15->12:30 bars);
  2. pool = eligible days strictly before D (positions j < i);
  3. compute Euclidean distances to every pool day's state;
  4. rank pool days by ascending distance;
  5. select the K nearest (requires pool_size >= K, else flagged);
  6. ONLY THEN read the selected analogues' forward outcomes.

The outcome matrix is passed separately and is touched only after selection,
so the causal ordering is structural: `select_analogues` receives states
only and returns indices; outcomes are gathered afterwards by the caller.

Similarity quality (protocol section on similarity diagnostics):
  - `pool_rank_nearest` — the nearest analogue's rank within this query's
    pool-distance distribution. By construction it is ~1 - 1/pool (the
    nearest IS the pool minimum), so it is reported but carries no
    information beyond "it is the minimum".
  - `reference_percentile` — the PRIMARY similarity measure: the nearest
    distance's percentile within the distribution of pairwise distances
    among a deterministic random sample of pool days (S = min(80, pool)).
    Walk-forward (sampled from the pool only), deterministic per query
    (seed = NULL_SEED + i). LOW percentile => the nearest analogue sits in
    the extreme lower tail of typical between-days distances (a genuinely
    similar state); HIGH percentile => weakly matched (most pairs of
    historical days are closer to each other than the nearest analogue is
    to the query).
"""
from __future__ import annotations

import numpy as np

from scripts.analog_path import config


def select_analogues(states: np.ndarray, i: int, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Nearest-K pool indices (into the full matrix) for query position i.

    Returns (pool_indices sorted by ascending distance, distances).
    The future of the pool days plays no role here: distances are computed
    from the morning-state matrix alone. Raises ValueError if pool < k.
    """
    if k > i:
        raise ValueError(f"pool size {i} < K={k} for query position {i}")
    dists = np.sqrt(np.sum((states[:i] - states[i]) ** 2, axis=1))
    order = np.argsort(dists, kind="stable")
    return order[:k], dists[order[:k]]


def match_day(states: np.ndarray, i: int, k: int,
              ref_sample_size: int = 80) -> dict | None:
    """Analogue selection for query position i at K. None if pool < K."""
    if i < k:
        return None
    idx, dists = select_analogues(states, i, k)
    pool_dists = np.sqrt(np.sum((states[:i] - states[i]) ** 2, axis=1))
    median_pool = float(np.median(pool_dists))
    pool_rank_nearest = float(np.mean(pool_dists > dists[0]))
    # reference pair-distance distribution among a deterministic pool sample
    s = min(ref_sample_size, i)
    rng = np.random.default_rng(config.NULL_SEED + i)
    sample = rng.choice(i, size=s, replace=False)
    subs = states[sample]
    d2 = (subs[:, None, :] - subs[None, :, :]) ** 2
    pair_dists = np.sqrt(d2.sum(axis=2))[np.triu_indices(s, k=1)]
    reference_percentile = float(np.mean(pair_dists < dists[0]))
    return {
        "analogue_idx": idx,          # ascending distance, len k
        "distances": dists,           # ascending, len k
        "nearest_dist": float(dists[0]),
        "kth_dist": float(dists[-1]),
        "median_pool_dist": median_pool,
        "pool_rank_nearest": pool_rank_nearest,
        "reference_percentile": reference_percentile,
        "pool_size": i,
    }


def analogue_forecasts(outcomes: np.ndarray, idx: np.ndarray) -> dict[str, float]:
    """Mean and median of the SELECTED analogues' forward outcomes.

    Called only after selection; the outcome matrix is indexed by the
    selected analogue indices, never by the query day itself.
    """
    sel = outcomes[idx]
    return {
        "mean": float(np.mean(sel)),
        "median": float(np.median(sel)),
    }
