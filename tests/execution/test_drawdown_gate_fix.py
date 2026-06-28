"""
Block D+E+F — Drawdown Gate I.M.2 Full Fix (MM9.3-S3).
"""

from datetime import datetime

import pytz

import core.execution.handler as handler_mod
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode, PriceSnapshot
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.portfolio_view import PortfolioView
from core.execution.position_models import Position, PositionSide
from core.instruments.equity import Equity

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


def _build_handler(tmp_path, monkeypatch, initial_capital=100000.0, **extra_kwargs):
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
        config=ExecutionConfig(mode=ExecutionMode.PAPER, **extra_kwargs),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
    ), clock


def _make_signal(symbol="NSE_EQ|INE001", signal_type=SignalType.BUY, suffix=""):
    return SignalEvent(
        strategy_id="test_strat",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=signal_type,
        confidence=0.9,
        metadata={"signal_id": f"SIG-S3-{suffix}", "entry_price": 100.0},
    )


# --------------------------------------------------------------------------- #
# Block D — Handler _handler_portfolio_view construction
# --------------------------------------------------------------------------- #
def test_handler_constructs_handler_portfolio_view(tmp_path, monkeypatch):
    handler, _ = _build_handler(tmp_path, monkeypatch)
    assert hasattr(handler, "_handler_portfolio_view")
    assert isinstance(handler._handler_portfolio_view, PortfolioView)


def test_handler_portfolio_view_wraps_handler_trackers(tmp_path, monkeypatch):
    handler, _ = _build_handler(tmp_path, monkeypatch)
    pv = handler._handler_portfolio_view
    assert pv.position_tracker is handler.position_tracker
    assert pv.pnl_tracker is handler.pnl_tracker
    assert pv.margin_tracker is handler.margin_tracker


def test_handler_portfolio_view_gets_portfolio_greeks(tmp_path, monkeypatch):
    handler, _ = _build_handler(tmp_path, monkeypatch)
    assert handler._handler_portfolio_view._portfolio_greeks is handler.portfolio_greeks


def test_handler_portfolio_view_no_conflict_with_driver_view(tmp_path, monkeypatch):
    handler, clock = _build_handler(tmp_path, monkeypatch)
    from core.runtime.driver import LoopDriver
    from core.runtime.config import DriverConfig, Mode
    driver_pv = PortfolioView(
        position_tracker=handler.position_tracker,
        pnl_tracker=handler.pnl_tracker,
        margin_tracker=handler.margin_tracker,
        portfolio_greeks=handler.portfolio_greeks,
    )
    driver = LoopDriver(
        DriverConfig(mode=Mode.REPLAY, symbols=["NSE_EQ|INE001"]),
        clock=clock,
        portfolio_view=driver_pv,
        execution=handler,
    )
    snap_h = handler._handler_portfolio_view.snapshot({}, 100000.0)
    snap_d = driver_pv.snapshot({}, 100000.0)
    assert snap_h == snap_d


# --------------------------------------------------------------------------- #
# Block E — Drawdown gate equity computation
# --------------------------------------------------------------------------- #
def test_drawdown_gate_uses_mtm_equity(tmp_path, monkeypatch):
    handler, clock = _build_handler(tmp_path, monkeypatch)
    # Seed a profitable position
    handler.position_tracker._positions["SYM1"] = Position(
        instrument=Equity("SYM1"), side=PositionSide.LONG, quantity=10, avg_price=100.0)
    # Warm price cache via the public method
    handler.update_market_price("SYM1", 110.0)

    captured_equity = []
    _orig_snapshot = PortfolioView.snapshot
    def _spy(self, current_prices, cash_balance):
        snap = _orig_snapshot(self, current_prices=current_prices, cash_balance=cash_balance)
        captured_equity.append(snap.mtm_equity)
        return snap
    monkeypatch.setattr(PortfolioView, "snapshot", _spy)

    cash_before = handler.metrics.cash_balance
    result = handler.process_signal(
        _make_signal("NSE_EQ|INE002", suffix="E1"), current_price=100.0)

    assert captured_equity, "PortfolioView.snapshot must have been called"
    assert captured_equity[0] > cash_before, (
        "mtm_equity must include the profitable position's unrealized PnL")


