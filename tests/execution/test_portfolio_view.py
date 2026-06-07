"""
Phase 1 — PortfolioView (read-only portfolio projection).

PortfolioView is a *projection*, not a source of truth (ADR-001 — Ledger Is
Truth). Given a price snapshot and the current cash balance, it reads the
existing execution trackers and returns an immutable PortfolioSnapshot. It
performs no new financial logic: every field is a pass-through of an existing
tracker calculation (PORTFOLIO_STATE_DISCOVERY.md section 5.2).

These tests prove the eight requirements of the phase plus the ADR-002
forbidden-import invariant.
"""

import ast
import dataclasses
from pathlib import Path

from core.execution.position_tracker import PositionTracker
from core.execution.pnl_tracker import PnLTracker
from core.execution.margin_tracker import MarginTracker
from core.execution.position_models import Position, PositionSide
from core.execution.portfolio_view import PortfolioView, PortfolioSnapshot
from core.instruments.equity import Equity


def _trackers():
    pt = PositionTracker()
    return pt, PnLTracker(pt), MarginTracker(pt)


def _open(pt, symbol, side, quantity, avg_price):
    pt._positions[symbol] = Position(
        instrument=Equity(symbol), side=side, quantity=quantity, avg_price=avg_price)


# --------------------------------------------------------------------------- #
# 1. Empty portfolio
# --------------------------------------------------------------------------- #
def test_empty_portfolio_snapshot():
    pt, pnl, margin = _trackers()
    view = PortfolioView(pt, pnl, margin)

    snap = view.snapshot(current_prices={}, cash_balance=100000.0)

    assert snap.positions == {}
    assert snap.cash_balance == 100000.0
    assert snap.realized_pnl == 0.0
    assert snap.unrealized_pnl == 0.0
    assert snap.gross_exposure == 0.0
    assert snap.used_margin == 0.0
    assert snap.mtm_equity == 100000.0  # equity == cash when the book is empty


