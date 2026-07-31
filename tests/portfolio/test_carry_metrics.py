"""Tests for the Carry production-metrics primitives.

The metrics layer recomputes fees and slippage per Delta — independently of
the blended FillEvent.fee — so a production-metrics DB carries a correct fee
vs slippage decomposition. See CARRY_PAPER_INTEGRATION_REVIEW.md §4 (slippage
circularity) and the fee/slippage conflation in _execute_deltas.
"""
from datetime import date

import pytest

from core.execution.futures.futures_fees import futures_fees
from core.execution.portfolio.carry_rebalancer import (
    Delta,
    summarize_rebalance,
    SLIPPAGE_BP,
)


def test_flip_charges_slippage_on_both_legs_separate_from_fees():
    """A FLIP is two fills (exit held leg + enter target leg). Slippage must
    accrue on BOTH legs' trade values, and fees must be a distinct total from
    slippage — not the conflated single number _execute_deltas logs today."""
    td = date(2019, 6, 1)
    flip = Delta(
        underlying="X",
        target_side="SHORT",
        target_cap=100_000.0,
        held_side="LONG",
        held_cap=80_000.0,
        delta_cap=180_000.0,   # compute_deltas sets this to held+target for FLIP
        action="FLIP",
        suppressed=False,
    )

    m = summarize_rebalance([flip], td)

    # Both legs are SELL here (exit a long -> SELL; enter a short -> SELL).
    exp_exit = futures_fees(side="SELL", trade_value=80_000.0, trade_date=td).total
    exp_entry = futures_fees(side="SELL", trade_value=100_000.0, trade_date=td).total

    assert m.fees_total == pytest.approx(exp_exit + exp_entry)
    assert m.slippage_total == pytest.approx(
        (SLIPPAGE_BP / 10_000) * (80_000.0 + 100_000.0)
    )
    # The bug being fixed: fees and slippage are NOT the same number.
    assert m.fees_total != pytest.approx(m.slippage_total)


def test_execute_deltas_returns_metrics_matching_summarize():
    """_execute_deltas must return the RebalanceMetrics for the fills it placed,
    computed via summarize_rebalance — so the hook's log and any metrics sink
    see the correct fee/slippage split, not the conflated blend."""
    from core.execution.portfolio.carry_rebalancer import (
        CarryRebalancerHook, TargetBook,
    )

    td = date(2019, 6, 1)
    fills = []

    class FakeTracker:
        def update_from_fill(self, fill):
            fills.append(fill)

    class FakeExec:
        position_tracker = FakeTracker()

    hook = object.__new__(CarryRebalancerHook)
    hook._exec = FakeExec()

    deltas = [
        Delta("A", "LONG", 100_000.0, None, 0.0, 100_000.0, "OPEN", False),
        Delta("B", None, 0.0, "SHORT", 80_000.0, -80_000.0, "CLOSE", False),
    ]
    target = TargetBook(formation_date=td, longs={"A": 100_000.0}, shorts={})

    m = hook._execute_deltas(deltas, target, td)
    exp = summarize_rebalance(deltas, td)

    assert m.fees_total == pytest.approx(exp.fees_total)
    assert m.slippage_total == pytest.approx(exp.slippage_total)
    assert m.n_entries == exp.n_entries
    assert m.n_exits == exp.n_exits
    assert len(fills) == 2  # the fills were still placed on the tracker


