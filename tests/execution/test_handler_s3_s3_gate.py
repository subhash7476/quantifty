"""
MM9.2-S3-S3 — Fresh Price Gate.

Validates MM9_2_S3_S3_IMPLEMENTATION_SPEC.md: a fresh-book preflight gate in
`ExecutionHandler.process_signal` that blocks ENTRY signals when any held
(non-FLAT) position cannot be freshly priced (snapshot MISSING from
`_price_cache`, or STALE — age > `ExecutionConfig.max_price_age_s`). EXIT
signals bypass it (inherited from the outer guard). The gate runs BEFORE the
MM9.1 capital gate so `_check_margin_budget` never computes utilisation on a
partial book (the C3 under-count class). Default `max_price_age_s = inf`
disables the gate (no-op) — existing behaviour preserved.

Architecture refinement (approved): `_check_book_priceable()` returns a pure
immutable `PriceabilityResult(priceable, stale_symbols, missing_symbols)` value
object instead of `tuple[bool, set]`. The helper has NO side effects — all
logging / metrics / journal work lives in the `process_signal` call-site.

Coverage mirrors spec §7 (TC-U/S/I/A/R). Phase-0 characterization (TC-C1/C2)
is superseded by the acceptance tests (TC-A1/A2) which confirm existence.
"""

import logging
import math
from datetime import datetime, timedelta

import pytz
import pytest

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.brokers.paper_broker import PaperBroker
from core.execution.handler import (
    ExecutionConfig,
    ExecutionHandler,
    PriceabilityResult,
)
from core.execution.order_lifecycle import FillEvent
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.position_models import Position, PositionSide
from core.runtime.event_journal import EventType, Severity, _DEFAULT_SEVERITY

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


# =========================================================================== #
# Shared construction helpers (mirror test_mm9_2_s3_s1_price_cache.py)
# =========================================================================== #

def _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0,
                   max_utilisation=0.80, max_price_age_s=float('inf'),
                   journal=None):
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
        config=ExecutionConfig(
            max_capital_utilisation=max_utilisation,
            max_price_age_s=max_price_age_s,
        ),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
        journal=journal,
    )


def _make_signal(symbol="NSE_EQ|INE001A01036", sig_type=SignalType.BUY,
                 suffix="S3S3", quantity=None):
    metadata = {
        "signal_id": f"SIG-MM9.2-S3-S3-{suffix}",
        "sl_distance": 1.0,
        "risk_r": 1.0,
    }
    if quantity is not None:
        metadata["quantity"] = quantity
    return SignalEvent(
        strategy_id="test_mm9_2_s3_s3",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=sig_type,
        confidence=0.9,
        metadata=metadata,
    )


def _inject_position(handler, symbol, qty, price, side="BUY"):
    """Pushes a FillEvent straight into position_tracker (mirrors _replay_state)
    so a non-FLAT held position exists WITHOUT warming _price_cache."""
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


class _MockJournal:
    """Records record() calls; never touches disk."""
    def __init__(self):
        self.calls = []

    def record(self, event_type, message, *, severity=None,
               source_component=None, metadata=None):
        self.calls.append({
            "event_type": event_type,
            "message": message,
            "severity": severity,
            "source_component": source_component,
            "metadata": metadata,
        })
        return {}


# =========================================================================== #
# Phase 1 — Unit tests for _check_book_priceable() (the pure helper)
# =========================================================================== #
# All age tests use max_price_age_s=60. Age is produced by warming the cache at
# clock.now() then advancing the deterministic ReplayClock.

def test_u1_flat_book_vacuously_priceable(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    result = handler._check_book_priceable()
    assert result.priceable is True
    assert result.stale_symbols == set()
    assert result.missing_symbols == set()


def test_u2_disabled_gate_always_priceable(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=float('inf'))
    _inject_position(handler, "NSE_EQ|X", 100, 100.0)
    # No cache entry for X — but gate is disabled.
    result = handler._check_book_priceable()
    assert result.priceable is True
    assert result.stale_symbols == set()
    assert result.missing_symbols == set()


def test_u3_fresh_snapshot_priceable(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, "NSE_EQ|X", 100, 100.0)
    handler.update_market_price("NSE_EQ|X", 100.0)        # timestamp = now
    handler.clock.advance(timedelta(seconds=30))          # age 30s <= 60
    result = handler._check_book_priceable()
    assert result.priceable is True
    assert result.stale_symbols == set()


def test_u4_age_equals_threshold_priceable(tmp_path, monkeypatch):
    """Equality boundary (spec §2.7): age == max_price_age_s is FRESH
    (comparison is strictly greater-than)."""
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, "NSE_EQ|X", 100, 100.0)
    handler.update_market_price("NSE_EQ|X", 100.0)
    handler.clock.advance(timedelta(seconds=60))          # age == 60 exactly
    result = handler._check_book_priceable()
    assert result.priceable is True
    assert result.stale_symbols == set()


