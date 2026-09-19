"""K3 / S9 tests on hand-built and random synthetic bars. No store is read."""

from datetime import date

import numpy as np
import pytest

from scripts.ptms.gann.calendar import Calendar, o5_after
from scripts.ptms.gann.k3 import DOWN, NONE, UP, run_k3, swings_of


def col(bars):
    h = np.array([[b[0]] for b in bars], dtype=float)
    lo = np.array([[b[1]] for b in bars], dtype=float)
    return h, lo


def rising(n, start=100.0):
    return [(start + i + 1, start + i - 1) for i in range(n)]


def test_initialization_needs_three_hh_hl_sessions():
    h, lo = col(rising(4))            # bar 0 is the base; bars 1..3 are HH+HL
    res = run_k3(h, lo)
    assert res.state[:, 0].tolist() == [NONE, NONE, NONE, UP]
    assert swings_of(res, 0) == []    # initialization confirms no swing


def test_down_switch_confirms_swing_high_at_max_high_first_occurrence():
    bars = rising(4) + [(104, 102), (104, 101.5), (103, 101), (102.5, 100.5), (102, 100)]
    # UP from bar 3 (high 104); bar 4 equal high 104 is not a new max (first occurrence kept);
    # bars 5..7 are three LL sessions -> DOWN switch at bar 7
    res = run_k3(*col(bars))
    assert res.state[7, 0] == DOWN and res.state[6, 0] == UP
    assert swings_of(res, 0) == [(7, 1, 104.0, 3)]


def test_equal_low_breaks_down_run():
    bars = rising(4) + [(103, 101), (102.9, 101), (102.8, 100), (102.7, 99), (102.6, 98)]
    # bar 5 equal low -> not LL -> run restarts; LL at 6, 7, 8 -> switch at 8
    res = run_k3(*col(bars))
    assert res.state[7, 0] == UP and res.state[8, 0] == DOWN


def test_inside_day_breaks_down_run_and_outside_day_extends_it():
    base = rising(4)                              # last bar (104, 102)
    inside = base + [(103.5, 101), (103, 102.5), (102, 100), (101, 99), (100, 98)]
    res = run_k3(*col(inside))                    # LL at 4, inside at 5 (not LL), LL at 6, 7, 8
    assert res.state[7, 0] == UP and res.state[8, 0] == DOWN
    outside = base + [(103.5, 101), (105, 100), (104.5, 99)]   # bar 5 outside day: HH and LL
    res = run_k3(*col(outside))
    assert res.state[6, 0] == DOWN                # LL at 4, 5 (outside), 6 -> switch at 6
    # IR-2: bar 5 is still UP at its close, so its high 105 is the swing high
    assert swings_of(res, 0) == [(6, 1, 105.0, 5)]


def test_missing_bar_is_skipped_not_a_break():
    bars = rising(3) + [(np.nan, np.nan)] + [(103.5, 101.5)]
    h, lo = col(bars)
    res = run_k3(h, lo)
    # comparisons 1, 2 then (skip) 4 vs 2: HH+HL -> third qualifying session -> UP at bar 4
    assert res.state[3, 0] == NONE and res.state[4, 0] == UP


def test_s9_bull_after_rising_highs_and_lows():
    seq = [(10, 8)]
    def up(n):
        for _ in range(n):
            hi, lo = seq[-1]
            seq.append((hi + 1, lo + 1))
    def dn(n):
        for _ in range(n):
            hi, lo = seq[-1]
            seq.append((hi - 0.5, lo - 1))
    up(3); dn(3); up(4); dn(3); up(5); dn(3); up(6)
    res = run_k3(*col(seq))
    kinds = [s[1] for s in swings_of(res, 0)]
    assert kinds == [1, -1, 1, -1, 1, -1]
    assert res.s9[-1, 0] == 1


def scalar_k3(h, lo):
    """Straight transcription of memo §5 for one column, used to cross-check the vector code."""
    state, up_run, dn_run, ph, pl, ext, ext_t = NONE, 0, 0, None, None, None, None
    states, swings = [], []
    for t, (a, b) in enumerate(zip(h, lo)):
        if np.isnan(a):
            states.append(state)
            continue
        if ph is not None:
            up_run = up_run + 1 if (a > ph and b > pl) else 0
            dn_run = dn_run + 1 if b < pl else 0
        if state == NONE and up_run >= 3:
            state, ext, ext_t = UP, a, t
        elif state == NONE and dn_run >= 3:
            state, ext, ext_t = DOWN, b, t
        elif state == UP and dn_run >= 3:
            swings.append((t, 1, ext, ext_t)); state, ext, ext_t = DOWN, b, t
        elif state == DOWN and up_run >= 3:
            swings.append((t, -1, ext, ext_t)); state, ext, ext_t = UP, a, t
        elif state == UP and a > ext:
            ext, ext_t = a, t
        elif state == DOWN and b < ext:
            ext, ext_t = b, t
        ph, pl = a, b
        states.append(state)
    return states, swings


def test_vector_matches_scalar_reference_on_random_panels():
    rng = np.random.default_rng(7)
    T, N = 400, 25
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, (T, N)), axis=0))
    h = np.round(c * (1 + np.abs(rng.normal(0, 0.01, (T, N)))), 1)
    lo = np.round(c * (1 - np.abs(rng.normal(0, 0.01, (T, N)))), 1)   # rounding forces ties
    gaps = rng.random((T, N)) < 0.03
    h[gaps] = np.nan
    lo[gaps] = np.nan
    res = run_k3(h, lo)
    for j in range(N):
        states, swings = scalar_k3(h[:, j], lo[:, j])
        assert res.state[:, j].tolist() == states
        assert swings_of(res, j) == swings


def test_iso_week_last_session_includes_sunday_muhurat():
    days = [date(2016, 10, 24), date(2016, 10, 25), date(2016, 10, 28), date(2016, 10, 30),
            date(2016, 10, 31)]
    cal = Calendar(days)
    weeks = cal.formation_weeks()
    assert [cal.sessions[w.last_idx] for w in weeks] == [date(2016, 10, 30), date(2016, 10, 31)]


def test_open_m_excludes_windows_past_z():
    days = [date(2022, 12, d) for d in (23, 26, 27, 28, 29, 30)] + [date(2023, 1, 2)]
    cal = Calendar(days)
    assert o5_after(cal, 0, date(2022, 12, 30)) == date(2022, 12, 30)
    assert o5_after(cal, 1, date(2022, 12, 30)) is None


def test_calendar_rejects_unsorted():
    with pytest.raises(ValueError):
        Calendar([date(2020, 1, 2), date(2020, 1, 1)])
