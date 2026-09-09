from datetime import date, time

import numpy as np

from scripts.analog_path import config
from scripts.analog_path.data_layer import load_session, read_day

# --- era boundaries -------------------------------------------------------

def test_era_boundaries():
    assert config.era_of(date(2022, 6, 1)) == "vendor"
    assert config.era_of(date(2023, 1, 31)) == "vendor"
    assert config.era_of(date(2024, 6, 1)) == "native"
    assert config.era_of(date(2026, 7, 31)) == "native"
    assert config.era_of(date(2026, 8, 3)) == "cas"


# --- 09:15 / 12:30 boundaries, both eras ----------------------------------

def test_vendor_open_is_first_bar_open():
    s = load_session(date(2012, 6, 4))
    assert s.valid
    assert s.open == 4791.25
    assert s.bars[0][0].time() == time(9, 16)


def test_vendor_1230_is_close_of_1230_bar():
    s = load_session(date(2012, 6, 4))
    assert s.p_1230 == 4794.35
    bar = [b for b in s.bars if b[0].time() == time(12, 30)][0]
    assert bar[4] == s.p_1230


def test_vendor_close_is_close_of_1530_bar():
    s = load_session(date(2012, 6, 4))
    bar = [b for b in s.bars if b[0].time() == time(15, 30)][0]
    assert s.outcomes["close"] == bar[4] / s.p_1230 - 1.0
    assert bar[4] == 4855.2


def test_native_open_is_first_bar_open():
    s = load_session(date(2024, 6, 3))
    assert s.valid
    assert s.open == 23337.9
    assert s.bars[0][0].time() == time(9, 15)


def test_native_1230_is_close_of_1229_bar():
    s = load_session(date(2024, 6, 3))
    assert s.p_1230 == 23226.3
    bar = [b for b in s.bars if b[0].time() == time(12, 29)][0]
    assert bar[4] == s.p_1230
    bar1230 = [b for b in s.bars if b[0].time() == time(12, 30)][0]
    # the 12:30-labelled bar opens at ~12:30:00 (first tick of the next
    # minute; not exactly the 12:29 close — tick-boundary artifact)
    assert np.isclose(bar1230[1], s.p_1230, rtol=1e-4, atol=1.0)


def test_native_1300_is_close_of_1259_bar():
    s = load_session(date(2024, 6, 3))
    bar = [b for b in s.bars if b[0].time() == time(12, 59)][0]
    assert s.outcomes["h13"] == bar[4] / s.p_1230 - 1.0
    assert bar[4] == 23227.95


def test_native_close_is_close_of_1529_bar():
    s = load_session(date(2024, 6, 3))
    bar = [b for b in s.bars if b[0].time() == time(15, 29)][0]
    assert bar[4] == 23305.95
    assert s.outcomes["close"] == bar[4] / s.p_1230 - 1.0


# --- close rule robustness -------------------------------------------------

def test_flat_extension_tail_does_not_corrupt_close():
    # 2025-04-25 carries 15:30-15:59 flat prints at a different frozen value;
    # the frozen close must be the 15:29 close, not the tail value.
    s = load_session(date(2025, 4, 25))
    assert s.valid
    bar = [b for b in s.bars if b[0].time() == time(15, 29)][0]
    tail = [b for b in s.bars if b[0].time() == time(15, 59)][0]
    assert bar[4] == 23991.65
    assert tail[4] == 24039.35
    assert s.outcomes["close"] == bar[4] / s.p_1230 - 1.0


def test_cas_close_is_1529_bar():
    s = load_session(date(2026, 8, 4))
    assert s.valid
    bar = [b for b in s.bars if b[0].time() == time(15, 29)][0]
    assert bar[4] == 24614.9
    assert s.outcomes["close"] == bar[4] / s.p_1230 - 1.0


# --- known defect days are excluded ----------------------------------------

def test_defect_days_invalid():
    for d in [date(2021, 2, 24),   # NSE telecom outage, trading halted
              date(2024, 3, 2),    # Saturday DR session ending 12:29
              date(2024, 5, 18),   # Saturday DR session ending 12:29
              date(2026, 2, 25),   # multi-day corrupt file
              date(2026, 3, 2),    # multi-day corrupt file
              date(2013, 10, 14),  # power-outage session
              date(2018, 7, 9),    # first bar 09:17 (nonstandard)
              date(2017, 7, 10),   # NSE outage
              date(2023, 11, 12),  # Muhurat evening session
              date(2025, 10, 21),  # 60-bar session 13:45-14:44
              ]:
        s = load_session(d)
        assert s is not None and not s.valid, d
        assert s.defects, d


def test_normal_days_valid():
    for d in [date(2012, 6, 4), date(2016, 6, 1), date(2022, 6, 1),
              date(2024, 6, 3), date(2026, 8, 4)]:
        s = load_session(d)
        assert s is not None and s.valid, d


def test_missing_file_returns_none():
    assert load_session(date(2018, 5, 15)) is None  # permanent May 2018 hole


# --- no cross-day contamination -------------------------------------------

def test_bars_all_belong_to_session_date():
    for d in [date(2012, 6, 4), date(2024, 6, 3), date(2026, 8, 4)]:
        bars = read_day(d)
        assert bars
        assert all(ts.date() == d for ts, *_ in bars)
