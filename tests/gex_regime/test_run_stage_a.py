import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.gex_regime.run_stage_a import build_outcomes, check_window  # noqa: E402


def test_check_window_refuses_sealed_dates():
    with pytest.raises(ValueError):
        check_window(date(2022, 1, 1), date(2023, 1, 1))
    check_window(date(2020, 1, 1), date(2022, 12, 31))


def _daily():
    dates = pd.bdate_range("2019-11-01", "2020-01-03")
    return pd.DataFrame({"date": dates.date, "high": 101.0, "low": 99.0,
                         "close": 100.0, "vix": 16.0})


def test_outcome_uses_next_day_and_drops_t_whose_next_day_leaves_window():
    out = build_outcomes(_daily(), {date(2019, 12, 26)}, date(2019, 12, 1), date(2019, 12, 31))
    assert out["date"].max() == date(2019, 12, 30)       # its t+1 (12-31) is in window
    assert date(2019, 12, 31) not in set(out["date"])     # t+1 = 2020-01-01 is outside
    rv = math.log(101 / 99) ** 2 / (4 * math.log(2))
    ivd = (16 / 100) ** 2 / 252
    row = out.set_index("date").loc[date(2019, 12, 24)]
    assert row["y"] == pytest.approx(math.log(rv / ivd))
    assert row["exp_next"] == 0
    assert out.set_index("date").loc[date(2019, 12, 25), "exp_next"] == 1
