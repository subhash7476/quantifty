"""M4a-CE cohorts: who is in which arm on which date. State and validity only - NO forward value is computed here.

Cohorts (all require: PIT member at t, and the compression state evaluable at t):
  comp  C : low(t) and, on each of the prior `quiet` sessions, state evaluable and not low        (onset)
  norm  N : not low(t)                                                                             (normal-state benchmark: the complement)
  pers  P : high(t) and, on each of the prior `quiet` sessions, state evaluable and not high        (persistence comparator)
An unevaluable prior session is UNKNOWN, never "no compression".
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.m4a_compress import common as C
from scripts.m4a_compress import state as S
from scripts.m4a_compress.common import P, Params

ST_NORMAL, ST_DROPPED, ST_BEYOND = 0, 2, 3


def _prior_all(flag: np.ndarray, w: int) -> np.ndarray:
    """True where `flag` held on every one of the w sessions strictly before t (t-w .. t-1)."""
    s = pd.DataFrame(flag.astype(float).T).rolling(w, min_periods=w).sum().shift(1).to_numpy().T
    return s == w


def cohort_masks(low: np.ndarray, high: np.ndarray, state_valid: np.ndarray, member: np.ndarray, quiet: int) -> dict:
    elig = member & state_valid
    clean_low = _prior_all(state_valid & ~low, quiet)
    clean_high = _prior_all(state_valid & ~high, quiet)
    return {"comp": elig & low & clean_low, "norm": elig & ~low, "pers": elig & high & clean_high, "elig": elig}


def cohort_flags(pn, variant: str, p: Params = P) -> dict:
    ratio = S.compression_ratio(pn.H, pn.L, pn.C, variant, p)
    pct = S.trailing_pct_rank(ratio, p.pct_window)
    low, high = S.tail_flags(pct, p.q_low, p.q_high)
    state_valid = np.isfinite(pct)
    out = {"ratio": ratio, "pct": pct, "state_valid": state_valid, "low": low, "high": high}
    out.update(cohort_masks(low, high, state_valid, pn.member, p.quiet))
    return out


def forward_status(valid: np.ndarray, h: int) -> np.ndarray:
    """0 normal: sessions t..t+h all have a valid row; 3 beyond: t+h is past the panel; 2 dropped: anything else.
    Depends on row availability only - no price is read."""
    E, T = valid.shape
    roll = pd.DataFrame(valid.astype(float).T).rolling(h + 1, min_periods=h + 1).sum().to_numpy().T
    st = np.full((E, T), ST_DROPPED, np.int8)
    ok = np.zeros((E, T), bool)
    ok[:, : T - h] = roll[:, h:] == h + 1
    st[ok] = ST_NORMAL
    st[:, max(T - h, 0):] = ST_BEYOND
    return st


def stage_bounds(sessions: np.ndarray, stage: str) -> tuple[int, int]:
    s0, s1 = (np.datetime64(x) for x in C.STAGES[stage])
    return int(np.searchsorted(sessions, s0, side="left")), int(np.searchsorted(sessions, s1, side="right")) - 1


def in_stage(t: np.ndarray, h: int, lo: int, hi: int) -> np.ndarray:
    """Formation t >= stage start AND the whole forward window t+h <= stage end."""
    t = np.asarray(t)
    return (t >= lo) & (t + h <= hi)


def events_frame(pn, flags: dict) -> pd.DataFrame:
    """One row per (entity, session) that belongs to at least one cohort."""
    any_ = flags["comp"] | flags["norm"] | flags["pers"]
    ei, ti = np.nonzero(any_)
    return pd.DataFrame({"entity": np.asarray(pn.entities, dtype=object)[ei], "e": ei, "t": ti,
                         "date": pn.sessions[ti],
                         "is_C": flags["comp"][ei, ti], "is_N": flags["norm"][ei, ti],
                         "is_P": flags["pers"][ei, ti],
                         "pct": flags["pct"][ei, ti]})
