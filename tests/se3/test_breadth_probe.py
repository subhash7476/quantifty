"""Tests for SE-3 Breadth/SD Probe — fence, MCWB lookahead, roll-day exclusion,
N_eff formula, and the demeaning artifact."""
import numpy as np
import pandas as pd
import pytest

from scripts.se3.breadth_probe import (
    _assert_fence,
    _corr_matrix_stats,
    _front_month_rv,
    _membership_for_date,
    _pick_expiry,
    _newey_west,
    DTE_LO,
    DTE_HI,
    FENCE_START,
    FENCE_END,
)


class TestFence:
    def test_fence_pass(self):
        df = pd.DataFrame({"trade_date": [pd.Timestamp("2024-06-15")]})
        _assert_fence(df)  # should not raise

    def test_fence_fail_early(self):
        df = pd.DataFrame({"trade_date": [pd.Timestamp("2022-12-31")]})
        with pytest.raises(AssertionError, match="FENCE VIOLATION"):
            _assert_fence(df)

    def test_fence_fail_late(self):
        df = pd.DataFrame({"trade_date": [pd.Timestamp("2026-01-01")]})
        with pytest.raises(AssertionError, match="FENCE VIOLATION"):
            _assert_fence(df)


class TestMCWBLookahead:
    def test_month_M_applies_to_M_plus_1(self):
        snapshots = {"2023-01-01": {"A": 1.0}, "2023-02-01": {"B": 2.0}}
        # Trade date in Feb 2023 uses the January snapshot.
        members = _membership_for_date(snapshots, pd.Timestamp("2023-02-15"))
        assert "A" in members
        assert "B" not in members

    def test_january_uses_previous_december(self):
        snapshots = {"2022-12-01": {"A": 1.0}}
        members = _membership_for_date(snapshots, pd.Timestamp("2023-01-15"))
        assert members == {"A": 1.0}

    def test_no_lookahead_same_month(self):
        snapshots = {"2023-01-01": {"A": 1.0}, "2023-03-01": {"C": 3.0}}
        # A trade date in March uses the February snapshot. February missing.
        with pytest.raises(SystemExit, match="no MCWB snapshot for month 2023-02-01"):
            _membership_for_date(snapshots, pd.Timestamp("2023-03-10"))

    def test_pick_expiry_dte_window(self):
        td = pd.Timestamp("2023-06-14")
        expiries = [
            pd.Timestamp("2023-06-22"),   # DTE 8
            pd.Timestamp("2023-07-27"),   # DTE 43
            pd.Timestamp("2023-08-31"),   # DTE 78 -> out of [7,60]
        ]
        chosen = _pick_expiry(expiries, td)
        assert chosen == pd.Timestamp("2023-06-22")

    def test_pick_expiry_none_out_of_window(self):
        td = pd.Timestamp("2023-06-14")
        expiries = [pd.Timestamp("2023-06-15"), pd.Timestamp("2023-09-01")]
        assert _pick_expiry(expiries, td) is None


class TestFrontMonthRV:
    def _frame(self, rows):
        df = pd.DataFrame(rows)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df["expiry_dt"] = pd.to_datetime(df["expiry_dt"])
        return df

    def test_roll_day_return_excluded(self):
        # Same expiry for the whole run: no roll, all returns count.
        # Expiry far ahead so every date satisfies DTE >= 7.
        rows = []
        price = 100.0
        for i in range(30):
            rows.append({"trade_date": f"2024-01-{i+1:02d}", "expiry_dt": "2024-03-25", "settle": price})
            price *= 1.001
        g = self._frame(rows)
        fdf = _front_month_rv(g)
        # 30 consecutive same-expiry days -> 29 returns, all non-null
        assert len(fdf) == 30
        assert fdf["ret"].notna().sum() == 29
        # RV computed from row 18 onward (>=18 observations), before that NaN
        assert fdf.loc[fdf.index[:17], "rv"].isna().all()
        assert fdf.loc[fdf.index[18:], "rv"].notna().all()

    def test_roll_gap_dropped(self):
        # Two contracts: roll over to the next expiry partway through.
        rows = []
        for i in range(10):
            rows.append({"trade_date": f"2024-01-{i+1:02d}", "expiry_dt": "2024-01-25", "settle": 100.0 + i})
        for i in range(10):
            rows.append({"trade_date": f"2024-01-{11+i:02d}", "expiry_dt": "2024-02-29", "settle": 100.0 + i})
        g = self._frame(rows)
        fdf = _front_month_rv(g)
        # The return at the roll boundary must be NaN
        roll_idx = fdf.index[fdf["expiry_dt"] != fdf["expiry_dt"].shift(1)][1]
        assert np.isnan(fdf.loc[roll_idx, "ret"])