# --------------------------------------------------------------------------- #
# 2. Single position
# --------------------------------------------------------------------------- #
def test_single_position_snapshot():
    pt, pnl, margin = _trackers()
    _open(pt, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    view = PortfolioView(pt, pnl, margin)

    snap = view.snapshot(current_prices={"RELIANCE": 2600.0}, cash_balance=50000.0)

    assert set(snap.positions) == {"RELIANCE"}
    assert snap.positions["RELIANCE"].quantity == 10
    # unrealized = (2600 - 2500) * 10 = 1000
    assert snap.unrealized_pnl == 1000.0
    # gross exposure = 10 * 2600 = 26000
    assert snap.gross_exposure == 26000.0
    # used margin = 26000 * 0.20
    assert snap.used_margin == 5200.0
    assert snap.mtm_equity == 51000.0  # cash 50000 + unrealized 1000


# --------------------------------------------------------------------------- #
# 3. Multi position
# --------------------------------------------------------------------------- #
def test_multi_position_snapshot():
    pt, pnl, margin = _trackers()
    _open(pt, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    _open(pt, "TCS", PositionSide.SHORT, 5, 3500.0)
    view = PortfolioView(pt, pnl, margin)

    prices = {"RELIANCE": 2600.0, "TCS": 3400.0}
    snap = view.snapshot(current_prices=prices, cash_balance=50000.0)

    assert set(snap.positions) == {"RELIANCE", "TCS"}
    # RELIANCE long: (2600 - 2500) * 10 = +1000
    # TCS short:     (3400 - 3500) * 5 * -1 = +500
    assert snap.unrealized_pnl == 1500.0
    # gross exposure = 10*2600 + 5*3400 = 26000 + 17000 = 43000
    assert snap.gross_exposure == 43000.0
    assert snap.used_margin == 43000.0 * 0.20
    assert snap.mtm_equity == 51500.0  # cash 50000 + unrealized 1500


# --------------------------------------------------------------------------- #
# 4. MTM equity (non-zero unrealized so equity != cash)
# --------------------------------------------------------------------------- #
def test_mtm_equity_reflects_unrealized():
    pt, pnl, margin = _trackers()
    _open(pt, "INFY", PositionSide.LONG, 100, 1500.0)
    view = PortfolioView(pt, pnl, margin)

    snap = view.snapshot(current_prices={"INFY": 1450.0}, cash_balance=200000.0)

    # unrealized = (1450 - 1500) * 100 = -5000
    assert snap.unrealized_pnl == -5000.0
    assert snap.mtm_equity == 195000.0
    assert snap.mtm_equity != snap.cash_balance


# --------------------------------------------------------------------------- #
# 4b. realized PnL is already in cash — never added to equity twice
# --------------------------------------------------------------------------- #
def test_mtm_equity_excludes_realized_pnl():
    pt, pnl, margin = _trackers()
    _open(pt, "INFY", PositionSide.LONG, 100, 1500.0)
    pnl._realized_pnl["INFY"] = 7500.0  # closed-trade profit, already in cash
    view = PortfolioView(pt, pnl, margin)

    snap = view.snapshot(current_prices={"INFY": 1550.0}, cash_balance=200000.0)

    assert snap.realized_pnl == 7500.0
    assert snap.unrealized_pnl == 5000.0  # (1550 - 1500) * 100
    # equity = cash + unrealized ONLY; realized is baked into cash already.
    assert snap.mtm_equity == 205000.0


# --------------------------------------------------------------------------- #
# 5. Exposure comes from the existing MarginTracker
# --------------------------------------------------------------------------- #
def test_exposure_comes_from_margin_tracker():
    pt, pnl, margin = _trackers()
    _open(pt, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    view = PortfolioView(pt, pnl, margin)
    prices = {"RELIANCE": 2600.0}

    snap = view.snapshot(current_prices=prices, cash_balance=0.0)

    assert snap.gross_exposure == margin.get_exposure(prices)
    assert snap.used_margin == margin.get_used_margin(prices)


# --------------------------------------------------------------------------- #
# 6. Determinism (non-empty book)
# --------------------------------------------------------------------------- #
def test_snapshot_is_deterministic():
    pt, pnl, margin = _trackers()
    _open(pt, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    _open(pt, "TCS", PositionSide.SHORT, 5, 3500.0)
    view = PortfolioView(pt, pnl, margin)
    prices = {"RELIANCE": 2600.0, "TCS": 3400.0}

    a = view.snapshot(current_prices=prices, cash_balance=50000.0)
    b = view.snapshot(current_prices=prices, cash_balance=50000.0)

    assert a == b


# --------------------------------------------------------------------------- #
# 7. No side effects — trackers are never mutated, snapshot is immutable
# --------------------------------------------------------------------------- #
def test_view_does_not_mutate_trackers():
    pt, pnl, margin = _trackers()
    _open(pt, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    view = PortfolioView(pt, pnl, margin)

    before = pt.get_all_positions()
    realized_before = pnl.get_realized_pnl()

    snap = view.snapshot(current_prices={"RELIANCE": 2600.0}, cash_balance=50000.0)

    assert pt.get_all_positions() == before
    assert pnl.get_realized_pnl() == realized_before
    # mutating the returned positions dict must not reach the tracker
    snap.positions["RELIANCE"] = None
    assert pt.get_all_positions()["RELIANCE"].quantity == 10


def test_snapshot_is_frozen():
    import pytest
    pt, pnl, margin = _trackers()
    view = PortfolioView(pt, pnl, margin)
    snap = view.snapshot(current_prices={}, cash_balance=100000.0)

    assert isinstance(snap, PortfolioSnapshot)
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.cash_balance = 1.0


# --------------------------------------------------------------------------- #
# 8 (+ ADR-002). Forbidden-import guard — PortfolioView is pure platform infra.
# --------------------------------------------------------------------------- #
def test_module_imports_no_strategy_or_alpha_code():
    forbidden_roots = {
        "strategies", "backtest", "runner", "ftmo",
        "models", "scanners", "research", "analytics",
    }
    src_path = Path(__file__).resolve().parents[2] / "core" / "execution" / "portfolio_view.py"
    tree = ast.parse(src_path.read_text(encoding="utf-8"))

    imported_roots: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
                if alias.name.startswith("core."):
                    imported_roots.add(alias.name.split(".")[1])
        elif isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            imported_roots.add(parts[0])
            if parts[0] == "core" and len(parts) > 1:
                imported_roots.add(parts[1])

    assert forbidden_roots.isdisjoint(imported_roots), (
        f"portfolio_view.py must not import strategy/alpha code; "
        f"found roots: {sorted(imported_roots)}"
    )
