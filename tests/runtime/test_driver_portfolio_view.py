"""
Block B — LoopDriver._build_positions() enrichment (MM9.3-S2).

The enriched path produces:
  {symbol: {quantity, avg_price, side, current_price, pnl_pct}, ...,
   _portfolio_summary: {version, cash_balance, realized_pnl, unrealized_pnl,
                        mtm_equity, gross_exposure, used_margin,
                        portfolio_greeks: {delta, gamma, vega, theta, rho}}}

The raw/degraded path (no PortfolioView injected) returns the pre-S2 flat format.
"""

import logging
from unittest.mock import Mock

from core.execution.position_models import Position, PositionSide
from core.execution.portfolio_view import PortfolioSnapshot
from core.instruments.equity import Equity
from core.risk.greeks.greeks_model import Greeks
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver

from _doubles import (FakeExecutionHandler, FakeClock, FakePriceSnapshot)


def _open(handler, symbol, side, quantity, avg_price):
    handler.position_tracker._positions[symbol] = Position(
        instrument=Equity(symbol), side=side, quantity=quantity, avg_price=avg_price)


# --------------------------------------------------------------------------- #
# B1. LoopDriver accepts optional portfolio_view
# --------------------------------------------------------------------------- #
def test_driver_accepts_optional_portfolio_view():
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=["A"])
    d = LoopDriver(cfg)
    assert d._portfolio_view is None


# --------------------------------------------------------------------------- #
# B2. Startup WARNING logged when no portfolio_view
# --------------------------------------------------------------------------- #
def test_driver_startup_warning_when_no_portfolio_view(caplog):
    logging.getLogger("loop_driver").propagate = True
    caplog.set_level(logging.WARNING)
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=["A"])
    LoopDriver(cfg)
    assert "PortfolioView unavailable" in caplog.text


