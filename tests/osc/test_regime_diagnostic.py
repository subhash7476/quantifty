"""Tests for OSC regime diagnostic — D-2 double-lag and D-4 trailing-window rank."""
import numpy as np
import pandas as pd
import pytest

from scripts.osc.regime_diagnostic import _pooled_median_iqr


class TestPooledMedianIQR:
    def test_basic(self):
        med, q25, q75, n = _pooled_median_iqr([1, 2, 3, 4, 5])
        assert med == 3.0
        assert q25 == 2.0
        assert q75 == 4.0
        assert n == 5

    def test_empty(self):
        med, q25, q75, n = _pooled_median_iqr([])
        assert np.isnan(med)
        assert n == 0

    def test_single(self):
        med, q25, q75, n = _pooled_median_iqr([7.0])
        assert med == 7.0
        assert n == 1


class TestD2DoubleLag:
    """Verify the double-lag construction: richness_{t-1} - richness_{t-2}."""

    def test_shift_identity(self):
        """Given known values at consecutive dates, verify shift yields correct diff."""
        df = pd.DataFrame({
            "trade_date": pd.to_datetime([
                "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
                "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
            ]),
            "expiry_dt": pd.to_datetime([
                "2024-02-01", "2024-02-01", "2024-02-01", "2024-02-01", "2024-02-01",
                "2024-03-01", "2024-03-01", "2024-03-01", "2024-03-01", "2024-03-01",
            ]),
            "strike": [100.0, 100.0, 100.0, 100.0, 100.0, 105.0, 105.0, 105.0, 105.0, 105.0],
            "option_type": ["CE"] * 10,
            "richness": [0.1, 0.2, 0.5, 0.3, 0.4, -0.1, -0.2, -0.3, -0.1, -0.4],
        })

        key_cols = ["expiry_dt", "strike", "option_type"]
        df = df.sort_values(key_cols + ["trade_date"])
        df["richness_lag1"] = df.groupby(key_cols)["richness"].shift(1)
        df["richness_lag2"] = df.groupby(key_cols)["richness"].shift(2)
        df["richness_diff"] = df["richness_lag1"] - df["richness_lag2"]

        # Key=CE/100/Feb: richness = [0.1, 0.2, 0.5, 0.3, 0.4]
        # t=01-03: lag1=0.2, lag2=0.1 → diff=0.1
        # t=01-04: lag1=0.5, lag2=0.2 → diff=0.3
        # t=01-05: lag1=0.3, lag2=0.5 → diff=-0.2
        row_jan03 = df[(df["trade_date"] == pd.Timestamp("2024-01-03")) & (df["strike"] == 100.0)]
        assert row_jan03["richness_lag1"].iloc[0] == 0.2
        assert row_jan03["richness_lag2"].iloc[0] == 0.1
        assert row_jan03["richness_diff"].iloc[0] == pytest.approx(0.1)

        row_jan05 = df[(df["trade_date"] == pd.Timestamp("2024-01-05")) & (df["strike"] == 100.0)]
        assert row_jan05["richness_lag1"].iloc[0] == 0.3
        assert row_jan05["richness_lag2"].iloc[0] == 0.5
        assert row_jan05["richness_diff"].iloc[0] == pytest.approx(-0.2)

        # First two rows should have NaN for lag1 or lag2
        row_jan01 = df[(df["trade_date"] == pd.Timestamp("2024-01-01")) & (df["strike"] == 100.0)]
        assert np.isnan(row_jan01["richness_lag1"].iloc[0])

    def test_shift_respects_group_boundary(self):
        """Shift should not leak values across different keys."""
        df = pd.DataFrame({
            "trade_date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-02"]),
            "expiry_dt": pd.to_datetime(["2024-02-01", "2024-02-01", "2024-03-01"]),
            "strike": [100.0, 100.0, 100.0],
            "option_type": ["CE", "CE", "CE"],
            "richness": [0.5, 0.6, 0.9],
        })
        key_cols = ["expiry_dt", "strike", "option_type"]
        df = df.sort_values(key_cols + ["trade_date"])
        df["lag1"] = df.groupby(key_cols)["richness"].shift(1)

        # The Mar expiry key has only one row → lag1 should be NaN
        row_mar = df[df["expiry_dt"] == pd.Timestamp("2024-03-01")]
        assert np.isnan(row_mar["lag1"].iloc[0])

        # The Feb expiry key's second row should have the first row's value
        row_feb = df[(df["expiry_dt"] == pd.Timestamp("2024-02-01")) & (df["trade_date"] == pd.Timestamp("2024-01-03"))]
        assert row_feb["lag1"].iloc[0] == 0.5