def test_drawdown_gate_multi_position_equity(tmp_path, monkeypatch):
    handler, clock = _build_handler(tmp_path, monkeypatch)
    # Two positions: SYM1 profitable, SYM2 profitable
    handler.position_tracker._positions["SYM1"] = Position(
        instrument=Equity("SYM1"), side=PositionSide.LONG, quantity=10, avg_price=100.0)
    handler.position_tracker._positions["SYM2"] = Position(
        instrument=Equity("SYM2"), side=PositionSide.LONG, quantity=5, avg_price=50.0)
    handler.update_market_price("SYM1", 110.0)
    handler.update_market_price("SYM2", 60.0)

    captured_equity = []
    _orig_snapshot = PortfolioView.snapshot
    def _spy(self, current_prices, cash_balance):
        snap = _orig_snapshot(self, current_prices=current_prices, cash_balance=cash_balance)
        captured_equity.append(snap.mtm_equity)
        return snap
    monkeypatch.setattr(PortfolioView, "snapshot", _spy)

    cash_before = handler.metrics.cash_balance
    handler.process_signal(
        _make_signal("NSE_EQ|INE003", suffix="E2"), current_price=100.0)

    assert captured_equity
    # mtm_equity uses the cash_balance at gate-time (before the signal's own
    # fill reduces cash), plus ALL positions' unrealized PnL.
    expected_equity = cash_before + (110 - 100) * 10 + (60 - 50) * 5
    assert captured_equity[0] == expected_equity, (
        "mtm_equity must include ALL positions' unrealized PnL")


def test_drawdown_gate_matches_correct_single_position_formula(tmp_path, monkeypatch):
    handler, clock = _build_handler(tmp_path, monkeypatch)
    handler.position_tracker._positions["SYM1"] = Position(
        instrument=Equity("SYM1"), side=PositionSide.LONG, quantity=10, avg_price=100.0)
    handler.update_market_price("SYM1", 110.0)

    captured_equity = []
    _orig_snapshot = PortfolioView.snapshot
    def _spy(self, current_prices, cash_balance):
        snap = _orig_snapshot(self, current_prices=current_prices, cash_balance=cash_balance)
        captured_equity.append(snap.mtm_equity)
        return snap
    monkeypatch.setattr(PortfolioView, "snapshot", _spy)

    cash_before = handler.metrics.cash_balance
    handler.process_signal(
        _make_signal("NSE_EQ|INE004", suffix="E3"), current_price=100.0)

    assert captured_equity
    # mtm_equity = cash_at_gate_time + (current - avg) * qty
    expected = cash_before + (110.0 - 100.0) * 10
    assert captured_equity[0] == expected


def test_drawdown_gate_triggers_on_full_portfolio_loss(tmp_path, monkeypatch):
    handler, clock = _build_handler(
        tmp_path, monkeypatch,
        initial_capital=10000.0,
        max_drawdown_limit=0.05,
    )
    handler.position_tracker._positions["SYM_LOSS"] = Position(
        instrument=Equity("SYM_LOSS"), side=PositionSide.LONG, quantity=100, avg_price=200.0)
    handler.update_market_price("SYM_LOSS", 150.0)

    # equity = 10000 + (150-200)*100 = 10000 - 5000 = 5000
    # drawdown = (10000 - 5000) / 10000 = 50% > 5% → triggers kill switch
    result = handler.process_signal(
        _make_signal("NSE_EQ|INE005", suffix="E4"), current_price=100.0)

    assert result is None, "drawdown breach must return None"
    assert handler._kill_switched, "drawdown breach must activate kill switch"


# --------------------------------------------------------------------------- #
# Block F — Exit bypass regression
# --------------------------------------------------------------------------- #
def test_exit_signal_bypasses_drawdown_gate(tmp_path, monkeypatch):
    handler, clock = _build_handler(tmp_path, monkeypatch)
    handler.position_tracker._positions["SYM1"] = Position(
        instrument=Equity("SYM1"), side=PositionSide.LONG, quantity=10, avg_price=100.0)
    handler.update_market_price("SYM1", 110.0)

    # Set a loss position so drawdown would trip for an ENTRY
    handler.position_tracker._positions["SYM_LOSS"] = Position(
        instrument=Equity("SYM_LOSS"), side=PositionSide.LONG, quantity=100, avg_price=200.0)
    handler.update_market_price("SYM_LOSS", 150.0)

    result = handler.process_signal(
        _make_signal("SYM1", SignalType.EXIT, suffix="F1"), current_price=110.0)

    # EXIT must pass through even though equity is in drawdown territory
    assert result is not None, "EXIT must bypass drawdown gate"