# --------------------------------------------------------------------------- #
# B3. Raw path when no view → no _portfolio_summary
# --------------------------------------------------------------------------- #
def test_build_positions_raw_when_no_view():
    handler = FakeExecutionHandler()
    _open(handler, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    d = LoopDriver(DriverConfig(mode=Mode.REPLAY, symbols=["A"]),
                   clock=FakeClock(), execution=handler)
    payload = d._build_positions()
    assert "RELIANCE" in payload
    assert "_portfolio_summary" not in payload
    assert payload["RELIANCE"]["quantity"] == 10
    assert payload["RELIANCE"]["pnl_pct"] == 0.0  # placeholder on raw path


# --------------------------------------------------------------------------- #
# B4. Empty book when no ExecutionHandler
# --------------------------------------------------------------------------- #
def test_build_positions_returns_empty_when_no_execution():
    d = LoopDriver(DriverConfig(mode=Mode.REPLAY, symbols=["A"]))
    assert d._build_positions() == {}


# --------------------------------------------------------------------------- #
# B5. Enriched payload has _portfolio_summary with all fields
# --------------------------------------------------------------------------- #
def test_build_positions_enriched_payload_has_portfolio_summary():
    handler = FakeExecutionHandler()
    handler._price_cache = {}
    snap = PortfolioSnapshot(
        positions={},
        cash_balance=100000.0,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        mtm_equity=100000.0,
        gross_exposure=0.0,
        used_margin=0.0,
        portfolio_greeks=Greeks(0.0, 0.0, 0.0, 0.0, 0.0),
    )
    mock_view = Mock()
    mock_view.snapshot.return_value = snap
    d = LoopDriver(DriverConfig(mode=Mode.REPLAY, symbols=["A"]),
                   clock=FakeClock(), execution=handler,
                   portfolio_view=mock_view)
    payload = d._build_positions()
    assert "_portfolio_summary" in payload
    summary = payload["_portfolio_summary"]
    for key in ("cash_balance", "realized_pnl", "unrealized_pnl",
                "mtm_equity", "gross_exposure", "used_margin",
                "portfolio_greeks", "version"):
        assert key in summary, f"missing _portfolio_summary.{key}"


# --------------------------------------------------------------------------- #
# B6. portfolio_greeks sub-structure is correct
# --------------------------------------------------------------------------- #
def test_build_positions_portfolio_greeks_structure():
    handler = FakeExecutionHandler()
    handler._price_cache = {}
    snap = PortfolioSnapshot(
        positions={},
        cash_balance=100000.0,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        mtm_equity=100000.0,
        gross_exposure=0.0,
        used_margin=0.0,
        portfolio_greeks=Greeks(10.5, 0.5, 2.0, -1.0, 0.1),
    )
    mock_view = Mock()
    mock_view.snapshot.return_value = snap
    d = LoopDriver(DriverConfig(mode=Mode.REPLAY, symbols=["A"]),
                   clock=FakeClock(), execution=handler,
                   portfolio_view=mock_view)
    payload = d._build_positions()
    pg = payload["_portfolio_summary"]["portfolio_greeks"]
    assert set(pg.keys()) == {"delta", "gamma", "vega", "theta", "rho"}
    assert isinstance(pg["delta"], float)
    assert isinstance(pg["gamma"], float)
    assert isinstance(pg["vega"], float)
    assert isinstance(pg["theta"], float)
    assert isinstance(pg["rho"], float)
    assert pg["delta"] == 10.5
    assert pg["gamma"] == 0.5
    assert pg["vega"] == 2.0
    assert pg["theta"] == -1.0
    assert pg["rho"] == 0.1


# --------------------------------------------------------------------------- #
# B7. pnl_pct computed not placeholder
# --------------------------------------------------------------------------- #
def test_build_positions_pnl_pct_computed_not_placeholder():
    handler = FakeExecutionHandler()
    handler._price_cache["SYM"] = FakePriceSnapshot(price=110.0)
    pos = Position(instrument=Equity("SYM"), side=PositionSide.LONG,
                   quantity=10, avg_price=100.0)
    snap = PortfolioSnapshot(
        positions={"SYM": pos},
        cash_balance=100000.0,
        realized_pnl=0.0,
        unrealized_pnl=100.0,
        mtm_equity=100100.0,
        gross_exposure=1100.0,
        used_margin=220.0,
        portfolio_greeks=Greeks(0.0, 0.0, 0.0, 0.0, 0.0),
    )
    mock_view = Mock()
    mock_view.snapshot.return_value = snap
    d = LoopDriver(DriverConfig(mode=Mode.REPLAY, symbols=["A"]),
                   clock=FakeClock(), execution=handler,
                   portfolio_view=mock_view)
    payload = d._build_positions()
    assert payload["SYM"]["pnl_pct"] == 10.0  # (110-100)/100 * 100
    assert "current_price" in payload["SYM"]
    assert payload["SYM"]["current_price"] == 110.0


# --------------------------------------------------------------------------- #
# B8. snapshot exception → fall back to raw, error logged
# --------------------------------------------------------------------------- #
def test_build_positions_snapshot_exception_falls_back_to_raw(caplog):
    logging.getLogger("loop_driver").propagate = True
    caplog.set_level(logging.ERROR)
    handler = FakeExecutionHandler()
    _open(handler, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    handler._price_cache["RELIANCE"] = FakePriceSnapshot(price=2600.0)
    mock_view = Mock()
    mock_view.snapshot.side_effect = RuntimeError("snapshot boom")
    d = LoopDriver(DriverConfig(mode=Mode.REPLAY, symbols=["A"]),
                   clock=FakeClock(), execution=handler,
                   portfolio_view=mock_view)
    payload = d._build_positions()
    assert "_portfolio_summary" not in payload
    assert "RELIANCE" in payload
    assert payload["RELIANCE"]["pnl_pct"] == 0.0  # raw path placeholder
    assert any("snapshot boom" in rec.message for rec in caplog.records)
