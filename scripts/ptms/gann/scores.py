"""GF-1 and GF-4T/R8 score rules and their G-3 placebo families (freeze §2.2, §2.3, §9).

A score looks at the calendar dates cal(D_L) + 1 … cal(D_L) + 7 (RR-7). With delta = cal(D_L) −
cal(anchor) ≥ 0, those dates sit at elapsed days delta + 1 … delta + 7.
"""

import numpy as np

from scripts.ptms.gann.constants import GF1_CYCLE, GF1_P4, GF4_WINDOWS, LOOKAHEAD_DAYS


# ---- GF-1: a point set of residues modulo 144, repeating every 144 days (P4 + 144k) ----

def residues(points):
    return frozenset(p % GF1_CYCLE for p in points)


def residue_hit_table(res_set):
    """hit[r] for r = delta mod 144: some elapsed day in delta+1 … delta+7 is a point. Elapsed day 0
    (the anchor date) is never in the look-ahead, so residue 0 means 144, 288, … (G-3 GF-1)."""
    mark = np.zeros(GF1_CYCLE, dtype=bool)
    mark[list(res_set)] = True
    return np.array([any(mark[(r + k) % GF1_CYCLE] for k in range(1, LOOKAHEAD_DAYS + 1))
                     for r in range(GF1_CYCLE)])


def gf1_score_fn(res_set):
    table = residue_hit_table(res_set)
    def fn(deltas):
        return np.logical_or.reduce([table[d % GF1_CYCLE] for d in deltas])
    return fn


def gf1_placebo_residue_sets():
    """G-3 GF-1: every shift d ∈ {0 … 143} of P4 mod 144 whose shifted set is disjoint from P4.
    Exactly 132 sets; no RNG."""
    p4 = residues(GF1_P4)
    sets = []
    for d in range(GF1_CYCLE):
        shifted = frozenset((p + d) % GF1_CYCLE for p in p4)
        if not shifted & p4:
            sets.append((d, shifted))
    if len(sets) != 132:
        raise AssertionError(f"G-3 GF-1 family has {len(sets)} sets, expected 132")
    return sets


# ---- GF-4T/R8: one-shot windows in calendar days from the anchor, no periodicity ----

def window_hit_table(windows, max_delta):
    """hit[delta]: some elapsed day in delta+1 … delta+7 falls in a window (inclusive)."""
    covered = np.zeros(max_delta + LOOKAHEAD_DAYS + 2, dtype=bool)
    for a, b in windows:
        covered[a:b + 1] = True
    return np.array([covered[delta + 1:delta + LOOKAHEAD_DAYS + 1].any() for delta in range(max_delta + 1)])


def window_score_fn(windows):
    max_end = max(b for _, b in windows)
    table = window_hit_table(windows, max_end)
    def fn(deltas):
        d = deltas[0]
        return (d <= max_end) & table[np.clip(d, 0, max_end)]
    return fn


def exact_points_score_fn(points):
    """V4-CT: exact-date points (no window width), the 7-day look-ahead as the only tolerance."""
    return window_score_fn(tuple((p, p) for p in points))


def gf4_placebo_window_sets():
    """G-3 GF-4T/R8: rigid translations d = 1 … 179 of the nine windows, excluding every d that makes
    any translated centre equal an original centre. Exactly 162 sets; no RNG."""
    centres = {(a + b) / 2 for a, b in GF4_WINDOWS}
    sets = []
    for d in range(1, 180):
        moved = tuple((a + d, b + d) for a, b in GF4_WINDOWS)
        if not {(a + b) / 2 for a, b in moved} & centres:
            sets.append((d, moved))
    if len(sets) != 162:
        raise AssertionError(f"G-3 GF-4T/R8 family has {len(sets)} sets, expected 162")
    return sets


GF1_PRIMARY = gf1_score_fn(residues(GF1_P4))
GF4_PRIMARY = window_score_fn(GF4_WINDOWS)
