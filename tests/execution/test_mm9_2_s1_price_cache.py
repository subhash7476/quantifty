"""
MM9.2-S1 — Handler-Owned Price Cache (C3 removal).

Architecture A (spec §2): ExecutionHandler owns a ``_latest_prices`` dict that
warms on every ``process_signal`` call and is fed to
``MarginTracker.get_used_margin``. MarginTracker stays stateless; its signature
is unchanged. The cache is signal-driven (not bar-driven), so a held symbol
that has not signalled since restart remains unpriced — the cold-start residual
documented at spec §8 R1/R2.

Coverage mirrors MM9.2-S1 IMPLEMENTATION_SPEC §10:

Priority 1 (required):
  * cache_initializes_empty
  * cache_updated_on_signal
  * cache_accumulates_across_signals
  * cache_overwritten_on_repeat_signal
  * margin_gate_uses_full_cache
  * held_symbol_contributes_to_used_margin
  * exit_still_bypasses_gate
  * cache_warm_cold_start
  * no_c3_warning_in_log_format

Priority 2 (cold-start / recovery):
  * cold_start_held_symbol_not_in_cache
  * recovery_positions_priced_after_first_bar
  * utilisation_with_two_held_positions_and_new_signal

Documented limitation:
  * stale_price_in_cache_for_non_signaling_symbol
"""

import logging
from datetime import datetime

import pytz
import pytest

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.brokers.paper_broker import PaperBroker
from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.order_lifecycle import FillEvent
from core.execution.order_models import OrderSide, OrderType
from core.execution.persistence.execution_store import ExecutionStore

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


# =========================================================================== #
# Shared construction helpers — mirror tests/execution/test_mm9_1_margin_gate.py
# =========================================================================== #

def _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0,
                   max_utilisation=0.80):
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
                 suffix="S1", quantity=None, price_metadata=None):
    metadata = {
        "signal_id": f"SIG-MM9.2-{suffix}",
        "sl_distance": 1.0,
        "risk_r": 1.0,
    }
    if quantity is not None:
        metadata["quantity"] = quantity
    return SignalEvent(
        strategy_id="test_mm9_2_s1",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=sig_type,
        confidence=0.9,
        metadata=metadata,
    )


def _inject_position(handler, symbol, qty, price, side="BUY"):
    """Mimics _replay_state: pushes a FillEvent straight into position_tracker
    without going through process_signal — so the cache is NOT warmed."""
    fill = FillEvent(
        fill_id=f"fill-{symbol}-{side}",
        order_id=f"ord-{symbol}-{side}",
        symbol=symbol,
        quantity=qty,
        price=price,
        timestamp=FIXED_DT,
        side=side,
    )
    handler.position_tracker.update_from_fill(fill)


def _spy_used_margin(handler, monkeypatch):
    """Wraps margin_tracker.get_used_margin to capture (prices, return value)."""
    captured = {"prices": None, "used": None, "n": 0}
    real = handler.margin_tracker.get_used_margin

    def spy(prices):
        captured["n"] += 1
        captured["prices"] = dict(prices)
        captured["used"] = real(prices)
        return captured["used"]

    monkeypatch.setattr(handler.margin_tracker, "get_used_margin", spy)
    return captured


# =========================================================================== #
# Priority 1 — cache mechanics
# =========================================================================== #

