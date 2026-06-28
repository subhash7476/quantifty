"""
Block A — PortfolioSnapshot and PortfolioView Greek fields (MM9.3-S2).
"""

from unittest.mock import Mock

from core.execution.position_tracker import PositionTracker
from core.execution.pnl_tracker import PnLTracker
from core.execution.margin_tracker import MarginTracker
from core.execution.position_models import Position, PositionSide
from core.execution.portfolio_view import PortfolioView, PortfolioSnapshot
from core.instruments.equity import Equity
from core.risk.greeks.greeks_model import Greeks
from core.risk.greeks.portfolio_greeks import PortfolioGreeks


def _trackers():
    pt = PositionTracker()
    return pt, PnLTracker(pt), MarginTracker(pt)


def _open(pt, symbol, side, quantity, avg_price):
    pt._positions[symbol] = Position(
        instrument=Equity(symbol), side=side, quantity=quantity, avg_price=avg_price)


# --------------------------------------------------------------------------- #
# A1. PortfolioSnapshot has portfolio_greeks field
# --------------------------------------------------------------------------- #
def test_portfolio_snapshot_has_portfolio_greeks_field():
    pt, pnl, margin = _trackers()
    view = PortfolioView(pt, pnl, margin)
    snap = view.snapshot(current_prices={}, cash_balance=100000.0)
    assert hasattr(snap, "portfolio_greeks")
    assert isinstance(snap.portfolio_greeks, Greeks)


# --------------------------------------------------------------------------- #
# A2. No PortfolioGreeks injected → zero Greeks
# --------------------------------------------------------------------------- #
def test_portfolio_view_without_pg_returns_zero_greeks():
    pt, pnl, margin = _trackers()
    view = PortfolioView(pt, pnl, margin)
    snap = view.snapshot(current_prices={}, cash_balance=100000.0)
    assert snap.portfolio_greeks == Greeks(0.0, 0.0, 0.0, 0.0, 0.0)


# --------------------------------------------------------------------------- #
# A3. PortfolioGreeks injected → computed Greeks returned
# --------------------------------------------------------------------------- #
def test_portfolio_view_with_pg_returns_computed_greeks():
    pt, pnl, margin = _trackers()
    mock_pg = Mock()
    mock_pg.calculate_portfolio_greeks.return_value = Greeks(50.0, 1.0, 2.0, 0.0, 0.0)
    view = PortfolioView(pt, pnl, margin, portfolio_greeks=mock_pg)
    snap = view.snapshot(current_prices={"SYM": 100.0}, cash_balance=50000.0)
    assert snap.portfolio_greeks.delta == 50.0
    assert snap.portfolio_greeks.gamma == 1.0
    assert snap.portfolio_greeks.vega == 2.0


# --------------------------------------------------------------------------- #
# A4. calculate_portfolio_greeks called with market_prices from snapshot()
# --------------------------------------------------------------------------- #
def test_portfolio_view_pg_called_with_price_cache():
    pt, pnl, margin = _trackers()
    mock_pg = Mock()
    mock_pg.calculate_portfolio_greeks.return_value = Greeks(0.0, 0.0, 0.0, 0.0, 0.0)
    view = PortfolioView(pt, pnl, margin, portfolio_greeks=mock_pg)
    prices = {"SYM": 100.0, "OTHER": 50.0}
    view.snapshot(current_prices=prices, cash_balance=50000.0)
    mock_pg.calculate_portfolio_greeks.assert_called_once()
    _, kwargs = mock_pg.calculate_portfolio_greeks.call_args
    assert kwargs["market_prices"] == prices


# --------------------------------------------------------------------------- #
# A5. volatilities={} and time_to_expiry_map={} in the PG call
# --------------------------------------------------------------------------- #
def test_portfolio_view_pg_called_with_empty_vol_and_tte():
    pt, pnl, margin = _trackers()
    mock_pg = Mock()
    mock_pg.calculate_portfolio_greeks.return_value = Greeks(0.0, 0.0, 0.0, 0.0, 0.0)
    view = PortfolioView(pt, pnl, margin, portfolio_greeks=mock_pg)
    view.snapshot(current_prices={"SYM": 100.0}, cash_balance=50000.0)
    _, kwargs = mock_pg.calculate_portfolio_greeks.call_args
    assert kwargs["volatilities"] == {}
    assert kwargs["time_to_expiry_map"] == {}


# --------------------------------------------------------------------------- #
# A6. Zero Greeks on empty book with real PortfolioGreeks injected
# --------------------------------------------------------------------------- #
def test_portfolio_view_zero_greeks_on_empty_book_with_pg_injected():
    pt, pnl, margin = _trackers()
    pg = PortfolioGreeks(pt)
    view = PortfolioView(pt, pnl, margin, portfolio_greeks=pg)
    snap = view.snapshot(current_prices={"SYM": 100.0}, cash_balance=50000.0)
    assert snap.portfolio_greeks == Greeks(0.0, 0.0, 0.0, 0.0, 0.0)


# --------------------------------------------------------------------------- #
# A7. Snapshot is deterministic with Greeks
# --------------------------------------------------------------------------- #
def test_portfolio_view_snapshot_deterministic_with_greeks():
    pt, pnl, margin = _trackers()
    _open(pt, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    pg = PortfolioGreeks(pt)
    view = PortfolioView(pt, pnl, margin, portfolio_greeks=pg)
    prices = {"RELIANCE": 2600.0}
    a = view.snapshot(current_prices=prices, cash_balance=50000.0)
    b = view.snapshot(current_prices=prices, cash_balance=50000.0)
    assert a == b


# --------------------------------------------------------------------------- #
# A8. Snapshot does not mutate trackers with PG injected
# --------------------------------------------------------------------------- #
def test_portfolio_view_does_not_mutate_trackers_with_pg():
    pt, pnl, margin = _trackers()
    _open(pt, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    pg = PortfolioGreeks(pt)
    view = PortfolioView(pt, pnl, margin, portfolio_greeks=pg)
    before = pt.get_all_positions()
    view.snapshot(current_prices={"RELIANCE": 2600.0}, cash_balance=50000.0)
    assert pt.get_all_positions() == before
    assert pt.get_all_positions()["RELIANCE"].quantity == 10