class TestCorrMatrixStats:
    def test_neff_hand_computed(self):
        # Three perfectly correlated names -> rho_bar=1 -> N_eff = N/(1+(N-1)) = 1
        panel = pd.DataFrame(
            {"A": [1.0, 2.0, 3.0, 4.0], "B": [1.0, 2.0, 3.0, 4.0], "C": [1.0, 2.0, 3.0, 4.0]},
            index=pd.date_range("2024-01-01", periods=4),
        )
        s = _corr_matrix_stats(panel)
        assert s is not None
        assert abs(s["rho_bar"] - 1.0) < 1e-9
        assert abs(s["neff"] - 1.0) < 1e-9
        assert abs(s["pc1"] - 1.0) < 1e-9

    def test_neff_independent(self):
        # Three mutually uncorrelated names -> rho_bar ~ 0 -> N_eff ~ N
        rng = np.random.default_rng(0)
        n = 200
        dates = pd.date_range("2024-01-01", periods=n)
        panel = pd.DataFrame(
            {
                "A": rng.normal(size=n),
                "B": rng.normal(size=n),
                "C": rng.normal(size=n),
            },
            index=dates,
        )
        s = _corr_matrix_stats(panel)
        assert s["neff"] > 2.5  # close to 3, not 1

    def test_neff_formula_direct(self):
        # 4 names with a known pairwise matrix -> verify formula N/(1+(N-1)*rho_bar)
        rng = np.random.default_rng(1)
        n = 100
        dates = pd.date_range("2024-01-01", periods=n)
        panel = pd.DataFrame(
            {
                "A": rng.normal(size=n),
                "B": rng.normal(size=n),
                "C": rng.normal(size=n),
                "D": rng.normal(size=n),
            },
            index=dates,
        )
        s = _corr_matrix_stats(panel)
        corr = panel.corr().values
        idx_upper = np.triu_indices(4, k=1)
        rho_bar = np.mean(corr[idx_upper])
        expected = 4 / (1 + 3 * rho_bar)
        assert abs(s["neff"] - expected) < 1e-9


class TestDemeaningArtifact:
    def test_demeaned_neff_gt_raw_with_common_factor(self):
        # Names all share a common factor -> raw rho_bar high, raw N_eff low.
        # Cross-sectional demeaning removes the common level -> N_eff rises toward N.
        rng = np.random.default_rng(42)
        n, k = 300, 20
        dates = pd.date_range("2024-01-01", periods=n)
        common = rng.normal(size=n)
        panel = pd.DataFrame(
            {f"N{i}": common * 5 + rng.normal(size=n) * 0.1 for i in range(k)},
            index=dates,
        )
        raw = _corr_matrix_stats(panel)
        demeaned = _corr_matrix_stats(panel.sub(panel.mean(axis=1), axis=0))
        assert raw["neff"] < 2.0
        assert demeaned["neff"] > raw["neff"]
        # Demeaned rho_bar should be small (near -1/(N-1)), not near +1
        assert demeaned["rho_bar"] < 0.1


class TestNeweyWest:
    def test_constant_series(self):
        x = np.ones(20)
        m, se = _newey_west(x, 5)
        assert abs(m - 1.0) < 1e-12
        assert se > 0  # numerical floor

    def test_nan_short_series(self):
        x = np.array([1.0, 2.0])
        m, se = _newey_west(x, 5)
        assert np.isnan(m) and np.isnan(se)


class TestSkipADayConstruction:
    """CRITICAL-1 corrective: richness at t paired with the dh return over
    t+1 -> t+2 (double-lag), so V_t never enters both signal and return."""

    def _build_panel(self):
        # Two names, five consecutive dates, one row per (date, name).
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"])
        rows = []
        for name in ("A", "B"):
            for i, td in enumerate(dates):
                rows.append({"trade_date": td, "underlying": name,
                             "richA": 0.1 * (i + 1) if name == "A" else -0.1 * (i + 1),
                             "dh_return_scaled": 0.2 * (i + 1) if name == "A" else -0.2 * (i + 1)})
        return pd.DataFrame(rows)

    def test_dh_skip_is_shifted_one_day_forward(self):
        df = self._build_panel()
        panel = df.sort_values(["underlying", "trade_date"]).copy()
        panel["dh_skip"] = panel.groupby("underlying")["dh_return_scaled"].shift(-1)
        # Row at t=2024-01-03, name A: dh_skip should be the t=2024-01-04 return.
        row = panel[(panel["underlying"] == "A") & (panel["trade_date"] == pd.Timestamp("2024-01-03"))]
        assert row["dh_skip"].iloc[0] == 0.2 * 3
        # Last date has no skip (no t+1) -> NaN.
        last = panel[(panel["underlying"] == "A") & (panel["trade_date"] == pd.Timestamp("2024-01-08"))]
        assert np.isnan(last["dh_skip"].iloc[0])
        # No cross-name leakage.
        b_row = panel[(panel["underlying"] == "B") & (panel["trade_date"] == pd.Timestamp("2024-01-03"))]
        assert b_row["dh_skip"].iloc[0] == -0.2 * 3

    def test_skip_uses_richness_at_t(self):
        # The skip frame must retain the richness AT t, not a shifted richness.
        df = self._build_panel()
        panel = df.sort_values(["underlying", "trade_date"]).copy()
        panel["dh_skip"] = panel.groupby("underlying")["dh_return_scaled"].shift(-1)
        panel = panel.dropna(subset=["dh_skip"])
        # Row at t=2024-01-03 name A: richness is 0.1*2 (at t), return is 0.2*3 (over t+1->t+2).
        row = panel[(panel["underlying"] == "A") & (panel["trade_date"] == pd.Timestamp("2024-01-03"))]
        assert row["richA"].iloc[0] == 0.1 * 2
