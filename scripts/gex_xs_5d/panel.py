"""GEX-XS-5D pure functions: sessions, formations, per-name construction, statistic, test.

Spec: docs/reports/GEX_XS_5D_PRE_REGISTRATION.md (FROZEN 2026-10-06). Every threshold here
is pinned there; core/analytics/gex_history.py is reused unchanged.
"""
from __future__ import annotations

import math
from bisect import bisect_right
from datetime import date, datetime

import numpy as np
from scipy import stats

from core.analytics.gex_history import ExpiryStrikes

# §2 D10 — the six weekday Diwali Muhurat sessions the store holds
SPECIAL_SESSIONS = frozenset({
    date(2017, 10, 19), date(2018, 11, 7), date(2021, 11, 4),
    date(2022, 10, 24), date(2024, 11, 1), date(2025, 10, 21),
})
STEP = 5                     # §2 formation spacing and target length
MIN_KEPT = 6                 # §4 D3
MIN_SIDE = 2
MAX_FWD_DEV = 0.03           # §4 D4
WINSOR_PCT = (1.0, 99.0)     # §8 D8
MIN_NAMES = 80               # §8 D6
NW_LAG = 4                   # §1 D7
RV5_MIN, RV20_MIN = 4, 15    # §6


def session_grid(dates, start: date, end: date) -> list[date]:
    return sorted(d for d in set(dates)
                  if start <= d <= end and d.weekday() < 5 and d not in SPECIAL_SESSIONS)


def formation_indices(n_sessions: int, phase: int = 0) -> list[int]:
    """Session indices of formations: every 5th from `phase`, with t+5 inside the stage."""
    return [i for i in range(phase, n_sessions, STEP) if i + STEP <= n_sessions - 1]


def name_valid(expiries: list[ExpiryStrikes]) -> bool:
    kept = sum(len(e.strikes) for e in expiries)
    below = sum(int((e.strikes < e.forward).sum()) for e in expiries)
    return kept >= MIN_KEPT and below >= MIN_SIDE and kept - below >= MIN_SIDE


def atm_iv(e: ExpiryStrikes):
    """IV at K = F: linear in ln(K/F) between the nearest kept strike below F and the nearest
    at or above F. None if either side is empty."""
    below, above = e.strikes < e.forward, e.strikes >= e.forward
    if not below.any() or not above.any():
        return None
    i_lo = np.flatnonzero(below)[np.argmax(e.strikes[below])]
    i_hi = np.flatnonzero(above)[np.argmin(e.strikes[above])]
    k_lo, k_hi = e.strikes[i_lo], e.strikes[i_hi]
    if k_hi == e.forward:
        return float(e.iv[i_hi])
    x_lo, x_hi = math.log(k_lo / e.forward), math.log(k_hi / e.forward)
    w = (0.0 - x_lo) / (x_hi - x_lo)
    return float(e.iv[i_lo] + w * (e.iv[i_hi] - e.iv[i_lo]))


def iv_expiry(expiries, window_end: date):
    """Nearest expiry that expires after the date of session t+5 (§5 D5)."""
    later = sorted(x for x in expiries if x > window_end)
    return later[0] if later else None


def parkinson(high: float, low: float) -> float:
    return math.log(high / low) ** 2 / (4 * math.log(2))


def index_meetings(rows) -> dict:
    """{key: sorted [(bm_date, known_ts)]} keyed by ('p', isin_prefix) and ('s', symbol)."""
    idx = {}
    for r in rows:
        item = (r["bm_date"], r["known_ts"])
        if r.get("isin_prefix"):
            idx.setdefault(("p", r["isin_prefix"]), []).append(item)
        idx.setdefault(("s", r["symbol"]), []).append(item)
    for v in idx.values():
        v.sort()
    return idx


def results_excluded(idx, prefix, symbol, t: date, t5: date, close_dt: datetime,
                     posthoc: bool = False) -> bool:
    """§7: a results meeting dated date(t)..date(session t+5) inclusive, known by the
    derivatives close on t. posthoc=True ignores the known time (descriptive split only)."""
    for key in (("p", prefix), ("s", symbol)):
        meetings = idx.get(key, [])
        i = bisect_right(meetings, (t, datetime.min))
        while i < len(meetings) and meetings[i][0] <= t5:
            if posthoc or meetings[i][1] <= close_dt:
                return True
            i += 1
    return False


def winsorize(x: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(x, WINSOR_PCT)
    return np.clip(x, lo, hi)


def _resid(v: np.ndarray, X: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(X, v, rcond=None)
    return v - X @ beta


def residual_ic(N: np.ndarray, y: np.ndarray, C: np.ndarray, method: str = "spearman") -> float:
    """§8: N and y each residualized on [1, controls]; rank (or Pearson) correlation."""
    X = np.column_stack([np.ones(len(N)), C])
    rn, ry = _resid(N, X), _resid(y, X)
    if method == "pearson":
        return float(np.corrcoef(rn, ry)[0, 1])
    return float(stats.spearmanr(rn, ry).statistic)


def nw_mean_test(x: np.ndarray, lag: int = NW_LAG) -> dict:
    """Mean with a Newey-West (Bartlett) HAC standard error; one-sided p for mean < 0."""
    x = np.asarray(x, float)
    n, m = len(x), float(np.mean(x))
    d = x - m
    var = float(d @ d) / n
    for l in range(1, min(lag, n - 1) + 1):
        var += 2 * (1 - l / (lag + 1)) * float(d[l:] @ d[:-l]) / n
    se = math.sqrt(var / n)
    t = m / se if se > 0 else float("nan")
    return {"n": n, "mean": m, "se": se, "t": t, "p_one_sided": float(stats.t.cdf(t, n - 1))}


def ac1(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    return float(np.corrcoef(x[:-1], x[1:])[0, 1]) if len(x) > 2 else float("nan")