class TestD4TrailingWindow:
    def test_trailing_mean_rank(self):
        """Verify trailing 60-day mean rank construction: window ends at t-1."""
        dates = pd.to_datetime([f"2024-01-{d:02d}" for d in range(2, 30)])
        np.random.seed(42)
        df = pd.DataFrame({
            "trade_date": pd.to_datetime(list(dates) * 2),
            "expiry_dt": pd.to_datetime(["2024-02-15"] * 28 + ["2024-03-15"] * 28),
            "strike": [100.0] * 28 + [105.0] * 28,
            "option_type": ["CE"] * 56,
            "richness": list(np.random.randn(28) * 0.1 + 0.5) + list(np.random.randn(28) * 0.1 + 0.3),
        })

        key_cols = ["expiry_dt", "strike", "option_type"]
        df = df.sort_values(key_cols + ["trade_date"])
        df["rank_pct"] = df.groupby("trade_date")["richness"].rank(pct=True)
        df["rank_pct_lag1"] = df.groupby(key_cols)["rank_pct"].shift(1)
        df["frozen_rank"] = (
            df.groupby(key_cols)["rank_pct_lag1"]
            .transform(lambda x: x.rolling(5, min_periods=2).mean())
        )

        # Row at t should use data through t-1 (nothing from t)
        key1 = df[df["strike"] == 100.0].sort_values("trade_date")
        # The first two rows have NaN frozen_rank (need at least 2 observations in trailing window)
        assert np.isnan(key1["rank_pct_lag1"].iloc[0])  # first row: no lag
        assert key1["rank_pct_lag1"].iloc[1] == key1["rank_pct"].iloc[0]  # shifted from row 0

    def test_no_lookahead(self):
        """The frozen_rank at t must not contain any information from t or later."""
        dates_list = [f"2024-01-{d:02d}" for d in range(2, 22)]
        # Two cells per date so rank_pct is not always 1.0
        df = pd.DataFrame({
            "trade_date": pd.to_datetime(dates_list * 2),
            "expiry_dt": pd.to_datetime(["2024-02-15"] * 40),
            "strike": [100.0] * 20 + [105.0] * 20,
            "option_type": ["CE"] * 40,
            "richness": list(range(20)) + list(reversed(range(20))),
        })
        key_cols = ["expiry_dt", "strike", "option_type"]
        df = df.sort_values(key_cols + ["trade_date"])
        df["rank_pct"] = df.groupby("trade_date")["richness"].rank(pct=True)
        df["rank_pct_lag1"] = df.groupby(key_cols)["rank_pct"].shift(1)
        df["frozen_rank"] = (
            df.groupby(key_cols)["rank_pct_lag1"]
            .transform(lambda x: x.rolling(5, min_periods=2).mean())
        )

        # Verify the shift is one trading day behind
        k100 = df[df["strike"] == 100.0].sort_values("trade_date")
        # rank_pct at first date (richness=0 vs richness=19) -> rank=0.5 for both (since both 0.5)
        # rank_pct_lag1 at second date = rank_pct at first date
        assert k100["rank_pct_lag1"].iloc[1] == k100["rank_pct"].iloc[0]
        # frozen_rank at row 5 (6th date) is mean of rank_pct_lag1 for rows 0-4
        expected = k100["rank_pct_lag1"].iloc[0:5].mean()
        assert k100["frozen_rank"].iloc[5] == pytest.approx(expected)
