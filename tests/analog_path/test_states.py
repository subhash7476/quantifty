from datetime import date

import numpy as np

from scripts.analog_path import config
from scripts.analog_path.data_layer import load_session


def test_path_state_is_14_points_first_zero():
    for d in [date(2012, 6, 4), date(2024, 6, 3)]:
        s = load_session(d)
        assert len(s.path_state) == 14
        assert s.path_state[0] == 0.0
        assert np.all(np.isfinite(s.path_state))


def test_path_state_is_normalized_cumulative():
    s = load_session(date(2024, 6, 3))
    expected = s.grid_prices / s.open - 1.0
    assert np.allclose(s.path_state, expected, rtol=1e-12)


def test_interval_state_is_13_consistent_with_path():
    for d in [date(2012, 6, 4), date(2024, 6, 3)]:
        s = load_session(d)
        assert len(s.interval_state) == 13
        implied = (1.0 + s.path_state[1:]) / (1.0 + s.path_state[:-1]) - 1.0
        assert np.allclose(s.interval_state, implied, rtol=1e-12, atol=1e-12)


def test_open_to_1230_return():
    s = load_session(date(2012, 6, 4))
    assert np.isclose(s.open_to_1230, s.p_1230 / s.open - 1.0, rtol=1e-12)


def test_all_five_horizons_are_finite():
    s = load_session(date(2024, 6, 3))
    assert set(s.outcomes) == set(config.HORIZONS)
    for k in config.HORIZONS:
        assert np.isfinite(s.outcomes[k]), k


def test_mfe_mae_bounds():
    for d in [date(2012, 6, 4), date(2024, 6, 3), date(2026, 8, 4)]:
        s = load_session(d)
        assert s.mfe >= 0.0
        assert s.mae <= 0.0
        assert s.mfe >= s.outcomes["close"]   # close return cannot exceed MFE
        assert s.mae <= s.outcomes["close"]


def test_grid_matches_frozen_15min_stamps():
    s = load_session(date(2024, 6, 3))
    assert len(s.grid_prices) == len(config.GRID_TIMES) == 14
    # 15-minute spacing of the frozen grid
    times = config.GRID_TIMES
    for a, b in zip(times, times[1:]):
        diff = (b.hour * 60 + b.minute) - (a.hour * 60 + a.minute)
        assert diff == 15
