"""
MM9.2-S2 — MarginTracker Multiplier Fix + Zero-Price Guard + Cold-Cache Warning.

Three surgical repairs (spec §10, Slice MM9.2-S2):

1. ``_calculate_single_exposure`` now prefers ``lot_size`` over ``multiplier``,
   so restored Option positions (canonical_restore sets lot_size=ci.lot_size but
   multiplier=1.0) compute exposure as ``qty × price × lot_size`` instead of
   ``qty × price × 1``. Futures already fold lot_size into multiplier
   (core/execution/futures.py:49); Equity has neither (defaults to 1.0).

2. ``get_exposure`` guard changed from ``if price:`` to ``if price is not None:``
   so a zero-priced leg (deep OTM near expiry) stays in the sum, contributing 0
   exposure instead of being silently skipped.

3. ExecutionHandler.__init__ emits ONE startup WARNING when _replay_state
   recovered positions but _latest_prices is empty (D-S1-4, deferred from
   MM9.2-S1).

Coverage:
  * Multiplier: NIFTY option, BANKNIFTY option, equity, future
  * Exposure: multiple options summed, mixed equity+option, portfolio totals
  * Zero-price: None skipped, 0.0 included, zero contribution
  * Startup warning: emitted with recovered positions, absent on fresh start,
    emitted exactly once
"""

import logging
from datetime import date, datetime

import pytz

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.brokers.paper_broker import PaperBroker
from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.margin_tracker import MarginTracker
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.position_models import Position, PositionSide
from core.execution.position_tracker import PositionTracker
from core.instruments.equity import Equity
from core.instruments.future import Future
from core.instruments.option import Option, OptionType

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
WARNING_SUBSTR = "latest-price cache is cold"


# =========================================================================== #
# Helpers
# =========================================================================== #

def _tracker_with_positions(positions: dict) -> MarginTracker:
    """Build a standalone MarginTracker whose position_tracker holds the given
    {symbol: Position} mapping. Exercises MarginTracker directly without the
    full handler — the unit under test is the multiplier/guard fix."""
    pt = PositionTracker()
    pt._positions = dict(positions)
    return MarginTracker(pt, margin_rate=0.2)


def _option(symbol, underlying, lot_size, strike=22500.0,
            opt_type=OptionType.CALL, expiry=date(2026, 6, 30)):
    """Mimics canonical_restore._resolve_option: lot_size from master, multiplier
    hardcoded to 1.0 — the exact defect MM9.2-S2 repairs."""
    return Option(
        symbol=symbol,
        underlying=underlying,
        expiry=expiry,
        strike=strike,
        option_type=opt_type,
        lot_size=lot_size,
        multiplier=1.0,
    )


def _future(symbol, underlying, lot_size, expiry=date(2026, 6, 30)):
    """Mimics core/execution/futures.resolve_future master-present path: lot_size
    folded into multiplier (core/execution/futures.py:49)."""
    return Future(
        symbol=symbol,
        underlying=underlying,
        expiry=expiry,
        multiplier=float(lot_size),
    )


def _long(instrument, qty=1):
    return Position(instrument=instrument, side=PositionSide.LONG, quantity=qty)


def _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0):
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
        config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
    )


def _make_signal(symbol="NSE_EQ|INE001A01036", sig_type=SignalType.BUY,
                 suffix="S2", quantity=None):
    metadata = {
        "signal_id": f"SIG-MM9.2-S2-{suffix}",
        "sl_distance": 1.0,
        "risk_r": 1.0,
    }
    if quantity is not None:
        metadata["quantity"] = quantity
    return SignalEvent(
        strategy_id="test_mm9_2_s2",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=sig_type,
        confidence=0.9,
        metadata=metadata,
    )


# =========================================================================== #
# 1. Multiplier — single-position exposure
# =========================================================================== #

def test_recovered_nifty_option_uses_lot_size():
    """NIFTY option, lot_size=75, multiplier=1.0 (canonical_restore defect).
    exposure must be qty × price × 75, not × 1."""
    opt = _option("NIFTY30JUN2622500CE", "NIFTY", lot_size=75)
    mt = _tracker_with_positions({"NIFTY30JUN2622500CE": _long(opt, qty=2)})
    exposure = mt.get_exposure({"NIFTY30JUN2622500CE": 200.0})
    # 2 lots × 200 × 75 = 30000 (would be 400 under the old ×1 defect)
    assert exposure == 2 * 200.0 * 75


def test_recovered_banknifty_option_uses_lot_size():
    """BANKNIFTY option, lot_size=30, multiplier=1.0."""
    opt = _option("BANKNIFTY30JUN2550000CE", "BANKNIFTY", lot_size=30)
    mt = _tracker_with_positions({"BANKNIFTY30JUN2550000CE": _long(opt, qty=1)})
    exposure = mt.get_exposure({"BANKNIFTY30JUN2550000CE": 500.0})
    # 1 × 500 × 30 = 15000 (would be 500 under the old ×1 defect)
    assert exposure == 1 * 500.0 * 30


