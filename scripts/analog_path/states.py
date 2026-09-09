"""State matrices for the analogue engine.

Loads eligible sessions once and stacks them into numeric matrices:
  - states_A (n x 14): normalized price path
  - states_B (n x 13): interval returns
  - states_C (n x 14): linear-detrended shape (diagnostic)
  - r_1230 (n): open->12:30 return
  - outcomes (n x 5): frozen horizons, column order = config.HORIZONS
  - excursions (n x 2): mfe, mae

Sessions are loaded strictly from their own day files; the matrix is a pure
function of the eligible date list.
"""
from __future__ import annotations

from datetime import date

import numpy as np

from scripts.analog_path import config
from scripts.analog_path.data_layer import load_session


def build_matrices(dates: list[date]) -> dict:
    n = len(dates)
    A = np.empty((n, 14))
    B = np.empty((n, 13))
    C = np.empty((n, 14))
    R = np.empty(n)
    O = np.empty((n, len(config.HORIZONS)))
    X = np.empty((n, 2))
    kept = []
    skipped = []
    for i, d in enumerate(dates):
        s = load_session(d)
        if s is None or not s.valid:
            skipped.append(d.isoformat())
            continue
        if not np.all(np.isfinite(s.path_state)) or not np.all(np.isfinite(s.interval_state)):
            skipped.append(d.isoformat())
            continue
        j = len(kept)
        A[j] = s.path_state
        B[j] = s.interval_state
        C[j] = s.shape_state
        R[j] = s.open_to_1230
        for k, key in enumerate(config.HORIZONS):
            O[j, k] = s.outcomes[key]
        X[j] = (s.mfe, s.mae)
        kept.append(d)
    return {
        "dates": kept,
        "states_A": A[:len(kept)],
        "states_B": B[:len(kept)],
        "states_C": C[:len(kept)],
        "r_1230": R[:len(kept)],
        "outcomes": O[:len(kept)],
        "excursions": X[:len(kept)],
        "horizon_keys": tuple(config.HORIZONS),
        "skipped": skipped,
    }