def test_metrics_sink_called_during_execute():
    """_execute must call metrics_sink with (fdate, deltas, target, metrics, capital_state)
    after _execute_deltas returns."""
    from datetime import date as Date
    from unittest.mock import patch, MagicMock
    from core.execution.portfolio.carry_rebalancer import (
        CarryRebalancerHook, TargetBook, CapitalState,
        paper_gross_exposure_policy,
    )

    td = Date(2019, 6, 1)
    sink_calls = []

    def fake_sink(fdate, deltas, target, metrics, cap_state):
        sink_calls.append((fdate, deltas, target, metrics, cap_state))

    tracker = MagicMock()
    tracker.get_all_positions.return_value = {}

    exec = MagicMock()
    exec.position_tracker = tracker
    fake_metrics_obj = MagicMock()
    fake_metrics_obj.cash_balance = 10_000_000.0
    fake_metrics_obj.max_equity = 10_000_000.0
    fake_metrics_obj.max_drawdown_pct = 0.0
    exec.metrics = fake_metrics_obj
    exec.pnl_tracker = None

    with patch('duckdb.connect') as mock_connect:
        mock_con = MagicMock()
        mock_con.execute.return_value.fetchall.return_value = []
        mock_connect.return_value = mock_con

        hook = CarryRebalancerHook(
            facts_db_path=":memory:",
            execution_handler=exec,
            gross_exposure_policy=paper_gross_exposure_policy,
            metrics_sink=fake_sink,
        )

        # Must match the 6 columns _execute actually SELECTs:
        # (underlying, z_carry_neut, quintile, eligible, raw_z, basis_reverting).
        # raw_z is deliberately distinct from both z_carry_neut and quintile so
        # that a regression putting either into the raw_z slot is caught rather
        # than silently passing.
        mock_con.execute.return_value.fetchall.return_value = [
            ("A", 1.5, 5, True, 3.9, False),
            ("B", 1.2, 5, True, 3.1, False),
            ("C", -1.8, 1, True, -4.2, False),
            ("D", -1.3, 1, True, -3.7, True),
            ("E", 0.9, 5, True, 2.6, False),
            ("F", -0.5, 1, True, -2.2, False),
        ]

        with patch.object(hook, '_load_adva', return_value={
            "A": 1e9, "B": 1e9, "C": 1e9, "D": 1e9, "E": 1e9, "F": 1e9,
        }):
            fake_metrics = MagicMock()
            fake_metrics.n_exits = 0
            fake_metrics.n_entries = 4
            fake_metrics.fees_total = 500.0
            fake_metrics.slippage_total = 250.0
            fake_metrics.traded_value_total = 1_000_000.0
            fake_metrics.fee_breakdown = {
                'brokerage': 100.0, 'stt': 200.0,
                'exchange_txn': 50.0, 'sebi_fee': 30.0,
                'stamp_duty': 20.0, 'gst': 100.0,
            }

            with patch.object(hook, '_execute_deltas', return_value=fake_metrics):
                hook._execute(td)

    assert len(sink_calls) == 1
    fdate_recv, deltas_recv, target_recv, metrics_recv, cap_recv = sink_calls[0]
    assert fdate_recv == td
    assert len(deltas_recv) == 2
    assert len(target_recv.longs) > 0
    assert len(target_recv.shorts) > 0
    assert metrics_recv is not None
    assert cap_recv.current_equity == 10_000_000.0


def test_trade_sink_receives_raw_z_not_quintile():
    """facts_full[2] must carry raw_z (the unclamped z), not quintile.

    TradeIntelligenceSink._process reads f[2] as raw_z and writes it to
    trade_intelligence.duckdb. _execute previously built that slot from r[2]
    (quintile) instead of r[4] (raw_z), so every trade would have recorded a
    1-5 bucket in the raw_z column. Caught only because the stale 4-tuple mock
    made the same line raise IndexError.
    """
    from datetime import date as Date
    from unittest.mock import patch, MagicMock
    from core.execution.portfolio.carry_rebalancer import (
        CarryRebalancerHook, paper_gross_exposure_policy,
    )

    td = Date(2019, 6, 1)
    trade_calls = []

    tracker = MagicMock()
    tracker.get_all_positions.return_value = {}
    exec_ = MagicMock()
    exec_.position_tracker = tracker
    m = MagicMock()
    m.cash_balance = 10_000_000.0
    m.max_equity = 10_000_000.0
    m.max_drawdown_pct = 0.0
    exec_.metrics = m
    exec_.pnl_tracker = None

    # (underlying, z_carry_neut, quintile, eligible, raw_z, basis_reverting)
    rows = [
        ("A", 1.5, 5, True, 3.9, False),
        ("B", 1.2, 5, True, 3.1, False),
        ("C", -1.8, 1, True, -4.2, False),
        ("D", -1.3, 1, True, -3.7, True),
        ("E", 0.9, 5, True, 2.6, False),
        ("F", -0.5, 1, True, -2.2, False),
    ]
    expected_raw_z = {r[0]: r[4] for r in rows}
    expected_quintile = {r[0]: r[2] for r in rows}

    with patch('duckdb.connect') as mock_connect:
        mock_con = MagicMock()
        mock_con.execute.return_value.fetchall.return_value = rows
        mock_connect.return_value = mock_con

        hook = CarryRebalancerHook(
            facts_db_path=":memory:",
            execution_handler=exec_,
            gross_exposure_policy=paper_gross_exposure_policy,
            trade_sink=lambda fd, ex, pe, facts: trade_calls.append(facts),
        )

        with patch.object(hook, '_load_adva', return_value={
            u: 1e9 for u in expected_raw_z
        }):
            with patch.object(hook, '_execute_deltas', return_value=MagicMock()):
                hook._execute(td)

    assert len(trade_calls) == 1
    facts = trade_calls[0]
    assert facts, "trade_sink received no facts"
    for f in facts:
        underlying, z, raw_z, quintile, basis_reverting = f
        assert raw_z == expected_raw_z[underlying], (
            f"{underlying}: raw_z slot carried {raw_z}, expected "
            f"{expected_raw_z[underlying]}"
        )
        assert quintile == expected_quintile[underlying]
        # The regression: raw_z must not be the quintile.
        assert raw_z != quintile
