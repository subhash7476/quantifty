"""GF-1 / GF-4T/R8 scores, placebo families, O-R10, exclusions, statistics and the panel loader, on
synthetic inputs only. No store is read."""

from datetime import date, timedelta

import duckdb
import numpy as np
import pytest
from scipy.stats import spearmanr

from scripts.ptms.gann import formation, scores, stats
from scripts.ptms.gann.constants import GF1_P4, GF4_WINDOWS
from scripts.ptms.gann.k3 import run_k3
from scripts.ptms.gann.panel import adjust, load_panel


# ---- scores ----

def test_placebo_families_have_the_ruled_sizes_and_exclude_real_points():
    gf1 = scores.gf1_placebo_residue_sets()
    assert len(gf1) == 132
    assert all(not (s & scores.residues(GF1_P4)) for _, s in gf1)
    gf4 = scores.gf4_placebo_window_sets()
    assert len(gf4) == 162
    forbidden = {10, 16, 20, 26, 36, 43, 55, 59, 64, 65, 69, 79, 108, 119, 124, 134, 144}
    assert {d for d, _ in gf4} == set(range(1, 180)) - forbidden


def test_gf1_hits_points_in_the_next_seven_days_and_repeats_every_144():
    fn = scores.GF1_PRIMARY
    hit = lambda delta: bool(fn([np.array([delta])])[0])
    assert hit(29) and not hit(28)          # 29+7 = 36
    assert hit(35) and not hit(36)          # 36 is day 0 of the look-ahead only when delta = 35
    assert hit(137) and hit(137 + 144)      # 144 and 288
    assert not hit(0)                       # delta 0: days 1..7, no point


def test_gf4_windows_inclusive_and_one_shot():
    fn = scores.GF4_PRIMARY
    hit = lambda delta: bool(fn([np.array([delta])])[0])
    assert hit(0)                           # 1..7 reaches 7
    assert not hit(185)                     # 186..192 beyond the last window
    assert hit(184) and hit(174)
    assert not hit(185 + 144)               # no periodicity
    assert hit(30) and not hit(31) and not hit(34) and hit(35)   # gap between 28-31 and 42-49


def test_v4ct_exact_points():
    fn = scores.exact_points_score_fn((90, 180, 270, 360))
    hit = lambda delta: bool(fn([np.array([delta])])[0])
    assert hit(83) and not hit(82) and not hit(90) and hit(359) and not hit(360)


# ---- statistics ----

def test_tc_equals_mean_spearman_and_drops_floor_and_undefined_dates():
    rng = np.random.default_rng(3)
    week, s, y, ics = [], [], [], []
    for w in range(6):
        n = 25
        sw, yw = rng.integers(0, 2, n), rng.integers(0, 2, n)
        week += [w] * n; s += sw.tolist(); y += yw.tolist()
        ics.append(spearmanr(sw, yw).statistic)
    week += [6] * 25; s += [0] * 25; y += rng.integers(0, 2, 25).tolist()   # all-zero score: undefined
    week += [7] * 10; s += [1, 0] * 5; y += [1, 0] * 5                       # below the floor
    res = stats.t_c(week, s, y, 8)
    assert res.value == pytest.approx(np.mean(ics))
    assert (res.n_dates, res.n_dropped_undefined, res.n_dropped_floor) == (6, 1, 1)


def test_rank_p_and_nan_guard():
    assert stats.rank_p(0.5, [0.1, 0.5, 0.9]) == pytest.approx(3 / 4)
    with pytest.raises(ValueError):
        stats.rank_p(float("nan"), [0.1])


# ---- observations ----

def zigzag():
    """One column: up 4, down 4, up 4, down 4 ... on consecutive calendar days."""
    seq, hi, lo = [], 100.0, 98.0
    for leg in range(12):
        for _ in range(4):
            if leg % 2 == 0:
                hi, lo = hi + 1, lo + 1
            else:
                hi, lo = hi - 1.5, lo - 1.5
            seq.append((hi, lo))
    return np.array([[h] for h, _ in seq]), np.array([[l] for _, l in seq])


