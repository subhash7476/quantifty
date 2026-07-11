"""Pure numeric primitives for the A2 Validation Harness.

No I/O and no MSI imports — deterministic functions only. ROC-AUC is rank-based
(Mann-Whitney U form) with average-rank tie handling; the moving-block bootstrap
resamples contiguous day-blocks to respect the autocorrelated label (dossier §8,
Phase-2 finding M2).
"""

import hashlib
import json
from typing import Tuple

import numpy as np


def roc_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    n_pos = int(np.sum(labels == 1))
    n_neg = int(np.sum(labels == 0))
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    ranks = np.empty(len(scores), dtype=float)
    i = 0
    while i < len(sorted_scores):
        j = i
        while j + 1 < len(sorted_scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        ranks[order[i : j + 1]] = avg_rank
        i = j + 1
    sum_ranks_pos = float(np.sum(ranks[labels == 1]))
    auc = (sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def _delta_auc(cand: np.ndarray, ref: np.ndarray, labels: np.ndarray) -> float:
    return roc_auc(cand, labels) - roc_auc(ref, labels)


def moving_block_bootstrap_delta_auc_ci(
    cand: np.ndarray,
    ref: np.ndarray,
    labels: np.ndarray,
    block_length: int,
    n_replicates: int,
    seed: int,
    alpha: float = 0.05,
) -> Tuple[float, float]:
    cand = np.asarray(cand, dtype=float)
    ref = np.asarray(ref, dtype=float)
    labels = np.asarray(labels, dtype=int)
    n = len(labels)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_length))
    max_start = n - block_length
    deltas = np.empty(n_replicates, dtype=float)
    filled = 0
    for _ in range(n_replicates):
        starts = rng.integers(0, max_start + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_length) for s in starts])[:n]
        d = _delta_auc(cand[idx], ref[idx], labels[idx])
        if not np.isnan(d):
            deltas[filled] = d
            filled += 1
    deltas = deltas[:filled]
    lower = float(np.percentile(deltas, 100 * (alpha / 2)))
    upper = float(np.percentile(deltas, 100 * (1 - alpha / 2)))
    return (lower, upper)


def format_6dp(x: float) -> float:
    return float(f"{float(x):.6f}")


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(", ", ": "))


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
