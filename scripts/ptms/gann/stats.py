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


def t_c(week, score, y, n_weeks) -> Tc:
    week = np.asarray(week, dtype=np.int64)
    s = np.asarray(score, dtype=float)
    o = np.asarray(y, dtype=float)
    n = np.bincount(week, minlength=n_weeks).astype(float)
    ss, so = np.bincount(week, s, n_weeks), np.bincount(week, o, n_weeks)
    sso = np.bincount(week, s * o, n_weeks)
    # binary: Σs² = Σs
    cov = sso - ss * so / np.where(n > 0, n, 1)
    var_s = ss - ss * ss / np.where(n > 0, n, 1)
    var_o = so - so * so / np.where(n > 0, n, 1)
    floor_ok = n >= MIN_NAMES
    defined = (var_s > 1e-12) & (var_o > 1e-12)
    use = floor_ok & defined
    ic = cov[use] / np.sqrt(var_s[use] * var_o[use])
    return Tc(float(ic.mean()) if ic.size else float("nan"), int(use.sum()),
              int(((n > 0) & ~floor_ok).sum()), int((floor_ok & ~defined).sum()))


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
