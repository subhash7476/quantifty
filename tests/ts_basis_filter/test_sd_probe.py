"""Tests for TS Basis Filter SD/Breadth/Stability probe.

Covers: fence (§1), IC-sign/rank-invariance sanity, drop-column bookkeeping,
OI-coverage accounting, and stability-table bookkeeping (circularity + calendar-
anchored concentration).
"""
import numpy as np
import pandas as pd
import pytest

from scripts.ts_basis_filter.sd_probe import (
    FENCE_START,
    FENCE_END,
    MIN_NAMES,
    _assert_fence,
    _ic_stats,
    _newey_west,
    CONFIG_RULES,
    _apply_config,
    _stability_table,
    _build_base_panel,
    _neff_stats,
)


class TestFence:
    def test_fence_pass(self):
        s = pd.Series([pd.Timestamp("2016-02-11"), pd.Timestamp("2022-12-31")])
        lo, hi = _assert_fence(s)  # should not raise
        assert lo == FENCE_START and hi == FENCE_END

    def test_fence_fail_early(self):
        s = pd.Series([pd.Timestamp("2015-12-31"), pd.Timestamp("2022-12-31")])
        with pytest.raises(AssertionError, match="FENCE VIOLATION"):
            _assert_fence(s)

    def test_fence_fail_late(self):
        s = pd.Series([pd.Timestamp("2016-02-11"), pd.Timestamp("2023-01-02")])
        with pytest.raises(AssertionError, match="FENCE VIOLATION"):
            _assert_fence(s)


class TestICStats:
    def _panel(self, n_dates=20, n_names=50, seed=1):
        rng = np.random.default_rng(seed)
        rows = []
        for d in range(n_dates):
            fdt = pd.Timestamp("2020-01-01") + pd.Timedelta(days=d)
            z = rng.normal(0, 1, n_names)
            ret = 0.05 * z + rng.normal(0, 1, n_names)
            for i in range(n_names):
                rows.append({"formation_date": fdt, "underlying": f"U{i}", "z_ts": z[i], "fwd_1": ret[i]})
        return pd.DataFrame(rows)

    def test_min_names_drops_small_formations(self):
        df = self._panel()
        st = _ic_stats(df, "z_ts", "fwd_1")
        assert st is not None
        assert st["n_dates"] == 20
        assert st["mean_ic"] > 0  # constructed positive

    def test_drops_formations_below_min_names(self):
        df = self._panel(n_names=10)  # below MIN_NAMES
        st = _ic_stats(df, "z_ts", "fwd_1")
        assert st is None or st["n_dates"] == 0

    def test_sign_flip_changes_mean_ic(self):
        df = self._panel()
        st_pos = _ic_stats(df, "z_ts", "fwd_1")
        df2 = df.copy()
        df2["fwd_1"] = -df2["fwd_1"]
        st_neg = _ic_stats(df2, "z_ts", "fwd_1")
        assert st_pos["mean_ic"] > 0 and st_neg["mean_ic"] < 0

    def test_rank_invariance(self):
        """Monotone transform of the return must not change Spearman IC."""
        df = self._panel()
        st1 = _ic_stats(df, "z_ts", "fwd_1")
        df2 = df.copy()
        df2["fwd_1"] = np.exp(df2["fwd_1"])
        st2 = _ic_stats(df2, "z_ts", "fwd_1")
        assert abs(st1["mean_ic"] - st2["mean_ic"]) < 1e-9


class TestNeweyWest:
    def test_sd_of_constant_zero(self):
        m, se = _newey_west(np.ones(50), 5)
        # harness floors variance at 1e-15 -> se floor is sqrt(1e-15/50) ~ 1.4e-9
        assert se < 1e-6

    def test_short_series_nan(self):
        m, se = _newey_west(np.array([1.0, 2.0]), 5)
        assert np.isnan(m) and np.isnan(se)


class TestDropColumnBookkeeping:
    def _panel(self):
        rng = np.random.default_rng(0)
        rows = []
        for d in range(15):
            fdt = pd.Timestamp("2020-01-01") + pd.Timedelta(days=d)
            for i in range(40):
                rows.append({
                    "formation_date": fdt, "underlying": f"U{i}",
                    "z_ts": float(rng.normal()), "fwd_1": float(rng.normal()),
                    "vix": 12.0 + d, "vix_med": 12.0,
                    "g1_admit": True, "g2_admit": bool(i % 2), "g3_admit": True,
                    "bull": bool(d % 2), "era": "Pre-COVID", "oi_chg": 1.0, "oi_missing": False,
                })
        return pd.DataFrame(rows)

    def test_config_names_monotone(self):
        """drop-column config (5 minus gate) must admit a superset of full (config 5) names."""
        panel = self._panel()
        full = _apply_config(panel, CONFIG_RULES["full"])
        for drop in ["drop_G1", "drop_G2", "drop_G3"]:
            drop_df = _apply_config(panel, CONFIG_RULES[drop])
            # every full row survives in the drop-column (same formation+underlying)
            full_keys = set(zip(full["formation_date"], full["underlying"]))
            drop_keys = set(zip(drop_df["formation_date"], drop_df["underlying"]))
            assert full_keys.issubset(drop_keys), f"{drop} should be a superset of full"

    def test_full_is_intersection_of_individual_gates(self):
        panel = self._panel()
        full = _apply_config(panel, CONFIG_RULES["full"])
        g1 = _apply_config(panel, CONFIG_RULES["G1"])
        g2 = _apply_config(panel, CONFIG_RULES["G2"])
        g3 = _apply_config(panel, CONFIG_RULES["G3"])
        inter = set(zip(g1["formation_date"], g1["underlying"])) & \
                set(zip(g2["formation_date"], g2["underlying"])) & \
                set(zip(g3["formation_date"], g3["underlying"]))
        assert set(zip(full["formation_date"], full["underlying"])) == inter


