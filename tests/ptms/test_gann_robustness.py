"""Pipeline, robustness variants and diagnostics, on synthetic panels only. No store is read."""

from datetime import date, timedelta

import numpy as np
import pytest

from scripts.ptms.gann import pipeline, robustness
from scripts.ptms.gann.calendar import Calendar
from scripts.ptms.gann.constants import GF4_WINDOWS
from scripts.ptms.gann.formation import Obs
from scripts.ptms.gann.k3 import DOWN, UP, run_k3
from scripts.ptms.gann.panel import Panel
from scripts.ptms.gann.scores import window_score_fn
from scripts.ptms.gann.stats import t_c


def weekdays(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def synthetic_panel(seed, T=700, N=30):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, (T, N)), axis=0))
    h = np.round(c * (1 + np.abs(rng.normal(0, 0.012, (T, N)))), 2)
    lo = np.round(c * (1 - np.abs(rng.normal(0, 0.012, (T, N)))), 2)
    c = np.round(c, 2)
    h[:40, 0] = lo[:40, 0] = c[:40, 0] = np.nan                 # a late listing
    gaps = rng.random((T, N)) < 0.005
    h[gaps] = lo[gaps] = c[gaps] = np.nan
    cal = Calendar(weekdays(date(2015, 1, 5), T))
    member = np.ones((T, N), dtype=bool)
    member[:100, 1] = False
    ex = [np.array(sorted(rng.choice(cal.ordinals, 2, replace=False)), dtype=np.int64) if j % 7 == 0
          else np.zeros(0, dtype=np.int64) for j in range(N)]
    return Panel(cal, tuple(f"E{j}" for j in range(N)), h, lo, c, c * 2.0, member, tuple(ex))


# ---- pipeline ----

def as_tuple(tc):
    return (None if np.isnan(tc.value) else tc.value, tc.n_dates, tc.n_dropped_floor, tc.n_dropped_undefined)


def test_stacked_panels_give_the_same_statistics_as_separate_runs():
    a, b = synthetic_panel(1, N=120), synthetic_panel(2, N=120)
    ctx = pipeline.Context.of(a)
    sep = pipeline.panel_stats(ctx, a.high, a.low) + pipeline.panel_stats(ctx, b.high, b.low)
    stacked = pipeline.panel_stats(ctx, np.hstack([a.high, b.high]), np.hstack([a.low, b.low]), k=2)
    flat = lambda runs: [{k: as_tuple(v) for k, v in s.items()} for s in runs]
    assert flat(sep) == flat(stacked)
    assert all(s[k].n_dates > 0 for s in sep for k in pipeline.ALL_KEYS)


def test_keys_restrict_the_computation():
    a = synthetic_panel(1)
    ctx = pipeline.Context.of(a)
    got = pipeline.panel_stats(ctx, a.high, a.low, keys=("GF-4T/R8",))[0]
    assert set(got) == {"GF-4T/R8"}
    assert got == {"GF-4T/R8": pipeline.panel_stats(ctx, a.high, a.low)[0]["GF-4T/R8"]}


def test_panel_tc_matches_single_panel_tc():
    rng = np.random.default_rng(0)
    week = rng.integers(0, 10, 900)
    s, y = rng.integers(0, 2, 900), rng.integers(0, 2, 900)
    from scripts.ptms.gann.stats import t_c_panels
    a = t_c_panels(np.zeros(900, dtype=int), week, s, y, 10, 1)[0]
    assert a == t_c(week, s, y, 10)


# ---- V-K3 ----

def test_symmetric_k3_needs_lower_highs_so_outside_days_do_not_switch_down():
    up = [(10 + i, 5 + i) for i in range(5)]                     # HH + HL: UP from session 3
    outside = [(15 + i, 3 - i) for i in range(3)]                # HH + LL three times
    lower = [(14 - i, 0 - i) for i in range(3)]                  # LL + LH three times
    bars = up + outside + lower
    h = np.array([[b[0]] for b in bars], dtype=float)
    lo = np.array([[b[1]] for b in bars], dtype=float)
    lit, sym = run_k3(h, lo), run_k3(h, lo, symmetric=True)
    assert lit.state[7, 0] == DOWN                               # literal: LL alone switches
    assert sym.state[7, 0] == UP and sym.state[10, 0] == DOWN    # symmetric waits for LL + LH
    assert list(sym.sw_ext_t) == [7]                             # swing high on the last outside day


