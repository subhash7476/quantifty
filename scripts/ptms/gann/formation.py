"""GF-1 and GF-4T/R8 observations: eligibility, O-R10 and exclusions (freeze §2.2, §2.3, §4, §6, §7, §11).

This path is for GF-1 and GF-4T/R8 **only**. GF-10's outcome differs on the read instant, the window
anchor and the prior-penetration rule (freeze §4 table), and it lives in its own module.

For formation week *w* with last session D_L (index t), per column j:
- State, anchors and the O-R10 reference are read as of close(D_L), **including** D_L (RR-4).
- Eligible: PIT member on D_L (RR-7), K3 state UP or DOWN (NO STATE ⇒ ineligible, G-2(a)) and the
  construct's anchor available. If no reference swing of the needed type is confirmed yet (a stock's
  first K3 line), the stock-week is eligible with y = 0 and its G-7 span starts at its anchors
  (PENDING-1 = b, operator ruling 2026-09-19).
- O-R10: K3 UP → 1 iff some low in O_1 … O_5 is strictly below the last swing low (RR-5); K3 DOWN →
  1 iff some high is strictly above the last swing high. No prior-penetration rule (RR-6). A session
  with no bar contributes no penetration (IR-4).
- OPEN-M: excluded if O_5 > Z. The calendar ends at Z, so O_5 must exist in it.
- G-7: excluded if any G-7 ex-date lies in [span start, O_5], span start = the earliest of every
  anchor date the score uses and the reference's extreme date (OC-1 = b).
"""

from dataclasses import dataclass

import numpy as np

from scripts.ptms.gann.constants import OUTCOME_SESSIONS
from scripts.ptms.gann.k3 import DOWN, UP, K3Result


@dataclass(frozen=True)
class Obs:
    week: np.ndarray        # (M,) formation-week number
    col: np.ndarray         # (M,) column
    score: np.ndarray       # (M,) int8
    y: np.ndarray           # (M,) int8
    n_excluded_open_m: int
    n_excluded_g7: int
    n_member: int = 0       # D-BH base: PIT-member stock-weeks on D_L
    n_ineligible: int = 0   # D-BH: member stock-weeks ineligible under the state rules (no K3 state or anchor)


def last_swings(res: K3Result, T: int, N: int):
    """Forward-filled level and extreme index of the last confirmed swing high and low, as of each
    close (a swing confirmed at t counts at t). NaN / -1 before the first."""
    out = {}
    for kind in (1, -1):
        level = np.full((T, N), np.nan)
        ext_t = np.full((T, N), -1, dtype=np.int64)
        sel = res.sw_kind == kind
        level[res.sw_t[sel], res.sw_col[sel]] = res.sw_level[sel]
        ext_t[res.sw_t[sel], res.sw_col[sel]] = res.sw_ext_t[sel]
        for t in range(1, T):
            fill = ext_t[t] < 0
            level[t, fill] = level[t - 1, fill]
            ext_t[t, fill] = ext_t[t - 1, fill]
        out[kind] = (level, ext_t)
    return out


def last_anchor(swings):
    """GF-4T/R8 anchor: the most recently confirmed swing of either kind; its extreme index."""
    hi_t, lo_t = swings[1][1], swings[-1][1]
    return np.maximum(hi_t, lo_t)


def running_extremes(high, low):
    """GF-1 anchors: extreme index of the running highest high and lowest low, as of each close.
    Only a strictly new extreme replaces an anchor (IR-3). -1 before the first bar."""
    T, N = high.shape
    hi_t = np.full((T, N), -1, dtype=np.int64)
    lo_t = np.full((T, N), -1, dtype=np.int64)
    best_h = np.full(N, np.nan)
    best_l = np.full(N, np.nan)
    cur_h = np.full(N, -1, dtype=np.int64)
    cur_l = np.full(N, -1, dtype=np.int64)
    for t in range(T):
        with np.errstate(invalid="ignore"):
            nh = ~np.isnan(high[t]) & (np.isnan(best_h) | (high[t] > best_h))
            nl = ~np.isnan(low[t]) & (np.isnan(best_l) | (low[t] < best_l))
        best_h = np.where(nh, high[t], best_h)
        best_l = np.where(nl, low[t], best_l)
        cur_h = np.where(nh, t, cur_h)
        cur_l = np.where(nl, t, cur_l)
        hi_t[t], lo_t[t] = cur_h, cur_l
    return hi_t, lo_t


