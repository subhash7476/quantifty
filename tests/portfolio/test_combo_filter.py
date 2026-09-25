"""Combo-filter tests (TS Basis Daily paper: recovery + conviction).

Covers apply_signal_filters boundary/AND/identity semantics and
CarryRebalancerHook param defaults + storage.
"""
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.portfolio.carry_rebalancer import (
    CarryRebalancerHook,
    apply_signal_filters,
    compute_quintile_combo_book,
)

# facts_full rows: (underlying, z, raw_z, quintile, reverting)


def _row(u, z, q=5, rev=False):
    return (u, z, z, q, rev)


class TestApplySignalFilters:
    def test_defaults_are_identity(self):
        rows = [_row("A", 0.1), _row("B", -3.0, 1, True)]
        assert apply_signal_filters(rows) == rows
        assert apply_signal_filters(rows, None, False) == rows

    def test_min_abs_z_boundary(self):
        rows = [_row("KEEP", 0.71), _row("EDGE", 0.70), _row("DROP", 0.69),
                _row("NEG", -0.71)]
        out = apply_signal_filters(rows, min_abs_z=0.7)
        assert {r[0] for r in out} == {"KEEP", "NEG"}

    def test_exclude_reverting(self):
        rows = [_row("CLEAN", 2.0), _row("REV", 2.0, rev=True),
                _row("NONE", 2.0)]
        rows[2] = ("NONE", 2.0, 2.0, 5, None)
        out = apply_signal_filters(rows, exclude_reverting=True)
        assert {r[0] for r in out} == {"CLEAN", "NONE"}

    def test_and_combination(self):
        rows = [_row("A", 1.2, 5, False), _row("B", 0.5, 5, False),
                _row("C", -2.0, 1, True), _row("D", -1.1, 1, False)]
        out = apply_signal_filters(rows, 0.7, True)
        assert [(r[0]) for r in out] == ["A", "D"]

    def test_quintile_ignored(self):
        rows = [_row("Q3", 1.5, 3, False)]
        assert apply_signal_filters(rows, 0.7, True) == rows

    def test_empty_in_empty_out(self):
        assert apply_signal_filters([], 0.7, True) == []


class TestHookParams:
    def _hook(self, tmp_path, **kw):
        db = tmp_path / "facts.duckdb"
        con = duckdb.connect(str(db))
        con.execute(
            "CREATE TABLE carry_facts (formation_date DATE, underlying VARCHAR)"
        )
        con.close()
        return CarryRebalancerHook(
            facts_db_path=str(db), execution_handler=object(), **kw)

    def test_defaults_preserve_behavior(self, tmp_path):
        hook = self._hook(tmp_path)
        assert hook._min_abs_z is None
        assert hook._exclude_reverting is False
        assert hook._legs_by_quintile is False

    def test_combo_params_stored(self, tmp_path):
        hook = self._hook(tmp_path, min_abs_z=0.7, exclude_reverting=True,
                           legs_by_quintile=True)
        assert hook._min_abs_z == 0.7
        assert hook._exclude_reverting is True
        assert hook._legs_by_quintile is True


class TestComputeQuintileComboBook:
    GROSS = 10_000_000.0
    HALF = 5_000_000.0

    def test_equal_weight_half_gross_per_leg(self):
        book = compute_quintile_combo_book(["A", "B"], ["C"], self.GROSS)
        assert set(book.longs) == {"A", "B"}
        assert set(book.shorts) == {"C"}
        assert sum(book.longs.values()) == pytest.approx(self.HALF)
        assert sum(book.shorts.values()) == pytest.approx(self.HALF)
        assert book.longs["A"] == pytest.approx(self.HALF / 2)

    def test_empty_leg_contributes_zero(self):
        book = compute_quintile_combo_book(["A", "B"], [], self.GROSS)
        assert book.shorts == {}
        assert sum(book.longs.values()) == pytest.approx(self.HALF)

    def test_adv_cap_binds_before_rescale(self):
        """A is ADV-capped pre-rescale, so A < B; leg still totals half gross.

        (Cap-then-rescale can lift a name above its ADV cap — same convention
        as compute_target_book; the cap binds the pre-scale split, not the final.)
        """
        adva = {"A": 1_000_000.0, "B": 1_000_000_000.0, "C": 1_000_000_000.0}
        book = compute_quintile_combo_book(["A", "B"], ["C"], self.GROSS, adva)
        assert book.longs["A"] < book.longs["B"]
        assert sum(book.longs.values()) == pytest.approx(self.HALF)
        assert sum(book.shorts.values()) == pytest.approx(self.HALF)
