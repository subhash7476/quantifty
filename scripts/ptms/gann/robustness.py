"""Robustness variants and diagnostics (freeze §12). Every one is off the pass path and outside the
multiplicity register. Each changes only its named element and otherwise runs the primary's code,
panel, eligibility and exclusions (G-6, G-7, OPEN-M). Variants report T_c; the caller reports effect
size against the primary's surrogate distribution (R-A). V-B5 / V-B60 are surrogate runs and live in
the entry point (R-A′).

Readings ruled by the operator on 2026-09-19 while P-3 was built (recorded in the P-3 build note):
- RB-1 V1-MD: points P4 + 144k are counted in sessions of 𝒟 from the anchor session; the look-ahead
  stays the calendar dates cal(D_L)+1 … +7 (RR-7), and each session in it is scored by its elapsed
  session count.
- RB-2 V4-AS: the G-7 span starts at the earliest swing whose windows can reach the look-ahead
  (delta ≤ 184 days, S-4 derived note), or at d_ref if earlier.
- RB-3 D-BH: base = PIT-member stock-weeks on D_L (GF-1, GF-4T/R8), split into state-rule
  ineligibility (the burn-in G-6a replaced), OPEN-M, G-7, the G-6b floor and entering. GF-10: base =
  the A1 set before exclusions; no state-rule limb.
- RB-4 diagnostics: D-PL puts a close equal to the median in the low half and leaves a stock-week with
  no as-traded bar on D_L out of both halves (counted). D-AA applies the G-6b floor per stratum-date
  and counts depth from the stock's first bar in the window. D-PS leaves out (and counts) a qualifying
  stock whose outcome never varies.
"""

from datetime import date

import numpy as np

from scripts.ptms.gann.constants import (GF1_CYCLE, GF1_P4, GF4_WINDOWS, LOOKAHEAD_DAYS, MIN_NAMES,
                                         OUTCOME_SESSIONS)
from scripts.ptms.gann.gf10 import BEAR, BULL
from scripts.ptms.gann.pipeline import CONSTRUCTS, facts, gf1_obs, gf10_obs, gf4_obs
from scripts.ptms.gann.scores import exact_points_score_fn, gf1_score_fn, residues, window_score_fn
from scripts.ptms.gann.stats import t_c

GF1_P8 = (36, 48, 54, 72, 90, 96, 108, 126, 144)                      # S-1
GF4_WE67 = tuple({(57, 65): (60, 67), (85, 92): (90, 98)}.get(w, w) for w in GF4_WINDOWS)   # R-4, R-D
GF4_WE72 = tuple({(57, 65): (60, 72), (85, 92): (90, 98)}.get(w, w) for w in GF4_WINDOWS)
GF4_CT_POINTS = (90, 180, 270, 360)                                    # S-5, Q-2 = (a)
GF4_REACH = max(b for _, b in GF4_WINDOWS) - 1                         # 184: oldest anchor a window can use
V10_RATIOS = (0.75, 1.33)                                              # R-E
V10_HORIZON = 15                                                       # V10-H15
PL_FLOOR = 10                                                          # Q-3
AA_EDGES = (144, 288)                                                  # Q-4 = (a), weeks
PS_MIN = 5                                                             # Q-5


def _hits(n, res_set):
    return (n > 0) & np.isin(n % GF1_CYCLE, list(res_set))


def _lookahead_session_ranges(ords, week_last_idx):
    """For each formation week, the session indices (lo, hi] whose dates fall in cal(D_L)+1 … +7."""
    t = np.asarray(week_last_idx, dtype=np.int64)
    hi = np.searchsorted(ords, ords[t] + LOOKAHEAD_DAYS, side="right") - 1
    return t, hi