def build(cal_ordinals, week_last_idx, high, low, member, g7_ord, res, swings, anchor_idx_list, score_fn,
          span_idx_list=None):
    """Assemble observations for GF-1 or GF-4T/R8 (and their placebos / variants via score_fn).

    anchor_idx_list: list of (T, N) arrays of anchor extreme indices (-1 = none) used by the score.
    score_fn(delta_list) -> (W, N) bool, where delta_list[i] = ord(D_L) − ord(anchor_i) per cell.
    span_idx_list: (W, N) arrays, one row per formation week, of the anchors that start the G-7 span
    when they differ from the eligibility anchors (V4-AS: the earliest reachable swing; T = none).
    Defaults to the eligibility anchors.
    """
    T, N = high.shape
    ords = np.asarray(cal_ordinals, dtype=np.int64)
    t = np.asarray(week_last_idx, dtype=np.int64)
    W = t.size
    in_cal = t + OUTCOME_SESSIONS <= T - 1                      # OPEN-M (calendar ends at Z)
    state = res.state[t]
    lvl_lo, ext_lo = swings[-1][0][t], swings[-1][1][t]
    lvl_hi, ext_hi = swings[1][0][t], swings[1][1][t]
    ref_lvl = np.where(state == UP, lvl_lo, lvl_hi)
    ref_ext = np.where(state == UP, ext_lo, ext_hi)
    anchors = [a[t] for a in anchor_idx_list]

    eligible = member[t] & (state != 0) & np.all([a >= 0 for a in anchors], axis=0)

    d_l_ord = ords[t][:, None]
    deltas = [d_l_ord - ords[np.maximum(a, 0)] for a in anchors]
    score = score_fn(deltas)

    y = np.zeros((W, N), dtype=bool)
    o5_ord = np.full(W, np.iinfo(np.int64).max)
    for i in np.nonzero(in_cal)[0]:
        win = slice(t[i] + 1, t[i] + OUTCOME_SESSIONS + 1)
        with np.errstate(invalid="ignore"):
            broke_lo = np.any(low[win] < ref_lvl[i], axis=0)
            broke_hi = np.any(high[win] > ref_lvl[i], axis=0)
        y[i] = np.where(state[i] == UP, broke_lo, np.where(state[i] == DOWN, broke_hi, False))
        o5_ord[i] = ords[t[i] + OUTCOME_SESSIONS]

    spans = anchors if span_idx_list is None else list(span_idx_list)
    start_idx = np.minimum.reduce([*spans, np.where(ref_ext >= 0, ref_ext, T)])
    if np.any(eligible & (start_idx >= T)):
        raise AssertionError("an eligible observation has no G-7 span start")
    start_ord = ords[np.clip(start_idx, 0, T - 1)]
    g7_hit = np.zeros((W, N), dtype=bool)
    for j in range(N):
        ex = g7_ord[j]
        if ex.size:
            first = np.searchsorted(ex, start_ord[:, j], side="left")
            g7_hit[:, j] = (first < ex.size) & (ex[np.minimum(first, ex.size - 1)] <= o5_ord)

    base = eligible & in_cal[:, None]
    keep = base & ~g7_hit
    wi, cj = np.nonzero(keep)
    return Obs(wi, cj, score[wi, cj].astype(np.int8), y[wi, cj].astype(np.int8),
               int((eligible & ~in_cal[:, None]).sum()), int((base & g7_hit).sum()),
               int(member[t].sum()), int((member[t] & ~eligible).sum()))
