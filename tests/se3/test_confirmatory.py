"""Tests for SE-3 Phase 1 + Phase 2 — fence, variant-B absence, skip-a-day
convention, one-shot guard, Phase-1 purity, helper cross-check, L/S direction."""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.se3 import certify_substrate as c
from scripts.se3 import run_confirmatory as r
from scripts.se3.breadth_probe import (
    _front_month_rv as probe_front_month_rv,
    _newey_west as probe_newey_west,
    _pick_expiry as probe_pick_expiry,
    _corr_matrix_stats as probe_corr_matrix_stats,
)

HERE = Path(__file__).resolve().parent
# The forbidden index-options DB token is the exact path segment; the stock
# options store is `stock_options_bhavcopy.duckdb`, which legitimately contains
# this string as a substring. Match the exact standalone token.
INDEX_DB_TOKEN = '"options_bhavcopy.duckdb"'
MODULES = {
    "certify": (Path(c.__file__), ["richB", "BETA_WINDOW"]),
    "confirmatory": (Path(r.__file__), ["richB", "BETA_WINDOW"]),
}


class TestFence:
    def test_fence_pass(self):
        df = pd.DataFrame({"trade_date": [pd.Timestamp("2019-06-14")]})
        c._assert_fence(df)

    def test_fence_fail_early(self):
        df = pd.DataFrame({"trade_date": [pd.Timestamp("2016-02-10")]})
        with pytest.raises(AssertionError, match="FENCE VIOLATION"):
            c._assert_fence(df)

    def test_fence_fail_late(self):
        df = pd.DataFrame({"trade_date": [pd.Timestamp("2023-01-03")]})
        with pytest.raises(AssertionError, match="FENCE VIOLATION"):
            c._assert_fence(df)


class TestVariantBAbsence:
    @pytest.mark.parametrize("mod", ["certify", "confirmatory"])
    def test_no_index_options_reference(self, mod):
        path, banned = MODULES[mod]
        src = path.read_text(encoding="utf-8")
        assert INDEX_DB_TOKEN not in src, f"{mod} source references the index-options database"
        for token in banned:
            assert token not in src, f"{mod} source contains forbidden token {token!r}"


class TestPhase1Purity:
    def test_no_ic_call(self):
        src = Path(c.__file__).read_text(encoding="utf-8")
        assert "spearmanr" not in src
        assert "scipy.stats" not in src.replace("from scipy import stats", "")

    def test_no_forward_return_construction(self):
        src = Path(c.__file__).read_text(encoding="utf-8")
        assert "dh_return" not in src
        assert "dh_return_scaled" not in src
        assert "black76_delta" not in src
        assert "black76_vega" not in src


class TestHelperCrossCheck:
    """Phase 1's helpers must agree with breadth_probe.py's on synthetic input."""

    def _rv_frame(self, n=40, expiry="2024-03-25"):
        rows = []
        price = 100.0
        dates = pd.date_range("2024-01-01", periods=n)
        for d in dates:
            rows.append({"trade_date": d, "expiry_dt": pd.Timestamp(expiry), "settle": price})
            price *= 1.001
        return pd.DataFrame(rows)

    def test_newey_west_identical(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=200)
        m1, s1 = probe_newey_west(x, 5)
        m2, s2 = c._newey_west(x, 5)
        assert m1 == pytest.approx(m2)
        assert s1 == pytest.approx(s2)

    def test_pick_expiry_identical(self):
        td = pd.Timestamp("2024-06-14")
        exps = [pd.Timestamp("2024-06-22"), pd.Timestamp("2024-07-27"), pd.Timestamp("2024-08-31")]
        e1 = probe_pick_expiry(exps, td)
        e2 = c._pick_expiry(exps, td)
        assert e1 == e2

    def test_front_month_rv_identical(self):
        g = self._rv_frame()
        f1 = probe_front_month_rv(g)
        f2 = c._front_month_rv(g)
        assert f1["ret"].equals(f2["ret"])
        assert np.allclose(f1["rv"].values, f2["rv"].values, equal_nan=True)

    def test_corr_matrix_stats_identical(self):
        rng = np.random.default_rng(1)
        panel = pd.DataFrame(
            {f"N{i}": rng.normal(size=100) for i in range(4)},
            index=pd.date_range("2024-01-01", periods=100),
        )
        s1 = probe_corr_matrix_stats(panel)
        s2 = c._corr_matrix_stats(panel)
        assert s1["rho_bar"] == pytest.approx(s2["rho_bar"])
        assert s1["neff"] == pytest.approx(s2["neff"])
        assert s1["pc1"] == pytest.approx(s2["pc1"])