def md_scores(ords, week_last_idx, anchors, res_set=None, in_cal=None):
    """V1-MD (RB-1): 1 iff some session in the look-ahead lies n sessions after an anchor session, with
    n ∈ P4 + 144k. A look-ahead that runs past the calendar's end on a week that OPEN-M keeps
    hard-fails: the sessions it would need were never read."""
    res_set = residues(GF1_P4) if res_set is None else res_set
    ords = np.asarray(ords, dtype=np.int64)
    t, hi = _lookahead_session_ranges(ords, week_last_idx)
    beyond = ords[t] + LOOKAHEAD_DAYS > ords[-1]
    if in_cal is not None and np.any(beyond & in_cal):
        raise SystemExit("V1-MD look-ahead reaches past Z on a week inside the sample")
    W, N = t.size, anchors[0].shape[1]
    score = np.zeros((W, N), dtype=bool)
    for i in range(W):
        for s in range(t[i] + 1, hi[i] + 1):
            for a in anchors:
                at = a[t[i]]
                score[i] |= (at >= 0) & _hits(s - at, res_set)
    return score


def week_scores(ords, week_last_idx, anchors, res_set=None):
    """V1-WK (S-2, Q-1 = a): 1 iff ISO week w + 1 is anchor week + n, n ∈ P4 + 144k."""
    res_set = residues(GF1_P4) if res_set is None else res_set
    ords = np.asarray(ords, dtype=np.int64)
    monday = ords - np.array([date.fromordinal(int(o)).weekday() for o in ords])
    t = np.asarray(week_last_idx, dtype=np.int64)
    score = np.zeros((t.size, anchors[0].shape[1]), dtype=bool)
    for a in anchors:
        at = a[t]
        n = (monday[t][:, None] + 7 - monday[np.maximum(at, 0)]) // 7
        score |= (at >= 0) & _hits(n, res_set)
    return score


def month_scores(ords, week_last_idx, anchors, res_set=None):
    """V1-MO (S-2, Q-1 = a): 1 iff some date in cal(D_L)+1 … +7 falls in month anchor month + n,
    n ∈ P4 + 144k."""
    res_set = residues(GF1_P4) if res_set is None else res_set
    ords = np.asarray(ords, dtype=np.int64)

    def month(o):
        d = date.fromordinal(int(o))
        return d.year * 12 + d.month - 1

    sess_month = np.array([month(o) for o in ords])
    t = np.asarray(week_last_idx, dtype=np.int64)
    score = np.zeros((t.size, anchors[0].shape[1]), dtype=bool)
    for i, ti in enumerate(t):
        ahead = {month(ords[ti] + k) for k in range(1, LOOKAHEAD_DAYS + 1)}
        for a in anchors:
            at = a[ti]
            am = sess_month[np.maximum(at, 0)]
            for m in ahead:
                score[i] |= (at >= 0) & _hits(m - am, res_set)
    return score


def all_swing_scores(ords, week_last_idx, res, N, windows=GF4_WINDOWS):
    """V4-AS (S-4): 1 iff some date in the look-ahead falls in a window of any confirmed swing (union).
    Also the per-week G-7 span anchor (RB-2): the earliest reachable swing extreme, T if none."""
    ords = np.asarray(ords, dtype=np.int64)
    T = ords.size
    t = np.asarray(week_last_idx, dtype=np.int64)
    fn = window_score_fn(windows)
    score = np.zeros((t.size, N), dtype=bool)
    span = np.full((t.size, N), T, dtype=np.int64)
    for j in range(N):
        lo, hi = np.searchsorted(res.sw_col, [j, j + 1])
        conf, ext = res.sw_t[lo:hi], res.sw_ext_t[lo:hi]      # confirmation order = extreme order
        if conf.size == 0:
            continue
        n_conf = np.searchsorted(conf, t, side="right")
        for i, ti in enumerate(t):
            e = ext[:n_conf[i]]
            delta = ords[ti] - ords[e]
            reach = delta <= GF4_REACH
            if reach.any():
                score[i, j] = bool(fn([delta[reach]]).any())
                span[i, j] = int(e[reach].min())
    return score, span