def test_formation_outcome_reference_and_open_m():
    h, lo = zigzag()
    T = h.shape[0]
    ords = [date(2020, 1, 1).toordinal() + i for i in range(T)]
    res = run_k3(h, lo)
    sw = formation.last_swings(res, T, 1)
    anchor = formation.last_anchor(sw)
    member = np.ones((T, 1), dtype=bool)
    weeks = np.arange(0, T, 5)
    obs = formation.build(ords, weeks, h, lo, member, (np.zeros(0, dtype=np.int64),), res, sw, [anchor],
                          scores.GF4_PRIMARY)
    assert obs.n_excluded_open_m == sum(1 for t in weeks if t + 5 > T - 1 and res.state[t, 0] != 0
                                        and anchor[t, 0] >= 0)
    for wi, j, yv in zip(obs.week, obs.col, obs.y):
        t = weeks[wi]
        if res.state[t, 0] == 1:
            ref = sw[-1][0][t, 0]
            assert yv == int((lo[t + 1:t + 6, 0] < ref).any())
        else:
            ref = sw[1][0][t, 0]
            assert yv == int((h[t + 1:t + 6, 0] > ref).any())


def test_g7_exclusion_uses_span_from_earliest_anchor_or_reference_to_o5():
    h, lo = zigzag()
    T = h.shape[0]
    ords = [date(2020, 1, 1).toordinal() + i for i in range(T)]
    res = run_k3(h, lo)
    sw = formation.last_swings(res, T, 1)
    anchor = formation.last_anchor(sw)
    member = np.ones((T, 1), dtype=bool)
    weeks = np.array([30])
    base = formation.build(ords, weeks, h, lo, member, (np.zeros(0, dtype=np.int64),), res, sw, [anchor],
                           scores.GF4_PRIMARY)
    assert base.week.size == 1
    ref_ext = sw[-1][1][30, 0] if res.state[30, 0] == 1 else sw[1][1][30, 0]
    start = min(anchor[30, 0], ref_ext)
    for ex_idx, excluded in ((start, True), (35, True), (36, False), (start - 1, False)):
        ex = (np.array([ords[ex_idx]], dtype=np.int64),)
        obs = formation.build(ords, weeks, h, lo, member, ex, res, sw, [anchor], scores.GF4_PRIMARY)
        assert (obs.n_excluded_g7 == 1) == excluded


def test_first_k3_line_without_reference_is_eligible_with_y0():
    # rise from bar 0, UP at bar 3 (initialization, no swing low yet), then a deep fall
    h = np.array([[10.0], [11.0], [12.0], [13.0], [13.5], [9.0], [8.0], [7.0], [6.0], [5.0], [4.0], [3.0]])
    lo = h - 1
    T = h.shape[0]
    ords = [date(2020, 1, 1).toordinal() + i for i in range(T)]
    res = run_k3(h, lo)
    sw = formation.last_swings(res, T, 1)
    hi_t, lo_t = formation.running_extremes(h, lo)
    obs = formation.build(ords, np.array([4]), h, lo, np.ones((T, 1), dtype=bool),
                          (np.zeros(0, dtype=np.int64),), res, sw, [hi_t, lo_t], scores.GF1_PRIMARY)
    assert res.state[4, 0] == 1 and sw[-1][1][4, 0] == -1
    assert obs.week.tolist() == [0] and obs.y.tolist() == [0]


def test_running_extremes_first_occurrence():
    h = np.array([[5.0], [7.0], [7.0], [6.0]])
    lo = np.array([[4.0], [3.0], [3.0], [2.0]])
    hi_t, lo_t = formation.running_extremes(h, lo)
    assert hi_t[:, 0].tolist() == [0, 1, 1, 1]
    assert lo_t[:, 0].tolist() == [0, 1, 1, 3]