class TestSkipADayConvention:
    """Phase 2 pairs richness at t with the return built from V_{t+1}, V_{t+2},
    Delta_{t+1}, vega_{t+1}, and the per-name row shift pairs across a missing
    date rather than dropping it."""

    def _mk(self):
        # Two names, five dates; name A present throughout, name B missing 01-04.
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"])
        rows = []
        for name, pres in (("A", [True]*5), ("B", [True, True, False, True, True])):
            for i, td in enumerate(dates):
                if not pres[i]:
                    continue
                rows.append({
                    "trade_date": td, "underlying": name, "expiry_dt": pd.Timestamp("2024-01-25"),
                    "F_t": 100.0 + i, "richness": 0.1 * (i + 1),
                    "iv_call": (100.0 + i, "CE", 0.2, 5.0),
                    "iv_put": None,
                })
        panel = pd.DataFrame(rows)
        return panel, dates

    def test_pairs_across_missing_date(self):
        panel, dates = self._mk()
        # Traded cells: each name's call cell settles on EVERY trading date so
        # V_{t+1} always resolves (even across B's 01-04 gap).
        traded_rows = []
        for _, row in panel.iterrows():
            strike, ot, iv, settle = row["iv_call"]
            for dd in dates:
                traded_rows.append({"trade_date": dd, "underlying": row["underlying"],
                                    "expiry_dt": row["expiry_dt"], "strike": strike,
                                    "option_type": ot, "settle": settle + 0.1})
        traded = pd.DataFrame(traded_rows)
        # Futures settle for each (underlying, expiry) on every trading date.
        fut_rows = []
        for name in ("A", "B"):
            for dd in dates:
                fut_rows.append({"underlying": name, "expiry_dt": pd.Timestamp("2024-01-25"),
                                 "trade_date": dd, "settle": 101.0})
        fut = pd.DataFrame(fut_rows)
        fut_settle = fut.set_index(["underlying", "expiry_dt", "trade_date"])["settle"]
        out = r.build_returns(panel, traded, fut_settle)
        a = out[out["underlying"] == "A"]
        b = out[out["underlying"] == "B"]
        # A present throughout: returns at 01-02, 01-03, 01-04, 01-05.
        assert set(a["trade_date"]) == set(dates[:-1])
        # B missing 01-04: still returns at 01-02, 01-03, 01-05 (shift(-1) on B's
        # own rows pairs 01-03 -> 01-05 across the gap), and 01-05 has no next row.
        assert set(b["trade_date"]) == {pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03"), pd.Timestamp("2024-01-05")}


class TestLSDirection:
    def test_long_bottom_short_top_pinned(self):
        assert r.LS_DIRECTION == "long_bottom_short_top"

    def test_quintile_direction(self):
        # Build a synthetic panel where bottom richness has high dh, top has low
        # dh -> gross P&L should be positive (long bottom, short top).
        rows = []
        for td in pd.date_range("2024-01-01", periods=5):
            for i in range(10):
                # richness monotonic in i; dh inverse of richness
                rows.append({"trade_date": td, "underlying": f"N{i}",
                             "richness": float(i), "dh_return_scaled": float(-i),
                             "expiry_dt": td + pd.Timedelta(days=20), "F_t": 100.0,
                             "iv_call": (100.0, "CE", 0.2, 5.0), "iv_put": None})
        df = pd.DataFrame(rows)
        q = r._quintile_pnl(df, 0)
        assert q is not None
        assert q["gross_pnl"].mean() > 0


class TestOneShotGuard:
    def test_refuses_when_snapshot_exists(self, tmp_path, monkeypatch):
        snap = tmp_path / "SE3_CONFIRMATORY_SNAPSHOT.json"
        snap.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(r, "SNAPSHOT", snap)
        cert = tmp_path / "SE3_SUBSTRATE_CERTIFICATION.md"
        cert.write_text("S3: PASS\n", encoding="utf-8")
        monkeypatch.setattr(r, "CERT_REPORT", cert)
        with pytest.raises(SystemExit, match="REFUSED"):
            r._check_one_shot()

    def test_refuses_when_cert_absent(self, tmp_path, monkeypatch):
        snap = tmp_path / "SE3_CONFIRMATORY_SNAPSHOT.json"
        monkeypatch.setattr(r, "SNAPSHOT", snap)
        cert = tmp_path / "SE3_SUBSTRATE_CERTIFICATION.md"
        monkeypatch.setattr(r, "CERT_REPORT", cert)
        with pytest.raises(SystemExit, match="REFUSED.*absent"):
            r._check_one_shot()

    def test_refuses_when_s3_fail(self, tmp_path, monkeypatch):
        snap = tmp_path / "SE3_CONFIRMATORY_SNAPSHOT.json"
        monkeypatch.setattr(r, "SNAPSHOT", snap)
        cert = tmp_path / "SE3_SUBSTRATE_CERTIFICATION.md"
        cert.write_text("S3: FAIL\n", encoding="utf-8")
        monkeypatch.setattr(r, "CERT_REPORT", cert)
        with pytest.raises(SystemExit, match="REFUSED.*S3 PASS"):
            r._check_one_shot()

    def test_passes_when_ready(self, tmp_path, monkeypatch):
        snap = tmp_path / "SE3_CONFIRMATORY_SNAPSHOT.json"
        monkeypatch.setattr(r, "SNAPSHOT", snap)
        cert = tmp_path / "SE3_SUBSTRATE_CERTIFICATION.md"
        cert.write_text("S3: PASS\n", encoding="utf-8")
        monkeypatch.setattr(r, "CERT_REPORT", cert)
        r._check_one_shot()  # should not raise
