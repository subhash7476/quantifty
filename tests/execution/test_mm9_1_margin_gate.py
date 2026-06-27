"""
MM9.1 — Margin Gate (capital-utilisation enforcement).

MM9.1-S1 scope: ExecutionConfig.max_capital_utilisation field only.
This file receives additional tests in S3 (gate method, call-site wiring,
full characterization) without modification to the S1 tests below.

MM9.1-S3 scope: _check_margin_budget gate method + process_signal wiring.
Priority 1 (U1–U7 gate-method unit tests, I1–I8 call-site integration),
Priority 2 (R1–R4 regression), and L1 (C3 known-limitation documentation).
"""

import logging
from datetime import date, datetime

import pytest
import pytz

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.brokers.paper_broker import PaperBroker
from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.order_lifecycle import FillEvent
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.position_models import PositionSide
from core.execution.rules import ExecutionRuleError
from core.instruments.canonical import AssetClass, CanonicalInstrument
from core.instruments.equity import Equity

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


# =========================================================================== #
# MM9.1-S1 — ExecutionConfig.max_capital_utilisation field
# =========================================================================== #

def test_execution_config_max_capital_utilisation_defaults_to_0_80():
    assert ExecutionConfig().max_capital_utilisation == 0.80


def test_execution_config_max_capital_utilisation_is_configurable():
    cfg = ExecutionConfig(max_capital_utilisation=0.5)
    assert cfg.max_capital_utilisation == 0.5


def test_execution_config_existing_fields_unaffected_by_s1():
    cfg = ExecutionConfig()
    assert cfg.broker_error_threshold == 3
    assert cfg.max_drawdown_limit == 0.05


def test_execution_config_max_capital_utilisation_type_is_float():
    assert isinstance(ExecutionConfig().max_capital_utilisation, float)


# =========================================================================== #
# Shared construction helpers (MM9.1-S3)
# =========================================================================== #

def _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0, max_utilisation=0.80):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    clock = ReplayClock(FIXED_DT)
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=PaperBroker(clock),
        config=ExecutionConfig(max_capital_utilisation=max_utilisation),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
    )


def _make_signal(symbol="NSE_EQ|INE001A01036", sig_type=SignalType.BUY,
                 suffix="S3", quantity=None):
    metadata = {
        "signal_id": f"SIG-MM9-{suffix}",
        "sl_distance": 1.0,
        "risk_r": 1.0,
    }
    if quantity is not None:
        metadata["quantity"] = quantity
    return SignalEvent(
        strategy_id="test_margin",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=sig_type,
        confidence=0.9,
        metadata=metadata,
    )


def _make_order(symbol="NSE_EQ|INE001A01036", quantity=100,
                canonical_instrument=None, side=OrderSide.BUY):
    return NormalizedOrder(
        instrument=Equity(symbol),
        side=side,
        quantity=quantity,
        order_type=OrderType.MARKET,
        strategy_id="test_margin",
        signal_id="sig-unit",
        timestamp=FIXED_DT,
        canonical_instrument=canonical_instrument,
    )


def _inject_position(handler, symbol, qty, price, side="BUY"):
    fill = FillEvent(
        fill_id=f"fill-{symbol}",
        order_id=f"ord-{symbol}",
        symbol=symbol,
        quantity=qty,
        price=price,
        timestamp=FIXED_DT,
        side=side,
    )
    handler.position_tracker.update_from_fill(fill)


# =========================================================================== #
# MM9.1-S3 Priority 1 — _check_margin_budget gate-method unit tests
# =========================================================================== #

def test_check_margin_budget_returns_tuple(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    result = handler._check_margin_budget(_make_order(quantity=10), 100.0)
    assert isinstance(result, tuple) and len(result) == 2
    approved, utilisation = result
    assert isinstance(approved, bool)
    assert isinstance(utilisation, float)


def test_check_margin_budget_approves_below_limit(tmp_path, monkeypatch):
    # incremental = (10 * 1.0 * 200) * 0.2 = 400; utilisation = 400/1000 = 0.4
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=1000.0)
    approved, utilisation = handler._check_margin_budget(_make_order(quantity=10), 200.0)
    assert approved is True
    assert abs(utilisation - 0.4) < 1e-9


