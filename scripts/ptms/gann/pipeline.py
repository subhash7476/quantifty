"""One code path for every panel: real, surrogate and pseudo-real (freeze §8 "identical code"; RR-8a).

A panel is (T, N) highs and lows on the real calendar. Everything that is not a price travels with
the real panel unchanged: the calendar, the formation weeks, PIT membership and the G-7 ex-dates
(`Context`). K panels can be stacked side by side as columns p·N … (p+1)·N − 1 and evaluated in one
pass, because K3, the observations and GF-10 all work column by column. T_c is then computed per
panel, so panels never mix.
"""

from dataclasses import dataclass

import numpy as np

from scripts.ptms.gann.constants import MEAN_BLOCK, OUTCOME_SESSIONS
from scripts.ptms.gann.formation import build, last_anchor, last_swings, running_extremes
from scripts.ptms.gann.gf10 import contrast_obs, primary_obs, run_gf10
from scripts.ptms.gann.k3 import run_k3
from scripts.ptms.gann.scores import GF1_PRIMARY, GF4_PRIMARY
from scripts.ptms.gann.stats import t_c_panels
from scripts.ptms.gann.surrogate import surrogate_panel

CONSTRUCTS = ("GF-1", "GF-4T/R8", "GF-10")
CONTRAST_LEGS = ("GF-10 time", "GF-10 price")
ALL_KEYS = CONSTRUCTS + CONTRAST_LEGS


@dataclass(frozen=True)
class Context:
    ords: np.ndarray            # (T,) session ordinals
    week_last_idx: np.ndarray   # (W,) index of D_L per formation week
    member: np.ndarray          # (T, n) PIT membership
    g7_ord: tuple               # per column: sorted G-7 ex-date ordinals
    n: int                      # stocks per panel

    @classmethod
    def of(cls, panel):
        wl = np.array([w.last_idx for w in panel.cal.formation_weeks()], dtype=np.int64)
        return cls(np.asarray(panel.cal.ordinals, dtype=np.int64), wl, panel.member, panel.g7_ord,
                   panel.member.shape[1])

    @property
    def n_weeks(self):
        return int(self.week_last_idx.size)

    def tiled(self, k):
        if k == 1:
            return self
        return Context(self.ords, self.week_last_idx, np.tile(self.member, (1, k)), self.g7_ord * k, self.n)


@dataclass(frozen=True)
class Facts:
    res: object                 # K3Result
    swings: dict                # last_swings(): {1: (level, ext_t), -1: (level, ext_t)}
    ext_hi: np.ndarray          # GF-1 anchors: running highest high / lowest low (extreme index)
    ext_lo: np.ndarray
    last_swing: np.ndarray      # GF-4T/R8 anchor: most recent confirmed swing (extreme index)


def facts(high, low, symmetric=False):
    res = run_k3(high, low, symmetric)
    T, N = high.shape
    sw = last_swings(res, T, N)
    hi_t, lo_t = running_extremes(high, low)
    return Facts(res, sw, hi_t, lo_t, last_anchor(sw))


def gf1_obs(ctx, high, low, f, score_fn=GF1_PRIMARY, anchors=None):
    return build(ctx.ords, ctx.week_last_idx, high, low, ctx.member, ctx.g7_ord, f.res, f.swings,
                 anchors or [f.ext_hi, f.ext_lo], score_fn)


def gf4_obs(ctx, high, low, f, score_fn=GF4_PRIMARY, span_idx_list=None):
    return build(ctx.ords, ctx.week_last_idx, high, low, ctx.member, ctx.g7_ord, f.res, f.swings,
                 [f.last_swing], score_fn, span_idx_list)


def gf10_obs(ctx, high, low, f, comparator="greatest", rt_scale=1.0, horizon=OUTCOME_SESSIONS):
    """(primary observations, contrast observations)."""
    tr = run_gf10(high, low, ctx.ords, f.res, comparator, rt_scale)
    prim = primary_obs(tr, ctx.week_last_idx, high, low, ctx.ords, ctx.member, ctx.g7_ord, f.swings,
                       horizon=horizon)
    con = contrast_obs(tr, ctx.week_last_idx, high, low, ctx.ords, ctx.member, ctx.g7_ord, f.swings)
    return prim, con


def panel_stats(ctx, high, low, k=1, keys=ALL_KEYS, symmetric=False):
    """T_c per key for each of k stacked panels: a list of k dicts {key: Tc}. Keys: the three
    primaries and the two GF-10 contrast legs (T(time), T(price) on the shared f_w outcome, RR-3)."""
    c = ctx.tiled(k)
    f = facts(high, low, symmetric)
    W = ctx.n_weeks

    def tc(o, score):
        return t_c_panels(o.col // ctx.n, o.week, score, o.y, W, k)

    out = {}
    if "GF-1" in keys:
        o = gf1_obs(c, high, low, f)
        out["GF-1"] = tc(o, o.score)
    if "GF-4T/R8" in keys:
        o = gf4_obs(c, high, low, f)
        out["GF-4T/R8"] = tc(o, o.score)
    if any(key.startswith("GF-10") for key in keys):
        prim, con = gf10_obs(c, high, low, f)
        if "GF-10" in keys:
            out["GF-10"] = tc(prim, prim.score)
        if "GF-10 time" in keys:
            out["GF-10 time"] = tc(con, con.score)
        if "GF-10 price" in keys:
            out["GF-10 price"] = tc(con, con.score_p)
    return [{key: out[key][p] for key in keys} for p in range(k)]


def surrogate_stats(ctx, high, low, close, seeds, mean_block=MEAN_BLOCK, keys=ALL_KEYS, batch=8):
    """panel_stats of one surrogate panel per seed (a SeedSequence), drawn from (high, low, close) and
    evaluated `batch` panels at a time. Order follows `seeds`."""
    out = []
    for i in range(0, len(seeds), batch):
        chunk = seeds[i:i + batch]
        drawn = [surrogate_panel(high, low, close, np.random.default_rng(s), mean_block) for s in chunk]
        out += panel_stats(ctx, np.hstack([d[0] for d in drawn]), np.hstack([d[1] for d in drawn]),
                           len(chunk), keys)
    return out
