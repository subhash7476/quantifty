"""Strict 3-Day Chart (K3) and the Rule 9 state S9 (freeze §3; memo §5 rows 1–13; R-1; OPEN-Q; v0.8
§1.2 row 4).

K3 is an explicitly labelled approximation of Gann's discretionary detector.

Vectorized over columns: each column is one stock in one panel (real, surrogate or pseudo-real), so
many panels are processed in one pass over time. Input arrays are (T, N) daily highs and lows on a
single ratio-adjusted basis, with NaN where the stock has no bar on that session (not listed, not
yet listed, or missing). Rules:

- Row 12: every comparison is against the stock's previous **available** bar. A NaN session is
  skipped: it neither extends nor breaks a run, and the state is unchanged (OPEN-Q = a).
- Row 5: strict inequalities; an equal value breaks a run.
- Row 11 (literal): an up-switch needs 3 consecutive sessions of HH **and** HL; a down-switch needs 3
  consecutive sessions of LL. From DOWN, the up-switch rule applies; from UP, the down-switch rule.
- Row 13 follows from the definitions: an outside day (HH and LL) counts toward a down run and
  breaks an up run; an inside day breaks both.
- V-K3 (freeze §12, off-path): `symmetric=True` makes a down run need LL **and** LH (memo §5 row 11,
  "Symmetric HH+HL / LL+LH as robustness"), for initialization and switching alike. Then an outside
  day breaks both runs.
- Row 8: no state until the first 3-session run. That initialization confirms no swing.
- Rows 2–4: the swing high is the maximum high while UP; its date is the day of that high; it is
  confirmed at the close of the down-switch session. Mirror for the swing low.

Implementation readings (IR, listed in the P-3 build note for the operator; not freeze text):
- IR-1: equal extremes inside one line take the **first** occurrence (as v0.8 OPEN-4.5).
- IR-2: "while UP" means the sessions whose post-close state is UP: from the switch session that set
  UP (inclusive) to the down-switch session (exclusive). The down-switch session belongs to DOWN.
"""

from dataclasses import dataclass

import numpy as np

from scripts.ptms.gann.constants import K3_RUN

UP, DOWN, NONE = 1, -1, 0


@dataclass(frozen=True)
class K3Result:
    state: np.ndarray        # (T, N) int8: post-close line state
    s9: np.ndarray           # (T, N) int8: post-close S9 (1 BULL, -1 BEAR, 0 NONE)
    sw_t: np.ndarray         # (E,) confirmation session index of each confirmed swing
    sw_col: np.ndarray       # (E,) column
    sw_kind: np.ndarray      # (E,) +1 swing high (confirmed at a down-switch), -1 swing low
    sw_level: np.ndarray     # (E,) swing level
    sw_ext_t: np.ndarray     # (E,) session index of the extreme (first occurrence)


def run_k3(high: np.ndarray, low: np.ndarray, symmetric: bool = False) -> K3Result:
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    if high.shape != low.shape or high.ndim != 2:
        raise ValueError("high and low must be (T, N) arrays of the same shape")
    T, N = high.shape
    state = np.zeros((T, N), dtype=np.int8)
    s9 = np.zeros((T, N), dtype=np.int8)

    cur = np.zeros(N, dtype=np.int8)
    up_run = np.zeros(N, dtype=np.int64)
    dn_run = np.zeros(N, dtype=np.int64)
    prev_h = np.full(N, np.nan)
    prev_l = np.full(N, np.nan)
    ext = np.full(N, np.nan)             # running max high while UP / min low while DOWN
    ext_t = np.full(N, -1, dtype=np.int64)
    highs = np.full((N, 2), np.nan)      # last two confirmed swing highs, [older, newer]
    lows = np.full((N, 2), np.nan)
    cur_s9 = np.zeros(N, dtype=np.int8)
    events = []

    for t in range(T):
        h, lo = high[t], low[t]
        present = ~np.isnan(h)
        with np.errstate(invalid="ignore"):
            hh = h > prev_h
            hl = lo > prev_l
            ll = lo < prev_l
            if symmetric:
                ll = ll & (h < prev_h)
        up_run = np.where(present, np.where(hh & hl, up_run + 1, 0), up_run)
        dn_run = np.where(present, np.where(ll, dn_run + 1, 0), dn_run)

        init_up = present & (cur == NONE) & (up_run >= K3_RUN)
        init_dn = present & (cur == NONE) & (dn_run >= K3_RUN) & ~init_up
        to_dn = present & (cur == UP) & (dn_run >= K3_RUN)
        to_up = present & (cur == DOWN) & (up_run >= K3_RUN)
        stay_up = present & (cur == UP) & ~to_dn
        stay_dn = present & (cur == DOWN) & ~to_up

        for mask, kind in ((to_dn, 1), (to_up, -1)):
            cols = np.nonzero(mask)[0]
            if cols.size:
                events.append((np.full(cols.size, t), cols, np.full(cols.size, kind), ext[cols], ext_t[cols]))
                book = highs if kind == 1 else lows
                book[cols, 0] = book[cols, 1]
                book[cols, 1] = ext[cols]

        # extremes: a stay extends the running extreme (strict, first occurrence);
        # a switch or initialization starts a new line at this session.
        new_hi = stay_up & (h > ext)
        new_lo = stay_dn & (lo < ext)
        start_up = init_up | to_up
        start_dn = init_dn | to_dn
        ext = np.where(new_hi | start_up, h, np.where(new_lo | start_dn, lo, ext))
        ext_t = np.where(new_hi | new_lo | start_up | start_dn, t, ext_t)

        cur = np.where(start_up, UP, np.where(start_dn, DOWN, cur)).astype(np.int8)
        switched = to_dn | to_up
        if switched.any():
            with np.errstate(invalid="ignore"):
                bull = (highs[:, 1] > highs[:, 0]) & (lows[:, 1] > lows[:, 0])
                bear = (highs[:, 1] < highs[:, 0]) & (lows[:, 1] < lows[:, 0])
            cur_s9 = np.where(switched, np.where(bull, 1, np.where(bear, -1, 0)), cur_s9).astype(np.int8)
        prev_h = np.where(present, h, prev_h)
        prev_l = np.where(present, lo, prev_l)
        state[t] = cur
        s9[t] = cur_s9

    if events:
        sw_t, sw_col, sw_kind, sw_level, sw_ext_t = (np.concatenate(x) for x in zip(*events))
    else:
        sw_t = sw_col = sw_kind = sw_ext_t = np.zeros(0, dtype=np.int64)
        sw_level = np.zeros(0)
    order = np.lexsort((sw_t, sw_col))
    return K3Result(state, s9, sw_t[order], sw_col[order], sw_kind[order], sw_level[order], sw_ext_t[order])


def swings_of(res: K3Result, col: int):
    """Confirmed swings of one column in confirmation order: (conf_t, kind, level, ext_t)."""
    lo, hi = np.searchsorted(res.sw_col, [col, col + 1])
    return list(zip(res.sw_t[lo:hi].tolist(), res.sw_kind[lo:hi].tolist(), res.sw_level[lo:hi].tolist(),
                    res.sw_ext_t[lo:hi].tolist()))
