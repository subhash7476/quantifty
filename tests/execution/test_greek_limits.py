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
from core.risk.greeks.greeks_model import Greeks

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


# =========================================================================== #
# Shared construction helpers
# =========================================================================== #

def _build_handler(tmp_path, monkeypatch, *, max_portfolio_delta=1000.0,
                   max_portfolio_vega=500.0, max_gamma_exposure=100.0,
                   max_capital_utilisation=0.80, initial_capital=100_000.0):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    clock = ReplayClock(FIXED_DT)
    config = ExecutionConfig(
        max_portfolio_delta=max_portfolio_delta,
        max_portfolio_vega=max_portfolio_vega,
        max_gamma_exposure=max_gamma_exposure,
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
# Characterization tests C1 and C2 were deleted at their respective slice
# closes. C1 (raises ExecutionRuleError) deleted at S1A close — semantics
# fixed. C2 (checks_only_marginal) deleted at S1B close — portfolio scope
# fixed. The gate is now portfolio-aware (delta + vega + gamma).
# =========================================================================== #


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
    # U5 — breach logs GREEK_LIMIT_BREACH with symbol + signal_id; pass/EXIT silent.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=50.0)
    monkeypatch.setattr(handler.logger, "propagate", True)
    with caplog.at_level(logging.WARNING):
        handler._check_greek_limits(_make_signal(suffix="U5breach"), 100.0)
    msgs = [r.getMessage() for r in caplog.records]
    assert any("GREEK_LIMIT_BREACH" in m for m in msgs)
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


# =========================================================================== #
# B1-B7 — S1B portfolio Greek aggregation tests
# =========================================================================== #

def test_greek_gate_returns_true_on_empty_book(tmp_path, monkeypatch):
    # B1 — no positions → portfolio Greeks = 0; marginal within limits → True.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=200.0)
    signal = _make_signal(suffix="B1")
    result = handler._check_greek_limits(signal, 100.0)
    assert result is True


def test_greek_gate_returns_false_on_portfolio_delta_breach(tmp_path, monkeypatch):
    # B2 — mock portfolio delta=50; marginal=95; combined=145 > limit 100 → False.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=100.0)
    monkeypatch.setattr(
        handler.portfolio_greeks, "calculate_portfolio_greeks",
        lambda **kw: Greeks(50.0, 0.0, 0.0, 0.0, 0.0))
    signal = _make_signal(suffix="B2")
    result = handler._check_greek_limits(signal, 100.0)
    assert result is False


def test_greek_gate_returns_false_on_vega_breach(tmp_path, monkeypatch):
    # B3 — portfolio vega=400; equity marginal vega=0; limit 300 → breach.
    # Delta and gamma limits are loose so only vega triggers.
    handler = _build_handler(
        tmp_path, monkeypatch,
        max_portfolio_delta=10000.0, max_portfolio_vega=300.0,
        max_gamma_exposure=10000.0)
    monkeypatch.setattr(
        handler.portfolio_greeks, "calculate_portfolio_greeks",
        lambda **kw: Greeks(0.0, 0.0, 400.0, 0.0, 0.0))
    signal = _make_signal(suffix="B3")
    result = handler._check_greek_limits(signal, 100.0)
    assert result is False


def test_greek_gate_returns_false_on_gamma_breach(tmp_path, monkeypatch):
    # B4 — portfolio gamma=80; equity marginal gamma=0; limit 50 → breach.
    handler = _build_handler(
        tmp_path, monkeypatch,
        max_portfolio_delta=10000.0, max_portfolio_vega=10000.0,
        max_gamma_exposure=50.0)
    monkeypatch.setattr(
        handler.portfolio_greeks, "calculate_portfolio_greeks",
        lambda **kw: Greeks(0.0, 80.0, 0.0, 0.0, 0.0))
    signal = _make_signal(suffix="B4")
    result = handler._check_greek_limits(signal, 100.0)
    assert result is False


def test_greek_gate_uses_price_cache_for_market_prices(tmp_path, monkeypatch):
    # B5 — _price_cache projected to market_prices dict passed to PortfolioGreeks.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=10000.0)
    handler.update_market_price("NSE_EQ|SYM_A", 150.0)
    handler.update_market_price("NSE_EQ|SYM_B", 250.0)
    captured = {}

    def spy(**kwargs):
        captured.update(kwargs)
        return Greeks(0.0, 0.0, 0.0, 0.0, 0.0)

    monkeypatch.setattr(
        handler.portfolio_greeks, "calculate_portfolio_greeks", spy)
    signal = _make_signal(suffix="B5")
    handler._check_greek_limits(signal, 100.0)
    assert captured["market_prices"] == {"NSE_EQ|SYM_A": 150.0, "NSE_EQ|SYM_B": 250.0}


def test_greek_gate_uses_signal_metadata_iv_for_marginal(tmp_path, monkeypatch):
    # B6 — signal.metadata['iv'] is passed as volatility to GreeksCalculator.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=10000.0)
    monkeypatch.setattr(
        handler.portfolio_greeks, "calculate_portfolio_greeks",
        lambda **kw: Greeks(0.0, 0.0, 0.0, 0.0, 0.0))
    from core.risk.greeks.greeks_calculator import GreeksCalculator
    captured = {}

    def spy_calc(**kwargs):
        captured.update(kwargs)
        return Greeks(95.0, 0.0, 0.0, 0.0, 0.0)

    monkeypatch.setattr(GreeksCalculator, "calculate", spy_calc)
    signal = _make_signal(suffix="B6")
    signal.metadata["iv"] = 0.5
    handler._check_greek_limits(signal, 100.0)
    assert captured.get("volatility") == 0.5


def test_greek_gate_defaults_iv_when_metadata_absent(tmp_path, monkeypatch):
    # B7 — no 'iv' in metadata → default 0.20 passed to GreeksCalculator.
    handler = _build_handler(tmp_path, monkeypatch, max_portfolio_delta=10000.0)
    monkeypatch.setattr(
        handler.portfolio_greeks, "calculate_portfolio_greeks",
        lambda **kw: Greeks(0.0, 0.0, 0.0, 0.0, 0.0))
    from core.risk.greeks.greeks_calculator import GreeksCalculator
    captured = {}

    def spy_calc(**kwargs):
        captured.update(kwargs)
        return Greeks(95.0, 0.0, 0.0, 0.0, 0.0)

    monkeypatch.setattr(GreeksCalculator, "calculate", spy_calc)
    signal = _make_signal(suffix="B7")
    signal.metadata.pop("iv", None)
    handler._check_greek_limits(signal, 100.0)
    assert captured.get("volatility") == 0.20