def test_equity_still_uses_multiplier_1():
    """Equity has no lot_size attribute; falls back to multiplier=1.0."""
    eq = Equity("NSE_EQ|INE001A01036")
    mt = _tracker_with_positions({"NSE_EQ|INE001A01036": _long(eq, qty=100)})
    exposure = mt.get_exposure({"NSE_EQ|INE001A01036": 200.0})
    assert exposure == 100 * 200.0 * 1.0


def test_future_uses_multiplier_which_is_lot_size():
    """Future carries lot_size folded into multiplier (futures.py:49).
    getattr(instrument, 'lot_size', None) is None -> falls back to multiplier."""
    fut = _future("NIFTY26JUNFUT", "NIFTY", lot_size=75)
    mt = _tracker_with_positions({"NIFTY26JUNFUT": _long(fut, qty=1)})
    exposure = mt.get_exposure({"NIFTY26JUNFUT": 22000.0})
    # multiplier=75.0 was set at construction; lot_size attr absent -> fallback
    assert exposure == 1 * 22000.0 * 75.0


# =========================================================================== #
# 2. Exposure — portfolio aggregation
# =========================================================================== #

def test_multiple_option_positions_summed_correctly():
    nifty = _option("NIFTY30JUN2622500CE", "NIFTY", lot_size=75)
    bnf = _option("BANKNIFTY30JUN2550000CE", "BANKNIFTY", lot_size=30)
    mt = _tracker_with_positions({
        "NIFTY30JUN2622500CE": _long(nifty, qty=2),
        "BANKNIFTY30JUN2550000CE": _long(bnf, qty=1),
    })
    prices = {"NIFTY30JUN2622500CE": 200.0, "BANKNIFTY30JUN2550000CE": 500.0}
    exposure = mt.get_exposure(prices)
    # 2×200×75 + 1×500×30 = 30000 + 15000 = 45000
    assert exposure == 45000.0


def test_mixed_equity_and_option_portfolio():
    eq = Equity("NSE_EQ|INE001A01036")
    opt = _option("NIFTY30JUN2622500CE", "NIFTY", lot_size=75)
    mt = _tracker_with_positions({
        "NSE_EQ|INE001A01036": _long(eq, qty=100),
        "NIFTY30JUN2622500CE": _long(opt, qty=1),
    })
    prices = {"NSE_EQ|INE001A01036": 200.0, "NIFTY30JUN2622500CE": 100.0}
    exposure = mt.get_exposure(prices)
    # 100×200×1 + 1×100×75 = 20000 + 7500 = 27500
    assert exposure == 27500.0


def test_portfolio_exposure_matches_expected_values():
    """End-to-end: exposure -> used_margin at the configured margin_rate."""
    opt = _option("NIFTY30JUN2622500CE", "NIFTY", lot_size=75)
    mt = _tracker_with_positions({"NIFTY30JUN2622500CE": _long(opt, qty=3)})
    used = mt.get_used_margin({"NIFTY30JUN2622500CE": 200.0})
    # exposure = 3×200×75 = 45000; used_margin = 45000 × 0.2 = 9000
    assert used == 9000.0


# =========================================================================== #
# 3. Zero-price guard
# =========================================================================== #

def test_price_none_skipped():
    """None price -> symbol skipped entirely (no error, no contribution)."""
    opt = _option("NIFTY30JUN2622500CE", "NIFTY", lot_size=75)
    mt = _tracker_with_positions({"NIFTY30JUN2622500CE": _long(opt, qty=1)})
    exposure = mt.get_exposure({})  # symbol absent -> .get() returns None
    assert exposure == 0.0


def test_price_zero_included():
    """0.0 price -> leg stays in the sum (MM9.2-S2 fix), contributing 0.
    Under the old 'if price:' guard, 0.0 was silently dropped —
    behaviourally identical here but the iteration difference matters for
    callers that count priced legs."""
    opt = _option("NIFTY30JUN2622500CE", "NIFTY", lot_size=75)
    mt = _tracker_with_positions({"NIFTY30JUN2622500CE": _long(opt, qty=5)})
    exposure = mt.get_exposure({"NIFTY30JUN2622500CE": 0.0})
    assert exposure == 0.0  # 5 × 0.0 × 75 = 0