class TestOIAccounting:
    def _panel_with_missing(self):
        rng = np.random.default_rng(0)
        rows = []
        for d in range(10):
            fdt = pd.Timestamp("2020-01-01") + pd.Timedelta(days=d)
            for i in range(30):
                missing = (i % 5 == 0)
                rows.append({
                    "formation_date": fdt, "underlying": f"U{i}",
                    "z_ts": float(rng.normal()), "fwd_1": float(rng.normal()),
                    "vix": 12.0, "vix_med": 12.0,
                    "g1_admit": True, "g2_admit": not missing, "g3_admit": True,
                    "bull": True, "era": "Pre-COVID", "oi_chg": 1.0 if not missing else np.nan,
                    "oi_missing": missing,
                })
        return pd.DataFrame(rows)

    def test_missing_oi_names_excluded_and_counted(self):
        panel = self._panel_with_missing()
        admitted = panel[panel["g2_admit"] == True]  # noqa: E712
        assert len(admitted) < len(panel)  # G2 dropped 1-in-5
        # the coverage cost (missing) is separate from the sign-filter effect
        assert int(panel["oi_missing"].sum()) == len(panel) // 5


class TestNeff:
    def test_neff_bounded_below_avg_names(self):
        rng = np.random.default_rng(3)
        rows = []
        for d in range(80):
            fdt = pd.Timestamp("2020-01-01") + pd.Timedelta(days=d)
            common = rng.normal(0, 1, 20)
            for i in range(20):
                rows.append({"formation_date": fdt, "underlying": f"U{i}",
                             "fwd_1": common[i] + rng.normal(0, 0.1)})
        df = pd.DataFrame(rows)
        st = _neff_stats(df, "fwd_1")
        assert st["median_neff"] is not None
        assert 1.0 <= st["median_neff"] <= 20.0
        assert 0 < st["median_pc1"] <= 1.0


class TestStabilityBookkeeping:
    def _full_ic_map(self, panel):
        """Reuse harness path: build ic_stats_by_config via CONFIG_RULES."""
        from scripts.ts_basis_filter.sd_probe import _ic_stats
        ic = {}
        for cfg, rule in CONFIG_RULES.items():
            sub = _apply_config(panel, rule)
            ic[cfg] = {"panel": sub, "H1": _ic_stats(sub, "z_ts", "fwd_1"), "H5": None}
        return ic

    def _panel(self):
        rng = np.random.default_rng(7)
        rows = []
        eras = ["Pre-COVID", "COVID", "Post-COVID"]
        for d in range(120):
            fdt = pd.Timestamp("2018-01-01") + pd.Timedelta(days=d)
            era = eras[0] if d < 40 else (eras[1] if d < 80 else eras[2])
            for i in range(40):
                vix = 15.0 if d < 40 else (25.0 if d < 80 else 12.0)
                rows.append({
                    "formation_date": fdt, "underlying": f"U{i}",
                    "z_ts": float(rng.normal()), "fwd_1": float(rng.normal()),
                    "vix": vix, "vix_med": 15.0,
                    "g1_admit": vix <= 1.5 * 15.0, "g2_admit": bool(i % 2), "g3_admit": True,
                    "bull": bool(d % 2), "era": era, "oi_chg": 1.0, "oi_missing": False,
                })
        return pd.DataFrame(rows)

    def test_circularity_g1_vix_excluded(self):
        panel = self._panel()
        ic = self._full_ic_map(panel)
        rows = _stability_table(panel, ic)
        g1 = next(r for r in rows if r["gate"] == "G1")
        assert g1["circular"] == {"High VIX", "Low VIX"}
        # circular cells are not in the consistency denominator
        counted = {k for k, v in g1["cells"].items() if v is not None and k not in g1["circular"]}
        num, den = g1["consistency"].split("/")
        assert int(den) == len(counted)

    def test_concentration_anchored_on_calendar(self):
        panel = self._panel()
        ic = self._full_ic_map(panel)
        rows = _stability_table(panel, ic)
        for r in rows:
            cal = {k: v for k, v in r["cells"].items()
                   if k in ("Pre-COVID", "COVID", "Post-COVID") and v is not None}
            if r["concentration"] != "—":
                label, pct = r["concentration"].split()
                assert label in ("Pre-COVID", "COVID", "Post-COVID")
                assert 0 < float(pct[:-1]) <= 100

    def test_every_gate_has_all_axes_tagged(self):
        panel = self._panel()
        ic = self._full_ic_map(panel)
        rows = _stability_table(panel, ic)
        assert len(rows) == 3  # G1, G2, G3
        for r in rows:
            assert set(r["cells"].keys()) == {
                "Bull", "Bear", "High VIX", "Low VIX", "Pre-COVID", "COVID", "Post-COVID"}