# ---- GF-1 unit variants ----

def test_week_unit_scores_the_next_iso_week():
    sessions = weekdays(date(2015, 1, 5), 400)
    ords = np.array([d.toordinal() for d in sessions])
    cal = Calendar(sessions)
    wl = np.array([w.last_idx for w in cal.formation_weeks()])
    anchor_idx = cal.index[date(2015, 1, 7)]                     # a Wednesday in ISO week 2015-W02
    a = np.full((len(sessions), 1), anchor_idx)
    got = robustness.week_scores(ords, wl, [a])[:, 0]
    hit_weeks = [cal.sessions[wl[i]] for i in np.nonzero(got)[0]]
    # w + 1 = anchor week + 36 / 48 / 72 → w = W02 + 35, + 47, + 71
    monday0 = date(2015, 1, 5)
    expect = [monday0 + timedelta(weeks=n - 1) + timedelta(days=4) for n in (36, 48, 72)]
    assert hit_weeks == expect


def test_month_unit_flags_every_week_touching_a_point_month():
    sessions = weekdays(date(2015, 1, 5), 900)
    ords = np.array([d.toordinal() for d in sessions])
    cal = Calendar(sessions)
    wl = np.array([w.last_idx for w in cal.formation_weeks()])
    a = np.full((len(sessions), 1), 0)                           # anchor in January 2015
    got = robustness.month_scores(ords, wl, [a])[:, 0]
    hit = [cal.sessions[wl[i]] for i in np.nonzero(got)[0]]
    assert hit[0] == date(2017, 12, 29)                          # look-ahead reaches 2018-01 = month 36
    assert all(date(2017, 12, 29) <= d <= date(2018, 1, 31) for d in hit)
    assert len(hit) == 5


def test_market_day_unit_counts_sessions_and_keeps_the_calendar_lookahead():
    sessions = weekdays(date(2015, 1, 5), 300)
    ords = np.array([d.toordinal() for d in sessions])
    cal = Calendar(sessions)
    wl = np.array([w.last_idx for w in cal.formation_weeks()])
    a = np.full((len(sessions), 1), 3)
    got = robustness.md_scores(ords, wl, [a])[:, 0]
    brute = []
    for t in wl:
        ahead = [s for s in range(len(sessions)) if 0 < ords[s] - ords[t] <= 7]
        brute.append(any((s - 3) % 144 in {36, 48, 72, 96, 108, 0} and s > 3 for s in ahead))
    assert got.tolist() == brute and any(brute)


def test_market_day_lookahead_past_the_calendar_end_hard_fails_on_a_kept_week():
    sessions = weekdays(date(2015, 1, 5), 30)
    ords = np.array([d.toordinal() for d in sessions])
    wl = np.array([29])
    a = np.zeros((30, 1), dtype=np.int64)
    with pytest.raises(SystemExit):
        robustness.md_scores(ords, wl, [a], in_cal=np.array([True]))
    robustness.md_scores(ords, wl, [a], in_cal=np.array([False]))


# ---- GF-4T/R8 variants ----

def test_worked_example_window_sets():
    assert robustness.GF4_WE67 == ((7, 12), (18, 21), (28, 31), (42, 49), (60, 67), (90, 98), (112, 120),
                                   (150, 157), (175, 185))
    assert robustness.GF4_WE72[4] == (60, 72) and robustness.GF4_WE72[5] == (90, 98)


def test_all_swings_score_and_span_match_brute_force():
    p = synthetic_panel(4, T=500, N=6)
    res = run_k3(p.high, p.low)
    ords = np.array(p.cal.ordinals)
    wl = np.array([w.last_idx for w in p.cal.formation_weeks()])
    score, span = robustness.all_swing_scores(ords, wl, res, 6)
    fn = window_score_fn(GF4_WINDOWS)
    for j in range(6):
        sw = [(t, e) for t, c, e in zip(res.sw_t, res.sw_col, res.sw_ext_t) if c == j]
        for i, t in enumerate(wl):
            reach = [e for ct, e in sw if ct <= t and ords[t] - ords[e] <= 184]
            assert score[i, j] == any(bool(fn([np.array([ords[t] - ords[e]])])[0]) for e in reach)
            assert span[i, j] == (min(reach) if reach else len(ords))
    assert score.any()


