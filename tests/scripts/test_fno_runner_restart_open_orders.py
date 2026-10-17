"""
A LIVE restart with orders still open in the ledger (PR #47 review, G).

The adapter's set of orders to poll lives in memory, so after a restart nothing
polls an order placed earlier the same day: if it filled at Upstox since, the
ledger is behind. Startup reconciliation compares positions only and would not
name the order. build_runner therefore alerts, naming each such order.

Orders are validity DAY, so an open order from an earlier day is dead and is not
reported; PAPER fills inline, so it is never checked.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytz

import scripts.fno_runner as fno_runner
from core.execution.handler import ExecutionMode
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.persistence.order_repository import OrderRepository

from _runner_harness import EQUITY, FIXED_DT, NoopSource, build


def _ledger_with(tmp_path, *orders):
    repo = OrderRepository(ExecutionStore(str(tmp_path / "execution.db")))
    for order in orders:
        repo.save(order)


def _order(signal_id, timestamp):
    return NormalizedOrder(symbol=EQUITY, side=OrderSide.BUY, quantity=50,
                           order_type=OrderType.MARKET, strategy_id="live",
                           signal_id=signal_id, timestamp=timestamp)


def _live(tmp_path, monkeypatch, alerts, adapter=None):
    creds = MagicMock()
    creds.has_upstox_token = True
    creds.is_token_expired = False
    monkeypatch.setattr(fno_runner, "_live_credentials", creds)
    monkeypatch.setattr(fno_runner, "alerter", alerts)
    return build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,),
                 execution_mode=ExecutionMode.LIVE, broker=adapter or MagicMock(),
                 broker_positions=lambda: [])


def test_a_live_restart_alerts_on_an_order_placed_earlier_today(tmp_path, monkeypatch):
    alerts = MagicMock()
    _ledger_with(tmp_path, _order("sig-open-today", FIXED_DT - timedelta(hours=2)))

    _live(tmp_path, monkeypatch, alerts)

    alerts.critical.assert_called_once()
    message = alerts.critical.call_args.args[0]
    assert "sig-open-today" in message and "BUY 50" in message
    # Honest about what the ledger can't tell: it never records a reject or cancel.
    assert "rejected or cancelled" in message and "order book" in message


def test_an_open_order_from_an_earlier_day_is_not_reported(tmp_path, monkeypatch):
    alerts = MagicMock()
    _ledger_with(tmp_path, _order("sig-yesterday", FIXED_DT - timedelta(days=1)))

    _live(tmp_path, monkeypatch, alerts)

    alerts.critical.assert_not_called()


def test_a_restart_with_a_clean_ledger_raises_no_alert(tmp_path, monkeypatch):
    alerts = MagicMock()

    _live(tmp_path, monkeypatch, alerts)

    alerts.critical.assert_not_called()


def test_paper_never_checks_for_open_orders(tmp_path, monkeypatch):
    alerts = MagicMock()
    monkeypatch.setattr(fno_runner, "alerter", alerts)
    _ledger_with(tmp_path, _order("sig-open-today", FIXED_DT - timedelta(hours=2)))

    build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,))

    alerts.critical.assert_not_called()


def test_a_rejected_order_is_reported_on_restart_because_the_ledger_never_closes_it(
        tmp_path, monkeypatch):
    """KNOWN LIMIT (handler.py is frozen for the E008 window): nothing tells the
    handler's OrderTracker that Upstox rejected an order, so it stays CREATED and
    the next LIVE restart that day lists it. The alert wording says so; closing
    the order in the tracker is a handler change for after the window."""
    from tests.brokers._upstox_http import install, order_details, placed
    from core.brokers.mapping.upstox import UpstoxMapping
    from core.brokers.upstox_adapter import BrokerOrderNotFilledError, UpstoxAdapter
    from core.clock import ReplayClock
    from core.events import SignalEvent, SignalType

    http = install(monkeypatch)
    http.route("POST", "/order/place", placed("R-1"))
    http.route("GET", "/order/details",
               order_details("R-1", "rejected", quantity=50, filled=0, average_price=0.0,
                             instrument_token=EQUITY, transaction_type="BUY",
                             status_message="Insufficient funds"))
    adapter = UpstoxAdapter("key", "secret", "token", ReplayClock(FIXED_DT))
    adapter._req_interval = 0
    adapter._mapping = UpstoxMapping(db_path=tmp_path / "no_master.duckdb")
    monkeypatch.setattr("core.brokers.upstox_adapter.alerter", MagicMock())
    driver = _live(tmp_path, monkeypatch, MagicMock(), adapter=adapter)
    driver._execution.process_signal(SignalEvent(
        strategy_id="live", symbol=EQUITY, timestamp=FIXED_DT, signal_type=SignalType.BUY,
        confidence=1.0, metadata={"quantity": 50, "sl_distance": 5.0, "risk_r": 1.0,
                                  "signal_id": "sig-rejected"}), current_price=2500.0)
    try:
        adapter.poll_fills()
    except BrokerOrderNotFilledError:
        pass

    restart_alerts = MagicMock()
    _live(tmp_path, monkeypatch, restart_alerts)

    restart_alerts.critical.assert_called_once()
    assert "sig-rejected" in restart_alerts.critical.call_args.args[0]
