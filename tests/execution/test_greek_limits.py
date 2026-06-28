"""
MM9.3-S1A — Greek Gate Semantic Correction.

Characterization:
  C1 (raises ExecutionRuleError) — DELETED at slice close (semantics fixed).
  C2 (marginal-only, not portfolio) — RETAINED for S1B.

Unit tests U1-U6: _check_greek_limits gate semantics.
Integration tests I1-I6: process_signal wiring + ordering.

Marginal delta math: equity delta = quantity (greeks_calculator.py:40).
With confidence=0.9, default_quantity=100, no explicit quantity:
    qty = 100 * (0.5 + 0.9 * 0.5) = 95  →  marginal delta = 95.0
"""

import logging
from datetime import datetime

import pytz

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.brokers.paper_broker import PaperBroker
from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.order_lifecycle import FillEvent
from core.execution.persistence.execution_store import ExecutionStore

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


# =========================================================================== #
# Shared construction helpers
# =========================================================================== #

def _build_handler(tmp_path, monkeypatch, *, max_portfolio_delta=1000.0,
                   max_capital_utilisation=0.80, initial_capital=100_000.0):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    clock = ReplayClock(FIXED_DT)
    config = ExecutionConfig(
        max_portfolio_delta=max_portfolio_delta,
        max_capital_utilisation=max_capital_utilisation,
    )
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=PaperBroker(clock),
        config=config,
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
    )


def _make_signal(symbol="NSE_EQ|INE001A01036", sig_type=SignalType.BUY,
                 suffix="S1A", confidence=0.9, quantity=None):
    metadata = {
        "signal_id": f"SIG-S1A-{suffix}",
        "sl_distance": 1.0,
        "risk_r": 1.0,
    }
    if quantity is not None:
        metadata["quantity"] = quantity
    return SignalEvent(
        strategy_id="test_greek",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=sig_type,
        confidence=confidence,
        metadata=metadata,
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
# Characterization test C1 (raises ExecutionRuleError) was deleted at slice
# close — the crash-escalation defect is fixed. C2 below is retained for S1B.
# =========================================================================== #

def test_current_greek_gate_checks_only_marginal_not_portfolio(
        tmp_path, monkeypatch):
    # C2 — documents the marginal-only interim state. RETAINED for S1B.
    # Inject a held position with delta 200; set limit 100. A portfolio-aware
    # gate would see combined 200 + 95 = 295 > 100 and reject. The current
    # gate checks only the marginal 95 <= 100 and does not reject.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=100.0)
    _inject_position(handler, "NSE_EQ|HELD1", 200, 100.0)
    signal = _make_signal(symbol="NSE_EQ|NEWSIG", suffix="C2")
    result = handler._check_greek_limits(signal, 100.0)
    # Pre-S1A: returns None (implicit). Post-S1A: returns True. Never False.
    assert result is not False


# =========================================================================== #
# U1-U6 — _check_greek_limits gate-method unit tests
# =========================================================================== #

def test_greek_gate_returns_bool(tmp_path, monkeypatch):
    # U1 — returns bool for both pass and breach inputs.
    handler_pass = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=200.0)
    handler_breach = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=50.0)
    signal = _make_signal(suffix="U1pass")
    assert isinstance(handler_pass._check_greek_limits(signal, 100.0), bool)
    assert isinstance(handler_breach._check_greek_limits(signal, 100.0), bool)


def test_greek_gate_never_raises_on_delta_breach(tmp_path, monkeypatch):
    # U2 — a breach input does NOT raise; returns False.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=50.0)
    signal = _make_signal(suffix="U2")
    result = handler._check_greek_limits(signal, 100.0)
    assert result is False


def test_greek_gate_bypasses_exit_signal(tmp_path, monkeypatch):
    # U3 — EXIT returns True; InstrumentParser.parse is NOT called.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=50.0)
    signal = _make_signal(sig_type=SignalType.EXIT, suffix="U3")
    parse_calls = {"n": 0}
    orig_parse = handler_mod.InstrumentParser.parse

    def spy_parse(symbol):
        parse_calls["n"] += 1
        return orig_parse(symbol)

    monkeypatch.setattr(handler_mod.InstrumentParser, "parse", spy_parse)
    before = handler.metrics.rejected_trades
    result = handler._check_greek_limits(signal, 100.0)
    assert result is True
    assert parse_calls["n"] == 0
    assert handler.metrics.rejected_trades == before