def test_variants_run_and_respect_the_construct_filter():
    p = synthetic_panel(5)
    ctx = pipeline.Context.of(p)
    out = robustness.variants(ctx, p.high, p.low)
    assert set(out["GF-1"]) == {"V-K3", "V1-MD", "V1-P8", "V1-WK", "V1-MO", "V1-K3"}
    assert set(out["GF-4T/R8"]) == {"V-K3", "V4-WE67", "V4-WE72", "V4-AS", "V4-CT"}
    assert set(out["GF-10"]) == {"V-K3", "V10-IP", "V10-H15", "R_T x 0.75", "R_T x 1.33", "N-DIR bull",
                                 "N-DIR bear", "N-SZ"}
    assert out["GF-1"]["V1-P8"].n_dates > 0
    only = robustness.variants(ctx, p.high, p.low, constructs=("GF-4T/R8",))
    assert set(only) == {"GF-4T/R8"} and only["GF-4T/R8"] == out["GF-4T/R8"]


# ---- diagnostics ----

def obs(week, col, score, y):
    return Obs(np.array(week), np.array(col), np.array(score, dtype=np.int8), np.array(y, dtype=np.int8), 0, 0)


def test_price_level_halves_put_the_median_in_the_low_half_and_count_missing_bars():
    o = obs([0] * 5, [0, 1, 2, 3, 4], [1, 0, 1, 0, 1], [1, 0, 0, 1, 1])
    close_raw = np.array([[1.0, 2.0, 2.0, 3.0, np.nan]])
    res = robustness.d_pl(o, [0], close_raw, 1)
    assert res["n_no_bar"] == 1
    assert res["low"].n_dropped_floor == 1 and res["high"].n_dropped_floor == 1   # 3 and 1 names < 10


def test_price_level_split_membership():
    rng = np.random.default_rng(1)
    n = 24
    o = obs([0] * n, list(range(n)), rng.integers(0, 2, n), rng.integers(0, 2, n))
    px = np.arange(1, n + 1, dtype=float)[None, :]
    res = robustness.d_pl(o, [0], px, 1)
    low = px[0] <= np.median(px[0])
    assert res["low"] == t_c(o.week[low], o.score[low], o.y[low], 1, 10)


def test_history_depth_strata_edges():
    ords = np.arange(3000) + date(2010, 1, 1).toordinal()
    first = np.array([0, 0, 0])
    wl = np.array([144 * 7 - 1, 144 * 7, 288 * 7])
    o = obs([0, 1, 2], [0, 1, 2], [1, 0, 1], [1, 1, 0])
    res = robustness.d_aa(o, ords, wl, first, 3)
    assert {k: v.n_dropped_floor for k, v in res.items()} == {"< 144": 1, "144-288": 1, ">= 288": 1}


def test_per_stock_phi_needs_five_and_five_and_counts_constant_outcomes():
    rows = []
    for col, (n1, n0, const) in enumerate([(5, 5, False), (4, 9, False), (6, 6, True)]):
        s = [1] * n1 + [0] * n0
        y = [0] * (n1 + n0) if const else [1] * n1 + [0] * n0
        rows += [(w, col, a, b) for w, (a, b) in enumerate(zip(s, y))]
    o = obs(*map(list, zip(*rows)))
    summary, per = robustness.d_ps(o, ("A", "B", "C"))
    assert summary["n_stocks"] == 1 and summary["n_undefined"] == 1
    assert per == [("A", 5, 5, 1.0)]


def test_exclusion_loss_limbs_partition_member_stock_weeks():
    p = synthetic_panel(6)
    ctx = pipeline.Context.of(p)
    f = pipeline.facts(p.high, p.low)
    for o in (pipeline.gf1_obs(ctx, p.high, p.low, f), pipeline.gf4_obs(ctx, p.high, p.low, f)):
        bh = robustness.d_bh(o, ctx.n_weeks)
        assert bh["base"] == int(p.member[ctx.week_last_idx].sum())
        assert bh["limbs"]["state rules"] > 0
    prim, _ = pipeline.gf10_obs(ctx, p.high, p.low, f)
    bh = robustness.d_bh(prim, ctx.n_weeks, gf10=True)
    assert "state rules" not in bh["limbs"] and sum(bh["limbs"].values()) == bh["base"]
