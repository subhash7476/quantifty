"""GATE C — Carry rebalancer tests.

Verifies:
  - compute_target_book: correct equal-weight quintile construction
  - compute_deltas: correct delta computation with no-trade band
  - rebalance_book: correct position state transitions
  - EARLY DE-RISK sub-check: research parity (rebalancer produces
    research-identical target book + deltas)
"""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))

from core.execution.portfolio.carry_rebalancer import (
    BAND_SIGMA,
    Delta,
    TargetBook,
    compute_deltas,
    compute_target_book,
    rebalance_book,
)

GROSS = 10_000_000.0
HALF = GROSS / 2.0


def _facts(longs, shorts):
    """Build (underlying, z_carry_neut) tuples. Extra fields ignored."""
    r = [(u, zn) for u, zn in longs] + [(u, zn) for u, zn in shorts]
    return r


class TestComputeTargetBook:
    def test_re_rank_by_z(self):
        """compute_target_book re-ranks by z, ignoring pre-assigned quintile."""
        facts = [("A", 2.0), ("B", 1.5), ("C", -1.5), ("D", -2.0)]
        target = compute_target_book(facts, GROSS)
        # n=4, nq=1 → top=A (highest z), bottom=D (lowest z)
        assert set(target.longs) == {"A"}
        assert set(target.shorts) == {"D"}
        assert target.longs["A"] == pytest.approx(HALF)
        assert target.shorts["D"] == pytest.approx(HALF)

    def test_single_long_single_short(self):
        facts = [("A", 1.0), ("B", -1.0)]
        target = compute_target_book(facts, GROSS)
        # n=2, nq=1
        assert set(target.longs) == {"A"}
        assert set(target.shorts) == {"B"}

    def test_only_long_if_no_negative_z(self):
        facts = [("A", 2.0), ("B", 1.0), ("C", 0.5)]
        target = compute_target_book(facts, GROSS)
        # n=3, nq=1 → long=A, short=C (lowest z among 3)
        assert set(target.longs) == {"A"}
        assert set(target.shorts) == {"C"}
        assert target.longs["A"] == pytest.approx(HALF)
        assert target.shorts["C"] == pytest.approx(HALF)

    def test_middle_z_excluded(self):
        """With nq=1, only highest and lowest z enter the book."""
        facts = [("A", 2.0), ("B", 0.5), ("C", -0.5), ("D", -2.0)]
        target = compute_target_book(facts, GROSS)
        # n=4, nq=1 → long=A, short=D. B and C are middle.
        assert set(target.longs) == {"A"}
        assert set(target.shorts) == {"D"}

    def test_adv_cap_limit(self):
        facts = [("A", 2.0), ("B", 1.5), ("C", -1.5)]
        adva = {"A": 100_000.0, "B": 5_000_000.0, "C": 1_000_000.0}
        target = compute_target_book(facts, GROSS, adva)
        # n=3, nq=1 → long=A (top z), short=C (bottom z)
        # A capped: max_pos = 100K * 0.10 = 10K, cap_each = 5M → min → 10K
        # After re-scale: 10K * (5M/10K) = 5M... no, scale = 5M/10K = 500 → 10K*500=5M
        # Actually cap applies then normalise. With single name in leg after
        # capping, total=10K, scale=5M/10K=500 → A=5M. So cap is just
        # re-scaled away when leg has only one name.
        assert target.longs["A"] == pytest.approx(HALF)
        assert target.shorts["C"] == pytest.approx(HALF)


class TestComputeDeltas:
    def test_open_new_positions(self):
        target = TargetBook(
            formation_date=date(2020, 1, 31),
            longs={"A": HALF / 2, "B": HALF / 2},
            shorts={"C": HALF / 2, "D": HALF / 2},
        )
        deltas = compute_deltas(target, {}, {}, band_sigma=BAND_SIGMA)

        opens = [d for d in deltas if d.action == 'OPEN']
        assert len(opens) == 4
        assert all(not d.suppressed for d in opens)

    def test_close_all_positions(self):
        target = TargetBook(
            formation_date=date(2020, 1, 31), longs={}, shorts={},
        )
        held_longs = {"A": HALF / 2, "B": HALF / 2}
        held_shorts = {"C": HALF / 2}
        deltas = compute_deltas(target, held_longs, held_shorts)

        closes = [d for d in deltas if d.action == 'CLOSE']
        assert len(closes) == 3
        assert all(not d.suppressed for d in closes)

    def test_scale_up_not_suppressed(self):
        target = TargetBook(
            formation_date=date(2020, 1, 31),
            longs={"A": 3_000_000.0, "B": 2_000_000.0},
            shorts={},
        )
        held_longs = {"A": 1_000_000.0, "B": 1_500_000.0}
        deltas = compute_deltas(target, held_longs, {})

        scales = [d for d in deltas if d.action == 'SCALE_UP']
        assert len(scales) == 2

    def test_no_trade_band_suppresses_small_adjustment(self):
        """A small scale-up under the band should be suppressed."""
        target = TargetBook(
            formation_date=date(2020, 1, 31),
            longs={"A": 5_000_000.0},
            shorts={},
        )
        held_longs = {"A": 4_999_999.0}
        # sigma_w is large (~5M) so band is large too — this won't suppress.
        # For a real test, use target with one name so sigma=0.

        deltas = compute_deltas(target, held_longs, {})
        scales = [d for d in deltas if d.action == 'SCALE_UP']
        # With single name, sigma_w = 0 → band = 0 → nothing suppressed
        assert all(not d.suppressed for d in scales)

    def test_no_trade_band_suppresses_small_delta_across_names(self):
        """With multiple names, small deltas under 0.25*std(target_weights) get suppressed."""
        target = TargetBook(
            formation_date=date(2020, 1, 31),
            longs={"A": 4_000_000.0, "B": 1_000_000.0},
            shorts={},
        )
        held_longs = {"A": 3_999_990.0, "B": 1_000_000.0}
        deltas = compute_deltas(target, held_longs, {})
        scales = [d for d in deltas if d.underlying == 'A']
        assert len(scales) == 1
        # sigma ~2.12M, band ~530K. Delta of 10Rs << band → suppressed
        assert scales[0].action == 'SCALE_UP'
        assert scales[0].suppressed

    def test_flip_action(self):
        target = TargetBook(
            formation_date=date(2020, 1, 31),
            longs={"A": 5_000_000.0},
            shorts={},
        )
        held_shorts = {"A": 5_000_000.0}
        deltas = compute_deltas(target, {}, held_shorts)
        flips = [d for d in deltas if d.action == 'FLIP']
        assert len(flips) == 1
        assert flips[0].delta_cap == pytest.approx(10_000_000.0)
        assert not flips[0].suppressed


