"""
Phase 2 — ExecutionMode.LIVE rung tests for scripts.fno_runner.

Covers:
  L1. LIVE rung uses the injected BrokerAdapter for order routing (not PaperBroker).
  L2. broker_positions is auto-constructed from the adapter when not overridden.
  L3. The auto-constructed callable chains correctly through rekey + shape adapter:
      get_positions() -> rekey_broker_positions_by_token() -> to_reconcile_positions().
  L4. Token-absent positions emit a warning and are excluded from the shaped list.
  L5. Explicit broker_positions override is respected (caller owns the callable).
  L6. _make_live_broker_positions: typed exception from get_positions() propagates
      (not swallowed) so LoopDriver._reconcile_ledger can convert to REFUSAL.

Built with the MM7C/MM7D.1 isolation construction where the driver is needed;
for unit-level callable tests, the real _make_live_broker_positions is called
directly (no driver construction required).
"""

import logging
from datetime import datetime
from unittest.mock import MagicMock

import pytz
import pytest

from core.brokers.broker_position import BrokerPosition
from core.brokers.upstox_adapter import BrokerUnavailableError
from core.execution.handler import ExecutionMode
from core.execution.position_models import PositionSide

from scripts.fno_runner import _make_live_broker_positions

from _runner_harness import EQUITY, NoopSource, build

NOW = datetime(2026, 6, 15, 9, 30, tzinfo=pytz.UTC)
TOKEN = "NSE_FO|53001"


def _mock_broker(*broker_positions):
    """Return a MagicMock BrokerAdapter whose get_positions() returns the supplied
    BrokerPosition objects keyed on their .symbol."""
    mock = MagicMock()
    mock.get_positions.return_value = {bp.symbol: bp for bp in broker_positions}
    return mock


def _long_bp(symbol="NIFTYFUT", token=TOKEN):
    return BrokerPosition(
        symbol=symbol, side=PositionSide.LONG, quantity=75.0,
        avg_price=22500.0, last_updated=NOW, instrument_token=token,
    )


def _flat_bp(symbol="RELIANCE", token=None):
    return BrokerPosition(
        symbol=symbol, side=PositionSide.LONG, quantity=10.0,
        avg_price=2500.0, last_updated=NOW, instrument_token=token,
    )


# --------------------------------------------------------------------------- #
# L1 — LIVE rung uses the injected broker, not PaperBroker
# --------------------------------------------------------------------------- #

def test_live_rung_uses_injected_broker_for_order_routing(tmp_path, monkeypatch):
    from core.brokers.paper_broker import PaperBroker

    mock_adapter = _mock_broker(_long_bp())
    d = build(
        tmp_path, monkeypatch,
        source=NoopSource(), symbols=(EQUITY,),
        execution_mode=ExecutionMode.LIVE,
        broker=mock_adapter,
        broker_positions=lambda: [],  # explicit override — flat book
    )
    assert d._execution.broker is mock_adapter
    assert not isinstance(d._execution.broker, PaperBroker)
    assert d._execution.config.mode is ExecutionMode.LIVE


# --------------------------------------------------------------------------- #
# L2 — broker_positions is auto-constructed when not overridden
# --------------------------------------------------------------------------- #

def test_live_rung_auto_constructs_broker_positions_when_not_provided(
        tmp_path, monkeypatch):
    mock_adapter = _mock_broker(_long_bp())
    d = build(
        tmp_path, monkeypatch,
        source=NoopSource(), symbols=(EQUITY,),
        execution_mode=ExecutionMode.LIVE,
        broker=mock_adapter,
        broker_positions=None,   # trigger auto-construction
    )
    assert d._broker_positions is not None
    assert callable(d._broker_positions)


# --------------------------------------------------------------------------- #
# L3 — auto-constructed callable chains correctly (unit-level, no driver)
# --------------------------------------------------------------------------- #

def test_make_live_broker_positions_returns_shaped_list_for_token_bearing_position():
    bp = _long_bp(symbol="NIFTYFUT", token=TOKEN)
    mock_adapter = _mock_broker(bp)
    fetch = _make_live_broker_positions(mock_adapter)

    result = fetch()

    # Rekeyed on instrument_token; shaped for reconcile engine
    assert result == [{"symbol": TOKEN, "quantity": 75.0, "side": "LONG"}]


def test_make_live_broker_positions_empty_when_no_positions():
    mock_adapter = MagicMock()
    mock_adapter.get_positions.return_value = {}
    fetch = _make_live_broker_positions(mock_adapter)
    assert fetch() == []


# --------------------------------------------------------------------------- #
# L4 — token-absent position: excluded + warning emitted
# --------------------------------------------------------------------------- #

def test_make_live_broker_positions_excludes_token_absent_and_warns(caplog):
    equity_bp = _flat_bp(symbol="RELIANCE", token=None)  # no instrument_token
    mock_adapter = _mock_broker(equity_bp)
    fetch = _make_live_broker_positions(mock_adapter)

    with caplog.at_level(logging.WARNING, logger="scripts.fno_runner"):
        result = fetch()

    assert result == []  # excluded from reconcile
    assert any("excluded" in r.message or "instrument_token" in r.message
               for r in caplog.records)


def test_make_live_broker_positions_mixes_token_and_no_token(caplog):
    deriv_bp = _long_bp(symbol="NIFTYFUT", token=TOKEN)
    equity_bp = _flat_bp(symbol="RELIANCE", token=None)
    mock_adapter = _mock_broker(deriv_bp, equity_bp)
    fetch = _make_live_broker_positions(mock_adapter)

    with caplog.at_level(logging.WARNING, logger="scripts.fno_runner"):
        result = fetch()

    # Only the token-bearing position makes it through
    assert result == [{"symbol": TOKEN, "quantity": 75.0, "side": "LONG"}]
    assert any("excluded" in r.message for r in caplog.records)


# --------------------------------------------------------------------------- #
# L5 — explicit broker_positions override respected
# --------------------------------------------------------------------------- #

def test_live_rung_explicit_broker_positions_override_is_used(tmp_path, monkeypatch):
    mock_adapter = _mock_broker(_long_bp())
    explicit = lambda: [{"symbol": "OVERRIDE", "quantity": 1.0, "side": "LONG"}]

    d = build(
        tmp_path, monkeypatch,
        source=NoopSource(), symbols=(EQUITY,),
        execution_mode=ExecutionMode.LIVE,
        broker=mock_adapter,
        broker_positions=explicit,
    )
    assert d._broker_positions is explicit


# --------------------------------------------------------------------------- #
# L6 — typed exception from get_positions() propagates (not swallowed)
# --------------------------------------------------------------------------- #

def test_make_live_broker_positions_propagates_broker_unavailable_error():
    mock_adapter = MagicMock()
    mock_adapter.get_positions.side_effect = BrokerUnavailableError("transport down")
    fetch = _make_live_broker_positions(mock_adapter)

    with pytest.raises(BrokerUnavailableError):
        fetch()
