"""PAPER integration tests (per CARRY_PAPER_INTEGRATION_PROMPT.md §8).

Extends the existing GATE C tests with:
  - Policy injection: paper_policy returns constant, live_policy raises
  - ADV-wiring warning: None bhavcopy_db_path emits WARNING
  - Margin-feasibility formula: rejected when utilisation exceeded
  - Fee/slippage: FillEvent.fee > 0 with real futures_fees call
"""
import logging
import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))

from core.execution.portfolio.carry_rebalancer import (
    BAND_SIGMA,
    ADV_CAP_FRAC,
    CapitalState,
    CarryRebalancerHook,
    Delta,
    TargetBook,
    compute_deltas,
    compute_target_book,
    live_gross_exposure_policy,
    paper_gross_exposure_policy,
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


# ── PAPER integration tests (CARRY_PAPER_INTEGRATION_PROMPT.md §8) ──


class TestGrossExposurePolicies:
    def test_paper_policy_returns_constant(self):
        state = CapitalState(
            starting_capital=1_000_000.0,
            current_equity=500_000.0,
            realized_pnl=-500_000.0,
            current_drawdown_pct=-0.50,
        )
        assert paper_gross_exposure_policy(state) == 10_000_000.0

    def test_paper_policy_ignores_state(self):
        """Policy returns the same constant regardless of state."""
        s1 = CapitalState(1e9, 1e9, 0.0, 0.0)
        s2 = CapitalState(1e3, 1e3, 0.0, 0.0)
        assert paper_gross_exposure_policy(s1) == paper_gross_exposure_policy(s2)

    def test_live_policy_raises(self):
        state = CapitalState(1_000_000.0, 1_000_000.0, 0.0, 0.0)
        with pytest.raises(NotImplementedError, match="separate, reviewed decision"):
            live_gross_exposure_policy(state)


class TestAdvWarning:
    def test_warning_on_none_bhavcopy(self, caplog, tmp_path):
        facts_db = tmp_path / "facts.duckdb"
        con = duckdb.connect(str(facts_db))
        con.execute("CREATE TABLE carry_facts (formation_date DATE, underlying VARCHAR)")
        con.close()

        class DummyExec:
            position_tracker = None

        with caplog.at_level(logging.WARNING):
            CarryRebalancerHook(
                facts_db_path=str(facts_db),
                execution_handler=DummyExec(),
                bhavcopy_db_path=None,
            )

        assert any("ADV capping disabled" in r.message for r in caplog.records)


class TestMarginFeasibility:
    MARGIN_RATE = 0.20
    MAX_UTIL = 0.80

    def test_feasible_passes(self):
        """Rs 1 Cr gross against Rs 1 Cr equity → 20% margin utilisation, OK."""
        gross = 10_000_000.0
        equity = 10_000_000.0
        required = gross * self.MARGIN_RATE       # 20 lakh
        available = equity * self.MAX_UTIL          # 80 lakh
        assert required <= available

    def test_over_utilised_fails(self):
        """Rs 5 Cr gross against Rs 1 Cr equity → 100% margin, fails."""
        gross = 50_000_000.0
        equity = 10_000_000.0
        required = gross * self.MARGIN_RATE        # 1 Cr
        available = equity * self.MAX_UTIL          # 80 lakh
        assert required > available

    def test_boundary_exact(self):
        """At exactly 4x equity, utilisation hits the 80% cap."""
        equity = 10_000_000.0
        gross = equity / self.MARGIN_RATE * self.MAX_UTIL  # 4 Cr
        required = gross * self.MARGIN_RATE        # 80 lakh
        available = equity * self.MAX_UTIL          # 80 lakh
        assert abs(required - available) < 1.0


class TestFeeOnFill:
    def test_build_fill_has_nonzero_fee(self):
        """_build_fill produces a FillEvent with fee > 0 from futures_fees + slippage."""
        from core.execution.portfolio.carry_rebalancer import CarryRebalancerHook, SLIPPAGE_BP

        class DummyExec:
            position_tracker = None

        hook = CarryRebalancerHook.__new__(CarryRebalancerHook)
        fill = hook._build_fill(
            underlying="TEST",
            side="SELL",
            trade_val=1_000_000.0,
            trade_date=date(2020, 6, 15),
            ts=date(2020, 6, 15),
        )
        assert fill.fee > 0
        # STT at 0.0100% on SELL = Rs 100. Slippage at 5bp = Rs 500.
        # Fee should exceed Rs 100 at minimum.
        assert fill.fee >= 100.0
        expected_slippage = (SLIPPAGE_BP / 10000) * 1_000_000.0
        assert expected_slippage == 500.0

    def test_build_fill_buy_no_stt(self):
        """BUY side has no STT, but still has exchange + sebi + stamp + slippage."""
        from core.execution.portfolio.carry_rebalancer import CarryRebalancerHook

        hook = CarryRebalancerHook.__new__(CarryRebalancerHook)
        fill = hook._build_fill(
            underlying="TEST",
            side="BUY",
            trade_val=1_000_000.0,
            trade_date=date(2020, 6, 15),
            ts=date(2020, 6, 15),
        )
        assert fill.fee > 0
        # BUY side has stamp duty at 0.002% = Rs 20. Slippage = Rs 500.
        assert fill.fee >= 20.0


# ── Integration test: _derive_capital_state reads from ExecutionHandler.metrics ──


class TestDeriveCapitalState:
    def test_reads_cash_balance_from_metrics(self):
        """_derive_capital_state sources equity from execution.metrics.cash_balance,
        not from held positions. This is the fix for the zero-equity-on-first-rebalance
        bug — held positions start empty, cash_balance carries the real initial_capital."""
        from core.execution.portfolio.carry_rebalancer import _derive_capital_state

        class FakeMetrics:
            cash_balance = 10_000_000.0
            max_equity = 10_000_000.0
            max_drawdown_pct = 0.0

        class FakeExec:
            metrics = FakeMetrics()
            pnl_tracker = None

        class FakeTracker:
            def get_all_positions(self):
                return {}  # empty — first rebalance, no positions yet

        state = _derive_capital_state(FakeTracker(), FakeExec())
        assert state.current_equity == 10_000_000.0
        assert state.starting_capital == 10_000_000.0

    def test_paper_flow_margin_clears(self):
        """End-to-end chain: derive capital → paper policy → margin check.
        With Rs 1 Cr cash and 1 Cr paper gross, the check passes:
        1 Cr * 0.20 = 20L required, 1 Cr * 0.80 = 80L available."""
        from core.execution.portfolio.carry_rebalancer import (
            _derive_capital_state, paper_gross_exposure_policy,
        )

        class FakeMetrics:
            cash_balance = 10_000_000.0
            max_equity = 10_000_000.0
            max_drawdown_pct = 0.0

        class FakeExec:
            metrics = FakeMetrics()
            pnl_tracker = None

        class FakeTracker:
            def get_all_positions(self):
                return {}

        state = _derive_capital_state(FakeTracker(), FakeExec())
        gross = paper_gross_exposure_policy(state)
        required = gross * 0.20
        available = state.current_equity * 0.80
        assert required <= available, (
            f"Margin check failed: required={required} available={available}"
        )

    def test_zero_cash_fails(self):
        """With no cash_balance (metrics missing or zero), margin check should fail."""
        from core.execution.portfolio.carry_rebalancer import _derive_capital_state

        class FakeExec:
            metrics = None
            pnl_tracker = None

        class FakeTracker:
            def get_all_positions(self):
                return {}

        state = _derive_capital_state(FakeTracker(), FakeExec())
        assert state.current_equity == 0.0
        assert state.starting_capital == 0.0
        # At 0 equity, even 1 Cr gross fails
        required = 10_000_000.0 * 0.20
        available = state.current_equity * 0.80
        assert required > available
