import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.analytics.gex_history import RATE  # noqa: E402
from core.execution.options.nifty_shield_pricing import bs_price  # noqa: E402
from scripts.gex_regime.fly_dev import Market, lot_for_expiry, metrics, simulate  # noqa: E402


def test_lot_for_expiry():
    assert lot_for_expiry(date(2021, 7, 22)) == 75
    assert lot_for_expiry(date(2021, 7, 29)) == 50
    with pytest.raises(ValueError):
        lot_for_expiry(date(2024, 1, 4))


def _market():
    sessions = list(pd.bdate_range("2020-01-06", "2020-01-24").date)
    expiries = [date(2020, 1, 16), date(2020, 1, 23), date(2020, 1, 30)]
    rows = []
    for t in sessions:
        for e in expiries:
            if e <= t:
                continue
            ty = (e - t).days / 365
            spot = 12000 * math.exp(-RATE * ty)
            for k in range(11000, 13001, 50):
                for o in ("CE", "PE"):
                    p = bs_price(spot, k, ty, RATE, 0.15, o)
                    rows.append({"trade_date": t, "expiry_dt": e, "strike": float(k), "option_type": o,
                                 "close": p, "settle": p, "contracts": 10, "open_int": 100})
    opts = pd.DataFrame(rows)
    n = pd.Series(0.0, index=sessions)
    zones = pd.DataFrame({"p67": 0.0, "p50": 0.0}, index=sessions)
    return Market.build(sessions, n, zones, opts, {t: 12000.0 for t in sessions})


def test_one_position_at_a_time_and_no_same_close_reentry():
    daily, spread_unit, trades, skips = simulate(_market(), "fly", gated=False)
    assert len(trades) >= 2
    for a, b in zip(trades, trades[1:]):
        assert b["entry"] > a["exit"]
    assert {t["reason"] for t in trades} <= {"stop", "profit", "regime", "time", "window_end"}


def test_daily_series_sums_to_trade_returns():
    daily, spread_unit, trades, _ = simulate(_market(), "fly", gated=False)
    total = sum((t["gross"] - t["fees"] - 0.5 * 0.02 * t["prem"]) / t["risk"] for t in trades)
    assert (daily - 0.02 * spread_unit).sum() == pytest.approx(total)
    m = metrics(daily, spread_unit, trades, 0.02)
    assert m["trades"] == len(trades)