def test_u5_age_greater_than_threshold_stale(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, "NSE_EQ|X", 100, 100.0)
    handler.update_market_price("NSE_EQ|X", 100.0)
    handler.clock.advance(timedelta(seconds=61))          # age 61 > 60
    result = handler._check_book_priceable()
    assert result.priceable is False
    assert result.stale_symbols == {"NSE_EQ|X"}
    assert result.missing_symbols == set()


def test_u6_symbol_missing_from_cache(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, "NSE_EQ|X", 100, 100.0)     # held, never warmed
    result = handler._check_book_priceable()
    assert result.priceable is False
    assert result.missing_symbols == {"NSE_EQ|X"}
    assert result.stale_symbols == set()


def test_u7_mix_fresh_and_stale(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, "NSE_EQ|X", 100, 100.0)
    _inject_position(handler, "NSE_EQ|Y", 100, 100.0)
    handler.update_market_price("NSE_EQ|X", 100.0)        # X fresh
    handler.update_market_price("NSE_EQ|Y", 100.0)        # Y warmed
    handler.clock.advance(timedelta(seconds=61))          # both age 61s now
    handler.update_market_price("NSE_EQ|X", 101.0)        # re-warm X -> fresh
    result = handler._check_book_priceable()
    assert result.priceable is False
    assert result.stale_symbols == {"NSE_EQ|Y"}
    assert result.missing_symbols == set()


def test_u8_mix_fresh_and_missing(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, "NSE_EQ|X", 100, 100.0)
    _inject_position(handler, "NSE_EQ|Y", 100, 100.0)     # Y never warmed
    handler.update_market_price("NSE_EQ|X", 100.0)        # X fresh
    result = handler._check_book_priceable()
    assert result.priceable is False
    assert result.missing_symbols == {"NSE_EQ|Y"}
    assert result.stale_symbols == set()


def test_u9_flat_position_excluded(tmp_path, monkeypatch):
    """A FLAT position contributes nothing to margin and must not trip the gate
    even if its symbol has no fresh cache entry (spec §2.8/§2.9)."""
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    # Place a FLAT position directly (a closed/expired slot the tracker retains).
    handler.position_tracker._positions["NSE_EQ|FLAT"] = Position(
        symbol="NSE_EQ|FLAT", side=PositionSide.FLAT, quantity=0)
    result = handler._check_book_priceable()
    assert result.priceable is True
    assert result.stale_symbols == set()
    assert result.missing_symbols == set()


def test_u_helper_is_pure_no_metrics_mutation(tmp_path, monkeypatch):
    """R8: the helper must not mutate metrics, log, journal, or call
    MarginTracker. Verifies the purity contract directly."""
    journal = _MockJournal()
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0,
                             journal=journal)
    _inject_position(handler, "NSE_EQ|X", 100, 100.0)     # missing -> blocks
    before = handler.metrics.rejected_trades
    result = handler._check_book_priceable()
    assert result.priceable is False
    # No side effects leaked out of the pure helper:
    assert handler.metrics.rejected_trades == before       # metrics untouched
    assert journal.calls == []                             # no journal write


# =========================================================================== #
# Phase 2 — Call-site tests (via process_signal)
# =========================================================================== #
# A held position is injected on one symbol; ENTRY signals fire on a DIFFERENT
# symbol (so the stacking guard at step 5 does not pre-empt the freshness gate).

HELD = "NSE_EQ|HELD"
SIG = "NSE_EQ|SIG"   # signalling symbol — no open position, so stacking guard passes


def test_s1_exit_bypasses_gate(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, HELD, 100, 100.0)           # cache empty -> would block
    exit_sig = _make_signal(symbol=HELD, sig_type=SignalType.EXIT, suffix="S1")
    result = handler.process_signal(exit_sig, 110.0)
    assert result is not None                             # EXIT proceeds