def _fixed(score):
    return lambda _deltas: score


def _obs_tc(o, n_weeks, score=None, rows=None):
    s = o.score if score is None else score
    if rows is None:
        return t_c(o.week, s, o.y, n_weeks)
    return t_c(o.week[rows], s[rows], o.y[rows], n_weeks)


def variants(ctx, high, low, f=None, constructs=CONSTRUCTS):
    """T_c of every §12 variant except V-B5 / V-B60, on one panel: {construct: {variant: Tc}}. A
    construct left out of `constructs` (stopped by the size check, G-9b) is not computed at all."""
    f = f or facts(high, low)
    W, N = ctx.n_weeks, high.shape[1]
    fk = facts(high, low, symmetric=True)                          # V-K3
    out = {}
    if "GF-1" in constructs:
        in_cal = ctx.week_last_idx + OUTCOME_SESSIONS <= ctx.ords.size - 1
        anchors = [f.ext_hi, f.ext_lo]
        wl = ctx.week_last_idx
        out["GF-1"] = {
            "V-K3": _obs_tc(gf1_obs(ctx, high, low, fk), W),
            "V1-MD": _obs_tc(gf1_obs(ctx, high, low, f, _fixed(md_scores(ctx.ords, wl, anchors, in_cal=in_cal))), W),
            "V1-P8": _obs_tc(gf1_obs(ctx, high, low, f, gf1_score_fn(residues(GF1_P8))), W),
            "V1-WK": _obs_tc(gf1_obs(ctx, high, low, f, _fixed(week_scores(ctx.ords, wl, anchors))), W),
            "V1-MO": _obs_tc(gf1_obs(ctx, high, low, f, _fixed(month_scores(ctx.ords, wl, anchors))), W),
            "V1-K3": _obs_tc(gf1_obs(ctx, high, low, f, anchors=[f.swings[1][1], f.swings[-1][1]]), W),
        }
    if "GF-4T/R8" in constructs:
        as_score, as_span = all_swing_scores(ctx.ords, ctx.week_last_idx, f.res, N)
        out["GF-4T/R8"] = {
            "V-K3": _obs_tc(gf4_obs(ctx, high, low, fk), W),
            "V4-WE67": _obs_tc(gf4_obs(ctx, high, low, f, window_score_fn(GF4_WE67)), W),
            "V4-WE72": _obs_tc(gf4_obs(ctx, high, low, f, window_score_fn(GF4_WE72)), W),
            "V4-AS": _obs_tc(gf4_obs(ctx, high, low, f, _fixed(as_score), [as_span]), W),
            "V4-CT": _obs_tc(gf4_obs(ctx, high, low, f, exact_points_score_fn(GF4_CT_POINTS)), W),
        }
    if "GF-10" in constructs:
        prim, _ = gf10_obs(ctx, high, low, f)
        g10 = {
            "V-K3": _obs_tc(gf10_obs(ctx, high, low, fk)[0], W),
            "V10-IP": _obs_tc(gf10_obs(ctx, high, low, f, comparator="preceding")[0], W),
            "V10-H15": _obs_tc(gf10_obs(ctx, high, low, f, horizon=V10_HORIZON)[0], W),
        }
        for r in V10_RATIOS:
            g10[f"R_T x {r}"] = _obs_tc(gf10_obs(ctx, high, low, f, rt_scale=r)[0], W)
        g10["N-DIR bull"] = _obs_tc(prim, W, rows=prim.dir == BULL)
        g10["N-DIR bear"] = _obs_tc(prim, W, rows=prim.dir == BEAR)
        g10["N-SZ"] = _obs_tc(prim, W, rows=prim.sz == 0)
        out["GF-10"] = g10
    return out


# ---------------------------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------------------------