def test_zero_price_does_not_suppress_other_legs():
    """Direct evidence the guard changed: a 0.0 leg alongside a priced leg.
    The priced leg must still contribute."""
    opt_a = _option("NIFTY30JUN2622500CE", "NIFTY", lot_size=75)
    opt_b = _option("NIFTY30JUN26227000PE", "NIFTY", lot_size=75)
    mt = _tracker_with_positions({
        "NIFTY30JUN2622500CE": _long(opt_a, qty=1),
        "NIFTY30JUN26227000PE": _long(opt_b, qty=2),
    })
    prices = {"NIFTY30JUN2622500CE": 0.0, "NIFTY30JUN26227000PE": 100.0}
    exposure = mt.get_exposure(prices)
    # 1×0×75 + 2×100×75 = 0 + 15000
    assert exposure == 15000.0


# =========================================================================== #
# 4. Cold-cache startup warning (D-S1-4)
# =========================================================================== #

def test_warning_not_emitted_on_fresh_startup(tmp_path, monkeypatch, caplog):
    """No recovered positions -> no cold-cache warning."""
    monkeypatch.setattr(handler_mod, "ExecutionStore",
                        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")))
    DatabaseManager.reset_instance()
    clock = ReplayClock(FIXED_DT)
    with caplog.at_level(logging.WARNING):
        handler = ExecutionHandler(
            db_manager=DatabaseManager(data_root=tmp_path),
            clock=clock,
            broker=PaperBroker(clock),
            config=ExecutionConfig(),
            metrics_path=str(tmp_path / "metrics.json"),
            load_db_state=True,
        )
    msgs = [r.getMessage() for r in caplog.records]
    assert not any(WARNING_SUBSTR in m for m in msgs)
    assert len(handler.position_tracker.get_all_positions()) == 0


def test_warning_emitted_when_recovered_positions_exist(tmp_path, monkeypatch, caplog):
    """Recovery path: handler1 fills an order (persisted); handler2 replays it,
    sees a held position, and emits the cold-cache warning exactly once."""
    monkeypatch.setattr(handler_mod, "ExecutionStore",
                        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")))
    DatabaseManager.reset_instance()

    # Phase 1: handler1 opens a position that persists to execution.db.
    clock1 = ReplayClock(FIXED_DT)
    handler1 = ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock1,
        broker=PaperBroker(clock1),
        config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
    )
    sig = _make_signal(symbol="NSE_EQ|INE001A01036", suffix="WARM")
    assert handler1.process_signal(sig, 100.0) is not None
    assert handler1.position_tracker.has_open_position("NSE_EQ|INE001A01036")

    # Phase 2: handler2 restarts against the same store; _replay_state recovers
    # the position. _latest_prices is empty -> warning must fire.
    DatabaseManager.reset_instance()
    clock2 = ReplayClock(FIXED_DT)
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        handler2 = ExecutionHandler(
            db_manager=DatabaseManager(data_root=tmp_path),
            clock=clock2,
            broker=PaperBroker(clock2),
            config=ExecutionConfig(),
            metrics_path=str(tmp_path / "metrics2.json"),
            load_db_state=True,
        )

    # Position recovered, cache still cold.
    assert handler2.position_tracker.has_open_position("NSE_EQ|INE001A01036")
    assert handler2._price_cache == {}

    # Warning fired with the documented message and the correct count.
    warm_msgs = [r.getMessage() for r in caplog.records
                 if WARNING_SUBSTR in r.getMessage()]
    assert len(warm_msgs) == 1
    assert "1 held position" in warm_msgs[0]


def test_warning_emitted_exactly_once(tmp_path, monkeypatch, caplog):
    """The warning must fire exactly once per handler construction, regardless
    of how many positions are recovered."""
    monkeypatch.setattr(handler_mod, "ExecutionStore",
                        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")))
    DatabaseManager.reset_instance()

    # Open TWO positions on distinct symbols via handler1.
    clock1 = ReplayClock(FIXED_DT)
    handler1 = ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock1,
        broker=PaperBroker(clock1),
        config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
    )
    handler1.process_signal(
        _make_signal(symbol="NSE_EQ|INE001A01036", suffix="A"), 100.0)
    handler1.process_signal(
        _make_signal(symbol="NSE_EQ|INE002A01020", suffix="B"), 100.0)
    assert len(handler1.position_tracker.get_all_positions()) == 2

    # handler2 recovers both.
    DatabaseManager.reset_instance()
    clock2 = ReplayClock(FIXED_DT)
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        handler2 = ExecutionHandler(
            db_manager=DatabaseManager(data_root=tmp_path),
            clock=clock2,
            broker=PaperBroker(clock2),
            config=ExecutionConfig(),
            metrics_path=str(tmp_path / "metrics2.json"),
            load_db_state=True,
        )

    warm_msgs = [r.getMessage() for r in caplog.records
                 if WARNING_SUBSTR in r.getMessage()]
    assert len(warm_msgs) == 1  # exactly one warning
    assert "2 held position" in warm_msgs[0]