def test_s2_stale_held_blocks_entry(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, HELD, 100, 100.0)
    handler.update_market_price(HELD, 100.0)
    handler.clock.advance(timedelta(seconds=61))          # HELD goes stale
    result = handler.process_signal(_make_signal(symbol=SIG, suffix="S2"), 50.0)
    assert result is None
    assert handler.metrics.rejected_trades == 1


def test_s3_fresh_prices_proceed_to_capital_gate(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, HELD, 100, 100.0)
    handler.update_market_price(HELD, 100.0)              # fresh
    result = handler.process_signal(_make_signal(symbol=SIG, suffix="S3"), 50.0)
    assert result is not None                             # passed both gates
    assert handler.metrics.rejected_trades == 0


def test_s4_rejected_trades_incremented_on_block(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, HELD, 100, 100.0)           # missing -> block
    before = handler.metrics.rejected_trades
    handler.process_signal(_make_signal(symbol=SIG, suffix="S4"), 50.0)
    assert handler.metrics.rejected_trades == before + 1


def test_s5_warning_logged_on_block(tmp_path, monkeypatch, caplog):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, HELD, 100, 100.0)           # missing
    monkeypatch.setattr(handler.logger, "propagate", True)
    with caplog.at_level(logging.WARNING):
        result = handler.process_signal(_make_signal(symbol=SIG, suffix="S5"), 50.0)
    assert result is None
    msgs = [r.getMessage() for r in caplog.records]
    assert any("PORTFOLIO_UNPRICEABLE" in m for m in msgs)
    assert any(HELD in m for m in msgs)


def test_s6_journal_event_written_on_block(tmp_path, monkeypatch):
    journal = _MockJournal()
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0,
                             journal=journal)
    _inject_position(handler, HELD, 100, 100.0)           # missing
    handler.process_signal(_make_signal(symbol=SIG, suffix="S6"), 50.0)
    assert len(journal.calls) == 1
    call = journal.calls[0]
    assert call["event_type"] == EventType.PORTFOLIO_UNPRICEABLE
    assert call["metadata"]["missing_symbols"] == [HELD]
    assert call["metadata"]["signal_symbol"] == SIG
    assert call["metadata"]["max_price_age_s"] == 60.0


def test_s7_no_journal_no_error(tmp_path, monkeypatch):
    """Backtest path: _journal is None. Block must still work; no AttributeError;
    broker never called."""
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0,
                             journal=None)
    _inject_position(handler, HELD, 100, 100.0)           # missing -> block
    broker_calls = {"n": 0}
    real_place = handler.broker.place_order

    def spy(order):
        broker_calls["n"] += 1
        return real_place(order)

    monkeypatch.setattr(handler.broker, "place_order", spy)
    result = handler.process_signal(_make_signal(symbol=SIG, suffix="S7"), 50.0)
    assert result is None
    assert broker_calls["n"] == 0                          # broker never reached


def test_s8_disabled_gate_never_blocks(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=float('inf'))
    _inject_position(handler, HELD, 100, 100.0)           # missing, but gate off
    result = handler.process_signal(_make_signal(symbol=SIG, suffix="S8"), 50.0)
    assert result is not None
    assert handler.metrics.rejected_trades == 0


# =========================================================================== #
# Phase 3 — Integration tests
# =========================================================================== #

def test_i1_end_to_end_freshness_block(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, HELD, 100, 100.0)
    handler.update_market_price(HELD, 100.0)
    handler.clock.advance(timedelta(seconds=70))          # stale
    result = handler.process_signal(_make_signal(symbol=SIG, suffix="I1"), 50.0)
    assert result is None
    assert handler.metrics.rejected_trades == 1


def test_i2_update_market_price_unblocks(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, HELD, 100, 100.0)
    handler.update_market_price(HELD, 100.0)
    handler.clock.advance(timedelta(seconds=70))          # stale -> blocks
    blocked = handler.process_signal(_make_signal(symbol=SIG, suffix="I2a"), 50.0)
    assert blocked is None
    # Re-warm HELD at the current (advanced) clock time -> fresh again.
    handler.update_market_price(HELD, 101.0)
    result = handler.process_signal(_make_signal(symbol=SIG, suffix="I2b"), 50.0)
    assert result is not None                             # unblocked


