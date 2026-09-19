"""T_c, p-values and effect size (freeze §8, §9, §10; G-4, G-6b, OPEN-P, RR-3).

T_c = mean over formation dates of the per-date cross-sectional Spearman IC of a binary score against
a binary outcome. With average ranks, Spearman on two binary vectors equals their Pearson
correlation (φ), which is what is computed.

A date enters T_c only if it has ≥ MIN_NAMES observations (G-6b) **and** a defined IC. The IC is
undefined when every observation on the date has the same score or the same outcome; such a date is
dropped and counted (OPEN-P = a).
"""

from dataclasses import dataclass

import numpy as np

from scripts.ptms.gann.constants import MIN_NAMES


@dataclass(frozen=True)
class Tc:
    value: float              # NaN if no date qualifies
    n_dates: int
    n_dropped_floor: int      # dates with 1 … MIN_NAMES−1 observations
    n_dropped_undefined: int  # OPEN-P


def t_c(week, score, y, n_weeks, floor=MIN_NAMES) -> Tc:
    """floor: G-6b's 20 for every primary, leg, variant and panel; D-PL uses 10 per half (Q-3)."""
    return t_c_panels(np.zeros(np.size(week), dtype=np.int64), week, score, y, n_weeks, 1, floor)[0]


def t_c_panels(panel, week, score, y, n_weeks, n_panels, floor=MIN_NAMES):
    """T_c of each of n_panels panels whose observations are pooled in one array (panel = its index).
    Dates are grouped by (panel, week), so panels never mix."""
    g = np.asarray(panel, dtype=np.int64) * n_weeks + np.asarray(week, dtype=np.int64)
    size = n_panels * n_weeks
    s = np.asarray(score, dtype=float)
    o = np.asarray(y, dtype=float)
    n = np.bincount(g, minlength=size).astype(float)
    ss, so = np.bincount(g, s, size), np.bincount(g, o, size)
    sso = np.bincount(g, s * o, size)
    # binary: Σs² = Σs
    den = np.where(n > 0, n, 1)
    cov = sso - ss * so / den
    var_s = ss - ss * ss / den
    var_o = so - so * so / den
    floor_ok = n >= floor
    defined = (var_s > 1e-12) & (var_o > 1e-12)
    use = floor_ok & defined
    ic = np.where(use, cov / np.sqrt(np.where(use, var_s * var_o, 1)), 0.0)
    out = []
    for p in range(n_panels):
        sl = slice(p * n_weeks, (p + 1) * n_weeks)
        k = int(use[sl].sum())
        out.append(Tc(float(ic[sl].sum() / k) if k else float("nan"), k,
                      int(((n[sl] > 0) & ~floor_ok[sl]).sum()), int((floor_ok[sl] & ~defined[sl]).sum())))
    return out


def rank_p(observed, null_values):
    """One-sided +1 rank p-value: (1 + #{null ≥ observed}) / (len(null) + 1). Used for p_sur
    (B = 1999), p_plac (132 or 162 placebo sets) and the G-4 contrast (Δ_b)."""
    null = np.asarray(null_values, dtype=float)
    if np.isnan(observed) or np.isnan(null).any():
        raise ValueError("undefined T_c in a p-value; no qualifying formation date on some panel")
    return (1 + int(np.sum(null >= observed))) / (null.size + 1)


def effect_size(observed, surrogate_values):
    """T_c − median T_c(b), with the 2.5–97.5% interval of the surrogate T_c(b). Descriptive."""
    sv = np.asarray(surrogate_values, dtype=float)
    return observed - float(np.median(sv)), (float(np.percentile(sv, 2.5)), float(np.percentile(sv, 97.5)))