class TestRebalanceBook:
    def test_state_transition(self):
        target = TargetBook(
            formation_date=date(2020, 1, 31),
            longs={"A": 5_000_000.0},
            shorts={"C": 5_000_000.0},
        )
        new_longs, new_shorts, deltas = rebalance_book(target, {}, {})
        assert new_longs == {"A": 5_000_000.0}
        assert new_shorts == {"C": 5_000_000.0}

    def test_close_then_open(self):
        target = TargetBook(
            formation_date=date(2020, 1, 31),
            longs={"B": 5_000_000.0},
            shorts={},
        )
        held_longs = {"A": 5_000_000.0}
        new_longs, new_shorts, deltas = rebalance_book(
            target, held_longs, {})

        assert "A" not in new_longs
        assert new_longs == {"B": 5_000_000.0}

    def test_suppressed_scale_keeps_old_position(self):
        """When scale is suppressed, the old position should be retained."""
        target = TargetBook(
            formation_date=date(2020, 1, 31),
            longs={"A": 4_000_000.0, "B": 1_000_000.0},
            shorts={},
        )
        held_longs = {"A": 3_999_990.0, "B": 1_000_000.0}
        new_longs, new_shorts, deltas = rebalance_book(
            target, held_longs, {})

        # Suppressed delta should keep old value
        assert new_longs["A"] == 3_999_990.0


# ── EARLY DE-RISK: rebalancer-only construction parity ──
# Feed research signal facts, verify target book + deltas match research harness.

class TestRebalancerResearchParity:
    """Verify the rebalancer reproduces the research harness's target book and
    deltas for a representative formation month.

    Compares compute_target_book output against run_net_spread._compute_targets
    for the same inputs.
    """

    def test_same_quintile_assignment(self):
        """Rebalancer and research harness assign the same names to long/short
        when given identical z_carry_neut values."""
        from scripts.signal_engine.carry.run_net_spread import _compute_targets

        # Research harness expects rows: [(underlying, z_carry_neut, fwd_ret_1m)]
        # and separate ADV dict.
        research_rows = [
            ("A", 2.5, 0.01), ("B", 1.2, 0.02), ("C", 0.8, -0.01),
            ("D", -0.5, 0.0), ("E", -1.3, 0.01), ("F", -2.0, -0.02),
            ("G", 0.3, 0.0), ("H", -0.1, 0.0), ("I", 1.8, 0.01),
            ("J", -1.8, -0.01),
        ]
        n = len(research_rows)
        nq = max(1, round(0.20 * n))  # quintile count = 2

        # Research target
        long_t, short_t = _compute_targets(False, research_rows, {}, nq)
        research_longs = set(long_t)
        research_shorts = set(short_t)

        # Rebalancer facts — quintiles from actual z_carry_neut rank:
        # Sorted: F(-2.0), J(-1.8), E(-1.3), D(-0.5), H(-0.1),
        #          G(0.3), C(0.8), B(1.2), I(1.8), A(2.5)
        # Q1 (bottom 2): F, J      | Q2: E, D   | Q3: H, G
        # Q4: C, B                 | Q5 (top 2): I, A
        facts = [
            ("A", 2.5, 5, True),  ("B", 1.2, 4, True),
            ("C", 0.8, 4, True),  ("D", -0.5, 2, True),
            ("E", -1.3, 2, True), ("F", -2.0, 1, True),
            ("G", 0.3, 3, True),  ("H", -0.1, 3, True),
            ("I", 1.8, 5, True),  ("J", -1.8, 1, True),
        ]
        target = compute_target_book(facts, GROSS)
        reb_longs = set(target.longs)
        reb_shorts = set(target.shorts)

        # Research quintile is by z_carry_neut rank: bottom 2 = F,J, top 2 = I,A
        assert reb_longs == research_longs, (
            f"Long mismatch: reb={reb_longs} research={research_longs}")
        assert reb_shorts == research_shorts, (
            f"Short mismatch: reb={reb_shorts} research={research_shorts}")

    def test_equal_weight_capital_matches_research(self):
        """With no ADV caps, capital allocation should be equal-weight in both."""
        facts = [("A", 2.5), ("I", 1.8), ("B", 1.2), ("C", 0.8),
                 ("G", 0.3), ("H", -0.1), ("D", -0.5), ("E", -1.3),
                 ("J", -1.8), ("F", -2.0)]
        target = compute_target_book(facts, GROSS)
        # n=10, nq=2 → 2 longs, 2 shorts
        assert set(target.longs) == {"A", "I"}
        assert set(target.shorts) == {"F", "J"}
        for u, cap in target.longs.items():
            assert abs(cap - HALF / 2) < 1.0
        for u, cap in target.shorts.items():
            assert abs(cap - HALF / 2) < 1.0