def test_i3_self_resolving_cold_window(tmp_path, monkeypatch):
    """Spec §2.12 / F10: a missing held symbol blocks, then resolves once its
    bar warms the cache — the self-resolving startup cold window."""
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, HELD, 100, 100.0)           # cache cold -> MISSING
    first = handler.process_signal(_make_signal(symbol=SIG, suffix="I3a"), 50.0)
    assert first is None                                  # blocked (missing)
    # HELD's bar arrives (driver warms it):
    handler.update_market_price(HELD, 100.0)
    second = handler.process_signal(_make_signal(symbol=SIG, suffix="I3b"), 50.0)
    assert second is not None                             # gate now passes


# =========================================================================== #
# Phase 4 — Acceptance tests (Definition of Done)
# =========================================================================== #

def test_a1_eventtype_and_default_severity():
    assert EventType.PORTFOLIO_UNPRICEABLE.value == "PORTFOLIO_UNPRICEABLE"
    assert _DEFAULT_SEVERITY[EventType.PORTFOLIO_UNPRICEABLE] == Severity.WARNING


def test_a2_max_price_age_s_defaults_to_inf():
    assert math.isinf(ExecutionConfig().max_price_age_s)


def test_a3_gate_noop_when_disabled(tmp_path, monkeypatch):
    """F7: with float('inf'), even a fully unpriceable book does not block."""
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=float('inf'))
    _inject_position(handler, HELD, 100, 100.0)           # missing, gate off
    result = handler.process_signal(_make_signal(symbol=SIG, suffix="A3"), 50.0)
    assert result is not None
    assert handler.metrics.rejected_trades == 0


def test_a4_freshness_gate_runs_before_capital_gate(tmp_path, monkeypatch):
    """F2/§4 ordering: when freshness blocks, _check_margin_budget is NEVER
    reached. We make the capital gate raise; a freshness block must swallow it."""
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, HELD, 100, 100.0)           # missing -> freshness blocks

    def capital_boom(order, current_price):
        raise AssertionError("capital gate reached — freshness should block first")

    monkeypatch.setattr(handler, "_check_margin_budget", capital_boom)
    # Must NOT raise; freshness returns None before capital gate runs.
    result = handler.process_signal(_make_signal(symbol=SIG, suffix="A4"), 50.0)
    assert result is None
    assert handler.metrics.rejected_trades == 1


def test_a5_gate_uses_deterministic_clock(tmp_path, monkeypatch):
    """ADR-003 / §2.5: the verdict tracks self.clock.now(), never wall-clock.
    Advancing ONLY the deterministic ReplayClock flips fresh->stale while no
    real time elapses."""
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0)
    _inject_position(handler, HELD, 100, 100.0)
    handler.update_market_price(HELD, 100.0)              # snapshot @ clock.now()
    assert handler._check_book_priceable().priceable is True
    # Advance only the deterministic clock — wall-clock untouched.
    handler.clock.advance(timedelta(seconds=61))
    assert handler._check_book_priceable().priceable is False


# =========================================================================== #
# Phase 5 — Regression tests
# =========================================================================== #

def test_r2_capital_gate_still_fires_when_prices_fresh(tmp_path, monkeypatch, caplog):
    """TC-R2: with all prices fresh (gate passes), an over-budget order is
    rejected by the MM9.1 CAPITAL gate — not the freshness gate."""
    handler = _build_handler(tmp_path, monkeypatch, max_price_age_s=60.0,
                             max_utilisation=0.0)         # anything > 0 rejected
    _inject_position(handler, HELD, 100, 100.0)
    handler.update_market_price(HELD, 100.0)              # fresh -> freshness passes
    monkeypatch.setattr(handler.logger, "propagate", True)
    with caplog.at_level(logging.WARNING):
        result = handler.process_signal(_make_signal(symbol=SIG, suffix="R2"), 50.0)
    assert result is None
    assert handler.metrics.rejected_trades == 1
    msgs = [r.getMessage() for r in caplog.records]
    assert any("MARGIN_BUDGET_REJECTED" in m for m in msgs)
    assert not any("PORTFOLIO_UNPRICEABLE" in m for m in msgs)


# =========================================================================== #
# PriceabilityResult value-object contract
# =========================================================================== #

def test_priceability_result_is_frozen_and_equal():
    a = PriceabilityResult(priceable=False, stale_symbols={"X"},
                           missing_symbols={"Y"})
    b = PriceabilityResult(priceable=False, stale_symbols={"X"},
                           missing_symbols={"Y"})
    assert a == b
    with pytest.raises(Exception):
        a.priceable = True  # frozen dataclass — attribute mutation forbidden