def test_greek_gate_increments_rejected_trades_on_breach(tmp_path, monkeypatch):
    # U4 — breach increments rejected_trades by exactly 1; pass leaves it.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=50.0)
    signal = _make_signal(suffix="U4")
    before = handler.metrics.rejected_trades
    handler._check_greek_limits(signal, 100.0)
    assert handler.metrics.rejected_trades == before + 1


def test_greek_gate_logs_warning_on_breach(tmp_path, monkeypatch, caplog):
    # U5 — breach logs GREEK_DELTA_BREACH with symbol + signal_id; pass/EXIT silent.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=50.0)
    monkeypatch.setattr(handler.logger, "propagate", True)
    with caplog.at_level(logging.WARNING):
        handler._check_greek_limits(_make_signal(suffix="U5breach"), 100.0)
    msgs = [r.getMessage() for r in caplog.records]
    assert any("GREEK_DELTA_BREACH" in m for m in msgs)
    assert any("NSE_EQ|INE001A01036" in m for m in msgs)
    assert any("SIG-S1A-U5breach" in m for m in msgs)


def test_greek_gate_passes_when_delta_within_limit(tmp_path, monkeypatch):
    # U6 — delta == limit is a pass (strict > breach). Explicit quantity=100,
    # limit 100.0: abs(100) > 100 is False → pass.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=100.0)
    signal = _make_signal(suffix="U6", quantity=100)
    result = handler._check_greek_limits(signal, 100.0)
    assert result is True


# =========================================================================== #
# I1-I6 — process_signal call-site integration tests
# =========================================================================== #

def test_process_signal_returns_none_when_greek_gate_rejects(tmp_path, monkeypatch):
    # I1 — over-limit BUY → None + rejected_trades == 1.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=50.0)
    result = handler.process_signal(_make_signal(suffix="I1"), 100.0)
    assert result is None
    assert handler.metrics.rejected_trades == 1


def test_process_signal_proceeds_when_greek_gate_passes(tmp_path, monkeypatch):
    # I2 — under-limit BUY reaches the PaperBroker fill path.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=1000.0)
    result = handler.process_signal(
        _make_signal(symbol="NSE_EQ|I2SYM", suffix="I2"), 100.0)
    assert result is not None


def test_process_signal_exit_bypasses_greek_gate(tmp_path, monkeypatch):
    # I3 — EXIT against an open LONG is not blocked by the greek gate.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=1.0)
    _inject_position(handler, "NSE_EQ|I3SYM", 100, 100.0)
    handler.update_market_price("NSE_EQ|I3SYM", 100.0)
    real_method = handler._check_greek_limits
    recorded = []

    def spy(signal, current_price):
        ret = real_method(signal, current_price)
        recorded.append(ret)
        return ret

    monkeypatch.setattr(handler, "_check_greek_limits", spy)
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|I3SYM", sig_type=SignalType.EXIT, suffix="I3"),
        100.0,
    )
    assert recorded and recorded[-1] is True


def test_greek_gate_rejection_pre_empts_margin_gate(tmp_path, monkeypatch):
    # I4 — greek rejection returns None before _check_margin_budget runs;
    # rejected_trades == 1 (not 2).
    handler = _build_handler(
        tmp_path, monkeypatch,
        max_portfolio_delta=50.0, max_capital_utilisation=0.01)
    margin_calls = {"n": 0}
    orig_margin = handler._check_margin_budget

    def spy_margin(order, price):
        margin_calls["n"] += 1
        return orig_margin(order, price)

    monkeypatch.setattr(handler, "_check_margin_budget", spy_margin)
    result = handler.process_signal(_make_signal(suffix="I4"), 100.0)
    assert result is None
    assert margin_calls["n"] == 0
    assert handler.metrics.rejected_trades == 1


def test_no_executionruleerror_from_greek_gate_in_process_signal(tmp_path, monkeypatch):
    # I5 — process_signal on a breach returns None (no raise).
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=50.0)
    result = handler.process_signal(_make_signal(suffix="I5"), 100.0)
    assert result is None


def test_greek_gate_rejection_does_not_create_order_tracker_entry(
        tmp_path, monkeypatch):
    # I6 — a Greek rejection leaves no orphan order in order_tracker.
    # Mirrors MM9.1's test_rejected_signal_order_not_in_tracker. The [9C] gate
    # runs strictly before [PHASE 5] order_tracker.add_order (handler.py:790).
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=50.0)
    result = handler.process_signal(_make_signal(suffix="I6"), 100.0)
    assert result is None
    assert len(handler.order_tracker.order_states()) == 0
