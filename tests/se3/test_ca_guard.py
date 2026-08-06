"""Tests for the SE-3 CA guard — corporate-action ex-dates must null the
front-month return; without a register entry the return survives (the guard is
doing the work, not the fixture); a genuine crash with no register entry is
preserved."""
import numpy as np
import pandas as pd
import pytest

from scripts.se3.certify_substrate import _front_month_rv, _load_ca_register


def _mk_series(prices, dates, expiry="2024-03-25"):
    rows = []
    for d, p in zip(dates, prices):
        rows.append({"trade_date": pd.Timestamp(d), "expiry_dt": pd.Timestamp(expiry), "settle": p})
    return pd.DataFrame(rows)


def _dates(n, start="2024-01-01"):
    return pd.date_range(start, periods=n)


class TestCAGuard:
    def test_bonus_ex_date_nan_finite_elsewhere(self):
        # 30 flat days then a 1:1 bonus (settle halves) mid-series, then flat.
        prices = [100.0] * 15 + [50.0] * 15
        dates = _dates(30)
        g = _mk_series(prices, dates)
        ex = pd.Timestamp("2024-01-16")  # the bonus ex-date (row 15)
        fdf = _front_month_rv(g, ca_ex_dates={ex})
        # The return ON the ex-date is NaN; returns after row 0 are finite.
        row = fdf[fdf["trade_date"] == ex]
        assert len(row) == 1
        assert np.isnan(row["ret"].iloc[0])
        # Row 0 is always NaN (no previous price); the ex-date row is the
        # intended NaN; every other row must be finite.
        finite_mask = (fdf.index > 0) & (fdf["trade_date"] != ex)
        assert fdf.loc[finite_mask, "ret"].notna().all()

    def test_without_register_entry_fabricated_return_survives(self):
        # Same series, but NO register entry -> the guard must NOT null it,
        # proving the drop is doing the work (not a coincidence of the fixture).
        prices = [100.0] * 15 + [50.0] * 15
        dates = _dates(30)
        g = _mk_series(prices, dates)
        fdf = _front_month_rv(g)  # no ca_ex_dates
        ret_on_ex = fdf[fdf["trade_date"] == pd.Timestamp("2024-01-16")]["ret"].iloc[0]
        assert abs(ret_on_ex - np.log(0.5)) < 1e-9

    def test_genuine_crash_with_no_register_preserved(self):
        # A genuine -60% single-day move, no register entry -> preserved.
        prices = [100.0] * 10 + [40.0] * 10
        dates = _dates(20)
        g = _mk_series(prices, dates)
        fdf = _front_month_rv(g)  # no register entry
        row = fdf[fdf["trade_date"] == pd.Timestamp("2024-01-11")]
        assert len(row) == 1
        assert abs(row["ret"].iloc[0] - np.log(0.4)) < 1e-9

    def test_roll_gap_still_dropped_with_ca_guard(self):
        # A roll (expiry change) AND a CA on different dates: both nulled.
        rows = []
        # days 0-9 expiry A, days 10-19 expiry B; bonus halves on day 12
        for i in range(10):
            rows.append({"trade_date": pd.Timestamp(f"2024-01-{i+1:02d}"),
                         "expiry_dt": pd.Timestamp("2024-01-25"), "settle": 100.0 + i})
        for i in range(10):
            rows.append({"trade_date": pd.Timestamp(f"2024-01-{11+i:02d}"),
                         "expiry_dt": pd.Timestamp("2024-02-25"), "settle": (100.0 + i) * 0.5})
        g = pd.DataFrame(rows)
        ex = pd.Timestamp("2024-01-12")  # bonus day
        fdf = _front_month_rv(g, ca_ex_dates={ex})
        roll_row = fdf[fdf["trade_date"] == pd.Timestamp("2024-01-11")]
        assert len(roll_row) == 1 and np.isnan(roll_row["ret"].iloc[0])  # roll gap
        bonus_row = fdf[fdf["trade_date"] == ex]
        assert len(bonus_row) == 1 and np.isnan(bonus_row["ret"].iloc[0])  # CA


class TestCARegister:
    def test_register_loads_and_is_symbol_keyed(self):
        reg = _load_ca_register()
        assert isinstance(reg, dict)
        # BAJFINANCE (entity BAJAUTOFIN) must carry its 2016-09-08 CA via alias.
        assert pd.Timestamp("2016-09-08") in {pd.Timestamp(d) for d in reg.get("BAJFINANCE", {})}
        assert pd.Timestamp("2017-09-07") in {pd.Timestamp(d) for d in reg.get("RELIANCE", {})}

    def test_register_excludes_dividends(self):
        reg = _load_ca_register()
        # RELIANCE should NOT carry a dividend-only date as a CA ex-date.
        for d in reg.get("RELIANCE", {}):
            assert str(d) in ("2017-09-07", "2024-10-28")