# ---- panel loader on a synthetic store ----

def test_adjust_multiplies_sessions_before_ex_date():
    sessions = [date(2020, 1, d) for d in (1, 2, 3)]
    out = adjust(np.array([[10.0], [10.0], [5.0]]), sessions, {0: [(date(2020, 1, 3), 0.5)]})
    assert out[:, 0].tolist() == [5.0, 5.0, 5.0]


def test_load_panel_on_synthetic_store(tmp_path):
    eq, n1 = tmp_path / "eq.duckdb", tmp_path / "n1.duckdb"
    days = [date(2011, 3, 25) + timedelta(days=i) for i in range(10)]
    c = duckdb.connect(str(eq))
    c.execute("create table trading_calendar (trade_date DATE, source VARCHAR, n_symbols INTEGER)")
    c.executemany("insert into trading_calendar values (?, 'x', 1)", [[d] for d in days + [date(2023, 1, 2)]])
    c.execute("create table symbol_entity_intervals (symbol VARCHAR, valid_from DATE, valid_to DATE, entity VARCHAR)")
    c.execute("insert into symbol_entity_intervals values ('OLD', '2000-01-01', '2011-03-30', 'E1'), "
              "('NEW', '2011-03-30', '2099-01-01', 'E1'), ('XX', '2000-01-01', '2099-01-01', 'E2')")
    c.execute("create table equity_bhavcopy (trade_date DATE, symbol VARCHAR, series VARCHAR, high DOUBLE, "
              "low DOUBLE, close DOUBLE)")
    for d in days:
        sym = "OLD" if d < date(2011, 3, 30) else "NEW"
        c.execute("insert into equity_bhavcopy values (?, ?, 'EQ', 20, 18, 19)", [d, sym])
        c.execute("insert into equity_bhavcopy values (?, 'XX', 'EQ', 5, 4, 4.5)", [d])
    c.execute("insert into equity_bhavcopy values ('2023-01-02', 'NEW', 'EQ', 999, 999, 999)")
    c.execute("create table adjustment_factors (symbol VARCHAR, ex_date DATE, factor DOUBLE, action_type VARCHAR, "
              "source VARCHAR)")
    c.execute("insert into adjustment_factors values ('NEW', '2011-04-01', 0.5, 'SPLIT', 's'), "
              "('NEW', '2011-04-02', 0.9, 'SPECIAL_DIVIDEND', 's')")
    c.close()
    c = duckdb.connect(str(n1))
    c.execute("create table n100_membership (symbol VARCHAR, company VARCHAR, valid_from DATE, valid_to DATE)")
    c.execute("insert into n100_membership values ('OLD', 'c', '2011-03-25', '2011-03-30'), "
              "('NEW', 'c', '2011-03-30', NULL)")
    c.close()
    g7 = tmp_path / "g7.csv"
    g7.write_text("entity,symbol,ex_date,class,series,purpose,source_file,in_membership,g7_event\n"
                  "E1,NEW,2011-04-02,SPECIAL_DIVIDEND,EQ,p,f,True,True\n"
                  "E1,NEW,2011-04-03,BUYBACK,EQ,p,f,True,False\n", encoding="utf-8")
    p = load_panel(eq, n1, g7)
    assert p.entities == ("E1",)                       # XX never a member
    assert len(p.cal) == 10                            # nothing after Z
    before = p.cal.index[date(2011, 3, 31)]
    after = p.cal.index[date(2011, 4, 1)]
    assert p.high[before, 0] == 10.0 and p.high[after, 0] == 20.0   # split only; special dividend ignored
    assert p.close_raw[before, 0] == 19.0
    assert p.member[:, 0].all()                        # rename OLD -> NEW keeps one entity
    assert p.g7_ord[0].tolist() == [date(2011, 4, 2).toordinal()]