def d_pl(o, week_last_idx, close_raw, n_weeks):
    """D-PL (S-6): T_c of the low and high halves at the per-date median as-traded close on D_L."""
    t = np.asarray(week_last_idx, dtype=np.int64)[o.week]
    px = close_raw[t, o.col]
    ok = ~np.isnan(px)
    low = np.zeros(o.week.size, dtype=bool)
    for w in np.unique(o.week[ok]):
        rows = ok & (o.week == w)
        low[rows] = px[rows] <= np.median(px[rows])
    high = ok & ~low
    return {"low": t_c(o.week[low], o.score[low], o.y[low], n_weeks, PL_FLOOR),
            "high": t_c(o.week[high], o.score[high], o.y[high], n_weeks, PL_FLOOR),
            "n_no_bar": int((~ok).sum())}


def d_aa(o, ords, week_last_idx, first_bar_idx, n_weeks):
    """D-AA (S-7, GF-1 only): T_c by store-history depth at D_L, in weeks: < 144, 144–288, ≥ 288."""
    ords = np.asarray(ords, dtype=np.int64)
    t = np.asarray(week_last_idx, dtype=np.int64)[o.week]
    depth = (ords[t] - ords[first_bar_idx[o.col]]) / 7.0
    strata = {"< 144": depth < AA_EDGES[0], "144-288": (depth >= AA_EDGES[0]) & (depth < AA_EDGES[1]),
              ">= 288": depth >= AA_EDGES[1]}
    return {k: t_c(o.week[m], o.score[m], o.y[m], n_weeks) for k, m in strata.items()}


def d_ps(o, entities):
    """D-PS (S-8): per-stock φ for stocks with ≥ 5 score-1 and ≥ 5 score-0 weeks. Descriptive."""
    rows, n_undefined = [], 0
    for j in np.unique(o.col):
        m = o.col == j
        s, y = o.score[m].astype(float), o.y[m].astype(float)
        n1 = int(s.sum())
        n0 = int(s.size - n1)
        if n1 < PS_MIN or n0 < PS_MIN:
            continue
        if y.std() == 0:
            n_undefined += 1
            continue
        rows.append((entities[j], n1, n0, float(np.corrcoef(s, y)[0, 1])))
    phi = np.array([r[3] for r in rows])
    summary = {"n_stocks": len(rows), "n_undefined": n_undefined}
    if phi.size:
        summary.update(median=float(np.median(phi)), q1=float(np.percentile(phi, 25)),
                       q3=float(np.percentile(phi, 75)), share_positive=float((phi > 0).mean()))
    return summary, rows


def floor_rows(week, n_weeks):
    """Observations on formation dates dropped by the G-6b floor (1 … 19 names)."""
    n = np.bincount(np.asarray(week, dtype=np.int64), minlength=n_weeks)
    return int(np.sum(np.where((n > 0) & (n < MIN_NAMES), n, 0)))


def d_bh(o, n_weeks, gf10=False):
    """D-BH (RB-3): the exclusion-loss share, per limb, as counts and shares of the base."""
    kept = int(o.week.size)
    floor = floor_rows(o.week, n_weeks)
    if gf10:
        base = kept + o.n_excluded_open_m + o.n_excluded_g7
        limbs = {"OPEN-M": o.n_excluded_open_m, "G-7": o.n_excluded_g7, "G-6b floor": floor}
    else:
        base = o.n_member
        limbs = {"state rules": o.n_ineligible, "OPEN-M": o.n_excluded_open_m, "G-7": o.n_excluded_g7,
                 "G-6b floor": floor}
    limbs["entering"] = kept - floor
    if sum(limbs.values()) != base:
        raise AssertionError("D-BH limbs do not partition the base")
    label = "the A1 set before exclusions" if gf10 else "PIT-member stock-weeks on D_L"
    return {"base": base, "base_label": label, "limbs": limbs,
            "shares": {k: (v / base if base else float("nan")) for k, v in limbs.items()}}