def test_check_margin_budget_rejects_above_limit(tmp_path, monkeypatch):
    # incremental = (100 * 1.0 * 10) * 0.2 = 200; utilisation = 200/100 = 2.0
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=100.0)
    approved, utilisation = handler._check_margin_budget(_make_order(quantity=100), 10.0)
    assert approved is False
    assert abs(utilisation - 2.0) < 1e-9


def test_check_margin_budget_boundary_equal_approved(tmp_path, monkeypatch):
    # incremental = (40 * 1.0 * 100) * 0.2 = 800; utilisation = 800/1000 = 0.8 (== limit)
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=1000.0)
    approved, utilisation = handler._check_margin_budget(_make_order(quantity=40), 100.0)
    assert approved is True
    assert abs(utilisation - 0.8) < 1e-12


def test_check_margin_budget_zero_cash_balance_returns_true(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    handler.metrics.cash_balance = 0
    approved, utilisation = handler._check_margin_budget(_make_order(quantity=100), 100.0)
    assert approved is True
    assert utilisation == 0.0


def test_canonical_multiplier_applied_f_and_o(tmp_path, monkeypatch):
    # canonical_instrument.multiplier == lot_size == 75 → incremental uses 75×
    # incremental = (10 * 75) * 100 * 0.2 = 15000; utilisation = 15000/100000 = 0.15
    # (equity fallback of 1.0 would give 0.002)
    handler = _build_handler(tmp_path, monkeypatch)
    ci = CanonicalInstrument(
        asset_class=AssetClass.FUTURE, exchange="NSE_FO",
        underlying="NIFTY", expiry=date(2026, 7, 30), lot_size=75,
    )
    order = _make_order(symbol="NSE_FO|NIFTY26JULFUT", quantity=10, canonical_instrument=ci)
    approved, utilisation = handler._check_margin_budget(order, 100.0)
    assert approved is True
    assert abs(utilisation - 0.15) < 1e-9


def test_equity_fallback_multiplier_is_1_0(tmp_path, monkeypatch):
    # canonical_instrument=None → instrument.multiplier == 1.0
    # incremental = (10 * 1.0 * 100) * 0.2 = 200; utilisation = 200/100000 = 0.002
    handler = _build_handler(tmp_path, monkeypatch)
    approved, utilisation = handler._check_margin_budget(_make_order(quantity=10), 100.0)
    assert approved is True
    assert abs(utilisation - 0.002) < 1e-12


# =========================================================================== #
# MM9.1-S3 Priority 1 — process_signal call-site integration tests
# =========================================================================== #

def test_process_signal_rejected_when_over_limit(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=100.0)
    before = handler.metrics.rejected_trades
    result = handler.process_signal(_make_signal(suffix="I1", quantity=100), 10.0)
    assert result is None
    assert handler.metrics.rejected_trades == before + 1


def test_process_signal_approved_when_under_limit(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    before = handler.metrics.rejected_trades
    result = handler.process_signal(_make_signal(suffix="I2"), 100.0)
    assert result is not None
    assert handler.metrics.rejected_trades == before


def test_exit_signal_bypasses_margin_gate(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    # Open a LONG first (passes the gate as a normal non-EXIT).
    buy = _make_signal(symbol="NSE_EQ|LONG1", suffix="I3BUY", quantity=100)
    assert handler.process_signal(buy, 100.0) is not None
    # Spy on the gate — it must NOT be invoked for the EXIT.
    calls = {"n": 0}

    def spy(order, price):
        calls["n"] += 1
        return True, 0.0

    monkeypatch.setattr(handler, "_check_margin_budget", spy)
    exit_sig = _make_signal(symbol="NSE_EQ|LONG1", sig_type=SignalType.EXIT, suffix="I3EXIT")
    result = handler.process_signal(exit_sig, 100.0)
    assert result is not None
    assert calls["n"] == 0


def test_rejected_trades_increments_exactly_once_on_rejection(tmp_path, monkeypatch):
    # Rejection path: +1 exactly.
    handler_rej = _build_handler(tmp_path, monkeypatch, initial_capital=100.0)
    before = handler_rej.metrics.rejected_trades
    handler_rej.process_signal(_make_signal(suffix="I4REJ", quantity=100), 10.0)
    assert handler_rej.metrics.rejected_trades == before + 1

    # Approval path: unchanged.
    handler_app = _build_handler(tmp_path, monkeypatch)
    before_app = handler_app.metrics.rejected_trades
    handler_app.process_signal(
        _make_signal(symbol="NSE_EQ|I4APP", suffix="I4APP"), 100.0)
    assert handler_app.metrics.rejected_trades == before_app


def test_approved_signal_order_not_orphaned(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    result = handler.process_signal(
        _make_signal(symbol="NSE_EQ|I5", suffix="I5"), 100.0)
    assert result is not None
    assert handler.order_tracker.get_order(str(result.correlation_id)) is not None
    assert len(handler.order_tracker.order_states()) == 1


def test_rejected_signal_order_not_in_tracker(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=100.0)
    result = handler.process_signal(_make_signal(suffix="I6", quantity=100), 10.0)
    assert result is None
    assert len(handler.order_tracker.order_states()) == 0


def test_warning_logged_on_rejection(tmp_path, monkeypatch, caplog):
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=100.0)
    # setup_logger sets propagate=False; re-enable so caplog (root handler) captures.
    monkeypatch.setattr(handler.logger, "propagate", True)
    with caplog.at_level(logging.WARNING):
        result = handler.process_signal(_make_signal(suffix="I7", quantity=100), 10.0)
    assert result is None
    msgs = [r.getMessage() for r in caplog.records]
    assert any("MARGIN_BUDGET_REJECTED" in m for m in msgs)
    # MM9.2-S1 removed the [C3: ...] disclosure from the rejection log;
    # the C3 limitation is resolved by the handler-owned price cache.
    assert not any("C3:" in m for m in msgs)


def test_warning_not_logged_on_approval(tmp_path, monkeypatch, caplog):
    handler = _build_handler(tmp_path, monkeypatch)
    monkeypatch.setattr(handler.logger, "propagate", True)
    with caplog.at_level(logging.WARNING):
        result = handler.process_signal(
            _make_signal(symbol="NSE_EQ|I8", suffix="I8"), 100.0)
    assert result is not None
    msgs = [r.getMessage() for r in caplog.records]
    assert not any("MARGIN_BUDGET_REJECTED" in m for m in msgs)


# =========================================================================== #
# MM9.1-S3 Priority 2 — regression tests
# =========================================================================== #

def test_kill_switch_still_gates_before_margin(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    handler._kill_switched = True
    calls = {"n": 0}

    def spy(order, price):
        calls["n"] += 1
        return True, 0.0

    monkeypatch.setattr(handler, "_check_margin_budget", spy)
    before = handler.metrics.rejected_trades
    result = handler.process_signal(_make_signal(suffix="R1"), 100.0)
    assert result is None
    assert calls["n"] == 0
    assert handler.metrics.rejected_trades == before


def test_risk_manager_rejection_fires_before_margin_gate(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    handler.risk_manager.denied_symbols.add("NSE_EQ|INE001A01036")
    calls = {"n": 0}

    def spy(order, price):
        calls["n"] += 1
        return True, 0.0

    monkeypatch.setattr(handler, "_check_margin_budget", spy)
    with pytest.raises(ExecutionRuleError):
        handler.process_signal(_make_signal(suffix="R2"), 100.0)
    assert calls["n"] == 0


def test_paper_broker_fill_path_unaffected_by_approved_margin(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    result = handler.process_signal(
        _make_signal(symbol="NSE_EQ|R3SYM", suffix="R3"), 100.0)
    assert result is not None
    pos = handler.position_tracker.get_position("NSE_EQ|R3SYM")
    assert pos.side == PositionSide.LONG
    assert pos.quantity > 0


def test_recovery_positions_contribute_to_margin(tmp_path, monkeypatch):
    # Inject a recovered position on REC1, then call the gate for an order on
    # the SAME symbol (bypassing process_signal's stacking guard). The injected
    # position must show up in used_current. No mocking of get_used_margin.
    # MM9.2-S1: _check_margin_budget reads self._price_cache; warm REC1's
    # entry to mimic the first signal arrival after a restart (the cache warms
    # as bars/signals arrive — see MM9.2-S1 spec §5).
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=1000.0)
    _inject_position(handler, "NSE_EQ|REC1", 100, 10.0)
    handler.update_market_price("NSE_EQ|REC1", 10.0)
    order = _make_order(symbol="NSE_EQ|REC1", quantity=10)
    approved, utilisation = handler._check_margin_budget(order, 10.0)
    # used_current = (100 * 10 * 1.0) * 0.2 = 200; incremental = (10 * 10) * 0.2 = 20
    # utilisation = (200 + 20) / 1000 = 0.22 (would be 0.02 without the position)
    assert approved is True
    assert abs(utilisation - 0.22) < 1e-9


# =========================================================================== #
# MM9.1-S3 Known-limitation documentation test (C3)
# =========================================================================== #

def test_multi_symbol_blindness_documented(tmp_path, monkeypatch, caplog):
    """Cold-start residual blindness after MM9.2-S1 (spec §8 R2).

    MM9.2-S1 introduced a handler-owned _latest_prices cache fed to
    get_used_margin, resolving the original C3 portfolio blindness for any
    symbol that has signalled since restart. The residual: a HELD symbol
    whose position was restored via _replay_state but which has not yet
    signalled is absent from _latest_prices, so it still contributes 0 to
    used_current. Symbol AAA is injected (replay seam) at ~100% of capital
    (500 @ 10, capital 1000 → used 1000 if priced). A new BUY for symbol BBB
    carries only ~19% incremental and is APPROVED, because AAA is invisible
    to the cold-start cache. The cold-start gap is bounded to the first tick
    cycle per symbol (spec §5.4). The [C3: ...] runtime disclosure is gone
    (C3 resolved), so the rejection WARNING no longer carries it.
    """
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=1000.0)
    handler._kill_switch_disabled = True  # S4: equity accounting reduces cash; test is about margin gate, not drawdown
    _inject_position(handler, "NSE_EQ|AAA", 500, 10.0)  # ~100% of capital if priced

    # BBB: different symbol, ~19% incremental — approved because AAA is invisible
    # to the cold-start cache (held via replay, never signalled since restart).
    sig_b = _make_signal(symbol="NSE_EQ|BBB", suffix="L1B")
    result = handler.process_signal(sig_b, 10.0)
    assert result is not None  # cold-start residual: AAA's saturation invisible

    # A rejection (its own incremental over the limit) — C3 disclosure is gone.
    monkeypatch.setattr(handler.logger, "propagate", True)
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        over = _make_signal(symbol="NSE_EQ|EEE", suffix="L1E", quantity=100)
        result2 = handler.process_signal(over, 1000.0)  # 100*1000*0.2/1000 = 20.0 > 0.8
    assert result2 is None
    msgs = [r.getMessage() for r in caplog.records]
    assert any("MARGIN_BUDGET_REJECTED" in m for m in msgs)
    assert not any("C3:" in m for m in msgs)