def test_price_cache_initializes_empty(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    assert handler._latest_prices == {}


def test_price_cache_updated_on_signal(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    handler.process_signal(_make_signal(symbol="NSE_EQ|AAA", suffix="P1A"), 100.0)
    assert handler._latest_prices.get("NSE_EQ|AAA") == 100.0


def test_price_cache_accumulates_across_signals(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|AAA", suffix="P1B-A"), 100.0)
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|BBB", suffix="P1B-B"), 200.0)
    assert set(handler._latest_prices.keys()) == {"NSE_EQ|AAA", "NSE_EQ|BBB"}
    assert handler._latest_prices["NSE_EQ|AAA"] == 100.0
    assert handler._latest_prices["NSE_EQ|BBB"] == 200.0


def test_price_cache_overwritten_on_repeat_signal(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    # First BUY fills -> AAA long, cache[AAA] = 100.
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|AAA", suffix="P1C-1"), 100.0)
    assert handler._latest_prices["NSE_EQ|AAA"] == 100.0
    # Second BUY on AAA is blocked by the stacking guard, but the cache update
    # happens before that guard, so the price is overwritten anyway.
    result = handler.process_signal(
        _make_signal(symbol="NSE_EQ|AAA", suffix="P1C-2"), 150.0)
    assert result is None  # stacking guard rejected the second entry
    assert handler._latest_prices["NSE_EQ|AAA"] == 150.0


# =========================================================================== #
# Priority 1 — gate uses full cache
# =========================================================================== #

def test_margin_gate_uses_full_cache(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    # First signal for AAA opens a position and warms cache AAA=100.
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|AAA", suffix="P1D-A"), 100.0)
    captured = _spy_used_margin(handler, monkeypatch)
    # Second signal for BBB triggers the gate; cache must contain both keys.
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|BBB", suffix="P1D-B"), 50.0)
    assert captured["n"] >= 1
    assert "NSE_EQ|AAA" in captured["prices"]
    assert "NSE_EQ|BBB" in captured["prices"]


def test_held_symbol_contributes_to_used_margin(tmp_path, monkeypatch):
    """Concrete: hold 100 AAA @ 100 (cached), then check used_margin when the
    gate runs for a new BBB order. Under MM9.1 used_margin was 0 (only BBB
    priced); under MM9.2-S1 AAA contributes 100*100*1.0*0.2 = 2000."""
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=1_000_000.0)
    # Open AAA position and warm its cache entry.
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|AAA", suffix="P1E-A", quantity=100), 100.0)
    captured = _spy_used_margin(handler, monkeypatch)
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|BBB", suffix="P1E-B"), 50.0)
    assert captured["used"] is not None
    # AAA alone contributes 100 * 100 * 1.0 * 0.2 = 2000 (> 0).
    assert captured["used"] > 0.0
    # Sanity: AAA's contribution alone is 2000; plus BBB's open position if any
    # (none — BBB is the signal that triggers the gate, not yet filled).
    assert captured["used"] >= 2000.0 - 1e-9


# =========================================================================== #
# Priority 1 — EXIT bypass preserved
# =========================================================================== #

def test_exit_still_bypasses_gate(tmp_path, monkeypatch):
    """EXIT signals must not invoke _check_margin_budget (D8), but the cache
    update at the start of process_signal still applies."""
    handler = _build_handler(tmp_path, monkeypatch)
    # Open a LONG on AAA (cache[AAA] = 100).
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|AAA", suffix="P1F-IN", quantity=100), 100.0)

    calls = {"n": 0}

    def spy(order, price):
        calls["n"] += 1
        return True, 0.0

    monkeypatch.setattr(handler, "_check_margin_budget", spy)
    exit_sig = _make_signal(symbol="NSE_EQ|AAA", sig_type=SignalType.EXIT,
                            suffix="P1F-EX")
    result = handler.process_signal(exit_sig, 110.0)
    assert result is not None
    assert calls["n"] == 0  # EXIT bypassed the gate
    # Cache update applied to EXIT too — price overwritten to 110.
    assert handler._latest_prices["NSE_EQ|AAA"] == 110.0


# =========================================================================== #
# Priority 1 — cold-start / log format
# =========================================================================== #

def test_cache_warm_cold_start(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    assert handler._latest_prices == {}  # cold
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|AAA", suffix="P1H"), 100.0)
    assert len(handler._latest_prices) == 1
    assert handler._latest_prices == {"NSE_EQ|AAA": 100.0}


def test_no_c3_warning_in_log_format(tmp_path, monkeypatch, caplog):
    """MM9.2-S1 resolves C3, so the [C3: ...] disclosure must be gone from the
    MARGIN_BUDGET_REJECTED log."""
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=100.0)
    monkeypatch.setattr(handler.logger, "propagate", True)
    with caplog.at_level(logging.WARNING):
        result = handler.process_signal(
            _make_signal(suffix="P1I", quantity=100), 10.0)
    assert result is None
    msgs = [r.getMessage() for r in caplog.records]
    assert any("MARGIN_BUDGET_REJECTED" in m for m in msgs)
    assert not any("single-symbol gate only" in m for m in msgs)
    assert not any("C3:" in m for m in msgs)


# =========================================================================== #
# Priority 2 — cold-start residual (held symbol not yet signalled)
# =========================================================================== #

def test_cold_start_held_symbol_not_in_cache(tmp_path, monkeypatch):
    """Spec §8 R2 cold-start residual: a held symbol whose price has not yet
    been warmed by a signal is absent from _latest_prices. The gate still
    runs without error and the symbol contributes 0 to used_margin."""
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=1_000_000.0)
    # Held position via the replay seam — bypasses process_signal entirely.
    _inject_position(handler, "NSE_EQ|HELD", 100, 100.0)
    assert "NSE_EQ|HELD" not in handler._latest_prices
    captured = _spy_used_margin(handler, monkeypatch)
    # Signal for an unrelated symbol — gate runs; HELD is unpriced -> 0.
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|NEW", suffix="P2A"), 50.0)
    assert captured["used"] == 0.0  # HELD invisible because cache is cold
    assert "NSE_EQ|HELD" not in captured["prices"]


def test_recovery_positions_priced_after_first_bar(tmp_path, monkeypatch):
    """Spec §5: after restart, PositionTracker has recovered held positions
    but _latest_prices is empty. The first signal for the held symbol warms
    its cache entry; a subsequent signal for a different symbol then sees the
    held position correctly priced."""
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=1_000_000.0)
    _inject_position(handler, "NSE_EQ|HELD", 100, 100.0)
    assert handler._latest_prices == {}  # cold after replay

    # First signal for HELD is blocked by the stacking guard (already long),
    # but the cache update at the start of process_signal still warms HELD.
    blocked = handler.process_signal(
        _make_signal(symbol="NSE_EQ|HELD", suffix="P2B-WARM"), 100.0)
    assert blocked is None  # stacking guard
    assert handler._latest_prices["NSE_EQ|HELD"] == 100.0

    # Now a different symbol's signal triggers the gate; HELD contributes.
    captured = _spy_used_margin(handler, monkeypatch)
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|NEW", suffix="P2B-NEW"), 50.0)
    assert "NSE_EQ|HELD" in captured["prices"]
    assert captured["used"] >= 100 * 100 * 1.0 * 0.2 - 1e-9  # HELD priced


def test_utilisation_with_two_held_positions_and_new_signal(tmp_path, monkeypatch):
    """Three-symbol scenario (spec §10 P2): two held positions A and B both
    cached, new signal for C. used_margin must include A + B; utilisation
    includes A + B + incremental(C)."""
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=1_000_000.0)
    # Open A and B (fills), each warming its own cache entry.
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|AAA", suffix="P2C-A", quantity=100), 100.0)
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|BBB", suffix="P2C-B", quantity=100), 100.0)
    captured = _spy_used_margin(handler, monkeypatch)
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|CCC", suffix="P2C-C"), 50.0)
    # used = 100*100*1*0.2 (AAA) + 100*100*1*0.2 (BBB) = 4000
    assert abs(captured["used"] - 4000.0) < 1e-9
    assert set(["NSE_EQ|AAA", "NSE_EQ|BBB"]).issubset(captured["prices"].keys())


# =========================================================================== #
# Documented limitation — stale price for non-signaling held symbol (§8 R1)
# =========================================================================== #

def test_stale_price_in_cache_for_non_signaling_symbol(tmp_path, monkeypatch):
    """Accepted limitation — cache is signal-driven, not bar-driven.

    A symbol that has not signalled since its last cache write retains the
    last signalled price indefinitely. If the market has moved, the gate
    computes used_margin against a stale mark. The future resolution
    (LoopDriver per-bar hook) is out of scope for MM9.2-S1. See
    MM9.2-S1 IMPLEMENTATION_SPEC §8 R1.
    """
    handler = _build_handler(tmp_path, monkeypatch)
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|STALE", suffix="P3-WARM"), 100.0)
    # Many signals on other symbols; STALE never signals again.
    for i in range(5):
        handler.process_signal(
            _make_signal(symbol=f"NSE_EQ|OTHER{i}", suffix=f"P3-{i}"), 10.0)
    # STALE's cached price is unchanged despite the (simulated) market drift.
    assert handler._latest_prices["NSE_EQ|STALE"] == 100.0
