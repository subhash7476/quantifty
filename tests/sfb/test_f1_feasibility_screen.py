"""Tests for F1 Feasibility Screen."""

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "sfb"))

import f1_feasibility_screen as S


class TestDataStore:
    def test_loads_calendar(self):
        ds = S.DataStore(S.DB_PATH, cutoff=S.DEV_HI)
        assert len(ds.cal) > 100
        assert len(ds.cal_pos) > 100
        ds.close()

    def test_get_px(self):
        ds = S.DataStore(S.DB_PATH, cutoff=S.DEV_HI)
        px = ds.get_px("RELIANCE", date(2020, 1, 1))
        assert px is None or px > 0
        ds.close()


class TestLiquidityUniverse:
    def test_returns_dict(self):
        ds = S.DataStore(S.DB_PATH, cutoff=S.DEV_HI)
        universe, form_dates = S.build_liquidity_universe(ds, cutoff=S.DEV_HI)
        assert isinstance(universe, dict)
        assert len(form_dates) > 0
        if universe:
            fd = list(universe.keys())[0]
            assert isinstance(fd, date)
            assert len(universe[fd]) > 0
        ds.close()


class TestScoreMomentum:
    def test_returns_scores(self):
        ds = S.DataStore(S.DB_PATH, cutoff=S.DEV_HI)
        universe, _ = S.build_liquidity_universe(ds, cutoff=S.DEV_HI)
        ents = []
        for fd in sorted(universe):
            ents = universe[fd]
            if len(ents) >= 3:
                break
        if ents:
            scores = S.score_momentum_12_1(ds, date(2015, 6, 30), set(ents))
            assert isinstance(scores, dict)
        ds.close()


class TestSelectTopN:
    def test_returns_correct_count(self):
        picks = S.select_top_n({"A": 0.1, "B": 0.2, "C": 0.3}, {"A", "B", "C"}, n=2)
        assert picks == ["C", "B"]

    def test_filters_by_universe(self):
        picks = S.select_top_n({"A": 0.1, "B": 0.2, "C": 0.3}, {"A", "C"}, n=3)
        assert picks == ["C", "A"]


class TestApplyBracket:
    def _bar(self, high, low, open_p=None):
        return (date(2020,1,1), high, low, open_p or (high + low) / 2)

    def test_hit_stop_loss_first(self):
        bars = [self._bar(105, 95)]
        price, days = S._apply_bracket(100.0, 2.0, 10, 1.5, 3.0, bars)
        assert price == 97.0
        assert days == 1

    def test_hit_take_profit(self):
        bars = [self._bar(108, 99)]
        price, days = S._apply_bracket(100.0, 2.0, 10, 1.5, 3.0, bars)
        assert price == 106.0
        assert days == 1

    def test_both_hit_sl_first(self):
        bars = [self._bar(108, 95)]
        price, days = S._apply_bracket(100.0, 2.0, 10, 1.5, 3.0, bars)
        assert price == 97.0
        assert days == 1

    def test_no_hit_returns_entry(self):
        bars = [self._bar(102, 98)]
        price, days = S._apply_bracket(100.0, 2.0, 10, 1.5, 3.0, bars)
        assert price == 100.0
        assert days == 10

    def test_differs_with_params(self):
        bars = [self._bar(105, 98), (date(2020,1,2), 107, 99, 103)]
        p1, _ = S._apply_bracket(100.0, 2.0, 5, 1.0, 2.0, bars)
        p2, _ = S._apply_bracket(100.0, 2.0, 5, 3.0, 5.0, bars)
        assert p1 != p2

    def test_open_gap_through_sl(self):
        """Gap open below SL fills at open, not at SL."""
        bars = [self._bar(105, 95, open_p=90)]
        price, days = S._apply_bracket(100.0, 2.0, 10, 1.5, 3.0, bars)
        assert price == 90.0
        assert days == 1


class TestFormationCost:
    def test_cost_is_fraction(self):
        c = S.formation_cost(1_000_000, date(2025, 1, 1), "BUY", 0.0010)
        assert 0.0 < c < 0.01

    def test_slippage_monotonic(self):
        low = S.formation_cost(1_000_000, date(2025, 1, 1), "BUY", 0.0005)
        mid = S.formation_cost(1_000_000, date(2025, 1, 1), "BUY", 0.0010)
        high = S.formation_cost(1_000_000, date(2025, 1, 1), "BUY", 0.0020)
        assert low < mid < high


class TestDecisionRule:
    def test_no_go_if_negative(self):
        pos = S.FoldResult("opt", 10, 0.01, (0, 0.02), 0, 0, 0, 0, 0, "opt", (5,1,2))
        neg = S.FoldResult("pes", 10, -0.01, (-0.02, 0), 0, 0, 0, 0, 0, "pes", (5,1,2))
        go, _, _ = S.decide([pos, neg], [pos, pos])
        assert not go

    def test_go_if_all_positive(self):
        r = S.FoldResult("t", 10, 0.01, (0.005, 0.015), -0.05, 20, 50, 0.02, 0.01, "test", (5,1,2))
        go, _, _ = S.decide([r, r, r], [r, r, r])
        assert go

    def test_no_go_if_fees_consume_edge(self):
        r = S.FoldResult("t", 10, 0.01, (0, 0.02), -0.05, 20, 50, 0.005, -0.001, "test", (5,1,2))
        go, _, _ = S.decide([r], [r])
        assert not go

    def test_ci_violation_detected(self):
        r = S.FoldResult("pessimistic", 10, 0.01, (-0.01, 0.03), -0.05, 20, 50, 0.02, 0.01, "pessimistic", (5,1,2))
        _, _, ci_viol = S.decide([r, r], [r, r])
        assert ci_viol


class TestDayBack:
    def test_returns_earlier_date(self):
        ds = S.DataStore(S.DB_PATH, cutoff=S.DEV_HI)
        cal = ds.cal
        if len(cal) > 50:
            d = cal[50]
            d_back = S._day_back(ds, d, 5)
            assert d_back is not None
            assert d_back < d
        ds.close()
